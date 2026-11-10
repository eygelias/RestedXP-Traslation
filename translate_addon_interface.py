#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
translate_addon_interface.py
Traduce la interfaz del addon RXPGuides (botones, menús, opciones).

Lee localization_strings.lua (inglés) y genera un archivo de locale traducido.
"""

import re
import sys
from pathlib import Path

try:
    from deep_translator import GoogleTranslator
except Exception:
    GoogleTranslator = None

# Locale codes for Google Translate
GOOGLE_TARGETS = {
    "esES": "es", "esMX": "es", "ptBR": "pt",
    "deDE": "de", "frFR": "fr", "ruRU": "ru",
    "koKR": "ko", "zhCN": "zh-CN", "zhTW": "zh-TW",
}

# Manual overrides for common WoW terms
MANUAL_OVERRIDES = {
    "esES": {
        "Addon": "Addon",
        "Discord": "Discord",
        "Hardcore": "Hardcore",
        "Quest": "Misión",
        "Questie": "Questie",
        "RestedXP": "RestedXP",
        "TomTom": "TomTom",
        "SilverDragon": "SilverDragon",
        "RXP": "RXP",
    },
    "esMX": {
        "Addon": "Addon",
        "Discord": "Discord",
        "Hardcore": "Hardcore",
        "Quest": "Misión",
        "Questie": "Questie",
        "RestedXP": "RestedXP",
        "TomTom": "TomTom",
        "SilverDragon": "SilverDragon",
        "RXP": "RXP",
    },
}


def extract_strings(lua_content: str) -> list[tuple[str, str]]:
    """Extract L["key"] = "value" pairs from localization_strings.lua."""
    pattern = r'L\["([^"]+)"\]\s*=\s*"([^"]*)"'
    return re.findall(pattern, lua_content)


def translate_string(text: str, target_locale: str) -> str:
    """Translate a single string using Google Translate."""
    if not GoogleTranslator:
        return text
    
    google_target = GOOGLE_TARGETS.get(target_locale, "es")
    
    # Skip strings with only formatting codes
    if text.startswith("|c") or text.startswith("|T"):
        return text
    
    # Skip very short strings
    if len(text) < 3:
        return text
    
    try:
        translated = GoogleTranslator(source="en", target=google_target).translate(text)
        return translated if translated else text
    except Exception:
        return text


def generate_locale_file(strings: list[tuple[str, str]], target_locale: str, 
                          output_path: Path, progress_callback=None) -> None:
    """Generate a locale file with translated strings."""
    lines = []
    lines.append(f"local addonName, addon = ...")
    lines.append(f"")
    lines.append(f"-- Traducción automática para {target_locale}")
    lines.append(f"-- Generado por RXP Translator V6")
    lines.append(f"local L = LibStub(\"AceLocale-3.0\"):NewLocale(addonName, \"{target_locale}\", false)")
    lines.append(f"if not L then return end")
    lines.append(f"")
    
    total = len(strings)
    for i, (key, value) in enumerate(strings):
        # Check for manual override
        overrides = MANUAL_OVERRIDES.get(target_locale, {})
        if value in overrides:
            translated = overrides[value]
        else:
            translated = translate_string(value, target_locale)
        
        # Escape quotes in the translated value
        translated_escaped = translated.replace('"', '\\"')
        
        lines.append(f'L["{key}"] = "{translated_escaped}"')
        
        if progress_callback:
            progress_callback(i + 1, total)
    
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    if len(sys.argv) < 3:
        print("Uso: python translate_addon_interface.py <locale> <output_path>")
        print("Ejemplo: python translate_addon_interface.py esES locale/esES.lua")
        return 1
    
    target_locale = sys.argv[1]
    output_path = Path(sys.argv[2])
    
    # Find localization_strings.lua
    base_dir = Path(__file__).resolve().parent
    strings_file = base_dir / "RXPGuides" / "locale" / "localization_strings.lua"
    
    if not strings_file.exists():
        # Try alternative paths
        alt_paths = [
            base_dir / "locale" / "localization_strings.lua",
            Path("locale/localization_strings.lua"),
        ]
        for alt in alt_paths:
            if alt.exists():
                strings_file = alt
                break
        else:
            print(f"ERROR: No encontré localization_strings.lua")
            return 1
    
    print(f"═══ Traduciendo interfaz del addon a {target_locale} ═══")
    print(f"Fuente: {strings_file}")
    print(f"Salida: {output_path}")
    
    # Read and extract strings
    content = strings_file.read_text(encoding="utf-8")
    strings = extract_strings(content)
    print(f"Strings encontrados: {len(strings)}")
    
    # Translate
    def progress(current, total):
        if current % 10 == 0 or current == total:
            print(f"  Traduciendo: {current}/{total}")
    
    generate_locale_file(strings, target_locale, output_path, progress)
    
    print(f"\n✅ Archivo generado: {output_path}")
    print(f"   {len(strings)} strings traducidos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
