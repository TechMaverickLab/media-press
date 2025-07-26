# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['press.py'],
    pathex=[],
    binaries=[
        ('bin/ffmpeg', 'bin'),    
        ('bin/ffprobe', 'bin')    
    ],
    datas=[
        ('templates', 'templates'), 
        ('static', 'static'),       
        ('config.yml', '.')         
    ],
    hiddenimports=[],
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
    bundle_identifier=None,
)