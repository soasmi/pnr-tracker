@echo off
title Push PNR Tracker to GitHub for 24/7 Cloud Tracking
cd /d "%~dp0"

echo ========================================================
echo   24/7 Cloud Indian Railways PNR Tracker Setup
echo ========================================================
echo.
echo Step 1: Go to https://github.com/new
echo Step 2: Name your repository (e.g., pnr-tracker)
echo         (Choose Public or Private)
echo Step 3: Click "Create repository"
echo.
set /p REPO_URL="Paste your GitHub repository HTTPS URL here: "

if "%REPO_URL%"=="" (
    echo [!] No URL provided. Exiting.
    pause
    exit /b
)

git remote remove origin 2>nul
git remote add origin %REPO_URL%
git branch -M main
echo.
echo Pushing tracker files and 24/7 GitHub Action to your cloud repository...
git push -u origin main

echo.
echo ========================================================
echo  SUCCESS! 
echo  Your tracker is now deployed to GitHub Actions!
echo  It will run 24/7 in the cloud every 30 minutes.
echo  Your laptop can now be completely powered OFF!
echo ========================================================
echo.
pause
