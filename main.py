import os
from config import OUTPUT_DIR
from pipelines import products

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Yangi pipeline qo'shish uchun:
#   1. pipelines/ papkasida yangi fayl yarating
#   2. Shu yerga import qilib, run() ni chaqiring

products.run()
