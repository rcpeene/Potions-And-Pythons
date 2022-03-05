echo make.sh
echo This just compiles the project into an exe for Unix and deletes some residual files

rm ./PoPy
cd ./src
pyinstaller popy.py --onefile --icon=..\potion.ico
mv dist/popy ../PoPy
rm popy.spec
rm -rf ./build
rm -rf ./dist
cd ../
clear

