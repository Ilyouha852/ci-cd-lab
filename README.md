# Система учёта автомобилей

Учебное веб-приложение для лабораторной работы по контейнеризации и CI/CD.
Построено как два микросервиса со своими базами данных и общим gateway.

## Архитектура

```
                          ┌──► owners-service  (Flask, SQLite owners_service.db)  ── владельцы
браузер ──► gateway ──────┤        ▲   │
            (nginx)       │        │   │ GET /api/cars/count?owner_id=N
                          └──► cars-service    (Flask, SQLite cars_service.db)    ── автомобили, марки,
                                   │ GET /api/owners, /api/owners/<id>               модели, техосмотры, полисы
                                   └─────► owners-service
```

| Компонент | Отвечает за | Своя БД | Образ |
|-----------|-------------|---------|-------|
| `owners-service` | владельцы (CRUD, веб-интерфейс `/owners/`, REST `/api/owners`) | `owners_service.db`, том `owners_data` | `car-accounting-owners-service` |
| `cars-service` | автомобили, марки, модели, техосмотры, страховые полисы, главная страница, REST `/api/cars` | `cars_service.db`, том `cars_data` | `car-accounting-cars-service` |
| `gateway` | единая точка входа: `/owners/` и `/api/owners` → owners-service, остальное → cars-service | нет | `car-accounting-gateway` |

Каждый сервис собирается из своей папки (`cars-service/`, `owners-service/`), имеет свой `Dockerfile`, `requirements.txt`, шаблоны, статику и тесты. Папки намеренно не делят код: общий `base.html` и `style.css` скопированы в оба сервиса.

### Как сервисы взаимодействуют

Между БД разных сервисов нет внешних ключей, поэтому то, что раньше делали `FOREIGN KEY`, теперь делают HTTP-запросы:

| Ситуация | Что происходит |
|----------|----------------|
| Создание/изменение автомобиля | cars-service запрашивает `GET /api/owners/<id>` у owners-service: нет такого владельца, запись отклоняется |
| Форма автомобиля, список, карточка, главная | имена владельцев и их число приходят из owners-service (`/api/owners`, `/api/owners/count`) |
| Удаление владельца | owners-service запрашивает `GET /api/cars/count?owner_id=N` у cars-service: если у владельца есть автомобили, удаление отклоняется |

Отказоустойчивость (проверяется тестами и скриптом `scripts/demo-selfheal.ps1`):

- **owners-service недоступен:** cars-service продолжает работать. Списки и карточки показывают `#id` вместо имени владельца, марки, модели, техосмотры и полисы доступны, а создание автомобиля отклоняется сообщением «Сервис владельцев недоступен».
- **cars-service недоступен:** owners-service продолжает работать, но удаление владельца отклоняется (проверить наличие машин нельзя).
- Пробы `/ready` проверяют только собственную БД сервиса. Сбой соседа не выводит сервис из балансировки.
- Вызовы между сервисами идут с таймаутом 2 секунды (`OWNERS_TIMEOUT`, `CARS_TIMEOUT`).

### Адреса сервисов

| Переменная | Где используется | В Compose / Kubernetes | Локально |
|------------|------------------|------------------------|----------|
| `OWNERS_SERVICE_URL` | cars-service | `http://owners-service:5000` | `http://localhost:5001` |
| `CARS_SERVICE_URL` | owners-service | `http://cars-service:5000` | `http://localhost:5000` |
| `DATABASE_PATH` | оба | `/data/cars_service.db`, `/data/owners_service.db` | `database/*.db` в папке сервиса |
| `SECRET_KEY` | оба | из `compose.yaml` / Secret `app-secret` | значение по умолчанию |

Cookie сессий у сервисов называются по-разному (`cars_session`, `owners_session`), чтобы они не затирали друг друга на одном хосте.

## Запуск без Docker (Windows)

```powershell
.\run.bat
```

Откроются два окна: cars-service на http://127.0.0.1:5000/ и owners-service на http://127.0.0.1:5001/owners/. При первом запуске создаются базы и демо-данные из `database/seed.sql` каждого сервиса (демо-автомобили ссылаются на владельцев 1-3).

## Тесты

Модули в сервисах называются одинаково (`app.py`, `database.py`, `config.py`), поэтому тесты каждого сервиса запускаются отдельно, из его папки:

```powershell
cd cars-service;   py -m pytest tests -v; cd ..
cd owners-service; py -m pytest tests -v; cd ..
```

Обращения к соседнему сервису в юнит-тестах подменяются, сеть не нужна.

## Docker Compose

```powershell
docker compose up -d --build        # http://localhost/
docker compose down                 # данные сохраняются (тома cars_data, owners_data)
```

Три контейнера: `cars-service`, `owners-service`, `gateway` (порт 80). Gateway автоматически перезапускается при пересоздании любого из сервисов (`depends_on ... restart: true`), чтобы заново найти его адрес.

Тома `cars_data` и `owners_data` отдельные: у каждого сервиса своя база. При обновлении с монолитной версии старый файл `cars.db` в томе `cars_data` не используется (новые файлы называются `cars_service.db` и `owners_service.db`), данные начинаются с демо-набора.

## Образы на Docker Hub

Имена образов: `${IMAGE_REPO}-cars-service`, `${IMAGE_REPO}-owners-service`, `${IMAGE_REPO}-gateway`; для `IMAGE_REPO=benjohnson1229/car-accounting` это репозитории `car-accounting-cars-service`, `car-accounting-owners-service`, `car-accounting-gateway`. Теги: номер сборки Jenkins и `latest`.

Вручную:

```powershell
$env:IMAGE_REPO = "ваш_логин/car-accounting"; $env:IMAGE_TAG = "1"
docker compose build
docker login
docker compose push
```

## Jenkins

Pipeline находится в `Jenkinsfile` (в настройках Multibranch Pipeline: Script Path = `Jenkinsfile`): GitHub push → Webhook (smee) → Jenkins → Checkout → тесты каждого сервиса → Build → Deploy.

- Любая ветка, кроме `main`: тесты, проверка Compose, пробная сборка трёх образов (`car-accounting-ci/...`). Деплоя нет.
- `main`: то же, затем `Deploy with Docker Compose`: `docker login` (креды `dockerhub-credentials`), `docker compose build`, `push` трёх образов (тег = номер сборки и `latest`), `docker compose up -d --remove-orphans`, проверка, что отвечают и `http://localhost/` (cars-service), и `http://localhost/owners/` (owners-service). Затем сборка образов для Kubernetes, деплой и smoke-тест.

Для Linux-агента команды `bat` в Jenkinsfile нужно заменить на `sh`.

## Kubernetes (minikube)

Манифесты лежат в `k8s/`, скрипты в `scripts/` (PowerShell, Windows).

| Файл | Что создаёт |
|------|-------------|
| `k8s/00-namespace.yaml` | namespace `car-accounting`, Secret `app-secret` (`SECRET_KEY`) |
| `k8s/01-storage.yaml` | PVC `cars-data` и `owners-data` (по 1 ГБ): по тому на каждый сервис |
| `k8s/10-db-init.yaml` | Jobs `db-init-cars` и `db-init-owners`: схема и демо-данные (идемпотентно) |
| `k8s/20-owners.yaml` | Deployment `owners-service` (2 реплики, проба `/ready`, `/health`, RollingUpdate без простоя) и Service `owners-service:5000` |
| `k8s/21-cars.yaml` | то же для `cars-service` |
| `k8s/30-gateway.yaml` | Deployment `gateway` (2 реплики) и Service NodePort `30090` |

```powershell
minikube start --driver=docker --cpus=2 --memory=3072   # кластер (один раз)
.\scripts\build.ps1 -Tag v1                              # сборка трёх образов и загрузка в minikube
.\scripts\deploy.ps1 -Tag v1                             # развёртывание
kubectl get all -n car-accounting
kubectl port-forward -n car-accounting svc/gateway 8082:80      # сайт: http://localhost:8082/
```

`deploy.ps1` также удаляет Deployment/Service `car-app` и Job `db-init` монолитной версии, если они остались в кластере.

### Проверка

```powershell
.\scripts\smoke.ps1       # port-forward + smoke-тесты (smoke_tests/), отчёт reports/results.xml
```

Smoke-тест идёт через gateway и проверяет: пробы, страницы всех разделов, CRUD владельца, сквозной сценарий «марка → модель → владелец → автомобиль → техосмотр → полис», отказ в автомобиле с несуществующим владельцем, запрет удаления владельца с автомобилями (проверка между сервисами), балансировку между репликами каждого сервиса. Без `BASE_URL` тесты пропускаются, обычный `pytest` кластер не трогает.

Балансировка (имя пода в заголовке `X-Served-By`):

```powershell
1..12 | ForEach-Object { (Invoke-WebRequest -UseBasicParsing http://localhost:8082/health).Headers["X-Served-By"] }               # cars-service
1..12 | ForEach-Object { (Invoke-WebRequest -UseBasicParsing http://localhost:8082/api/owners/count).Headers["X-Served-By"] }     # owners-service
```

### Самовосстановление и независимость сервисов

```powershell
.\scripts\demo-selfheal.ps1
```

Пошаговый сценарий: удаление пода, падение контейнера, удаление всех реплик, масштабирование, сохранность данных на PVC и **отказ owners-service целиком**: остальной сайт продолжает работать.

### Ограничения

- База каждого сервиса, SQLite на одном PVC, а обе реплики сервиса работают с одним файлом. Это корректно только в однонодовом кластере (minikube). Для многонодового кластера и настоящей отказоустойчивости нужна клиент-серверная СУБД (например, PostgreSQL как StatefulSet на каждый сервис).
- Секрет `SECRET_KEY` лежит в манифесте открытым текстом: допустимо только для учебного стенда.
- Внешних ключей между сервисами нет: если сервис владельцев удалит запись в обход проверки (например, прямым доступом к БД), автомобиль останется с «висячим» `owner_id`. Целостность поддерживается только через API.

### Удаление

```powershell
kubectl delete namespace car-accounting     # удалит и PVC с данными
```
