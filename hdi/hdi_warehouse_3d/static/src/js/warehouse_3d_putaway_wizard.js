/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * 3D PUTAWAY WIZARD
 * Integrated with Odoo 18 Incoming Picking workflow
 * 
 * Flow:
 * 1. Odoo Incoming Picking
 * 2. Stock Move Line (Lot/Serial)
 * 3. Open 3D via button "🏗️ 3D Putaway"
 * 4. Click Bin
 * 5. Assign Lot → Bin
 * 6. Update move_line.location_dest_id
 * 7. User validates picking normally
 * 8. stock.quant created at assigned bin
 * 9. 3D shows updated bin color
 * 
 * 📌 3D KHÔNG thay thế validate picking
 * 📌 Chỉ can thiệp vào bước "đặt hàng ở đâu"
 */
export class Warehouse3DPutawayWizard extends Component {
    setup() {
        this.orm = useService("orm");
        this.rpc = useService("rpc");
        this.action = useService("action");
        
        this.state = useState({
            pickingId: null,
            picking: null,
            moveLines: [],
            selectedMoveLine: null,
            bins: [],
            selectedBin: null,
            filterArea: null,
            viewMode: '2d',
        });

        onMounted(async () => {
            // Get picking context
            this.state.pickingId = this.props.action?.context?.default_picking_id;
            
            if (this.state.pickingId) {
                await this.loadPickingData();
                await this.loadWarehouseData();
            }
        });
    }

    async loadPickingData() {
        // Load picking and move lines
        const picking = await this.orm.read(
            'stock.picking',
            [this.state.pickingId],
            ['name', 'partner_id', 'scheduled_date', 'picking_type_id', 'state']
        );
        this.state.picking = picking[0];

        // Load move lines that need bin assignment
        const moveLines = await this.orm.searchRead(
            'stock.move.line',
            [
                ['picking_id', '=', this.state.pickingId],
                ['location_dest_id.usage', '=', 'internal'],
            ],
            ['product_id', 'lot_id', 'lot_name', 'reserved_uom_qty', 'product_uom_id', 
             'location_dest_id', 'warehouse_bin_assigned', 'assigned_bin_id']
        );
        this.state.moveLines = moveLines;
        
        // Auto-select first unassigned line
        const unassigned = moveLines.find(ml => !ml.warehouse_bin_assigned);
        if (unassigned) {
            this.state.selectedMoveLine = unassigned;
        }
    }

    async loadWarehouseData() {
        const data = await this.rpc('/warehouse_3d/get_layout', {
            area_id: this.state.filterArea
        });
        this.state.bins = data.bins;
        this.renderWarehouse();
    }

    renderWarehouse() {
        // Similar to 3D Viewer rendering
        const canvas = this.el.querySelector('#putaway_canvas');
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        this.state.bins.forEach(bin => {
            const x = bin.coordinates.x * 10;
            const y = bin.coordinates.y * 10;
            const size = 15;
            
            // Highlight suitable bins for selected product
            let color = bin.color;
            if (this.state.selectedBin?.id === bin.id) {
                color = '#FFD700'; // Gold for selected
            }
            
            ctx.fillStyle = color;
            ctx.fillRect(x, y, size, size);
            
            ctx.strokeStyle = '#333';
            ctx.lineWidth = 0.5;
            ctx.strokeRect(x, y, size, size);
        });
    }

    selectMoveLine(moveLine) {
        this.state.selectedMoveLine = moveLine;
        this.renderWarehouse();
    }

    async selectBin(bin) {
        if (!this.state.selectedMoveLine) {
            alert('⚠️ Please select a product line first');
            return;
        }
        
        this.state.selectedBin = bin;
        
        // Show bin details
        const detail = await this.rpc('/warehouse_3d/get_bin_detail', {
            bin_id: bin.id
        });
        
        this.showBinDetail(detail);
    }

    showBinDetail(detail) {
        const panel = this.el.querySelector('#putaway_bin_detail');
        if (!panel) return;
        
        panel.innerHTML = `
            <h5>${detail.name}</h5>
            <p><strong>State:</strong> <span class="badge bin_${detail.state}">${detail.state}</span></p>
            <p><strong>Current Load:</strong> ${detail.inventory.reduce((sum, inv) => sum + inv.quantity, 0)} / ${detail.dimensions.capacity || 'N/A'}</p>
            
            ${detail.is_blocked ? `
                <div class="alert alert-danger">
                    🚫 Bin is blocked: ${detail.block_reason}
                </div>
            ` : `
                <button class="btn btn-success w-100" onclick="window.putawayWizard.assignToBin()">
                    ✅ Assign Here
                </button>
            `}
        `;
        
        window.putawayWizard = this; // Store reference
    }

    async assignToBin() {
        if (!this.state.selectedMoveLine || !this.state.selectedBin) {
            alert('⚠️ Please select both product and bin');
            return;
        }
        
        try {
            // Call backend to assign bin
            const result = await this.rpc('/warehouse_3d/assign_move_line_to_bin', {
                move_line_id: this.state.selectedMoveLine.id,
                bin_id: this.state.selectedBin.id,
            });
            
            if (result.success) {
                alert(`✅ ${result.message}`);
                
                // Mark as assigned in UI
                this.state.selectedMoveLine.warehouse_bin_assigned = true;
                this.state.selectedMoveLine.assigned_bin_id = result.bin_id;
                
                // Move to next unassigned line
                const nextUnassigned = this.state.moveLines.find(
                    ml => !ml.warehouse_bin_assigned && ml.id !== this.state.selectedMoveLine.id
                );
                
                if (nextUnassigned) {
                    this.selectMoveLine(nextUnassigned);
                } else {
                    // All assigned
                    alert('🎉 All products assigned! You can now close this and validate the picking.');
                }
                
                // Reload warehouse to update colors
                await this.loadWarehouseData();
            } else {
                alert(`❌ Error: ${result.error}`);
            }
        } catch (error) {
            alert(`❌ Error: ${error.message}`);
        }
    }

    async closeWizard() {
        // Check if all lines are assigned
        const unassigned = this.state.moveLines.filter(ml => !ml.warehouse_bin_assigned);
        
        if (unassigned.length > 0) {
            const confirm = window.confirm(
                `⚠️ ${unassigned.length} product(s) not yet assigned to bins.\n\n` +
                `They will use default location.\n\nContinue?`
            );
            if (!confirm) return;
        }
        
        // Close wizard and return to picking
        this.action.doAction({
            type: 'ir.actions.act_window_close'
        });
    }
}

Warehouse3DPutawayWizard.template = "hdi_warehouse_3d.warehouse_3d_putaway_wizard";

// Register component
registry.category("actions").add("warehouse_3d_putaway_wizard", Warehouse3DPutawayWizard);
