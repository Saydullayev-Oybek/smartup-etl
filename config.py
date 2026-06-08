import json
import base64
from pathlib import Path

_ROOT = Path(__file__).resolve().parent

# ── API ───────────────────────────────────────────────────────────────────────
PROJECT_CODE = "trade"
FILIAL_ID    = "86401"
TIMEOUT      = 150

ENDPOINTS = {
    "inventory":             "https://smartup.online/b/anor/mxsx/mr/inventory$export",
    "natural_person":        "https://smartup.online/b/anor/mxsx/mr/natural_person$export",
    "legal_person":          "https://smartup.online/b/anor/mxsx/mr/legal_person$export",
    "order":                 "https://smartup.online/b/trade/txs/tdeal/order$export",
    "return":                "https://smartup.online/b/anor/mxsx/mdeal/return$export",
    "visit":                 "https://smartup.online/b/trade/txs/tvt/visit$export",
    "writeoff":              "https://smartup.online/b/anor/mxsx/mkw/writeoff$export",
    "Return_to_suppliers":   "https://smartup.online/b/anor/mxsx/mkw/return$export",
    "Payments_from_clients": "https://smartup.online/b/trade/txs/tcs/cashin$export",
    "Bank_Statements":       "https://smartup.online/b/anor/mxsx/mkcs/bank_operation$import",
    "Cash_Operations":       "https://smartup.online/b/anor/mxsx/mkcs/cash_operation$export",
    "Product_group":         "https://smartup.online/b/anor/mxsx/mr/product_group$export",
    "Inventory_price":       "https://smartup.online/b/anor/api/v2/mkf/product_price$export",
    "Persons_group":         "https://smartup.online/b/anor/mxsx/mr/person_group$export",
}

# ── Database ──────────────────────────────────────────────────────────────────
DB_URL = "postgresql://postgres:0121@localhost:5432/smartup"

# ── Output ────────────────────────────────────────────────────────────────────
OUTPUT_DIR = "CleanedData"


def get_headers() -> dict:
    with open(_ROOT / "auth.json") as f:
        auth = json.load(f)

    token = base64.b64encode(
        f"{auth['username']}:{auth['password']}".encode()
    ).decode()

    return {
        "Authorization": f"Basic {token}",
        "project_code":  PROJECT_CODE,
        "filial_id":     FILIAL_ID,
    }
