# -*- mode: python ; coding: utf-8 -*-

from importlib.util import find_spec
from PyInstaller.utils.hooks import collect_all

package_datas = []
package_binaries = []
package_hiddenimports = ['zipfile']

for package in ('pgdumplib', 'pyzipper'):
    if find_spec(package) is None:
        raise ModuleNotFoundError(
            f'{package} is required to build TAC_to_csv. '
            'Install requirements.txt in the Python environment running PyInstaller.'
        )
    datas, binaries, hiddenimports = collect_all(package)
    package_datas.extend(datas)
    package_binaries.extend(binaries)
    package_hiddenimports.extend(hiddenimports)

a = Analysis(
    ['TAC_to_csv.py'],
    pathex=[],
    binaries=package_binaries,
    datas=[('index.html', '.')] + package_datas,
    hiddenimports=package_hiddenimports,
    hookspath=[],
    hooksconfig={'matplotlib': {'backends': ['TkAgg', 'Agg']}},
    runtime_hooks=[],
    # Keep PyArrow for Feather files; these optional integrations are not used.
    excludes=[
        'polars',
        '_polars_runtime_32',
        'scipy',
        'PySide6',
        'shiboken6',
        'PySide2',
        'shiboken2',
        'PyQt6',
        'PyQt5',
        'IPython',
        'ipykernel',
        'ipywidgets',
        'notebook',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='TAC_to_csv',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
