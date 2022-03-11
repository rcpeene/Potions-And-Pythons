echo make.sh
echo This just compiles the project into an executable for Linux/Mac and deletes some residual files from that process

rm ./popy.exe
cd ./src
pyinstaller popy.py --onefile --icon=..\potion.ico
mv dist/popy ../popy.exe
rm popy.spec
rm -rf ./build
rm -rf ./dist
cd ../
clear
