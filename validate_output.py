#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_output.py
RXP Translator V6 - Valida que una guía traducida mantenga intacta la sintaxis.

V6: Validaciones adicionales:
    - Condiciones << no deben haberse traducido
    - .goto no debe haber traducido zona
    - Nombres de clase/raza en << deben permanecer en inglés
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Iterable

BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"
REPORT_FILE = BASE_DIR / "cache" / "validation_report.json"

COMMAND_RE = re.compile(
    r"^(\s*\.(?:accept|turnin|complete|daily|weekly|goto|zone|fly|fp|target|mob|collect|use|itemcount|destroy|train|cast|subzone|home|step|isQuestComplete|isOnQuest|xp|level|race|class|unitscan|vendor|waypoint|aura|equip|buy|sell)\b[^>]*)(?:>>.*)?$",
    re.IGNORECASE,
)
DIRECTIVE_RE = re.compile(r"^\s*#.*$")
# Directivas que SÍ pueden traducirse (contienen texto visible para el usuario)
TRANSLATABLE_DIRECTIVES = {"#name", "#next"}
RXP_TAG_RE = re.compile(r"\|cRXP_([A-Z_]+)_")
COLOR_RE = re.compile(r"\|c[0-9A-Fa-f]{8}")
TEXTURE_RE = re.compile(r"\|T[^|]*\|t")
LINK_RE = re.compile(r"\|H[^|]*\|h|\|h")

# V6: Validación de condicionales
CONDITIONAL_RE = re.compile(r"<<\s*(.+?)\s*$")
GOTO_RE = re.compile(r"^(\s*\.goto\s+)([^,]+)(,.*)$", re.IGNORECASE)

# Clases y razas que NUNCA deben traducirse en condicionales
WOW_CONDITIONALS = {
    # Clases
    "druid", "hunter", "mage", "paladin", "priest", "rogue", "shaman", "warlock", "warrior",
    "deathknight", "monk", "demonhunter", "evoker",
    # Razas
    "human", "dwarf", "nightelf", "gnome", "draenei", "worgen", "voidelf", "lightforged",
    "darkiron", "kul_tiran", "mechagnome", "orc", "undead", "tauren", "troll", "bloodelf",
    "goblin", "nightborne", "highmountain", "zandalarian", "vulpera", "maghar",
    # Facciones
    "alliance", "horde",
    # Modificadores
    "sod", "hardcore", "era", "tbc", "wotlk", "cata", "mop",
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def normalize_newlines(text: str) -> list[str]:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    # El salto de línea final es opcional: su presencia/ausencia no es una
    # línea de contenido extra (evita falsos 'line_count' de ±1).
    if len(lines) > 1 and lines[-1] == "":
        lines.pop()
    return lines


def structural_prefix(line: str) -> str | None:
    match = COMMAND_RE.match(line)
    return match.group(1).rstrip() if match else None


def check_conditional_not_translated(original: str, translated: str, line_no: int) -> list[dict]:
    """V6: Verifica que los condicionales << no se hayan traducido."""
    errors = []
    orig_match = CONDITIONAL_RE.search(original)
    trans_match = CONDITIONAL_RE.search(translated)

    if orig_match and not trans_match:
        errors.append({
            "type": "conditional_lost",
            "line": line_no,
            "before": original,
            "after": translated,
        })
    elif orig_match and trans_match:
        orig_cond = orig_match.group(1).strip()
        trans_cond = trans_match.group(1).strip()
        if orig_cond != trans_cond:
            errors.append({
                "type": "conditional_translated",
                "line": line_no,
                "before": original,
                "after": translated,
                "original_conditional": orig_cond,
                "translated_conditional": trans_cond,
            })

    return errors


def check_goto_not_translated(original: str, translated: str, line_no: int) -> list[dict]:
    """V6: Verifica que .goto no haya traducido el nombre de zona."""
    errors = []
    orig_match = GOTO_RE.match(original)
    trans_match = GOTO_RE.match(translated)

    if orig_match and trans_match:
        orig_zone = orig_match.group(2).strip()
        trans_zone = trans_match.group(2).strip()
        if orig_zone != trans_zone:
            errors.append({
                "type": "goto_zone_translated",
                "line": line_no,
                "before": original,
                "after": translated,
                "original_zone": orig_zone,
                "translated_zone": trans_zone,
            })

    return errors


# Commands where the argument (NPC name) is allowed to change during translation
TRANSLATABLE_COMMANDS = {".mob", ".target", ".unitscan"}

def compare_files(original: Path, translated: Path) -> dict:
    original_lines = normalize_newlines(read_text(original))
    translated_lines = normalize_newlines(read_text(translated))

    errors: list[dict] = []
    warnings: list[dict] = []

    if len(original_lines) != len(translated_lines):
        errors.append({
            "type": "line_count",
            "original": len(original_lines),
            "translated": len(translated_lines),
        })

    total = min(len(original_lines), len(translated_lines))

    for index in range(total):
        line_no = index + 1
        before = original_lines[index]
        after = translated_lines[index]

        # Comando estructural
        before_command = structural_prefix(before)
        after_command = structural_prefix(after)
        if before_command != after_command:
            if before_command is not None or after_command is not None:
                # Allow .mob, .target, .unitscan to have translated NPC names
                before_cmd = before.strip().split()[0].lower() if before.strip() else ""
                after_cmd = after.strip().split()[0].lower() if after.strip() else ""
                if before_cmd in TRANSLATABLE_COMMANDS and after_cmd in TRANSLATABLE_COMMANDS:
                    pass  # NPC name translation is allowed
                else:
                    errors.append({
                        "type": "command_changed",
                        "line": line_no,
                        "before": before,
                        "after": after,
                    })

        # Directivas (excepto las traducibles como #name)
        if DIRECTIVE_RE.match(before) and before != after:
            # Verificar si es una directiva traducible
            directive_key = before.strip().split()[0] if before.strip() else ""
            if directive_key not in TRANSLATABLE_DIRECTIVES:
                errors.append({
                    "type": "directive_changed",
                    "line": line_no,
                    "before": before,
                    "after": after,
                })

        # V6: .goto no debe traducir zona
        errors.extend(check_goto_not_translated(before, after, line_no))

        # V6: Condicional << no debe traducirse
        errors.extend(check_conditional_not_translated(before, after, line_no))

        # Checks de integridad estructural
        checks = [
            ("rxp_tags", RXP_TAG_RE.findall(before), RXP_TAG_RE.findall(after)),
            ("colors", COLOR_RE.findall(before), COLOR_RE.findall(after)),
            ("textures", TEXTURE_RE.findall(before), TEXTURE_RE.findall(after)),
            ("links", LINK_RE.findall(before), LINK_RE.findall(after)),
            ("reset_count", before.count("|r"), after.count("|r")),
            ("double_arrow_count", before.count(">>"), after.count(">>")),
        ]

        for check_name, expected, actual in checks:
            if expected != actual:
                errors.append({
                    "type": f"{check_name}_changed",
                    "line": line_no,
                    "before": before,
                    "after": after,
                    "expected": expected,
                    "actual": actual,
                })

        # Todo lo que no es texto visible debería mantenerse idéntico.
        # Excepción: #name, #next, .mob, .target, .unitscan se traducen.
        before_stripped = before.lstrip()
        visible_line = (
            ">>" in before
            or before_stripped.startswith("+")
            or before_stripped.startswith("--")
            or "|cRXP_" in before
            or before_stripped.startswith("#name ")
            or before_stripped.startswith("#next ")
            or any(before_stripped.lower().startswith(cmd) for cmd in TRANSLATABLE_COMMANDS)
        )
        if not visible_line and before != after:
            errors.append({
                "type": "non_visible_line_changed",
                "line": line_no,
                "before": before,
                "after": after,
            })

    return {
        "original": str(original),
        "translated": str(translated),
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
    }


def discover_pairs() -> list[tuple[Path, Path]]:
    pairs = []
    for original in INPUT_DIR.rglob("*.lua"):
        rel = original.relative_to(INPUT_DIR)
        candidate_same = OUTPUT_DIR / rel
        candidate_suffix = candidate_same.with_name(candidate_same.stem + "_es.lua")
        if candidate_suffix.exists():
            pairs.append((original, candidate_suffix))
        elif candidate_same.exists():
            pairs.append((original, candidate_same))
    return pairs


def main(argv: list[str]) -> int:
    REPORT_FILE.parent.mkdir(exist_ok=True)

    if len(argv) == 3:
        pairs = [(Path(argv[1]), Path(argv[2]))]
    else:
        pairs = discover_pairs()

    if not pairs:
        print("ERROR: no encontré pares input/output para validar.")
        return 1

    reports = []
    overall_ok = True

    for original, translated in pairs:
        report = compare_files(original, translated)
        reports.append(report)
        overall_ok = overall_ok and report["ok"]

        print("\n" + "=" * 50)
        print(f"Original:  {original}")
        print(f"Traducido: {translated}")
        print(f"Estado:    {'OK' if report['ok'] else 'ERROR'}")
        print(f"Errores:   {len(report['errors'])}")

        if report["errors"]:
            for error in report["errors"][:15]:
                etype = error["type"]
                line = error.get("line", "?")
                print(f"  - Línea {line}: {etype}")
                if etype == "conditional_translated":
                    print(f"    Original: {error['original_conditional']}")
                    print(f"    Traducido: {error['translated_conditional']}")
                elif etype == "goto_zone_translated":
                    print(f"    Zona original: {error['original_zone']}")
                    print(f"    Zona traducida: {error['translated_zone']}")
            if len(report["errors"]) > 15:
                print(f"  ... y {len(report['errors']) - 15} errores adicionales")

    REPORT_FILE.write_text(
        json.dumps({"ok": overall_ok, "files": reports}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\n" + "=" * 50)
    print(f"Reporte: {REPORT_FILE}")
    print("VALIDACIÓN CORRECTA" if overall_ok else "VALIDACIÓN FALLÓ")
    print("=" * 50)

    return 0 if overall_ok else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
