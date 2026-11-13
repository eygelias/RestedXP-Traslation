#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_database_forever.py
Construye database/questiedb_forever.json a partir de QuestieDB 1.x (flavor Forever).

Es el equivalente a build_database.py para el formato "baked" de QuestieDB 1.x
(los .toc con metadata store). El archivo generado es exactamente el que
LocalDatabase de translate_guides.py carga cuando wow_version="forever"
(database/questiedb_{wow_version}.json).

Fuentes de datos (en orden de prioridad, igual que el pipeline V6):
    1. manual_overrides.json  - correcciones manuales (se aplican en tiempo de traducción)
    2. NPCnames.lua (RXPGuides) - nombres del cliente; sobrescriben traducciones l10n
    3. QuestieDB Forever 1.0.13 - entidades + localizaciones oficiales (l10n)

Lee:
    - QuestieDB-*.zip / carpeta QuestieDB / QuestieDB_Forever.toc  (QuestieDB 1.x baked)
    - rxpguides_locale/NPCnames.lua

Genera:
    - database/questiedb_forever.json  (sección quests/npcs/items/objects multi-locale)

Uso:
    python build_database_forever.py
    python build_database_forever.py --source "C:/ruta/QuestieDB-1.0.13-Forever.zip"
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

from locales_config import SUPPORTED_LOCALES
from questiedb_forever import ENTITY_TYPES, LOCALES, QuestieDBForever

# Reutiliza el parser/merge de NPCnames del pipeline V6 para mantener la misma
# semántica de prioridad (NPCnames > QuestieDB a la hora de construir).
from build_database import merge_npcnames_into_npcs, parse_npcnames_locale

BASE_DIR = Path(__file__).resolve().parent
DATABASE_DIR = BASE_DIR / "database"
NPCNAMES_LUA = BASE_DIR / "rxpguides_locale" / "NPCnames.lua"

OUTPUT_DB = DATABASE_DIR / "questiedb_forever.json"

# Mapeo tipo QuestieDB → sección del JSON del traductor (igual que ENTITY_CONFIG de V6).
SECTION_BY_TYPE = {
    "Quest": "quests",
    "Npc": "npcs",
    "Item": "items",
    "Object": "objects",
}

MINIMUM_EXPECTED = {
    "quests": 3000,
    "npcs": 10000,
    "items": 10000,
    "objects": 1000,
}


def detect_source(explicit: str | None) -> Path:
    if explicit:
        path = Path(explicit)
        if not path.exists():
            raise FileNotFoundError(f"No existe la fuente: {path}")
        return path
    candidates = sorted(BASE_DIR.glob("QuestieDB*.zip"))
    if candidates:
        return candidates[-1]
    folder = BASE_DIR / "QuestieDB"
    if folder.exists():
        return folder
    raise FileNotFoundError(
        "No encontré QuestieDB. Coloca QuestieDB-*.zip junto a este script "
        "o pasa --source <zip|carpeta|.toc>."
    )


def build_section(db: QuestieDBForever, entity_type: str) -> Dict[str, dict]:
    section = SECTION_BY_TYPE[entity_type]
    ids = db.entity_ids(entity_type)
    print(f"\n  {section}: {len(ids)} IDs — leyendo nombres y localizaciones")

    entries: Dict[str, dict] = {}
    localized_counts = {locale: 0 for locale in LOCALES}

    # Nombres localizados por locale (una sola pasada por columna).
    per_locale: Dict[str, Dict[int, str]] = {}
    for locale in LOCALES:
        per_locale[locale] = db.localized_names(locale, entity_type)

    for entity_id in ids:
        english = db.name(entity_type, entity_id)
        if not english:
            continue
        entry: dict = {
            "id": entity_id,
            "source": "forever",
            "en": english,
        }
        for locale in LOCALES:
            translated = per_locale[locale].get(entity_id)
            if translated:
                entry[locale] = translated
                localized_counts[locale] += 1
        entries[str(entity_id)] = entry

    done = " | ".join(f"{loc} {n}" for loc, n in localized_counts.items() if n)
    print(f"    registros con nombre EN: {len(entries)}")
    print(f"    con traducción: {done or '(ninguna)'}")
    return entries


def merge_client_names(entries: Dict[str, dict], client: dict, locale: str) -> int:
    """Sobrescribe con los nombres REALES del cliente (caché WDB extraída).

    El cliente es la máxima autoridad: su cadena es exactamente la que el juego
    muestra. Devuelve cuántas entradas cambiaron.
    """
    by_id = {
        int(data["id"]): key
        for key, data in entries.items()
        if isinstance(data, dict) and isinstance(data.get("id"), int)
    }
    changed = 0
    for cid_str, info in client.items():
        try:
            cid = int(cid_str)
        except (TypeError, ValueError):
            continue
        key = by_id.get(cid)
        if key is None:
            continue
        name = str((info or {}).get("name") or "").strip()
        if not name:
            continue
        if str(entries[key].get(locale) or "") != name:
            entries[key][locale] = name
            entries[key][f"client_{locale}"] = True
            changed += 1
    return changed


def overlay_client_names(result: dict) -> int:
    """Aplica database/client_names_<locale>.json sobre npcs y objects."""
    total = 0
    for cpath in sorted(DATABASE_DIR.glob("client_names_*.json")):
        locale = cpath.stem.replace("client_names_", "")
        try:
            payload = json.loads(cpath.read_text(encoding="utf-8"))
        except Exception:
            continue
        for section in ("npcs", "objects"):
            changed = merge_client_names(result.get(section, {}), payload.get(section, {}), locale)
            if changed:
                print(f"  {locale}/{section}: {changed} nombres corregidos con el cliente")
                total += changed
    return total


def validate(result: dict) -> bool:
    problems = []
    for section, minimum in MINIMUM_EXPECTED.items():
        actual = len(result.get(section, {}))
        if actual < minimum:
            problems.append((section, actual, minimum))
    if not problems:
        return True
    print("\n" + "=" * 50)
    print(" ERROR: LA BASE RESULTANTE ES DEMASIADO PEQUEÑA")
    print("=" * 50)
    for section, actual, minimum in problems:
        print(f"  {section:10}: {actual} | mínimo esperado: {minimum}")
    print(f"\nNo se sobrescribió {OUTPUT_DB}.")
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Construye questiedb_forever.json desde QuestieDB 1.x baked")
    parser.add_argument("--source", help="ZIP, carpeta extraída o .toc de QuestieDB 1.x")
    parser.add_argument("--out", help=f"Archivo de salida (por defecto: {OUTPUT_DB})")
    args = parser.parse_args()

    DATABASE_DIR.mkdir(exist_ok=True)
    out_path = Path(args.out) if args.out else OUTPUT_DB

    print("=" * 50)
    print(" RXP Translator — Construir questiedb_forever.json")
    print("=" * 50)

    source_path = detect_source(args.source)
    print(f"\nFuente QuestieDB: {source_path}")
    db = QuestieDBForever(source_path)

    result: Dict[str, dict] = {
        "meta": {
            "generator": "build_database_forever.py",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "questiedb_source": str(source_path),
            "questiedb_flavor": "forever",
            "format": "QuestieDB 1.x baked TOC + NPCnames.lua (multi-locale)",
            "supported_locales": list(SUPPORTED_LOCALES.keys()),
            "l10n_locales": list(LOCALES),
        }
    }

    for entity_type in ENTITY_TYPES:
        print(f"\n{'=' * 50}")
        print(f" Procesando {SECTION_BY_TYPE[entity_type]}")
        print("=" * 50)
        result[SECTION_BY_TYPE[entity_type]] = build_section(db, entity_type)

    # ── Merge NPCnames.lua (misma semántica que build_database.py) ──
    print(f"\n── Fusionar NPCnames.lua con NPCs ──")
    total_npcnames = 0
    for locale_code in SUPPORTED_LOCALES:
        npcnames = parse_npcnames_locale(locale_code)
        if npcnames:
            updated = merge_npcnames_into_npcs(result["npcs"], npcnames, locale_code)
            print(f"  {locale_code}: {len(npcnames)} entradas | {updated} aplicadas")
            total_npcnames += updated
    print(f"  Total NPCnames aplicados: {total_npcnames}")
    result["meta"]["npcnames_merged"] = total_npcnames

    # ── Overlay del CLIENTE (máxima autoridad: lo que el juego muestra) ──
    print(f"\n── Nombres reales del cliente (caché WDB) ──")
    total_client = overlay_client_names(result)
    print(f"  Total nombres de cliente aplicados: {total_client}")
    result["meta"]["client_names_merged"] = total_client

    if not validate(result):
        return 1

    import json
    out_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=False),
        encoding="utf-8",
    )

    print(f"\n{'=' * 50}")
    print(" Base construida correctamente")
    print("=" * 50)
    for section in ["quests", "npcs", "items", "objects"]:
        entries = result[section]
        translated = sum(1 for d in entries.values() if len(d) > 3)
        print(f"  {section:10}: {len(entries):7} registros | {translated:7} con traducciones")
    print(f"\nArchivo: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
