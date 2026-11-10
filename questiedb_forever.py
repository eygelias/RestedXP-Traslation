#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
questiedb_forever.py
Lector del formato "baked" de QuestieDB 1.x (flavor Forever / Camelot).

Un artefacto QuestieDB 1.x en modo baked es un .toc de WoW con la base de datos
codificada en el "TOC metadata store" (líneas `## X-...: valor`):

    X-<Tipo>-IDS           lista de IDs (chunkeada `~N~`)  → base64 → zlib → CBOR
    X-<Tipo>-<id>-S        fila scalar de la entidad      → base64 → CBOR
    X-<Tipo>-<id>-<campo>  campo tipo tabla (chunkeable)   → base64 → CBOR
    X-l10n-<locale>-<Tipo> bloque de columnas de l10n       → base64 → zlib → CBOR

Codificación equivalente a C_EncodingUtil del cliente:
    DecodeBase64 → DecompressString(bytes, 1) [zlib] → DeserializeCBOR

Columnas l10n (src/l10n/overlay.lua): una por campo traducible, alineadas con la
lista de IDs ascendente. Cada columna es:
    - lista densa (posición 0-based, huecos = None, nulos finales recortados), o
    - dict esparsa (clave = posición 1-based).

Campos traducibles por tipo:
    Quest:  1=name  2=objectivesText (lista de líneas)
    Npc:    1=name  2=subName
    Item:   1=name
    Object: 1=name

Uso como librería:
    db = QuestieDBForever("QuestieDB-1.0.13-Forever.zip")
    ids = db.entity_ids("Npc")
    db.scalar("Npc", 10000)["name"]            # 'Arugal'
    db.localized_names("esES", "Npc")[10000]   # 'Arugal'

Uso como CLI:
    python questiedb_forever.py QuestieDB-1.0.13-Forever.zip --stats
"""

from __future__ import annotations

import base64
import re
import struct
import sys
import zipfile
import zlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ENTITY_TYPES = ("Quest", "Npc", "Item", "Object")
LOCALES = ("deDE", "esES", "esMX", "frFR", "koKR", "ptBR", "ruRU", "zhCN", "zhTW")

# Campo "name" (índice 1) en todos los esquemas (questMeta/npcMeta/itemMeta/objectMeta).
NAME_FIELD = 1

_CHUNK_RE = re.compile(r"^~(\d+)~$")


# ─────────────────────────────────────────────────────────────────
# CBOR mínimo (RFC 8949) — solo lo que emite el generador de QuestieDB
# ─────────────────────────────────────────────────────────────────

class _Cbor:
    def __init__(self, data: bytes) -> None:
        self.d = data
        self.i = 0

    def _take(self, n: int) -> bytes:
        if self.i + n > len(self.d):
            raise ValueError("CBOR truncado")
        b = self.d[self.i:self.i + n]
        self.i += n
        return b

    def _head(self) -> Tuple[int, int]:
        ib = self._take(1)[0]
        return ib >> 5, ib & 0x1F

    def _len(self, ai: int) -> int:
        if ai < 24:
            return ai
        if ai == 24:
            return int.from_bytes(self._take(1), "big")
        if ai == 25:
            return int.from_bytes(self._take(2), "big")
        if ai == 26:
            return int.from_bytes(self._take(4), "big")
        if ai == 27:
            return int.from_bytes(self._take(8), "big")
        raise ValueError(f"CBOR: longitud indefinida no soportada (ai={ai})")

    def value(self) -> Any:
        mt, ai = self._head()
        if mt == 0:
            return self._len(ai)
        if mt == 1:
            return -1 - self._len(ai)
        if mt == 2:
            return self._take(self._len(ai))
        if mt == 3:
            return self._take(self._len(ai)).decode("utf-8")
        if mt == 4:
            return [self.value() for _ in range(self._len(ai))]
        if mt == 5:
            out: Dict[Any, Any] = {}
            for _ in range(self._len(ai)):
                k = self.value()
                out[k] = self.value()
            return out
        if mt == 6:
            self._len(ai)  # tag: se descarta, se devuelve el valor interno
            return self.value()
        if mt == 7:
            if ai == 20:
                return False
            if ai == 21:
                return True
            if ai == 22:
                return None
            if ai == 23:
                return None
            if ai == 25:
                return struct.unpack(">e", self._take(2))[0]
            if ai == 26:
                return struct.unpack(">f", self._take(4))[0]
            if ai == 27:
                return struct.unpack(">d", self._take(8))[0]
            raise ValueError(f"CBOR: simple ai={ai} no soportado")
        raise ValueError(f"CBOR: major type {mt} no soportado")


def cbor_decode(data: bytes) -> Any:
    """Decodifica un único valor CBOR (bytes de cadena se devuelven como str UTF-8)."""
    return _to_text(_Cbor(data).value())


def _to_text(value: Any) -> Any:
    """Normaliza bytes → str (el codificador de QuestieDB escribe textos como byte strings)."""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, list):
        return [_to_text(v) for v in value]
    if isinstance(value, dict):
        return {_to_text(k): _to_text(v) for k, v in value.items()}
    return value


# ─────────────────────────────────────────────────────────────────
# TOC metadata store
# ─────────────────────────────────────────────────────────────────

def parse_toc(text: str) -> Dict[str, str]:
    """Extrae el metadata store: {clave: valor} de las líneas `## clave: valor`."""
    meta: Dict[str, str] = {}
    for line in text.splitlines():
        if line.startswith("## ") and ":" in line:
            key, _, val = line[3:].partition(":")
            meta[key.strip()] = val.strip()
    return meta


def get_stored(meta: Dict[str, str], key: str) -> Optional[str]:
    """Reensambla un valor chunkeado `~N~` (igual que src/read/baked.lua getStored)."""
    val = meta.get(key)
    if val is None:
        return None
    m = _CHUNK_RE.match(val)
    if not m:
        return val
    parts = []
    for i in range(1, int(m.group(1)) + 1):
        part = meta.get(f"{key}-{i}")
        if part is None:
            raise ValueError(f"chunk {key}-{i} ausente (se declararon {m.group(1)})")
        parts.append(part)
    return "".join(parts)


def _b64(text: str) -> bytes:
    return base64.b64decode(text + "=" * (-len(text) % 4))


# ─────────────────────────────────────────────────────────────────
# Lector de alto nivel
# ─────────────────────────────────────────────────────────────────

class QuestieDBForever:
    """Lee un artefacto QuestieDB 1.x baked desde .toc, carpeta extraída o ZIP."""

    def __init__(self, source: str | Path) -> None:
        self.source = Path(source)
        self._meta = self._load_meta(self.source)
        self._ids_cache: Dict[str, List[int]] = {}
        self._scalar_cache: Dict[Tuple[str, int], dict] = {}

    # ── carga ──
    @staticmethod
    def _load_meta(source: Path) -> Dict[str, str]:
        if source.is_dir():
            for name in ("QuestieDB_Forever.toc", "QuestieDB_Camelot.toc"):
                candidate = source / name
                if candidate.exists():
                    return parse_toc(candidate.read_text(encoding="utf-8", errors="ignore"))
            # carpeta que contiene la subcarpeta QuestieDB/
            nested = source / "QuestieDB"
            if nested.is_dir():
                return QuestieDBForever._load_meta(nested)
            raise FileNotFoundError(f"No hay .toc de QuestieDB en {source}")
        if source.suffix.lower() == ".toc":
            return parse_toc(source.read_text(encoding="utf-8", errors="ignore"))
        if source.suffix.lower() == ".zip":
            with zipfile.ZipFile(source) as zf:
                for name in zf.namelist():
                    if name.endswith("QuestieDB_Forever.toc") or name.endswith("QuestieDB_Camelot.toc"):
                        return parse_toc(zf.read(name).decode("utf-8", errors="ignore"))
            raise FileNotFoundError(f"No hay .toc de QuestieDB en {source}")
        raise ValueError(f"Fuente no soportada: {source}")

    # ── IDs ──
    def entity_ids(self, entity_type: str) -> List[int]:
        if entity_type not in self._ids_cache:
            stored = get_stored(self._meta, f"X-{entity_type}-IDS")
            if stored is None:
                raise KeyError(f"Falta X-{entity_type}-IDS en el metadata store")
            ids = cbor_decode(zlib.decompress(_b64(stored)))
            if not isinstance(ids, list) or not all(isinstance(i, int) for i in ids):
                raise ValueError(f"X-{entity_type}-IDS no es una lista de enteros")
            self._ids_cache[entity_type] = ids
        return self._ids_cache[entity_type]

    # ── scalars ──
    def scalar(self, entity_type: str, entity_id: int) -> Optional[dict]:
        """Fila scalar decodificada como dict {índice de campo: valor}.

        El generador emite dos formas equivalentes:
          - mapa CBOR con claves enteras (+ 'p' = máscara de presencia de tablas)
          - array CBOR denso posicional (posición 0 = campo 1); nulos recortados al final
        Se normaliza siempre a dict de claves de campo 1-based.
        """
        key = (entity_type, entity_id)
        if key not in self._scalar_cache:
            stored = get_stored(self._meta, f"X-{entity_type}-{entity_id}-S")
            row = cbor_decode(_b64(stored)) if stored is not None else None
            if isinstance(row, dict):
                norm = row
            elif isinstance(row, list):
                norm = {i + 1: v for i, v in enumerate(row) if v is not None}
            else:
                norm = {}
            self._scalar_cache[key] = norm
        return self._scalar_cache[key] or None

    def name(self, entity_type: str, entity_id: int) -> str:
        row = self.scalar(entity_type, entity_id)
        if not row:
            return ""
        value = row.get(NAME_FIELD)
        return value.strip() if isinstance(value, str) else ""

    # ── l10n ──
    def l10n_columns(self, locale: str, entity_type: str) -> Optional[list]:
        """Bloque de columnas l10n decodificado para (locale, tipo). None si no existe."""
        stored = get_stored(self._meta, f"X-l10n-{locale}-{entity_type}")
        if stored is None:
            return None
        cols = cbor_decode(zlib.decompress(_b64(stored)))
        return cols if isinstance(cols, list) else None

    @staticmethod
    def _column_lookup(col: Any, pos: int) -> Any:
        """Valor de la columna en posición 0-based de la lista de IDs (densa o esparsa)."""
        if isinstance(col, dict):
            return col.get(pos + 1)          # dict esparsa: claves 1-based
        if isinstance(col, list):
            return col[pos] if pos < len(col) else None  # densa recortada al final
        return None

    def localized_names(self, locale: str, entity_type: str) -> Dict[int, str]:
        """{entity_id: nombre traducido} para los IDs presentes en la columna name."""
        return self._localized_column(locale, entity_type, field=0, scalar=False)

    def localized_subnames(self, locale: str) -> Dict[int, str]:
        """{npc_id: subtítulo traducido} (campo 2 de Npc)."""
        return self._localized_column(locale, "Npc", field=1, scalar=False)

    def localized_objectives(self, locale: str) -> Dict[int, List[str]]:
        """{quest_id: [líneas de objectivesText traducidas]} (campo 2 de Quest)."""
        return self._localized_column(locale, "Quest", field=1, scalar=True)

    def _localized_column(self, locale: str, entity_type: str, field: int, scalar: bool) -> Dict[int, Any]:
        cols = self.l10n_columns(locale, entity_type)
        if not cols or field >= len(cols):
            return {}
        col = cols[field]
        ids = self.entity_ids(entity_type)
        out: Dict[int, Any] = {}
        for pos, entity_id in enumerate(ids):
            raw = self._column_lookup(col, pos)
            if raw is None:
                continue
            if scalar:
                if isinstance(raw, list):
                    lines = [s.strip() for s in raw if isinstance(s, str) and s.strip()]
                    if lines:
                        out[entity_id] = lines
            else:
                if isinstance(raw, str) and raw.strip():
                    out[entity_id] = raw.strip()
        return out


# ─────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────

def _print_stats(db: QuestieDBForever) -> None:
    print(f"Fuente: {db.source}")
    for typ in ENTITY_TYPES:
        ids = db.entity_ids(typ)
        print(f"\n{typ}: {len(ids)} entidades (IDs {ids[0]}..{ids[-1]})")
        for pos in (0, len(ids) // 2, len(ids) - 1):
            eid = ids[pos]
            print(f"  #{eid}: {db.name(typ, eid)!r}")
        for locale in ("esES", "deDE"):
            names = db.localized_names(locale, typ)
            sample = next(iter(names.items()), None)
            print(f"  l10n {locale}: {len(names)} traducciones | ej. {sample}")


def main(argv: List[str]) -> int:
    if len(argv) < 2:
        print("Uso: python questiedb_forever.py <QuestieDB.zip|carpeta|.toc> [--stats]")
        return 2
    db = QuestieDBForever(argv[1])
    if "--stats" in argv:
        _print_stats(db)
    else:
        print(f"OK: {db.source} | Quest={len(db.entity_ids('Quest'))} "
              f"Npc={len(db.entity_ids('Npc'))} Item={len(db.entity_ids('Item'))} "
              f"Object={len(db.entity_ids('Object'))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
