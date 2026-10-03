@echo off
cd /d "%~dp0.."
python src\main.py --vfs-path "tests\fixtures\vfs_files" --startup-script "scripts\startup_demo.txt"
