"""End-to-end UAT for erpnext_export_tracker. Rolls everything back at the end."""

import frappe
from frappe.utils import add_days, today

PASS, FAIL = [], []


def check(label, cond, detail=""):
	(PASS if cond else FAIL).append(label)
	print("%s  %s%s" % ("PASS" if cond else "FAIL", label, (" -- " + str(detail)) if detail else ""))


def expect_throw(label, fn):
	try:
		fn()
	except frappe.ValidationError as e:
		check(label, True, str(e)[:110].replace("\n", " "))
		return
	except Exception as e:
		check(label, False, "wrong exception: %r" % e)
		return
	check(label, False, "no exception raised")


frappe.init(site="supreme.localhost")
frappe.connect()


def pick(doctype, preferred, filters):
	"""The first preferred name that still exists here, else anything matching.

	The chart of accounts and the warehouse tree get restructured between
	releases. A pinned name that has since been renamed reads as a test failure
	when it is really site housekeeping, so prefer the documented name and fall
	back to a live one.
	"""
	for name in preferred:
		# the preference has to satisfy the same filters -- an account that has
		# since become a group account still "exists" but cannot be posted to
		if frappe.db.get_value(doctype, dict(filters, name=name), "name"):
			return name
	return frappe.db.get_value(doctype, filters, "name")

frappe.set_user("Administrator")
frappe.flags.in_test = True

CUSTOMER = "A1 Poultry Farm"
ITEM = "SE-AO-FS-300011"
COMPANY = "Supreme Equipments Pvt Ltd"
WAREHOUSE = "P1 - Central / Main Store - SEPL"
if frappe.db.get_value("Warehouse", WAREHOUSE, "disabled") != 0:
	WAREHOUSE = frappe.db.get_value(
		"Warehouse", {"company": COMPANY, "is_group": 0, "disabled": 0}, "name"
	)
INCOME = pick("Account", ["Sales Account - Cages - SEPL - SEPL", "Sales Export - SEPL"],
	{"company": COMPANY, "root_type": "Income", "is_group": 0})
COST_CENTER = "Main - SEPL"
DEBIT_TO = pick("Account", ["Sundry Debtors - Corporate - SEPL",
	"Sundry Debtors - Cages - Corporate - SEPL"],
	{"company": COMPANY, "account_type": "Receivable", "is_group": 0})

print("\n=== 1. Sales Order with Is Export -> auto-create shipment ===")
so = frappe.new_doc("Sales Order")
so.customer = CUSTOMER
so.company = COMPANY
so.currency = "USD"
so.conversion_rate = 93.0
so.transaction_date = today()
so.delivery_date = add_days(today(), 30)
so.incoterm = "CIF"
so.named_place = "MOMBASA PORT"
so.custom_is_export = 1
so.custom_consignee_name = "M/S. ROYAL AGROVET LTD."
so.custom_consignee_address = "Plot No. 705, Mawanda Road,\nP.O. Box 11194, Kampala - Uganda"
so.custom_port_of_discharge = "MOMBASA PORT"
so.custom_final_destination = "UGANDA"
so.custom_country_of_final_destination = "UGANDA"
so.custom_terms_of_payment = "100% ADVANCE"
so.append("items", {
	"item_code": ITEM, "qty": 700, "rate": 3.46, "uom": "Nos",
	"warehouse": WAREHOUSE, "delivery_date": add_days(today(), 30),
})
so.insert()
so.submit()
check("Sales Order submitted", so.docstatus == 1, so.name)

shipments = frappe.get_all("Export Shipment", {"sales_order": so.name}, ["name", "status"])
check("Export Shipment auto-created on submit", len(shipments) == 1, shipments)
ship = frappe.get_doc("Export Shipment", shipments[0].name)
check("initial state is Order Confirmed", ship.status == "Order Confirmed", ship.status)
check("consignee copied from order", ship.consignee_name == "M/S. ROYAL AGROVET LTD.")
check("terms copied from order", ship.terms_of_payment == "100% ADVANCE")
check("port of discharge copied", ship.port_of_discharge == "MOMBASA PORT")
check("defaults from settings applied",
      ship.port_of_loading == "NHAVA SHEVA SEA PORT, INDIA" and ship.pre_carriage_by == "BY ROAD",
      "%s / %s" % (ship.port_of_loading, ship.pre_carriage_by))
check("CIF auto-set insurance required", ship.insurance_required == 1)
check("SO back-link set", frappe.db.get_value("Sales Order", so.name, "custom_export_shipment") == ship.name)

print("\n=== 2. non-export Sales Order must NOT create a shipment ===")
so2 = frappe.new_doc("Sales Order")
so2.customer = CUSTOMER
so2.company = COMPANY
so2.transaction_date = today()
so2.delivery_date = add_days(today(), 30)
so2.append("items", {"item_code": ITEM, "qty": 1, "rate": 100, "warehouse": WAREHOUSE,
                     "delivery_date": add_days(today(), 30)})
so2.insert()
so2.submit()
check("no shipment for domestic order",
      frappe.db.count("Export Shipment", {"sales_order": so2.name}) == 0)

print("\n=== 3. CHA freight comparison gate (SOP G.c.i.1-2) ===")
ship.status = "Freight Finalised"
expect_throw("blocked: freight finalised with no selected CHA", ship.save)

ship.reload()
cha = frappe.db.get_value("Supplier", {"supplier_group": "CHA"}, "name") or frappe.db.get_value(
	"Supplier", {}, "name")
cha2 = frappe.db.get_value("Supplier", {"name": ["!=", cha]}, "name")
ship.freight_currency = "USD"
ship.append("cha_quotes", {"cha": cha, "quote_date": today(), "currency": "USD",
                           "freight_amount": 3350, "other_charges": 290, "transit_days": 22,
                           "free_days": 14})
ship.append("cha_quotes", {"cha": cha2, "quote_date": today(), "currency": "USD",
                           "freight_amount": 3100, "other_charges": 500, "transit_days": 30,
                           "free_days": 7})
ship.save()
check("quote totals computed",
      [q.total_amount for q in ship.cha_quotes] == [3640, 3600],
      [q.total_amount for q in ship.cha_quotes])

ship.cha_quotes[0].is_selected = 1
ship.cha_quotes[1].is_selected = 1
expect_throw("blocked: two CHA quotes selected", ship.save)

ship.reload()
ship.cha_quotes[0].is_selected = 1
ship.save()
check("selected CHA mirrored to parent",
      ship.selected_cha == cha and ship.selected_freight_amount == 3640
      and ship.selected_transit_days == 22 and ship.selected_free_days == 14,
      "%s / %s / %s d / %s free" % (ship.selected_cha, ship.selected_freight_amount,
                                    ship.selected_transit_days, ship.selected_free_days))

ship.status = "Indent Approved"
ship.save()
ship.status = "Freight Finalised"
ship.save()
check("freight finalised passes with a selected quote", ship.status == "Freight Finalised")

print("\n=== 4. country-driven document checklist ===")
ship.destination_country = "Uganda"
ship.save()
result = ship.load_document_checklist()
ship.save()
ship.reload()
check("template resolved by destination country",
      result["template"] == "Uganda - Standard", result)
pre = [d.document_name for d in ship.pre_shipment_documents]
post = [d.document_name for d in ship.post_shipment_documents]
check("SGS certificate pulled in for Uganda", "SGS Certificate" in pre, pre)
check("pre + post rows loaded", len(pre) == 11 and len(post) == 5,
      "%d pre / %d post" % (len(pre), len(post)))

print("\n=== 5. destination compliance (SOP sections 2C and 16) ===")
check("Uganda profile switched inspection on", ship.inspection_required == 1)
check("inspection agency came from the profile", ship.inspection_agency == "SGS",
      ship.inspection_agency)

print("\n=== 5b. document-completion gate (SOP G.c.i.5) ===")
ship.dispatch_plan_date = today()
ship.status = "Dispatch Planned"
ship.save()
ship.status = "Customs Docs Prepared"
expect_throw("blocked: customs docs stage with unprepared documents", ship.save)

ship.reload()
for row in ship.pre_shipment_documents:
	row.prepared = 1
ship.status = "Customs Docs Prepared"
expect_throw("blocked: customs docs stage without a shipment type", ship.save)

ship.reload()
for row in ship.pre_shipment_documents:
	row.prepared = 1
ship.shipment_type = "FCL"
ship.status = "Customs Docs Prepared"
expect_throw("blocked: customs docs stage with the inspection still open", ship.save)

ship.reload()
for row in ship.pre_shipment_documents:
	row.prepared = 1
ship.shipment_type = "FCL"
ship.inspection_status = "Final Report"
ship.inspection_report_no = "SGS/UG/2026/0041"
ship.status = "Customs Docs Prepared"
ship.save()
check("customs docs stage passes when all prepared", ship.status == "Customs Docs Prepared")

print("\n=== 6. container / shipping gates ===")
ship.status = "Container Loaded"
expect_throw("blocked: container loaded without seals", ship.save)

ship.reload()
ship.loading_date = today()
ship.container_no = "MSBU7434841"
ship.no_of_containers = 3
ship.container_type = "40 HC"
ship.customs_seal_no = "CUS-99881"
ship.shipping_line_seal_no = "SL-77120"
ship.net_weight = 7060
ship.gross_weight = 7080
ship.no_of_packages = 426
ship.status = "Container Loaded"
ship.save()
check("container loaded passes with seals", ship.status == "Container Loaded")

ship.status = "Shipped"
expect_throw("blocked: shipped without shipping bill", ship.save)

ship.reload()
ship.shipping_bill_no = "7412563"
ship.shipping_bill_date = today()
ship.port_code = "INNSA1"
ship.etd = today()
ship.eta = add_days(today(), 22)
ship.vessel_flight_no = "MSC ANNA / 431W"
ship.status = "Shipped"
ship.save()
check("shipped passes with shipping bill + ETD", ship.status == "Shipped")

print("\n=== 7. post-shipment + management signature gates ===")
for row in ship.post_shipment_documents:
	row.prepared = 1
ship.status = "Post-Shipment Docs Prepared"
expect_throw("blocked: post-shipment without BL number", ship.save)

ship.reload()
for row in ship.post_shipment_documents:
	row.prepared = 1
ship.bl_no = "MEDUJ1234567"
ship.bl_date = today()
ship.bl_type = "Seaway Bill of Lading (Telex BL)"
ship.coo_type = "MACCIA / Federation"
ship.status = "Post-Shipment Docs Prepared"
expect_throw("blocked: COO type set but no COO number", ship.save)

ship.reload()
for row in ship.post_shipment_documents:
	row.prepared = 1
ship.bl_no = "MEDUJ1234567"
ship.bl_date = today()
ship.coo_type = "MACCIA / Federation"
ship.coo_no = "MACCIA/2026/8891"
ship.coo_date = today()
ship.insurance_policy_no = "NIA-MAR-556677"
ship.insurance_policy_date = today()
ship.status = "Post-Shipment Docs Prepared"
ship.save()
check("post-shipment passes when complete", ship.status == "Post-Shipment Docs Prepared")

ship.status = "Docs Submitted"
expect_throw("blocked: docs submitted without management signature", ship.save)

ship.reload()
ship.management_signed = 1
ship.docs_submitted_on = today()
ship.status = "Docs Submitted"
ship.save()
check("management signature stamped",
      ship.management_signed_by == "Administrator" and ship.management_signed_on,
      "%s on %s" % (ship.management_signed_by, ship.management_signed_on))

print("\n=== 8. bank closure blocked until fully paid (SOP I) ===")
ship.status = "Payment Received"
expect_throw("blocked: closure before final payment", ship.save)

print("\n=== 9. Export Invoice with the printout's charge build-up ===")
si = frappe.new_doc("Sales Invoice")
si.naming_series = "EXP/.###"
si.customer = CUSTOMER
si.company = COMPANY
si.currency = "USD"
si.conversion_rate = 93.0
si.posting_date = today()
si.debit_to = DEBIT_TO
si.incoterm = "CIF"
si.named_place = "MOMBASA PORT"
si.custom_is_export = 1
si.custom_export_shipment = ship.name
si.custom_consignee_name = "M/S. ROYAL AGROVET LTD."
si.custom_consignee_address = "Plot No. 705, Mawanda Road,\nP.O. Box 11194, Kampala - Uganda"
si.custom_pre_carriage_by = "BY ROAD"
si.custom_place_of_receipt = "NASHIK"
si.custom_port_of_loading = "NHAVA SHEVA SEA PORT, INDIA"
si.custom_port_of_discharge = "MOMBASA PORT"
si.custom_final_destination = "UGANDA"
si.custom_country_of_origin = "INDIA"
si.custom_country_of_final_destination = "UGANDA"
si.custom_container_no = "MSBU7434841 [3]"
si.custom_marks_and_nos = "SUPREME EQUIPMENTS PVT. LTD.\n\nM/S. ROYAL AGROVET LTD."
si.custom_net_weight = 7060
si.custom_gross_weight = 7080
si.custom_no_of_packages = 426
si.custom_terms_of_payment = "100% ADVANCE"
si.custom_goods_description = "Poultry Keeping Equipments & parts in ckd condition"

for qty, rate in ((700, 3.46), (10000, 0.42), (600, 3.20), (600, 3.66),
                  (2000, 3.12), (1800, 3.14), (25, 27.00), (300, 0.68)):
	si.append("items", {
		"item_code": ITEM, "qty": qty, "rate": rate, "uom": "Nos",
		"income_account": INCOME, "cost_center": COST_CENTER, "warehouse": WAREHOUSE,
	})

FREIGHT_ACC = pick("Account", ["Clearing & Forwarding Charges -Export - SEPL",
	"Clearing & Forwarding Charges -Export - RD - SEPL"],
	{"company": COMPANY, "is_group": 0, "name": ["like", "%Forwarding%Export%"]})
INSURANCE_ACC = pick("Account", ["Insurance Charges - SEPL",
	"Marine Insurance - Export - SEPL"],
	{"company": COMPANY, "is_group": 0, "name": ["like", "%Insurance%"]})
for desc, amount, acc in (
	("LOCAL TRANSPORTATION AND FREIGHT UPTO MOMBASA PORT", 3350, FREIGHT_ACC),
	("SGS CHARGES", 290, FREIGHT_ACC),
	("INSURANCE", 125, INSURANCE_ACC),
):
	si.append("taxes", {
		"charge_type": "Actual", "account_head": acc,
		"description": desc, "tax_amount": amount, "cost_center": COST_CENTER,
	})

si.set_missing_values()
si.insert()
check("invoice used the EXP series", si.name.startswith("EXP/"), si.name)
check("ex-works total = 23,509", round(si.net_total, 2) == 23509.00, si.net_total)
check("CIF total = 27,274", round(si.grand_total, 2) == 27274.00, si.grand_total)
check("amount in words rendered", "Twenty Seven Thousand" in (si.in_words or ""), si.in_words)

si.submit()
ship.reload()
check("invoice linked to shipment on submit", ship.sales_invoice == si.name, ship.sales_invoice)
check("invoice amount pulled onto shipment", round(ship.invoice_amount, 2) == 27274.00,
      ship.invoice_amount)
check("payment status Unpaid before receipt", ship.payment_status == "Unpaid",
      ship.payment_status)

print("\n=== 10. Export Invoice print format renders ===")
html = frappe.get_print("Sales Invoice", si.name, print_format="Export Invoice")
for needle in ("EXPORT INVOICE", "3111025713", "GNX200", "AAOCS5679N", "KOTAK MAHINDRA BANK LTD.",
               "KKBKINBB", "9412246419", "MOMBASA PORT", "NHAVA SHEVA SEA PORT, INDIA",
               "MSBU7434841 [3]", "TOTAL EX-WORKS AMOUNT", "SGS CHARGES",
               "84369900", "7060.000 KGS", "426 PACKAGES", "VIDYA RIJAL",
               "Poultry Keeping Equipments &amp; parts in ckd condition"):
	check("print contains %r" % needle, needle in html)
check("print shows the CIF grand total", "27,274.00" in html)
check("print has all 8 item rows", html.count("<tr>") > 20)

print("\n=== 11. payment -> closure chain ===")
pe = frappe.new_doc("Payment Entry")
pe.payment_type = "Receive"
pe.company = COMPANY
pe.party_type = "Customer"
pe.party = CUSTOMER
pe.posting_date = today()
pe.reference_no = "TT-99881"
pe.reference_date = today()
pe.paid_from = DEBIT_TO
pe.paid_from_account_currency = "INR"
pe.paid_to = "KOTAK MAHINDRA BANK OD NO. - 6396 - SEPL"
pe.source_exchange_rate = 1
pe.target_exchange_rate = 1
pe.paid_amount = 27274.00 * 93.0
pe.received_amount = 27274.00 * 93.0
pe.append("references", {"reference_doctype": "Sales Invoice", "reference_name": si.name,
                         "total_amount": 27274.00 * 93.0, "outstanding_amount": 27274.00 * 93.0,
                         "allocated_amount": 27274.00 * 93.0})
pe.insert()
pe.submit()

ship.reload()
check("payment status Fully Paid after receipt", ship.payment_status == "Fully Paid",
      "%s / outstanding %s" % (ship.payment_status, ship.outstanding_amount))
check("final payment date stamped", bool(ship.final_payment_date), ship.final_payment_date)

ship.status = "Payment Received"
ship.save()
check("closure now allowed", ship.status == "Payment Received")

ship.status = "XAR Generated"
expect_throw("blocked: XAR state without XAR number", ship.save)

ship.reload()
ship.xar_no = "XAR20260730001"
ship.xar_date = today()
ship.bank_charges = 45
ship.status = "XAR Generated"
ship.save()
check("XAR recorded", ship.status == "XAR Generated")

ship.status = "Bank Submission Done"
ship.save()
check("bank submission passes (SB + port code present)", ship.status == "Bank Submission Done",
      ship.bank_submission_date)

ship.status = "EBRC Generated"
expect_throw("blocked: EBRC state without EBRC number", ship.save)

ship.reload()
ship.ebrc_no = "EBRC/2026/0099887"
ship.ebrc_date = today()
ship.status = "EBRC Generated"
ship.save()
check("shipment closed with EBRC", ship.status == "EBRC Generated")

print("\n=== 12. Export Indent (SOP G.a) ===")
from erpnext_export_tracker.export_tracker.doctype.export_indent.export_indent import (
	make_export_indent,
)
indent_name = make_export_indent(so.name)
indent = frappe.get_doc("Export Indent", indent_name)
check("indent created from order", indent.status == "Draft" and len(indent.items) == 1,
      indent_name)
check("indent totals computed", indent.total_qty == 700 and round(indent.total_amount, 2) == 2422.00,
      "%s qty / %s" % (indent.total_qty, indent.total_amount))

indent.management_approved = 1
expect_throw("blocked: management approval before production confirmation", indent.save)

indent.reload()
indent.production_confirmed = 1
indent.technical_specs = None
indent.save()
check("production confirmation stamped",
      indent.status == "Production Confirmed" and indent.production_confirmed_by == "Administrator")
indent.management_approved = 1
indent.save()
check("management approval passes after production", indent.status == "Management Approved")

print("\n=== 13. shipment-based letters render ===")
for pf in ("Bill of Exchange", "Dispatch Declaration", "Letter of Undertaking",
           "Request Letter to Bank", "Export Value Declaration", "SCOMET Letter",
           "Insurance Declaration"):
	try:
		out = frappe.get_print("Export Shipment", ship.name, print_format=pf)
		check("renders: %s" % pf, len(out) > 500 and "Traceback" not in out, "%d chars" % len(out))
	except Exception as e:
		check("renders: %s" % pf, False, repr(e)[:140])

for pf, dt, name in (("Export Packing List", "Sales Invoice", si.name),
                     ("Export Proforma Invoice", "Sales Order", so.name)):
	try:
		out = frappe.get_print(dt, name, print_format=pf)
		check("renders: %s" % pf, len(out) > 500, "%d chars" % len(out))
	except Exception as e:
		check("renders: %s" % pf, False, repr(e)[:140])

print("\n=== 14. reports execute ===")
for report in ("Export Shipment Status", "Pending Export Documents",
               "Export Outstanding Payment Statement", "Export Bank Closure Ageing",
               "Export Incentive Master Details", "Export Quotation Follow-up"):
	try:
		from frappe.desk.query_report import run as run_report
		res = run_report(report, filters={"company": COMPANY}, ignore_prepared_report=True)
		check("report runs: %s" % report, "columns" in res,
		      "%d row(s)" % len(res.get("result") or []))
	except Exception as e:
		check("report runs: %s" % report, False, repr(e)[:140])

print("\n=== 15. cancel protection ===")
expect_throw("blocked: cancelling an order with a live shipment", so.cancel)

print("\n=== 16. daily reminder task runs ===")
try:
	from erpnext_export_tracker import tasks
	frappe.flags.mute_emails = True
	tasks.send_export_reminders()
	check("send_export_reminders completes", True)
except Exception as e:
	check("send_export_reminders completes", False, repr(e)[:200])

print("\n" + "=" * 62)
print("PASSED: %d    FAILED: %d" % (len(PASS), len(FAIL)))
if FAIL:
	print("\nFailures:")
	for f in FAIL:
		print("  -", f)
print("=" * 62)

frappe.db.rollback()
print("\nrolled back -- no test data persisted")
