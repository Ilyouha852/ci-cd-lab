# Развёртывание в Kubernetes.
# Использование: .\scripts\deploy.ps1 [-Tag v1]
param([string]$Tag = "v1")
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$ns = "car-accounting"

kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/01-storage.yaml

# Job нельзя обновить на месте: удаляем прошлый запуск и создаём новый.
kubectl delete job db-init -n $ns --ignore-not-found
(Get-Content k8s/10-db-init.yaml -Raw -Encoding UTF8).Replace("__TAG__", $Tag) | kubectl apply -f -
kubectl wait --for=condition=complete job/db-init -n $ns --timeout=180s
if ($LASTEXITCODE -ne 0) {
    kubectl logs job/db-init -n $ns
    throw "db-init job failed"
}

(Get-Content k8s/20-app.yaml -Raw -Encoding UTF8).Replace("__TAG__", $Tag) | kubectl apply -f -
(Get-Content k8s/30-gateway.yaml -Raw -Encoding UTF8).Replace("__TAG__", $Tag) | kubectl apply -f -

foreach ($d in "car-app", "gateway") {
    kubectl rollout status deployment/$d -n $ns --timeout=180s
    if ($LASTEXITCODE -ne 0) { throw "rollout of $d failed" }
}
kubectl get all -n $ns
