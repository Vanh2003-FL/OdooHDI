/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

/**
 * 2D LAYOUT DESIGNER
 * Purpose: Thiết kế, kéo thả, chia bin, đổi kích thước
 * NOT allowed: Gán hàng
 * Users: Admin/Manager only
 */
export class Warehouse2DDesigner extends Component {
    setup() {
        this.orm = useService("orm");
        
        this.state = useState({
            areas: [],
            shelves: [],
            bins: [],
            selectedItem: null,
            mode: 'select', // select, move, resize, create_shelf, create_bin
            gridSize: 50,
            zoom: 1.0
        });

        onMounted(() => {
            this.loadLayoutData();
            this.initCanvas();
        });
    }

    async loadLayoutData() {
        try {
            const data = await rpc('/warehouse_3d/get_layout', {});
            console.log('📦 Loaded warehouse data:', data);
            this.state.areas = data.areas || [];
            this.state.shelves = data.shelves || [];
            this.state.bins = data.bins || [];
            console.log(`✅ Areas: ${this.state.areas.length}, Shelves: ${this.state.shelves.length}, Bins: ${this.state.bins.length}`);
            this.renderLayout();
        } catch (e) {
            console.error('❌ Failed to load layout:', e);
        }
    }

    initCanvas() {
        if (!this.el) return;
        this.canvas = this.el.querySelector('#designer_canvas');
        if (!this.canvas) return;
        this.ctx = this.canvas.getContext('2d');
        this.canvas.width = 1200;
        this.canvas.height = 800;
        
        // Mouse events for drag & drop
        this.canvas.addEventListener('mousedown', this.onMouseDown.bind(this));
        this.canvas.addEventListener('mousemove', this.onMouseMove.bind(this));
        this.canvas.addEventListener('mouseup', this.onMouseUp.bind(this));
    }

    renderLayout() {
        if (!this.ctx || !this.canvas) {
            console.warn('⚠️ Canvas not ready');
            return;
        }
        
        console.log('🎨 Rendering layout...');
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Draw grid
        this.drawGrid();
        
        // Draw areas
        console.log(`Drawing ${this.state.areas.length} areas`);
        this.state.areas.forEach(area => this.drawArea(area));
        
        // Draw shelves
        console.log(`Drawing ${this.state.shelves.length} shelves`);
        this.state.shelves.forEach(shelf => this.drawShelf(shelf));
        
        // Draw bins
        console.log(`Drawing ${this.state.bins.length} bins`);
        this.state.bins.forEach(bin => this.drawBin(bin));
        
        // Draw selected item highlight
        if (this.state.selectedItem) {
            this.highlightSelected(this.state.selectedItem);
        }
        
        console.log('✅ Layout rendered');
    }

    drawGrid() {
        this.ctx.strokeStyle = '#E0E0E0';
        this.ctx.lineWidth = 0.5;
        
        for (let x = 0; x < this.canvas.width; x += this.state.gridSize) {
            this.ctx.beginPath();
            this.ctx.moveTo(x, 0);
            this.ctx.lineTo(x, this.canvas.height);
            this.ctx.stroke();
        }
        
        for (let y = 0; y < this.canvas.height; y += this.state.gridSize) {
            this.ctx.beginPath();
            this.ctx.moveTo(0, y);
            this.ctx.lineTo(this.canvas.width, y);
            this.ctx.stroke();
        }
    }

    drawArea(area) {
        const x = area.position_x * this.state.gridSize;
        const y = area.position_y * this.state.gridSize;
        const w = area.width * this.state.gridSize;
        const h = area.height * this.state.gridSize;
        
        this.ctx.fillStyle = area.color || '#E8E8FF';
        this.ctx.fillRect(x, y, w, h);
        
        this.ctx.strokeStyle = '#333';
        this.ctx.lineWidth = 2;
        this.ctx.strokeRect(x, y, w, h);
        
        this.ctx.fillStyle = '#000';
        this.ctx.font = '14px Arial';
        this.ctx.fillText(area.name, x + 10, y + 20);
    }

    drawShelf(shelf) {
        const x = shelf.position_x * this.state.gridSize;
        const y = shelf.position_y * this.state.gridSize;
        const w = shelf.width * 10; // Convert meters to pixels
        const h = shelf.depth * 10;
        
        this.ctx.fillStyle = '#B3B3FF';
        this.ctx.fillRect(x, y, w, h);
        
        this.ctx.strokeStyle = '#666';
        this.ctx.lineWidth = 1;
        this.ctx.strokeRect(x, y, w, h);
        
        this.ctx.fillStyle = '#000';
        this.ctx.font = '10px Arial';
        this.ctx.fillText(shelf.code, x + 2, y + 10);
    }

    drawBin(bin) {
        if (!bin.coordinates) {
            console.warn('⚠️ Bin missing coordinates:', bin);
            return;
        }
        
        const x = bin.coordinates.x * 10;
        const y = bin.coordinates.y * 10;
        const size = 8;
        
        this.ctx.fillStyle = bin.color || '#E8E8FF';
        this.ctx.fillRect(x, y, size, size);
        
        this.ctx.strokeStyle = '#333';
        this.ctx.lineWidth = 0.5;
        this.ctx.strokeRect(x, y, size, size);
    }

    highlightSelected(item) {
        // Highlight border for selected item
        this.ctx.strokeStyle = '#FF0000';
        this.ctx.lineWidth = 3;
        this.ctx.setLineDash([5, 5]);
        // Draw highlight based on item type
        this.ctx.setLineDash([]);
    }

    onMouseDown(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        // Select item at mouse position
        this.state.selectedItem = this.getItemAt(x, y);
    }

    onMouseMove(e) {
        if (this.state.mode === 'move' && this.state.selectedItem) {
            const rect = this.canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            // Update position (snap to grid)
            const gridX = Math.round(x / this.state.gridSize);
            const gridY = Math.round(y / this.state.gridSize);
            
            this.updateItemPosition(this.state.selectedItem, gridX, gridY);
            this.renderLayout();
        }
    }

    onMouseUp(e) {
        if (this.state.selectedItem && this.state.mode === 'move') {
            // Save position to database
            this.saveItemPosition(this.state.selectedItem);
        }
    }

    getItemAt(x, y) {
        // Check which item is at this position
        // Priority: bins > shelves > areas
        return null;
    }

    async updateItemPosition(item, x, y) {
        // Update item position in state
    }

    async saveItemPosition(item) {
        // Save to database via ORM
        await this.orm.write(item.model, [item.id], {
            position_x: item.x,
            position_y: item.y
        });
    }

    async createShelf() {
        // Open wizard to create new shelf
        const result = await rpc('/warehouse_3d/create_shelf', {
            name: prompt('Shelf Name:'),
            code: prompt('Shelf Code:'),
            area_id: this.state.selectedItem?.area_id || 1,
            width: 1.2,
            depth: 1.0,
            level_count: 4,
            bins_per_level: 2,
            orientation: 'horizontal',
        });
        
        if (result.success) {
            alert(`✅ Created shelf with ${result.bin_count} bins`);
            this.loadLayoutData();
        } else {
            alert(`❌ Error: ${result.error}`);
        }
    }

    async saveLayout() {
        // 📌 SKUSavvy rule: Save layout structure, DO NOT touch stock.quant
        const result = await rpc('/warehouse_3d/save_layout', {
            areas: this.state.areas,
            shelves: this.state.shelves,
        });
        
        if (result.success) {
            alert('✅ Layout saved successfully');
            if (result.errors.length > 0) {
                console.warn('Warnings:', result.errors);
            }
        } else {
            alert('❌ Save failed');
        }
    }

    rotateShelf() {
        if (!this.state.selectedItem || this.state.selectedItem.type !== 'shelf') {
            alert('Please select a shelf first');
            return;
        }
        
        // Toggle orientation
        this.state.selectedItem.orientation = 
            this.state.selectedItem.orientation === 'horizontal' ? 'vertical' : 'horizontal';
        this.renderLayout();
    }

    async divideBins() {
        // Divide shelf into more bins per level
        if (!this.state.selectedItem || this.state.selectedItem.type !== 'shelf') {
            alert('Please select a shelf first');
            return;
        }
        
        const newBinCount = parseInt(prompt('Bins per level:', this.state.selectedItem.bins_per_level));
        if (newBinCount && newBinCount > 0) {
            // Update shelf with new bin division
            await this.orm.write('warehouse.shelf', [this.state.selectedItem.id], {
                bins_per_level: newBinCount
            });
            
            // Note: This will require re-creating bins
            alert('⚠️ To apply changes, please delete old bins and re-create shelf');
        }
    }

    async createBin() {
        // Create new bin in selected shelf
        if (!this.state.selectedItem || this.state.selectedItem.type !== 'shelf') {
            alert('Please select a shelf first');
            return;
        }
        
        // Open wizard to create bin with size input
    }

    async resizeItem() {
        this.state.mode = 'resize';
        // Enable resize handles on selected item
    }

    zoomIn() {
        this.state.zoom = Math.min(this.state.zoom + 0.1, 2.0);
        this.renderLayout();
    }

    zoomOut() {
        this.state.zoom = Math.max(this.state.zoom - 0.1, 0.5);
        this.renderLayout();
    }

    toggleGrid() {
        this.state.showGrid = !this.state.showGrid;
        this.renderLayout();
    }
}

Warehouse2DDesigner.template = "hdi_warehouse_3d.warehouse_2d_designer";

/**
 * 3D WAREHOUSE VIEWER
 * Purpose: Quan sát, thao tác nghiệp vụ (putaway, pick)
 * NOT allowed: Sửa layout
 * Users: All warehouse users
 */
export class Warehouse3DViewer extends Component {
    setup() {
        this.orm = useService("orm");
        
        this.state = useState({
            bins: [],
            selectedBin: null,
            filterArea: null,
            filterShelf: null,
            viewMode: '2d', // 2d or 3d
            showEmpty: true,
            showBlocked: true
        });

        onMounted(() => {
            this.loadWarehouseData();
            this.init3DScene();
        });
    }

    async loadWarehouseData() {
        try {
            const data = await rpc('/warehouse_3d/get_layout', {
                area_id: this.state.filterArea,
                shelf_id: this.state.filterShelf
            });
            
            this.state.bins = data.bins;
            this.renderWarehouse();
        } catch (e) {
            console.error('Failed to load warehouse data:', e);
        }
    }

    init3DScene() {
        // Initialize Three.js scene for 3D view
        if (!this.el) return;
        this.canvas = this.el.querySelector('#viewer_canvas');
        // TODO: Three.js setup
    }

    renderWarehouse() {
        if (this.state.viewMode === '2d') {
            this.render2DView();
        } else {
            this.render3DView();
        }
    }

    render2DView() {
        // Render 2D top-down view with color-coded bins
        if (!this.el) return;
        const canvas = this.el.querySelector('#viewer_canvas');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        this.state.bins.forEach(bin => {
            if (!this.shouldShowBin(bin)) return;
            
            const x = bin.coordinates.x * 10;
            const y = bin.coordinates.y * 10;
            const size = 15;
            
            // Color by state
            ctx.fillStyle = bin.color;
            ctx.fillRect(x, y, size, size);
            
            ctx.strokeStyle = '#333';
            ctx.strokeRect(x, y, size, size);
            
            // Show inventory info on hover
            if (bin.id === this.state.selectedBin?.id) {
                this.drawBinTooltip(ctx, bin, x, y);
            }
        });
    }

    render3DView() {
        // Render 3D isometric view using Three.js
        // TODO: Implement 3D rendering
    }

    shouldShowBin(bin) {
        if (!this.state.showEmpty && bin.state === 'empty') return false;
        if (!this.state.showBlocked && bin.state === 'blocked') return false;
        return true;
    }

    drawBinTooltip(ctx, bin, x, y) {
        // Draw tooltip showing bin inventory
        ctx.fillStyle = 'rgba(255, 255, 255, 0.95)';
        ctx.fillRect(x + 20, y, 200, 100);
        
        ctx.fillStyle = '#000';
        ctx.font = '12px Arial';
        ctx.fillText(`Bin: ${bin.name}`, x + 25, y + 20);
        ctx.fillText(`State: ${bin.state}`, x + 25, y + 40);
        
        bin.inventory.forEach((item, i) => {
            ctx.fillText(
                `${item.product_code}: ${item.quantity}`,
                x + 25,
                y + 60 + (i * 15)
            );
        });
    }

    async onBinClick(bin) {
        this.state.selectedBin = bin;
        
        // Load full bin details
        const detail = await rpc('/warehouse_3d/get_bin_detail', {
            bin_id: bin.id
        });
        
        this.showBinDetailPanel(detail);
    }

    showBinDetailPanel(detail) {
        if (!this.el) return;
        const panel = this.el.querySelector('#bin_detail_panel');
        if (!panel) return;
        panel.innerHTML = `
            <div class="bin-detail-header">
                <h4>${detail.name}</h4>
                <button class="btn-close" onclick="document.getElementById('bin_detail_panel').classList.remove('active')">&times;</button>
            </div>
            <p><strong>State:</strong> <span class="badge bin_${detail.state}">${detail.state}</span></p>
            <p><strong>Location:</strong> ${detail.barcode}</p>
            ${detail.is_blocked ? `<div class="alert alert-warning">⚠️ ${detail.block_reason}</div>` : ''}
            
            <h5>📊 Current Inventory:</h5>
            ${detail.inventory.length === 0 ? '<p class="text-muted">Empty bin</p>' : ''}
            <table class="table table-sm">
                <thead>
                    <tr>
                        <th>Product</th>
                        <th>Lot</th>
                        <th>Qty</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    ${detail.inventory.map((inv, idx) => `
                        <tr>
                            <td>${inv.product_code}</td>
                            <td>${inv.lot_name || '-'}</td>
                            <td>${inv.quantity}</td>
                            <td>
                                <button class="btn btn-xs btn-danger" onclick="window.currentViewer.pickFromBin(${inv.product_id}, ${inv.quantity}, ${inv.lot_id || 'null'})">
                                    Pick
                                </button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
            
            <hr/>
            <h5>🔧 Operations:</h5>
            <div class="btn-group-vertical w-100 gap-2">
                ${!detail.is_blocked ? `
                    <button class="btn btn-primary btn-sm" onclick="window.currentViewer.openPutawayDialog(${detail.id})">
                        📦 Putaway to Here
                    </button>
                    <button class="btn btn-info btn-sm" onclick="window.currentViewer.openMoveDialog(${detail.id})">
                        🔄 Move from Here
                    </button>
                    <button class="btn btn-warning btn-sm" onclick="window.currentViewer.blockBin(${detail.id})">
                        🚫 Block Bin
                    </button>
                ` : `
                    <button class="btn btn-success btn-sm" onclick="window.currentViewer.unblockBin(${detail.id})">
                        ✅ Unblock Bin
                    </button>
                `}
            </div>
            
            <div class="mt-3 text-muted small">
                <strong>📌 Note:</strong> 3D operations edit stock.quant, NOT layout
            </div>
        `;
        panel.classList.add('active');
        window.currentViewer = this; // Store reference for onclick handlers
    }

    async openPutawayDialog(binId) {
        // Simple prompt-based putaway (can be replaced with proper wizard)
        const productId = prompt('Product ID:');
        const quantity = parseFloat(prompt('Quantity:'));
        const lotId = prompt('Lot/Serial (optional, leave empty if none):');
        
        if (!productId || !quantity) {
            alert('Product ID and Quantity are required');
            return;
        }
        
        await this.performPutaway(binId, productId, quantity, lotId || null);
    }

    async performPutaway(binId, productId, quantity, lotId) {
        const result = await rpc('/warehouse_3d/putaway', {
            bin_id: binId,
            product_id: productId,
            quantity: quantity,
            lot_id: lotId
        });
        
        if (result.success) {
            alert(`✅ ${result.message}`);
            this.loadWarehouseData(); // Refresh view
            // Reload bin detail
            const detail = await rpc('/warehouse_3d/get_bin_detail', { bin_id: binId });
            this.showBinDetailPanel(detail);
        } else {
            alert(`❌ Error: ${result.error}`);
        }
    }

    async pickFromBin(productId, quantity, lotId) {
        if (!this.state.selectedBin) return;
        
        const result = await rpc('/warehouse_3d/pick', {
            bin_id: this.state.selectedBin.id,
            product_id: productId,
            quantity: quantity,
            lot_id: lotId
        });
        
        if (result.success) {
            alert(`✅ ${result.message}`);
            this.loadWarehouseData();
            // Reload bin detail
            const detail = await rpc('/warehouse_3d/get_bin_detail', { bin_id: this.state.selectedBin.id });
            this.showBinDetailPanel(detail);
        } else {
            alert(`❌ Error: ${result.error}`);
        }
    }

    async openMoveDialog(fromBinId) {
        const toBinId = prompt('Move to Bin ID:');
        const productId = prompt('Product ID:');
        const quantity = parseFloat(prompt('Quantity:'));
        const lotId = prompt('Lot/Serial (optional):');
        
        if (!toBinId || !productId || !quantity) {
            alert('All fields are required');
            return;
        }
        
        const result = await rpc('/warehouse_3d/move_inventory', {
            from_bin_id: fromBinId,
            to_bin_id: toBinId,
            product_id: productId,
            quantity: quantity,
            lot_id: lotId || null
        });
        
        if (result.success) {
            alert(`✅ ${result.message}`);
            this.loadWarehouseData();
        } else {
            alert(`❌ Error: ${result.error}`);
        }
    }

    async blockBin(binId) {
        const reason = prompt('Block reason:');
        if (!reason) return;
        
        const result = await rpc('/warehouse_3d/block_bin', {
            bin_id: binId,
            reason: reason
        });
        
        if (result.success) {
            alert(`✅ ${result.message}`);
            this.loadWarehouseData();
            const detail = await rpc('/warehouse_3d/get_bin_detail', { bin_id: binId });
            this.showBinDetailPanel(detail);
        } else {
            alert(`❌ Error: ${result.error}`);
        }
    }

    async unblockBin(binId) {
        const result = await rpc('/warehouse_3d/unblock_bin', {
            bin_id: binId
        });
        
        if (result.success) {
            alert(`✅ ${result.message}`);
            this.loadWarehouseData();
            const detail = await rpc('/warehouse_3d/get_bin_detail', { bin_id: binId });
            this.showBinDetailPanel(detail);
        } else {
            alert(`❌ Error: ${result.error}`);
        }
    }

    switchView(mode) {
        this.state.viewMode = mode;
        this.renderWarehouse();
    }

    toggleEmptyBins() {
        this.state.showEmpty = !this.state.showEmpty;
        this.renderWarehouse();
    }

    toggleBlockedBins() {
        this.state.showBlocked = !this.state.showBlocked;
        this.renderWarehouse();
    }
}

Warehouse3DViewer.template = "hdi_warehouse_3d.warehouse_3d_viewer";

/**
 * UNIFIED WAREHOUSE VIEW
 * Toggle between 2D Designer and 3D Operations
 * Based on user permissions and mode selection
 */
export class WarehouseUnifiedView extends Component {
    static components = {
        Warehouse2DDesigner,
        Warehouse3DViewer
    };

    setup() {
        this.orm = useService("orm");
        
        this.state = useState({
            mode: '3d', // '2d' for design, '3d' for operations
            isManager: true, // Allow toggle, menu security will handle access
            areas: [],
            shelves: [],
            bins: [],
        });

        onMounted(async () => {
            // Load data
            await this.loadData();
        });
    }

    async loadData() {
        try {
            const data = await rpc('/warehouse_3d/get_layout', {});
            this.state.areas = data.areas;
            this.state.shelves = data.shelves;
            this.state.bins = data.bins;
        } catch (e) {
            console.error('Failed to load warehouse data:', e);
        }
    }

    switchTo2D() {
        // Toggle allowed - menu security handles access control
        this.state.mode = '2d';
    }

    switchTo3D() {
        this.state.mode = '3d';
    }
}

WarehouseUnifiedView.template = "hdi_warehouse_3d.warehouse_unified_view";

// Register components
registry.category("actions").add("warehouse_2d_designer", Warehouse2DDesigner);
registry.category("actions").add("warehouse_3d_viewer", Warehouse3DViewer);
registry.category("actions").add("warehouse_unified_view", WarehouseUnifiedView);
