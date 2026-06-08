import os
from config import OUTPUT_DIR
from pipelines import (
    products,
    orders,
    natural_person,
    legal_person,
    visit,
    writeoff,
    payments,
    cash_operations,
    product_group,
    inventory_price,
    person_group,
    returns,
    returns_to_supplier,
)

os.makedirs(OUTPUT_DIR, exist_ok=True)

orders.run(begin_date="01.05.2026")
products.run()
natural_person.run()
legal_person.run()
visit.run()
writeoff.run()
payments.run()
cash_operations.run()
product_group.run()
inventory_price.run()
person_group.run()
returns.run()
returns_to_supplier.run()


