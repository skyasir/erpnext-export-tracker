import frappe
from frappe import _
from frappe.model.document import Document


class ExportDocumentTemplate(Document):
	def validate(self):
		self.validate_duplicate_documents()
		self.validate_single_fallback()

	def validate_duplicate_documents(self):
		seen = set()
		for row in self.documents:
			key = ((row.document_name or "").strip().lower(), row.stage)
			if key in seen:
				frappe.throw(
					_("Row {0}: {1} is listed twice for the {2} stage.").format(
						row.idx, row.document_name, row.stage
					)
				)
			seen.add(key)

	def validate_single_fallback(self):
		if not self.is_default:
			return

		other = frappe.db.get_value(
			"Export Document Template",
			{"is_default": 1, "name": ["!=", self.name]},
			"name",
		)
		if other:
			frappe.throw(
				_("{0} is already the fallback template. Only one fallback is allowed.").format(
					frappe.utils.get_link_to_form("Export Document Template", other)
				)
			)
