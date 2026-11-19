# Демонстрация самовосстановления. Порт-форвард должен быть запущен в другом окне:
#   kubectl port-forward -n car-accounting svc/gateway 8082:80
# В третьем окне: kubectl get pods -n car-accounting -w
$B = "http://localhost:8082"
$NS = "car-accounting"

function Step($t) { Write-Host "`n=== $t ===" -ForegroundColor Cyan; Read-Host "Enter для запуска" | Out-Null }

Step "Сценарий 1: удаление одного пода car-app"
$p = kubectl get pods -n $NS -l app=car-app -o name | Select-Object -First 1
kubectl delete -n $NS $p
Start-Sleep 5
kubectl get pods -n $NS -l app=car-app

Step "Сценарий 2: падение контейнера (перезапуск kubelet, растёт RESTARTS)"
$pod = kubectl get pods -n $NS -l app=car-app -o jsonpath="{.items[0].metadata.name}"
minikube ssh -- "sudo crictl ps --label io.kubernetes.pod.name=$pod -q | xargs sudo crictl stop"
Start-Sleep 5
kubectl get pods -n $NS -l app=car-app

Step "Сценарий 3: удаление всех реплик car-app"
kubectl delete pod -n $NS -l app=car-app
Start-Sleep 15
kubectl get pods -n $NS -l app=car-app

Step "Сценарий 4: масштабирование до 5 и обратно до 2"
kubectl scale deployment/car-app -n $NS --replicas=5
Start-Sleep 8
kubectl get pods -n $NS -l app=car-app
kubectl scale deployment/car-app -n $NS --replicas=2

Step "Сценарий 5: пересоздание всех подов, данные сохраняются (PVC)"
$name = "Selfheal-" + (Get-Date -Format "HHmmss")
Invoke-WebRequest -UseBasicParsing -Method Post -Uri "$B/brands/create" -Body @{ name = $name } | Out-Null
Write-Host "Создана марка $name"
kubectl rollout restart deployment/car-app -n $NS
kubectl rollout status deployment/car-app -n $NS --timeout=120s
Start-Sleep 5
$page = (Invoke-WebRequest -UseBasicParsing "$B/brands/").Content
if ($page -match "<td>(\d+)</td><td>$([regex]::Escape($name))</td>") {
    Write-Host "Запись $name на месте после пересоздания подов" -ForegroundColor Green
    Invoke-WebRequest -UseBasicParsing -Method Post -Uri "$B/brands/$($Matches[1])/delete" | Out-Null
    Write-Host "Тестовая запись удалена"
} else {
    Write-Host "Запись $name потеряна" -ForegroundColor Red
}

Write-Host "`nСобытия:" -ForegroundColor Cyan
kubectl get events -n $NS --sort-by=.lastTimestamp | Select-Object -Last 20
