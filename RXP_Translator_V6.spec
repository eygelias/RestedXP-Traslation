# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[('RXP_Guide_Translator_ES.html', '.'), ('locales_config.py', '.'), ('translate_guides.py', '.'), ('translate_addon_interface.py', '.'), ('build_database.py', '.'), ('build_database_forever.py', '.'), ('questiedb_forever.py', '.'), ('validate_output.py', '.'), ('database', 'database'), ('cache', 'cache'), ('input', 'input')],
    hiddenimports=['PyQt5', 'PyQt5.QtWebEngineWidgets', 'PyQt5.QtWebChannel', 'deep_translator', 'deep_translator.google', 'deep_translator.mymemory'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='RXP_Translator_V6',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='RXP_Translator_V6',
)
