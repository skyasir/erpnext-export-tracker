"""Build a walkthrough set of Export Tracker entries on a site.

Three shipments, deliberately left at three different stages so the guidance
panel, the freight comparison and the closure checklist all have something real
to show:

  A  Nigeria  CIF  under a Letter of Credit   walked all the way to EBRC Generated
  B  Uganda   FOB  through the bank           parked at Freight Finalised
  C  Malawi   CIF  direct to the client       fresh, waiting on indent approval

Everything is tagged DEMO and tied to three demo customers, so
`clean_demo_data.py` can take it all out again.

    cd <bench>/sites
    ../env/bin/python ../apps/erpnext_export_tracker/tests/seed_demo_data.py
"""

import frappe
from frappe.utils import add_days, today

frappe.init(site="supreme.localhost")
frappe.connect()
frappe.set_user("Administrator")

TAG = "DEMO - Export Tracker walkthrough"
COMPANY = frappe.db.get_value("Company", {}, "name")


def pick(doctype, preferred, filters):
	"""The first preferred name that still satisfies the filters, else any match."""
	for name in preferred:
		if frappe.db.get_value(doctype, dict(filters, name=name), "name"):
			return name
	return frappe.db.get_value(doctype, filters, "name")


ITEM = (frappe.db.get_value("Item", {"is_stock_item": 1, "disabled": 0, "has_variants": 0,
	"is_sales_item": 1, "item_name": ["like", "%Cage%"]}, "name")
	or pick("Item", [], {"is_stock_item": 1, "disabled": 0, "has_variants": 0, "is_sales_item": 1}))
WAREHOUSE = pick("Warehouse", ["P1 - Central / Main Store - SEPL"],
	{"company": COMPANY, "is_group": 0, "disabled": 0})
INCOME = pick("Account", ["Sales Export - SEPL"],
	{"company": COMPANY, "root_type": "Income", "is_group": 0})
COST_CENTER = pick("Cost Center", ["Main - SEPL"], {"company": COMPANY, "is_group": 0})
DEBIT_TO = pick("Account", ["Sundry Debtors - Cages - Corporate - SEPL"],
	{"company": COMPANY, "account_type": "Receivable", "is_group": 0})
BANK = pick("Account", ["KOTAK MAHINDRA BANK OD NO. - 6396 - SEPL"],
	{"company": COMPANY, "account_type": "Bank", "is_group": 0})
FREIGHT_ACC = pick("Account", ["Clearing & Forwarding Charges -Export - RD - SEPL"],
	{"company": COMPANY, "is_group": 0, "name": ["like", "%Forwarding%Export%"]})
INSURANCE_ACC = pick("Account", ["Marine Insurance - Export - SEPL"],
	{"company": COMPANY, "is_group": 0, "name": ["like", "%Insurance%"]})
# India Compliance refuses a sales transaction that cannot resolve the company
# GSTIN, and it resolves it from the company address
COMPANY_ADDRESS = frappe.db.sql("""
	select a.name from tabAddress a
	join `tabDynamic Link` d on d.parent = a.name
	where d.link_doctype = 'Company' and d.link_name = %s
	order by a.is_primary_address desc limit 1""", COMPANY)
COMPANY_ADDRESS = COMPANY_ADDRESS[0][0] if COMPANY_ADDRESS else None
def demo_customer(label, country, city):
	"""Customer is named by series here, so look it up by customer_name and return
	the real docname -- the Address link needs that, not the label.

	GST Category "Overseas" matters: India Compliance refuses a sales transaction
	whose party has no category set.
	"""
	name = frappe.db.get_value("Customer", {"customer_name": label}, "name")
	if not name:
		name = frappe.get_doc({
			"doctype": "Customer", "customer_name": label, "customer_type": "Company",
			"gst_category": "Overseas",
			"customer_group": frappe.db.get_value("Customer Group", {"is_group": 0}, "name"),
			"territory": frappe.db.get_value("Territory", {"is_group": 0}, "name"),
		}).insert(ignore_permissions=True).name

	if not frappe.db.exists("Address", {"address_title": label, "address_type": "Billing"}):
		frappe.get_doc({
			"doctype": "Address", "address_title": label, "address_type": "Billing",
			"address_line1": "%s Industrial Area" % city, "city": city, "country": country,
			"gst_category": "Overseas", "is_primary_address": 1,
			"links": [{"link_doctype": "Customer", "link_name": name}],
		}).insert(ignore_permissions=True)
	return name


for _country, _city in (("Nigeria", "Lagos"), ("Uganda", "Kampala"), ("Malawi", "Lilongwe")):
	demo_customer("Demo Buyer %s (Export Tracker)" % _country, _country, _city)
frappe.db.commit()

CUST = {c: frappe.db.get_value("Customer",
	{"customer_name": "Demo Buyer %s (Export Tracker)" % c}, "name")
	for c in ("Nigeria", "Uganda", "Malawi")}
CHA = (frappe.get_all("Supplier", filters={"supplier_group": "CHA"}, pluck="name", limit=3)
	or frappe.get_all("Supplier", pluck="name", limit=3))

created = []


def already(customer):
	return frappe.db.get_value("Export Shipment", {"customer": customer, "docstatus": ["<", 2]},
	                           "name")


def make_so(customer, incoterm, place, lines, consignee, terms):
	so = frappe.new_doc("Sales Order")
	so.customer = customer
	so.company = COMPANY
	so.currency = "USD"
	so.conversion_rate = 93.0
	so.transaction_date = today()
	so.delivery_date = add_days(today(), 45)
	so.incoterm = incoterm
	so.named_place = place
	so.company_address = COMPANY_ADDRESS
	so.custom_is_export = 1
	so.custom_consignee_name = consignee
	so.custom_terms_of_payment = terms
	for qty, price in lines:
		so.append("items", {"item_code": ITEM, "qty": qty, "rate": price,
		                    "warehouse": WAREHOUSE, "delivery_date": add_days(today(), 45)})
	so.insert()
	so.submit()
	return so


def make_indent(so, approve):
	ind = frappe.new_doc("Export Indent")
	ind.sales_order = so.name
	ind.customer = so.customer
	ind.company = COMPANY
	ind.indent_date = today()
	ind.currency = so.currency
	ind.remarks = TAG
	for row in so.items:
		ind.append("items", {"item_code": row.item_code, "qty": row.qty, "uom": row.uom,
		                     "rate": row.rate, "currency": so.currency})
	ind.insert()
	if approve:
		ind.production_confirmed = 1
		ind.technical_specs = "CKD packing, hot-dip galvanised."
		ind.save()
		ind.management_approved = 1
		ind.save()
	return ind


def add_quotes(ship):
	rows = [
		(CHA[0], 2450, 180, 145, 60, 90, 26, 14, "MSC ANNA", 12),
		(CHA[1], 2280, 210, 145, 75, 120, 31, 21, "MAERSK KOWLOON", 9),
		(CHA[2], 2610, 160, 145, 55, 40, 22, 10, "CMA CGM JULES VERNE", 15),
	]
	for cha, fr, local, thc, doc, other, transit, free, vessel, offset in rows:
		ship.append("cha_quotes", {
			"cha": cha, "quote_date": today(), "currency": "USD",
			"container_type": "1 x 40 HC", "freight_amount": fr, "local_charges": local,
			"thc": thc, "documentation_charges": doc, "other_charges": other,
			"transit_days": transit, "free_days": free, "vessel": vessel,
			"etd": add_days(today(), offset), "eta": add_days(today(), offset + transit),
		})


def production_history(ship, weeks):
	for n, (status, done, pending, packing) in enumerate(weeks, start=1):
		ship.append("production_updates", {
			"week_ending": add_days(today(), -7 * (len(weeks) - n)),
			"production_status": status, "qty_completed": done, "qty_pending": pending,
			"packing_status": packing,
			"expected_completion_date": add_days(today(), 7),
			"remarks": TAG,
		})


# =====================================================================
# A -- Nigeria, CIF, under a Letter of Credit, walked all the way to EBRC
# =====================================================================
if already(CUST["Nigeria"]):
	print("\nA: already seeded ->", already(CUST["Nigeria"]))
else:
	print("\n=== A: Nigeria / CIF / LC -- full lifecycle ===")
	so = make_so(CUST["Nigeria"], "CIF", "APAPA PORT, LAGOS",
	             [(240, 46.50), (600, 12.80), (120, 33.00)],
	             "ROYAL AGRO NIGERIA LTD.", "IRREVOCABLE LC AT SIGHT")
	# the indent's save touches the shipment, so build it before loading the
	# shipment or the in-memory copy is stale on the first save
	indent = make_indent(so, approve=True)
	ship = frappe.get_doc("Export Shipment", {"sales_order": so.name})
	created.append(("Export Shipment", ship.name))
	print("   shipment:", ship.name, "| country:", ship.destination_country,
	      "| inspection:", ship.inspection_required, "| Form M:", ship.form_m_required,
	      "| COO:", ship.coo_type)

	ship.payment_route = "Through Letter of Credit"
	ship.consignee_address = "Plot 14, Amuwo Odofin Industrial Estate\nApapa, Lagos - Nigeria"
	ship.notify_name = "ROYAL AGRO NIGERIA LTD."
	ship.buyer_same_as_consignee = 1
	ship.port_of_discharge = "APAPA PORT, LAGOS"
	ship.final_destination = "NIGERIA"
	ship.shipment_type = "FCL"
	ship.mode = "Sea"
	ship.remarks = TAG
	ship.export_indent = indent.name
	ship.status = "Indent Approved"
	ship.save()

	# -- freight: three forwarders, pick the cheapest landed total
	add_quotes(ship)
	ship.cha_quotes[1].is_selected = 1
	ship.route = "NHAVA SHEVA - APAPA (direct)"
	ship.route_verified = 1
	ship.destination_charges = 340
	ship.booking_no = "BKG-NG-77412"
	ship.booking_date = today()
	ship.voyage_no = "241W"
	ship.cutoff_date = add_days(today(), 7)
	ship.si_cutoff = add_days(today(), 6)
	ship.vgm_cutoff = add_days(today(), 6)
	ship.doc_cutoff = add_days(today(), 5)
	ship.status = "Freight Finalised"
	ship.save()
	print("   freight: %s @ %s (landed totals %s)" % (
		ship.selected_cha, ship.selected_freight_amount,
		[q.total_amount for q in ship.cha_quotes]))

	# -- Nigeria's pre-shipment finance formality
	ship.form_m_no = "MF20260912345"
	ship.form_m_date = add_days(today(), -20)
	ship.form_m_status = "Approved"
	ship.form_m_approved_on = add_days(today(), -14)
	ship.ba_no = "BA/2026/00891"
	ship.ba_date = add_days(today(), -12)
	ship.dispatch_plan_date = add_days(today(), 3)
	ship.status = "Dispatch Planned"
	ship.save()

	# -- SONCAP inspection, then the pre-shipment checklist
	production_history(ship, [
		("In Production", 300, 660, "Not Started"),
		("Partially Ready", 700, 260, "In Progress"),
		("Ready", 960, 0, "Completed"),
	])
	ship.inspection_agent = "SGS Nigeria - Lagos office"
	ship.inspection_location = "Nashik plant"
	ship.inspection_request_date = add_days(today(), -10)
	ship.inspection_date = add_days(today(), -6)
	ship.inspection_status = "Final Report"
	ship.inspection_report_no = "SONCAP/2026/NG/4471"
	ship.inspection_client_approved = 1
	ship.inspection_invoice_no = "SGS-INV-8821"
	ship.inspection_invoice_amount = 640
	ship.inspection_payment_status = "Paid"
	ship.save()

	result = ship.load_document_checklist()
	print("   checklist: %s (%s rows)" % (result["template"], result["added"]))
	for row in ship.pre_shipment_documents:
		row.prepared = 1
		row.document_date = today()
	ship.status = "Customs Docs Prepared"
	ship.save()

	# -- loading and sealing
	for n, (cno, pkgs, net, gross) in enumerate((
		("MSCU7734112", 214, 6120, 6310),
		("TGHU4419087", 198, 5840, 6020),
	), start=1):
		ship.append("containers", {
			"container_no": cno, "container_size": "40 HC", "seal_no": "CS-9911%d" % n,
			"no_of_packages": pkgs, "net_weight": net, "gross_weight": gross,
			"max_permissible_weight": 30480, "weighbridge": "Nashik Weighbridge",
			"vgm_weight": gross + 3800, "weighing_datetime": today() + " 09:30:00",
			"weighing_slip_no": "WB/2026/%d" % (5540 + n), "cargo_type": "NORMAL",
		})
	ship.append("packing_items", {
		"container_no": "MSCU7734112", "description": "Layer cage panels (CKD)",
		"qty_per_bundle": 4, "no_of_packages": 214, "weight_per_package": 28.6})
	ship.append("packing_items", {
		"container_no": "TGHU4419087", "description": "Feeder trays and fittings",
		"qty_per_bundle": 10, "no_of_packages": 198, "weight_per_package": 29.5})
	ship.loading_date = today()
	ship.customs_seal_no = "CS-99111"
	ship.shipping_line_seal_no = "SL-448210"
	ship.vgm_submitted = 1
	ship.form_13_received = 1
	ship.status = "Container Loaded"
	ship.save()
	print("   containers: %s | %s pkgs | net %s" % (
		ship.no_of_containers, ship.no_of_packages, ship.net_weight))

	# -- LC, shipping bill, e-seal, e-way bill
	ship.lc_no = "LC/FBN/2026/00417"
	ship.lc_issuing_bank = "First Bank of Nigeria"
	ship.lc_advising_bank = "Kotak Mahindra Bank, Mumbai"
	ship.lc_applicant = "ROYAL AGRO NIGERIA LTD."
	ship.lc_beneficiary = COMPANY
	ship.lc_amount = 24720
	ship.lc_presentation_days = 21
	ship.lc_draft_received_on = add_days(today(), -25)
	ship.lc_terms_reviewed = 1
	ship.lc_management_confirmed = 1
	ship.lc_acceptance_sent_on = add_days(today(), -22)
	ship.lc_received_on = add_days(today(), -18)
	ship.lc_expiry_date = add_days(today(), 45)
	ship.lc_last_shipment_date = add_days(today(), 20)
	ship.cha_docs_sent_on = add_days(today(), -2)
	ship.cha_checklist_status = "Approved"
	ship.cha_checklist_remarks = "HSN, value and container numbers verified."
	ship.shipping_bill_no = "7741209"
	ship.shipping_bill_date = today()
	ship.port_code = "INNSA1"
	ship.e_seal_no = "RFID-IN-88214471"
	ship.e_seal_date = today()
	ship.e_seal_provider = "ICEGATE approved vendor - Nashik"
	ship.e_seal_container_no = "MSCU7734112"
	ship.eway_bill_no = "381004472190"
	ship.eway_bill_date = today()
	ship.eway_validity_date = add_days(today(), 5)
	ship.vehicle_no = "MH15 GH 4471"
	ship.transporter = "Speed Cargo Movers"
	ship.lr_no = "LR/NSK/2026/1187"
	ship.lr_date = today()
	ship.etd = add_days(today(), 4)
	ship.eta = add_days(today(), 35)
	ship.vessel_flight_no = "MAERSK KOWLOON"
	ship.status = "Shipped"
	ship.save()

	# -- post-shipment set
	ship.coo_type = "CCVO (Nigeria)"
	ship.coo_application_no = "CCVO/APP/2026/2214"
	ship.coo_applied_on = today()
	ship.coo_no = "CCVO/2026/NG/0912"
	ship.coo_date = today()
	ship.coo_payment_done = 1
	ship.bl_type = "Original BL"
	ship.draft_bl_received_on = today()
	ship.draft_bl_sent_on = today()
	ship.bl_client_approved_on = today()
	ship.bl_no = "MAEU574412907"
	ship.bl_date = today()
	ship.insurance_company = "New India Assurance"
	ship.insurance_premium_requested_on = add_days(today(), -5)
	ship.insurance_premium_paid_on = add_days(today(), -3)
	ship.insurance_policy_no = "NIA/MAR/2026/77120"
	ship.insurance_policy_date = add_days(today(), -3)
	for row in ship.post_shipment_documents:
		row.prepared = 1
		row.document_date = today()
	ship.status = "Post-Shipment Docs Prepared"
	ship.save()

	ship.management_signed = 1
	ship.docs_courier_no = "DHL 4471209183"
	ship.submitted_to_bank = "Kotak Mahindra Bank, Nashik"
	ship.docs_emailed_on = today()
	ship.docs_emailed_to = "docs@royalagro.example"
	ship.client_acknowledged = 1
	ship.client_ack_date = today()
	ship.originals_required = 1
	ship.originals_address_confirmed = 1
	ship.courier_company = "DHL Express"
	ship.courier_tracking_no = "4471209183"
	ship.originals_dispatch_date = today()
	ship.originals_delivery_status = "Delivered"
	ship.originals_document_list = "Original BL (3/3), CCVO, Insurance Policy"
	ship.status = "Docs Submitted"
	ship.save()
	print("   docs submitted, signed by", ship.management_signed_by)
	frappe.db.commit()
	print("   A parked at:", ship.status)


# ---------------------------------------------------------------- A: closure
ship = frappe.get_doc("Export Shipment", {"customer": CUST["Nigeria"], "docstatus": ["<", 2]})
so = frappe.get_doc("Sales Order", ship.sales_order)
print("A =", ship.name, "at", ship.status)

if ship.status == "Docs Submitted":
	si = frappe.new_doc("Sales Invoice")
	si.naming_series = "EXP/.###"
	si.customer = ship.customer
	si.company = COMPANY
	si.currency = "USD"
	si.conversion_rate = 93.0
	si.posting_date = today()
	si.debit_to = DEBIT_TO
	# NOT company_address: with it set, India Compliance rebuilds the tax table on
	# an export invoice and drops the freight and insurance rows that make up the
	# CIF value. The Sales Order needs it; the invoice resolves its GSTIN anyway.
	si.incoterm = "CIF"
	si.named_place = "APAPA PORT, LAGOS"
	si.custom_is_export = 1
	si.custom_export_shipment = ship.name
	si.custom_consignee_name = "ROYAL AGRO NIGERIA LTD."
	si.custom_consignee_address = ("Plot 14, Amuwo Odofin Industrial Estate\n"
	                               "Apapa, Lagos - Nigeria")
	si.custom_pre_carriage_by = "BY ROAD"
	si.custom_place_of_receipt = "NASHIK"
	si.custom_port_of_loading = "NHAVA SHEVA SEA PORT, INDIA"
	si.custom_port_of_discharge = "APAPA PORT, LAGOS"
	si.custom_final_destination = "NIGERIA"
	si.custom_country_of_origin = "INDIA"
	si.custom_country_of_final_destination = "NIGERIA"
	si.custom_vessel_flight_no = "MAERSK KOWLOON"
	si.custom_container_no = "MSCU7734112 / TGHU4419087 [2]"
	si.custom_marks_and_nos = "SUPREME EQUIPMENTS PVT. LTD.\n\nROYAL AGRO NIGERIA LTD."
	si.custom_net_weight = 11960
	si.custom_gross_weight = 12330
	si.custom_no_of_packages = 412
	si.custom_terms_of_payment = "IRREVOCABLE LC AT SIGHT"
	si.custom_fob_value = 23180
	si.custom_goods_description = "Poultry Keeping Equipments & parts in ckd condition"
	for row in so.items:
		si.append("items", {
			"item_code": row.item_code, "qty": row.qty, "rate": row.rate, "uom": row.uom,
			"income_account": INCOME, "cost_center": COST_CENTER, "warehouse": WAREHOUSE,
			"sales_order": so.name, "so_detail": row.name,
		})
	# non-GST heads: India Compliance rejects GST heads on an export without payment of GST
	si.append("taxes", {"charge_type": "Actual", "account_head": FREIGHT_ACC,
	                    "description": "Ocean Freight", "tax_amount": 2830,
	                    "cost_center": COST_CENTER})
	si.append("taxes", {"charge_type": "Actual", "account_head": INSURANCE_ACC,
	                    "description": "Marine Insurance", "tax_amount": 260,
	                    "cost_center": COST_CENTER})
	si.insert()
	si.submit()
	print("   invoice:", si.name, si.currency, si.grand_total)

	inr = si.grand_total * 93.0
	pe = frappe.new_doc("Payment Entry")
	pe.payment_type = "Receive"
	pe.company = COMPANY
	pe.party_type = "Customer"
	pe.party = ship.customer
	pe.posting_date = today()
	pe.reference_no = "LC/FBN/2026/00417"
	pe.reference_date = today()
	pe.paid_from = DEBIT_TO
	pe.paid_from_account_currency = "INR"
	pe.paid_to = BANK
	pe.source_exchange_rate = 1
	pe.target_exchange_rate = 1
	pe.paid_amount = inr
	pe.received_amount = inr
	pe.append("references", {"reference_doctype": "Sales Invoice", "reference_name": si.name,
	                         "total_amount": inr, "outstanding_amount": inr,
	                         "allocated_amount": inr})
	pe.insert()
	pe.submit()
	print("   payment:", pe.name)
	frappe.db.commit()

	ship.reload()
	print("   payment status:", ship.payment_status, "| outstanding", ship.outstanding_amount)
	ship.lc_payment_released_on = today()
	ship.status = "Payment Received"
	ship.save()

	ship.xar_no = "XAR/KMB/2026/44120"
	ship.xar_date = today()
	ship.bank_charges = 4200
	ship.status = "XAR Generated"
	ship.save()

	ship.status = "Bank Submission Done"
	ship.save()

	ship.ebrc_no = "EBRC/2026/NG/774120"
	ship.ebrc_date = today()
	ship.closure_remarks = "LC proceeds realised in full. Shipment closed."
	ship.incentive_status = "Scrip Received"
	ship.master_details_sent_on = today()
	ship.rodtep_scrip_no = "RODTEP/2026/8841"
	ship.rodtep_amount = 31200
	ship.drawback_amount = 18400
	ship.status = "EBRC Generated"
	ship.save()
	frappe.db.commit()
	print("   A closed at:", ship.status)


# ============================================================== B -- Uganda
if frappe.db.exists("Export Shipment", {"customer": CUST["Uganda"], "docstatus": ["<", 2]}):
	print("B already seeded")
else:
	print("=== B: Uganda / FOB / Through Bank -- parked mid-flow ===")
	so = make_so(CUST["Uganda"], "FOB", "NHAVA SHEVA",
	             [(180, 44.00), (450, 12.20)], "ROYAL AGROVET LTD., KAMPALA",
	             "30% ADVANCE, BALANCE AGAINST DOCUMENTS")
	indent = make_indent(so, approve=True)
	ship = frappe.get_doc("Export Shipment", {"sales_order": so.name})
	ship.payment_route = "Through Bank"
	ship.export_indent = indent.name
	ship.consignee_address = ("Plot No. 705, Mawanda Road\nP.O. Box 11194, Kampala - Uganda")
	ship.notify_name = "ROYAL AGROVET LTD."
	ship.buyer_same_as_consignee = 1
	ship.port_of_discharge = "MOMBASA PORT"
	ship.final_destination = "UGANDA"
	ship.shipment_type = "FCL"
	ship.mode = "Sea"
	ship.remarks = TAG
	ship.status = "Indent Approved"
	ship.save()
	print("   %s | country %s | inspection %s (%s)" % (
		ship.name, ship.destination_country, ship.inspection_required, ship.inspection_agency))

	for cha, fr, local, thc, doc, other, transit, free, vessel, off in (
		(CHA[0], 1980, 165, 145, 60, 70, 24, 14, "MSC ANNA", 11),
		(CHA[1], 1875, 190, 145, 75, 110, 29, 21, "MAERSK KOWLOON", 8),
		(CHA[2], 2140, 150, 145, 55, 35, 20, 7, "CMA CGM JULES VERNE", 14),
	):
		ship.append("cha_quotes", {
			"cha": cha, "quote_date": today(), "currency": "USD",
			"container_type": "1 x 40 HC", "freight_amount": fr, "local_charges": local,
			"thc": thc, "documentation_charges": doc, "other_charges": other,
			"transit_days": transit, "free_days": free, "vessel": vessel,
			"etd": add_days(today(), off), "eta": add_days(today(), off + transit)})
	ship.cha_quotes[1].is_selected = 1
	for n, (status, done, pending, packing) in enumerate((
		("Not Started", 0, 630, "Not Started"),
		("In Production", 240, 390, "Not Started"),
		("Partially Ready", 470, 160, "In Progress"),
	), start=1):
		ship.append("production_updates", {
			"week_ending": add_days(today(), -7 * (3 - n)),
			"production_status": status, "qty_completed": done, "qty_pending": pending,
			"packing_status": packing, "expected_completion_date": add_days(today(), 12),
			"remarks": TAG})
	ship.inspection_request_date = add_days(today(), -3)
	ship.inspection_status = "Requested"
	ship.status = "Freight Finalised"
	ship.save()
	frappe.db.commit()
	step = ship.get_next_step()
	print("   parked at %s -> next %s | blockers %s | todos %s" % (
		ship.status, step["next_action"], [b["label"] for b in step["blockers"]],
		[t["label"] for t in step["todos"]]))

# ============================================================== C -- Malawi
if frappe.db.exists("Export Shipment", {"customer": CUST["Malawi"], "docstatus": ["<", 2]}):
	print("C already seeded")
else:
	print("\n=== C: Malawi / CIF / Direct -- fresh enquiry ===")
	so = make_so(CUST["Malawi"], "CIF", "BEIRA PORT",
	             [(96, 48.75)], "AGRO MALAWI LIMITED, LILONGWE", "100% ADVANCE")
	indent = make_indent(so, approve=False)   # left awaiting VP approval on purpose
	ship = frappe.get_doc("Export Shipment", {"sales_order": so.name})
	ship.export_indent = indent.name
	ship.consignee_address = "Area 4, Plot 217\nLilongwe - Malawi"
	ship.buyer_same_as_consignee = 1
	ship.port_of_discharge = "BEIRA PORT, MOZAMBIQUE"
	ship.final_destination = "LILONGWE, MALAWI"
	ship.mode = "Sea"
	ship.remarks = TAG
	ship.save()
	frappe.db.commit()
	step = ship.get_next_step()
	print("   %s | country %s | haulage %s" % (
		ship.name, ship.destination_country, ship.haulage_required))
	print("   note:", ship.country_note())
	print("   parked at %s -> next %s | blockers %s" % (
		ship.status, step["next_action"], [b["label"] for b in step["blockers"]]))


# =====================================================================
# attach the real documents to A's checklist, then build the pack
# =====================================================================
A = frappe.db.get_value("Export Shipment",
	{"customer": CUST["Nigeria"], "ebrc_no": ["is", "set"]})
if A:
	ship = frappe.get_doc("Export Shipment", A)
	SI = frappe.db.get_value("Sales Invoice", {"custom_export_shipment": A, "docstatus": 1})

	def attach(filename, content):
		return frappe.get_doc({
			"doctype": "File", "file_name": filename, "attached_to_doctype": "Export Shipment",
			"attached_to_name": A, "is_private": 1, "content": content,
		}).insert(ignore_permissions=True).file_url

	rendered = {
		"Commercial Invoice": ("commercial-invoice.html",
		                       frappe.get_print("Sales Invoice", SI, "Export Invoice")),
		"Packing List": ("packing-list.html",
		                 frappe.get_print("Sales Invoice", SI, "Export Packing List")),
		"SCOMET Letter": ("scomet-letter.html",
		                  frappe.get_print("Export Shipment", A, "SCOMET Letter")),
		"Verified Gross Mass (VGM)": ("vgm.html",
		                              frappe.get_print("Export Shipment", A, "Verified Gross Mass")),
	}
	attached = 0
	for row in ship.pre_shipment_documents:
		if row.document_name in rendered and not row.attachment:
			filename, html = rendered[row.document_name]
			row.attachment = attach(filename, html)
			row.document_no = "%s/%s" % (row.document_name[:4].upper(), ship.name[-5:])
			attached += 1
	if not ship.shipping_bill_attachment:
		ship.shipping_bill_attachment = attach(
			"shipping-bill-%s.html" % ship.shipping_bill_no,
			"<h1>Shipping Bill %s</h1><p>Demo copy.</p>" % ship.shipping_bill_no)
	if not ship.bl_attachment:
		ship.bl_attachment = attach("bl-%s.html" % ship.bl_no,
			"<h1>Bill of Lading %s</h1><p>Demo copy.</p>" % ship.bl_no)
	ship.save()
	frappe.db.commit()

	pack = ship.build_document_pack()
	frappe.db.commit()
	print("\n   attached to %d checklist rows; pack = %s (%d file(s))"
	      % (attached, pack["file_url"], pack["packed"]))

print("\n" + "=" * 62)
for s in frappe.get_all("Export Shipment", filters={"remarks": ["like", "%DEMO%"]},
		fields=["name", "destination_country", "status", "payment_status"], order_by="name"):
	print("  %-20s %-9s %-28s %s" % (s.name, s.destination_country, s.status, s.payment_status))
print("=" * 62)
print("Remove it all again with tests/clean_demo_data.py")
