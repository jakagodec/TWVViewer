# -*- mode: python ; coding: utf-8 -*-
# Build with: pyinstaller build.spec  (run from this directory, inside the venv)

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TWV Viewer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
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
    name='TWV Viewer',
)

app = BUNDLE(
    coll,
    name='TWV Viewer.app',
    icon='icon.icns',
    bundle_identifier='org.twvviewer.app',
    info_plist={
        'CFBundleName': 'TWV Viewer',
        'CFBundleDisplayName': 'TWV Viewer',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'NSHighResolutionCapable': True,
        'LSApplicationCategoryType': 'public.app-category.utilities',
        # Register .twv as a document type this app can open, and claim the
        # corresponding Uniform Type Identifier. Together these let Finder
        # offer "TWV Viewer" in Get Info > Open With, and "Change All..."
        # then sets it as the default handler for .twv files.
        'CFBundleDocumentTypes': [
            {
                'CFBundleTypeName': 'TWV Video',
                'CFBundleTypeRole': 'Viewer',
                'LSHandlerRank': 'Owner',
                'LSItemContentTypes': ['org.twvviewer.twv'],
                'CFBundleTypeExtensions': ['twv'],
            }
        ],
        'UTExportedTypeDeclarations': [
            {
                'UTTypeIdentifier': 'org.twvviewer.twv',
                'UTTypeDescription': 'Aresis Tweez Video File',
                'UTTypeConformsTo': ['public.data'],
                'UTTypeTagSpecification': {
                    'public.filename-extension': ['twv'],
                },
            }
        ],
    },
)
