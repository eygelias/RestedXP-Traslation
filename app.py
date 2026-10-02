"""
app.py - RXP Translator V5
Interfaz con PyQt5 + QWebEngineView (Chromium embebido).
No se congela, renderiza HTML exacto, soporta frameless.
"""

import sys
import os
import json
import threading
from pathlib import Path

from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal, QUrl, Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage, QWebEngineProfile
from PyQt5.QtWebChannel import QWebChannel

# ── Paths ──
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).resolve().parent

WORK_DIR = Path(os.environ.get('RXP_WORKDIR', Path(sys.executable).parent if getattr(sys, 'frozen', False) else BASE_DIR))
sys.path.insert(0, str(BASE_DIR))

from locales_config import SUPPORTED_LOCALES, get_output_suffix, get_locale_config

# ── Messages (same as before) ──
MSG = {
    "esES": {"ready": "✅ RXP Translator V5 — Listo", "no_guides": "⚠ Selecciona una guía", "translating": "═══ Traduciendo a {}", "completed": "═══ Completado ═══", "no_pairs": "⚠ No hay archivos traducidos para validar. Traduce primero.", "validating": "═══ Validando ═══", "ok": "✅ OK", "fail": "❌ ERROR", "busy": "⚠ Operación en progreso...", "starting": "▶ Iniciando...", "done": "✅ Traducción completada", "error": "❌ ERROR:", "line": "Línea", "google": "Google", "cache": "Caché", "npcnames": "NPCnames", "official": "Oficial", "pending": "Pendientes"},
    "en": {"ready": "✅ RXP Translator V5 — Ready", "no_guides": "⚠ Select a guide", "translating": "═══ Translating to {}", "completed": "═══ Completed ═══", "no_pairs": "⚠ No translated files to validate. Translate first.", "validating": "═══ Validating ═══", "ok": "✅ OK", "fail": "❌ ERROR", "busy": "⚠ Operation in progress...", "starting": "▶ Starting...", "done": "✅ Translation completed", "error": "❌ ERROR:", "line": "Line", "google": "Google", "cache": "Cache", "npcnames": "NPCnames", "official": "Official", "pending": "Pending"},
    "ptBR": {"ready": "✅ Pronto", "no_guides": "⚠ Selecione um guia", "translating": "═══ Traduzindo para {}", "completed": "═══ Concluído ═══", "no_pairs": "⚠ Nenhum arquivo traduzido.", "validating": "═══ Validando ═══", "ok": "✅ OK", "fail": "❌ ERRO", "busy": "⚠ Em andamento...", "starting": "▶ Iniciando...", "done": "✅ Tradução concluída", "error": "❌ ERRO:", "line": "Linha", "google": "Google", "cache": "Cache", "npcnames": "NPCnames", "official": "Oficial", "pending": "Pendentes"},
    "deDE": {"ready": "✅ Bereit", "no_guides": "⚠ Guide wählen", "translating": "═══ Übersetze nach {}", "completed": "═══ Abgeschlossen ═══", "no_pairs": "⚠ Keine übersetzten Dateien.", "validating": "═══ Validiere ═══", "ok": "✅ OK", "fail": "❌ FEHLER", "busy": "⚠ Läuft...", "starting": "▶ Startet...", "done": "✅ Übersetzung abgeschlossen", "error": "❌ FEHLER:", "line": "Zeile", "google": "Google", "cache": "Cache", "npcnames": "NPCnames", "official": "Offiziell", "pending": "Ausstehend"},
    "frFR": {"ready": "✅ Prêt", "no_guides": "⚠ Sélectionnez un guide", "translating": "═══ Traduction vers {}", "completed": "═══ Terminé ═══", "no_pairs": "⚠ Aucun fichier traduit.", "validating": "═══ Validation ═══", "ok": "✅ OK", "fail": "❌ ERREUR", "busy": "⚠ En cours...", "starting": "▶ Démarrage...", "done": "✅ Traduction terminée", "error": "❌ ERREUR:", "line": "Ligne", "google": "Google", "cache": "Cache", "npcnames": "NPCnames", "official": "Officiel", "pending": "En attente"},
    "ruRU": {"ready": "✅ Готов", "no_guides": "⚠ Выберите гайд", "translating": "═══ Перевод на {}", "completed": "═══ Завершено ═══", "no_pairs": "⚠ Нет переведённых файлов.", "validating": "═══ Проверка ═══", "ok": "✅ OK", "fail": "❌ ОШИБКА", "busy": "⚠ Выполняется...", "starting": "▶ Начинаем...", "done": "✅ Перевод завершён", "error": "❌ ОШИБКА:", "line": "Строка", "google": "Google", "cache": "Кэш", "npcnames": "NPCnames", "official": "Официальный", "pending": "Ожидающие"},
    "koKR": {"ready": "✅ 준비됨", "no_guides": "⚠ 가이드를 선택하세요", "translating": "═══ 번역 중: {}", "completed": "═══ 완료 ═══", "no_pairs": "⚠ 번역된 파일 없음.", "validating": "═══ 검증 ═══", "ok": "✅ OK", "fail": "❌ 오류", "busy": "⚠ 진행 중...", "starting": "▶ 시작...", "done": "✅ 번역 완료", "error": "❌ 오류:", "line": "줄", "google": "Google", "cache": "캐시", "npcnames": "NPCnames", "official": "공식", "pending": "대기"},
    "zhTW": {"ready": "✅ 就緒", "no_guides": "⚠ 請選擇指南", "translating": "═══ 翻譯至 {}", "completed": "═══ 完成 ═══", "no_pairs": "⚠ 無已翻譯檔案.", "validating": "═══ 驗證 ═══", "ok": "✅ OK", "fail": "❌ 錯誤", "busy": "⚠ 進行中...", "starting": "▶ 開始...", "done": "✅ 翻譯完成", "error": "❌ 錯誤:", "line": "行", "google": "Google", "cache": "快取", "npcnames": "NPCnames", "official": "官方", "pending": "待處理"},
    "zhCN": {"ready": "✅ 就绪", "no_guides": "⚠ 请选择指南", "translating": "═══ 翻译至 {}", "completed": "═══ 完成 ═══", "no_pairs": "⚠ 无已翻译文件.", "validating": "═══ 验证 ═══", "ok": "✅ OK", "fail": "❌ 错误", "busy": "⚠ 进行中...", "starting": "▶ 开始...", "done": "✅ 翻译完成", "error": "❌ 错误:", "line": "行", "google": "Google", "cache": "缓存", "npcnames": "NPCnames", "official": "官方", "pending": "待处理"},
}

UI_TO_LOCALE = {"es": "esES", "en": "en", "pt": "ptBR", "de": "deDE", "fr": "frFR", "ru": "ruRU", "ko": "koKR", "zh-tw": "zhTW", "zh-cn": "zhCN"}


class Bridge(QObject):
    """Python ↔ JavaScript bridge via QWebChannel."""

    # Signal to send messages to JS
    js_log = pyqtSignal(str)
    js_progress = pyqtSignal(int, str)
    js_loading = pyqtSignal(str)  # 'start', 'stop', 'pulse'

    def __init__(self):
        super().__init__()
        self.window = None
        self.selected_files = []
        self.output_dir = str(WORK_DIR / "output")
        self.translating = False
        self.stop_requested = False
        self.ui_lang = "esES"
        self._config_file = WORK_DIR / "config.json"
        self._load_config()

    def set_window(self, win):
        self.window = win

    def _msg(self, key):
        return MSG.get(self.ui_lang, MSG["esES"]).get(key, key)

    def _log(self, text):
        safe = text.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
        self.js_log.emit(safe)

    def _update_progress(self, pct, text=""):
        safe = text.replace("'", "\\'")
        self.js_progress.emit(pct, safe)

    @pyqtSlot(str)
    def set_language(self, lang_code):
        self.ui_lang = UI_TO_LOCALE.get(lang_code, "esES")

    def _load_config(self):
        """Load saved folder paths from config.json."""
        try:
            if self._config_file.exists():
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                if cfg.get("output_dir"):
                    self.output_dir = cfg["output_dir"]
        except Exception:
            pass

    def _save_config(self):
        """Save current folder paths to config.json."""
        try:
            cfg = {"output_dir": self.output_dir}
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    @pyqtSlot()
    def stop_translation(self):
        """Request translation stop."""
        self.stop_requested = True
        self._log("⏹ Deteniendo...")

    @pyqtSlot(result=str)
    def select_guide_files(self):
        self.base_input_dir = None
        files, _ = QFileDialog.getOpenFileNames(
            self.window, "Seleccionar guía", "", "Guías Lua (*.lua);;Todos (*.*)"
        )
        if files:
            self.selected_files = files
            names = [Path(f).name for f in files]
            self._log(f"📁 {len(files)} guía(s) seleccionada(s)")
            return json.dumps({"files": files, "names": names})
        return json.dumps({"files": [], "names": []})


    @pyqtSlot(result=str)
    def select_guide_folder(self):
        folder = QFileDialog.getExistingDirectory(self.window, "Seleccionar carpeta de guías")
        if folder:
            self.base_input_dir = folder
            self.selected_files = []
            names = []
            base_dir = Path(folder)
            for file_path in base_dir.rglob("*.lua"):
                self.selected_files.append(str(file_path))
                names.append(file_path.name)
            
            self._log(f"📁 {len(self.selected_files)} guía(s) encontradas en carpeta")
            return json.dumps({"files": self.selected_files, "names": [base_dir.name + "/* (" + str(len(names)) + " archivos)"]})
        return json.dumps({"files": [], "names": []})

    @pyqtSlot(result=str)
    def select_output_dir(self):
        folder = QFileDialog.getExistingDirectory(self.window, "Seleccionar carpeta de salida")
        if folder:
            self.output_dir = folder
            self._save_config()
            return json.dumps({"dir": folder})
        return json.dumps({"dir": self.output_dir})
    
    @pyqtSlot(result=str)
    def select_addon_folder(self):
        """Select RXPGuides addon folder for interface translation."""
        folder = QFileDialog.getExistingDirectory(self.window, "Seleccionar carpeta del addon RXPGuides")
        if folder:
            self.addon_dir = folder
            return json.dumps({"dir": folder})
        return json.dumps({"dir": getattr(self, 'addon_dir', '')})

    @pyqtSlot()
    def open_output_folder(self):
        os.startfile(self.output_dir)

    @pyqtSlot()
    def close_app(self):
        QApplication.instance().quit()

    @pyqtSlot()
    def start_drag(self):
        """Called from JS when user clicks on the header."""
        if self.window:
            self.window._dragging = True
            cursor_pos = QApplication.desktop().cursor().pos()
            self.window._drag_start_x = cursor_pos.x()
            self.window._drag_start_y = cursor_pos.y()
            self.window._win_start_x = self.window.x()
            self.window._win_start_y = self.window.y()

    @pyqtSlot(int, int)
    def do_drag(self, x, y):
        """Called from JS on mousemove over header."""
        if self.window and self.window._dragging:
            dx = x - self.window._drag_start_x
            dy = y - self.window._drag_start_y
            self.window.move(self.window._win_start_x + dx, self.window._win_start_y + dy)

    @pyqtSlot()
    def stop_drag(self):
        """Called from JS on mouseup."""
        if self.window:
            self.window._dragging = False

    @pyqtSlot(str, str, result=str)
    def translate(self, locale, categories_json):
        if self.translating:
            self._log(self._msg("busy"))
            return '{"status":"busy"}'
        if not self.selected_files:
            self._log(self._msg("no_guides"))
            return '{"status":"error"}'
        self.translating = True
        self.stop_requested = False
        self.js_loading.emit("start")
        threading.Thread(target=self._translate_worker, args=(locale,), daemon=True).start()
        return '{"status":"started"}'

    @pyqtSlot(result=str)
    def validate(self):
        if self.translating:
            self._log(self._msg("busy"))
            return '{"status":"busy"}'
        if not self.selected_files:
            self._log(self._msg("no_pairs"))
            return '{"status":"error"}'
        self.translating = True
        self.js_loading.emit("start")
        threading.Thread(target=self._validate_worker, daemon=True).start()
        return '{"status":"started"}'
    
    @pyqtSlot(str, result=str)
    def translate_addon_interface(self, locale):
        """Translate RXPGuides addon interface to the specified locale."""
        if self.translating:
            self._log(self._msg("busy"))
            return '{"status":"busy"}'
        
        addon_dir = getattr(self, 'addon_dir', '')
        if not addon_dir:
            self._log("⚠ Selecciona la carpeta del addon RXPGuides primero")
            return '{"status":"error"}'
        
        # Check if localization_strings.lua exists
        strings_file = Path(addon_dir) / "locale" / "localization_strings.lua"
        if not strings_file.exists():
            self._log(f"⚠ No encontré localization_strings.lua en {addon_dir}")
            return '{"status":"error"}'
        
        self.translating = True
        self.js_loading.emit("start")
        threading.Thread(target=self._translate_addon_worker, args=(locale, addon_dir), daemon=True).start()
        return '{"status":"started"}'

    def _translate_worker(self, locale):
        try:
            import translate_guides as tg
            from translate_guides import (LocalDatabase, DescriptionTranslator, GuideTranslator,
                                           ensure_dirs, save_json, deduplicate_unresolved, compare_files)

            tg._ZONE_PATTERNS.clear()
            tg._QUESTIE_ZONES.clear()
            tg.TARGET_LOCALE = locale
            tg.OUTPUT_SUFFIX = get_output_suffix(locale)
            locale_name = get_locale_config(locale)["name"]

            self._log(self._msg("translating").format(f"{locale_name} ({locale})"))
            self._update_progress(0, self._msg("starting"))

            ensure_dirs()
            database = LocalDatabase(locale=locale)
            descriptions = DescriptionTranslator(locale=locale)
            translator = GuideTranslator(database, descriptions)

total_lines = 0
            for file_path in self.selected_files:
                source = Path(file_path)
                if source.exists():
                    total_lines += len(source.read_text(encoding="utf-8", errors="ignore").splitlines())

            done_lines = 0
            lock = threading.Lock()
            
            def process_file(file_path):
                nonlocal done_lines
                source = Path(file_path)
                if not source.exists():
                    return
                    
                if getattr(self, 'base_input_dir', None) and str(source).startswith(self.base_input_dir):
                    rel_path = source.relative_to(self.base_input_dir)
                    destination = Path(self.output_dir) / rel_path
                else:
                    destination = Path(self.output_dir) / source.name
                    
                destination.parent.mkdir(parents=True, exist_ok=True)
                
                lines = source.read_text(encoding="utf-8", errors="ignore").splitlines()
                result_lines = []
                errors = 0
                
                for line_no, line in enumerate(lines, start=1):
                    try:
                        result_lines.append(translator.translate_line(line, file=source.name, line_no=line_no))
                    except Exception as e:
                        result_lines.append(line)
                        errors += 1
                        if errors <= 3:
                            pass # log in thread can be messy
                    
                    with lock:
                        done_lines += 1
                        if done_lines % 50 == 0 or done_lines == total_lines:
                            pct = int(done_lines / max(total_lines, 1) * 100)
                            stats = f"Procesando {len(self.selected_files)} guías | Google: {descriptions.stats['google']} | Caché: {descriptions.stats['cache']}"
                            self._update_progress(pct, stats)
                            
                destination.write_text("
".join(result_lines) + "
", encoding="utf-8")

            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                executor.map(process_file, self.selected_files)

            save_json(tg.CACHE_DIR / "wowhead_cache.json", descriptions.wowhead_cache)
            deduplicate_unresolved()
            
            self._log(f"✅ ¡{len(self.selected_files)} guías traducidas al {locale}!")
            self._update_progress(100, self._msg("done"))
            
        except Exception as e:
            self._log(f"❌ Error fatal: {str(e)}")
        finally:
            self.translating = False
            self.js_loading.emit("stop")


    def _validate_worker(self):
        try:
            from validate_output import compare_files
            output_dir = Path(self.output_dir)
            if not output_dir.exists():
                self._log(self._msg("no_pairs"))
                return
            pairs = []
            for fp in self.selected_files:
                orig = Path(fp)
                trans = output_dir / orig.name
                if trans.exists():
                    pairs.append((orig, trans))
            if not pairs:
                self._log(self._msg("no_pairs"))
                return
            self._log(self._msg("validating"))
            overall_ok = True
            for orig, trans in pairs:
                report = compare_files(orig, trans)
                ok = report["ok"]
                overall_ok = overall_ok and ok
                err_c = len(report["errors"])
                status = self._msg("ok") if ok else f"{self._msg('fail')} {err_c} errores"
                self._log(f"  {orig.name} → {status}")
                if not ok:
                    for err in report["errors"][:3]:
                        self._log(f"    {self._msg('line')} {err.get('line','?')}: {err['type']}")
            self._log(self._msg("ok") if overall_ok else self._msg("fail"))
        except Exception as e:
            self._log(f"{self._msg('error')} {str(e)}")
        finally:
            self.translating = False
            self.js_loading.emit("stop")
    
    def _translate_addon_worker(self, locale, addon_dir):
        """Worker thread for translating addon interface.
        Scans ALL .lua files for L("text") calls AND localization_strings.lua.
        Generates a complete locale file matching ChatGPT's approach."""
        try:
            import re
            from pathlib import Path
            
            addon_path = Path(addon_dir)
            locale_dir = addon_path / "locale"
            strings_file = locale_dir / "localization_strings.lua"
            
            self._log(f"═══ Traduciendo interfaz del addon a {locale} ═══")
            
            # Step 1: Collect ALL translatable strings from the addon
            all_strings = {}  # key -> english text (deduplicated)
            
            # 1a. From localization_strings.lua: L["key"] = "value"
            if strings_file.exists():
                content = strings_file.read_text(encoding="utf-8-sig")
                pattern = r'L\["([^"]+)"\]\s*=\s*"((?:[^"\\]|\\.|"")*)"'
                for key, value in re.findall(pattern, content, re.DOTALL):
                    if len(value) >= 3 and key not in all_strings:
                        all_strings[key] = value
                self._log(f"  localization_strings.lua: {len(all_strings)} strings")
            
            # 1b. From ALL .lua files in addon root: L("text")
            lua_files = list(addon_path.glob("*.lua"))
            l_call_count = 0
            for lua_file in lua_files:
                try:
                    fc = lua_file.read_text(encoding="utf-8-sig", errors="ignore")
                    # Match L("text") - the most common pattern
                    for match in re.finditer(r'L\("([^"]+)"\)', fc):
                        text = match.group(1)
                        if len(text) >= 3 and text not in all_strings:
                            all_strings[text] = text
                            l_call_count += 1
                except Exception:
                    pass
            
            # Also scan UI/*.lua files
            for lua_file in (addon_path / "UI").glob("**/*.lua"):
                try:
                    fc = lua_file.read_text(encoding="utf-8-sig", errors="ignore")
                    for match in re.finditer(r'L\("([^"]+)"\)', fc):
                        text = match.group(1)
                        if len(text) >= 3 and text not in all_strings:
                            all_strings[text] = text
                            l_call_count += 1
                except Exception:
                    pass
            
            self._log(f"  Archivos .lua: +{l_call_count} strings adicionales")
            self._log(f"  TOTAL: {len(all_strings)} strings únicos")
            
            if not all_strings:
                self._log("⚠ No se encontraron strings para traducir")
                return
            
            # Step 2: Setup translator
            google_targets = {
                "esES": "es", "esMX": "es", "ptBR": "pt",
                "deDE": "de", "frFR": "fr", "ruRU": "ru",
                "koKR": "ko", "zhCN": "zh-CN", "zhTW": "zh-TW",
            }
            google_target = google_targets.get(locale, "es")
            
            has_translator = False
            try:
                from deep_translator import GoogleTranslator
                has_translator = True
            except ImportError:
                self._log("⚠ deep_translator no disponible. Usando strings originales.")
            
            translated_count = 0
            skipped_count = 0
            
            # Step 3: Generate translated locale file
            output_file = locale_dir / f"{locale}.lua"
            lines = []
            lines.append("local addonName, addon = ...")
            lines.append("")
            lines.append(f"-- Traducción automática para {locale}")
            lines.append("-- Generado por RXP Translator V5")
            lines.append(f'local L = LibStub("AceLocale-3.0"):NewLocale(addonName, "{locale}", false)')
            lines.append("if not L then return end")
            lines.append("")
            
            # Binding names
            binding_names = [
                ("RXPItemFrameButton1", "Active Item 1"), ("RXPItemFrameButton2", "Active Item 2"),
                ("RXPItemFrameButton3", "Active Item 3"), ("RXPItemFrameButton4", "Active Item 4"),
                ("RXPTargetFrame_FriendlyButton1", "Friendly Active Target 1"),
                ("RXPTargetFrame_FriendlyButton2", "Friendly Active Target 2"),
                ("RXPTargetFrame_FriendlyButton3", "Friendly Active Target 3"),
                ("RXPTargetFrame_FriendlyButton4", "Friendly Active Target 4"),
                ("RXPTargetFrame_EnemyButton1", "Enemy Active Target 1"),
                ("RXPTargetFrame_EnemyButton2", "Enemy Active Target 2"),
                ("RXPTargetFrame_EnemyButton3", "Enemy Active Target 3"),
                ("RXPTargetFrame_EnemyButton4", "Enemy Active Target 4"),
            ]
            
            translated_bindings = {}
            for btn, default_name in binding_names:
                if has_translator:
                    try:
                        tr = GoogleTranslator(source="en", target=google_target).translate(default_name)
                        translated_bindings[btn] = tr if tr else default_name
                    except Exception:
                        translated_bindings[btn] = default_name
                else:
                    translated_bindings[btn] = default_name
            
            lines.append("-- Binding names")
            for btn, name in translated_bindings.items():
                safe_name = name.replace('"', '\\"')
                lines.append(f'_G["BINDING_NAME_" .. "CLICK {btn}:LeftButton"] = "{safe_name}"')
            lines.append("")
            
            # L.delimiter and L.words
            words_default = {
                "Accept": "Accept", "Kill": "Kill", "Talk to": "Talk to",
                "Turn in": "Turn in", "Collect": "Collect", "Buy": "Buy",
                "Use": "Use", "Set": "Set"
            }
            translated_words = {}
            if has_translator:
                for eng, val in words_default.items():
                    try:
                        tr = GoogleTranslator(source="en", target=google_target).translate(val)
                        translated_words[eng] = tr if tr else val
                    except Exception:
                        translated_words[eng] = val
            else:
                translated_words = words_default
            
            lines.append("L.delimiter = ' '")
            words_str = ", ".join(f'["{k}"] = "{v}"' for k, v in translated_words.items())
            lines.append(f"L.words = {{ {words_str} }}")
            lines.append("")
            
            # Step 4: Translate all strings
            total = len(all_strings)
            self._log(f"Traduciendo {total} strings...")
            
            for i, (key, value) in enumerate(all_strings.items()):
                if has_translator and len(value) >= 3:
                    try:
                        translated = GoogleTranslator(source="en", target=google_target).translate(value)
                        if translated:
                            safe_key = key.replace('\\', '\\\\').replace('"', '\\"')
                            safe_val = translated.replace('\\', '\\\\').replace('"', '\\"')
                            lines.append(f'L["{safe_key}"] = "{safe_val}"')
                            translated_count += 1
                        else:
                            safe_key = key.replace('\\', '\\\\').replace('"', '\\"')
                            lines.append(f'L["{safe_key}"] = "{value}"')
                            skipped_count += 1
                    except Exception:
                        safe_key = key.replace('\\', '\\\\').replace('"', '\\"')
                        lines.append(f'L["{safe_key}"] = "{value}"')
                        skipped_count += 1
                else:
                    safe_key = key.replace('\\', '\\\\').replace('"', '\\"')
                    lines.append(f'L["{safe_key}"] = "{value}"')
                    skipped_count += 1
                
                if (i + 1) % 25 == 0:
                    pct = int((i + 1) / total * 90)
                    self._update_progress(pct, f"Traduciendo: {i+1}/{total}")
                    self._log(f"  {i+1}/{total}...")
            
            # Alliance/Horde
            if has_translator:
                try:
                    al = GoogleTranslator(source="en", target=google_target).translate("Alliance")
                    ho = GoogleTranslator(source="en", target=google_target).translate("Horde")
                    lines.append(f'L["Alliance"] = "{al if al else "Alliance"}"')
                    lines.append(f'L["Horde"] = "{ho if ho else "Horde"}"')
                except Exception:
                    lines.append('L["Alliance"] = "Alliance"')
                    lines.append('L["Horde"] = "Horde"')
            else:
                lines.append('L["Alliance"] = "Alliance"')
                lines.append('L["Horde"] = "Horde"')
            
            # Write the file
            output_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
            self._log(f"✅ {output_file.name} ({translated_count} traducidos, {skipped_count} sin traducir)")
            
            # esMX: copy from esES
            if locale == "esMX":
                eses_file = locale_dir / "esES.lua"
                if eses_file.exists():
                    esmx_content = eses_file.read_text(encoding="utf-8-sig")
                    esmx_content = esmx_content.replace('"esES"', '"esMX"')
                    esmx_file = locale_dir / "esMX.lua"
                    esmx_file.write_text(esmx_content, encoding="utf-8")
                    self._log("✅ esMX.lua generado como copia de esES")
            
            # Update locales.xml
            locales_xml = locale_dir / "locales.xml"
            if locales_xml.exists():
                xml_content = locales_xml.read_text(encoding="utf-8-sig")
                if f'{locale}.lua' not in xml_content:
                    xml_content = xml_content.replace(
                        '    <Script file="NPCnames.lua"/>',
                        f'    <Script file="{locale}.lua"/>\n    <Script file="NPCnames.lua"/>'
                    )
                    locales_xml.write_text(xml_content, encoding="utf-8")
                    self._log(f"✅ locales.xml actualizado")
            
            # Update Locale.lua
            locale_lua = addon_path / "Locale.lua"
            if locale_lua.exists():
                locale_content = locale_lua.read_text(encoding="utf-8-sig")
                if f"'{locale}'" not in locale_content:
                    old = "or locale == 'ruRU' then"
                    new = f"or locale == 'ruRU' or locale == '{locale}' then"
                    if old in locale_content:
                        locale_content = locale_content.replace(old, new)
                        locale_lua.write_text(locale_content, encoding="utf-8")
                        self._log(f"✅ Locale.lua actualizado")
            
            self._update_progress(100, f"✅ Interfaz traducida a {locale}")
            self._log("═══ Traducción del addon completada ═══")
            
        except Exception as e:
            import traceback
            self._log(f"{self._msg('error')} {str(e)}")
            for line in traceback.format_exc().strip().split('\n')[-3:]:
                self._log(f"  {line.strip()}")
        finally:
            self.translating = False
            self.js_loading.emit("stop")


class MainWindow(QMainWindow):
    def __init__(self, bridge):
        super().__init__()
        self.bridge = bridge
        self.setWindowTitle("RXP Translator V5")

        # ── Frameless + transparent ──
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(480, 620)
        self.setMinimumSize(460, 550)
        self.setContentsMargins(0, 0, 0, 0)

        # Try icon
        try:
            from PyQt5.QtGui import QIcon
            ico = BASE_DIR / "icon.ico"
            if ico.exists():
                self.setWindowIcon(QIcon(str(ico)))
        except Exception:
            pass

        # ── WebEngine view ──
        self.view = QWebEngineView(self)
        self.setCentralWidget(self.view)

        # Remove layout margins
        if self.layout():
            self.layout().setContentsMargins(0, 0, 0, 0)
            self.layout().setSpacing(0)

        # Make page background transparent
        page = self.view.page()
        page.setBackgroundColor(Qt.transparent)

        # Close window when JS calls window.close()
        page.windowCloseRequested.connect(self.close)

        # Inject CSS to make body transparent on every load
        page.loadFinished.connect(self._inject_transparency)

        # ── WebChannel ──
        self.channel = QWebChannel()
        self.channel.registerObject("bridge", self.bridge)
        page.setWebChannel(self.channel)

        # Connect signals
        self.bridge.js_log.connect(self._on_log)
        self.bridge.js_progress.connect(self._on_progress)
        self.bridge.js_loading.connect(self._on_loading)

        # Load HTML
        html_path = self._find_html()
        if html_path:
            self.view.setUrl(QUrl.fromLocalFile(str(html_path)))
        else:
            self.view.setHtml("<h1>ERROR: No se encontró RXP_Guide_Translator_ES.html</h1>")

        # Drag state
        self._dragging = False
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._win_start_x = 0
        self._win_start_y = 0

    def _inject_transparency(self, ok):
        """Inject CSS to make body transparent after page loads."""
        if ok:
            js = """
            document.documentElement.style.background = 'transparent';
            document.body.style.background = 'transparent';
            document.documentElement.style.margin = '0';
            document.body.style.margin = '0';
            """
            self.view.page().runJavaScript(js)

    def _find_html(self):
        candidates = [
            BASE_DIR / "RXP_Guide_Translator_ES.html",
            WORK_DIR / "RXP_Guide_Translator_ES.html",
        ]
        for p in candidates:
            if p.exists():
                return p
        return None

    def _run_js(self, code):
        self.view.page().runJavaScript(code)

    def _on_log(self, text):
        self._run_js(f"addLog('{text}')")

    def _on_progress(self, pct, text):
        self._run_js(f"updateProgress({pct}, '{text}')")

    def _on_loading(self, action):
        if action == "start":
            self._run_js("startLoading()")
        elif action == "stop":
            self._run_js("stopLoading()")
        elif action == "pulse":
            self._run_js("pulseLoading()")

    # Allow dragging the frameless window
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if hasattr(self, '_drag_pos') and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()


def main():
    # High DPI support
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)

    app = QApplication(sys.argv)
    app.setApplicationName("RXP Translator V5")

    # ── Set icon for taskbar + title bar + task manager ──
    from PyQt5.QtGui import QIcon
    icon_path = BASE_DIR / "icon.ico"
    if not icon_path.exists():
        # Fallback: look next to the .exe
        icon_path = Path(sys.executable).parent / "icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
        # Windows-specific: set AppUserModelID so taskbar shows the correct icon
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("RXPTranslatorV5")
        except Exception:
            pass

    bridge = Bridge()
    window = MainWindow(bridge)
    bridge.set_window(window)
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
