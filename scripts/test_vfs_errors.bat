@echo off
cd /d "%~dp0.."
python src\main.py --vfs-path "tests\fixtures\missing"
python src\main.py --vfs-path "tests\fixtures\vfs_minimal\hello.txt"
