"""Daily nudges for the export desk.

Every alert is also visible as a report, so a missing SMTP account only costs
you the email, never the information.
"""

import frappe
from frappe.utils import add_days, add_months, formatdate, get_link_to_form, getdate, today


def send_export_reminders():
	settings = frappe.get_single("Export Tracker Settings")
	if not settings.enable_reminders:
		return

	sales_recipients = get_recipients(settings.notification_role or "Sales User")
	accounts_recipients = get_recipients(settings.accounts_notification_role or "Accounts User")

	blocks = []
	blocks += quotation_followup_due(settings)
	blocks += documents_pending_before_etd(settings)
	blocks += cutoffs_approaching()
	blocks += compliance_pending()
	blocks += bl_approval_pending()
	blocks += production_update_overdue()
	blocks += lc_deadlines()
	if sales_recipients:
		send("Export Tracker: pending actions", blocks, sales_recipients)

	closure_blocks = closure_pending(settings) + realisation_due(settings)
	if accounts_recipients:
		send("Export Tracker: bank closure pending", closure_blocks, accounts_recipients)


# ----------------------------------------------------------------------
# individual checks
# ----------------------------------------------------------------------
def quotation_followup_due(settings):
	days = settings.followup_reminder_days or 7
	cutoff = add_days(today(), -days)

	rows = frappe.get_all(
		"Quotation",
		filters={
			"docstatus": 1,
			"status": ["not in", ["Ordered", "Lost", "Closed", "Expired"]],
			"custom_is_export": 1,
		},
		or_filters=[
			["custom_next_followup_date", "<=", today()],
			["modified", "<=", cutoff],
		],
		fields=["name", "party_name", "grand_total", "currency", "custom_next_followup_date"],
		limit=100,
	)
	if not rows:
		return []

	return [
		table(
			"Export quotations awaiting follow-up",
			["Quotation", "Customer", "Value", "Follow-up Due"],
			[
				[
					link("Quotation", r.name),
					r.party_name or "",
					fmt_money(r.grand_total, r.currency),
					formatdate(r.custom_next_followup_date)
					if r.custom_next_followup_date
					else "-",
				]
				for r in rows
			],
		)
	]


def documents_pending_before_etd(settings):
	days = settings.docs_pending_days_before_etd or 7
	horizon = add_days(today(), days)

	shipments = frappe.get_all(
		"Export Shipment",
		filters={
			"status": ["not in", ["Shipped", "Post-Shipment Docs Prepared", "Docs Submitted",
			                      "Payment Received", "XAR Generated", "Bank Submission Done",
			                      "EBRC Generated"]],
			"etd": ["between", [today(), horizon]],
		},
		fields=["name", "customer_name", "etd", "status"],
		limit=100,
	)

	pending_rows = []
	for s in shipments:
		pending = frappe.db.count(
			"Export Document Item",
			{"parent": s.name, "stage": "Pre-Shipment", "is_required": 1, "prepared": 0},
		)
		if pending:
			pending_rows.append(
				[link("Export Shipment", s.name), s.customer_name or "", formatdate(s.etd),
				 s.status, str(pending)]
			)

	if not pending_rows:
		return []

	return [
		table(
			"Pre-shipment documents not ready, ETD within {0} day(s)".format(days),
			["Shipment", "Customer", "ETD", "Status", "Pending Docs"],
			pending_rows,
		)
	]


ACTIVE_STATES = [
	"Order Confirmed",
	"Indent Approved",
	"Freight Finalised",
	"Dispatch Planned",
	"Customs Docs Prepared",
	"Container Loaded",
]


def cutoffs_approaching(days=3):
	"""Vessel, SI, VGM and documentation cut-offs -- SOP section 40.

	A missed cut-off rolls the whole shipment to the next vessel, so this is the
	one alert the desk cannot afford to read late.
	"""
	horizon = add_days(today(), days)
	rows = frappe.get_all(
		"Export Shipment",
		filters={"status": ["in", ACTIVE_STATES]},
		or_filters=[
			["cutoff_date", "between", [today(), horizon]],
			["si_cutoff", "between", [today(), horizon]],
			["vgm_cutoff", "between", [today(), horizon]],
			["doc_cutoff", "between", [today(), horizon]],
		],
		fields=["name", "customer_name", "booking_no", "cutoff_date", "si_cutoff", "vgm_cutoff",
		        "doc_cutoff"],
		limit=100,
	)
	if not rows:
		return []

	def when(value):
		return formatdate(value) if value else "-"

	return [
		table(
			"Cut-offs within {0} day(s)".format(days),
			["Shipment", "Customer", "Booking", "Gate", "SI", "VGM", "Docs"],
			[
				[
					link("Export Shipment", r.name),
					r.customer_name or "",
					r.booking_no or "-",
					when(r.cutoff_date),
					when(r.si_cutoff),
					when(r.vgm_cutoff),
					when(r.doc_cutoff),
				]
				for r in rows
			],
		)
	]


def compliance_pending():
	"""Form M / BA and pre-shipment inspection -- SOP sections 9 and 16."""
	blocks = []

	form_m = frappe.get_all(
		"Export Shipment",
		filters={
			"form_m_required": 1,
			"form_m_no": ["is", "not set"],
			"status": ["in", ACTIVE_STATES],
		},
		fields=["name", "customer_name", "destination_country", "etd"],
		limit=100,
	)
	if form_m:
		blocks.append(
			table(
				"Form M / BA number not yet received",
				["Shipment", "Customer", "Destination", "ETD"],
				[
					[
						link("Export Shipment", r.name),
						r.customer_name or "",
						r.destination_country or "-",
						formatdate(r.etd) if r.etd else "-",
					]
					for r in form_m
				],
			)
		)

	inspection = frappe.get_all(
		"Export Shipment",
		filters={
			"inspection_required": 1,
			"inspection_status": ["!=", "Final Report"],
			"status": ["in", ACTIVE_STATES],
		},
		fields=["name", "customer_name", "inspection_agency", "inspection_status", "etd"],
		limit=100,
	)
	if inspection:
		blocks.append(
			table(
				"Pre-shipment inspection not closed out",
				["Shipment", "Customer", "Agency", "Stage", "ETD"],
				[
					[
						link("Export Shipment", r.name),
						r.customer_name or "",
						r.inspection_agency or "-",
						r.inspection_status or "Not Started",
						formatdate(r.etd) if r.etd else "-",
					]
					for r in inspection
				],
			)
		)

	return blocks


def bl_approval_pending(days=2):
	"""Draft BL sent to the client and still unapproved -- SOP section 28."""
	cutoff = add_days(today(), -days)
	rows = frappe.get_all(
		"Export Shipment",
		filters={
			"draft_bl_received_on": ["<=", cutoff],
			"bl_client_approved_on": ["is", "not set"],
			"status": ["not in", ["EBRC Generated"]],
		},
		fields=["name", "customer_name", "draft_bl_received_on", "draft_bl_sent_on"],
		limit=100,
	)
	if not rows:
		return []

	return [
		table(
			"Draft BL awaiting client approval",
			["Shipment", "Customer", "Draft Received", "Sent to Client"],
			[
				[
					link("Export Shipment", r.name),
					r.customer_name or "",
					formatdate(r.draft_bl_received_on),
					formatdate(r.draft_bl_sent_on) if r.draft_bl_sent_on else "-",
				]
				for r in rows
			],
		)
	]


def production_update_overdue(days=7):
	"""The weekly readiness update -- SOP section 12 -- has gone stale."""
	cutoff = add_days(today(), -days)
	rows = frappe.get_all(
		"Export Shipment",
		filters={"status": ["in", ACTIVE_STATES]},
		or_filters=[
			["last_production_update", "<=", cutoff],
			["last_production_update", "is", "not set"],
		],
		fields=["name", "customer_name", "production_status", "last_production_update",
		        "expected_completion_date"],
		limit=100,
	)
	if not rows:
		return []

	return [
		table(
			"Weekly production update overdue",
			["Shipment", "Customer", "Production Status", "Last Update", "Expected Ready"],
			[
				[
					link("Export Shipment", r.name),
					r.customer_name or "",
					r.production_status or "Not Started",
					formatdate(r.last_production_update) if r.last_production_update else "never",
					formatdate(r.expected_completion_date) if r.expected_completion_date else "-",
				]
				for r in rows
			],
		)
	]


def lc_deadlines():
	horizon = add_days(today(), 15)
	rows = frappe.get_all(
		"Export Shipment",
		filters={
			"payment_route": "Through Letter of Credit",
			"status": ["not in", ["Payment Received", "XAR Generated", "Bank Submission Done",
			                      "EBRC Generated"]],
		},
		or_filters=[
			["lc_expiry_date", "between", [today(), horizon]],
			["lc_last_shipment_date", "between", [today(), horizon]],
		],
		fields=["name", "customer_name", "lc_no", "lc_expiry_date", "lc_last_shipment_date"],
		limit=100,
	)
	if not rows:
		return []

	return [
		table(
			"Letters of Credit approaching a deadline",
			["Shipment", "Customer", "LC No", "LC Expiry", "Last Shipment Date"],
			[
				[
					link("Export Shipment", r.name),
					r.customer_name or "",
					r.lc_no or "-",
					formatdate(r.lc_expiry_date) if r.lc_expiry_date else "-",
					formatdate(r.lc_last_shipment_date) if r.lc_last_shipment_date else "-",
				]
				for r in rows
			],
		)
	]


def closure_pending(settings):
	# ["is", "not set"] compiles to ifnull(field,'')='' -- it matches both NULL and
	# '' . ["in", ["", None]] becomes SQL `IN ('', NULL)`, which never matches NULL,
	# so it silently skipped every shipment whose XAR/EBRC had never been touched.
	blocks = []

	xar_days = settings.xar_pending_days or 7
	xar_cutoff = add_days(today(), -xar_days)
	xar_rows = frappe.get_all(
		"Export Shipment",
		filters={
			"payment_status": "Fully Paid",
			"xar_no": ["is", "not set"],
			"final_payment_date": ["<=", xar_cutoff],
		},
		fields=["name", "customer_name", "final_payment_date", "shipping_bill_no"],
		limit=100,
	)
	if xar_rows:
		blocks.append(
			table(
				"Paid in full, XAR not generated for more than {0} day(s)".format(xar_days),
				["Shipment", "Customer", "Shipping Bill", "Payment Received On"],
				[
					[
						link("Export Shipment", r.name),
						r.customer_name or "",
						r.shipping_bill_no or "-",
						formatdate(r.final_payment_date) if r.final_payment_date else "-",
					]
					for r in xar_rows
				],
			)
		)

	ebrc_days = settings.ebrc_pending_days or 15
	ebrc_cutoff = add_days(today(), -ebrc_days)
	ebrc_rows = frappe.get_all(
		"Export Shipment",
		filters={
			"xar_no": ["is", "set"],
			"ebrc_no": ["is", "not set"],
			"xar_date": ["<=", ebrc_cutoff],
		},
		fields=["name", "customer_name", "xar_no", "xar_date"],
		limit=100,
	)
	if ebrc_rows:
		blocks.append(
			table(
				"XAR done, EBRC not generated for more than {0} day(s)".format(ebrc_days),
				["Shipment", "Customer", "XAR No", "XAR Date"],
				[
					[
						link("Export Shipment", r.name),
						r.customer_name or "",
						r.xar_no or "-",
						formatdate(r.xar_date) if r.xar_date else "-",
					]
					for r in ebrc_rows
				],
			)
		)

	return blocks


def realisation_due(settings):
	"""Export proceeds have a statutory realisation window from the shipping
	bill date. Warn a month before it closes."""
	months = settings.realisation_period_months or 9
	warn_from = add_months(today(), -(months - 1))

	rows = frappe.get_all(
		"Export Shipment",
		filters={
			"payment_status": ["!=", "Fully Paid"],
			"shipping_bill_date": ["<=", warn_from],
			"status": ["not in", ["EBRC Generated"]],
		},
		fields=["name", "customer_name", "shipping_bill_no", "shipping_bill_date",
		        "outstanding_amount", "currency"],
		limit=100,
	)
	if not rows:
		return []

	return [
		table(
			"Realisation window closing (within {0} months of shipping bill)".format(months),
			["Shipment", "Customer", "Shipping Bill", "SB Date", "Due By", "Outstanding"],
			[
				[
					link("Export Shipment", r.name),
					r.customer_name or "",
					r.shipping_bill_no or "-",
					formatdate(r.shipping_bill_date),
					formatdate(add_months(getdate(r.shipping_bill_date), months)),
					fmt_money(r.outstanding_amount, r.currency),
				]
				for r in rows
			],
		)
	]


# ----------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------
def get_recipients(role):
	users = frappe.get_all(
		"Has Role", filters={"role": role, "parenttype": "User"}, pluck="parent"
	)
	return [
		u
		for u in set(users)
		if u not in ("Administrator", "Guest") and frappe.db.get_value("User", u, "enabled")
	]


def link(doctype, name):
	return get_link_to_form(doctype, name)


def fmt_money(value, currency):
	return frappe.utils.fmt_money(value or 0, currency=currency)


def table(title, headers, rows):
	head = "".join("<th>{0}</th>".format(h) for h in headers)
	body = "".join(
		"<tr>{0}</tr>".format("".join("<td>{0}</td>".format(c) for c in row)) for row in rows
	)
	return (
		"<h4>{0}</h4>"
		"<table class='table table-bordered'><thead><tr>{1}</tr></thead><tbody>{2}</tbody></table>"
	).format(title, head, body)


def send(subject, blocks, recipients):
	blocks = [b for b in blocks if b]
	if not blocks:
		return

	frappe.sendmail(
		recipients=recipients,
		subject=subject,
		message="".join(blocks),
	)
