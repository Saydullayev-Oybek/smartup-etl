"""Behavioural tests for the transform functions of representative pipelines.

These lock in the output schema/semantics after the iterrows->explode refactor.
"""
import pandas as pd

from pipelines import orders, products, visit


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
