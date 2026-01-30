/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState } from "@odoo/owl";
import { WarehouseMap2D } from "./warehouse_map_2d";
import { WarehouseMap3D } from "./warehouse_map_3d";

/**
 * Main Warehouse Map Widget
 * Wrapper component cho phép chuyển đổi giữa 2D và 3D view
 */
export class WarehouseMapWidget extends Component {
    setup() {
        this.state = useState({
            viewMode: '2d', // '2d' or '3d'
        });
    }
    
    switchTo2D() {
        this.state.viewMode = '2d';
    }
    
    switchTo3D() {
        this.state.viewMode = '3d';
    }
}

WarehouseMapWidget.template = "hdi_warehouse_map.WarehouseMapWidgetTemplate";
WarehouseMapWidget.components = { WarehouseMap2D, WarehouseMap3D };
WarehouseMapWidget.props = {
    context: { type: Object, optional: true },
};
