"""
Сквозной smoke-тест приложения «Учёт автомобилей», развёрнутого в Kubernetes.
Запросы идут через gateway (nginx) -> car-app -> SQLite на PVC.

Запуск (через scripts/smoke.ps1 или вручную при поднятом port-forward):
    BASE_URL=http://localhost:8082 python -m pytest smoke_tests --junitxml=reports/results.xml

Без BASE_URL тесты пропускаются, поэтому обычный `pytest` в корне проекта
не пытается ходить в кластер. Используется только стандартная библиотека.
"""
import http.cookiejar
import os
import re
import unittest
import urllib.error
import urllib.parse
import urllib.request
import uuid

BASE = os.environ.get("BASE_URL", "").rstrip("/")
EXPECT_REPLICAS = int(os.environ.get("EXPECT_REPLICAS", "1"))
T = 10


class Client:
    """HTTP-клиент с cookie: flash-сообщения Flask живут в подписанной cookie-сессии."""

    def __init__(self):
        jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    def request(self, path, form=None):
        data = urllib.parse.urlencode(form).encode() if form is not None else None
        req = urllib.request.Request(BASE + path, data=data)
        try:
            with self.opener.open(req, timeout=T) as r:
                return r.status, r.read().decode("utf-8"), r.headers
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace"), e.headers

    def get(self, path):
        return self.request(path)

    def post(self, path, **form):
        return self.request(path, form)


def row_id(html, text):
    """id строки таблицы, содержащей text (формат: <tr><td>ID</td>...text...)."""
    m = re.search(r"<tr><td>(\d+)</td>(?:(?!</tr>).)*?" + re.escape(text), html, re.S)
    return int(m.group(1)) if m else None


@unittest.skipUnless(BASE, "BASE_URL не задан: smoke-тест запускается только против развёрнутого приложения")
class CarAccountingSmokeTest(unittest.TestCase):

    def setUp(self):
        self.c = Client()
        self.tag = uuid.uuid4().hex[:8].upper()

    # --- helpers: создать запись и гарантированно удалить её в конце теста ---
    # addCleanup выполняется в обратном порядке, поэтому зависимые записи
    # (автомобиль) удаляются раньше справочников (владелец, марка, модель).
    def create(self, entity, find_text, **form):
        status, _, _ = self.c.post(f"/{entity}/create", **form)
        self.assertEqual(status, 200, f"create {entity}")
        _, page, _ = self.c.get(f"/{entity}/")
        rid = row_id(page, find_text)
        self.assertIsNotNone(rid, f"{entity}: созданная запись {find_text} не найдена в списке")
        self.addCleanup(self.c.post, f"/{entity}/{rid}/delete")
        return rid

    # --- проверки ---
    def test_gateway_health(self):
        status, body, headers = self.c.get("/healthz")
        self.assertEqual(status, 200)
        self.assertIn('"status":"ok"', body)
        self.assertTrue(headers.get("X-Gateway"), "gateway не вернул X-Gateway")

    def test_app_probes_through_gateway(self):
        status, body, headers = self.c.get("/health")
        self.assertEqual(status, 200)
        self.assertIn('"status":"ok"', body)
        self.assertTrue(headers.get("X-Served-By"), "приложение не вернуло X-Served-By")
        self.assertEqual(self.c.get("/ready")[0], 200)

    def test_pages(self):
        status, body, _ = self.c.get("/")
        self.assertEqual(status, 200)
        self.assertIn("Система учёта автомобилей", body)
        for e in ("cars", "owners", "brands", "models", "inspections", "insurance"):
            self.assertEqual(self.c.get(f"/{e}/")[0], 200, e)
        self.assertEqual(self.c.get("/nope/")[0], 404)

    def test_seed_data_present(self):
        # демо-данные создаёт Job db-init
        _, page, _ = self.c.get("/brands/")
        for brand in ("Toyota", "BMW", "Lada", "Honda"):
            self.assertIn(brand, page)

    def test_load_balancing(self):
        pods = {self.c.get("/health")[2].get("X-Served-By") for _ in range(30)}
        pods.discard(None)
        self.assertGreaterEqual(len(pods), min(EXPECT_REPLICAS, 2),
                                f"запросы обслужили поды {pods}, ожидалось реплик: {EXPECT_REPLICAS}")
        print(f"\nPods that served requests: {sorted(pods)}")

    def test_owner_crud(self):
        name = f"Смоук Владелец {self.tag}"
        oid = self.create("owners", name, full_name=name, phone="+7 900 000-00-00",
                          email="smoke@example.com", address="Тестовый адрес")
        new_name = f"Смоук Изменён {self.tag}"
        status, _, _ = self.c.post(f"/owners/{oid}/edit", full_name=new_name, phone="1",
                                   email="smoke@example.com", address="Тестовый адрес")
        self.assertEqual(status, 200)
        _, page, _ = self.c.get("/owners/")
        self.assertIn(new_name, page)
        self.assertNotIn(name, page)
        self.c.post(f"/owners/{oid}/delete")
        _, page, _ = self.c.get("/owners/")
        self.assertNotIn(new_name, page)

    def test_car_flow_across_entities(self):
        brand = f"SmokeBrand{self.tag}"
        model = f"SmokeModel{self.tag}"
        owner = f"Смоук Владелец {self.tag}"
        reg = f"S{self.tag}"
        vin = f"VIN{self.tag}{self.tag}"[:17].ljust(17, "0")
        policy = f"SMOKE-{self.tag}"

        brand_id = self.create("brands", brand, name=brand)
        model_id = self.create("models", model, brand_id=brand_id, name=model)
        owner_id = self.create("owners", owner, full_name=owner, phone="", email="", address="")
        car_id = self.create("cars", reg, owner_id=owner_id, brand_id=brand_id, model_id=model_id,
                             registration_number=reg, vin=vin, production_year=2024,
                             color="Синий", mileage=1000, status="Активен")
        self.create("inspections", "Смоук-комментарий", car_id=car_id,
                    inspection_date="2026-10-01", next_inspection_date="2027-10-01",
                    result="Пройден", mileage=1500, comment="Смоук-комментарий")
        self.create("insurance", policy, car_id=car_id, policy_number=policy,
                    insurance_company="SmokeInsure", start_date="2026-10-01",
                    end_date="2027-09-30", insurance_type="ОСАГО", cost=10000)

        # карточка автомобиля собирает данные из нескольких таблиц
        status, page, _ = self.c.get(f"/cars/{car_id}")
        self.assertEqual(status, 200)
        for expected in (reg, owner, brand, model, policy):
            self.assertIn(expected, page)

        # удаление автомобиля каскадно удаляет осмотры и полисы
        self.c.post(f"/cars/{car_id}/delete")
        self.assertEqual(self.c.get(f"/cars/{car_id}")[0], 404)
        _, page, _ = self.c.get("/insurance/")
        self.assertNotIn(policy, page)

    def test_delete_restricted_when_referenced(self):
        brand = f"SmokeBrand{self.tag}"
        brand_id = self.create("brands", brand, name=brand)
        self.create("models", f"SmokeModel{self.tag}", brand_id=brand_id, name=f"SmokeModel{self.tag}")

        # марку с моделями удалить нельзя (ON DELETE RESTRICT); сообщение приходит
        # во flash через cookie и должно читаться любой репликой (общий SECRET_KEY)
        status, page, _ = self.c.post(f"/brands/{brand_id}/delete")
        self.assertEqual(status, 200)
        self.assertIn("Удаление невозможно", page)
        self.assertIn(brand, page)


if __name__ == "__main__":
    unittest.main()
