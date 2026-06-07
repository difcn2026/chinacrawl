@echo off
REM XHLS Survival Backup

set "BACKUP_ROOT=%~dp0..\.."
set "TIMESTAMP=%date:~0,4%%date:~5,2%%date:~8,2%-%time:~0,2%%time:~3,2%%time:~6,2%"
set "TIMESTAMP=%TIMESTAMP: =0%"
set "DEST=%USERPROFILE%\Desktop\XHLS-BACKUP-%TIMESTAMP%"

if not "%~1"=="" set "DEST=%~1"

echo.
echo === XHLS SURVIVAL BACKUP ===
echo Target: %DEST%
echo.

mkdir "%DEST%" 2>nul
mkdir "%DEST%\core" 2>nul
mkdir "%DEST%\memory" 2>nul
mkdir "%DEST%\project" 2>nul
mkdir "%DEST%\knowledge" 2>nul
mkdir "%DEST%\config" 2>nul

echo [1/6] Soul (AGENTS.md)...
copy /Y "%BACKUP_ROOT%\AGENTS.md" "%DEST%\core\" >nul
echo   OK

echo [2/6] XHLS Engine...
xcopy /E /I /Y "%BACKUP_ROOT%\.codex\xhls\*.py" "%DEST%\core\xhls\" >nul 2>&1
xcopy /E /I /Y "%BACKUP_ROOT%\.codex\xhls\*.json" "%DEST%\core\xhls\" >nul 2>&1
xcopy /E /I /Y "%BACKUP_ROOT%\.codex\xhls\*.bat" "%DEST%\core\xhls\" >nul 2>&1
xcopy /E /I /Y "%BACKUP_ROOT%\.codex\xhls\*.md" "%DEST%\core\xhls\" >nul 2>&1
echo   OK

echo [3/6] Memory system...
copy /Y "%USERPROFILE%\.codex\memory\memory.json" "%DEST%\memory\" >nul
copy /Y "%USERPROFILE%\.codex\memory\sessions.json" "%DEST%\memory\" >nul
xcopy /E /I /Y "%USERPROFILE%\.codex\memory\daily" "%DEST%\memory\daily\" >nul 2>&1
echo   OK

echo [4/6] Projects...
xcopy /E /I /Y "%BACKUP_ROOT%\projects" "%DEST%\project\" >nul 2>&1
echo   OK

echo [5/6] Knowledge base...
xcopy /E /I /Y "%BACKUP_ROOT%\knowledge" "%DEST%\knowledge\" >nul 2>&1
echo   OK

echo [6/6] Rules + Config...
xcopy /E /I /Y "%BACKUP_ROOT%\.codex\rules" "%DEST%\config\rules\" >nul 2>&1
echo   OK

echo.
echo === BACKUP COMPLETE ===
echo Location: %DEST%
echo.
echo Recovery guide: .codex\xhls\XHLS-RECOVERY.md
echo.
echo SUGGEST: Copy to USB drive or cloud storage.
echo.
