#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
translate_guides.py
RXP Translator V5 - Traduce guías RestedXP a cualquier idioma soportado.

Idiomas: esES, esMX, deDE, frFR, ptBR, ruRU, koKR, zhCN, zhTW

Uso:
    python translate_guides.py                  # Traduce a esES (default)
    python translate_guides.py deDE             # Traduce a alemán
    python translate_guides.py frFR             # Traduce a francés

Dependencia opcional:
    pip install deep-translator
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from typing import Dict

try:
    from deep_translator import GoogleTranslator, MyMemoryTranslator
except Exception:
    GoogleTranslator = None
    MyMemoryTranslator = None

from validate_output import compare_files
from locales_config import (
    SUPPORTED_LOCALES, DEFAULT_LOCALE,
    get_google_target, get_output_suffix, get_locale_config,
)

import sys
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"
DATABASE_DIR = BASE_DIR / "database"
CACHE_DIR = BASE_DIR / "cache"

QUESTIEDB_FILE = DATABASE_DIR / "questiedb_es.json"
ZONES_FILE = DATABASE_DIR / "zones_all.json"
SPELLS_FILE = DATABASE_DIR / "spells_es.json"
OVERRIDES_FILE = DATABASE_DIR / "manual_overrides.json"
ADDON_PHRASES_FILE = DATABASE_DIR / "addon_phrases.json"

# Multi-idioma: se configura desde línea de comandos
TARGET_LOCALE = DEFAULT_LOCALE
TARGET_WOW_VERSION = "forever"
OUTPUT_SUFFIX = "_esES"
USE_GOOGLE_TRANSLATOR = True
USE_MYMEMORY_FALLBACK = True

# ─────────────────────────────────────────────────────────
# Etiquetas RXP: clasificación
# ─────────────────────────────────────────────────────────

# Etiquetas que contienen una ENTIDAD (NPC, item, objeto).
# Su contenido se traduce con la base de datos, NO con Google.
ENTITY_TAG_SECTION = {
    "FRIENDLY": "entity",    # V5: busca en npcs + items
    "ENEMY": "npcs",
    "LOOT": "items",
    "PICK": "objects",
}

# Etiquetas de texto libre visible (sí se envían a Google/reglas).
FREE_TEXT_TAGS = {
    "BUY", "WARN", "IMPORTANT", "NOTE", "GREEN", "RED", "BLUE", "YELLOW",
    "XP_WARN", "XP_GREEN", "XP_RED", "XP_BONUS", "XP_PENALTY",
}

# Todos los tipos conocidos de etiquetas RXP.
RXP_TAG_TYPES = {
    "FRIENDLY", "ENEMY", "LOOT", "BUY", "PICK",
    "WARN", "IMPORTANT", "NOTE", "GREEN", "RED", "BLUE", "YELLOW",
    "XP_WARN", "XP_GREEN", "XP_RED", "XP_BONUS", "XP_PENALTY",
}

# ─────────────────────────────────────────────────────────
# Regex patterns
# ─────────────────────────────────────────────────────────

COLOR_START_RE = re.compile(r"\|c([0-9A-Fa-f]{8})")
BRACKET_RE = re.compile(r"\[([^\]\n]{2,120})\]")
TEXTURE_RE = re.compile(r"\|T[^|]*\|t")
LINK_RE = re.compile(r"\|H[^|]*\|h.*?\|h")
PLACEHOLDER_RE = re.compile(r"ZXQPH\d{6}QXZ")

# Condicional RXP: << ... (al final de la línea, después de >>)
CONDITIONAL_RE = re.compile(r"<<\s*(.+?)\s*$")

# Comandos con ID numérico (para buscar entidad por ID)
COMMAND_ID_PATTERNS = [
    ("quests", re.compile(r"^\s*\.(?:accept|turnin|complete|daily|weekly)\s+(\d+)\b", re.IGNORECASE)),
    ("items", re.compile(r"^\s*\.(?:collect|use|itemcount|destroy|buy|sell|equip)\s+(\d+)\b", re.IGNORECASE)),
    ("spells", re.compile(r"^\s*\.(?:cast|train)\s+(\d+)\b", re.IGNORECASE)),
]

# Color hex de zona (|cFFfa9602Nombre|r) — NO traducir el contenido
ZONE_COLOR_RE = re.compile(r"\|c[0-9A-Fa-f]{8}([^|]+)\|r")

# .goto ZoneName,x,y — NO traducir ZoneName
GOTO_RE = re.compile(r"(\.goto\s+)([^,]+)(,.*)")

# ─────────────────────────────────────────────────────────
# Zone/dungeon name translations for guide titles (#name)
# ─────────────────────────────────────────────────────────

ZONE_TRANSLATIONS = {
    # Kalimdor - Zones
    "Durotar": "Durotar",
    "Mulgore": "Mulgore",
    "Teldrassil": "Teldrassil",
    "Darkshore": "Costa Oscura",
    "Ashenvale": "Vallefresno",
    "Thousand Needles": "Las Mil Agujas",
    "Stonetalon Mountains": "Sierra Espolón",
    "Desolace": "Desolace",
    "Feralas": "Feralas",
    "Tanaris": "Tanaris",
    "Un'Goro Crater": "Cráter de Un'Goro",
    "Silithus": "Silithus",
    "Winterspring": "Cuna del Invierno",
    "Azshara": "Azshara",
    "Felwood": "Frondavil",
    "Moonglade": "Claro de la Luna",
    "Dustwallow Marsh": "Pantano de las Penas",
    "Dustwallow": "Pantano de las Penas",
    "Barrens": "Los Baldíos",
    "The Barrens": "Los Baldíos",
    "Northern Barrens": "Los Baldíos del Norte",
    "Southern Barrens": "Los Baldíos del Sur",
    "Orgrimmar": "Orgrimmar",
    "Thunder Bluff": "Cima del Trueno",
    "Darnassus": "Darnassus",
    "Ratchet": "Trinquete",

    # Eastern Kingdoms - Zones
    "Elwynn Forest": "Bosque de Elwynn",
    "Westfall": "Páramos de Poniente",
    "Redridge Mountains": "Montañas de Crestagrana",
    "Duskwood": "Bosque del Ocaso",
    "Stranglethorn Vale": "Vega de Tuercespina",
    "STV": "Tuercespina",
    "Swamp of Sorrows": "Pantano de las Penas",
    "Blasted Lands": "Las Tierras Devastadas",
    "Hillsbrad Foothills": "Laderas de Trabalomas",
    "Hillsbrad": "Trabalomas",
    "Alterac Mountains": "Montañas de Alterac",
    "Alterac": "Alterac",
    "Arathi Highlands": "Tierras Altas de Arathi",
    "Arathi": "Arathi",
    "The Hinterlands": "Tierras del Interior",
    "Western Plaguelands": "Tierras de la Peste del Oeste",
    "Eastern Plaguelands": "Tierras de la Peste del Este",
    "Tirisfal Glades": "Claros de Tirisfal",
    "Silverpine Forest": "Bosque de Argénteos",
    "Loch Modan": "Loch Modan",
    "Wetlands": "Los Humedales",
    "Dun Morogh": "Dun Morogh",
    "Badlands": "Tierras Inhóspitas",
    "Searing Gorge": "La Garganta de Fuego",
    "Burning Steppes": "Las Estepas Ardientes",
    "Blackrock Mountain": "Montaña Roca Negra",
    "Deadwind Pass": "Paso de la Muerte",
    "Stormwind": "Ventormenta",
    "Ironforge": "Forjaz",
    "Undercity": "Entrañas",
    "Silvermoon": "Lunargenta",
    "Shimmering Flats": "Los Baldíos Brillantes",
    "Shimmering": "Los Baldíos Brillantes",

    # Dungeons (Classic)
    "Ragefire Chasm": "Sima Ígnea",
    "Wailing Caverns": "Cuevas de los Lamentos",
    "Shadowfang Keep": "Castillo de Colmillo Oscuro",
    "Blackfathom Deeps": "Cavernas de Brazanegra",
    "Razorfen Kraul": "Horado Rajacieno",
    "Gnomeregan": "Gnomeregan",
    "Razorfen Downs": "Zahúrda Rajacieno",
    "Scarlet Monastery": "Monasterio Escarlata",
    "Uldaman": "Uldaman",
    "Zul'Farrak": "Zul'Farrak",
    "Maraudon": "Maraudon",
    "Sunken Temple": "Templo Sumergido",
    "Blackrock Depths": "Profundidades de Roca Negra",
    "Lower Blackrock Spire": "Aguja de Roca Negra Inferior",
    "Upper Blackrock Spire": "Aguja de Roca Negra Superior",
    "Scholomance": "Scholomance",
    "Stratholme": "Stratholme",
    "Dire Maul": "La Masacre",
    "Dire Maul (East)": "La Masacre (Este)",
    "Dire Maul (West)": "La Masacre (Oeste)",
    "Dire Maul (North)": "La Masacre (Norte)",

    # TBC Dungeons
    "Hellfire Ramparts": "Murallas de Fuego Infernal",
    "Blood Furnace": "El Horno de Sangre",
    "Underbog": "La Sotiénaga",
    "Slave Pens": "Recinto de los Esclavos",
    "Mana Tombs": "Tumbas de Maná",
    "Auchenai Crypts": "Criptas Auchenai",
    "Sethekk Halls": "Salas Sethekk",
    "Shadow Labyrinth": "Laberinto de las Sombras",
    "Old Hillsbrad": "Antiguo Trabalomas",
    "Black Morass": "La Ciénaga Negra",
    "Steamvault": "La Cámara de Vapor",
    "The Steamvault": "La Cámara de Vapor",
    "Escape from Durnholde": "Escape de Durnholde",
    "Opening the Dark Portal": "Apertura del Portal Oscuro",

    # TBC Zones
    "Hellfire Peninsula": "Península de Fuego Infernal",
    "Zangarmarsh": "Marisma de Zangar",
    "Terokkar Forest": "Bosque de Terokkar",
    "Nagrand": "Nagrand",
    "Blade's Edge Mountains": "Montañas Filospada",
    "Netherstorm": "Tormenta Abisal",
    "Shadowmoon Valley": "Valle Sombraluna",
    "Isle of Quel'Danas": "Isla de Quel'Danas",
    "Shattrath": "Shattrath",
    "Exodar": "El Exodar",

    # Common abbreviations
    "part 2": "parte 2",
    "part 3": "parte 3",
    "Alliance": "Alianza",
    "Horde": "Horda",
    "Dungeon Cleave": "Dungeon Cleave",
    "Leveling": "Subida de nivel",
}

# ─────────────────────────────────────────────────────────
# Reglas de traducción ampliadas (V5)
# ─────────────────────────────────────────────────────────

FALLBACK_RULES = [
    # Acciones del juego
    ("Buy as many", "Compra tantos como puedas"),
    ("that are available", "que estén disponibles"),
    ("Buy food/water if needed", "Compra comida y agua si es necesario"),
    ("Buy food if needed", "Compra comida si es necesario"),
    ("Talk to ", "Habla con "),
    ("Speak with ", "Habla con "),
    ("Accept ", "Acepta "),
    ("Turn in ", "Entrega "),
    ("Complete ", "Completa "),
    ("Kill ", "Mata "),
    ("Slay ", "Mata "),
    ("Loot ", "Despoja "),
    ("Collect ", "Consigue "),
    ("Buy ", "Compra "),
    ("Sell ", "Vende "),
    ("Use ", "Usa "),
    ("Equip ", "Equipa "),
    ("Click ", "Haz clic en "),
    ("Open ", "Abre "),
    ("Destroy ", "Destruye "),
    ("Train ", "Entrena "),
    ("Fly to ", "Vuela a "),
    ("Go to ", "Ve a "),
    ("Run to ", "Corre a "),
    ("Travel to ", "Viaja a "),
    ("Take the boat to ", "Toma el barco a "),
    ("Take the tram to ", "Toma el tranvía a "),
    ("Get the flight path", "Consigue la ruta de vuelo"),
    ("if possible", "si es posible"),
    ("if needed", "si es necesario"),
    ("Optional", "Opcional"),
    ("optional", "opcional"),
    ("Obtain the", "Obtén el"),
    ("Obtain", "Obtén"),
    ("Grind until", "Farmea hasta que"),
    ("Sell junk/resupply", "Vende basura/reabastécete"),
    ("Train skills", "Entrena habilidades"),
    ("Stable your pet", "Estabiliza a tu mascota"),
    ("Die and respawn at the graveyard", "Muere y reaparece en el cementerio"),
    ("Set your Hearthstone to", "Establece tu Piedra de hogar en"),
    ("Get the", "Consigue el"),
    ("from the Auction House", "de la Casa de Subastas"),
    ("Auction House", "Casa de Subastas"),
    ("Bind-on-Equip", "Se liga al equiparlo"),
    ("Bind on Equip", "Se liga al equiparlo"),
    ("Alternatively", "Alternativamente"),
    ("This is a", "Este es un"),
    ("drop in", "caída en"),
    ("drops in", "caídas en"),
    ("and", "y"),
    ("or", "o"),
    ("from", "de"),
    ("in exchange for", "a cambio de"),
]

# ─────────────────────────────────────────────────────────
# Utilidades
# ─────────────────────────────────────────────────────────


def ensure_dirs() -> None:
    INPUT_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
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


def normalize_name(value: str) -> str:
    value = value.strip().casefold()
    value = value.strip("[](){}.,:;")
    value = re.sub(r"\s+", " ", value)
    return value


IRREGULAR_SINGULARS = {
    "axes": "axe", "boxes": "box", "wolves": "wolf", "knives": "knife",
    "leaves": "leaf", "teeth": "tooth", "feet": "foot", "men": "man",
    "women": "woman", "children": "child", "mice": "mouse",
}


def singularize_word(word: str) -> str:
    if not word:
        return word
    match = re.match(r"^([^A-Za-zÀ-ÿ']*)([A-Za-zÀ-ÿ'-]+)([^A-Za-zÀ-ÿ']*)$", word)
    if not match:
        return word
    prefix, core, suffix = match.groups()
    lower = core.casefold()
    if lower in IRREGULAR_SINGULARS:
        singular = IRREGULAR_SINGULARS[lower]
    elif lower.endswith("ies") and len(core) > 4:
        singular = core[:-3] + "y"
    elif lower.endswith(("sses", "shes", "ches", "xes", "zes")) and len(core) > 4:
        singular = core[:-2]
    elif lower.endswith("s") and not lower.endswith(("ss", "us", "is")) and len(core) > 3:
        singular = core[:-1]
    else:
        singular = core
    if core[:1].isupper():
        singular = singular[:1].upper() + singular[1:]
    return prefix + singular + suffix


def entity_name_variants(value: str) -> list[str]:
    value = str(value or "").strip()
    value = value.strip("[](){} \t\r\n.,:;")
    if not value:
        return []
    variants = [value]
    without_article = re.sub(r"^(?:the|a|an)\s+", "", value, flags=re.IGNORECASE).strip()
    if without_article and without_article != value:
        variants.append(without_article)
    base_values = list(variants)
    for base in base_values:
        words = base.split()
        if not words:
            continue
        last = words[:-1] + [singularize_word(words[-1])]
        variants.append(" ".join(last))
        all_singular = [singularize_word(w) for w in words]
        variants.append(" ".join(all_singular))
        for idx, word in enumerate(words):
            singular = singularize_word(word)
            if singular != word:
                partial = list(words)
                partial[idx] = singular
                variants.append(" ".join(partial))
    cleaned = []
    seen = set()
    for variant in variants:
        variant = variant.strip("[](){} \t\r\n.,:;")
        key = normalize_name(variant)
        if variant and key and key not in seen:
            seen.add(key)
            cleaned.append(variant)
    return cleaned


def select_translation(data: dict) -> str:
    """Selecciona la traducción según el locale destino."""
    locale = TARGET_LOCALE
    # Intentar el locale específico, luego fallback a variantes
    result = str(data.get(locale) or "").strip()
    if not result:
        # Fallback: esES <-> esMX, luego genérico
        if locale in ("esES", "esMX"):
            result = str(data.get("esES") or data.get("esMX") or "").strip()
        elif locale == "deDE":
            result = str(data.get("deDE") or "").strip()
        elif locale == "frFR":
            result = str(data.get("frFR") or "").strip()
        elif locale == "ptBR":
            result = str(data.get("ptBR") or "").strip()
        elif locale == "ruRU":
            result = str(data.get("ruRU") or "").strip()
        elif locale == "koKR":
            result = str(data.get("koKR") or "").strip()
        elif locale == "zhCN":
            result = str(data.get("zhCN") or "").strip()
        elif locale == "zhTW":
            result = str(data.get("zhTW") or "").strip()
    if not result:
        result = str(data.get("en") or "").strip()
    return result


class PlaceholderStore:
    def __init__(self) -> None:
        self.values: Dict[str, str] = {}
        self.counter = 0

    def add(self, value: str) -> str:
        token = f"ZXQPH{self.counter:06d}QXZ"
        self.values[token] = value
        self.counter += 1
        return token

    def restore(self, text: str) -> str:
        for token, value in self.values.items():
            text = text.replace(token, value)
        return text


# ─────────────────────────────────────────────────────────
# LocalDatabase — V5 con prioridad NPCnames
# ─────────────────────────────────────────────────────────


class LocalDatabase:
    def __init__(self, wow_version: str = "forever", locale: str = "esES") -> None:
        self.locale = locale
        db_file = DATABASE_DIR / f"questiedb_{wow_version}.json"
        raw = load_json(db_file, {})
        self.sections: Dict[str, Dict[str, dict]] = {}

        for section in ["quests", "npcs", "items", "objects"]:
            value = raw.get(section, {})
            self.sections[section] = value if isinstance(value, dict) else {}

        zones_raw = load_json(ZONES_FILE, {})
        spells_raw = load_json(SPELLS_FILE, {})
        if "expansions" in zones_raw:
            all_zones = zones_raw["expansions"].get("all", {}).copy()
            exp_zones = zones_raw["expansions"].get(wow_version, {})
            all_zones.update(exp_zones)
            self.sections["zones"] = all_zones
        else:
            self.sections["zones"] = zones_raw.get("zones", {}) if isinstance(zones_raw, dict) else {}
        self.sections["spells"] = spells_raw.get("spells", {}) if isinstance(spells_raw, dict) else {}

        overrides = load_json(OVERRIDES_FILE, {})
        self.overrides = overrides if isinstance(overrides, dict) else {}

        # Cargar frases del addon
        addon_raw = load_json(ADDON_PHRASES_FILE, {})
        self.addon_phrases = addon_raw.get("phrases", {}) if isinstance(addon_raw, dict) else {}

        # Índice por nombre inglés
        self.by_name: Dict[str, Dict[str, list[dict]]] = {}

        for section, entries in self.sections.items():
            index: Dict[str, list[dict]] = {}
            for key, data in entries.items():
                if not isinstance(data, dict):
                    continue
                en = str(data.get("enUS") or data.get("en") or key).strip()
                if en:
                    index.setdefault(normalize_name(en), []).append(data)
            # Manual overrides tienen prioridad
            manual_section = self.overrides.get(section, {})
            if isinstance(manual_section, dict):
                for en, translated in manual_section.items():
                    if isinstance(translated, str):
                        data = {"id": None, "source": "manual_overrides", "en": en, "es": translated, "mx": translated}
                    elif isinstance(translated, dict):
                        data = dict(translated)
                        data.setdefault("en", en)
                    else:
                        continue
                    index.setdefault(normalize_name(en), []).insert(0, data)
            self.by_name[section] = index

        self.terms = {}
        manual_terms = self.overrides.get("terms", {})
        if isinstance(manual_terms, dict):
            self.terms = {str(k): str(v) for k, v in manual_terms.items()}

        self.unresolved: list[dict] = []
        self.stats = {
            "official_translated": 0,
            "official_same_name": 0,
            "resolved_exact": 0,
            "resolved_variant": 0,
            "unresolved": 0,
            "ambiguous": 0,
            "npcnames_hit": 0,
        }

    def by_id(self, section: str, entity_id: str | int) -> dict | None:
        return self.sections.get(section, {}).get(str(entity_id))

    def _unique_official_match(self, candidates: list[dict]) -> dict | None:
        if not candidates:
            return None
        groups = {}
        for data in candidates:
            key = (
                str(data.get("enUS") or data.get("en") or "").strip().casefold(),
                str(data.get(self.locale) or data.get("es") or "").strip().casefold(),
            )
            groups.setdefault(key, data)
        if len(groups) == 1:
            return next(iter(groups.values()))
        return None

    def by_english_name(self, section: str, name: str) -> tuple[dict | None, str]:
        index = self.by_name.get(section, {})
        variants = entity_name_variants(name)
        if not variants:
            return None, "missing"
        exact_key = normalize_name(variants[0])
        exact = self._unique_official_match(index.get(exact_key, []))
        if exact:
            return exact, "exact"
        matches = []
        for variant in variants[1:]:
            data = self._unique_official_match(index.get(normalize_name(variant), []))
            if data:
                matches.append(data)
        unique = self._unique_official_match(matches)
        if unique:
            return unique, "variant"
        if matches:
            return None, "ambiguous"
        return None, "missing"

    def get_zone_patterns(self) -> list[tuple[re.Pattern, str]]:
        if hasattr(self, "_zone_patterns"):
            return self._zone_patterns
        merged = dict(self.sections.get("zones", {}))
        for en, es in ZONE_TRANSLATIONS.items():
            if en not in merged:
                merged[en] = es
        sorted_zones = sorted(merged.items(), key=lambda p: len(p[0]), reverse=True)
        patterns = []
        for en, es in sorted_zones:
            if en != es:
                try:
                    pattern = re.compile(re.escape(en), re.IGNORECASE)
                    patterns.append((pattern, es))
                except re.error:
                    pass
        self._zone_patterns = patterns
        return patterns
        
    def translate_entity(self, name: str, *, file: str, line: int, context: str) -> str:
        """
        V5: Busca en npcs + items (FRIENDLY puede ser cualquiera de los dos).
        Prioridad: manual_overrides > NPCnames > QuestieDB.
        """
        # Buscar en NPCs primero
        data, resolution = self.by_english_name("npcs", name)
        if data:
            translated = select_translation(data) or name
            self.stats[f"resolved_{resolution}"] += 1
            if data.get("source") == "npcnames" or data.get("es_source") == "npcnames":
                self.stats["npcnames_hit"] += 1
            if normalize_name(translated) == normalize_name(name):
                self.stats["official_same_name"] += 1
            else:
                self.stats["official_translated"] += 1
            return translated

        # Buscar en items
        data, resolution = self.by_english_name("items", name)
        if data:
            translated = select_translation(data) or name
            self.stats[f"resolved_{resolution}"] += 1
            if normalize_name(translated) == normalize_name(name):
                self.stats["official_same_name"] += 1
            else:
                self.stats["official_translated"] += 1
            return translated

        self.stats["unresolved"] += 1
        self.unresolved.append({
            "type": "entity",
            "name": name,
            "file": file,
            "line": line,
            "context": context,
            "reason": "missing",
            "variants_checked": entity_name_variants(name),
        })
        return name

    def translate_name(self, section: str, name: str, *, file: str, line: int, context: str) -> str:
        """Traduce un nombre de entidad de una sección específica."""
        data, resolution = self.by_english_name(section, name)
        if data:
            translated = select_translation(data) or name
            self.stats[f"resolved_{resolution}"] += 1
            if data.get("source") == "npcnames" or data.get("es_source") == "npcnames":
                self.stats["npcnames_hit"] += 1
            if normalize_name(translated) == normalize_name(name):
                self.stats["official_same_name"] += 1
            else:
                self.stats["official_translated"] += 1
            return translated

        self.stats["ambiguous" if resolution == "ambiguous" else "unresolved"] += 1
        self.unresolved.append({
            "type": section,
            "name": name,
            "file": file,
            "line": line,
            "context": context,
            "reason": resolution,
            "variants_checked": entity_name_variants(name),
        })
        return name

    def localized_count(self, section: str) -> tuple[int, int]:
        total = 0
        translated = 0
        for data in self.sections.get(section, {}).values():
            if not isinstance(data, dict):
                continue
            en = str(data.get("en") or "").strip()
            loc = select_translation(data)
            if not en:
                continue
            total += 1
            if loc and normalize_name(loc) != normalize_name(en):
                translated += 1
        return total, translated

    def print_database_summary(self) -> None:
        locale_name = get_locale_config(TARGET_LOCALE)["name"]
        print(f"\nBase local V5 cargada (idioma: {locale_name}):")
        for section in ["quests", "npcs", "items", "objects", "zones", "spells"]:
            total, localized = self.localized_count(section)
            print(f"  {section:10}: {total:7} registros | {localized:7} con nombre traducido")
        print(f"  Frases addon: {len(self.addon_phrases)}")


# ─────────────────────────────────────────────────────────
# DescriptionTranslator — texto libre
# ─────────────────────────────────────────────────────────


class DescriptionTranslator:
    def __init__(self, locale: str = DEFAULT_LOCALE) -> None:
        self.locale = locale
        self.google_target = get_google_target(locale)

        # Caché específico por locale
        self.cache_file = CACHE_DIR / f"descriptions_{locale}.json"
        self.cache = load_json(self.cache_file, {})
        if not isinstance(self.cache, dict):
            self.cache = {}

        self.google = None
        self.mymemory = None

        if USE_GOOGLE_TRANSLATOR and GoogleTranslator is not None:
            try:
                self.google = GoogleTranslator(source="en", target=self.google_target)
            except Exception:
                self.google = None

        if USE_MYMEMORY_FALLBACK and MyMemoryTranslator is not None:
            try:
                mymemory_target = f"{self.locale[:2]}-{self.locale[2:]}"
                self.mymemory = MyMemoryTranslator(source="en-US", target=mymemory_target)
            except Exception:
                self.mymemory = None

        self.stats = {"cache": 0, "google": 0, "mymemory": 0, "rules": 0, "unchanged": 0}

    def save(self) -> None:
        save_json(self.cache_file, self.cache)

    def fallback(self, text: str) -> str:
        result = text
        for old, new in FALLBACK_RULES:
            old_clean = old.strip()
            new_clean = new.strip()
            if not old_clean:
                continue
            try:
                pattern = re.compile(
                    rf"(?<![A-Za-zÀ-ÿ]){re.escape(old_clean)}(?![A-Za-zÀ-ÿ])",
                    re.IGNORECASE,
                )
                result = pattern.sub(new_clean, result)
            except re.error:
                pass
        return result

    def translate(self, text: str) -> str:
        key = text.strip()
        if not key:
            return text
        if key in self.cache:
            self.stats["cache"] += 1
            return self.cache[key]

        translated = None
        provider = "unchanged"

        if self.google is not None:
            try:
                translated = self.google.translate(text)
                if translated:
                    provider = "google"
            except Exception:
                translated = None

        if not translated and self.mymemory is not None:
            try:
                time.sleep(0.15)
                translated = self.mymemory.translate(text)
                if translated:
                    provider = "mymemory"
            except Exception:
                translated = None

        if not translated:
            translated = self.fallback(text)
            provider = "rules" if translated != text else "unchanged"

        self.stats[provider] = self.stats.get(provider, 0) + 1
        self.cache[key] = translated
        self.save()
        return translated


# ─────────────────────────────────────────────────────────
# GuideTranslator — V5 con todas las correcciones
# ─────────────────────────────────────────────────────────


class GuideTranslator:
    """
    Motor V5. Traduce texto visible respetando:
    - Etiquetas RXP (|cRXP_...|r) con pila de anidamiento
    - Texturas |T...|t y enlaces |H...|h (literal)
    - Colores hex |cAARRGGBB|r (literal, NO traducir contenido de zona)
    - Condiciones << (NUNCA traducir)
    - .goto (NUNCA traducir nombre de zona)
    - Entidades por ID de comando (.accept 1234 → nombre traducido)
    - Etiquetas [Item Name] → nombre traducido
    """

    def __init__(self, database: LocalDatabase, descriptions: DescriptionTranslator) -> None:
        self.db = database
        self.descriptions = descriptions
        self.term_replacements = self._build_term_replacements()
        self.global_replacements = self._build_global_replacements()

    def translate_zone_names(self, text: str) -> str:
        """Replaces English zone/dungeon names with Spanish equivalents."""
        result = text
        for pattern, translated in self.db.get_zone_patterns():
            safe_translated = translated.replace("\\", "\\\\")
            result = pattern.sub(safe_translated, result)
        return result

    def _build_term_replacements(self) -> list[tuple[re.Pattern, str]]:
        result = []
        for english, translated in sorted(self.db.terms.items(), key=lambda p: len(p[0]), reverse=True):
            if english and translated:
                try:
                    result.append((re.compile(re.escape(english), re.IGNORECASE), translated))
                except re.error:
                    pass
        return result

    def _build_global_replacements(self) -> list[tuple[re.Pattern, str]]:
        """Construye patrones para zonas y spells que aparecen en texto libre."""
        result = []
        for section in ["zones", "spells"]:
            candidates = []
            for _, data_list in self.db.by_name.get(section, {}).items():
                # by_name values are lists; iterate
                for data in (data_list if isinstance(data_list, list) else [data_list]):
                    if not isinstance(data, dict):
                        continue
                    english = str(data.get("en") or "").strip()
                    translated = select_translation(data)
                    if not english or not translated or english == translated:
                        continue
                    if section == "spells" and len(english) < 4:
                        continue
                    candidates.append((english, translated))
                    break  # solo el primero

            candidates.sort(key=lambda p: len(p[0]), reverse=True)
            for english, translated in candidates:
                try:
                    pattern = re.compile(
                        rf"(?<![\w']){re.escape(english)}(?![\w'])",
                        re.IGNORECASE,
                    )
                    result.append((pattern, translated))
                except re.error:
                    pass
        return result

    def _rxp_start_at(self, text: str, pos: int) -> tuple[str, str, int] | None:
        if not text.startswith("|cRXP_", pos):
            return None
        for tag_type in sorted(RXP_TAG_TYPES, key=len, reverse=True):
            prefix = f"|cRXP_{tag_type}_"
            if text.startswith(prefix, pos):
                return tag_type, prefix, pos + len(prefix)
        type_start = pos + len("|cRXP_")
        underscore = text.find("_", type_start)
        if underscore == -1:
            return None
        tag_type = text[type_start:underscore]
        if not tag_type:
            return None
        prefix = text[pos: underscore + 1]
        return tag_type, prefix, underscore + 1

    def _tag_start_at(self, text: str, pos: int) -> tuple[str, str, str | None, int] | None:
        rxp = self._rxp_start_at(text, pos)
        if rxp:
            tag_type, prefix, content_start = rxp
            return "rxp", prefix, tag_type, content_start
        color = COLOR_START_RE.match(text, pos)
        if color:
            prefix = color.group(0)
            return "color", prefix, None, color.end()
        return None

    def _find_matching_reset(self, text: str, content_start: int) -> int | None:
        depth = 1
        pos = content_start
        while pos < len(text):
            texture = TEXTURE_RE.match(text, pos)
            if texture:
                pos = texture.end()
                continue
            link = LINK_RE.match(text, pos)
            if link:
                pos = link.end()
                continue
            nested = self._tag_start_at(text, pos)
            if nested:
                depth += 1
                pos = nested[3]
                continue
            if text.startswith("|r", pos):
                depth -= 1
                if depth == 0:
                    return pos
                pos += 2
                continue
            pos += 1
        return None

    def _replace_known_name(self, text: str, section: str, english: str, store: PlaceholderStore, *, file: str, line_no: int, context: str) -> str:
        if not english:
            return text
        translated = self.db.translate_name(section, english, file=file, line=line_no, context=context)
        try:
            pattern = re.compile(re.escape(english), re.IGNORECASE)
            return pattern.sub(lambda _: store.add(translated), text)
        except re.error:
            return text

    def _inject_ids_from_command(self, command_prefix: str, visible_text: str, store: PlaceholderStore, *, file: str, line_no: int) -> str:
        result = visible_text
        for section, pattern in COMMAND_ID_PATTERNS:
            match = pattern.match(command_prefix)
            if not match:
                continue
            entity_id = match.group(1)
            data = self.db.by_id(section, entity_id)
            if not data:
                continue
            english = str(data.get("en") or "").strip()
            if english:
                result = self._replace_known_name(result, section, english, store, file=file, line_no=line_no, context=f"command_id:{entity_id}")
        return result

    def _replace_bracket_items(self, text: str, store: PlaceholderStore, *, file: str, line_no: int) -> str:
        def repl(match: re.Match) -> str:
            original = match.group(1)
            translated = self.db.translate_name("items", original, file=file, line=line_no, context="bracket_item")
            return store.add(f"[{translated}]")
        return BRACKET_RE.sub(repl, text)

    def _replace_terms(self, text: str, store: PlaceholderStore) -> str:
        result = text
        for pattern, translated in self.term_replacements:
            result = pattern.sub(lambda _: store.add(translated), result)
        return result

    def _replace_global_zones_spells(self, text: str, store: PlaceholderStore) -> str:
        result = text
        for pattern, translated in self.global_replacements:
            safe = translated.replace("\\", "\\\\")
            result = pattern.sub(lambda _: store.add(safe), result)
        return result

    def _translate_plain_preserving_spaces(self, text: str) -> str:
        if not text:
            return text
        match = re.match(r"^(\s*)(.*?)(\s*)$", text, flags=re.DOTALL)
        if not match:
            return text
        leading, core, trailing = match.groups()
        if not core or not re.search(r"[A-Za-z]", core):
            return text
        # Traducir texto libre con Google/reglas
        translated = self.descriptions.translate(core)
        # V5: Reemplazar nombres de zona que Google no conoce
        translated = self.translate_zone_names(translated)
        return leading + translated + trailing

    def _translate_segments_without_sending_tokens(self, text: str, store: PlaceholderStore) -> str:
        if not store.values:
            return self._translate_plain_preserving_spaces(text)
        pieces = re.split(f"({PLACEHOLDER_RE.pattern})", text)
        output = []
        for piece in pieces:
            if piece in store.values:
                output.append(store.values[piece])
            else:
                output.append(self._translate_plain_preserving_spaces(piece))
        return "".join(output)

    def _translate_plain_chunk(self, text: str, *, command_prefix: str, file: str, line_no: int) -> str:
        if not text:
            return text
        store = PlaceholderStore()
        protected = self._replace_bracket_items(text, store, file=file, line_no=line_no)
        protected = self._inject_ids_from_command(command_prefix, protected, store, file=file, line_no=line_no)
        protected = self._replace_terms(protected, store)
        protected = self._replace_global_zones_spells(protected, store)
        return self._translate_segments_without_sending_tokens(protected, store)

    def _translate_markup_aware(self, text: str, *, command_prefix: str, file: str, line_no: int) -> str:
        """Traduce texto visible preservando toda la sintaxis WoW/RXP."""
        output: list[str] = []
        plain_buffer: list[str] = []

        def flush_plain() -> None:
            if not plain_buffer:
                return
            chunk = "".join(plain_buffer)
            plain_buffer.clear()
            output.append(
                self._translate_plain_chunk(chunk, command_prefix=command_prefix, file=file, line_no=line_no)
            )

        pos = 0
        while pos < len(text):
            # Texturas: literal
            texture = TEXTURE_RE.match(text, pos)
            if texture:
                flush_plain()
                output.append(texture.group(0))
                pos = texture.end()
                continue

            # Enlaces: literal
            link = LINK_RE.match(text, pos)
            if link:
                flush_plain()
                output.append(link.group(0))
                pos = link.end()
                continue

            # Etiquetas RXP o colores
            tag = self._tag_start_at(text, pos)
            if tag:
                flush_plain()
                kind, prefix, tag_type, content_start = tag
                reset_pos = self._find_matching_reset(text, content_start)

                if reset_pos is None:
                    output.append(text[pos:])
                    pos = len(text)
                    break

                inner = text[content_start:reset_pos]

                if kind == "rxp" and tag_type in ENTITY_TAG_SECTION:
                    # V5: FRIENDLY busca en npcs + items
                    if tag_type == "FRIENDLY":
                        translated_inner = self.db.translate_entity(
                            inner, file=file, line=line_no, context=f"rxp_tag:{tag_type}"
                        )
                    else:
                        section = ENTITY_TAG_SECTION[tag_type]
                        translated_inner = self.db.translate_name(
                            section, inner, file=file, line=line_no, context=f"rxp_tag:{tag_type}"
                        )
                elif kind == "color":
                    # V5: NO traducir contenido de colores hex (pueden ser zonas)
                    translated_inner = inner
                else:
                    translated_inner = self._translate_markup_aware(
                        inner, command_prefix="", file=file, line_no=line_no
                    )

                # Preserve exact |r count from original inner text
                orig_r_count = inner.count("|r")
                translated_r_count = translated_inner.count("|r")
                if translated_r_count > orig_r_count:
                    # Remove excess trailing |r sequences
                    excess = translated_r_count - orig_r_count
                    for _ in range(excess):
                        if translated_inner.endswith("|r"):
                            translated_inner = translated_inner[:-2]
                elif translated_r_count < orig_r_count:
                    # Add missing |r sequences at the end
                    missing = orig_r_count - translated_r_count
                    translated_inner = translated_inner + "|r" * missing

                output.append(prefix + translated_inner + "|r")
                pos = reset_pos + 2
                continue

            plain_buffer.append(text[pos])
            pos += 1

        flush_plain()
        return "".join(output)

    def translate_visible_text(self, text: str, *, command_prefix: str, file: str, line_no: int) -> str:
        if not text.strip():
            return text
        return self._translate_markup_aware(text, command_prefix=command_prefix, file=file, line_no=line_no)

    def _split_conditional(self, text: str) -> tuple[str, str]:
        """
        V5: Separa un condicional << del texto visible.
        Retorna (texto_visible, condicional).
        Maneja múltiples condicionales: << !Druid !Warlock !Shaman
        Y condicionales compuestos: << Warlock/Shaman
        """
        match = CONDITIONAL_RE.search(text)
        if match:
            return text[:match.start()], match.group(0)
        return text, ""

    def _preserve_reset_count(self, original: str, translated: str) -> str:
        """Ensure the |r count in translated matches original.
        
        Only counts standalone |r that are NOT inside |cRRGGBBAA| tags.
        |r inside color tags (like |cRXP_FRIENDLY|) should be preserved as-is.
        """
        # Count standalone |r (not preceded by |c...| pattern)
        # A standalone |r is one that's not part of a color tag sequence
        def count_standalone_reset(s: str) -> int:
            count = 0
            i = 0
            while i < len(s):
                if s[i:i+2] == '|r':
                    # Check if this |r is preceded by a color tag opening
                    # Color tags look like |cRRGGBBAA or |cRXP_FRIENDLY
                    # A standalone |r should not be inside such a tag
                    count += 1
                    i += 2
                else:
                    i += 1
            return count
        
        orig_count = count_standalone_reset(original)
        trans_count = count_standalone_reset(translated)
        
        if orig_count == trans_count:
            return translated
        
        # If translation has more |r, remove excess from the end
        if trans_count > orig_count:
            excess = trans_count - orig_count
            for _ in range(excess):
                idx = translated.rfind('|r')
                if idx >= 0:
                    translated = translated[:idx] + translated[idx+2:]
        
        # If translation has fewer |r, add missing ones at the end
        elif trans_count < orig_count:
            missing = orig_count - trans_count
            translated = translated + '|r' * missing
        
        return translated

    def translate_line(self, line: str, *, file: str, line_no: int) -> str:
        """
        V5: Traduce una línea de guía.

        Reglas críticas:
        - .goto: NUNCA traducir nombre de zona
        - << condicional: NUNCA traducir (en ninguna posición)
        - >> visible: traducir texto después de >>
        - + / --: traducir texto visible
        - |cRXP_: traducir texto visible
        """
        # ── .goto: no tocar zona/coordenadas, pero traducir instrucción después de >> ──
        stripped = line.lstrip()
        if stripped.lower().startswith(".goto "):
            if ">>" in line:
                # .goto Undercity,65.53,43.62,15 >>Take the lift down
                prefix, visible = line.split(">>", 1)
                visible_text, conditional = self._split_conditional(visible)
                translated = self.translate_visible_text(
                    visible_text, command_prefix="", file=file, line_no=line_no
                )
                return prefix + ">>" + translated + conditional
            return line  # Sin >>, literal sin cambios
        
        # ── .zoneskip / .subzoneskip: NUNCA traducir nombre de zona ──
        for skip_cmd in (".zoneskip ", ".subzoneskip "):
            if stripped.lower().startswith(skip_cmd):
                if ">>" in line:
                    prefix, visible = line.split(">>", 1)
                    visible_text, conditional = self._split_conditional(visible)
                    translated = self.translate_visible_text(
                        visible_text, command_prefix="", file=file, line_no=line_no
                    )
                    return prefix + ">>" + translated + conditional
                return line  # Sin >>, literal sin cambios

        # ── .mob, .target, .unitscan: traducir nombre de NPC ──
        for cmd in (".mob ", ".target ", ".unitscan "):
            if stripped.lower().startswith(cmd):
                prefix = line[: len(line) - len(stripped)]
                npc_name = stripped[len(cmd):].strip()
                if npc_name:
                    # Handle + prefix (elite/boss indicator)
                    plus_prefix = ""
                    if npc_name.startswith("+"):
                        plus_prefix = "+"
                        npc_name = npc_name[1:].strip()
                    translated_npc = self.db.translate_name(
                        "npcs", npc_name, file=file, line=line_no, context=cmd.strip()
                    )
                    return prefix + cmd + plus_prefix + translated_npc
                return line

        # ── #name y #next: traducir nombres de zona/dungeon ──
        if stripped.startswith("#name ") or stripped.startswith("#next "):
            directive = stripped.split()[0]  # "#name" o "#next"
            content = stripped[len(directive) + 1:]
            content, conditional = self._split_conditional(content)
            translated = self.translate_zone_names(content)
            prefix = line[: len(line) - len(stripped)]
            return prefix + directive + " " + translated + conditional

        # ── Líneas con >> (comando >> texto visible) ──
        if ">>" in line:
            prefix, visible = line.split(">>", 1)
            visible_text, conditional = self._split_conditional(visible)
            translated = self.translate_visible_text(
                visible_text, command_prefix=prefix, file=file, line_no=line_no
            )
            translated = self._preserve_reset_count(visible_text, translated)
            return prefix + ">>" + translated + conditional

        # ── Líneas con + (texto visible) ──
        indentation = line[: len(line) - len(stripped)]
        if stripped.startswith("+"):
            content = stripped[1:]
            visible_text, conditional = self._split_conditional(content)
            translated = self.translate_visible_text(
                visible_text, command_prefix="", file=file, line_no=line_no
            )
            translated = self._preserve_reset_count(visible_text, translated)
            return indentation + "+" + translated + conditional

        # ── Líneas con -- (comentario visible) ──
        if stripped.startswith("--"):
            content = stripped[2:]
            visible_text, conditional = self._split_conditional(content)
            translated = self.translate_visible_text(
                visible_text, command_prefix="", file=file, line_no=line_no
            )
            translated = self._preserve_reset_count(visible_text, translated)
            return indentation + "--" + translated + conditional

        # ── Líneas con |cRXP_ (etiquetas sueltas, sin >> ni +) ──
        if "|cRXP_" in line:
            visible_text, conditional = self._split_conditional(line)
            if conditional:
                translated = self.translate_visible_text(
                    visible_text, command_prefix="", file=file, line_no=line_no
                )
                translated = self._preserve_reset_count(visible_text, translated)
                return translated + conditional
            return self.translate_visible_text(line, command_prefix="", file=file, line_no=line_no)

        # ── Sintaxis interna: no tocar ──
        return line


# ─────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────


def deduplicate_unresolved(records: list[dict]) -> list[dict]:
    seen = set()
    result = []
    for item in records:
        key = (item.get("type"), item.get("name"), item.get("file"), item.get("line"), item.get("context"))
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def output_path_for(relative: Path) -> Path:
    """Retorna la ruta de salida con el MISMO nombre que el original."""
    return OUTPUT_DIR / relative


def main() -> int:
    global TARGET_LOCALE, OUTPUT_SUFFIX

    ensure_dirs()

    # ── Configurar idioma desde línea de comandos ──
    locale = DEFAULT_LOCALE
    if len(sys.argv) > 1 and sys.argv[1] in SUPPORTED_LOCALES:
        locale = sys.argv[1]

    TARGET_LOCALE = locale
    OUTPUT_SUFFIX = get_output_suffix(locale)
    locale_name = get_locale_config(locale)["name"]

    print("=" * 55)
    print(f" RXP Translator V5 - Traducir a {locale_name} ({locale})")
    print("=" * 55)

    if not QUESTIEDB_FILE.exists():
        print(f"\nERROR: primero ejecuta:\npython build_database.py")
        return 1

    lua_files = sorted(INPUT_DIR.rglob("*.lua"))
    if not lua_files:
        print(f"\nERROR: no encontré archivos .lua en:\n{INPUT_DIR}")
        return 1

    database = LocalDatabase(locale=locale)
    database.print_database_summary()
    descriptions = DescriptionTranslator(locale=locale)
    translator = GuideTranslator(database, descriptions)

    validation_reports = []
    overall_ok = True

    for file_index, source in enumerate(lua_files, start=1):
        relative = source.relative_to(INPUT_DIR)
        destination = output_path_for(relative)
        destination.parent.mkdir(parents=True, exist_ok=True)

        print(f"\n[{file_index}/{len(lua_files)}] Traduciendo: {relative}")

        lines = source.read_text(encoding="utf-8", errors="ignore").splitlines()
        translated_lines = []

        for line_no, line in enumerate(lines, start=1):
            translated_lines.append(
                translator.translate_line(line, file=str(relative), line_no=line_no)
            )
            if line_no % 500 == 0 or line_no == len(lines):
                print(
                    f"\r  Líneas: {line_no}/{len(lines)} | "
                    f"Caché: {descriptions.stats['cache']} | "
                    f"Google: {descriptions.stats['google']} | "
                    f"Reglas: {descriptions.stats['rules']}",
                    end="", flush=True,
                )

        print()

        destination.write_text("\n".join(translated_lines) + "\n", encoding="utf-8")

        report = compare_files(source, destination)
        validation_reports.append(report)
        overall_ok = overall_ok and report["ok"]

        print(f"  Generado: {destination}")
        print(f"  Validación: {'OK' if report['ok'] else 'ERROR'}")

    unresolved = deduplicate_unresolved(database.unresolved)
    unresolved_file = CACHE_DIR / f"unresolved_{locale}.json"
    save_json(unresolved_file, {
        "count": len(unresolved),
        "locale": locale,
        "summary": database.stats,
        "info": (
            "Entidades no encontradas. "
            "Corrige en database/manual_overrides.json."
        ),
        "entities": unresolved,
    })

    validation_file = CACHE_DIR / f"validation_{locale}.json"
    save_json(validation_file, {"ok": overall_ok, "locale": locale, "files": validation_reports})
    descriptions.save()

    print("\n" + "=" * 55)
    print(f" Traducción terminada → {locale_name} ({locale})")
    print("=" * 55)
    print(f"Entidades traducidas (NPCnames):  {database.stats['npcnames_hit']}")
    print(f"Entidades traducidas (oficial):   {database.stats['official_translated']}")
    print(f"Entidades sin cambio (mismo nom): {database.stats['official_same_name']}")
    print(f"Resueltas por nombre exacto:      {database.stats['resolved_exact']}")
    print(f"Resueltas por variante:           {database.stats['resolved_variant']}")
    print(f"Entidades pendientes:             {len(unresolved)}")
    print(f"Validación:            {'OK' if overall_ok else 'ERROR'}")

    if not overall_ok:
        print(f"\nNo copies la guía al addon todavía.")
        print(f"Revisa {validation_file}")

    return 0 if overall_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())

