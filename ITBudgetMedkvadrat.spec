# -*- mode: python ; coding: utf-8 -*-
import os

# Корень проекта (где лежит .spec)
project_dir = os.path.dirname(os.path.abspath(SPECPATH))

# Локальные модули и данные, чтобы приложение работало из exe
datas = [
    (os.path.join(project_dir, 'config.py'), '.'),
    (os.path.join(project_dir, 'config.yaml'), '.'),
    (os.path.join(project_dir, 'dashboard.py'), '.'),
    (os.path.join(project_dir, 'init_db.py'), '.'),
    (os.path.join(project_dir, 'init_app.py'), '.'),
    (os.path.join(project_dir, 'create_data.py'), '.'),
    (os.path.join(project_dir, 'parser.py'), '.'),
    (os.path.join(project_dir, 'analyze_telecom_payments.py'), '.'),
    (os.path.join(project_dir, 'analyze_requests_vs_budget.py'), '.'),
]
if os.path.isdir(os.path.join(project_dir, 'data')):
    datas.append((os.path.join(project_dir, 'data'), 'data'))

a = Analysis(
    ['run_app.py'],
    pathex=[project_dir],
    binaries=[],
    datas=datas,
    hiddenimports=['config', 'init_app', 'init_db', 'create_data', 'parser',
                   'analyze_telecom_payments', 'analyze_requests_vs_budget'],
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
    a.binaries,
    a.datas,
    [],
    name='ITBudgetMedkvadrat',
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
    icon=['assets\\icon.ico'],
)
