@echo off
cd /d "%~dp0"
set PYTHON=py

if /i "%~1"=="test" goto test
if /i "%~1"=="run" shift
set ARGS=
:collect
if "%~1"=="" goto run
set ARGS=%ARGS% %1
shift
goto collect

:run
%PYTHON% src\main.py %ARGS%
exit /b %ERRORLEVEL%

:test
%PYTHON% -m unittest discover -s tests -v
exit /b %ERRORLEVEL%
