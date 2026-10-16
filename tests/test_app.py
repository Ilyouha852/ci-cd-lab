def test_home(client):
    r=client.get('/'); assert r.status_code==200; assert 'Система учёта автомобилей' in r.text

def test_all_sections(client):
    for e in ['cars','owners','brands','models','inspections','insurance']: assert client.get(f'/{e}/').status_code==200

def test_car_crud(client):
    r=client.post('/cars/create',data={'owner_id':'1','brand_id':'1','model_id':'2','registration_number':'Н111АА777','vin':'JTD000000000000001','production_year':'2024','color':'Синий','mileage':'1000','status':'Активен'},follow_redirects=True); assert r.status_code==200 and 'Н111АА777' in r.text
    r=client.post('/cars/1/edit',data={'owner_id':'1','brand_id':'1','model_id':'1','registration_number':'А123ВС777','vin':'JTNB11HK103456789','production_year':'2022','color':'Красный','mileage':'50000','status':'Активен'},follow_redirects=True); assert r.status_code==200
    assert client.get('/cars/1').status_code==200
    assert client.post('/cars/4/delete',follow_redirects=True).status_code==200

def test_owner_and_reference_crud(client):
    assert client.post('/owners/create',data={'full_name':'Тест Тестов','phone':'1','email':'t@e.ru','address':'Адрес'},follow_redirects=True).status_code==200
    assert client.post('/owners/1/edit',data={'full_name':'Иванов Иван Иванович','phone':'2','email':'x@e.ru','address':'Новый'},follow_redirects=True).status_code==200
    assert client.post('/brands/create',data={'name':'Mazda'},follow_redirects=True).status_code==200
    assert client.post('/models/create',data={'brand_id':'1','name':'Corolla'},follow_redirects=True).status_code==200
    assert client.post('/inspections/create',data={'car_id':'1','inspection_date':'2026-10-01','next_inspection_date':'2027-10-01','result':'Пройден','mileage':'46000','comment':'OK'},follow_redirects=True).status_code==200
    assert client.post('/insurance/create',data={'car_id':'1','policy_number':'OSAGO-999999','insurance_company':'Test','start_date':'2026-10-01','end_date':'2027-09-30','insurance_type':'ОСАГО','cost':'10000'},follow_redirects=True).status_code==200
 