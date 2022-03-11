Rem make.bat
Rem This just compiles the project into an executable for Windows and deletes some residual files from that process

del "popy.exe"
chdir .\src
pyinstaller popy.py --onefile --icon=..\potion.ico
move dist\popy.exe ..\
del popy.spec
rd /s /q .\build\
rd /s /q .\dist\
chdir ..\
cls
