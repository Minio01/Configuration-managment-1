@echo off
cd /d "%~dp0.."
python src\main.py --vfs-path "tests\fixtures\vfs_rm" --startup-script "scripts\startup_rm.txt"
dir /s /b tests\fixtures\vfs_rm
