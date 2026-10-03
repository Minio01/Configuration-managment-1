@echo off
cd /d "%~dp0.."
echo ^> python src\main.py --vfs-path "tests\fixtures\missing"
python src\main.py --vfs-path "tests\fixtures\missing"
echo ^> python src\main.py --vfs-path "tests\fixtures\vfs_minimal\hello.txt"
python src\main.py --vfs-path "tests\fixtures\vfs_minimal\hello.txt"
