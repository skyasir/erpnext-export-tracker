"""Rebuild shipment EXP/398 (Malawi) and check the five documents we issue."""

import frappe
from frappe.utils import add_days, today

PASS, FAIL = [], []


def check(label, cond, detail=""):
	(PASS if cond else FAIL).append(label)
	print("%s  %s%s" % ("PASS" if cond else "FAIL", label, (" -- " + str(detail)) if detail else ""))


frappe.init(site="supreme.localhost")
frappe.connect()
frappe.set_user("Administrator")

CUSTOMER, ITEM, COMPANY = "A1 Poultry Farm", "SE-AO-FS-300011", "Supreme Equipments Pvt Ltd"
WAREHOUSE = "P1 - Central / Main Store - SEPL"
INCOME, COST_CENTER = "Sales Account - Cages - SEPL - SEPL", "Main - SEPL"
DEBIT_TO = "Sundry Debtors - Corporate - SEPL"
FREIGHT_ACC = "Clearing & Forwarding Charges -Export - SEPL"
INSURANCE_ACC = "Insurance Charges - SEPL"

so = frappe.new_doc("Sales Order")
so.customer, so.company, so.currency, so.conversion_rate = CUSTOMER, COMPANY, "USD", 93.0
so.transaction_date, so.delivery_date = today(), add_days(today(), 30)
so.incoterm, so.custom_is_export = "CIF", 1
so.custom_consignee_name = "CENTRAL POULTRY 2000 LIMITED"
so.custom_consignee_address = "P.O. BOX NO.-340 , LILONGWE, MALAWI"
so.append("items", {"item_code": ITEM, "qty": 1, "rate": 185079.90, "uom": "Nos",
                    "warehouse": WAREHOUSE, "delivery_date": add_days(today(), 30)})
so.insert(); so.submit()

ship = frappe.get_doc("Export Shipment", {"sales_order": so.name})
ship.destination_country = "Malawi"
ship.consignee_name = "CENTRAL POULTRY 2000 LIMITED"
ship.consignee_address = "P.O. BOX NO.-340 , LILONGWE, MALAWI\nKIND ATTENTION : Mr. SABARI"
ship.notify_name = "DYNAMIC TRADING FZE"
ship.notify_address = "P-2 Hamriyah Business Center, Hamriyah Free Zone,\nSharjah, U A E."
ship.notify_email = "AK@SYNERGYGROUP.AE"
ship.port_of_discharge, ship.final_destination = "NACALA", "LILONGWE, MALAWI"
ship.country_of_final_destination = "MALAWI"
ship.terms_of_payment, ship.vessel_flight_no = "100% Advance", "APL CAIRO/02SOUS1MA"

CONTAINERS = [
	("CMAU9248348", "M8963888", 511, 24780.190, 24790.190, "6102"),
	("BEAU4073471", "M8963865", 370, 24530.650, 24540.650, "6103"),
	("BMOU6735150", "M8963892", 815, 23990.200, 24000.200, "6104"),
]
for cn, seal, pkgs, net, gross, slip in CONTAINERS:
	ship.append("containers", {
		"container_no": cn, "container_size": "40 HC", "seal_no": seal,
		"no_of_packages": pkgs, "net_weight": net, "gross_weight": gross,
		"max_permissible_weight": 32500, "vgm_weight": gross,
		"weighing_datetime": "2026-04-13 12:10:00", "weighing_slip_no": slip,
		"cargo_type": "NORMAL", "un_imdg_class": "NA",
	})

# first six packing lines of the real list, first container
for desc, qb, pk, wt in (("NEST SIDE PANEL", 864, 4, 1000),
                         ("NEST BOX PLASTIC BELTING", 100, 125, 27.8),
                         ("FEEDING TROUGH (10 FT)", 750, 1, 6988),
                         ("BOTTOM ANGLE", 96, 251, 33.29),
                         ("FEED TROUGH MESH (GRILLS)", 10, 102, 14),
                         ("NEST CENTER PANEL", 20, 28, 19.05)):
	ship.append("packing_items", {"container_no": "CMAU9248348", "description": desc,
	                              "qty_per_bundle": qb, "no_of_packages": pk,
	                              "weight_per_package": wt})
ship.append("packing_items", {"container_no": "BEAU4073471", "description": "NEST SIDE PANEL",
                              "qty_per_bundle": 864, "no_of_packages": 4, "weight_per_package": 1000})
ship.save()

print("\n=== container roll-up ===")
check("container_no derived from the table", ship.container_no.count("\n") == 2, repr(ship.container_no))
check("no_of_containers = 3", ship.no_of_containers == 3, ship.no_of_containers)
check("packages summed = 1696", ship.no_of_packages == 1696, ship.no_of_packages)
check("net weight summed = 73301.040", round(ship.net_weight, 3) == 73301.040, ship.net_weight)
check("gross weight summed = 73331.040", round(ship.gross_weight, 3) == 73331.040, ship.gross_weight)

print("\n=== packing line maths and package numbering ===")
rows = ship.packing_items
check("row 1 total qty 864x4 = 3456", rows[0].total_qty == 3456, rows[0].total_qty)
check("row 1 total weight 1000x4 = 4000", rows[0].total_weight == 4000, rows[0].total_weight)
check("row 2 total qty 100x125 = 12500", rows[1].total_qty == 12500, rows[1].total_qty)
check("row 1 packages numbered 1 TO 4",
      (rows[0].package_from, rows[0].package_to) == (1, 4),
      "%s-%s" % (rows[0].package_from, rows[0].package_to))
check("row 2 continues 5 TO 129",
      (rows[1].package_from, rows[1].package_to) == (5, 129),
      "%s-%s" % (rows[1].package_from, rows[1].package_to))
check("row 6 ends at 511 (container 1 total)",
      rows[5].package_to == 511, rows[5].package_to)
check("row 7 starts container 2 at 512", rows[6].package_from == 512, rows[6].package_from)

print("\n=== packing row must name a real container ===")
ship.append("packing_items", {"container_no": "BOGUS123", "description": "X",
                              "qty_per_bundle": 1, "no_of_packages": 1})
try:
	ship.save()
	check("unknown container rejected", False, "no exception")
except frappe.ValidationError as e:
	check("unknown container rejected", True, str(e)[:90])
ship.reload()

print("\n=== invoice with the real CIF build-up ===")
si = frappe.new_doc("Sales Invoice")
si.naming_series, si.customer, si.company = "EXP/.###", CUSTOMER, COMPANY
si.currency, si.conversion_rate, si.posting_date = "USD", 93.0, today()
si.debit_to, si.incoterm, si.custom_is_export = DEBIT_TO, "CIF", 1
si.custom_export_shipment = ship.name
si.custom_goods_description = "Poultry Keeping Equipments & parts in ckd condition"
si.custom_consignee_name = "CENTRAL POULTRY 2000 LIMITED"
si.custom_notify_name = "DYNAMIC TRADING FZE"
si.custom_notify_address = "P-2 Hamriyah Business Center, Hamriyah Free Zone,\nSharjah, U A E."
si.custom_notify_email = "AK@SYNERGYGROUP.AE"
si.custom_container_no = "\n".join(c[0] for c in CONTAINERS)
si.custom_net_weight, si.custom_gross_weight, si.custom_no_of_packages = 73301.040, 73331.040, 1696
si.custom_port_of_loading = "NHAVA SHEVA SEA PORT, INDIA"
si.custom_port_of_discharge, si.custom_final_destination = "NACALA", "LILONGWE, MALAWI"
si.custom_country_of_final_destination = "MALAWI"
si.custom_terms_of_payment = "100% Advance"
si.append("items", {"item_code": ITEM, "qty": 1, "rate": 185079.90, "uom": "Nos",
                    "income_account": INCOME, "cost_center": COST_CENTER,
                    "warehouse": WAREHOUSE, "sales_order": so.name})
for desc, amt, acc in (("SEA FREIGHT FOR 3 X 40' CONTAINER", 28025.00, FREIGHT_ACC),
                       ("INSURANCE", 375.00, INSURANCE_ACC)):
	si.append("taxes", {"charge_type": "Actual", "account_head": acc, "description": desc,
	                    "tax_amount": amt, "cost_center": COST_CENTER})
si.set_missing_values()
si.insert()
check("ex-works = 185,079.90", round(si.net_total, 2) == 185079.90, si.net_total)
check("CIF total = 213,479.90", round(si.grand_total, 2) == 213479.90, si.grand_total)
si.submit()
ship.reload()

print("\n=== the five documents we issue ===")
EXPECT = {
	"Verified Gross Mass": ("Export Shipment", ship.name, [
		"INFORMATION ABOUT VERIFIED GROSS MASS OF CONTAINER", "3111025713", "SACHIN SHARMA",
		"CLIENT RELATIONS", "+91 9420695063", "CMAU9248348", "40 HC", "32500.00 KGS",
		"PERFECT COMPUTERISED WEIGH BRIDGE", "13.04.2026 @ 12:10", "6102", "NORMAL"]),
	"SCOMET Letter": ("Export Shipment", ship.name, [
		"SCOMET DECLARATION", "Deputy Commissioner of Customs", "CENTRAL POULTRY 2000 LIMITED",
		"do not fall under", "LILONGWE, MALAWI", "NHAVA SHEVA"]),
	"Export Value Declaration": ("Export Shipment", ship.name, [
		"Annexure-A", "EXPORT VALUE DECLARATION", "Rule 7 of Customs Valuation",
		"Sale Basis", "100% Advance", "CIF", "SACHIN SHARMA"]),
	"Export Packing List": ("Export Shipment", ship.name, [
		"PACKING LIST", "DYNAMIC TRADING FZE", "CENTRAL POULTRY 2000 LIMITED",
		"CONTAINER NO : CMAU9248348", "CONTAINER NO : BEAU4073471", "CONTAINER NO : BMOU6735150",
		"NEST BOX PLASTIC BELTING", "73301.040 KGS", "1696 PACKAGES", "IEC CODE - 3111025713"]),
	"Export Invoice": ("Sales Invoice", si.name, [
		"EXPORT INVOICE", "NOTIFY PARTY", "DYNAMIC TRADING FZE", "HS CODE",
		"CONTAINER NO : CMAU9248348", "CONTAINER NO : BMOU6735150",
		"185,079.90", "213,479.90", "73301.040 KGS", "1696 PACKAGES", "VIDYA RIJAL"]),
}
for pf, (dt, name, needles) in EXPECT.items():
	try:
		html = frappe.get_print(dt, name, print_format=pf)
		missing = [n for n in needles if n not in html]
		check("renders: %s" % pf, not missing and len(html) > 500,
		      "%d chars%s" % (len(html), "" if not missing else ", MISSING %s" % missing))
	except Exception as e:
		check("renders: %s" % pf, False, repr(e)[:160])

print("\n=== one VGM page per container ===")
vgm = frappe.get_print("Export Shipment", ship.name, print_format="Verified Gross Mass")
check("VGM repeats for all 3 containers",
      vgm.count("INFORMATION ABOUT VERIFIED GROSS MASS") == 3,
      vgm.count("INFORMATION ABOUT VERIFIED GROSS MASS"))
check("VGM page-breaks between containers", vgm.count("page-break-after") >= 1)

print("\n=== third-party documents are NOT generated ===")
existing = set(frappe.get_all("Print Format", {"module": "Export Tracker"}, pluck="name"))
for never in ("Certificate of Origin", "Bill of Lading", "Insurance Policy", "Express BL"):
	check("no print format for %s (third party)" % never, never not in existing)

print("\n" + "=" * 62)
print("PASSED: %d    FAILED: %d" % (len(PASS), len(FAIL)))
for f in FAIL:
	print("  -", f)
print("=" * 62)

frappe.db.rollback()
print("\nrolled back")


# ======================================================================
# Air variant -- EXP/399 to Malawi via DHL / Sahar Air Cargo.
# Same print formats, different output: no containers, BUYER instead of
# NOTIFY, and the air customs office on the SCOMET letter.
# ======================================================================
print("\n\n=== AIR shipment (EXP/399) ===")
PASS.clear(); FAIL.clear()

so2 = frappe.new_doc("Sales Order")
so2.customer, so2.company, so2.currency, so2.conversion_rate = CUSTOMER, COMPANY, "USD", 93.0
so2.transaction_date, so2.delivery_date = today(), add_days(today(), 15)
so2.custom_is_export = 1
so2.append("items", {"item_code": ITEM, "qty": 1, "rate": 500, "uom": "Nos",
                     "warehouse": WAREHOUSE, "delivery_date": add_days(today(), 15)})
so2.insert(); so2.submit()

air = frappe.get_doc("Export Shipment", {"sales_order": so2.name})
air.mode = "Air"
air.destination_country = "Malawi"
air.consignee_name = "CENTRAL POULTRY 2000 LIMITED"
air.consignee_address = "P.O. BOX NO.-340\nLILONGWE, MALAWI\nKIND ATTENTION : Mr. SABARI"
air.buyer_same_as_consignee = 0
air.buyer_name = "CENTRAL POULTRY 2000 LIMITED"
air.buyer_address = "PO BOX 340, DUDU ESTATE\nPOSTAL CODES 207236 LILONGWE, MALAWI"
air.port_of_loading, air.port_of_discharge = "MUMBAI AIRPORT", "LILONGWE AIRPORT"
air.final_destination, air.country_of_final_destination = "LILONGWE, MALAWI", "MALAWI"
air.incoterm, air.terms_of_payment = "CFR", "100% ADVANCE"
air.signatory_name, air.signatory_designation = "Vidya Rijal", "Client Relations"
air.signatory_contact = "96579 66444"
air.customs_broker_name = "DHL Express (India) Pvt. Ltd. ('DHL')"
air.append("packing_items", {"description": "NOSE CLIP", "qty_per_bundle": 5000,
                             "no_of_packages": 1, "weight_per_package": 3.900})
air.save()
check("air shipment has no containers", not air.containers)
check("packing line still totalled", air.packing_items[0].total_qty == 5000,
      air.packing_items[0].total_qty)
check("packages numbered 1 TO 1",
      (air.packing_items[0].package_from, air.packing_items[0].package_to) == (1, 1))

si2 = frappe.new_doc("Sales Invoice")
si2.naming_series, si2.customer, si2.company = "EXP/.###", CUSTOMER, COMPANY
si2.currency, si2.conversion_rate, si2.posting_date = "USD", 93.0, today()
si2.debit_to, si2.custom_is_export = DEBIT_TO, 1
si2.custom_export_shipment = air.name
si2.custom_goods_description = "Poultry Keeping Equipments & Parts there of"
si2.append("items", {"item_code": ITEM, "qty": 1, "rate": 500, "uom": "Nos",
                     "income_account": INCOME, "cost_center": COST_CENTER,
                     "warehouse": WAREHOUSE, "sales_order": so2.name})
si2.set_missing_values(); si2.insert(); si2.submit()
air.reload()

AIR_EXPECT = {
	"SCOMET Letter": ["Sahar Air Cargo Complex", "SCOMET DECLARATION", "HS CODE",
	                  "CATEGORY 3B/3D OF APPENDIX-3", "Your faithfully",
	                  "CENTRAL POULTRY 2000 LIMITED", "MALAWI"],
	"Export Packing List": ["PACKING LIST", "BUYER :", "DUDU ESTATE", "NOSE CLIP",
	                        "MUMBAI AIRPORT", "LILONGWE AIRPORT", "Vidya Rijal"],
	"FEMA Declaration": ["DECLARATION", "Name of the Exporter", "Name of Customs Broker",
	                     "DHL Express", "Foreign Exchange Management Act, 1999",
	                     "ID Card Number", "Client Relations"],
	"Customs Broker Authorization": ["Authorization for Export shipment",
	                                 "To whomsoever it may concern", "DHL Express",
	                                 "e-way bill", "Vidya Rijal", "Client Relations",
	                                 "96579 66444", "Individual Shipper Name"],
	"Export Value Declaration": ["Annexure-A", "100% ADVANCE", "VIDYA RIJAL"],
}
for pf, needles in AIR_EXPECT.items():
	try:
		html = frappe.get_print("Export Shipment", air.name, print_format=pf)
		missing = [n for n in needles if n not in html]
		check("air renders: %s" % pf, not missing, "MISSING %s" % missing if missing else "%d chars" % len(html))
	except Exception as e:
		check("air renders: %s" % pf, False, repr(e)[:150])

scomet_air = frappe.get_print("Export Shipment", air.name, print_format="SCOMET Letter")
check("air SCOMET does NOT use the sea customs office",
      "Exports Department" not in scomet_air)
pl_air = frappe.get_print("Export Shipment", air.name, print_format="Export Packing List")
check("air packing list shows no CONTAINER NO heading", "CONTAINER NO :" not in pl_air)

print("\n" + "=" * 62)
print("AIR -- PASSED: %d    FAILED: %d" % (len(PASS), len(FAIL)))
for f in FAIL:
	print("  -", f)
print("=" * 62)
frappe.db.rollback()
