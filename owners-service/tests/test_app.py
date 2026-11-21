import clients, config, database
from app import create_app


def test_list_page(client):
    r = client.get('/owners/')
    assert r.status_code == 200 and 'Иванов Иван Иванович' in r.text
    assert client.get('/').status_code == 302


def test_owner_crud(client):
    r = client.post('/owners/create', data={'full_name': 'Тест Тестов', 'phone': '1', 'email': 't@e.ru', 'address': 'Адрес'}, follow_redirects=True)
    assert r.status_code == 200 and 'Тест Тестов' in r.text
    r = client.post('/owners/1/edit', data={'full_name': 'Иванов Иван', 'phone': '2', 'email': 'x@e.ru', 'address': 'Новый'}, follow_redirects=True)
    assert 'Иванов Иван' in r.text and 'Новый' in r.text
    r = client.post('/owners/4/delete', follow_redirects=True)
    assert 'Запись удалена' in r.text and 'Тест Тестов' not in r.text
    assert client.get('/owners/99/edit').status_code == 404


def test_full_name_required(client):
    r = client.post('/owners/create', data={'full_name': ' ', 'phone': '', 'email': '', 'address': ''}, follow_redirects=True)
    assert 'Укажите ФИО' in r.text


def test_api(client):
    owners = client.get('/api/owners').get_json()
    assert len(owners) == 3 and {'id', 'full_name', 'phone', 'email', 'address'} <= set(owners[0])
    assert client.get('/api/owners/count').get_json() == {'count': 3}
    assert client.get('/api/owners/1').get_json()['full_name'] == 'Иванов Иван Иванович'
    r = client.get('/api/owners/99')
    assert r.status_code == 404 and r.get_json()['error']


def test_delete_blocked_when_owner_has_cars(client, monkeypatch):
    monkeypatch.setattr(clients, 'count_cars', lambda owner_id: 2)
    r = client.post('/owners/1/delete', follow_redirects=True)
    assert 'Удаление невозможно' in r.text and 'Иванов Иван Иванович' in r.text
    assert client.get('/api/owners/count').get_json() == {'count': 3}


def test_delete_blocked_when_cars_service_down(client, monkeypatch):
    def boom(owner_id):
        raise clients.CarsUnavailable('down')
    monkeypatch.setattr(clients, 'count_cars', boom)
    r = client.post('/owners/1/delete', follow_redirects=True)
    assert 'сервис автомобилей недоступен' in r.text
    assert client.get('/api/owners/count').get_json() == {'count': 3}


def test_owners_work_when_cars_service_down(client, monkeypatch):
    def boom(owner_id):
        raise clients.CarsUnavailable('down')
    monkeypatch.setattr(clients, 'count_cars', boom)
    assert client.get('/owners/').status_code == 200
    assert client.get('/api/owners').status_code == 200
    assert client.post('/owners/create', data={'full_name': 'Новый', 'phone': '', 'email': '', 'address': ''}).status_code == 302


def test_health_ready_header(client):
    r = client.get('/health')
    assert r.status_code == 200 and r.get_json()['service'] == 'owners-service'
    assert r.headers.get('X-Served-By')
    assert client.get('/ready').get_json()['status'] == 'ready'


def test_ready_fails_without_schema(tmp_path, monkeypatch):
    dbfile = tmp_path / 'empty.db'
    monkeypatch.setattr(config, 'DATABASE_PATH', dbfile)
    monkeypatch.setattr(database, 'DATABASE_PATH', dbfile)
    c = create_app({'TESTING': True, 'SECRET_KEY': 'test'}).test_client()
    assert c.get('/health').status_code == 200
    assert c.get('/ready').status_code == 503
