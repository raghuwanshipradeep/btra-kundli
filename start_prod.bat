@echo off
set PATH=C:\msys64\mingw64\bin;%PATH%
cd /d "%~dp0"
uvicorn main:app --workers 4 --host 0.0.0.0 --port 8000
