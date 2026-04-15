@echo off
REM ─────────────────────────────────────────────────────────
REM amorce.bat — Lanceur de l'Application Locale Judi-Expert
REM Vérifie Docker Desktop, démarre le daemon si nécessaire,
REM lance les conteneurs et ouvre le navigateur.
REM Exigences : 1.4, 1.5, 2.2
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
echo        Judi-Expert - Amorce / Lanceur (Windows)
echo ======================================================
echo.

REM ── Etape 1 : Verifier que Docker est installe ─────────

echo [*] Verification de l'installation de Docker...

where docker >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] Docker n'est pas installe ou n'est pas dans le PATH.
    echo.
    echo   Veuillez installer Docker Desktop depuis :
    echo     https://www.docker.com/products/docker-desktop
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%v in ('docker --version 2^>nul') do set "DOCKER_VERSION=%%v"
echo [OK] Docker est installe (%DOCKER_VERSION%)

REM ── Etape 2 : Verifier / demarrer le daemon Docker ─────

echo [*] Verification du daemon Docker...

docker info >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Le daemon Docker est en cours d'execution.
    goto :launch_containers
)

echo [!] Le daemon Docker n'est pas en cours d'execution.
echo [*] Tentative de demarrage de Docker Desktop...

REM Try to start Docker Desktop
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
    REM Fallback: try via start menu shortcut
    start "" "Docker Desktop" >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERREUR] Impossible de demarrer Docker Desktop automatiquement.
        echo   Veuillez demarrer Docker Desktop manuellement et relancer ce script.
        echo.
        pause
        exit /b 1
    )
)

REM ── Attente du daemon Docker ────────────────────────────

echo [*] Attente du daemon Docker (timeout : %DOCKER_READY_TIMEOUT%s)...

set /a "elapsed=0"

:wait_docker_loop
if %elapsed% geq %DOCKER_READY_TIMEOUT% (
    echo.
    echo [ERREUR] Le daemon Docker n'a pas demarre dans le delai imparti.
    echo   Veuillez demarrer Docker Desktop manuellement et relancer ce script.
    echo.
    pause
    exit /b 1
)

docker info >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Le daemon Docker est pret.
    goto :launch_containers
)

timeout /t 2 /nobreak >nul
set /a "elapsed+=2"
echo   Attente... %elapsed%s / %DOCKER_READY_TIMEOUT%s
goto :wait_docker_loop

REM ── Etape 3 : Lancer docker compose ────────────────────

:launch_containers
echo.
echo [*] Lancement des conteneurs via docker compose...
echo.

docker compose -f "%COMPOSE_FILE%" up -d
if %errorlevel% neq 0 (
    echo.
    echo [ERREUR] Echec du lancement des conteneurs.
    echo   Consultez les logs avec : docker compose -f "%COMPOSE_FILE%" logs
    echo.
    pause
    exit /b 1
)

echo.
echo [OK] Tous les conteneurs sont lances.

REM ── Etape 4 : Attendre que le frontend soit pret ───────

echo [*] Attente du frontend judi-web-frontend (timeout : %FRONTEND_READY_TIMEOUT%s)...

set /a "elapsed=0"

:wait_frontend_loop
if %elapsed% geq %FRONTEND_READY_TIMEOUT% (
    echo.
    echo [!] Le frontend n'a pas repondu dans le delai imparti.
    echo [!] Les conteneurs sont demarres mais le frontend peut encore charger.
    echo [*] Verifiez manuellement : %FRONTEND_URL%
    goto :open_browser
)

curl -sf %FRONTEND_URL% >nul 2>&1
if %errorlevel% equ 0 (
    echo.
    echo [OK] Le frontend est pret sur %FRONTEND_URL%
    goto :open_browser
)

timeout /t 3 /nobreak >nul
set /a "elapsed+=3"
echo   Attente du frontend... %elapsed%s / %FRONTEND_READY_TIMEOUT%s
goto :wait_frontend_loop

REM ── Etape 5 : Ouvrir le navigateur ─────────────────────

:open_browser
echo.
echo [*] Ouverture du navigateur...
start "" "%FRONTEND_URL%"
echo [OK] Navigateur ouvert sur %FRONTEND_URL%

REM ── Resume final ────────────────────────────────────────

echo.
echo ======================================================
echo   Judi-Expert est pret !
echo ======================================================
echo.
echo   Services disponibles :
echo     * Frontend  : http://localhost:3000
echo     * Backend   : http://localhost:8000
echo     * LLM       : http://localhost:11434
echo     * RAG       : http://localhost:6333
echo     * OCR       : http://localhost:8001
echo.
echo   Commandes utiles :
echo     Arreter  : docker compose -f "%COMPOSE_FILE%" down
echo     Logs     : docker compose -f "%COMPOSE_FILE%" logs -f
echo     Statut   : docker compose -f "%COMPOSE_FILE%" ps
echo.
pause
