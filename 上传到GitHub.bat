@echo off
title Upload PuJiang APK to GitHub
echo ============================================================
echo   Upload PuJiang APK project to GitHub (for cloud build)
echo ============================================================
echo.

REM ====== Edit the token below ======
set GH_USER=yanzeyu0
set GH_TOKEN=PASTE_YOUR_TOKEN_HERE
set GH_REPO=pujiang-apk
REM ===================================

if "%GH_TOKEN%"=="PASTE_YOUR_TOKEN_HERE" (
    echo [ERROR] Please set GH_TOKEN in this file first.
    echo   Token: GitHub - Settings - Developer settings - Personal access tokens - Tokens(classic)
    echo   Check scopes: repo, workflow
    pause
    exit /b
)

where git >nul 2>&1
if errorlevel 1 (
    echo [ERROR] git not found. Install Git for Windows first.
    pause
    exit /b
)

cd /d "%~dp0"

if exist .git (
    echo [OK] .git exists, skip init.
) else (
    git init
)

git config user.name "%GH_USER%"
git config user.email "%GH_USER%@users.noreply.github.com"

git add -A
git commit -m "pujiang apk - P1 client" >nul 2>&1

set "REMOTE=https://%GH_USER%:%GH_TOKEN%@github.com/%GH_USER%/%GH_REPO%.git"

git remote remove origin >nul 2>&1
git remote add origin "%REMOTE%"

echo Pushing to GitHub...
git branch -M main
git push -u origin main --force

echo.
echo ============================================================
echo   DONE. Now open:
echo     https://github.com/%GH_USER%/%GH_REPO%/actions
echo   Click "Build PuJiang APK" - "Run workflow".
echo ============================================================
pause
