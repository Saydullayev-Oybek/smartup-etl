"""Behavioural tests for the transform functions of all pipelines.

These lock in the output schema/semantics after the iterrows->explode refactor.
"""
import pandas as pd

from pipelines import (
    bank_statements,
    cash_operations,
    inventory_price,
    legal_person,
    natural_person,
    orders,
    payments,
    person_group,
    product_group,
    products,
    returns,
    returns_to_supplier,
    visit,
    writeoff,
)


def test_products_transforms():
    raw = pd.DataFrame([
        {
            "state": "A", "product_id": "5", "name": "X", "weight_netto": "1.5",
            "groups": [{"group_id": 1, "group_code": "g", "type_id": 2, "type_code": "t"}],
            "inventory_kinds": [{"inventory_kind": " g "}],
            "sector_codes": [{"sector_code": " s1 "}],
        },
        {
            "state": "P", "product_id": "6", "name": "Y", "weight_netto": "2",
            "groups": None, "inventory_kinds": None, "sector_codes": None,
        },
    ])

    dim = products.build_products(raw)
    assert dim["product_id"].tolist() == [5]               # inactive (state P) filtered out
    assert str(dim["product_id"].dtype) == "Int64"

    pg = products.build_product_group(dim)
    assert pg.loc[0, "group_id"] == 1 and pg.loc[0, "type_code"] == "t"

    inv = products.build_product_inv_kind(dim)
    assert inv.loc[0, "inventory_kind"] == "G"             # stripped + upper-cased
    assert inv.loc[0, "label"].startswith("Goods")

    sec = products.build_product_sector(dim)
    assert sec.loc[0, "sector_code"] == "s1"               # stripped


def test_orders_transforms():
    raw = pd.DataFrame([
        {
            "deal_id": "100", "total_amount": "50.5", "person_id": "7",
            "order_products": [
                {"product_unit_id": "3", "order_quant": "2", "details": [{"d": 1}]},
            ],
            "order_gifts": [],
            "order_actions": None,
            "order_consignments": [{"consignment_amount": "9"}],
        },
    ])

    o = orders.build_orders(raw)
    assert o.loc[0, "deal_id"] == 100
    assert o.loc[0, "total_amount"] == 50.5

    op = orders.build_order_products(raw)
    assert "details" not in op.columns                     # nested list dropped
    assert op.loc[0, "product_unit_id"] == 3
    assert op.loc[0, "deal_id"] == 100

    assert orders.build_order_gifts(raw).empty             # empty list -> empty frame

    oc = orders.build_order_consignments(raw)
    assert oc.loc[0, "consignment_amount"] == 9


def test_visit_transforms():
    raw = pd.DataFrame([
        {
            "visit_headers": [{
                "visit_id": "11", "person_id": "2",
                "person_types": [{"person_type_id": "5", "person_type_name": "N"}],
            }],
            "comments": [{"comment_name": "c", "comment_created_by_name": "u"}],
        },
    ])

    v = visit.build_visits(raw)
    assert v.loc[0, "visit_id"] == 11
    assert "person_types" not in v.columns                 # nested list dropped from headers

    pt = visit.build_visit_person_types(raw)
    assert pt.loc[0, "visit_id"] == 11
    assert pt.loc[0, "person_type_id"] == 5

    cm = visit.build_visit_comments(raw)
    assert cm.loc[0, "visit_id"] == 11
    assert cm.loc[0, "comment_name"] == "c"


def test_natural_person_transforms():
    raw = pd.DataFrame([{
        "person_id": "10", "first_name": "Ali", "state": "A",
        "groups": [{"group_code": "G1", "type_code": "T1"}],
        "rooms": [{"room_id": "5", "room_code": "R1", "room_type_code": "RT"}],
    }])

    dim = natural_person.build_natural_persons(raw)
    assert dim.loc[0, "person_id"] == 10
    assert str(dim["person_id"].dtype) == "Int64"

    grp = natural_person.build_natural_person_group(raw)
    assert grp.loc[0, "person_id"] == 10
    assert grp.loc[0, "group_code"] == "G1"

    rooms = natural_person.build_natural_person_room(raw)
    assert rooms.loc[0, "person_id"] == 10
    assert rooms.loc[0, "room_id"] == 5


def test_legal_person_transforms():
    raw = pd.DataFrame([{
        "person_id": "20", "name": "Firma", "state": "A",
        "groups": [{"group_id": "1", "group_code": "GRP", "type_id": "2", "type_code": "T"}],
        "bank_accounts": [{"bank_account_id": "3", "bank_account_code": "BA1",
                           "bank_account_name": "Hisob", "is_main": True,
                           "state": "A", "currency_code": "UZS",
                           "mfo": "123", "bank_name": "NBU"}],
        "rooms": [{"room_id": "7", "room_code": "R7", "room_type_code": "RT"}],
    }])

    dim = legal_person.build_legal_persons(raw)
    assert dim.loc[0, "person_id"] == 20

    grp = legal_person.build_legal_person_group(raw)
    assert grp.loc[0, "group_id"] == 1

    ba = legal_person.build_legal_person_bank_account(raw)
    assert ba.loc[0, "bank_account_id"] == 3
    assert ba.loc[0, "bank_account_code"] == "BA1"

    rooms = legal_person.build_legal_person_room(raw)
    assert rooms.loc[0, "room_id"] == 7


def test_person_group_transforms():
    raw = pd.DataFrame([{
        "person_group_id": "5", "code": "PG1", "name": "Guruh", "state": "A",
        "person_group_types": [{"person_type_id": "2", "code": "T", "name": "Type",
                                "state": "A", "order_no": "1"}],
    }])

    grp = person_group.build_person_groups(raw)
    assert grp.loc[0, "person_group_id"] == 5

    types = person_group.build_person_group_types(raw)
    assert types.loc[0, "person_group_id"] == 5
    assert types.loc[0, "person_type_id"] == 2


def test_product_group_transforms():
    raw = pd.DataFrame([{
        "product_group_id": "3", "code": "PG", "name": "Guruh", "state": "A",
        "product_group_types": [{"product_type_id": "8", "code": "T", "name": "Tur",
                                 "state": "A", "order_no": "1"}],
    }])

    grp = product_group.build_product_groups(raw)
    assert grp.loc[0, "product_group_id"] == 3

    types = product_group.build_product_group_types(raw)
    assert types.loc[0, "product_group_id"] == 3
    assert types.loc[0, "product_type_id"] == 8


def test_inventory_price_transforms():
    raw = pd.DataFrame([{
        "product_id": "15", "inventory_code": "INV1", "inventory_barcode": "BC1",
        "price_type": [{"price_type_code": "R", "card_code": "C1", "price": "12500.5"}],
    }])

    prices = inventory_price.build_inventory_prices(raw)
    assert prices.loc[0, "product_id"] == 15
    assert prices.loc[0, "price"] == 12500.5
    assert prices.loc[0, "price_type_code"] == "R"


def test_payments_transforms():
    raw = pd.DataFrame([{
        "cashin_id": "99", "client_id": "7", "amount": "1500000.0",
        "cashin_time": "2026-01-15", "currency_code": "UZS",
    }])

    p = payments.build_payments(raw)
    assert p.loc[0, "cashin_id"] == 99
    assert p.loc[0, "amount"] == 1_500_000.0
    assert p.loc[0, "client_id"] == 7


def test_cash_operations_transforms():
    raw = pd.DataFrame([{
        "operation_id": "55", "amount": "250000.0", "cashflow_kind": "IN",
        "ref_codes": [{"ref_code": "R1"}, {"ref_code": "R2"}],
    }])

    ops = cash_operations.build_cash_operations(raw)
    assert ops.loc[0, "operation_id"] == 55
    assert ops.loc[0, "amount"] == 250_000.0

    refs = cash_operations.build_cash_operation_refs(raw)
    assert len(refs) == 2
    assert refs.loc[0, "operation_id"] == 55


def test_writeoff_transforms():
    raw = pd.DataFrame([{
        "writeoff_id": "33", "c_amount": "5000.0", "c_amount_base": "4500.0",
        "status": "A",
        "writeoff_items": [{"writeoff_item_id": "1", "quantity": "10.0"}],
    }])

    wo = writeoff.build_writeoffs(raw)
    assert wo.loc[0, "writeoff_id"] == 33
    assert wo.loc[0, "c_amount"] == 5000.0

    items = writeoff.build_writeoff_items(raw)
    assert items.loc[0, "writeoff_id"] == 33
    assert items.loc[0, "writeoff_item_id"] == 1
    assert items.loc[0, "quantity"] == 10.0


def test_returns_transforms():
    raw = pd.DataFrame([{
        "deal_id": "77", "total_amount": "300.0",
        "return_products": [{"product_id": "5", "quant": "2"}],
    }])

    ret = returns._build_main(raw)
    assert ret.loc[0, "deal_id"] == 77
    assert "return_products" not in ret.columns            # nested column dropped

    items = returns._build_items(raw)
    assert items.loc[0, "deal_id"] == 77


def test_returns_to_supplier_transforms():
    raw = pd.DataFrame([{
        "return_id": "44", "status": "A",
        "return_items": [{"product_id": "9", "quantity": "3"}],
    }])

    ret = returns_to_supplier._build_main(raw)
    assert ret.loc[0, "return_id"] == 44
    assert "return_items" not in ret.columns

    items = returns_to_supplier._build_items(raw)
    assert items.loc[0, "return_id"] == 44


def test_bank_statements_transforms():
    raw = pd.DataFrame([{
        "operation_id": "88", "amount": "999000.0", "cashflow_kind": "OUT",
        "bank_account_code": "BA99",
        "ref_codes": [{"ref_code": "X1"}],
    }])

    stmt = bank_statements.build_bank_statements(raw)
    assert stmt.loc[0, "operation_id"] == 88
    assert stmt.loc[0, "amount"] == 999_000.0

    refs = bank_statements.build_bank_statement_refs(raw)
    assert refs.loc[0, "operation_id"] == 88
    assert refs.loc[0, "ref_code"] == "X1"
