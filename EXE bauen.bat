@echo off
REM Baut eine eigenstaendige SC-BP-Watcher.exe (kein Python beim Empfaenger noetig).
REM Voraussetzung: einmalig PyInstaller installieren (macht die naechste Zeile automatisch).
cd /d "%~dp0"

echo PyInstaller wird sichergestellt...
python -m pip install --upgrade pyinstaller || goto :fehler

echo.
echo EXE wird gebaut...
python -m PyInstaller --noconfirm --onefile --windowed --name "SC-BP-Watcher" sc_bp_watcher.py || goto :fehler

echo.
echo Fertig! Die EXE liegt in:  %~dp0dist\SC-BP-Watcher.exe
echo (Die Ordner build\ und SC-BP-Watcher.spec koennen geloescht werden.)
pause
exit /b 0

:fehler
echo.
echo FEHLER beim Bauen. Ist Python korrekt installiert?
pause
exit /b 1
