# Сборка образов и загрузка их в minikube.
# Использование: .\scripts\build.ps1 [-Tag v1]
param([string]$Tag = "v1")
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

docker build -t "car-accounting/app:$Tag" .
if ($LASTEXITCODE -ne 0) { throw "build of app failed" }
docker build -t "car-accounting/gateway:$Tag" gateway
if ($LASTEXITCODE -ne 0) { throw "build of gateway failed" }

foreach ($i in "car-accounting/app:$Tag", "car-accounting/gateway:$Tag") {
    minikube image load $i
    if ($LASTEXITCODE -ne 0) { throw "image load of $i failed" }
}
Write-Host "Images built and loaded into minikube with tag $Tag"

Write-Host "whoami: $(whoami)"
Write-Host "MINIKUBE_HOME: $env:MINIKUBE_HOME"
Write-Host "minikube: $((Get-Command minikube).Source)"
minikube profile list
$found = minikube image ls | Select-String "car-accounting/app:$Tag"
if (-not $found) { throw "image app:$Tag not found in minikube after load" }
