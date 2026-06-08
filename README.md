# SmartUp ETL Pipeline

SmartUp ERP API dan ma'lumot olib, pandas bilan tozalab, Excel va PostgreSQL ga yuklaydigan ETL loyiha.

---

## Loyiha strukturasi

```
smartup-etl/
│
├── config.py               ← API endpointlari, DB URL, auth headers
├── client.py               ← fetch() va fetch_post() — API so'rovlari
├── loader.py               ← save_to_db() — DataFrame → PostgreSQL
├── main.py                 ← ishga tushiruvchi, barcha pipelinelarni chaqiradi
│
├── pipelines/
│   ├── products.py         ← products, product_group, inv_kind, sector
│   ├── orders.py           ← orders, order_products, gifts, actions, consignments
│   ├── natural_person.py   ← natural_persons, group, room
│   ├── legal_person.py     ← legal_persons, group, bank_account, room
│   ├── visit.py            ← visits, visit_person_types, visit_comments
│   ├── writeoff.py         ← writeoffs, writeoff_items
│   ├── payments.py         ← payments
│   ├── cash_operations.py  ← cash_operations, cash_operation_refs
│   ├── product_group.py    ← product_groups, product_group_types
│   ├── inventory_price.py  ← inventory_prices
│   ├── person_group.py     ← person_groups, person_group_types
│   ├── returns.py          ← returns, return_products (mijozlardan)
│   └── returns_to_supplier.py ← supplier_returns, supplier_return_items
│
├── auth.json.example       ← namuna (auth.json gitignore da)
├── requerements.txt        ← dependencies
└── CleanedData/            ← Excel fayllar (avtomatik yaratiladi)
```

---

## O'rnatish

### 1. Reponi clone qiling

```bash
git clone https://github.com/Saydullayev-Oybek/smartup-etl.git
cd smartup-etl
```

### 2. Virtual environment yarating va kutubxonalarni o'rnating

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requerements.txt
```

### 3. `auth.json` faylini yarating

```bash
copy auth.json.example auth.json
```

`auth.json` ni oching va SmartUp login/parolingizni kiriting:

```json
{
    "username": "SIZNING_LOGINIZ",
    "password": "SIZNING_PAROLINGIZ"
}
```

### 4. `config.py` da DB URL ni sozlang

```python
DB_URL = "postgresql://postgres:PAROLINGIZ@localhost:5432/smartup"
```

### 5. Ishga tushiring

```bash
python main.py
```

---

## Pipelinelar va jadvallar

| Pipeline | Jadvallar | Tavsif |
| --- | --- | --- |
| `products` | `products`, `product_group`, `product_inventory_kind`, `product_sector` | Mahsulot katalogi |
| `orders` | `orders`, `order_products`, `order_gifts`, `order_actions`, `order_consignments` | Buyurtmalar (POST, 30-kunlik chunk) |
| `natural_person` | `natural_persons`, `natural_person_group`, `natural_person_room` | Jismoniy shaxslar |
| `legal_person` | `legal_persons`, `legal_person_group`, `legal_person_bank_account`, `legal_person_room` | Yuridik shaxslar |
| `visit` | `visits`, `visit_person_types`, `visit_comments` | Savdo vakili tashriflari |
| `writeoff` | `writeoffs`, `writeoff_items` | Hisobdan chiqarishlar |
| `payments` | `payments` | Mijozlardan to'lovlar |
| `cash_operations` | `cash_operations`, `cash_operation_refs` | Kassa operatsiyalari |
| `product_group` | `product_groups`, `product_group_types` | Mahsulot guruhlari |
| `inventory_price` | `inventory_prices` | Mahsulot narxlari |
| `person_group` | `person_groups`, `person_group_types` | Shaxs guruhlari |
| `returns` | `returns`, `return_products` | Mijozlardan qaytarish |
| `returns_to_supplier` | `supplier_returns`, `supplier_return_items` | Yetkazib beruvchilarga qaytarish |

---

## ETL jarayoni

```
SmartUp API → client.py (fetch/fetch_post) → pipelines/*.py (transform) → loader.py + Excel
```

### GET endpointlari (filtr yo'q, barcha ma'lumot)

```python
raw = fetch(url, headers, key="...")
```

### POST endpointlari (sana oralig'i bilan, 30-kunlik chunk)

```python
raw = fetch_post(url, headers, body={"begin_modified_on": "...", "end_modified_on": "..."}, key="...")
```

---

## Yangi pipeline qo'shish

1. **`config.py`** ga endpoint qo'shing:

```python
ENDPOINTS = {
    ...
    "new_entity": "https://smartup.online/b/.../new_entity$export",
}
```

1. **`pipelines/new_entity.py`** yarating (`products.py` ga qarab):

```python
def build_new_entity(raw: pd.DataFrame) -> pd.DataFrame:
    ...

def run():
    raw = fetch(ENDPOINTS["new_entity"], get_headers(), key="new_entity")
    df = build_new_entity(raw)
    df.to_excel(os.path.join(OUTPUT_DIR, "new_entity.xlsx"), index=False)
    save_to_db(df, "new_entity")
```

1. **`main.py`** ga qo'shing:

```python
from pipelines import ..., new_entity

new_entity.run()
```

---

## Xatolar

| Xato | Sabab | Yechim |
| --- | --- | --- |
| `[XATO] Status: 401` | Login/parol noto'g'ri | `auth.json` ni tekshiring |
| `[XATO] Status: 400` | Noto'g'ri so'rov parametri | `config.py` da endpoint yoki body ni tekshiring |
| `[XATO] Status: 429` | API rate limit | Bir necha daqiqa kuting |
| `connection refused` | PostgreSQL ishlamayapti | DB ni ishga tushiring |
| `PermissionError` on xlsx | Fayl Excel da ochiq | Faylni yoping va qayta ishga tushiring |
