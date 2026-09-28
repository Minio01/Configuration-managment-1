@echo off
cd /d "%~dp0.."
python src\main.py --vfs-path "." --startup-script "scripts\startup_demo.txt"
