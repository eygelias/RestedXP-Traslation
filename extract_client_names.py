#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_client_names.py
Extrae los nombres REALES de NPCs y objetos directamente de las cachés del
cliente de WoW (formato WDB moderno: magics WMOB / WGOB / WQST).

Es la "verdad de terreno": son exactamente las cadenas que el juego muestra,
asociadas al ID. Formato del contenedor y de los registros tomado de la
implementación de referencia SaneWDBReader (MMOSimca) — lector open-source de
las cachés WDB:

    Cabecera (24 bytes):
        magic    4B  (ASCII invertido: 'WMOB' criaturas, 'WGOB' objetos, 'WQST' misiones)
        build    int32
        locale   4B  (ASCII invertido: 'esMX', 'esES', ...)
        recSize  int32
        recVer   int32
        cacheVer int32
    Registros:
        id int32, length int32, data bytes[length]   (length==0 = fin)

    CreatureCache (dentro de data): cabecera de BITS con longitudes
        title(11) titleAlt(11) cursorName(6) leader(1)
        name0(11) nameAlt0(11) name1(11) nameAlt1(11)
        name2(11) nameAlt2(11) name3(11) nameAlt3(11)
      y a continuación las cadenas UTF-8 con esas longitudes en el mismo orden
      (Name/NameAlt intercalados 0..3).

    GameObjectCache (dentro de data):
        type int32, displayId int32, Name[4] cstring, ...

Uso:
    python extract_client_names.py [--wow "C:\\...\\World of Warcraft"]
Salida:
    database/client_names_<locale>.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_WOW = r"C:\Program Files (x86)\World of Warcraft"
BASE_DIR = Path(__file__).resolve().parent
OUT_DIR = BASE_DIR / "database"


class Bits:
    """Lectura de bits e enteros al estilo DataStore de SaneWDBReader."""

    def __init__(self, data: bytes):
        self.d = data
        self.i = 0
        self._bitpos = 8
        self._curr = 0

    # ── bits ──
    def get_bit(self) -> int:
        if self._bitpos == 8:
            self._curr = self.d[self.i]
            self.i += 1
            self._bitpos = 0
        result = (self._curr >> 7) & 1
        self._curr = (self._curr << 1) & 0xFF
        self._bitpos += 1
        return result

    def get_bits(self, count: int) -> int:
        result = 0
        for _ in range(count):
            result = (result << 1) | self.get_bit()
        return result

    def flush(self) -> None:
        self._bitpos = 8

    # ── enteros / cadenas ──
    def get_int(self) -> int:
        self.flush()
        v = int.from_bytes(self.d[self.i:self.i + 4], "little", signed=True)
        self.i += 4
        return v

    def get_uint(self) -> int:
        self.flush()
        v = int.from_bytes(self.d[self.i:self.i + 4], "little")
        self.i += 4
        return v

    def get_string(self, length: int) -> str:
        self.flush()
        if length <= 0:
            return ""
        raw = self.d[self.i:self.i + length]
        self.i += length
        return raw.decode("utf-8", errors="replace").split("\x00", 1)[0]

    def get_cstring(self) -> str:
        self.flush()
        end = self.d.index(b"\x00", self.i) if b"\x00" in self.d[self.i:] else len(self.d)
        raw = self.d[self.i:end]
        self.i = end + 1 if end < len(self.d) else end
        return raw.decode("utf-8", errors="replace")


def parse_container(path: Path):
    """Devuelve (magic, locale, build, [(id, data), ...]) de un .wdb."""
    data = path.read_bytes()
    magic = data[0:4][::-1].decode("ascii", "replace")
    build = int.from_bytes(data[4:8], "little", signed=True)
    locale = data[8:12][::-1].decode("ascii", "replace")
    # 12: recSize, 16: recVer, 20: cacheVer
    pos = 24
    records = []
    n = len(data)
    while pos + 8 <= n:
        rid = int.from_bytes(data[pos:pos + 4], "little", signed=True)
        length = int.from_bytes(data[pos + 4:pos + 8], "little", signed=True)
        pos += 8
        if length <= 0 or pos + length > n:
            break
        records.append((rid, data[pos:pos + length]))
        pos += length
    return magic, locale, build, records


def parse_creature(data: bytes) -> dict:
    ds = Bits(data)
    title_len = ds.get_bits(11)
    title_alt_len = ds.get_bits(11)
    cursor_len = ds.get_bits(6)
    ds.get_bits(1)  # leader
    lens = [ds.get_bits(11) for _ in range(8)]  # name0, alt0, name1, alt1, ...
    ds.flush()
    names, alts = [], []
    for idx in range(0, 8, 2):
        names.append(ds.get_string(lens[idx]))
        alts.append(ds.get_string(lens[idx + 1]))
    name = next((x for x in names if x), "")
    alt = next((x for x in alts if x), "")
    return {"name": name, "subname": alt, "_title_lens": (title_len, title_alt_len, cursor_len)}


def parse_gameobject(data: bytes) -> dict:
    ds = Bits(data)
    ds.get_int()      # type
    ds.get_int()      # displayId
    names = [ds.get_cstring() for _ in range(4)]
    name = next((x for x in names if x), "")
    return {"name": name}


def extract(wow_dir: Path) -> dict:
    out = {}
    wdb_root = None
    for flavor in sorted(wow_dir.glob("_*")):
        candidate = flavor / "Cache" / "WDB"
        if candidate.exists():
            wdb_root = candidate
            print(f"Caché WDB encontrada en: {candidate}")
    if wdb_root is None:
        raise SystemExit(f"No encontré Cache\\WDB bajo {wow_dir}")

    for locale_dir in sorted(wdb_root.iterdir()):
        if not locale_dir.is_dir():
            continue
        locale = locale_dir.name
        npcs, objects = {}, {}
        for wdb in sorted(locale_dir.glob("*.wdb")):
            magic, _loc, build, records = parse_container(wdb)
            print(f"  {locale}/{wdb.name}: magic={magic} build={build} registros={len(records)}")
            if magic == "WMOB":
                for rid, raw in records:
                    try:
                        info = parse_creature(raw)
                    except Exception:
                        continue
                    if info["name"]:
                        npcs[rid] = {"name": info["name"], "subname": info["subname"]}
            elif magic == "WGOB":
                for rid, raw in records:
                    try:
                        info = parse_gameobject(raw)
                    except Exception:
                        continue
                    if info["name"]:
                        objects[rid] = {"name": info["name"]}
        out[locale] = {
            "meta": {
                "source": f"{locale_dir} (caché del cliente WoW)",
                "extracted_utc": datetime.now(timezone.utc).isoformat(),
                "locale": locale,
                "npcs": len(npcs),
                "objects": len(objects),
            },
            "npcs": {str(k): v for k, v in sorted(npcs.items())},
            "objects": {str(k): v for k, v in sorted(objects.items())},
        }
        print(f"  → {locale}: {len(npcs)} NPCs, {len(objects)} objetos")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wow", default=DEFAULT_WOW, help="Carpeta del juego (con _forever_ dentro)")
    args = ap.parse_args()

    wow_dir = Path(args.wow)
    if not wow_dir.exists():
        print(f"No existe: {wow_dir}")
        return 1

    result = extract(wow_dir)
    OUT_DIR.mkdir(exist_ok=True)
    for locale, payload in result.items():
        out_path = OUT_DIR / f"client_names_{locale}.json"
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\nEscrito: {out_path}")
        sample = list(payload["npcs"].items())[:5]
        for rid, info in sample:
            print(f"   #{rid}: {info['name']!r} {('<' + info['subname'] + '>') if info.get('subname') else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
