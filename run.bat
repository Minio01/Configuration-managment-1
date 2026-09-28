@echo off
cd /d "%~dp0"
set PYTHON=python

if "%1"=="" goto run
if /i "%1"=="run" goto run
if /i "%1"=="test" goto test
echo Usage: run.bat [run^|test]
exit /b 1

:run
%PYTHON% src\main.py
exit /b %ERRORLEVEL%

:test
%PYTHON% -m unittest discover -s tests -v
exit /b %ERRORLEVEL%
