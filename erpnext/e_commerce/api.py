# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.utils import cint

from erpnext.e_commerce.product_data_engine.filters import ProductFiltersBuilder
from erpnext.e_commerce.product_data_engine.query import ProductQuery
from erpnext.setup.doctype.item_group.item_group import get_child_groups_for_website


@frappe.whitelist(allow_guest=True)
def get_product_filter_data(query_args=None, guest_cart_cookie=None):
	"""
	Returns filtered products and discount filters.
	:param query_args (dict): contains filters to get products list

	Query Args filters:
	search (str): Search Term.
	field_filters (dict): Keys include item_group, brand, etc.
	attribute_filters(dict): Keys include Color, Size, etc.
	start (int): Offset items by
	item_group (str): Valid Item Group
	from_filters (bool): Set as True to jump to page 1
	"""
	if isinstance(query_args, str):
		query_args = json.loads(query_args)

	query_args = frappe._dict(query_args)
	if query_args:
		search = query_args.get("search")
		field_filters = query_args.get("field_filters", {})
		attribute_filters = query_args.get("attribute_filters", {})
		start = cint(query_args.start) if query_args.get("start") else 0
		item_group = query_args.get("item_group")
		from_filters = query_args.get("from_filters")
	else:
		search, attribute_filters, item_group, from_filters = None, None, None, None
		field_filters = {}
		start = 0

	# if new filter is checked, reset start to show filtered items from page 1
	if from_filters:
		start = 0

	sub_categories = []
	if item_group:
		sub_categories = get_child_groups_for_website(item_group, immediate=True)

	engine = ProductQuery()
	try:
		result = engine.query(
			attribute_filters, field_filters, search_term=search, start=start, item_group=item_group
		)
	except Exception:
		frappe.log_error("Product query with filter failed")
		return {"exc": "Something went wrong!"}

	if guest_cart_cookie:
		from erpnext.e_commerce.shopping_cart.cart import _get_cart_quotation
		cart = _get_cart_quotation(quote_identifier=guest_cart_cookie)
		if cart:
			cart_item_qty = {}
			for item in cart.items:
				if item.item_code not in cart_item_qty:
					cart_item_qty[item.item_code] = item.qty
			items_with_qty = []
			for item in result["items"]:
				if item["item_code"] in cart_item_qty:
					item["qty"] = cart_item_qty[item["item_code"]]
				items_with_qty.append(item)
			result["items"] = items_with_qty
	# discount filter data
	filters = {}
	discounts = result["discounts"]

	if discounts:
		filter_engine = ProductFiltersBuilder()
		filters["discount_filters"] = filter_engine.get_discount_filters(discounts)


	brand_data = {}
	item_group_data = {}
	for item in result["items"]:
		if "brand" in item:
			if item["brand"] in brand_data:
				brand_data[item["brand"]] = brand_data[item["brand"]] + 1
			else:
				brand_data[item["brand"]] = 1

		if "item_group" in item:
			if item["item_group"] in item_group_data:
				item_group_data[item["item_group"]] = item_group_data[item["item_group"]] + 1
			else:
				item_group_data[item["item_group"]] = 1

	data_return =  {
		"items": result["items"] or [],
		"filters": filters,
		"settings": engine.settings,
		"sub_categories": sub_categories,
		"items_count": result["items_count"],
		"brand_count": brand_data,
		"item_group_count": item_group_data
	}
	return data_return


@frappe.whitelist(allow_guest=True)
def get_guest_redirect_on_action():
	return frappe.db.get_single_value("E Commerce Settings", "redirect_on_action")
