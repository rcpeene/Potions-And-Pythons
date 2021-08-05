Rem make.bat
Rem This just compiles the project into an exe and deletes some residual files
Rem from that process

del "PoPy.exe"
chdir .\src
pyinstaller popy.py --onefile --icon=..\potion.ico
move dist\popy.exe ..\
del popy.spec
rd /s /q .\build\
rd /s /q .\dist\
chdir ..\
ren "popy.exe" "PoPy.exe"
cls
