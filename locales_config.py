"""
locales_config.py
Configuración central de idiomas soportados por RXP Translator V6.
"""

# ─────────────────────────────────────────────────────────
# Locales soportados
# ─────────────────────────────────────────────────────────

SUPPORTED_LOCALES = {
    "esES": {
        "name": "Español (EU)",
        "flag": "🇪🇸",
        "wow_locale": "esES",
        "google_target": "es",
        "libbabble_file": "subzone_esES.lua",
        "npcnames_locale": "esES",
        "output_suffix": "_esES",
    },
    "esMX": {
        "name": "Español (AL)",
        "flag": "🇲🇽",
        "wow_locale": "esMX",
        "google_target": "es",
        "libbabble_file": "subzone_esMX.lua",
        "npcnames_locale": "esMX",
        "output_suffix": "_esMX",
    },
    "ptBR": {
        "name": "Português",
        "flag": "🇧🇷",
        "wow_locale": "ptBR",
        "google_target": "pt",
        "libbabble_file": "subzone_ptBR.lua",
        "npcnames_locale": "ptBR",
        "output_suffix": "_ptBR",
    },
    "deDE": {
        "name": "Deutsch",
        "flag": "🇩🇪",
        "wow_locale": "deDE",
        "google_target": "de",
        "libbabble_file": "subzone_deDE.lua",
        "npcnames_locale": "deDE",
        "output_suffix": "_deDE",
    },
    "frFR": {
        "name": "Français",
        "flag": "🇫🇷",
        "wow_locale": "frFR",
        "google_target": "fr",
        "libbabble_file": "subzone_frFR.lua",
        "npcnames_locale": "frFR",
        "output_suffix": "_frFR",
    },
    "ruRU": {
        "name": "Русский",
        "flag": "🇷🇺",
        "wow_locale": "ruRU",
        "google_target": "ru",
        "libbabble_file": "subzone_ruRU.lua",
        "npcnames_locale": "ruRU",
        "output_suffix": "_ruRU",
    },
    "koKR": {
        "name": "한국어",
        "flag": "🇰🇷",
        "wow_locale": "koKR",
        "google_target": "ko",
        "libbabble_file": "subzone_koKR.lua",
        "npcnames_locale": "koKR",
        "output_suffix": "_koKR",
    },
    "zhTW": {
        "name": "繁體中文",
        "flag": "🇹🇼",
        "wow_locale": "zhTW",
        "google_target": "zh-TW",
        "libbabble_file": "subzone_zhTW.lua",
        "npcnames_locale": "zhTW",
        "output_suffix": "_zhTW",
    },
    "zhCN": {
        "name": "简体中文",
        "flag": "🇨🇳",
        "wow_locale": "zhCN",
        "google_target": "zh-CN",
        "libbabble_file": "subzone_zhCN.lua",
        "npcnames_locale": "zhCN",
        "output_suffix": "_zhCN",
    },
}

DEFAULT_LOCALE = "esES"


def get_locale_config(locale: str) -> dict:
    """Retorna la configuración de un locale, o el default si no existe."""
    return SUPPORTED_LOCALES.get(locale, SUPPORTED_LOCALES[DEFAULT_LOCALE])


def get_google_target(locale: str) -> str:
    """Retorna el código de idioma para Google Translate."""
    return get_locale_config(locale)["google_target"]


def get_output_suffix(locale: str) -> str:
    """Retorna el sufijo para el archivo de salida."""
    return get_locale_config(locale)["output_suffix"]


def list_locales() -> list[tuple[str, str]]:
    """Retorna lista de (código, nombre) de todos los locales."""
    return [(code, cfg["name"]) for code, cfg in SUPPORTED_LOCALES.items()]
