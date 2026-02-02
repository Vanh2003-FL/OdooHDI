/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

export class Warehouse3DWidget extends Component {
    setup() {
        super.setup();
        this.loadWarehouseData();
    }

    async loadWarehouseData() {
        const data = await this.env.services.rpc({
            route: '/warehouse_3d/get_layout',
            params: {}
        });
        this.renderWarehouse(data);
    }

    renderWarehouse(data) {
        console.log('Warehouse data:', data);
        // 3D rendering logic here (using Three.js or similar)
        // For now, just log the data
    }

    async onBinClick(binId) {
        const detail = await this.env.services.rpc({
            route: '/warehouse_3d/get_bin_detail',
            params: { bin_id: binId }
        });
        this.showBinDetail(detail);
    }

    showBinDetail(detail) {
        console.log('Bin detail:', detail);
        // Show bin details in panel
    }
}

Warehouse3DWidget.template = "hdi_warehouse_3d.warehouse_3d_viewer";

registry.category("fields").add("warehouse_3d_widget", Warehouse3DWidget);
