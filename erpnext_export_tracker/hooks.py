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

# Customize Form's field_order property setter outranks the DocType's own order,
# so re-assert the app's layout after every migrate -- otherwise a site that has
# ever opened Customize Form silently keeps whatever layout it froze.
after_migrate = ["erpnext_export_tracker.patches.resync_form_layouts.resync_all"]

doctype_js = {
	"Sales Order": "public/js/sales_order.js",
	"Sales Invoice": "public/js/sales_invoice.js",
}

doc_events = {
	"Sales Order": {
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
