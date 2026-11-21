import config, database
from app import create_app

CAR = {'owner_id': '1', 'brand_id': '1', 'model_id': '2', 'registration_number': 'Н111АА777',
       'vin': 'JTD000000000000001', 'production_year': '2024', 'color': 'Синий', 'mileage': '1000',
       'status': 'Активен'}


def test_home(client):
    r = client.get('/')
    assert r.status_code == 200 and 'Система учёта автомобилей' in r.text


def test_all_sections(client):
    for e in ['cars', 'brands', 'models', 'inspections', 'insurance']:
        assert client.get(f'/{e}/').status_code == 200
    # владельцы живут в другом сервисе
    assert client.get('/owners/').status_code == 404


def test_car_crud(client):
    r = client.post('/cars/create', data=CAR, follow_redirects=True)
    assert r.status_code == 200 and 'Н111АА777' in r.text
    r = client.post('/cars/1/edit', data={**CAR, 'registration_number': 'А123ВС777', 'vin': 'JTNB11HK103456789', 'color': 'Красный'}, follow_redirects=True)
    assert r.status_code == 200
    assert client.get('/cars/1').status_code == 200
    assert client.post('/cars/4/delete', follow_redirects=True).status_code == 200
    assert client.get('/cars/4').status_code == 404


def test_reference_crud(client):
    assert client.post('/brands/create', data={'name': 'Mazda'}, follow_redirects=True).status_code == 200
    assert client.post('/models/create', data={'brand_id': '1', 'name': 'Corolla'}, follow_redirects=True).status_code == 200
    assert client.post('/inspections/create', data={'car_id': '1', 'inspection_date': '2026-10-01', 'next_inspection_date': '2027-10-01', 'result': 'Пройден', 'mileage': '46000', 'comment': 'OK'}, follow_redirects=True).status_code == 200
    assert client.post('/insurance/create', data={'car_id': '1', 'policy_number': 'OSAGO-999999', 'insurance_company': 'Test', 'start_date': '2026-10-01', 'end_date': '2027-09-30', 'insurance_type': 'ОСАГО', 'cost': '10000'}, follow_redirects=True).status_code == 200


def test_car_pages_show_owner_name_from_owners_service(client):
    assert 'Иванов Иван Иванович' in client.get('/cars/').text
    assert 'Иванов Иван Иванович' in client.get('/cars/1').text
    assert 'Петров Пётр Петрович' in client.get('/cars/create').text    # выпадающий список


def test_car_with_unknown_owner_is_rejected(client):
    r = client.post('/cars/create', data={**CAR, 'owner_id': '99'}, follow_redirects=True)
    assert 'Владелец не найден' in r.text and 'Н111АА777' not in client.get('/cars/').text


def test_car_with_garbage_owner_is_rejected(client):
    r = client.post('/cars/create', data={**CAR, 'owner_id': 'abc'}, follow_redirects=True)
    assert 'Некорректный владелец' in r.text


def test_owners_service_down_degrades_gracefully(client, owners_down):
    # чтение работает, вместо имени - #id
    r = client.get('/cars/')
    assert r.status_code == 200 and '#1' in r.text and 'Сервис владельцев недоступен' in r.text
    r = client.get('/cars/1')
    assert r.status_code == 200 and 'сервис владельцев недоступен' in r.text
    assert client.get('/').status_code == 200
    assert client.get('/brands/').status_code == 200
    # запись автомобиля отклоняется с понятным сообщением, а не 500
    r = client.post('/cars/create', data=CAR, follow_redirects=True)
    assert r.status_code == 200 and 'Сервис владельцев недоступен' in r.text
    assert 'Н111АА777' not in client.get('/cars/').text
    # справочники и собственная БД не зависят от owners-service
    assert client.post('/brands/create', data={'name': 'Mazda'}, follow_redirects=True).status_code == 200


def test_api_cars_count(client):
    assert client.get('/api/cars/count').get_json() == {'count': 3}
    assert client.get('/api/cars/count?owner_id=1').get_json() == {'count': 1}
    assert client.get('/api/cars/count?owner_id=99').get_json() == {'count': 0}
    assert len(client.get('/api/cars').get_json()) == 3


def test_health_and_ready(client):
    r = client.get('/health')
    assert r.status_code == 200 and r.get_json()['service'] == 'cars-service'
    r = client.get('/ready')
    assert r.status_code == 200 and r.get_json()['status'] == 'ready'


def test_ready_does_not_depend_on_owners_service(client, owners_down):
    assert client.get('/ready').status_code == 200


def test_served_by_header(client):
    assert client.get('/health').headers.get('X-Served-By')


def test_ready_fails_without_schema(tmp_path, monkeypatch):
    dbfile = tmp_path / 'empty.db'
    monkeypatch.setattr(config, 'DATABASE_PATH', dbfile)
    monkeypatch.setattr(database, 'DATABASE_PATH', dbfile)
    c = create_app({'TESTING': True, 'SECRET_KEY': 'test'}).test_client()
    assert c.get('/health').status_code == 200
    assert c.get('/ready').status_code == 503
