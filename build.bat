@echo off
chcp 65001 >nul
setlocal
title EdgeRunners build

echo ============================================================
echo   EdgeRunners - build to exe
echo ============================================================
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python not found in PATH.
  pause
  exit /b 1
)

echo [1/3] Checking PyInstaller ...
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
  echo       installing ...
  python -m pip install pyinstaller -i https://pypi.tuna.tsinghua.edu.cn/simple
  if errorlevel 1 (
    echo [ERROR] Failed to install PyInstaller.
    pause
    exit /b 1
  )
)

echo [2/3] Building ...
python -m PyInstaller build.spec --noconfirm --clean
if errorlevel 1 (
  echo [ERROR] Build failed.
  pause
  exit /b 1
)

echo [3/3] Copying config and manual ...
copy /y config.json dist\EdgeRunners\ >nul 2>&1
copy /y routes.json dist\EdgeRunners\ >nul 2>&1
if exist 說明.html copy /y 說明.html dist\EdgeRunners\ >nul 2>&1

echo.
echo ============================================================
echo   Done.  Output: dist\EdgeRunners\
echo ============================================================
echo.
echo   Remember: the whole folder must be shipped, not just the exe.
echo.
pause

