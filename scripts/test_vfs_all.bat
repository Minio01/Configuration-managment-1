@echo off
cd /d "%~dp0.."
echo ^> python src\main.py --vfs-path "tests\fixtures\vfs_nested" --startup-script "scripts\startup_all.txt"
python src\main.py --vfs-path "tests\fixtures\vfs_nested" --startup-script "scripts\startup_all.txt"
