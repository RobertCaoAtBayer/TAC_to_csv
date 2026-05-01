set MY_CMD=pyinstaller
rem if exist C:\Users\chcao\AppData\Roaming\Python\Python312\Scripts\pyinstaller.exe set MY_CMD=C:\Users\chcao\AppData\Roaming\Python\Python312\Scripts\pyinstaller.exe
rem %MY_CMD% --onefile --add-data "index.html;." TAC_to_csv.py
set BASE_DIR=%~dp0\..\
rem convert base dir to absolute path
for %%I in ("%BASE_DIR%") do set "BASE_DIR=%%~fI"
echo Base directory for dist/build: %BASE_DIR%
set EXTRA_ARGS=--distpath %BASE_DIR%\build\dist

mkdir %BASE_DIR%\build
%MY_CMD%  TAC_to_csv.spec %EXTRA_ARGS%