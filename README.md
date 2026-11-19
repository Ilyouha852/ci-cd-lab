# Система учёта автомобилей

Учебное Flask + SQLite веб-приложение для лабораторной работы по CI/CD.

## Функциональность

Шесть CRUD-модулей: автомобили, владельцы, марки, модели, технические осмотры и страховые полисы. Это 24 базовые CRUD-операции.

## Запуск Windows

```powershell
py -m venv .venv
.venv\\Scripts\\activate
py -m pip install -r requirements.txt
py app.py
```

Открыть http://127.0.0.1:5000

## Тесты

```powershell
py -m pytest -v
```

## Jenkins

Pipeline находится в `Jenkinsfile`: GitHub push → Webhook → Jenkins → Checkout → Build → Test → Deploy.

Для Linux команды `bat` в Jenkinsfile нужно заменить на `sh`.

## База данных

При первом запуске автоматически создаются `database/cars.db` и демонстрационные данные из `database/seed.sql`.

## Kubernetes

Приложение можно развернуть в однонодовом кластере Kubernetes (minikube). Манифесты лежат в `k8s/`, скрипты — в `scripts/` (PowerShell, Windows).

### Архитектура

```
браузер ── NodePort 30090 ──► gateway (nginx, 2 пода) ──► Service car-app :80 ──► car-app (Flask + gunicorn, 2 пода)
                                                                                     │
                                                          Job db-init (схема + seed) ─┴─► PVC cars-data (SQLite /data/cars.db)
```

| Файл | Что создаёт |
|------|-------------|
| `k8s/00-namespace.yaml` | namespace `car-accounting`, Secret `app-secret` (`SECRET_KEY`) |
| `k8s/01-storage.yaml` | PVC `cars-data` (1 ГБ) под файл SQLite |
| `k8s/10-db-init.yaml` | Job `db-init`: создаёт схему и демо-данные один раз (идемпотентно) |
| `k8s/20-app.yaml` | Deployment `car-app` (2 реплики, readiness `/ready`, liveness `/health`, RollingUpdate без простоя) и Service ClusterIP |
| `k8s/30-gateway.yaml` | Deployment `gateway` (nginx, 2 реплики) и Service NodePort `30090` |
| `gateway/` | Dockerfile и конфиг nginx для gateway (в Compose по-прежнему используется `nginx/nginx.conf`) |

Приложение получило служебные эндпоинты для проб: `/health` (процесс жив), `/ready` (БД доступна и схема создана) и заголовок `X-Served-By` с именем пода.

### Запуск

```powershell
# 1. кластер (один раз)
minikube start --driver=docker --cpus=2 --memory=3072

# 2. сборка образов и загрузка в minikube
.\scripts\build.ps1 -Tag v1

# 3. развёртывание
.\scripts\deploy.ps1 -Tag v1

# 4. проверка
kubectl get all -n car-accounting
kubectl port-forward -n car-accounting svc/gateway 8082:80      # сайт: http://localhost:8082/
# либо без port-forward:  minikube service gateway -n car-accounting --url
```

Порты выбраны так, чтобы проект не конфликтовал с «Библиотекой» в одном minikube (у неё NodePort `30080` и port-forward `8081`).

### Проверка работоспособности

```powershell
.\scripts\smoke.ps1       # port-forward + smoke-тесты (smoke_tests/), отчёт в reports/results.xml
```

Smoke-тест идёт через gateway и проверяет пробы, страницы всех разделов, CRUD владельца, сквозной сценарий «марка → модель → владелец → автомобиль → техосмотр → полис» с каскадным удалением, запрет удаления связанных записей и балансировку между репликами. Без переменной `BASE_URL` тесты пропускаются, поэтому обычный `pytest` в корне проекта кластер не трогает.

Балансировка между подами приложения (порт-форвард привязывается к одному поду gateway, но поды `car-app` чередуются):

```powershell
1..12 | ForEach-Object { (Invoke-WebRequest -UseBasicParsing http://localhost:8082/health).Headers["X-Served-By"] }
```

### Стресс-тест и самовосстановление

```powershell
# окно 1: kubectl port-forward -n car-accounting svc/gateway 8082:80
# окно 2: kubectl get pods -n car-accounting -w
# окно 3: непрерывная нагрузка (код ответа или ERR)
while ($true) {
    try { (Invoke-WebRequest -UseBasicParsing http://localhost:8082/cars/ -TimeoutSec 3).StatusCode } catch { "ERR" }
    Start-Sleep -Milliseconds 300
}
# окно 4: перезапуск подов приложения во время нагрузки (ошибок быть не должно)
kubectl rollout restart deployment/car-app -n car-accounting
```

Во время теста перезапускайте `car-app`, а не `gateway`: port-forward привязан к конкретному поду gateway.

Готовый пошаговый сценарий (удаление пода, падение контейнера, удаление всех реплик, масштабирование, сохранность данных на PVC):

```powershell
.\scripts\demo-selfheal.ps1
```

### Ограничения

- База — SQLite на одном PVC, поэтому обе реплики `car-app` работают с одним файлом. Это корректно только в однонодовом кластере (minikube): все поды на одном узле и делят блокировки файла. Для многонодового кластера и настоящей отказоустойчивости БД нужно вынести в клиент-серверную СУБД (например, PostgreSQL как StatefulSet, как в «Библиотеке»).
- Секрет `SECRET_KEY` лежит в манифесте открытым текстом — допустимо только для учебного стенда.

### Jenkins

В ветке `main` после деплоя через Docker Compose выполняются стадии `Build images for Kubernetes` → `Deploy to Kubernetes` → `Smoke test (Kubernetes)` (результаты публикуются через `junit`). На агенте должны быть установлены `minikube` и `kubectl`, кластер запущен (`minikube start`), у пользователя службы Jenkins доступен kubeconfig. Остальные ветки Kubernetes не затрагивают.

### Удаление

```powershell
kubectl delete namespace car-accounting     # удалит и PVC с данными
```
