PRAGMA foreign_keys=ON;
-- Таблицы cars-service. Владельцы живут в БД owners-service, поэтому cars.owner_id
-- НЕ внешний ключ: его существование проверяется запросом к owners-service
-- (см. clients.py и app.py).
CREATE TABLE IF NOT EXISTS brands(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS models(id INTEGER PRIMARY KEY AUTOINCREMENT,brand_id INTEGER NOT NULL,name TEXT NOT NULL,UNIQUE(brand_id,name),FOREIGN KEY(brand_id) REFERENCES brands(id) ON DELETE RESTRICT);
CREATE TABLE IF NOT EXISTS cars(id INTEGER PRIMARY KEY AUTOINCREMENT,owner_id INTEGER NOT NULL,brand_id INTEGER NOT NULL,model_id INTEGER NOT NULL,registration_number TEXT NOT NULL UNIQUE,vin TEXT NOT NULL UNIQUE,production_year INTEGER NOT NULL,color TEXT NOT NULL,mileage INTEGER NOT NULL DEFAULT 0,status TEXT NOT NULL DEFAULT 'Активен',FOREIGN KEY(brand_id) REFERENCES brands(id) ON DELETE RESTRICT,FOREIGN KEY(model_id) REFERENCES models(id) ON DELETE RESTRICT);
CREATE TABLE IF NOT EXISTS technical_inspections(id INTEGER PRIMARY KEY AUTOINCREMENT,car_id INTEGER NOT NULL,inspection_date TEXT NOT NULL,next_inspection_date TEXT NOT NULL,result TEXT NOT NULL,mileage INTEGER NOT NULL DEFAULT 0,comment TEXT,FOREIGN KEY(car_id) REFERENCES cars(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS insurance_policies(id INTEGER PRIMARY KEY AUTOINCREMENT,car_id INTEGER NOT NULL,policy_number TEXT NOT NULL UNIQUE,insurance_company TEXT NOT NULL,start_date TEXT NOT NULL,end_date TEXT NOT NULL,insurance_type TEXT NOT NULL,cost REAL NOT NULL DEFAULT 0,FOREIGN KEY(car_id) REFERENCES cars(id) ON DELETE CASCADE);
