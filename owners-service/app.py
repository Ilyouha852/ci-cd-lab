"""owners-service: владельцы автомобилей.

Своя БД, свой веб-интерфейс (/owners/) и REST API (/api/owners), которым
пользуется cars-service. Единственная обратная зависимость: перед удалением
владельца спрашиваем cars-service, нет ли у него автомобилей. Если cars-service
недоступен, удаление отклоняется (безопаснее, чем оставить "осиротевшие" машины).
"""
import socket
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import clients
from clients import CarsUnavailable
from config import SECRET_KEY
from database import get_db, init_db

COLUMNS = ['full_name', 'phone', 'email', 'address']
LABELS = {'full_name': 'ФИО', 'phone': 'Телефон', 'email': 'Email', 'address': 'Адрес'}


def create_app(test_config=None):
    app = Flask(__name__)
    # отдельное имя cookie: на одном хосте (localhost) cookie сессии cars-service
    # не должна затирать cookie owners-service
    app.config.update(SECRET_KEY=SECRET_KEY, SESSION_COOKIE_NAME='owners_session')
    if test_config:
        app.config.update(test_config)

    @app.after_request
    def add_pod_header(resp):
        resp.headers['X-Served-By'] = socket.gethostname()
        return resp

    @app.route('/health')
    def health():
        return jsonify(service='owners-service', status='ok', pod=socket.gethostname())

    @app.route('/ready')
    def ready():
        # только собственная БД; cars-service не проверяем (см. cars-service/app.py)
        try:
            db = get_db()
            try:
                db.execute('SELECT 1 FROM owners LIMIT 1')
            finally:
                db.close()
            return jsonify(status='ready')
        except Exception:
            return jsonify(status='db unavailable'), 503

    # ---------- REST API ----------
    @app.route('/api/owners')
    def api_list():
        with get_db() as db:
            rows = db.execute('SELECT * FROM owners ORDER BY full_name').fetchall()
        return jsonify([dict(r) for r in rows])

    @app.route('/api/owners/count')
    def api_count():
        with get_db() as db:
            n = db.execute('SELECT COUNT(*) FROM owners').fetchone()[0]
        return jsonify(count=n)

    @app.route('/api/owners/<int:owner_id>')
    def api_get(owner_id):
        with get_db() as db:
            row = db.execute('SELECT * FROM owners WHERE id=?', (owner_id,)).fetchone()
        if not row:
            return jsonify(error='owner not found'), 404
        return jsonify(dict(row))

    # ---------- веб-интерфейс ----------
    @app.route('/')
    def index():
        return redirect(url_for('listing'))

    @app.route('/owners/')
    def listing():
        with get_db() as db:
            rows = db.execute('SELECT * FROM owners ORDER BY id DESC').fetchall()
        return render_template('owners.html', columns=COLUMNS, labels=LABELS, rows=rows)

    def read_form():
        return [request.form.get(c, '').strip() for c in COLUMNS]

    @app.route('/owners/create', methods=['GET', 'POST'])
    def create():
        if request.method == 'POST':
            vals = read_form()
            if not vals[0]:
                flash('Укажите ФИО.', 'error')
            else:
                with get_db() as db:
                    db.execute(f"INSERT INTO owners({','.join(COLUMNS)}) VALUES(?,?,?,?)", vals)
                    db.commit()
                flash('Запись добавлена.', 'success')
                return redirect(url_for('listing'))
        return render_template('owner_form.html', row=None, labels=LABELS)

    @app.route('/owners/<int:owner_id>/edit', methods=['GET', 'POST'])
    def edit(owner_id):
        with get_db() as db:
            row = db.execute('SELECT * FROM owners WHERE id=?', (owner_id,)).fetchone()
            if not row:
                return ('Not found', 404)
            if request.method == 'POST':
                vals = read_form()
                if not vals[0]:
                    flash('Укажите ФИО.', 'error')
                else:
                    setters = ','.join(f'{c}=?' for c in COLUMNS)
                    db.execute(f'UPDATE owners SET {setters} WHERE id=?', vals + [owner_id])
                    db.commit()
                    flash('Запись обновлена.', 'success')
                    return redirect(url_for('listing'))
        return render_template('owner_form.html', row=row, labels=LABELS)

    @app.post('/owners/<int:owner_id>/delete')
    def delete(owner_id):
        try:
            cars = clients.count_cars(owner_id)
        except CarsUnavailable:
            flash('Удаление невозможно: сервис автомобилей недоступен, наличие машин у владельца проверить нельзя.', 'error')
            return redirect(url_for('listing'))
        if cars:
            flash(f'Удаление невозможно: у владельца есть автомобили ({cars}).', 'error')
            return redirect(url_for('listing'))
        with get_db() as db:
            db.execute('DELETE FROM owners WHERE id=?', (owner_id,))
            db.commit()
        flash('Запись удалена.', 'success')
        return redirect(url_for('listing'))

    return app


app = create_app()

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5001, debug=False, use_reloader=False)
