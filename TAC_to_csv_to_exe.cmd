set MY_CMD=pyinstaller
if exist C:\Users\chcao\AppData\Roaming\Python\Python312\Scripts\pyinstaller.exe set MY_CMD=C:\Users\chcao\AppData\Roaming\Python\Python312\Scripts\pyinstaller.exe
rem %MY_CMD% --onefile --add-data "index.html;." TAC_to_csv.py
%MY_CMD%  TAC_to_csv.spec 