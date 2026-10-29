app_name = "erpnext_export_tracker"
app_title = "Export Tracker"
app_publisher = "Smurik Solutions"
app_description = (
	"Exporter-side shipment tracking for ERPNext (India) - CHA freight comparison, "
	"export document checklists, LC handling, bank closure (XAR/EBRC) and incentive handoff"
)
app_email = "info@smurik.com"
app_license = "mit"

after_install = "erpnext_export_tracker.install.after_install"

# Both of these have to run on every migrate, not once in a patch. A patch that
# defines a custom field fixes the site it ran on and then ignores every later
# edit to that definition; and Customize Form's field_order property setter
# outranks the DocType's own order, so a site that has ever opened it silently
# keeps whatever layout it froze. Fields first, then put them in position.
after_migrate = [
	# our own fields first, then India Compliance's GST set which anchors to
	# them -- its set changes with its version and with GST Settings, so it is
	# re-asserted rather than created once. The layout is rebuilt around both.
	"erpnext_export_tracker.install.make_custom_fields",
	"erpnext_export_tracker.install.make_gst_custom_fields",
	"erpnext_export_tracker.patches.resync_form_layouts.resync_all",
]

# ERPNext and India Compliance match a selling doctype by name against plain
# module globals -- including the allow-list that decides who may price an item.
# Those lists have to carry the Proforma Invoice in every process that serves
# one, and fetching an item or a pricing rule never builds the document, so the
# controller import cannot be relied on to put it there. Register at the start of
# each request and each background job instead; it is a flag check after the
# first call.
PRICING_REGISTER = "erpnext_export_tracker.selling_doctype.register"

before_request = [PRICING_REGISTER]
before_job = [PRICING_REGISTER]

doctype_js = {
	"Quotation": "public/js/quotation.js",
	"Sales Order": "public/js/sales_order.js",
	"Sales Invoice": "public/js/sales_invoice.js",
}

# Quotation -> Proforma Invoice -> Sales Order. Each document shows the next and
# the previous in its Connections, which neither erpnext doctype knows about on
# its own -- this is the supported way to add to another app's dashboard.
override_doctype_dashboards = {
	"Quotation": "erpnext_export_tracker.dashboards.quotation_dashboard",
	"Sales Order": "erpnext_export_tracker.dashboards.sales_order_dashboard",
}

# India Compliance registers its GST handling per doctype by name, so a document
# it has never heard of gets none. A Proforma Invoice is a Sales Order that has
# not been agreed yet; give it the same handlers the order gets, and it computes
# GST the same way. Harmless on a site without India Compliance -- frappe skips
# a hook whose module will not import.
GST_TRANSACTION = "india_compliance.gst_india.overrides.transaction"

doc_events = {
	"Proforma Invoice": {
		"onload": f"{GST_TRANSACTION}.onload",
		"before_print": f"{GST_TRANSACTION}.before_print",
		"before_validate": f"{GST_TRANSACTION}.before_validate_transaction",
		"validate": f"{GST_TRANSACTION}.validate_transaction",
		"before_update_after_submit": f"{GST_TRANSACTION}.before_update_after_submit",
		"after_mapping": f"{GST_TRANSACTION}.after_mapping",
	},
	"Sales Order": {
		"after_insert": "erpnext_export_tracker.events.sales_order.after_insert",
		"on_submit": "erpnext_export_tracker.events.sales_order.on_submit",
		"on_cancel": "erpnext_export_tracker.events.sales_order.on_cancel",
	},
	"Sales Invoice": {
		"on_submit": "erpnext_export_tracker.events.sales_invoice.on_submit",
		"on_cancel": "erpnext_export_tracker.events.sales_invoice.on_cancel",
	},
	"Delivery Note": {
		"on_submit": "erpnext_export_tracker.events.delivery_note.on_submit",
	},
	"Payment Entry": {
		"on_submit": "erpnext_export_tracker.events.payment_entry.on_submit",
		"on_cancel": "erpnext_export_tracker.events.payment_entry.on_cancel",
	},
}

scheduler_events = {
	"daily": [
		"erpnext_export_tracker.tasks.send_export_reminders",
	],
}

fixtures = [
	{"dt": "Custom Field", "filters": [["module", "=", "Export Tracker"]]},
	{"dt": "Property Setter", "filters": [["module", "=", "Export Tracker"]]},
]
