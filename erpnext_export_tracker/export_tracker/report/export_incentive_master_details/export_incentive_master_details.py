"""SOP J -- the Master Details sheet handed to the export incentive consultant.

Export this to Excel and send it; the columns are the ones the consultant asks
for (shipping details, bank details, payment details).
"""

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{"label": _("Shipment"), "fieldname": "name", "fieldtype": "Link",
		 "options": "Export Shipment", "width": 140},
		{"label": _("Invoice No"), "fieldname": "sales_invoice", "fieldtype": "Link",
		 "options": "Sales Invoice", "width": 110},
		{"label": _("Invoice Date"), "fieldname": "invoice_date", "fieldtype": "Date",
		 "width": 100},
		{"label": _("Invoice Value"), "fieldname": "invoice_amount", "fieldtype": "Currency",
		 "options": "currency", "width": 120},
		{"label": _("Currency"), "fieldname": "currency", "fieldtype": "Link",
		 "options": "Currency", "width": 80},
		{"label": _("Consignee"), "fieldname": "consignee_name", "fieldtype": "Data",
		 "width": 180},
		{"label": _("Destination Country"), "fieldname": "country_of_final_destination",
		 "fieldtype": "Data", "width": 130},
		{"label": _("HSN Code(s)"), "fieldname": "hsn_codes", "fieldtype": "Data", "width": 120},
		{"label": _("Shipping Bill No"), "fieldname": "shipping_bill_no", "fieldtype": "Data",
		 "width": 120},
		{"label": _("Shipping Bill Date"), "fieldname": "shipping_bill_date", "fieldtype": "Date",
		 "width": 115},
		{"label": _("Port Code"), "fieldname": "port_code", "fieldtype": "Data", "width": 85},
		{"label": _("Port of Loading"), "fieldname": "port_of_loading", "fieldtype": "Data",
		 "width": 140},
		{"label": _("BL / AWB No"), "fieldname": "bl_no", "fieldtype": "Data", "width": 120},
		{"label": _("BL Date"), "fieldname": "bl_date", "fieldtype": "Date", "width": 95},
		{"label": _("XAR No"), "fieldname": "xar_no", "fieldtype": "Data", "width": 110},
		{"label": _("XAR Date"), "fieldname": "xar_date", "fieldtype": "Date", "width": 95},
		{"label": _("Bank Charges"), "fieldname": "bank_charges", "fieldtype": "Currency",
		 "options": "currency", "width": 110},
		{"label": _("Payment Received On"), "fieldname": "final_payment_date", "fieldtype": "Date",
		 "width": 125},
		{"label": _("EBRC No"), "fieldname": "ebrc_no", "fieldtype": "Data", "width": 110},
		{"label": _("EBRC Date"), "fieldname": "ebrc_date", "fieldtype": "Date", "width": 95},
		{"label": _("Bank"), "fieldname": "bank_name", "fieldtype": "Data", "width": 160},
		{"label": _("Bank A/C No"), "fieldname": "bank_account_no", "fieldtype": "Data",
		 "width": 120},
		{"label": _("AD Code / IFSC"), "fieldname": "ifsc_code", "fieldtype": "Data", "width": 110},
		{"label": _("Incentive Status"), "fieldname": "incentive_status", "fieldtype": "Data",
		 "width": 120},
		{"label": _("Details Sent On"), "fieldname": "master_details_sent_on", "fieldtype": "Date",
		 "width": 115},
		{"label": _("RoDTEP Scrip"), "fieldname": "rodtep_scrip_no", "fieldtype": "Data",
		 "width": 120},
	]


def get_data(filters):
	conditions = ["1 = 1"]
	values = {}

	if filters.get("company"):
		conditions.append("s.company = %(company)s")
		values["company"] = filters.get("company")
	if filters.get("from_date") and filters.get("to_date"):
		conditions.append("s.shipping_bill_date between %(from_date)s and %(to_date)s")
		values["from_date"] = filters.get("from_date")
		values["to_date"] = filters.get("to_date")
	if filters.get("incentive_status"):
		conditions.append("s.incentive_status = %(incentive_status)s")
		values["incentive_status"] = filters.get("incentive_status")
	if not filters.get("include_unclosed"):
		# the consultant can only file once the EBRC exists
		conditions.append("ifnull(s.ebrc_no, '') != ''")

	rows = frappe.db.sql(
		"""
		select
			s.name, s.sales_invoice, si.posting_date as invoice_date, s.invoice_amount,
			s.currency, s.consignee_name, s.country_of_final_destination, s.shipping_bill_no,
			s.shipping_bill_date, s.port_code, s.port_of_loading, s.bl_no, s.bl_date,
			s.xar_no, s.xar_date, s.bank_charges, s.final_payment_date, s.ebrc_no, s.ebrc_date,
			s.incentive_status, s.master_details_sent_on, s.rodtep_scrip_no
		from `tabExport Shipment` s
		left join `tabSales Invoice` si on si.name = s.sales_invoice
		where {conditions}
		order by s.shipping_bill_date asc
		""".format(conditions=" and ".join(conditions)),
		values,
		as_dict=True,
	)

	settings = frappe.get_cached_doc("Export Tracker Settings")
	for row in rows:
		row.bank_name = settings.banker_name
		row.bank_account_no = settings.bank_account_no
		row.ifsc_code = settings.ifsc_code
		row.hsn_codes = get_hsn_codes(row.sales_invoice)

	return rows


def get_hsn_codes(sales_invoice):
	if not sales_invoice:
		return ""

	codes = frappe.db.sql_list(
		"""
		select distinct gst_hsn_code
		from `tabSales Invoice Item`
		where parent = %s and ifnull(gst_hsn_code, '') != ''
		""",
		sales_invoice,
	)
	return ", ".join(codes)
