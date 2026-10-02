#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_database.py
RXP Translator V4 - Construye la base de datos de traducción unificada.

Fuentes de datos (en orden de prioridad):
    1. manual_overrides.json  - Correcciones manuales (máxima prioridad)
    2. NPCnames.lua (esES)    - Nombres reales del cliente WoW (fuente primaria NPCs)
    3. QuestieDB v0.7.x       - Entidades completas (NPCs, Items, Objects, Quests)
    4. esES.lua (RXPGuides)   - Frases de interfaz del addon

Lee:
    - rxpguides_locale/NPCnames.lua   (addon RXPGuides)
    - rxpguides_locale/esES.lua       (addon RXPGuides)
    - QuestieDB/ o QuestieDB-v*.zip   (QuestieDB)
    - database/manual_overrides.json  (correcciones manuales)

Genera:
    - database/questiedb_es.json   (base principal unificada)
    - database/npcnames_es.json    (NPCnames extraído)
    - database/zones_es.json       (zonas)
    - database/spells_es.json      (habilidades)
    - database/addon_phrases.json  (frases de interfaz del addon)
"""

from __future__ import annotations

import json
import re
import zipfile
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Dict, Tuple

from locales_config import SUPPORTED_LOCALES

BASE_DIR = Path(__file__).resolve().parent
DATABASE_DIR = BASE_DIR / "database"
CACHE_DIR = BASE_DIR / "cache"
RXPGUIDES_LOCALE = BASE_DIR / "rxpguides_locale"

OUTPUT_DB = DATABASE_DIR / "questiedb_es.json"
ZONES_DB = DATABASE_DIR / "zones_es.json"
SPELLS_DB = DATABASE_DIR / "spells_es.json"
MANUAL_OVERRIDES = DATABASE_DIR / "manual_overrides.json"
LEGACY_WOWHEAD_CACHE = CACHE_DIR / "wowhead_cache.json"

NPCNAMES_LUA = RXPGUIDES_LOCALE / "NPCnames.lua"
ESES_LUA = RXPGUIDES_LOCALE / "esES.lua"

PREFERRED_EXPANSIONS = ["Era", "Tbc"]

LOCALE_ORDER = [
    "ptBR", "ruRU", "deDE", "koKR", "esES", "esMX", "frFR", "zhCN", "zhTW",
]

ENTITY_CONFIG = {
    "quests": ("Quest", 4),
    "npcs": ("Npc", 2),
    "items": ("Item", 1),
    "objects": ("Object", 3),
}

MINIMUM_EXPECTED = {
    "quests": 3000,
    "npcs": 10000,
    "items": 10000,
    "objects": 1000,
}

ENTRY_BLOCK_RE = re.compile(
    r"<!--\s*(\d+)\s*-->\s*(.*?)(?=<!--\s*\d+\s*-->|</body>)",
    re.IGNORECASE | re.DOTALL,
)
PARAGRAPH_RE = re.compile(r"<p>(.*?)</p>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")
NUMERIC_ZONE_RE = re.compile(r"^[\d\s,./-]+$")


def ensure_dirs() -> None:
    DATABASE_DIR.mkdir(exist_ok=True)
    CACHE_DIR.mkdir(exist_ok=True)


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, data) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=False),
        encoding="utf-8",
    )


# ─────────────────────────────────────────────────────────
# NPCnames.lua parser
# ─────────────────────────────────────────────────────────

def parse_npcnames_locale(locale: str) -> dict[str, str]:
    """Extrae la tabla NPCnames para un locale específico."""
    if not NPCNAMES_LUA.exists():
        print(f"  ADVERTENCIA: No encontré {NPCNAMES_LUA}")
        return {}

    content = NPCNAMES_LUA.read_text(encoding="utf-8")
    pattern = rf'elseif\s+locale\s*==\s*"{locale}"\s*then'
    match = re.search(pattern, content)

    if not match:
        # Buscar combinación como "esES" or "esMX"
        pattern = rf'elseif\s+locale\s*==\s*"{locale}"\s*or\s+locale\s*==\s*"[^"]+"\s*then'
        match = re.search(pattern, content)
    if not match:
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


def parse_es_es_phrases() -> dict[str, str]:
    """Extrae frases traducidas de esES.lua del addon."""
    if not ESES_LUA.exists():
        return {}

    content = ESES_LUA.read_text(encoding="utf-8")
    result = {}

    # Patrón: L["English"] = "Spanish"
    for m in re.finditer(r'L\["([^"]+)"\]\s*=\s*"([^"]*)"', content):
        en, es = m.group(1), m.group(2)
        if en and es and en != es:
            result[en] = es

    # Patrón: words = { ["Accept"] = _G.ACCEPT, ["Kill"] = "Matar" }
    words_match = re.search(r'L\.words\s*=\s*\{(.*?)\}', content, re.DOTALL)
    if words_match:
        for m in re.finditer(r'\["(\w+)"\]\s*=\s*"([^"]*)"', words_match.group(1)):
            en, es = m.group(1), m.group(2)
            if en and es and en != es:
                result[f"word:{en}"] = es

    return result


# ─────────────────────────────────────────────────────────
# QuestieDB parser (from V3, unchanged)
# ─────────────────────────────────────────────────────────

class QuestieDBSource:
    """Abstracción para leer QuestieDB desde carpeta extraída o ZIP."""

    def __init__(self, *, folder: Path | None = None, zip_path: Path | None = None, zip_root: str = "") -> None:
        self.folder = folder
        self.zip_path = zip_path
        self.zip_root = zip_root.strip("/")
        self._archive = None
        self._names = None

        if folder is not None:
            self.label = str(folder)
        else:
            self.label = f"{zip_path}::{self.zip_root or '/'}"
            assert zip_path is not None
            self._archive = zipfile.ZipFile(zip_path)
            self._names = self._archive.namelist()

    @property
    def is_zip(self) -> bool:
        return self.zip_path is not None

    def _zip_member(self, relative: str) -> str:
        relative = relative.replace("\\", "/").lstrip("/")
        if self.zip_root:
            return f"{self.zip_root}/{relative}"
        return relative

    def exists(self, relative: str) -> bool:
        relative = relative.replace("\\", "/").lstrip("/")
        if self.folder is not None:
            return (self.folder / relative).exists()
        assert self.zip_path is not None
        member = self._zip_member(relative)
        prefix = member.rstrip("/") + "/"
        assert self._names is not None
        return member in self._names or any(name.startswith(prefix) for name in self._names)

    def read_text(self, relative: str) -> str:
        relative = relative.replace("\\", "/").lstrip("/")
        if self.folder is not None:
            return (self.folder / relative).read_text(encoding="utf-8", errors="ignore")
        assert self.zip_path is not None and self._archive is not None
        return self._archive.read(self._zip_member(relative)).decode("utf-8", errors="ignore")

    def glob_html(self, relative_dir: str) -> list[str]:
        relative_dir = relative_dir.replace("\\", "/").strip("/")
        prefix = relative_dir + "/"
        if self.folder is not None:
            root = self.folder / relative_dir
            if not root.exists():
                return []
            return sorted(
                str(path.relative_to(self.folder)).replace("\\", "/")
                for path in root.glob("*.html")
                if path.is_file()
            )
        assert self.zip_path is not None and self._names is not None
        archive_prefix = self._zip_member(prefix)
        result = []
        for member in self._names:
            if not member.startswith(archive_prefix) or not member.lower().endswith(".html"):
                continue
            rest = member[len(archive_prefix):]
            if "/" in rest:
                continue
            relative = member
            if self.zip_root:
                relative = member[len(self.zip_root) + 1:]
            result.append(relative)
        return sorted(result)


def _directory_candidates() -> list[Path]:
    candidates = [
        BASE_DIR / "QuestieDB",
        BASE_DIR / "QuestieDB-main",
        BASE_DIR / "QuestieDB-v0.7.0",
    ]
    for root in [BASE_DIR, BASE_DIR / "QuestieDB"]:
        if not root.exists():
            continue
        for child in root.iterdir():
            if child.is_dir():
                candidates.append(child)
                for nested in child.iterdir():
                    if nested.is_dir():
                        candidates.append(nested)
    unique: list[Path] = []
    seen = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except Exception:
            resolved = candidate
        if resolved not in seen:
            seen.add(resolved)
            unique.append(candidate)
    return unique


def _score_directory(path: Path) -> int:
    checks = [
        "Database/Npc/Tbc/_data", "Database/Item/Tbc/_data",
        "Database/Object/Tbc/_data", "Database/Quest/Tbc/_data",
        "Database/l10n/Tbc/_data", "Database/Npc/Era/_data",
        "Database/l10n/Era/_data",
    ]
    if not path.exists() or not path.is_dir():
        return -1
    return sum(1 for relative in checks if (path / relative).exists())


def _find_zip_root(path: Path) -> Tuple[str, int]:
    checks = [
        "Database/Npc/Tbc/_data/", "Database/Item/Tbc/_data/",
        "Database/Object/Tbc/_data/", "Database/Quest/Tbc/_data/",
        "Database/l10n/Tbc/_data/", "Database/Npc/Era/_data/",
        "Database/l10n/Era/_data/",
    ]
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
    except Exception:
        return "", -1

    possible_roots = {""}
    for name in names:
        normalized = name.strip("/")
        if normalized.endswith("Database/Npc/Tbc/_data"):
            possible_roots.add(normalized[:-len("Database/Npc/Tbc/_data")].rstrip("/"))
        marker = "/Database/Npc/Tbc/_data/"
        if marker in normalized:
            possible_roots.add(normalized.split(marker, 1)[0])

    best_root = ""
    best_score = -1
    for root in possible_roots:
        prefix = f"{root}/" if root else ""
        score = sum(1 for check in checks if any(name.startswith(prefix + check) for name in names))
        if score > best_score:
            best_score = score
            best_root = root
    return best_root, best_score


def locate_source() -> QuestieDBSource | None:
    ranked: list[Tuple[int, QuestieDBSource]] = []
    for folder in _directory_candidates():
        score = _score_directory(folder)
        if score >= 0:
            ranked.append((score, QuestieDBSource(folder=folder)))
    for zip_path in sorted(BASE_DIR.glob("QuestieDB*.zip")):
        root, score = _find_zip_root(zip_path)
        if score >= 0:
            ranked.append((score, QuestieDBSource(zip_path=zip_path, zip_root=root)))

    if not ranked:
        return None

    ranked.sort(key=lambda pair: pair[0], reverse=True)
    print("\nFuentes QuestieDB detectadas:")
    for score, source in ranked:
        print(f"  {source.label} | estructura reconocida: {score}/7")

    selected = ranked[0][1]
    if ranked[0][0] < 7:
        print("\nERROR: encontré QuestieDB, pero su estructura no está completa.")
        return None

    print(f"\nUsando fuente QuestieDB:\n{selected.label}")
    return selected


def clean_html_value(value: str) -> str:
    value = unescape(value)
    value = TAG_RE.sub("", value)
    return value.strip()


def parse_html_records(html_text: str) -> Dict[str, Dict[int, str]]:
    result: Dict[str, Dict[int, str]] = {}
    for match in ENTRY_BLOCK_RE.finditer(html_text):
        entity_id = match.group(1)
        values = [clean_html_value(raw) for raw in PARAGRAPH_RE.findall(match.group(2))]
        if not values:
            continue
        try:
            active_indexes = [int(v.strip()) for v in values[0].split(",") if v.strip()]
        except Exception:
            continue
        field_values = values[1:]
        result[entity_id] = {idx: val for idx, val in zip(active_indexes, field_values)}
    return result


RECORD_CACHE: Dict[str, Dict[str, Dict[int, str]]] = {}


def load_records(source: QuestieDBSource, relative_dir: str) -> Dict[str, Dict[int, str]]:
    if relative_dir in RECORD_CACHE:
        return RECORD_CACHE[relative_dir]

    records: Dict[str, Dict[int, str]] = {}
    files = source.glob_html(relative_dir)
    print(f"    shards HTML: {len(files)}")

    for file_index, relative in enumerate(files, start=1):
        records.update(parse_html_records(source.read_text(relative)))
        if file_index % 100 == 0 or file_index == len(files):
            print(f"\r    archivos procesados: {file_index}/{len(files)} | registros: {len(records)}", end="", flush=True)

    if files:
        print()
    RECORD_CACHE[relative_dir] = records
    return records


def lua_unescape(value: str) -> str:
    replacements = {"\\\\": "\0BACKSLASH\0", "\\'": "'", '\\"': '"', "\\n": "\n", "\\r": "\r", "\\t": "\t"}
    for old, new in replacements.items():
        value = value.replace(old, new)
    return value.replace("\0BACKSLASH\0", "\\")


def first_lua_quoted_string(raw: str | None) -> str | None:
    if not raw:
        return None
    raw = raw.strip()
    if not raw.startswith("{"):
        return raw
    for start, char in enumerate(raw):
        if char not in ("'", '"'):
            continue
        quote = char
        chars = []
        pos = start + 1
        while pos < len(raw):
            current = raw[pos]
            if current == "\\" and pos + 1 < len(raw):
                chars.append(current)
                chars.append(raw[pos + 1])
                pos += 2
                continue
            if current == quote:
                return lua_unescape("".join(chars))
            chars.append(current)
            pos += 1
    return None


def localized_names(packed: str | None, english: str) -> dict[str, str]:
    """Retorna diccionario con TODOS los idiomas: {locale: name}."""
    result = {"en": english}
    if not packed:
        return result
    parts = packed.split("‡")
    if len(parts) < len(LOCALE_ORDER):
        parts += [""] * (len(LOCALE_ORDER) - len(parts))
    locale_data = dict(zip(LOCALE_ORDER, parts))
    for loc, name in locale_data.items():
        name = (name or "").strip()
        if name:
            result[loc] = name
    return result


def build_entity_section(source: QuestieDBSource, section: str) -> Dict[str, dict]:
    folder_name, l10n_field_index = ENTITY_CONFIG[section]
    merged: Dict[str, dict] = {}

    for expansion in PREFERRED_EXPANSIONS:
        print(f"\n  {section} / {expansion}: nombres ingleses")
        english_records = load_records(source, f"Database/{folder_name}/{expansion}/_data")

        print(f"  {section} / {expansion}: localizaciones")
        l10n_records = load_records(source, f"Database/l10n/{expansion}/_data")

        localized_count = 0
        for entity_id, fields in english_records.items():
            english = str(fields.get(1) or "").strip()
            if not english:
                continue
            localized_field = l10n_records.get(entity_id, {}).get(l10n_field_index)
            packed = first_lua_quoted_string(localized_field)
            all_names = localized_names(packed, english)
            if len(all_names) > 1:
                localized_count += 1
            entry = {
                "id": int(entity_id),
                "source": expansion.lower(),
                "en": english,
            }
            entry.update(all_names)
            merged[entity_id] = entry

        print(f"  {section} / {expansion}: {len(english_records)} EN | {localized_count} con traducciones")

    return merged


# ─────────────────────────────────────────────────────────
# V4: Merge NPCnames.lua into NPC section
# ─────────────────────────────────────────────────────────

def merge_npcnames_into_npcs(npcs: dict[str, dict], npcnames: dict[str, str], locale: str) -> int:
    """
    Fusiona NPCnames con NPCs de QuestieDB para un locale específico.
    """
    en_index: dict[str, list[str]] = {}
    for entity_id, data in npcs.items():
        en = str(data.get("en") or "").strip()
        if en:
            en_index.setdefault(en.casefold(), []).append(entity_id)

    updated = 0
    for en_name, loc_name in npcnames.items():
        key = en_name.casefold()
        if key in en_index:
            for entity_id in en_index[key]:
                current = str(npcs[entity_id].get(locale) or "").strip()
                if current.casefold() != loc_name.casefold():
                    npcs[entity_id][locale] = loc_name
                    npcs[entity_id][f"npcnames_{locale}"] = True
                    updated += 1
        else:
            new_id = f"npcnames_{len(npcs)}"
            entry = {
                "id": None,
                "source": "npcnames",
                "en": en_name,
                locale: loc_name,
                f"npcnames_{locale}": True,
            }
            npcs[new_id] = entry
            updated += 1

    return updated


def validate_result_counts(result: dict) -> bool:
    errors = []
    for section, minimum in MINIMUM_EXPECTED.items():
        actual = len(result.get(section, {}))
        if actual < minimum:
            errors.append((section, actual, minimum))
    if not errors:
        return True
    print("\n" + "=" * 50)
    print(" ERROR: LA BASE RESULTANTE ES DEMASIADO PEQUEÑA")
    print("=" * 50)
    for section, actual, minimum in errors:
        print(f"  {section:10}: {actual} | mínimo esperado: {minimum}")
    print("\nNo se sobrescribió database\\questiedb_es.json.")
    return False


def is_valid_named_entry(data: dict) -> bool:
    en = str(data.get("en") or "").strip()
    es = str(data.get("es") or "").strip()
    if not en or not es:
        return False
    return not NUMERIC_ZONE_RE.fullmatch(en)


def import_legacy_zone_spell_cache() -> Tuple[Dict[str, dict], Dict[str, dict]]:
    legacy = load_json(LEGACY_WOWHEAD_CACHE, {})
    zones: Dict[str, dict] = {}
    spells: Dict[str, dict] = {}
    if not isinstance(legacy, dict):
        return zones, spells
    for section_name, destination in [("zones", zones), ("spells", spells)]:
        raw_section = legacy.get(section_name, {})
        if not isinstance(raw_section, dict):
            continue
        for key, raw in raw_section.items():
            if not isinstance(raw, dict):
                continue
            data = {
                "id": raw.get("id"),
                "source": raw.get("source") or "legacy_wowhead_cache",
                "en": raw.get("en") or key,
                "es": raw.get("es") or raw.get("mx") or raw.get("en") or key,
                "mx": raw.get("mx") or raw.get("es") or raw.get("en") or key,
            }
            if is_valid_named_entry(data):
                destination[str(key)] = data
    return zones, spells


def initialize_auxiliary_files() -> None:
    legacy_zones, legacy_spells = import_legacy_zone_spell_cache()

    zones = load_json(ZONES_DB, {})
    if not isinstance(zones, dict):
        zones = {}
    zones.setdefault("zones", {})
    for key, data in legacy_zones.items():
        zones["zones"].setdefault(key, data)
    zones.setdefault("meta", {})
    zones["meta"].update({
        "description": "Zonas oficiales/manuales y migradas desde caché antiguo.",
        "legacy_imported": len(legacy_zones),
    })
    save_json(ZONES_DB, zones)

    spells = load_json(SPELLS_DB, {})
    if not isinstance(spells, dict):
        spells = {}
    spells.setdefault("spells", {})
    for key, data in legacy_spells.items():
        spells["spells"].setdefault(key, data)
    spells.setdefault("meta", {})
    spells["meta"].update({
        "description": "Habilidades oficiales/manuales y migradas desde caché antiguo.",
        "legacy_imported": len(legacy_spells),
    })
    save_json(SPELLS_DB, spells)

    overrides = load_json(MANUAL_OVERRIDES, {})
    if not isinstance(overrides, dict):
        overrides = {}
    for section in ["quests", "npcs", "items", "objects", "zones", "spells", "terms"]:
        overrides.setdefault(section, {})
    overrides.setdefault("_info", {
        "uso": 'Agrega correcciones manuales por nombre inglés. Ejemplo: "zones": {"Old Town": "Casco Antiguo"}.'
    })
    save_json(MANUAL_OVERRIDES, overrides)


def print_summary(result: dict, total_npcnames_updated: int) -> None:
    print("\nResumen:")
    for section in ["quests", "npcs", "items", "objects"]:
        entries = result.get(section, {})
        # Contar entradas con al menos una traducción (cualquier idioma)
        translated = sum(
            1 for d in entries.values()
            if isinstance(d, dict) and len(d) > 3  # más que id, source, en
        )
        print(f"  {section:10}: {len(entries):7} registros | {translated:7} con traducciones")
    print(f"\n  NPCnames aplicados (todos los idiomas): {total_npcnames_updated}")


def main() -> int:
    ensure_dirs()

    print("=" * 50)
    print(" RXP Translator V4 - Construir base de datos")
    print("=" * 50)

    # ── Paso 1: NPCnames.lua (se procesa en Paso 4 para todos los idiomas) ──
    print("\n── Paso 1: NPCnames.lua ──")
    if NPCNAMES_LUA.exists():
        print(f"  Archivo encontrado: {NPCNAMES_LUA}")
    else:
        print(f"  ADVERTENCIA: No encontré {NPCNAMES_LUA}")

    # ── Paso 2: Extraer frases de esES.lua ──
    print("\n── Paso 2: esES.lua (frases de interfaz) ──")
    addon_phrases = parse_es_es_phrases()
    print(f"  Frases extraídas: {len(addon_phrases)}")

    # ── Paso 3: QuestieDB ──
    print("\n── Paso 3: QuestieDB ──")
    source = locate_source()
    if source is None:
        print("\nNo encontré una fuente QuestieDB compatible.")
        print("Coloca junto a este script una de estas opciones:")
        print("  - carpeta QuestieDB extraída")
        print("  - archivo QuestieDB-v0.7.0.zip")
        return 1

    result = {
        "meta": {
            "generator": "build_database.py V4",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "questiedb_source": source.label,
            "format": "QuestieDB HTML shards + NPCnames.lua (multi-locale)",
            "expansions": PREFERRED_EXPANSIONS,
            "supported_locales": list(SUPPORTED_LOCALES.keys()),
            "addon_phrases": len(addon_phrases),
        }
    }

    for section in ["quests", "npcs", "items", "objects"]:
        print(f"\n{'=' * 50}")
        print(f" Procesando {section}")
        print("=" * 50)
        result[section] = build_entity_section(source, section)

    # ── Paso 4: Merge NPCnames into NPCs (todos los idiomas) ──
    print(f"\n── Paso 4: Fusionar NPCnames.lua con NPCs de QuestieDB ──")
    total_npcnames_updated = 0
    for locale_code in SUPPORTED_LOCALES:
        npcnames = parse_npcnames_locale(locale_code)
        if npcnames:
            updated = merge_npcnames_into_npcs(result["npcs"], npcnames, locale_code)
            print(f"  {locale_code}: {len(npcnames)} entradas | {updated} aplicadas")
            total_npcnames_updated += updated
    print(f"  Total NPCnames aplicados: {total_npcnames_updated}")

    if not validate_result_counts(result):
        return 1

    # ── Paso 5: Guardar ──
    save_json(OUTPUT_DB, result)
    initialize_auxiliary_files()
    print_summary(result, total_npcnames_updated)

    # Guardar addon phrases
    addon_phrases_json = DATABASE_DIR / "addon_phrases.json"
    addon_phrases_json.write_text(
        json.dumps({
            "meta": {
                "source": "RXPGuides/locale/esES.lua",
                "total_phrases": len(addon_phrases),
            },
            "phrases": addon_phrases,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\n{'=' * 50}")
    print(" Base construida correctamente")
    print("=" * 50)
    print(f"Archivo principal:   {OUTPUT_DB}")
    print(f"NPCnames (9 idiomas): {DATABASE_DIR / 'npcnames_*.json'}")
    print(f"Frases addon:        {addon_phrases_json}")
    print(f"Zones:               {ZONES_DB}")
    print(f"Spells:              {SPELLS_DB}")
    print(f"Overrides:           {MANUAL_OVERRIDES}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
