#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_all_zones.py
RXP Translator V6 - Extrae zonas/subzonas para cualquier idioma.

Fuentes:
    1. LibBabble-SubZone-3.0 (rxpguides_locale/subzone_*.lua)
    2. Questie GitHub (Localization/Translations/Zones)

Genera: database/zones_{locale}.json

Uso:
    python extract_all_zones.py              # Extrae esES (default)
    python extract_all_zones.py deDE         # Extrae alemán
    python extract_all_zones.py all           # Extrae TODOS los idiomas
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE_DIR = BASE_DIR / "database"
RXPGUIDES_LOCALE = BASE_DIR / "rxpguides_locale"

GITHUB_RAW = "https://raw.githubusercontent.com/Questie/Questie/master/Localization/Translations/Zones"
QUESTIE_FILES = [
    "EasternKingdoms.lua", "Kalimdor.lua", "Outland.lua",
    "Northrend.lua", "Dungeons.lua", "Raids.lua", "Battlegrounds.lua",
]

from locales_config import SUPPORTED_LOCALES, DEFAULT_LOCALE

# Mapeo de locale a clave Questie para archivos LibBabble
LIBBABBLE_LOCALE_MAP = {
    "esES": "esES", "esMX": "esMX", "deDE": "deDE", "frFR": "frFR",
    "ptBR": "ptBR", "ruRU": "ruRU", "koKR": "koKR", "zhCN": "zhCN", "zhTW": "zhTW",
}


def parse_libbabble(path: Path) -> dict[str, str]:
    """Extrae traducciones de un archivo LibBabble-SubZone."""
    if not path.exists():
        return {}
    content = path.read_text(encoding="utf-8", errors="ignore")
    result = {}
    for m in re.finditer(r'\["([^"]+)"\]\s*=\s*"([^"]*)"', content):
        en, translated = m.group(1), m.group(2)
        if en and translated and en != translated:
            result[en] = translated
    return result


def download_lua(filename: str) -> str:
    url = f"{GITHUB_RAW}/{filename}"
    print(f"    Descargando {filename}...")
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            return response.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"      ⚠ Error: {e}")
        return ""


def parse_questie_zones(lua_content: str, locale: str) -> dict[str, str]:
    """Extrae pares English -> translated de archivos Lua de Questie."""
    result = {}
    entry_re = re.compile(r'\["([^"]+)"\]\s*=\s*\{(.*?)\}', re.DOTALL)

    for match in entry_re.finditer(lua_content):
        en_name = match.group(1)
        block = match.group(2)

        # Buscar el locale específico
        loc_match = re.search(rf'\["{locale}"\]\s*=\s*"([^"]*)"', block)
        translated = loc_match.group(1) if loc_match else None

        if translated == "true":
            translated = None

        # Condicionales de expansión
        if translated is None:
            cond = re.search(
                rf'\["{locale}"\]\s*=\s*\(.*?and\s*"([^"]*)"\)\s*or\s*"([^"]*)"',
                block,
            )
            if cond:
                translated = cond.group(2)

        # Fallback a esMX si buscamos esES y no hay
        if translated is None and locale == "esES":
            mx_match = re.search(r'\["esMX"\]\s*=\s*"([^"]*)"', block)
            if mx_match and mx_match.group(1) != "true":
                translated = mx_match.group(1)

        if translated and translated != en_name:
            result[en_name] = translated

    return result


def extract_locale(locale: str) -> int:
    """Extrae todas las zonas para un locale específico."""
    print(f"\n── {locale} ({SUPPORTED_LOCALES[locale]['name']}) ──")

    all_zones: dict[str, str] = {}

    # Fuente 1: LibBabble-SubZone
    libbabble_file = RXPGUIDES_LOCALE / f"subzone_{locale}.lua"
    if libbabble_file.exists():
        libbabble = parse_libbabble(libbabble_file)
        print(f"  LibBabble: {len(libbabble)} subzonas")
        all_zones.update(libbabble)
    else:
        # Intentar con esES como fallback para esMX
        if locale == "esMX":
            fallback = RXPGUIDES_LOCALE / "subzone_esES.lua"
            if fallback.exists():
                libbabble = parse_libbabble(fallback)
                print(f"  LibBabble (fallback esES): {len(libbabble)} subzonas")
                all_zones.update(libbabble)

    # Fuente 2: Questie GitHub
    for filename in QUESTIE_FILES:
        content = download_lua(filename)
        if not content:
            continue
        translations = parse_questie_zones(content, locale)
        count = 0
        for en, translated in translations.items():
            if en not in all_zones:
                all_zones[en] = translated
                count += 1
        if count:
            print(f"    {filename}: +{count} zonas")

    # Guardar
    output_file = DATABASE_DIR / f"zones_{locale}.json"
    output = {
        "meta": {
            "sources": ["LibBabble-SubZone-3.0", "Questie/Questie GitHub"],
            "locale": locale,
            "total_entries": len(all_zones),
        },
        "zones": all_zones,
    }

    output_file.write_text(
        json.dumps(output, ensure_ascii=False, indent=2, sort_keys=False),
        encoding="utf-8",
    )

    print(f"  ✅ {locale}: {len(all_zones)} zonas → {output_file.name}")
    return len(all_zones)


def main() -> int:
    DATABASE_DIR.mkdir(exist_ok=True)

    print("=" * 55)
    print(" RXP Translator V6 - Extraer zonas/subzonas")
    print("=" * 55)

    # Determinar qué locales extraer
    if len(sys.argv) > 1 and sys.argv[1] == "all":
        locales = list(SUPPORTED_LOCALES.keys())
    elif len(sys.argv) > 1:
        locales = [sys.argv[1]]
    else:
        locales = [DEFAULT_LOCALE]

    total = 0
    for locale in locales:
        total += extract_locale(locale)

    print(f"\n{'=' * 55}")
    print(f" Total: {total} zonas en {len(locales)} idioma(s)")
    print(f"{'=' * 55}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
