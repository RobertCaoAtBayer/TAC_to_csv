setlocal enabledelayedexpansion
pushd .
echo === Building Executables with PyInstaller (CMD) ===

if %VIRTUAL_ENV%x==x (
  echo Warning: No virtual environment detected. Ensure you have the required dependencies installed globally or activate your venv before running this script.
  rem assume pyinstaller is installed globally if no venv is active
  set PYINSTALLER_EXE=%LOCALAPPDATA%\Programs\Python\Python313\Scripts\pyinstaller.exe
) else (
  echo Using virtual environment at %VIRTUAL_ENV%
  set PYINSTALLER_EXE=%VIRTUAL_ENV%\Scripts\pyinstaller.exe
)
echo Using PyInstaller executable at: %PYINSTALLER_EXE%
if not exist "%PYINSTALLER_EXE%" (
  echo Error: PyInstaller executable not found at %PYINSTALLER_EXE%. Please ensure PyInstaller is installed in your environment.
  goto :end
)
set SCRIPT_DIR=%~dp0
echo SCRIPT_DIR=%SCRIPT_DIR%

set BASE_DIR=%~dp0\..\
rem convert base dir to absolute path
for %%I in ("%BASE_DIR%") do set "BASE_DIR=%%~fI"
echo Base directory for dist/build: %BASE_DIR%

set EXTRA_ARGS=--distpath "%BASE_DIR%\build\dist" --workpath "%BASE_DIR%\build"


%PYINSTALLER_EXE% --onefile --add-data "index.html;." TAC_to_csv.py  %EXTRA_ARGS%