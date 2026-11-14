#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fill_addon_ui.py
Rellena los huecos de database/addon_ui.json con calidad:

  1. Etiquetas de UI   -> addon_ui_translations.AUTHORED (curadas, glosario WoW).
  2. Nombres entidades -> questiedb_forever.json (nombres verificados del cliente).
  3. Nombres propios   -> se conservan (string plano en AUTHORED).
  4. Fragmentos código -> se conservan.
  5. Resto (frases)    -> Google Translate (8 hilos, caché por texto).

Solo se rellenan celdas vacías: los valores existentes (locales oficiales) no se tocan.
"""

from __future__ import annotations

import concurrent.futures
import json
import re
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from addon_ui_translations import AUTHORED  # noqa: E402
from addon_ui_translations2 import AUTHORED2  # noqa: E402
from addon_ui_translations3 import AUTHORED3  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent
UI_FILE = BASE_DIR / "database" / "addon_ui.json"
DB_FILE = BASE_DIR / "database" / "questiedb_forever.json"

LOCALES = ["esES", "esMX", "ptBR", "deDE", "frFR", "ruRU", "koKR", "zhCN", "zhTW"]
TUPLE_INDEX = {"esES": 0, "esMX": 0, "ptBR": 1, "deDE": 2, "frFR": 3,
               "ruRU": 4, "koKR": 5, "zhCN": 6, "zhTW": 7}
GOOGLE_TARGET = {"esES": "es", "esMX": "es", "ptBR": "pt", "deDE": "de", "frFR": "fr",
                 "ruRU": "ru", "koKR": "ko", "zhCN": "zh-CN", "zhTW": "zh-TW"}

CODE_JUNK = re.compile(r"^\s*(and |or event|,\s*$)|u:find|\* (Group|Killing|Quests|Solo): %")

_local = threading.local()
_cache = {}
_cache_lock = threading.Lock()
_stats = {"authored": 0, "db": 0, "google": 0, "kept": 0, "fail": 0}
_done = 0


def translator_for(target):
    t = getattr(_local, "t", None)
    if t is None or getattr(_local, "target", None) != target:
        from deep_translator import GoogleTranslator
        t = GoogleTranslator(source="en", target=target)
        _local.t = t
        _local.target = target
    return t


def translate_cached(text, target, locale):
    key = (text, target)
    with _cache_lock:
        if key in _cache:
            return _cache[key]
    import time
    out = None
    # Google con ritmo suave (máx. ~2-3 pet./seg entre hilos)
    for attempt in range(2):
        try:
            out = translator_for(target).translate(text)
            break
        except Exception:
            time.sleep(2.5 + attempt * 2)
    if not out:
        # Respaldo: MyMemory (mismo proveedor que usa el programa en runtime)
        try:
            from deep_translator import MyMemoryTranslator
            mm_target = f"{locale[:2]}-{locale[2:]}"
            out = MyMemoryTranslator(source="en-US", target=mm_target).translate(text)
        except Exception:
            out = None
    time.sleep(0.45)  # acota las peticiones por segundo
    out = out.strip() if out else None
    with _cache_lock:
        _cache[key] = out
    return out


def main():
    global _done
    from deep_translator import GoogleTranslator  # noqa: F401  (valida disponibilidad)
    ui = json.loads(UI_FILE.read_text(encoding="utf-8"))
    phrases = ui.get("ui", {})

    db = json.loads(DB_FILE.read_text(encoding="utf-8"))
    names = {}
    for sec in ("npcs", "items", "objects"):
        for v in db.get(sec, {}).values():
            en = str(v.get("en") or "").strip()
            if en and en.casefold() not in names:
                names[en.casefold()] = v

    # ── fases 1–4 (locales, sin red) ──
    google_jobs = []
    for eng, row in phrases.items():
        for locale in LOCALES:
            if str(row.get(locale) or "").strip():
                continue
            val = None
            table = AUTHORED
            if eng not in table:
                table = AUTHORED2 if eng in AUTHORED2 else AUTHORED3
            if eng in table:
                a = table[eng]
                val = a if isinstance(a, str) else a[TUPLE_INDEX[locale]]
                _stats["authored"] += 1
            if not val:
                hit = names.get(eng.strip().casefold())
                if hit:
                    val = str(hit.get(locale) or "").strip() or None
                    if val:
                        _stats["db"] += 1
            if not val and CODE_JUNK.search(eng):
                val = eng
                _stats["kept"] += 1
            if val:
                row[locale] = val
            else:
                google_jobs.append((eng, locale))

    print(f"Local: {dict(_stats)} | pendientes Google: {len(google_jobs)}")
    UI_FILE.write_text(json.dumps(ui, ensure_ascii=False, indent=1), encoding="utf-8")

    # ── fase 5 (Google, 8 hilos) ──
    lock = threading.Lock()

    def work(job):
        global _done
        eng, locale = job
        out = translate_cached(eng, GOOGLE_TARGET[locale], locale)
        with lock:
            if out:
                phrases[eng][locale] = out
                _stats["google"] += 1
            else:
                _stats["fail"] += 1
            _done += 1
            if _done % 50 == 0 or _done == len(google_jobs):
                print(f"  Traducción: {_done}/{len(google_jobs)}  {dict(_stats)}", flush=True)
                UI_FILE.write_text(json.dumps(ui, ensure_ascii=False, indent=1), encoding="utf-8")

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
        list(ex.map(work, google_jobs))

    ui["meta"]["fill_tool"] = "fill_addon_ui.py (curadas+cliente+Google)"
    UI_FILE.write_text(json.dumps(ui, ensure_ascii=False, indent=1), encoding="utf-8")

    print("\nCOBERTURA FINAL:")
    for l in LOCALES:
        total = sum(1 for r in phrases.values() if str(r.get(l) or "").strip())
        print(f"  {l}: {total}/{len(phrases)}")
    print("Origen:", dict(_stats))


if __name__ == "__main__":
    main()
