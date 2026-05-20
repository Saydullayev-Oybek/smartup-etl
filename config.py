import json
import base64

# ── API ───────────────────────────────────────────────────────────────────────
PROJECT_CODE = "trade"
FILIAL_ID    = "86401"
TIMEOUT      = 30

ENDPOINTS = {
    "inventory":      "https://smartup.online/b/anor/mxsx/mr/inventory$export",
    "natural_person": "https://smartup.online/b/anor/mxsx/mr/natural_person$export",
}

# ── Database ──────────────────────────────────────────────────────────────────
DB_URL = "postgresql://postgres:0121@localhost:5432/smartup"

# ── Output ────────────────────────────────────────────────────────────────────
OUTPUT_DIR = "CleanedData"


def get_headers() -> dict:
    with open("auth.json") as f:
        auth = json.load(f)

    token = base64.b64encode(
        f"{auth['username']}:{auth['password']}".encode()
    ).decode()

    return {
        "Authorization": f"Basic {token}",
        "project_code":  PROJECT_CODE,
        "filial_id":     FILIAL_ID,
    }
