/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * Warehouse Map 2D Widget
 * Hiển thị sơ đồ kho dạng 2D với grid layout
 */
export class WarehouseMap2D extends Component {
    setup() {
        this.orm = useService("orm");
        this.rpc = useService("rpc");
        
        this.state = useState({
            warehouseData: null,
            selectedBin: null,
            highlightedBins: [],
            viewMode: '2d',
            zoom: 1.0,
        });
        
        onWillStart(async () => {
            await this.loadWarehouseData();
        });
    }
    
    async loadWarehouseData() {
        const warehouse_id = this.props.context?.default_warehouse_id;
        const data = await this.rpc("/warehouse_map/get_data", {
            warehouse_id: warehouse_id,
        });
        this.state.warehouseData = data;
        
        // Highlight bins if specified
        const highlight_bin_ids = this.props.context?.highlight_bin_ids;
        if (highlight_bin_ids && highlight_bin_ids.length > 0) {
            this.state.highlightedBins = highlight_bin_ids;
        }
    }
    
    async onBinClick(bin) {
        const details = await this.rpc("/warehouse_map/get_bin_details", {
            bin_id: bin.id,
        });
        this.state.selectedBin = details;
    }
    
    onBinHover(bin) {
        // Show tooltip with basic info
        console.log("Hover bin:", bin.name);
    }
    
    getBinStyle(bin) {
        const isHighlighted = this.state.highlightedBins.includes(bin.id);
        const baseStyle = {
            'background-color': bin.color,
            'border': isHighlighted ? '3px solid #f39c12' : '1px solid #333',
            'box-shadow': isHighlighted ? '0 0 10px #f39c12' : 'none',
        };
        return Object.entries(baseStyle).map(([k, v]) => `${k}: ${v}`).join('; ');
    }
    
    zoomIn() {
        this.state.zoom = Math.min(this.state.zoom + 0.1, 2.0);
    }
    
    zoomOut() {
        this.state.zoom = Math.max(this.state.zoom - 0.1, 0.5);
    }
    
    resetZoom() {
        this.state.zoom = 1.0;
    }
}

WarehouseMap2D.template = "hdi_warehouse_map.WarehouseMap2DTemplate";
WarehouseMap2D.props = {
    context: { type: Object, optional: true },
};

// Register as client action
registry.category("actions").add("warehouse_map_view", WarehouseMap2D);
