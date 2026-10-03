@echo off
cd /d "%~dp0.."
python src\main.py --vfs-path "tests\fixtures\vfs_nested" --startup-script "scripts\startup_commands.txt"
python src\main.py --vfs-path "tests\fixtures\vfs_files" --startup-script "scripts\startup_files.txt"
