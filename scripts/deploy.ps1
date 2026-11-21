# Развёртывание в Kubernetes: два сервиса (cars-service, owners-service) и gateway.
# Использование: .\scripts\deploy.ps1 [-Tag v1]
param([string]$Tag = "v1")
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$ns = "car-accounting"

function Apply-Tagged($file) {
    (Get-Content $file -Raw -Encoding UTF8).Replace("__TAG__", $Tag) | kubectl apply -f -
    if ($LASTEXITCODE -ne 0) { throw "kubectl apply $file failed" }
}

kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/01-storage.yaml

# Остатки монолитной версии (если она была развёрнута раньше): Deployment/Service car-app
# и общий Job db-init. Если их нет, команды ничего не делают.
kubectl delete deployment car-app -n $ns --ignore-not-found
kubectl delete service car-app -n $ns --ignore-not-found
kubectl delete job db-init -n $ns --ignore-not-found

# Job нельзя обновить на месте: удаляем прошлые запуски и создаём новые.
kubectl delete job db-init-cars db-init-owners -n $ns --ignore-not-found
Apply-Tagged k8s/10-db-init.yaml
foreach ($j in "db-init-cars", "db-init-owners") {
    kubectl wait --for=condition=complete job/$j -n $ns --timeout=180s
    if ($LASTEXITCODE -ne 0) {
        kubectl logs job/$j -n $ns
        throw "$j job failed"
    }
}

# Сервисы создаются до gateway: nginx резолвит их имена при старте.
Apply-Tagged k8s/20-owners.yaml
Apply-Tagged k8s/21-cars.yaml
Apply-Tagged k8s/30-gateway.yaml

foreach ($d in "owners-service", "cars-service", "gateway") {
    kubectl rollout status deployment/$d -n $ns --timeout=180s
    if ($LASTEXITCODE -ne 0) { throw "rollout of $d failed" }
}
kubectl get all -n $ns
