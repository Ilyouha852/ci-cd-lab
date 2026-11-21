"""cars-service: автомобили, марки, модели, техосмотры и страховые полисы.

Владельцев здесь нет: это зона ответственности owners-service. Автомобиль хранит
только owner_id, а существование владельца и его имя запрашиваются по HTTP
(clients.py). Если owners-service недоступен, сервис продолжает работать:
списки и карточки показывают "#id", а создание/изменение автомобиля отклоняется
с понятным сообщением.
"""
import socket
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import clients
from clients import OwnersUnavailable
from config import SECRET_KEY
from database import get_db, init_db

ENTITIES = {
    'brands': {'title': 'Марки', 'table': 'brands', 'columns': ['name'], 'labels': {'name': 'Название марки'}},
    'models': {'title': 'Модели тачек1', 'table': 'models', 'columns': ['brand_id', 'name'], 'labels': {'brand_id': 'Марка', 'name': 'Название модели'}},
    'cars': {'title': 'Наши тачки', 'table': 'cars', 'columns': ['owner_id', 'brand_id', 'model_id', 'registration_number', 'vin', 'production_year', 'color', 'mileage', 'status'], 'labels': {'owner_id': 'Владелец', 'brand_id': 'Марка', 'model_id': 'Модель', 'registration_number': 'Госномер', 'vin': 'VIN', 'production_year': 'Год выпуска', 'color': 'Цвет', 'mileage': 'Пробег', 'status': 'Статус'}},
    'inspections': {'title': 'Техосмотры', 'table': 'technical_inspections', 'columns': ['car_id', 'inspection_date', 'next_inspection_date', 'result', 'mileage', 'comment'], 'labels': {'car_id': 'Автомобиль', 'inspection_date': 'Дата', 'next_inspection_date': 'Следующий осмотр', 'result': 'Результат', 'mileage': 'Пробег', 'comment': 'Комментарий'}},
    'insurance': {'title': 'Страховые полисы', 'table': 'insurance_policies', 'columns': ['car_id', 'policy_number', 'insurance_company', 'start_date', 'end_date', 'insurance_type', 'cost'], 'labels': {'car_id': 'Автомобиль', 'policy_number': 'Номер полиса', 'insurance_company': 'Компания', 'start_date': 'Начало', 'end_date': 'Окончание', 'insurance_type': 'Тип', 'cost': 'Стоимость'}},
}

OWNERS_DOWN = 'Сервис владельцев недоступен, попробуйте позже.'


def options():
    """Варианты для выпадающих списков. Владельцы приходят из owners-service."""
    with get_db() as db:
        opts = {
            'brand_id': db.execute('SELECT id,name label FROM brands ORDER BY name').fetchall(),
            'model_id': db.execute("SELECT models.id,brands.name||' — '||models.name label FROM models JOIN brands ON brands.id=models.brand_id ORDER BY label").fetchall(),
            'car_id': db.execute('SELECT id,registration_number label FROM cars ORDER BY registration_number').fetchall(),
        }
    try:
        opts['owner_id'] = [{'id': o['id'], 'label': o['full_name']} for o in clients.list_owners()]
    except OwnersUnavailable:
        opts['owner_id'] = []
        flash(OWNERS_DOWN, 'error')
    return opts


def check_owner(raw_id):
    """Текст ошибки, если владельца нельзя использовать, иначе None.

    Заменяет внешний ключ cars.owner_id -> owners.id, которого между БД разных
    сервисов быть не может.
    """
    try:
        owner = clients.get_owner(raw_id)
    except ValueError:
        return 'Некорректный владелец.'
    except OwnersUnavailable:
        return OWNERS_DOWN
    return None if owner else 'Владелец не найден.'


def create_app(test_config=None):
    app = Flask(__name__)
    # отдельное имя cookie: на одном хосте (localhost) cookie сессии owners-service
    # не должна затирать cookie cars-service
    app.config.update(SECRET_KEY=SECRET_KEY, SESSION_COOKIE_NAME='cars_session')
    if test_config:
        app.config.update(test_config)

    @app.after_request
    def add_pod_header(resp):
        # имя пода/контейнера, обработавшего запрос (видна балансировка между репликами)
        resp.headers['X-Served-By'] = socket.gethostname()
        return resp

    @app.route('/health')
    def health():
        # liveness-проба: процесс жив, ничего внешнего не трогаем
        return jsonify(service='cars-service', status='ok', pod=socket.gethostname())

    @app.route('/ready')
    def ready():
        # readiness-проба: собственная БД доступна и схема создана.
        # owners-service намеренно НЕ проверяется: его сбой не должен выводить
        # из балансировки все реплики cars-service.
        try:
            db = get_db()
            try:
                db.execute('SELECT 1 FROM cars LIMIT 1')
            finally:
                db.close()
            return jsonify(status='ready')
        except Exception:
            return jsonify(status='db unavailable'), 503

    # ---------- REST API (для других сервисов) ----------
    @app.route('/api/cars')
    def api_cars():
        with get_db() as db:
            rows = db.execute('SELECT * FROM cars ORDER BY id').fetchall()
        return jsonify([dict(r) for r in rows])

    @app.route('/api/cars/count')
    def api_cars_count():
        """Сколько автомобилей у владельца: owners-service спрашивает перед удалением."""
        owner_id = request.args.get('owner_id', type=int)
        with get_db() as db:
            if owner_id is None:
                n = db.execute('SELECT COUNT(*) FROM cars').fetchone()[0]
            else:
                n = db.execute('SELECT COUNT(*) FROM cars WHERE owner_id=?', (owner_id,)).fetchone()[0]
        return jsonify(count=n)

    # ---------- веб-интерфейс ----------
    @app.route('/')
    def index():
        with get_db() as db:
            stats = {k: db.execute(q).fetchone()[0] for k, q in {
                'cars': 'SELECT COUNT(*) FROM cars',
                'active': "SELECT COUNT(*) FROM cars WHERE status='Активен'",
                'repair': "SELECT COUNT(*) FROM cars WHERE status='На ремонте'",
                'brands': 'SELECT COUNT(*) FROM brands',
                'inspections': 'SELECT COUNT(*) FROM technical_inspections',
            }.items()}
        try:
            stats['owners'] = clients.count_owners()
        except OwnersUnavailable:
            stats['owners'] = '—'
        stats = {k: stats[k] for k in ('cars', 'active', 'repair', 'owners', 'brands', 'inspections')}
        return render_template('index.html', stats=stats)

    @app.route('/<entity>/')
    def listing(entity):
        if entity not in ENTITIES:
            return ('Not found', 404)
        cfg = ENTITIES[entity]
        with get_db() as db:
            rows = db.execute(f"SELECT * FROM {cfg['table']} ORDER BY id DESC").fetchall()
        owner_names = {}
        if entity == 'cars':
            try:
                owner_names = {o['id']: o['full_name'] for o in clients.list_owners()}
            except OwnersUnavailable:
                flash(OWNERS_DOWN + ' Имена владельцев не показаны.', 'error')
        return render_template('list.html', cfg=cfg, entity=entity, rows=rows, owner_names=owner_names)

    @app.route('/<entity>/create', methods=['GET', 'POST'])
    def create(entity):
        if entity not in ENTITIES:
            return ('Not found', 404)
        cfg = ENTITIES[entity]
        if request.method == 'POST':
            vals = [request.form.get(c, '').strip() for c in cfg['columns']]
            error = check_owner(request.form.get('owner_id', '')) if entity == 'cars' else None
            if error:
                flash(error, 'error')
            else:
                with get_db() as db:
                    try:
                        db.execute(f"INSERT INTO {cfg['table']}({','.join(cfg['columns'])}) VALUES({','.join('?' * len(vals))})", vals)
                        db.commit()
                        flash('Запись добавлена.', 'success')
                        return redirect(url_for('listing', entity=entity))
                    except Exception as e:
                        flash(f'Ошибка: {e}', 'error')
        return render_template('form.html', cfg=cfg, entity=entity, row=None, options=options())

    @app.route('/<entity>/<int:item_id>/edit', methods=['GET', 'POST'])
    def edit(entity, item_id):
        if entity not in ENTITIES:
            return ('Not found', 404)
        cfg = ENTITIES[entity]
        with get_db() as db:
            row = db.execute(f'SELECT * FROM {cfg["table"]} WHERE id=?', (item_id,)).fetchone()
            if not row:
                return ('Not found', 404)
            if request.method == 'POST':
                vals = [request.form.get(c, '').strip() for c in cfg['columns']]
                error = check_owner(request.form.get('owner_id', '')) if entity == 'cars' else None
                if error:
                    flash(error, 'error')
                else:
                    try:
                        setters = ','.join(f'{c}=?' for c in cfg['columns'])
                        db.execute(f'UPDATE {cfg["table"]} SET {setters} WHERE id=?', vals + [item_id])
                        db.commit()
                        flash('Запись обновлена.', 'success')
                        return redirect(url_for('listing', entity=entity))
                    except Exception as e:
                        flash(f'Ошибка: {e}', 'error')
        return render_template('form.html', cfg=cfg, entity=entity, row=row, options=options())

    @app.post('/<entity>/<int:item_id>/delete')
    def delete(entity, item_id):
        if entity not in ENTITIES:
            return ('Not found', 404)
        with get_db() as db:
            try:
                db.execute(f'DELETE FROM {ENTITIES[entity]["table"]} WHERE id=?', (item_id,))
                db.commit()
                flash('Запись удалена.', 'success')
            except Exception as e:
                flash(f'Удаление невозможно: {e}', 'error')
        return redirect(url_for('listing', entity=entity))

    @app.route('/cars/<int:item_id>')
    def car_detail(item_id):
        with get_db() as db:
            car = db.execute("SELECT cars.*,brands.name brand_name,models.name model_name FROM cars JOIN brands ON brands.id=cars.brand_id JOIN models ON models.id=cars.model_id WHERE cars.id=?", (item_id,)).fetchone()
            if not car:
                return ('Not found', 404)
            inspections = db.execute('SELECT * FROM technical_inspections WHERE car_id=?', (item_id,)).fetchall()
            policies = db.execute('SELECT * FROM insurance_policies WHERE car_id=?', (item_id,)).fetchall()
        try:
            owner = clients.get_owner(car['owner_id'])
            owner_name = owner['full_name'] if owner else f"владелец #{car['owner_id']} не найден"
        except OwnersUnavailable:
            owner_name = f"#{car['owner_id']} (сервис владельцев недоступен)"
        return render_template('car_detail.html', car=car, owner_name=owner_name, inspections=inspections, policies=policies)

    return app


app = create_app()

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
