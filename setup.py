"""
Сборка Contragenti в exe и MSI-инсталлятор для Windows.

Использование:
    .venv\\Scripts\\python setup.py build          # только exe (build/exe.win-amd64-3.12/)
    .venv\\Scripts\\python setup.py bdist_msi       # exe + MSI-инсталлятор (dist/*.msi)

OfficePlus-сборка: Demo CRM (crm_delphi/) не включается — это была
демонстрация/реклама платформы una.md от автора Contragenti, сотрудникам
OfficePlus она не нужна.

Мастер настройки (setup_wizard.py → «ContragentiSetup.exe») идёт первым в
списке Executable: именно первый exe cx_Freeze запускает по галочке «Launch
on finish» в конце установки (launch_on_finish=True). Мастер докачивает из
GitHub свежие компоненты и стартовую базу (release.json, data/), настраивает
crm.ini и реестр, прогоняет самопроверку и при ошибках собирает отчёт
(паспорт системы + лог) для отправки разработчику. Он же доступен из меню
«Пуск» — «Contragenti — настройка и обновление».
"""

import os
import sys
import zipfile
from cx_Freeze import setup, Executable

APP_VERSION = "1.3.8"   # то же значение — в VERSION, release.json и company_search.py

_HERE = os.path.dirname(os.path.abspath(__file__))


def _prepare_seed_db():
    """Стартовая база компаний (companies.db) для установки — из
    data/companies_seed.zip. После установки в Program Files программа при
    первом запуске копирует её в %LOCALAPPDATA%\\Contragenti и работает
    с копией."""
    seed_dir = os.path.join(_HERE, "build", "seed")
    os.makedirs(seed_dir, exist_ok=True)
    companies = os.path.join(seed_dir, "companies.db")
    with zipfile.ZipFile(os.path.join(_HERE, "data", "companies_seed.zip")) as z:
        with open(companies, "wb") as f:
            f.write(z.read("companies.db"))
    print(f"[setup.py] стартовая база: {companies} ({os.path.getsize(companies)} байт)")
    return companies


_BUILDING = any(a.startswith(("build", "bdist")) for a in sys.argv[1:])
_SEED_COMPANIES = _prepare_seed_db() if _BUILDING else ""

build_exe_options = {
    "packages": [
        "tkinter",
        "selenium",
        "openpyxl",
        "PIL",
        "pystray",
        "sqlite3",
        "xml",
        "http",
        "queue",
        "threading",
        "argparse",
        "csv",
        "json",
        "datetime",
        "oracledb",
    ],
    # certifi — запасной набор корневых сертификатов для мастера настройки:
    # хранилище Windows на свежем сервере не знало цепочку GitHub
    "includes": ["tms_export", "certifi"],
    # numpy/onnxruntime/sympy попадают в окружение сборки транзитивно
    # (markitdown для проверки презентаций) и утяжеляют установщик на 11 МБ;
    # программе они не нужны (openpyxl работает без numpy)
    "excludes": ["test", "unittest", "numpy", "onnxruntime", "sympy", "mpmath", "magika",
                 "markitdown", "pptx", "PyInstaller"],
    "include_files": [
        ("README.md", "README.md"),
        ("GUIDE_ru.md", "GUIDE_ru.md"),
        ("API_ru.md", "API_ru.md"),
        ("INTEGRATION.md", "INTEGRATION.md"),
        ("INSTALL_WINDOWS_ru.md", "INSTALL_WINDOWS_ru.md"),
        ("INSTALL_MSI_ru.md", "INSTALL_MSI_ru.md"),
        ("INSTALL_RO.md", "INSTALL_RO.md"),
        ("LICENSE", "LICENSE"),
        ("app_icon.ico", "app_icon.ico"),
        # версия установки и манифест обновления — их сравнивает мастер настройки
        ("VERSION", "VERSION"),
        ("release.json", "release.json"),
        # стартовая база компаний: запасная копия на случай компьютера без интернета
        ("data/companies_seed.zip", "data/companies_seed.zip"),
        # SDK для Python/C++ — чтобы интеграция была под рукой сразу после установки
        ("sdk", "sdk"),
    ],
}

if _SEED_COMPANIES:
    # база компаний с данными — утилита сразу не пустая
    build_exe_options["include_files"].append((_SEED_COMPANIES, "companies.db"))

# Тихий запуск GUI-приложения (без консольного окна)
base = "Win32GUI" if sys.platform == "win32" else None

executables = [
    # Первым — мастер настройки: cx_Freeze запускает executables[0] по галочке
    # «Launch on finish» в конце установки.
    Executable(
        "setup_wizard.py",
        base=base,
        target_name="ContragentiSetup.exe",
        icon="app_icon.ico",
        shortcut_name="Contragenti — настройка и обновление",
        shortcut_dir="ProgramMenuFolder",
    ),
    Executable(
        "company_search.py",
        base=base,
        target_name="Contragenti.exe",
        icon="app_icon.ico",
        shortcut_name="Contragenti",
        shortcut_dir="DesktopFolder",
    ),
]

bdist_msi_options = {
    "upgrade_code": "{8E2C6C7A-6B0B-4C2C-9C7A-3B2D4E5F6A7B}",
    "add_to_path": False,
    # установка для всех пользователей в Program Files (msiexec попросит права
    # администратора); данные программы пишут в %LOCALAPPDATA%\Contragenti
    "all_users": True,
    "initial_target_dir": r"[ProgramFilesFolder]\Contragenti",
    "install_icon": "app_icon.ico",
    # в конце установки — галочка «Launch on finish»: запускает мастер настройки
    "launch_on_finish": True,
    # …а при тихой установке (msiexec /i … /qn) диалога нет, поэтому мастер
    # запускается пользовательским действием после InstallFinalize
    "data": {
        "CustomAction": [
            ("LaunchWizardAfterInstall", 226, "TARGETDIR", '"[TARGETDIR]ContragentiSetup.exe"'),
        ],
        "InstallExecuteSequence": [
            ("LaunchWizardAfterInstall", "NOT Installed AND NOT REMOVE", 6601),
        ],
    },
    "summary_data": {
        "author": "Pavel Tuhari",
        "comments": "Contragenti — поиск юридических лиц Молдовы (data2b.md)",
    },
}

setup(
    name="Contragenti",
    version=APP_VERSION,
    description="Contragenti — поиск юридических лиц Молдовы (data2b.md)",
    options={
        "build_exe": build_exe_options,
        "bdist_msi": bdist_msi_options,
    },
    executables=executables,
)
