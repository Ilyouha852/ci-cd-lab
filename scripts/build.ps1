# Сборка образов трёх компонентов и загрузка их в minikube.
# Использование: .\scripts\build.ps1 [-Tag v1]
param([string]$Tag = "v1")
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

# имя образа = имя папки с его Dockerfile
$components = "cars-service", "owners-service", "gateway"

foreach ($c in $components) {
    docker build -t "car-accounting/${c}:$Tag" $c
    if ($LASTEXITCODE -ne 0) { throw "build of $c failed" }
}

foreach ($c in $components) {
    $img = "car-accounting/${c}:$Tag"
    minikube image load $img
    if ($LASTEXITCODE -ne 0) { throw "image load of $img failed" }
}
Write-Host "Images built and loaded into minikube with tag $Tag"

Write-Host "whoami: $(whoami)"
Write-Host "MINIKUBE_HOME: $env:MINIKUBE_HOME"
Write-Host "minikube: $((Get-Command minikube).Source)"
minikube profile list
$loaded = minikube image ls
foreach ($c in $components) {
    if (-not ($loaded | Select-String "car-accounting/${c}:$Tag")) {
        throw "image ${c}:$Tag not found in minikube after load"
    }
}
