# SmartUp ETL

SmartUp ERP tizimidan ma'lumot olib, tozalab, PostgreSQL ga yuklaydi.
Har bir pipeline API → pandas transform → DB upsert zanjirida ishlaydi.

---

## Ishlatish usullari

Loyihani **3 xil usulda** ishlatish mumkin. O'zingizga mosini tanlang:

---

### 1-usul — Faqat Excel (eng oddiy, Docker kerak emas)

PostgreSQL ham, Docker ham kerak emas. Ma'lumotlar `CleanedData/` papkasiga `.xlsx` formatda saqlanadi.

```bash
# 1. Virtual muhit
python -m venv .venv && . .venv/Scripts/activate
pip install -r requirements.txt

# 2. .env faylini yarating
cp .env.example .env
```

`.env` faylida faqat shu ikki narsani to'ldiring:

```env
SMARTUP_USERNAME=your-username
SMARTUP_PASSWORD=your-password
EXCEL_ONLY=true
```

```bash
# 3. Ishga tushiring
python main.py
```

Natija: `CleanedData/` papkasida Excel fayllar paydo bo'ladi.

---

### 2-usul — Docker bilan (to'liq stack: DB + Airflow + pgAdmin)

Docker Desktop o'rnatilgan bo'lishi kerak.

```bash
# 1. .env faylini yarating va to'ldiring
cp .env.example .env
```

`.env` da to'ldiradigan asosiy qiymatlar:

```env
SMARTUP_USERNAME=your-username
SMARTUP_PASSWORD=your-password
DB_PASSWORD=your-db-password
DB_HOST=smartup-db        # Docker ichida ishlaydi, o'zgartirmang
EXCEL_ONLY=false
PGADMIN_EMAIL=admin@smartup.com
PGADMIN_PASSWORD=your-pgadmin-password
_AIRFLOW_WWW_USER_PASSWORD=your-airflow-password
```

```bash
# 2. Barcha servislani ishga tushiring
docker compose up -d --build
```

| Xizmat | Manzil | Login |
| --- | --- | --- |
| Airflow | <http://localhost:8080> | airflow / `_AIRFLOW_WWW_USER_PASSWORD` |
| pgAdmin | <http://localhost:5050> | `PGADMIN_EMAIL` / `PGADMIN_PASSWORD` |
| PostgreSQL | localhost:**5433** | postgres / `DB_PASSWORD` |

**pgAdmin da DB ga ulanish:** Host = `smartup-db`, Port = `5432`, DB = `smartup`

Airflow DAG `smartup_etl` har kuni 02:00 da ishlaydi. Qo'lda ham ishlatish mumkin.

---

### 3-usul — Lokal Python + Docker DB

Docker orqali faqat DB ni ishga tushirib, Python skriptni lokal ishlatish.

```bash
# 1. Faqat DB ni ishga tushiring
docker compose up -d smartup-db

# 2. .env da DB_HOST ni localhost ga o'zgartiring
```

```env
SMARTUP_USERNAME=your-username
SMARTUP_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5433              # Docker 5433 portini tashqariga ochadi
DB_PASSWORD=your-db-password
EXCEL_ONLY=false
```

```bash
# 3. Ishga tushiring
python main.py
```

---

## DB_HOST — muhim eslatma

| Qayerdan ishlatyapsiz | `DB_HOST` | `DB_PORT` |
| --- | --- | --- |
| Docker container ichidan (Airflow) | `smartup-db` | `5432` |
| Lokal `python main.py` + Docker DB | `localhost` | `5433` |
| Lokal `python main.py` + lokal PG | `localhost` | `5432` |

---

## Pipelinelar

Barcha pipelinelar `pipelines/` papkasida joylashgan.

| Pipeline | Yaratadigan jadvallar |
| --- | --- |
| `products` | `products`, `product_group`, `product_inventory_kind`, `product_sector` |
| `orders` | `orders`, `order_products`, `order_gifts`, `order_actions`, `order_consignments` |
| `natural_person` | `natural_persons`, `natural_person_group`, `natural_person_room` |
| `legal_person` | `legal_persons`, `legal_person_group`, `legal_person_bank_account`, `legal_person_room` |
| `visit` | `visits`, `visit_person_types`, `visit_comments` |
| `writeoff` | `writeoffs`, `writeoff_items` |
| `payments` | `payments` |
| `cash_operations` | `cash_operations`, `cash_operation_refs` |
| `product_group` | `product_groups`, `product_group_types` |
| `inventory_price` | `inventory_prices` |
| `person_group` | `person_groups`, `person_group_types` |
| `returns` | `returns`, `return_products` |
| `returns_to_supplier` | `supplier_returns`, `supplier_return_items` |
| `bank_statements` | `bank_statements` |

---

## Arxitektura

```text
SmartUp API → client.py → pipelines/*.py → pipeline_utils.emit() → loader.py → PostgreSQL
              (fetch,      (transform,       (validate +              (idempotent
               retry)       explode)          Excel + load)            upsert)
```

`core/` — barcha qurilish bloklari (config, client, loader, transforms, validation)  
`pipelines/` — har bir entity uchun alohida pipeline  
`dags/` — Airflow DAG (dimensionlar → facts)

---

## DB backup

```bash
# Saqlash
docker compose exec -T smartup-db pg_dump -U postgres -d smartup > backup.dump

# Qayta yuklash
docker compose exec -T smartup-db psql -U postgres -d smartup < backup.dump
```

---

## Test va lint

```bash
pip install -r requirements-dev.txt
pytest
ruff check .
```
