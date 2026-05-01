; ─────────────────────────────────────────────────────────
; judi-expert-installer.nsi — Installateur Windows NSIS
; Produit un installateur autonome pour l'Application Locale
; Judi-Expert sur Windows.
;
; NSIS est gratuit et open-source (zlib/libpng license),
; compatible avec un usage commercial.
;
; Exigences : 31.1, 31.2, 31.3, 31.4, 31.5, 31.6, 1.1, 1.2, 1.3
; ─────────────────────────────────────────────────────────

!include "nsDialogs.nsh"
!include "MUI2.nsh"
!include "LogicLib.nsh"

!ifndef VERSION
  !define VERSION "1.0.0"
!endif

!ifndef STAGING_DIR
  !define STAGING_DIR "..\..\.staging"
!endif

!ifndef OUTPUT_DIR
  !define OUTPUT_DIR "..\output"
!endif

; ── Configuration générale ────────────────────────────────

Name "Judi-Expert ${VERSION}"
OutFile "${OUTPUT_DIR}\judi-expert-installer-${VERSION}-windows.exe"
InstallDir "C:\judi-expert"
RequestExecutionLevel admin
SetCompressor /SOLID lzma
Unicode true

; ── Variables ─────────────────────────────────────────────

Var CPU_CORES
Var RAM_GB
Var DISK_FREE_GB
Var DISK_ENCRYPTED
Var PREREQ_ERRORS
Var PREREQ_WARNINGS
Var ACCEPT_NO_ENCRYPT
Var DOCKER_INSTALLED

; ── Cloud sync detection variables ────────────────────────
Var CLOUD_SYNC_WARNING

; ── Software detection variables ──────────────────────────
Var CHROME_FOUND
Var VERACRYPT_FOUND
Var BITLOCKER_ON
Var SOFTWARE_WARNINGS

; ── Pages ─────────────────────────────────────────────────

Page custom PagePrerequisites PagePrerequisitesLeave
Page directory
Page instfiles
Page custom PageFinish

; ── Macros utilitaires ────────────────────────────────────

!macro CheckPrerequisites
  ; Verification CPU (nombre de coeurs)
  ReadEnvStr $CPU_CORES "NUMBER_OF_PROCESSORS"
  IntCmp $CPU_CORES 4 +2 0 +2
    StrCpy $PREREQ_ERRORS "$PREREQ_ERRORS$\nCPU insuffisant : $CPU_CORES coeurs (minimum 4)"

  ; Verification RAM via PowerShell
  nsExec::ExecToStack 'powershell -NoProfile -Command "[math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 1)"'
  Pop $0
  Pop $RAM_GB
  StrCpy $RAM_GB $RAM_GB -1
  IntCmp $RAM_GB 8 +2 0 +2
    StrCpy $PREREQ_ERRORS "$PREREQ_ERRORS$\nRAM insuffisante : $RAM_GB Go (minimum 8 Go)"

  ; Verification espace disque libre
  nsExec::ExecToStack 'powershell -NoProfile -Command "[math]::Round((Get-PSDrive C).Free / 1GB, 1)"'
  Pop $0
  Pop $DISK_FREE_GB
  StrCpy $DISK_FREE_GB $DISK_FREE_GB -1
  IntCmp $DISK_FREE_GB 50 +2 0 +2
    StrCpy $PREREQ_ERRORS "$PREREQ_ERRORS$\nEspace disque insuffisant : $DISK_FREE_GB Go libres (minimum 50 Go)"

  ; Verification chiffrement du disque (BitLocker) - avertissement seulement
  nsExec::ExecToStack 'powershell -NoProfile -Command "(Get-BitLockerVolume -MountPoint C: -ErrorAction SilentlyContinue).ProtectionStatus"'
  Pop $0
  Pop $DISK_ENCRYPTED
  StrCmp $DISK_ENCRYPTED "On" +2
    StrCpy $PREREQ_WARNINGS "Le disque n est pas chiffre (BitLocker recommande)"

  ; Verification que le repertoire d installation n est pas dans un dossier cloud synchronise
  StrCpy $CLOUD_SYNC_WARNING ""
  nsExec::ExecToStack 'powershell -NoProfile -Command "if ($INSTDIR -match ''OneDrive|Dropbox|Google Drive|iCloudDrive'') { Write-Output ''cloud'' } else { Write-Output ''ok'' }"'
  Pop $0
  Pop $1
  StrCmp $1 "cloud" 0 +2
    StrCpy $PREREQ_WARNINGS "$PREREQ_WARNINGS$\nATTENTION : Le repertoire d installation est dans un dossier synchronise (OneDrive/Dropbox/Google Drive). Les donnees d expertise ne doivent PAS etre synchronisees dans le cloud (RGPD). Choisissez C:\judi-expert comme repertoire."

  ; Verification OneDrive : le dossier C:\judi-expert ne doit pas etre sauvegarde par OneDrive
  nsExec::ExecToStack 'powershell -NoProfile -Command "try { $folders = (Get-ItemProperty -Path ''HKCU:\Software\Microsoft\OneDrive\Accounts\Personal'' -Name ''UserFolder'' -ErrorAction SilentlyContinue).UserFolder; if ($folders -and ''C:\judi-expert''.StartsWith($folders)) { Write-Output ''synced'' } else { Write-Output ''ok'' } } catch { Write-Output ''ok'' }"'
  Pop $0
  Pop $1
  StrCmp $1 "synced" 0 +2
    StrCpy $PREREQ_WARNINGS "$PREREQ_WARNINGS$\nATTENTION : C:\judi-expert est dans le dossier OneDrive. Deplacez OneDrive ou changez le repertoire d installation."

  ; Verification Google Chrome
  StrCpy $SOFTWARE_WARNINGS ""
  StrCpy $CHROME_FOUND "0"
  IfFileExists "$PROGRAMFILES\Google\Chrome\Application\chrome.exe" chrome_ok
  IfFileExists "$PROGRAMFILES64\Google\Chrome\Application\chrome.exe" chrome_ok
  IfFileExists "$LOCALAPPDATA\Google\Chrome\Application\chrome.exe" chrome_ok
    StrCpy $SOFTWARE_WARNINGS "$SOFTWARE_WARNINGS$\n- Google Chrome n est pas installe (requis pour l interface Judi-Expert)"
    Goto chrome_done
  chrome_ok:
    StrCpy $CHROME_FOUND "1"
  chrome_done:

  ; Verification chiffrement : BitLocker ou VeraCrypt
  StrCpy $BITLOCKER_ON "0"
  StrCpy $VERACRYPT_FOUND "0"

  ; Verifier BitLocker
  nsExec::ExecToStack 'powershell -NoProfile -Command "(Get-BitLockerVolume -MountPoint C: -ErrorAction SilentlyContinue).ProtectionStatus"'
  Pop $0
  Pop $2
  StrCmp $2 "On" bitlocker_active
    Goto check_veracrypt
  bitlocker_active:
    StrCpy $BITLOCKER_ON "1"
    Goto encryption_done

  check_veracrypt:
  ; Verifier VeraCrypt (installé ou driver actif)
  IfFileExists "$PROGRAMFILES\VeraCrypt\VeraCrypt.exe" veracrypt_found
  IfFileExists "$PROGRAMFILES64\VeraCrypt\VeraCrypt.exe" veracrypt_found
    ; Ni BitLocker ni VeraCrypt
    StrCpy $SOFTWARE_WARNINGS "$SOFTWARE_WARNINGS$\n- Le disque n est pas chiffre : installez VeraCrypt (https://veracrypt.eu) puis chiffrez le disque systeme"
    Goto encryption_done
  veracrypt_found:
    StrCpy $VERACRYPT_FOUND "1"
  encryption_done:
!macroend

Function PagePrerequisites
  nsDialogs::Create 1018
  Pop $0

  ${NSD_CreateLabel} 0 0 100% 20u "Verification des prerequis systeme..."
  Pop $0

  StrCpy $PREREQ_ERRORS ""
  StrCpy $PREREQ_WARNINGS ""
  !insertmacro CheckPrerequisites

  ; Afficher le resultat
  StrCmp $PREREQ_ERRORS "" no_errors
    ; Erreurs bloquantes
    ${NSD_CreateLabel} 0 30u 100% 100u "ERREUR - Prerequis non satisfaits :$\n$PREREQ_ERRORS$\n$\nL installation ne peut pas continuer."
    Goto show_done
  no_errors:
    ; Combiner les avertissements
    StrCpy $0 "$PREREQ_WARNINGS$SOFTWARE_WARNINGS"
    StrCmp $0 "" all_ok
      ; Avertissements (chiffrement, cloud, logiciels manquants)
      ${NSD_CreateLabel} 0 30u 100% 60u "Prerequis materiels satisfaits :$\n$\nCPU : $CPU_CORES coeurs$\nRAM : $RAM_GB Go$\nDisque libre : $DISK_FREE_GB Go$\n$\nATTENTION :$PREREQ_WARNINGS$SOFTWARE_WARNINGS"
      Pop $0
      ${NSD_CreateCheckBox} 0 100u 100% 20u "J accepte de continuer malgre les avertissements"
      Pop $ACCEPT_NO_ENCRYPT
      Goto show_done
  all_ok:
    ${NSD_CreateLabel} 0 30u 100% 80u "OK - Tous les prerequis sont satisfaits.$\n$\nCPU : $CPU_CORES coeurs$\nRAM : $RAM_GB Go$\nDisque libre : $DISK_FREE_GB Go$\nChiffrement : Actif$\nGoogle Chrome : Installe"
  show_done:
  Pop $0

  nsDialogs::Show
FunctionEnd

Function PagePrerequisitesLeave
  ; Bloquer si erreurs critiques (CPU, RAM, disque)
  StrCmp $PREREQ_ERRORS "" no_block
    Abort
  no_block:
  ; Si avertissements (chiffrement, cloud, logiciels), verifier la checkbox
  StrCpy $0 "$PREREQ_WARNINGS$SOFTWARE_WARNINGS"
  StrCmp $0 "" done
    ${NSD_GetState} $ACCEPT_NO_ENCRYPT $0
    ${If} $0 == ${BST_UNCHECKED}
      MessageBox MB_OK "Vous devez accepter les avertissements pour poursuivre l installation.$\n$\nIl est fortement recommande d installer les logiciels manquants avant de continuer."
      Abort
    ${EndIf}
  done:
FunctionEnd

; ── Section principale : Installation ─────────────────────

Section "Installation Judi-Expert" SecMain
  SetOutPath "$INSTDIR"

  ; ── Verifier si une installation precedente existe ──────
  IfFileExists "$INSTDIR\config\docker-compose.yml" 0 fresh_install

    ; Installation existante detectee - arreter les conteneurs
    DetailPrint "Installation precedente detectee. Arret des conteneurs..."
    nsExec::ExecToStack 'docker compose -f "$INSTDIR\config\docker-compose.yml" down'
    Pop $0
    DetailPrint "Conteneurs arretes."

    ; Sauvegarder les donnees utilisateur
    DetailPrint "Sauvegarde des donnees utilisateur..."
    CreateDirectory "$INSTDIR\_backup"
    CopyFiles /SILENT "$INSTDIR\config\.env" "$INSTDIR\_backup\.env"
    IfFileExists "$INSTDIR\data\*.*" 0 +2
      CopyFiles /SILENT "$INSTDIR\data\*.*" "$INSTDIR\_backup\data\"
    DetailPrint "Donnees utilisateur sauvegardees."

  fresh_install:

  ; Copier les fichiers de configuration
  SetOutPath "$INSTDIR\config"
  File "${STAGING_DIR}\config\default.env"
  File "${STAGING_DIR}\config\docker-compose.yml"
  File /nonfatal "${STAGING_DIR}\config\ollama-entrypoint.sh"

  ; Copier les scripts (Amorce + prérequis)
  SetOutPath "$INSTDIR\scripts"
  File "${STAGING_DIR}\scripts\amorce.bat"
  File "${STAGING_DIR}\scripts\amorce.sh"
  File "${STAGING_DIR}\scripts\prerequisites_check.py"

  ; Copier les images Docker (sauf Ollama — téléchargé au premier lancement)
  SetOutPath "$INSTDIR\docker-images"
  File /nonfatal "${STAGING_DIR}\docker-images\judi-web-backend.tar"
  File /nonfatal "${STAGING_DIR}\docker-images\judi-web-frontend.tar"
  File /nonfatal "${STAGING_DIR}\docker-images\judi-ocr.tar"
  File /nonfatal "${STAGING_DIR}\docker-images\qdrant_qdrant_latest.tar"
  ; Note: ollama/ollama:latest sera téléchargé automatiquement par docker pull au premier démarrage

  ; Renommer default.env en .env
  Rename "$INSTDIR\config\default.env" "$INSTDIR\config\.env"

  ; Restaurer les donnees utilisateur si backup existe
  IfFileExists "$INSTDIR\_backup\.env" 0 no_restore
    DetailPrint "Restauration des donnees utilisateur..."
    CopyFiles /SILENT "$INSTDIR\_backup\.env" "$INSTDIR\config\.env"
    IfFileExists "$INSTDIR\_backup\data\*.*" 0 +3
      CreateDirectory "$INSTDIR\data"
      CopyFiles /SILENT "$INSTDIR\_backup\data\*.*" "$INSTDIR\data\"
    RMDir /r "$INSTDIR\_backup"
    DetailPrint "Donnees utilisateur restaurees."
  no_restore:

  ; Installer Docker Desktop si non présent
  Call InstallDockerIfNeeded

  ; Charger les images Docker
  Call LoadDockerImages

  ; Créer le raccourci Bureau
  CreateShortCut "$DESKTOP\Judi-Expert.lnk" "$INSTDIR\scripts\amorce.bat" "" "$INSTDIR\scripts\amorce.bat" 0

  ; Créer l'entrée dans le menu Démarrer
  CreateDirectory "$SMPROGRAMS\Judi-Expert"
  CreateShortCut "$SMPROGRAMS\Judi-Expert\Judi-Expert.lnk" "$INSTDIR\scripts\amorce.bat"
  CreateShortCut "$SMPROGRAMS\Judi-Expert\Desinstaller.lnk" "$INSTDIR\uninstall.exe"

  ; Créer le désinstalleur
  WriteUninstaller "$INSTDIR\uninstall.exe"

  ; Écrire les clés de registre pour Ajout/Suppression de programmes
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\JudiExpert" "DisplayName" "Judi-Expert ${VERSION}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\JudiExpert" "UninstallString" "$INSTDIR\uninstall.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\JudiExpert" "DisplayVersion" "${VERSION}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\JudiExpert" "Publisher" "ITechSource"
SectionEnd

; ── Fonction : Installer Docker si nécessaire ─────────────

Function InstallDockerIfNeeded
  nsExec::ExecToStack 'where docker'
  Pop $0
  StrCmp $0 "0" docker_found

  ; Docker non trouvé — télécharger et installer Docker Desktop
  DetailPrint "Docker n est pas installe. Telechargement de Docker Desktop..."
  DetailPrint "Veuillez suivre les instructions de l installateur Docker Desktop."

  ; Télécharger Docker Desktop Installer via PowerShell
  nsExec::ExecToStack 'powershell -NoProfile -Command "Invoke-WebRequest -Uri ''https://desktop.docker.com/win/main/amd64/Docker%%20Desktop%%20Installer.exe'' -OutFile ''$TEMP\DockerDesktopInstaller.exe''"'
  Pop $0
  StrCmp $0 "0" +3
    DetailPrint "Echec du telechargement de Docker Desktop."
    DetailPrint "Veuillez installer Docker Desktop manuellement depuis https://www.docker.com/products/docker-desktop"
    Goto docker_done

  ; Lancer l'installateur Docker Desktop en mode silencieux
  ExecWait '"$TEMP\DockerDesktopInstaller.exe" install --quiet --accept-license'
  Delete "$TEMP\DockerDesktopInstaller.exe"

  DetailPrint "Docker Desktop installe. Un redemarrage peut etre necessaire."

  docker_found:
    DetailPrint "Docker est deja installe."

  docker_done:
FunctionEnd

; ── Fonction : Charger les images Docker ──────────────────

Function LoadDockerImages
  DetailPrint "Chargement des images Docker..."

  FindFirst $0 $1 "$INSTDIR\docker-images\*.tar"
  loop:
    StrCmp $1 "" done
    DetailPrint "  Chargement de $1..."
    nsExec::ExecToStack 'docker load -i "$INSTDIR\docker-images\$1"'
    Pop $2
    FindNext $0 $1
    Goto loop
  done:
  FindClose $0

  DetailPrint "Toutes les images Docker sont chargees."
FunctionEnd

; ── Page : Fin de l'installation ──────────────────────────

Function PageFinish
  nsDialogs::Create 1018
  Pop $0

  ${NSD_CreateLabel} 0 0 100% 30u "Installation de Judi-Expert ${VERSION} terminee !"
  Pop $0

  ${NSD_CreateLabel} 0 40u 100% 40u "Un raccourci Judi-Expert a ete cree sur votre Bureau.$\nDouble-cliquez dessus pour lancer l application."
  Pop $0

  ${NSD_CreateLabel} 0 90u 100% 30u "Services disponibles apres lancement :$\n  - Application : http://localhost:3000$\n  - API : http://localhost:8000"
  Pop $0

  nsDialogs::Show
FunctionEnd

; ── Section : Désinstallation ─────────────────────────────

Section "Uninstall"
  ; Arrêter les conteneurs Docker
  nsExec::ExecToStack 'docker compose -f "$INSTDIR\config\docker-compose.yml" down'

  ; Supprimer les fichiers
  RMDir /r "$INSTDIR\config"
  RMDir /r "$INSTDIR\scripts"
  RMDir /r "$INSTDIR\docker-images"
  Delete "$INSTDIR\uninstall.exe"
  RMDir "$INSTDIR"

  ; Supprimer les raccourcis
  Delete "$DESKTOP\Judi-Expert.lnk"
  RMDir /r "$SMPROGRAMS\Judi-Expert"

  ; Supprimer les clés de registre
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\JudiExpert"
SectionEnd
