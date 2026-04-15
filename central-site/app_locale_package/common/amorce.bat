@echo off
REM ─────────────────────────────────────────────────────────
REM amorce.bat — Lanceur Amorce pour l'Application Locale
REM Copie embarquée dans l'installateur Windows.
REM
REM Vérifie Docker Desktop, démarre le daemon si nécessaire,
REM lance les conteneurs et ouvre le navigateur.
REM
REM Exigences : 1.4, 1.5, 2.2, 31.2
REM ─────────────────────────────────────────────────────────

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "INSTALL_DIR=%SCRIPT_DIR%.."
set "COMPOSE_FILE=%INSTALL_DIR%\config\docker-compose.yml"
set "DOCKER_READY_TIMEOUT=60"
set "FRONTEND_READY_TIMEOUT=180"
set "FRONTEND_URL=http://localhost:3000"

echo.
echo ======================================================
echo        Judi-Expert — Amorce / Lanceur (Windows)
echo ======================================================
echo.

REM ── Verifier Docker ─────────────────────────────────────

echo [*] Verification de Docker...

where docker >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] Docker n'est pas installe.
    echo   Veuillez reinstaller Judi-Expert.
    pause
    exit /b 1
)

for /f "tokens=*" %%v in ('docker --version 2^>nul') do set "DOCKER_VERSION=%%v"
echo [OK] Docker est installe (%DOCKER_VERSION%)

REM ── Verifier le daemon Docker ───────────────────────────

docker info >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Le daemon Docker est en cours d'execution.
    goto :launch
)

echo [!] Le daemon Docker n'est pas en cours d'execution.
echo [*] Tentative de demarrage de Docker Desktop...

set "DOCKER_DESKTOP="
if exist "%ProgramFiles%\Docker\Docker\Docker Desktop.exe" (
    set "DOCKER_DESKTOP=%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
)
if exist "%LOCALAPPDATA%\Docker\Docker Desktop.exe" (
    set "DOCKER_DESKTOP=%LOCALAPPDATA%\Docker\Docker Desktop.exe"
)

if defined DOCKER_DESKTOP (
    start "" "!DOCKER_DESKTOP!"
) else (
    start "" "Docker Desktop" >nul 2>&1
)

echo [*] Attente du daemon Docker (timeout : %DOCKER_READY_TIMEOUT%s)...
set /a "elapsed=0"

:wait_docker
if %elapsed% geq %DOCKER_READY_TIMEOUT% (
    echo [ERREUR] Docker n'a pas demarre. Veuillez le demarrer manuellement.
    pause
    exit /b 1
)
docker info >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Le daemon Docker est pret.
    goto :launch
)
timeout /t 2 /nobreak >nul
set /a "elapsed+=2"
goto :wait_docker

REM ── Lancer les conteneurs ───────────────────────────────

:launch
echo.
echo [*] Lancement des conteneurs...
docker compose -f "%COMPOSE_FILE%" up -d
if %errorlevel% neq 0 (
    echo [ERREUR] Echec du lancement des conteneurs.
    pause
    exit /b 1
)
echo [OK] Conteneurs lances.

REM ── Attendre le frontend ────────────────────────────────

echo [*] Attente du frontend (timeout : %FRONTEND_READY_TIMEOUT%s)...
set /a "elapsed=0"

:wait_frontend
if %elapsed% geq %FRONTEND_READY_TIMEOUT% (
    echo [!] Le frontend n'a pas repondu dans le delai imparti.
    goto :open_browser
)
curl -sf %FRONTEND_URL% >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Le frontend est pret.
    goto :open_browser
)
timeout /t 3 /nobreak >nul
set /a "elapsed+=3"
goto :wait_frontend

:open_browser
echo [*] Ouverture du navigateur...
start "" "%FRONTEND_URL%"

echo.
echo ======================================================
echo   Judi-Expert est pret !
echo ======================================================
echo.
echo   Application : %FRONTEND_URL%
echo.
pause
