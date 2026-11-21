# Демонстрация самовосстановления и независимости сервисов.
# Порт-форвард должен быть запущен в другом окне:
#   kubectl port-forward -n car-accounting svc/gateway 8082:80
# В третьем окне: kubectl get pods -n car-accounting -w
$B = "http://localhost:8082"
$NS = "car-accounting"

function Step($t) { Write-Host "`n=== $t ===" -ForegroundColor Cyan; Read-Host "Enter для запуска" | Out-Null }

# код ответа или текст ошибки (для проверки недоступных страниц)
function Code($url) {
    try { return (Invoke-WebRequest -UseBasicParsing $url -TimeoutSec 8).StatusCode }
    catch {
        if ($_.Exception.Response) { return [int]$_.Exception.Response.StatusCode }
        return "ERR"
    }
}

Step "Сценарий 1: удаление одного пода cars-service"
$p = kubectl get pods -n $NS -l app=cars-service -o name | Select-Object -First 1
kubectl delete -n $NS $p
Start-Sleep 5
kubectl get pods -n $NS -l app=cars-service

Step "Сценарий 2: падение контейнера (перезапуск kubelet, растёт RESTARTS)"
$pod = kubectl get pods -n $NS -l app=cars-service -o jsonpath="{.items[0].metadata.name}"
minikube ssh -- "sudo crictl ps --label io.kubernetes.pod.name=$pod -q | xargs sudo crictl stop"
Start-Sleep 5
kubectl get pods -n $NS -l app=cars-service

Step "Сценарий 3: удаление всех реплик owners-service"
kubectl delete pod -n $NS -l app=owners-service
Start-Sleep 15
kubectl get pods -n $NS -l app=owners-service

Step "Сценарий 4: масштабирование cars-service до 5 и обратно до 2"
kubectl scale deployment/cars-service -n $NS --replicas=5
Start-Sleep 8
kubectl get pods -n $NS -l app=cars-service
kubectl scale deployment/cars-service -n $NS --replicas=2

Step "Сценарий 5: пересоздание всех подов cars-service, данные сохраняются (PVC)"
$name = "Selfheal-" + (Get-Date -Format "HHmmss")
Invoke-WebRequest -UseBasicParsing -Method Post -Uri "$B/brands/create" -Body @{ name = $name } | Out-Null
Write-Host "Создана марка $name"
kubectl rollout restart deployment/cars-service -n $NS
kubectl rollout status deployment/cars-service -n $NS --timeout=120s
Start-Sleep 5
$page = (Invoke-WebRequest -UseBasicParsing "$B/brands/").Content
if ($page -match "<td>(\d+)</td><td>$([regex]::Escape($name))</td>") {
    Write-Host "Запись $name на месте после пересоздания подов" -ForegroundColor Green
    Invoke-WebRequest -UseBasicParsing -Method Post -Uri "$B/brands/$($Matches[1])/delete" | Out-Null
    Write-Host "Тестовая запись удалена"
} else {
    Write-Host "Запись $name потеряна" -ForegroundColor Red
}

Step "Сценарий 6: отказ owners-service целиком (остальной сайт продолжает работать)"
kubectl scale deployment/owners-service -n $NS --replicas=0
Start-Sleep 5
Write-Host "Страница автомобилей (cars-service): $(Code "$B/cars/")  <- должна быть 200, вместо имён владельцев #id"
Write-Host "Марки (cars-service):                $(Code "$B/brands/")  <- 200"
Write-Host "Страница владельцев (owners-service): $(Code "$B/owners/")  <- 502/503, сервис недоступен"
Write-Host "Откройте $B/cars/create и попробуйте сохранить автомобиль: будет сообщение 'Сервис владельцев недоступен'."
Read-Host "Enter, чтобы вернуть owners-service" | Out-Null
kubectl scale deployment/owners-service -n $NS --replicas=2
kubectl rollout status deployment/owners-service -n $NS --timeout=120s
Write-Host "Страница владельцев после восстановления: $(Code "$B/owners/")  <- 200" -ForegroundColor Green

Write-Host "`nСобытия:" -ForegroundColor Cyan
kubectl get events -n $NS --sort-by=.lastTimestamp | Select-Object -Last 20
