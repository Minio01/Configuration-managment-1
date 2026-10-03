@echo off
cd /d "%~dp0.."
python src\main.py --vfs-path "tests\fixtures\vfs_minimal" --startup-script "scripts\startup_errors.txt"
