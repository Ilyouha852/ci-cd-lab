from flask import Flask,render_template,request,redirect,url_for,flash
from config import SECRET_KEY
from database import get_db,init_db

ENTITIES={
'owners':{'title':'Владельцы','table':'owners','columns':['full_name','phone','email','address'],'labels':{'full_name':'ФИО','phone':'Телефон','email':'Email','address':'Адрес'}},
'brands':{'title':'Марки','table':'brands','columns':['name'],'labels':{'name':'Название марки'}},
'models':{'title':'Модели','table':'models','columns':['brand_id','name'],'labels':{'brand_id':'Марка','name':'Название модели'}},
'cars':{'title':'Автомобили','table':'cars','columns':['owner_id','brand_id','model_id','registration_number','vin','production_year','color','mileage','status'],'labels':{'owner_id':'Владелец','brand_id':'Марка','model_id':'Модель','registration_number':'Госномер','vin':'VIN','production_year':'Год выпуска','color':'Цвет','mileage':'Пробег','status':'Статус'}},
'inspections':{'title':'Технические осмотры','table':'technical_inspections','columns':['car_id','inspection_date','next_inspection_date','result','mileage','comment'],'labels':{'car_id':'Автомобиль','inspection_date':'Дата','next_inspection_date':'Следующий осмотр','result':'Результат','mileage':'Пробег','comment':'Комментарий'}},
'insurance':{'title':'Страховые полисы','table':'insurance_policies','columns':['car_id','policy_number','insurance_company','start_date','end_date','insurance_type','cost'],'labels':{'car_id':'Автомобиль','policy_number':'Номер полиса','insurance_company':'Компания','start_date':'Начало','end_date':'Окончание','insurance_type':'Тип','cost':'Стоимость'}}}

def options():
    with get_db() as db:
        return {'owner_id':db.execute('SELECT id,full_name label FROM owners ORDER BY full_name').fetchall(),'brand_id':db.execute('SELECT id,name label FROM brands ORDER BY name').fetchall(),'model_id':db.execute("SELECT models.id,brands.name||' — '||models.name label FROM models JOIN brands ON brands.id=models.brand_id ORDER BY label").fetchall(),'car_id':db.execute('SELECT id,registration_number label FROM cars ORDER BY registration_number').fetchall()}

def create_app(test_config=None):
    app=Flask(__name__); app.config.update(SECRET_KEY=SECRET_KEY)
    if test_config: app.config.update(test_config)
    @app.route('/')
    def index():
        with get_db() as db:
            stats={k:db.execute(q).fetchone()[0] for k,q in {'cars':'SELECT COUNT(*) FROM cars','active':"SELECT COUNT(*) FROM cars WHERE status='Активен'",'repair':"SELECT COUNT(*) FROM cars WHERE status='На ремонте'",'owners':'SELECT COUNT(*) FROM owners','brands':'SELECT COUNT(*) FROM brands','inspections':'SELECT COUNT(*) FROM technical_inspections'}.items()}
        return render_template('index.html',stats=stats)
    @app.route('/<entity>/')
    def listing(entity):
        if entity not in ENTITIES:return ('Not found',404)
        cfg=ENTITIES[entity]
        with get_db() as db: rows=db.execute(f"SELECT * FROM {cfg['table']} ORDER BY id DESC").fetchall()
        return render_template('list.html',cfg=cfg,entity=entity,rows=rows)
    @app.route('/<entity>/create',methods=['GET','POST'])
    def create(entity):
        if entity not in ENTITIES:return ('Not found',404)
        cfg=ENTITIES[entity]
        if request.method=='POST':
            vals=[request.form.get(c,'').strip() for c in cfg['columns']]
            with get_db() as db:
                try:
                    db.execute(f"INSERT INTO {cfg['table']}({','.join(cfg['columns'])}) VALUES({','.join('?'*len(vals))})",vals); db.commit(); flash('Запись добавлена.','success'); return redirect(url_for('listing',entity=entity))
                except Exception as e: flash(f'Ошибка: {e}','error')
        return render_template('form.html',cfg=cfg,entity=entity,row=None,options=options())
    @app.route('/<entity>/<int:item_id>/edit',methods=['GET','POST'])
    def edit(entity,item_id):
        if entity not in ENTITIES:return ('Not found',404)
        cfg=ENTITIES[entity]
        with get_db() as db:
            row=db.execute(f'SELECT * FROM {cfg["table"]} WHERE id=?',(item_id,)).fetchone()
            if not row:return ('Not found',404)
            if request.method=='POST':
                vals=[request.form.get(c,'').strip() for c in cfg['columns']]
                try:
                    setters=','.join(f'{c}=?' for c in cfg['columns']); db.execute(f'UPDATE {cfg["table"]} SET {setters} WHERE id=?',vals+[item_id]); db.commit(); flash('Запись обновлена.','success'); return redirect(url_for('listing',entity=entity))
                except Exception as e: flash(f'Ошибка: {e}','error')
        return render_template('form.html',cfg=cfg,entity=entity,row=row,options=options())
    @app.post('/<entity>/<int:item_id>/delete')
    def delete(entity,item_id):
        if entity not in ENTITIES:return ('Not found',404)
        with get_db() as db:
            try: db.execute(f'DELETE FROM {ENTITIES[entity]["table"]} WHERE id=?',(item_id,)); db.commit(); flash('Запись удалена.','success')
            except Exception as e: flash(f'Удаление невозможно: {e}','error')
        return redirect(url_for('listing',entity=entity))
    @app.route('/cars/<int:item_id>')
    def car_detail(item_id):
        with get_db() as db:
            car=db.execute("SELECT cars.*,owners.full_name owner_name,brands.name brand_name,models.name model_name FROM cars JOIN owners ON owners.id=cars.owner_id JOIN brands ON brands.id=cars.brand_id JOIN models ON models.id=cars.model_id WHERE cars.id=?",(item_id,)).fetchone()
            if not car:return ('Not found',404)
            inspections=db.execute('SELECT * FROM technical_inspections WHERE car_id=?',(item_id,)).fetchall(); policies=db.execute('SELECT * FROM insurance_policies WHERE car_id=?',(item_id,)).fetchall()
        return render_template('car_detail.html',car=car,inspections=inspections,policies=policies)
    return app

app=create_app()
if __name__=='__main__': init_db(); app.run(host='0.0.0.0',port=5000,debug=True)
