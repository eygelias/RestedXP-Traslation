#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pase final: sobrescribe con las traducciones curadas y repara frases con \\n perdidos."""
import json
import re
import sys
from pathlib import Path

BASE = Path(r"repo-extract\RestedXP-Traslation-main")
sys.path.insert(0, str(BASE))
from addon_ui_translations import AUTHORED  # noqa: E402
from addon_ui_translations2 import AUTHORED2  # noqa: E402
from addon_ui_translations3 import AUTHORED3  # noqa: E402

UI = BASE / "database" / "addon_ui.json"
ui = json.loads(UI.read_text(encoding="utf-8"))
phrases = ui["ui"]
LOCALES = ["esES", "esMX", "ptBR", "deDE", "frFR", "ruRU", "koKR", "zhCN", "zhTW"]
TUP = {"esES": 0, "esMX": 0, "ptBR": 1, "deDE": 2, "frFR": 3, "ruRU": 4, "koKR": 5, "zhCN": 6, "zhTW": 7}

EXTRA = {
    "Check out the new Ultimate Hardcore Surivival Guide,\\nspecifically crafted to level your character as safe as\\n possible. |cff228B22Including new features.|r": (
        "Descubre la nueva Guía Definitiva de Supervivencia Hardcore,\\nespecialmente creada para subir de nivel con la máxima seguridad\\n posible. |cff228B22Incluye nuevas funciones.|r",
        "Confira a nova Guia Definitiva de Sobrevivência Hardcore,\\nespecialmente criada para subir de nível com a máxima segurança\\n possível. |cff228B22Inclui novas funções.|r",
        "Sieh dir den neuen ultimativen Hardcore-Überlebensguide an,\\nspeziell für maximale Sicherheit beim Leveln erstellt\\n möglich. |cff228B22Mit neuen Funktionen.|r",
        "Découvrez le nouveau Guide ultime de survie Hardcore,\\nspécialement conçu pour monter en niveau en toute sécurité\\n possible. |cff228B22Nouvelles fonctionnalités incluses.|r",
        "Попробуй новый Гайд по выживанию,\\nсозданный для максимально безопасной прокачки\\n персонажа. |cff228B22Включая новые функции.|r",
        "새로운 궁극의 하드코어 생존 가이드를 확인하세요.\\n안전하게 레벨업하도록 특별히 제작되었습니다\\n 있습니다. |cff228B22새로운 기능 포함.|r",
        "来看看全新的终极硬核生存指南，\\n专为尽可能安全地提升等级而打造\\n 。 |cff228B22包含全新功能。|r",
        "來看看全新的終極硬核生存指南，\\n專為盡可能安全地提升等級而打造\\n 。 |cff228B22包含全新功能。|r"),
    "Experience the fastest and most efficient Leveling Routes.\\nHand-crafted and maintained by the best Speedrunners in\\nthe Classic WoW Community.": (
        "Vive las rutas de nivelación más rápidas y eficientes.\\nCreadas y mantenidas por los mejores speedrunners de\\nla comunidad de WoW Classic.",
        "Viva as rotas de nivelamento mais rápidas e eficientes.\\nCriadas e mantidas pelos melhores speedrunners da\\ncomunidade do WoW Classic.",
        "Erlebe die schnellsten und effizientesten Leveling-Routen.\\nErstellt und gepflegt von den besten Speedrunnern der\\nClassic-WoW-Community.",
        "Découvrez les itinéraires de montée en niveau les plus rapides et efficaces.\\nCréés et maintenus par les meilleurs speedrunners de\\nla communauté de WoW Classic.",
        "Испытай самые быстрые и эффективные маршруты прокачки.\\nСозданы и поддерживаются лучшими спидраннерами\\nсообщества Classic WoW.",
        "가장 빠르고 효율적인 레벨링 루트를 경험하세요.\\n클래식 WoW 커뮤니티 최고의\\n스피드러너들이 제작하고 관리합니다.",
        "体验最快最高效的升级路线。\\n由经典旧世社区最顶尖的\\n速通玩家精心打造和维护。",
        "體驗最快最高效的升級路線。\\n由經典版社群最頂尖的\\n速通玩家精心打造和維護。"),
}

CURATED = {}
CURATED.update(AUTHORED)
CURATED.update(AUTHORED2)
CURATED.update(AUTHORED3)
CURATED.update(EXTRA)

over = 0
for eng, table in CURATED.items():
    row = phrases.get(eng)
    if row is None:
        continue
    for l in LOCALES:
        val = table if isinstance(table, str) else table[TUP[l]]
        if str(row.get(l) or "") != val:
            row[l] = val
            over += 1

# verificar marcadores finales
PH = re.compile(r"%(\d+\$)?[sd]")
def sig(t):
    return (len(PH.findall(t)), t.count("\\n"), t.count("|c"), t.count("|r"))

bad = []
for eng, row in phrases.items():
    s0 = sig(eng)
    for l in LOCALES:
        if sig(str(row.get(l) or "")) != s0:
            bad.append((l, eng[:50]))

UI.write_text(json.dumps(ui, ensure_ascii=False, indent=1), encoding="utf-8")
print("celdas sobrescritas con versión curada:", over)
print("problemas de marcadores restantes:", len(bad))
for b in bad[:15]:
    print("  ", b)
