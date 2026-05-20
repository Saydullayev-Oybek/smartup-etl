# SmartUp ETL Pipeline

API dan ma'lumot olib, tozalab, PostgreSQL ga yuklaydigan loyiha.

---

## Loyiha strukturasi

```
Project(SmartUp)/
│
├── config.py          ← API va DB sozlamalari
├── client.py          ← API dan ma'lumot olish
├── loader.py          ← PostgreSQL ga yuklash
├── main.py            ← ishga tushiruvchi
│
├── pipelines/
│   ├── products.py    ← tayyor namuna
│   ├── customers.py   ← shablon (sizniki)
│   └── orders.py      ← shablon (sizniki)
│
└── CleanedData/       ← Excel fayllar saqlanadi
```

---

## O'rnatish

### 1. Reponi clone qiling
```bash
git clone https://github.com/Saydullayev-Oybek/smartup-etl.git
cd smartup-etl
```

### 2. Kerakli kutubxonalarni o'rnating
```bash
pip install -r requerements.txt
```

### 3. `auth.json` faylini yarating
```bash
# auth.json.example faylidan nusxa oling
copy auth.json.example auth.json
```
Keyin `auth.json` faylini oching va o'z login/parolingizni kiriting:
```json
{
    "username": "SIZNING_LOGINIZ",
    "password": "SIZNING_PAROLINGIZ"
}
```

### 4. `config.py` da DB ni sozlang
```python
DB_URL = "postgresql://postgres:PAROLINGIZ@localhost:5432/smartup"
```

### 5. Ishga tushiring
```bash
python main.py
```

---

## ETL jarayoni qanday ishlaydi

```
1. EXTRACT  — API dan ma'lumot olinadi
2. TRANSFORM — ma'lumot tozalanadi, to'g'ri turga o'tkaziladi
3. LOAD     — Excel va PostgreSQL ga saqlanadi
```

### Har bir pipeline shu 3 qadamdan iborat:

```python
# 1. Extract
raw = fetch(url, headers, key="...")

# 2. Transform
clean_data = build_...(raw)

# 3. Load
clean_data.to_excel("CleanedData/....xlsx")
save_to_db(clean_data, "jadval_nomi")
```

---

## Yangi pipeline yozish — 4 qadam

### 1-qadam — `config.py` ga endpoint qo'shing

```python
ENDPOINTS = {
    "inventory": f"{BASE_URL}/mr/inventory$export",
    "customers": f"{BASE_URL}/...",   # ← yangi endpoint
}
```

### 2-qadam — `pipelines/customers.py` ni to'ldiring

`products.py` ga qarab yozing.

```python
def build_customers(raw: pd.DataFrame) -> pd.DataFrame:
    pass


def run():
    pass
```

### 3-qadam — `main.py` ga qo'shing

```python
from pipelines import products, customers

products.run()
customers.run()   # ← yangi qator
```

### 4-qadam — Tekshiring

```bash
python main.py
```

PostgreSQL da `SELECT * FROM customers LIMIT 10;` bilan natijani ko'ring.

---

## Fayllar vazifasi

| Fayl | Vazifasi | O'zgartirish kerakmi? |
|------|----------|----------------------|
| `config.py` | URL, DB, headerlar | Yangi endpoint qo'shganda |
| `client.py` | API so'rov yuboradi | Yo'q |
| `loader.py` | DB ga yuklaydi | Yo'q |
| `main.py` | Hammasini ishga tushiradi | Yangi pipeline qo'shganda |
| `pipelines/*.py` | ETL logikasi | Har bir jadval uchun |

---

## Xato chiqsa

| Xato | Sabab | Yechim |
|------|-------|--------|
| `[XATO] Status: 401` | Login/parol noto'g'ri | `auth.json` ni tekshiring |
| `[XATO] Status: 404` | URL noto'g'ri | `config.py` da endpoint ni tekshiring |
| `connection refused` | PostgreSQL ishlamayapti | DB ni ishga tushiring |
| `column not found` | API ustun nomini o'zgartirgan | `df.columns` chiqarib tekshiring |
