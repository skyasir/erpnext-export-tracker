frappe.ui.form.on("Sales Invoice", {
	custom_is_export(frm) {
		if (!frm.doc.custom_is_export) return;

		if (!frm.doc.custom_consignee_name) {
			frm.set_value("custom_consignee_name", frm.doc.customer_name);
		}

		// pull the exporter defaults so the invoice prints complete
		frappe.db.get_doc("Export Tracker Settings").then((settings) => {
			const map = {
				custom_pre_carriage_by: settings.default_pre_carriage_by,
				custom_place_of_receipt: settings.default_place_of_receipt,
				custom_port_of_loading: settings.default_port_of_loading,
				custom_country_of_origin: settings.default_country_of_origin,
				custom_goods_description: settings.goods_description,
			};
			Object.keys(map).forEach((field) => {
				if (map[field] && !frm.doc[field]) frm.set_value(field, map[field]);
			});
		});
	},

	custom_export_shipment(frm) {
		if (!frm.doc.custom_export_shipment) return;

		frappe.db.get_doc("Export Shipment", frm.doc.custom_export_shipment).then((shipment) => {
			const map = {
				custom_consignee_name: shipment.consignee_name,
				custom_consignee_address: shipment.consignee_address,
				custom_buyer_name: shipment.buyer_same_as_consignee ? null : shipment.buyer_name,
				custom_buyer_address: shipment.buyer_same_as_consignee
					? null
					: shipment.buyer_address,
				custom_pre_carriage_by: shipment.pre_carriage_by,
				custom_place_of_receipt: shipment.place_of_receipt,
				custom_port_of_loading: shipment.port_of_loading,
				custom_vessel_flight_no: shipment.vessel_flight_no,
				custom_port_of_discharge: shipment.port_of_discharge,
				custom_final_destination: shipment.final_destination,
				custom_country_of_origin: shipment.country_of_origin,
				custom_country_of_final_destination: shipment.country_of_final_destination,
				custom_container_no: shipment.container_no,
				custom_net_weight: shipment.net_weight,
				custom_gross_weight: shipment.gross_weight,
				custom_no_of_packages: shipment.no_of_packages,
				custom_terms_of_payment: shipment.terms_of_payment,
			};
			Object.keys(map).forEach((field) => {
				if (map[field]) frm.set_value(field, map[field]);
			});
			if (shipment.incoterm && !frm.doc.incoterm) frm.set_value("incoterm", shipment.incoterm);
		});
	},
});
