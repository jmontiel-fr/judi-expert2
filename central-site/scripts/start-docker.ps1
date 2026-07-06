# Redemarre Docker Desktop et attend que le moteur reponde
Write-Host "Arret Docker Desktop..."
Stop-Process -Name "Docker Desktop", "com.docker.backend", "com.docker.build" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3

Write-Host "Termination WSL docker-desktop..."
wsl --terminate docker-desktop 2>$null
Start-Sleep -Seconds 2

Write-Host "Relance Docker Desktop..."
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"

$docker = "C:\Program Files\Docker\Docker\resources\bin\docker.exe"
Write-Host "Attente moteur (max 120s)..."

for ($i = 1; $i -le 30; $i++) {
    $job = Start-Job -ScriptBlock {
        param($d)
        & $d info 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) { "ok" } else { "fail" }
    } -ArgumentList $docker

    if (Wait-Job $job -Timeout 4) {
        $result = Receive-Job $job
        Remove-Job $job -Force
        if ($result -eq "ok") {
            Write-Host "Docker pret en $($i * 4)s"
            & $docker version
            exit 0
        }
    } else {
        Stop-Job $job -Force -ErrorAction SilentlyContinue
        Remove-Job $job -Force -ErrorAction SilentlyContinue
    }

    if ($i % 5 -eq 0) { Write-Host "... $($i * 4)s" }
    Start-Sleep -Seconds 4
}

Write-Host "ECHEC: Docker ne repond pas. Ouvrez Docker Desktop manuellement et attendez 'Engine running'."
Get-Service com.docker.service -ErrorAction SilentlyContinue | Format-List Name, Status
exit 1
