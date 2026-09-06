import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

MODULE = "Export Tracker"
EXPORT_INVOICE_SERIES = "EXP/.###"

# (state, allow_edit_role, style)
STATES = [
	("Order Confirmed", "Sales User", "Warning"),
	("Indent Approved", "Sales Manager", "Warning"),
	("Freight Finalised", "Sales User", "Warning"),
	("Dispatch Planned", "Sales User", "Warning"),
	("Customs Docs Prepared", "Sales User", "Info"),
	("Container Loaded", "Sales User", "Info"),
	("Shipped", "Sales User", "Info"),
	("Post-Shipment Docs Prepared", "Sales User", "Info"),
	("Docs Submitted", "Sales Manager", "Info"),
	("Payment Received", "Accounts User", "Success"),
	("XAR Generated", "Accounts User", "Success"),
	("Bank Submission Done", "Accounts User", "Success"),
	("EBRC Generated", "Accounts Manager", "Success"),
]

# (state, action, next_state, allowed_role)
TRANSITIONS = [
	("Order Confirmed", "Approve Indent", "Indent Approved", "Sales Manager"),
	("Indent Approved", "Finalise Freight", "Freight Finalised", "Sales User"),
	("Freight Finalised", "Plan Dispatch", "Dispatch Planned", "Sales User"),
	("Dispatch Planned", "Prepare Customs Docs", "Customs Docs Prepared", "Sales User"),
	("Customs Docs Prepared", "Confirm Loading", "Container Loaded", "Sales User"),
	("Container Loaded", "Mark Shipped", "Shipped", "Sales User"),
	("Shipped", "Prepare Post-Shipment Docs", "Post-Shipment Docs Prepared", "Sales User"),
	("Post-Shipment Docs Prepared", "Submit Documents", "Docs Submitted", "Sales Manager"),
	("Docs Submitted", "Confirm Payment Received", "Payment Received", "Accounts User"),
	("Payment Received", "Generate XAR", "XAR Generated", "Accounts User"),
	("XAR Generated", "Complete Bank Submission", "Bank Submission Done", "Accounts User"),
	("Bank Submission Done", "Generate EBRC", "EBRC Generated", "Accounts Manager"),
]

WORKFLOW_NAME = "Export Shipment Process"


def after_install():
	make_custom_fields()
	add_export_invoice_series()
	make_workflow_masters()
	make_workflow()
	make_document_templates()
	make_country_profiles()
	make_dashboard()
	frappe.db.commit()


# ----------------------------------------------------------------------
# custom fields
# ----------------------------------------------------------------------
def tab_anchor(doctype):
	"""Where the Export Details tab goes: after the form's very last field.

	A Tab Break captures everything between it and the next one, so anchoring it
	mid-form would drag the standard fields below it into the Export tab. Our own
	fields are skipped so re-running this never nests the tab inside itself.
	"""
	ours = set(
		frappe.get_all("Custom Field", filters={"dt": doctype, "module": MODULE},
		               pluck="fieldname")
	)
	fields = frappe.get_meta(doctype).fields
	for df in reversed(fields):
		if df.fieldname not in ours:
			return df.fieldname
	return fields[-1].fieldname if fields else None


def get_custom_fields():
	"""Order / invoice level fields.

	The process itself lives on Export Shipment; these are only the attributes
	that genuinely belong to the order or to the invoice as issued. They sit in
	their own Export Details tab, which only appears once Is Export is ticked.
	"""
	export_tab = lambda doctype: {  # noqa: E731
		"fieldname": "custom_export_tab",
		"label": "Export Details",
		"fieldtype": "Tab Break",
		"insert_after": tab_anchor(doctype),
		"depends_on": "custom_is_export",
		"module": MODULE,
	}

	consignee_fields = lambda insert_after: [  # noqa: E731
		{
			"fieldname": "custom_export_details_section",
			"label": "Consignee & Buyer",
			"fieldtype": "Section Break",
			"insert_after": insert_after,
			# both spelled out so an update clears what the old inline section
			# carried -- create_custom_fields only writes the keys it is given,
			# so leaving these off would keep the section collapsed and gated
			"collapsible": 0,
			"depends_on": "",
			"module": MODULE,
		},
		{
			"fieldname": "custom_consignee_name",
			"label": "Consignee Name",
			"fieldtype": "Data",
			"insert_after": "custom_export_details_section",
			"module": MODULE,
		},
		{
			"fieldname": "custom_consignee_address",
			"label": "Consignee Address",
			"fieldtype": "Small Text",
			"insert_after": "custom_consignee_name",
			"module": MODULE,
		},
		{
			"fieldname": "custom_buyer_name",
			"label": "Buyer Name",
			"fieldtype": "Data",
			"insert_after": "custom_consignee_address",
			"description": "Leave blank if the buyer is the consignee",
			"module": MODULE,
		},
		{
			"fieldname": "custom_buyer_address",
			"label": "Buyer Address",
			"fieldtype": "Small Text",
			"insert_after": "custom_buyer_name",
			"module": MODULE,
		},
		{
			"fieldname": "custom_notify_name",
			"label": "Notify Party",
			"fieldtype": "Data",
			"insert_after": "custom_buyer_address",
			"module": MODULE,
		},
		{
			"fieldname": "custom_notify_address",
			"label": "Notify Address",
			"fieldtype": "Small Text",
			"insert_after": "custom_notify_name",
			"module": MODULE,
		},
		{
			"fieldname": "custom_notify_email",
			"label": "Notify Email",
			"fieldtype": "Data",
			"options": "Email",
			"insert_after": "custom_notify_address",
			"module": MODULE,
		},
		{
			"fieldname": "custom_column_break_export",
			"fieldtype": "Column Break",
			"insert_after": "custom_buyer_address",
			"module": MODULE,
		},
		{
			"fieldname": "custom_port_of_discharge",
			"label": "Port of Discharge",
			"fieldtype": "Data",
			"insert_after": "custom_column_break_export",
			"module": MODULE,
		},
		{
			"fieldname": "custom_final_destination",
			"label": "Final Destination",
			"fieldtype": "Data",
			"insert_after": "custom_port_of_discharge",
			"module": MODULE,
		},
		{
			"fieldname": "custom_country_of_final_destination",
			"label": "Country of Final Destination",
			"fieldtype": "Data",
			"insert_after": "custom_final_destination",
			"module": MODULE,
		},
		{
			"fieldname": "custom_terms_of_payment",
			"label": "Terms of Payment",
			"fieldtype": "Data",
			"insert_after": "custom_country_of_final_destination",
			"description": "Printed on the export invoice, e.g. 100% ADVANCE",
			"module": MODULE,
		},
	]

	invoice_shipping_fields = [
		{
			"fieldname": "custom_export_shipping_section",
			"label": "Export Shipping Details",
			"fieldtype": "Section Break",
			"insert_after": "custom_terms_of_payment",
			# cleared explicitly: the tab carries the Is Export condition now, and
			# create_custom_fields only writes the keys it is given
			"depends_on": "",
			"collapsible": 0,
			"module": MODULE,
		},
		{
			"fieldname": "custom_pre_carriage_by",
			"label": "Pre-Carriage By",
			"fieldtype": "Data",
			"insert_after": "custom_export_shipping_section",
			"module": MODULE,
		},
		{
			"fieldname": "custom_place_of_receipt",
			"label": "Place of Receipt by Pre-Carrier",
			"fieldtype": "Data",
			"insert_after": "custom_pre_carriage_by",
			"module": MODULE,
		},
		{
			"fieldname": "custom_port_of_loading",
			"label": "Port of Loading",
			"fieldtype": "Data",
			"insert_after": "custom_place_of_receipt",
			"module": MODULE,
		},
		{
			"fieldname": "custom_vessel_flight_no",
			"label": "Vessel / Flight No",
			"fieldtype": "Data",
			"insert_after": "custom_port_of_loading",
			"module": MODULE,
		},
		{
			"fieldname": "custom_country_of_origin",
			"label": "Country of Origin",
			"fieldtype": "Data",
			"insert_after": "custom_vessel_flight_no",
			"default": "INDIA",
			"module": MODULE,
		},
		{
			"fieldname": "custom_column_break_shipping",
			"fieldtype": "Column Break",
			"insert_after": "custom_country_of_origin",
			"module": MODULE,
		},
		{
			"fieldname": "custom_marks_and_nos",
			"label": "Marks & Nos",
			"fieldtype": "Small Text",
			"insert_after": "custom_column_break_shipping",
			"module": MODULE,
		},
		{
			"fieldname": "custom_container_no",
			"label": "Container No",
			"fieldtype": "Data",
			"insert_after": "custom_marks_and_nos",
			"module": MODULE,
		},
		{
			"fieldname": "custom_net_weight",
			"label": "Total Net Weight (KGS)",
			"fieldtype": "Float",
			"precision": "3",
			"insert_after": "custom_container_no",
			"module": MODULE,
		},
		{
			"fieldname": "custom_gross_weight",
			"label": "Total Gross Weight (KGS)",
			"fieldtype": "Float",
			"precision": "3",
			"insert_after": "custom_net_weight",
			"module": MODULE,
		},
		{
			"fieldname": "custom_no_of_packages",
			"label": "Total No of Packages",
			"fieldtype": "Int",
			"insert_after": "custom_gross_weight",
			"module": MODULE,
		},
		{
			"fieldname": "custom_goods_description",
			"label": "Description of Goods (heading)",
			"fieldtype": "Small Text",
			"insert_after": "custom_no_of_packages",
			"description": "Printed above the item rows on the export invoice",
			"module": MODULE,
		},
	]

	is_export = lambda insert_after: {  # noqa: E731
		"fieldname": "custom_is_export",
		"label": "Is Export",
		"fieldtype": "Check",
		"insert_after": insert_after,
		"default": "0",
		"module": MODULE,
	}

	return {
		"Quotation": [
			is_export("party_name"),
			export_tab("Quotation"),
			*consignee_fields("custom_export_tab"),
			{
				"fieldname": "custom_next_followup_date",
				"label": "Next Follow-up Date",
				"fieldtype": "Date",
				"insert_after": "custom_terms_of_payment",
				"module": MODULE,
			},
		],
		"Sales Order": [
			is_export("customer"),
			export_tab("Sales Order"),
			*consignee_fields("custom_export_tab"),
			{
				"fieldname": "custom_proforma_invoice",
				"label": "Proforma Invoice",
				"fieldtype": "Link",
				"options": "Export Proforma Invoice",
				"insert_after": "custom_terms_of_payment",
				"read_only": 1,
				"description": "The proforma this order was raised from",
				"module": MODULE,
			},
			{
				"fieldname": "custom_export_shipment",
				"label": "Export Shipment",
				"fieldtype": "Link",
				"options": "Export Shipment",
				"insert_after": "custom_proforma_invoice",
				"read_only": 1,
				"allow_on_submit": 1,
				"module": MODULE,
			},
		],
		"Sales Invoice": [
			is_export("customer"),
			export_tab("Sales Invoice"),
			*consignee_fields("custom_export_tab"),
			*invoice_shipping_fields,
			{
				"fieldname": "custom_fob_value",
				"label": "FOB Value",
				"fieldtype": "Currency",
				"options": "currency",
				"insert_after": "custom_goods_description",
				"description": "Declared FOB value, as filed on the shipping bill",
				"module": MODULE,
			},
			{
				"fieldname": "custom_export_shipment",
				"label": "Export Shipment",
				"fieldtype": "Link",
				"options": "Export Shipment",
				"insert_after": "custom_fob_value",
				"allow_on_submit": 1,
				"module": MODULE,
			},
		],
		"Delivery Note": [
			is_export("customer"),
			{
				"fieldname": "custom_export_shipment",
				"label": "Export Shipment",
				"fieldtype": "Link",
				"options": "Export Shipment",
				"insert_after": "custom_is_export",
				"allow_on_submit": 1,
				"depends_on": "custom_is_export",
				"module": MODULE,
			},
		],
	}


def make_custom_fields():
	create_custom_fields(get_custom_fields(), ignore_validate=True)


def add_export_invoice_series():
	"""Add EXP/.### alongside the existing Sales Invoice series -- the export
	department numbers its invoices EXP/420, not SINV-26-00002."""
	meta = frappe.get_meta("Sales Invoice")
	field = meta.get_field("naming_series")
	if not field:
		return

	current = frappe.db.get_value(
		"Property Setter",
		{"doc_type": "Sales Invoice", "field_name": "naming_series", "property": "options"},
		"value",
	)
	options = current if current is not None else (field.options or "")
	existing = [o for o in options.split("\n")]

	if EXPORT_INVOICE_SERIES in existing:
		return

	existing.append(EXPORT_INVOICE_SERIES)
	make_property_setter(
		"Sales Invoice",
		"naming_series",
		"options",
		"\n".join(existing),
		"Text",
		validate_fields_for_doctype=False,
	)
	frappe.db.set_value(
		"Property Setter",
		{"doc_type": "Sales Invoice", "field_name": "naming_series", "property": "options"},
		"module",
		MODULE,
	)


# ----------------------------------------------------------------------
# workflow
# ----------------------------------------------------------------------
def make_workflow_masters():
	for state, _role, style in STATES:
		if not frappe.db.exists("Workflow State", state):
			frappe.get_doc(
				{"doctype": "Workflow State", "workflow_state_name": state, "style": style}
			).insert(ignore_permissions=True)

	for _state, action, _next, _role in TRANSITIONS:
		if not frappe.db.exists("Workflow Action Master", action):
			frappe.get_doc(
				{"doctype": "Workflow Action Master", "workflow_action_name": action}
			).insert(ignore_permissions=True)


def make_workflow():
	if frappe.db.exists("Workflow", WORKFLOW_NAME):
		return

	wf = frappe.new_doc("Workflow")
	wf.workflow_name = WORKFLOW_NAME
	wf.document_type = "Export Shipment"
	wf.workflow_state_field = "status"
	wf.is_active = 1
	wf.send_email_alert = 0

	# states[0] is the initial state for new documents -- keep Order Confirmed first
	for state, role, _style in STATES:
		wf.append("states", {"state": state, "doc_status": "0", "allow_edit": role})

	for state, action, next_state, role in TRANSITIONS:
		wf.append(
			"transitions",
			{
				"state": state,
				"action": action,
				"next_state": next_state,
				"allowed": role,
				"allow_self_approval": 1,
			},
		)

	wf.insert(ignore_permissions=True)


# ----------------------------------------------------------------------
# document templates -- SOP G.c.i.5 and G.c.ii
# ----------------------------------------------------------------------
PRE_SHIPMENT_BASE = [
	("Commercial Invoice", 1, "Export Dept"),
	("Packing List", 1, "Export Dept"),
	("SCOMET Letter", 1, "Export Dept"),
	("Annexure", 1, "Export Dept"),
	("Examination Report", 1, "CHA"),
	("Export Value Declaration", 1, "Export Dept"),
	("Verified Gross Mass (VGM)", 1, "Export Dept"),
	("Form 13", 1, "CHA"),
	("Bill of Lading", 1, "CHA"),
	("Insurance", 0, "Insurer"),
]

POST_DIRECT = [
	("Invoice", 1, "Export Dept"),
	("Packing List", 1, "Export Dept"),
	("Certificate of Origin", 1, "Consultant"),
	("Bill of Lading", 1, "CHA"),
	("Insurance Policy", 0, "Insurer"),
]

POST_BANK = POST_DIRECT + [
	("Bill of Exchange", 1, "Export Dept"),
	("Dispatch Declaration", 1, "Export Dept"),
	("Letter of Undertaking", 1, "Export Dept"),
	("Request Letter to Bank for Export Bill on Collection", 1, "Export Dept"),
	("Document Set for Our Bank", 1, "Export Dept"),
	("Document Set for Consignee Bank", 1, "Export Dept"),
]

POST_LC = POST_BANK + [
	("Letter of Credit Copy", 1, "Customer"),
]

# destination specific certification -- SOP G.c.i.5.a and G.c.ii.1.c
# these are the destinations Supreme ships to; add your own as needed
COUNTRY_EXTRAS = {
	"Nigeria": [
		("SONCAP Certificate", 1, "Consultant", "Pre-Shipment"),
		("Combined Certificate of Value and Origin (CCVO)", 1, "Consultant", "Post-Shipment"),
	],
	"Uganda": [("SGS Certificate", 1, "Consultant", "Pre-Shipment")],
	"Nepal": [("Letter of Undertaking", 1, "Export Dept", "Pre-Shipment")],
	"Bhutan": [("Letter of Undertaking", 1, "Export Dept", "Pre-Shipment")],
	"Sri Lanka": [
		("ISFTA Certificate of Origin", 1, "Consultant", "Post-Shipment"),
	],
}

ROUTE_DOCS = {
	"Direct through Client": POST_DIRECT,
	"Through Bank": POST_BANK,
	"Through Letter of Credit": POST_LC,
}


def make_document_templates():
	"""One fallback template per route, plus a country template where the
	destination needs extra certification."""
	for route, post_docs in ROUTE_DOCS.items():
		name = "Standard - {0}".format(route)
		rows = [(d, r, who, "Pre-Shipment") for d, r, who in PRE_SHIPMENT_BASE]
		rows += [(d, r, who, "Post-Shipment") for d, r, who in post_docs]
		upsert_template(
			name,
			rows,
			payment_route=route,
			is_default=1 if route == "Direct through Client" else 0,
		)

	for country, extras in COUNTRY_EXTRAS.items():
		if not frappe.db.exists("Country", country):
			continue
		name = "{0} - Standard".format(country)
		rows = [(d, r, who, "Pre-Shipment") for d, r, who in PRE_SHIPMENT_BASE]
		rows += [(d, r, who, "Post-Shipment") for d, r, who in POST_DIRECT]
		rows += list(extras)
		upsert_template(name, rows, destination_country=country)


def upsert_template(name, rows, destination_country=None, payment_route="Any", is_default=0):
	if frappe.db.exists("Export Document Template", name):
		return

	doc = frappe.new_doc("Export Document Template")
	doc.template_name = name
	doc.destination_country = destination_country
	doc.payment_route = payment_route
	doc.is_default = is_default

	seen = set()
	for document_name, is_required, responsibility, stage in rows:
		key = (document_name.strip().lower(), stage)
		if key in seen:
			continue
		seen.add(key)
		doc.append(
			"documents",
			{
				"document_name": document_name,
				"stage": stage,
				"is_required": is_required,
				"responsibility": responsibility,
			},
		)

	doc.insert(ignore_permissions=True)


# ----------------------------------------------------------------------
# country profiles -- SOP section 2C: nothing about a destination is hard-coded
# ----------------------------------------------------------------------
COUNTRY_PROFILES = {
	"Nigeria": {
		"inspection_required": 1,
		"inspection_agency": "SONCAP",
		"form_m_required": 1,
		"coo_type": "CCVO (Nigeria)",
		"special_requirement": (
			"The buyer opens Form M and the BA number before shipment. "
			"SONCAP inspection applies; the CCVO goes with the post-shipment set."
		),
	},
	"Uganda": {
		"inspection_required": 1,
		"inspection_agency": "SGS",
		"special_requirement": "SGS pre-export verification of conformity applies.",
	},
	"Malawi": {
		"haulage_required": 1,
		"special_requirement": (
			"Landlocked. Cargo is trucked from the discharge port to site -- "
			"capture the haulage leg and its charges separately."
		),
	},
	"Nepal": {"special_requirement": "Letter of Undertaking travels with the pre-shipment set."},
	"Bhutan": {"special_requirement": "Letter of Undertaking travels with the pre-shipment set."},
	"Sri Lanka": {
		"coo_type": "ISFTA (India Sri-Lanka FTA)",
		"special_requirement": "ISFTA preferential certificate of origin applies.",
	},
}


def make_country_profiles():
	"""Seed a profile for each destination the app already knew about, so the
	rules that used to live in COUNTRY_EXTRAS become editable records."""
	for country, values in COUNTRY_PROFILES.items():
		if not frappe.db.exists("Country", country):
			continue
		if frappe.db.exists("Export Country Profile", country):
			continue

		doc = frappe.new_doc("Export Country Profile")
		doc.country = country
		doc.update(values)
		for document_name, is_required, responsibility, stage in COUNTRY_EXTRAS.get(country, []):
			doc.append(
				"documents",
				{
					"document_name": document_name,
					"stage": stage,
					"is_required": is_required,
					"responsibility": responsibility,
				},
			)
		doc.insert(ignore_permissions=True)


# ----------------------------------------------------------------------
# export control tower -- SOP section 39
# ----------------------------------------------------------------------
OPEN_STATES = [
	"Order Confirmed",
	"Indent Approved",
	"Freight Finalised",
	"Dispatch Planned",
	"Customs Docs Prepared",
	"Container Loaded",
]

# (name, doctype, filters, function, aggregate field, colour)
NUMBER_CARDS = [
	(
		"Export Quotations Pending",
		"Quotation",
		[
			["Quotation", "custom_is_export", "=", 1],
			["Quotation", "docstatus", "=", 1],
			["Quotation", "status", "not in", ["Ordered", "Lost", "Closed", "Expired"]],
		],
		"Count",
		None,
		"#7575ff",
	),
	(
		"Export Indent Approval Pending",
		"Export Indent",
		[["Export Indent", "management_approved", "=", 0]],
		"Count",
		None,
		"#ffa00a",
	),
	(
		"Export Production Pending",
		"Export Shipment",
		[
			["Export Shipment", "status", "in", OPEN_STATES],
			["Export Shipment", "production_status", "not in", ["Ready", "Dispatch Planning"]],
		],
		"Count",
		None,
		"#ffa00a",
	),
	(
		"Export Freight Selection Pending",
		"Export Shipment",
		[
			["Export Shipment", "status", "in", ["Order Confirmed", "Indent Approved"]],
			["Export Shipment", "selected_cha", "is", "not set"],
		],
		"Count",
		None,
		"#29cd42",
	),
	(
		"Export Booking Pending",
		"Export Shipment",
		[
			["Export Shipment", "status", "in", OPEN_STATES],
			["Export Shipment", "booking_no", "is", "not set"],
		],
		"Count",
		None,
		"#29cd42",
	),
	(
		"Export Form M Pending",
		"Export Shipment",
		[
			["Export Shipment", "form_m_required", "=", 1],
			["Export Shipment", "form_m_no", "is", "not set"],
		],
		"Count",
		None,
		"#cb2929",
	),
	(
		"Export Inspection Pending",
		"Export Shipment",
		[
			["Export Shipment", "inspection_required", "=", 1],
			["Export Shipment", "inspection_status", "!=", "Final Report"],
		],
		"Count",
		None,
		"#cb2929",
	),
	(
		"Export Shipping Bill Pending",
		"Export Shipment",
		[
			["Export Shipment", "status", "in", ["Customs Docs Prepared", "Container Loaded"]],
			["Export Shipment", "shipping_bill_no", "is", "not set"],
		],
		"Count",
		None,
		"#ff5858",
	),
	(
		"Export BL Approval Pending",
		"Export Shipment",
		[
			["Export Shipment", "draft_bl_received_on", "is", "set"],
			["Export Shipment", "bl_client_approved_on", "is", "not set"],
		],
		"Count",
		None,
		"#ff5858",
	),
	(
		"Export Payment Outstanding",
		"Export Shipment",
		[["Export Shipment", "payment_status", "!=", "Fully Paid"]],
		"Sum",
		"outstanding_amount",
		"#cb2929",
	),
	(
		"Export Closure Pending",
		"Export Shipment",
		[
			[
				"Export Shipment",
				"status",
				"in",
				["Docs Submitted", "Payment Received", "XAR Generated", "Bank Submission Done"],
			]
		],
		"Count",
		None,
		"#7575ff",
	),
]

STAGE_CHART = "Export Shipments by Stage"


def make_dashboard():
	"""Number cards and the stage chart behind the Export Tracker workspace."""
	for name, doctype, filters, function, based_on, colour in NUMBER_CARDS:
		# A Number Card names itself from its label, and the workspace resolves the
		# card by that same string -- so label, name and the workspace's child row
		# all have to agree. The cards are laid out three to a row instead, which
		# is what stops the titles truncating.
		if frappe.db.exists("Number Card", name):
			if frappe.db.get_value("Number Card", name, "label") != name:
				frappe.db.set_value("Number Card", name, "label", name)
			continue
		card = frappe.new_doc("Number Card")
		card.update(
			{
				# a Number Card names itself from its label, so the label has to be
				# the full name the workspace references -- and the "Export" prefix
				# keeps it from colliding with another app's "Payment Outstanding"
				"label": name,
				"type": "Document Type",
				"document_type": doctype,
				"function": function,
				"aggregate_function_based_on": based_on,
				"filters_json": frappe.as_json(filters),
				"is_public": 1,
				"show_percentage_change": 0,
				"color": colour,
				"module": MODULE,
			}
		)
		card.insert(ignore_permissions=True)

	if not frappe.db.exists("Dashboard Chart", STAGE_CHART):
		frappe.get_doc(
			{
				"doctype": "Dashboard Chart",
				"name": STAGE_CHART,
				"chart_name": STAGE_CHART,
				"chart_type": "Group By",
				"document_type": "Export Shipment",
				"group_by_type": "Count",
				"group_by_based_on": "status",
				"type": "Bar",
				"timeseries": 0,
				"filters_json": "[]",
				"dynamic_filters_json": "[]",
				"is_public": 1,
				"number_of_groups": 13,
				"module": MODULE,
			}
		).insert(ignore_permissions=True)
