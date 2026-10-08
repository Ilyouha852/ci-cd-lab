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
