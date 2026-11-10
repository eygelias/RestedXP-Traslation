#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_npcnames.py
RXP Translator V6 - Extrae NPCnames.lua para cualquier idioma soportado.

Lee: rxpguides_locale/NPCnames.lua
Genera: database/npcnames_{locale}.json

Uso:
    python extract_npcnames.py              # Extrae esES (default)
    python extract_npcnames.py deDE         # Extrae alemán
    python extract_npcnames.py all           # Extrae TODOS los idiomas
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
RXPGUIDES_LOCALE = BASE_DIR / "rxpguides_locale"
DATABASE_DIR = BASE_DIR / "database"

NPCNAMES_LUA = RXPGUIDES_LOCALE / "NPCnames.lua"

from locales_config import SUPPORTED_LOCALES, DEFAULT_LOCALE


def ensure_dirs() -> None:
    DATABASE_DIR.mkdir(exist_ok=True)


def parse_npcnames_section(content: str, locale: str) -> dict[str, str]:
    """
    Extrae la tabla addon.npcNames de la sección del locale indicado.

    Formato:
        elseif locale == "deDE" then
        addon.npcNames = {
            ["Guard Byron"] = "Wache Byron",
            ...
        }
    """
    # Buscar la sección del locale
    pattern = rf'elseif\s+locale\s*==\s*"{locale}"\s*then'
    match = re.search(pattern, content)
    if not match:
        # Buscar combinación como "esES" or "esMX"
        pattern = rf'elseif\s+locale\s*==\s*"{locale}"\s*or\s+locale\s*==\s*"[^"]+"\s*then'
        match = re.search(pattern, content)
    if not match:
        # Buscar como segunda opción en combinación
        pattern = rf'elseif\s+locale\s*==\s*"[^"]+"\s*or\s+locale\s*==\s*"{locale}"\s*then'
        match = re.search(pattern, content)

    if not match:
        return {}

    start = match.end()
    table_start = content.find("addon.npcNames", start)
    if table_start == -1:
        return {}

    brace_start = content.find("{", table_start)
    if brace_start == -1:
        return {}

    depth = 0
    pos = brace_start
    while pos < len(content):
        if content[pos] == "{":
            depth += 1
        elif content[pos] == "}":
            depth -= 1
            if depth == 0:
                break
        pos += 1

    table_content = content[brace_start + 1:pos]
    result = {}
    entry_re = re.compile(r'\["([^"]+)"\]\s*=\s*"([^"]*)"')

    for m in entry_re.finditer(table_content):
        en, translated = m.group(1), m.group(2)
        if en and translated:
            result[en] = translated

    return result


def extract_locale(locale: str, content: str) -> int:
    """Extrae un locale específico y guarda el JSON."""
    npcnames = parse_npcnames_section(content, locale)

    if not npcnames:
        print(f"  ⚠ {locale}: No se encontraron entradas")
        return 0

    output_file = DATABASE_DIR / f"npcnames_{locale}.json"
    output = {
        "meta": {
            "source": "RXPGuides/locale/NPCnames.lua",
            "locale": locale,
            "description": f"Nombres de NPCs para {locale}.",
            "total_entries": len(npcnames),
        },
        "npcs": npcnames,
    }

    output_file.write_text(
        json.dumps(output, ensure_ascii=False, indent=2, sort_keys=False),
        encoding="utf-8",
    )

    print(f"  ✅ {locale}: {len(npcnames)} NPCs → {output_file.name}")
    return len(npcnames)


def main() -> int:
    ensure_dirs()

    print("=" * 50)
    print(" RXP Translator V6 - Extraer NPCnames")
    print("=" * 50)

    if not NPCNAMES_LUA.exists():
        print(f"\nERROR: No encontré {NPCNAMES_LUA}")
        print("Copia locale/NPCnames.lua a rxpguides_locale/")
        return 1

    content = NPCNAMES_LUA.read_text(encoding="utf-8")

    # Determinar qué locales extraer
    if len(sys.argv) > 1 and sys.argv[1] == "all":
        locales = list(SUPPORTED_LOCALES.keys())
    elif len(sys.argv) > 1:
        locales = [sys.argv[1]]
    else:
        locales = [DEFAULT_LOCALE]

    print(f"\nExtrayendo {len(locales)} idioma(s)...")
    total = 0

    for locale in locales:
        total += extract_locale(locale, content)

    print(f"\n{'=' * 50}")
    print(f" Total: {total} entradas en {len(locales)} idioma(s)")
    print(f"{'=' * 50}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
