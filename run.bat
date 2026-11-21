@echo off
rem Локальный запуск без Docker: два сервиса в отдельных окнах.
rem cars-service: http://127.0.0.1:5000/   owners-service: http://127.0.0.1:5001/owners/
if not exist .venv py -m venv .venv
call .venv\Scripts\activate
py -m pip install -r cars-service\requirements.txt

start "owners-service" cmd /k "cd owners-service && ..\.venv\Scripts\python app.py"
start "cars-service" cmd /k "cd cars-service && ..\.venv\Scripts\python app.py"
