# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


added_files = [
    ('templates', 'templates'),
    ('static', 'static'),
    ('config.yml', '.')
]

added_binaries = [
    ('bin/ffmpeg', 'bin'),
    ('bin/ffprobe', 'bin')
]

a = Analysis(
    ['press.py'],
    pathex=[],
    binaries=added_binaries,
    datas=added_files,
    hiddenimports=['webview.platforms.cocoa'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Media Press',
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
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Media Press',
)

app = BUNDLE(
    coll,
    name='Media Press.app',
    icon='icon.icns',
    bundle_identifier='com.techmavericklab.mediapress',
)