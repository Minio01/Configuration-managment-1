@echo off
cd /d "%~dp0.."
echo ^> python src\main.py --vfs-path "." --startup-script "scripts\startup_demo.txt"
python src\main.py --vfs-path "." --startup-script "scripts\startup_demo.txt"
