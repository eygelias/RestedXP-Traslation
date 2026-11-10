@echo off
chcp 65001 >nul
title RXP Translator V6 - Build EXE
cd /d "%~dp0"

echo ===============================================
echo  RXP Translator V5 - Construir EXE (PyQt5)
echo ===============================================
echo.

echo [1/2] Generando EXE con PyInstaller...

pyinstaller --noconfirm --onedir --windowed --name "RXP_Translator_V6" ^
    --add-data "RXP_Guide_Translator_ES.html;." ^
    --add-data "locales_config.py;." ^
    --add-data "translate_guides.py;." ^
    --add-data "translate_addon_interface.py;." ^
    --add-data "build_database.py;." ^
    --add-data "build_database_forever.py;." ^
    --add-data "questiedb_forever.py;." ^
    --add-data "validate_output.py;." ^
    --add-data "database;database" ^
    --add-data "cache;cache" ^
    --add-data "input;input" ^
    --hidden-import "PyQt5" ^
    --hidden-import "PyQt5.QtWebEngineWidgets" ^
    --hidden-import "PyQt5.QtWebChannel" ^
    --hidden-import "deep_translator" ^
    --hidden-import "deep_translator.google" ^
    --hidden-import "deep_translator.mymemory" ^
    app.py
echo.

echo [2/2] Copiando datos adicionales...
if exist "dist\RXP_Translator_V6" (
    mkdir "dist\RXP_Translator_V6\output" 2>nul
    if exist "icon.ico" copy /Y "icon.ico" "dist\RXP_Translator_V6\" >nul 2>&1
    echo Listo.
) else (
    echo ERROR: No se genero la carpeta dist\RXP_Translator_V6
)

echo.
echo ===============================================
if exist "dist\RXP_Translator_V6\RXP_Translator_V6.exe" (
    echo  EXE generado correctamente!
    echo  Ruta: %~dp0dist\RXP_Translator_V6\RXP_Translator_V6.exe
) else (
    echo  ERROR: El EXE no se genero.
)
echo ===============================================
pause
