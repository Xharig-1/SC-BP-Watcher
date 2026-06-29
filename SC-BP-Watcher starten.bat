@echo off
REM Startet den Watcher ohne schwarzes Konsolenfenster (pythonw).
cd /d "%~dp0"
start "" pythonw "sc_bp_watcher.py"
