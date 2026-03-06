# -*- mode: python ; coding: utf-8 -*-
import os

# Корень проекта: перебираем кандидатов (spec, cwd, в CI репо может быть в подпапке)
_spec_dir = os.path.dirname(os.path.abspath(SPECPATH))
_cwd = os.getcwd()
_candidates = [
    _spec_dir,
    _cwd,
    os.path.join(_cwd, 'medkvadrat-budget'),  # GitHub Actions: repo в подпапке
]
project_dir = None
for _d in _candidates:
    if _d and os.path.isfile(os.path.join(_d, 'config.py')):
        project_dir = os.path.abspath(_d)
        break
if project_dir is None:
    raise SystemExit(
        "PyInstaller: project root not found (no config.py in any of %s)." % _candidates
    )

# Локальные модули и данные — добавляем только существующие пути
_data_files = [
    'config.py', 'config.yaml', 'dashboard.py', 'init_db.py', 'init_app.py',
    'create_data.py', 'parser.py', 'analyze_telecom_payments.py', 'analyze_requests_vs_budget.py',
]
datas = []
for _f in _data_files:
    _path = os.path.join(project_dir, _f)
    if os.path.isfile(_path):
        datas.append((_path, '.'))
    else:
        raise SystemExit(f"PyInstaller: required file not found: {_path!r} (project_dir={project_dir!r})")
_data_dir = os.path.join(project_dir, 'data')
if os.path.isdir(_data_dir):
    datas.append((_data_dir, 'data'))

a = Analysis(
    [os.path.join(project_dir, 'run_app.py')],
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
    icon=[os.path.join(project_dir, 'assets', 'icon.ico')],
)
