@echo off
set SRC=%~dp0
set DST=%APPDATA%\Blender Foundation\Blender\5.0\scripts\addons\vrm_rigify_for_unity

echo Copying py files from:
echo   %SRC%
echo To:
echo   %DST%
echo.

if not exist "%DST%" (
    mkdir "%DST%"
    echo Created destination directory.
)

xcopy /Y "%SRC%\*.py" "%DST%\"

if exist "%DST%\__pycache__" (
    rd /S /Q "%DST%\__pycache__"
    echo Deleted __pycache__.
)

echo.
echo Done.
pause
