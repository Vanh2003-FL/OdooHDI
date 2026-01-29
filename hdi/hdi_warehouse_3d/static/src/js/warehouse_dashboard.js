/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Layout } from "@web/search/layout";
import { Warehouse3DViewer } from "./warehouse_3d_viewer";

/**
 * Warehouse 3D Dashboard
 * Full-screen dashboard showing warehouse overview
 */
export class Warehouse3DDashboard extends Component {
    static template = "hdi_warehouse_3d.Warehouse3DDashboard";
    static components = { Layout, Warehouse3DViewer };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        
        this.state = useState({
            loading: true,
            selectedLayout: null,
            layouts: [],
            metrics: {
                totalBins: 0,
                emptyBins: 0,
                partialBins: 0,
                fullBins: 0,
                utilization: 0,
                efficiencyScore: 0,
            },
            recentPickings: [],
            topHotspots: [],
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    async loadDashboardData() {
        try {
            this.state.loading = true;

            // Load all layouts
            const layouts = await this.orm.searchRead(
                'warehouse.layout',
                [],
                ['id', 'name', 'warehouse_id'],
                { limit: 10 }
            );
            this.state.layouts = layouts;

            if (layouts.length > 0) {
                this.state.selectedLayout = layouts[0].id;
                await this.loadLayoutMetrics(this.state.selectedLayout);
            }

            // Load recent pickings
            const pickings = await this.orm.searchRead(
                'stock.picking',
                [['state', 'in', ['assigned', 'done']]],
                ['id', 'name', 'partner_id', 'scheduled_date'],
                { limit: 5, order: 'scheduled_date desc' }
            );
            this.state.recentPickings = pickings;

            this.state.loading = false;
        } catch (error) {
            console.error('Failed to load dashboard:', error);
            this.state.loading = false;
        }
    }

    async loadLayoutMetrics(layoutId) {
        try {
            // Load bins
            const bins = await this.orm.searchRead(
                'warehouse.bin',
                [['shelf_id.rack_id.aisle_id.layout_id', '=', layoutId]],
                ['bin_status']
            );

            const totalBins = bins.length;
            const emptyBins = bins.filter(b => b.bin_status === 'empty').length;
            const partialBins = bins.filter(b => b.bin_status === 'partial').length;
            const fullBins = bins.filter(b => b.bin_status === 'full').length;

            this.state.metrics = {
                totalBins,
                emptyBins,
                partialBins,
                fullBins,
                utilization: totalBins > 0 ? ((partialBins + fullBins) / totalBins * 100).toFixed(1) : 0,
                efficiencyScore: 0,
            };

            // Load latest efficiency score
            const metrics = await this.orm.searchRead(
                'warehouse.metrics',
                [['layout_id', '=', layoutId]],
                ['efficiency_score'],
                { limit: 1, order: 'date desc' }
            );

            if (metrics.length > 0) {
                this.state.metrics.efficiencyScore = metrics[0].efficiency_score;
            }

            // Load top hotspots
            const heatmap = await this.orm.searchRead(
                'warehouse.heatmap',
                [['layout_id', '=', layoutId]],
                ['heatmap_data'],
                { limit: 1, order: 'date desc' }
            );

            if (heatmap.length > 0 && heatmap[0].heatmap_data) {
                const hotspots = Object.entries(heatmap[0].heatmap_data)
                    .sort((a, b) => b[1] - a[1])
                    .slice(0, 5)
                    .map(([binId, picks]) => ({ binId: parseInt(binId), picks }));
                
                this.state.topHotspots = hotspots;
            }
        } catch (error) {
            console.error('Failed to load metrics:', error);
        }
    }

    async onLayoutChange(layoutId) {
        this.state.selectedLayout = layoutId;
        await this.loadLayoutMetrics(layoutId);
    }

    async openLayoutForm() {
        if (!this.state.selectedLayout) return;

        await this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'warehouse.layout',
            res_id: this.state.selectedLayout,
            views: [[false, 'form']],
            target: 'current',
        });
    }

    async openBinList() {
        await this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'warehouse.bin',
            views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
            target: 'current',
            domain: [['shelf_id.rack_id.aisle_id.layout_id', '=', this.state.selectedLayout]],
        });
    }

    async openMetricsReport() {
        await this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'warehouse.metrics',
            views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
            target: 'current',
            domain: [['layout_id', '=', this.state.selectedLayout]],
        });
    }

    getUtilizationColor(value) {
        if (value < 40) return 'text-danger';
        if (value < 70) return 'text-warning';
        return 'text-success';
    }

    getEfficiencyColor(value) {
        if (value < 50) return 'text-danger';
        if (value < 70) return 'text-warning';
        return 'text-success';
    }
}

registry.category("actions").add("warehouse_3d_dashboard", Warehouse3DDashboard);
