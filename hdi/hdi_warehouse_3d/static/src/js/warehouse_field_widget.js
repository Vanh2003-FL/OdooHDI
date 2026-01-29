/** @odoo-module **/

import { Component, useState, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Warehouse3DViewer } from "./warehouse_3d_viewer";
import { Warehouse2DViewer } from "./warehouse_2d_viewer";

/**
 * Field Widget for warehouse layout visualization
 * Can be used in form views with widget="warehouse_layout_viewer"
 */
export class WarehouseLayoutFieldWidget extends Component {
    static template = "hdi_warehouse_3d.WarehouseLayoutFieldWidget";
    static components = { Warehouse3DViewer, Warehouse2DViewer };
    
    static props = {
        readonly: { type: Boolean, optional: true },
        record: { type: Object },
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        
        this.state = useState({
            viewMode: '3d',
            showHeatmap: false,
            editable: false,
        });
    }

    get layoutId() {
        return this.props.record.data.id;
    }

    toggleViewMode() {
        this.state.viewMode = this.state.viewMode === '3d' ? '2d' : '3d';
    }

    toggleHeatmap() {
        this.state.showHeatmap = !this.state.showHeatmap;
    }

    toggleEditable() {
        this.state.editable = !this.state.editable;
    }

    async openFullscreen() {
        await this.action.doAction({
            type: 'ir.actions.client',
            tag: 'warehouse_3d_fullscreen',
            params: {
                layoutId: this.layoutId,
                viewMode: this.state.viewMode,
            },
        });
    }
}

registry.category("fields").add("warehouse_layout_viewer", {
    component: WarehouseLayoutFieldWidget,
});


/**
 * Field Widget for picking route visualization
 * Can be used in picking form views
 */
export class PickingRouteFieldWidget extends Component {
    static template = "hdi_warehouse_3d.PickingRouteFieldWidget";
    
    static props = {
        readonly: { type: Boolean, optional: true },
        record: { type: Object },
    };

    setup() {
        this.orm = useService("orm");
        this.rpc = useService("rpc");
        this.notification = useService("notification");
        
        this.state = useState({
            loading: false,
            routeData: null,
            hasRoute: false,
        });

        onMounted(() => {
            this.loadRouteData();
        });
    }

    get pickingId() {
        return this.props.record.data.id;
    }

    async loadRouteData() {
        if (!this.pickingId) return;

        try {
            this.state.loading = true;
            const route = await this.orm.searchRead(
                'stock.picking.route',
                [['picking_id', '=', this.pickingId]],
                ['id', 'route_type', 'bin_count', 'route_distance', 'estimated_time']
            );
            
            if (route.length > 0) {
                this.state.routeData = route[0];
                this.state.hasRoute = true;
            }
            
            this.state.loading = false;
        } catch (error) {
            console.error('Failed to load route:', error);
            this.state.loading = false;
        }
    }

    async optimizeRoute() {
        if (!this.pickingId) return;

        try {
            this.state.loading = true;
            await this.rpc(`/warehouse_3d/optimize_route/${this.pickingId}`, {});
            this.notification.add('Route optimized successfully', { type: 'success' });
            await this.loadRouteData();
        } catch (error) {
            this.notification.add('Failed to optimize route', { type: 'danger' });
            console.error(error);
        } finally {
            this.state.loading = false;
        }
    }

    async visualizeRoute() {
        if (!this.state.routeData) return;

        // Open 3D viewer with route
        const layoutId = this.props.record.data.warehouse_id?.[0];
        if (!layoutId) {
            this.notification.add('No warehouse layout found', { type: 'warning' });
            return;
        }

        window.open(`/warehouse_3d/viewer?layout=${layoutId}&picking=${this.pickingId}`, '_blank');
    }
}

registry.category("fields").add("picking_route_viewer", {
    component: PickingRouteFieldWidget,
});


/**
 * Field Widget for warehouse heatmap visualization
 * Shows color-coded bin activity
 */
export class WarehouseHeatmapFieldWidget extends Component {
    static template = "hdi_warehouse_3d.WarehouseHeatmapFieldWidget";
    
    static props = {
        readonly: { type: Boolean, optional: true },
        record: { type: Object },
    };

    setup() {
        this.rpc = useService("rpc");
        
        this.state = useState({
            loading: false,
            stats: {
                totalPicks: 0,
                maxPicks: 0,
                avgPicks: 0,
            },
        });

        onMounted(() => {
            this.loadStats();
        });
    }

    get layoutId() {
        return this.props.record.data.layout_id?.[0];
    }

    async loadStats() {
        if (!this.layoutId) return;

        try {
            this.state.loading = true;
            const data = await this.rpc(`/warehouse_3d/heatmap/${this.layoutId}`, {});
            
            this.state.stats = {
                totalPicks: data.total_picks || 0,
                maxPicks: data.max_picks || 0,
                avgPicks: data.avg_picks || 0,
            };
            
            this.state.loading = false;
        } catch (error) {
            console.error('Failed to load heatmap stats:', error);
            this.state.loading = false;
        }
    }

    getHeatColor(intensity) {
        // intensity: 0-1
        if (intensity < 0.25) return '#2196F3'; // blue
        if (intensity < 0.5) return '#4CAF50'; // green
        if (intensity < 0.75) return '#FFC107'; // yellow
        return '#F44336'; // red
    }
}

registry.category("fields").add("warehouse_heatmap_viewer", {
    component: WarehouseHeatmapFieldWidget,
});
