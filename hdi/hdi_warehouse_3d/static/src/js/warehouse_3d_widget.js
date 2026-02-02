/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onMounted, useRef } from "@odoo/owl";
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
        this.canvasRef = useRef("designerCanvas");
        
        this.state = useState({
            areas: [],
            shelves: [],
            bins: [],
            selectedItem: null,
            mode: 'select', // select, move, resize, create_shelf, create_bin
            gridSize: 20, // SKUsavvy-style: smaller grid for better precision
            zoom: 1.0,
            showGrid: true,
            isDragging: false,
            dragOffset: { x: 0, y: 0 }
        });

        onMounted(() => {
            this.loadLayoutData();
            // Delay canvas init to ensure DOM is ready
            setTimeout(() => {
                this.initCanvas();
            }, 100);
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
        console.log('🎨 Initializing canvas...');
        
        this.canvas = this.canvasRef.el;
        if (!this.canvas) {
            console.error('❌ Canvas element not found via ref');
            return;
        }
        
        console.log('✅ Canvas found:', this.canvas);
        this.ctx = this.canvas.getContext('2d');
        
        // SKUsavvy style: Full screen canvas
        const container = this.canvas.parentElement;
        this.canvas.width = container.clientWidth;
        this.canvas.height = container.clientHeight;
        
        console.log(`✅ Canvas initialized: ${this.canvas.width}x${this.canvas.height}`);
        
        // Mouse events for drag & drop
        this.canvas.addEventListener('mousedown', this.onMouseDown.bind(this));
        this.canvas.addEventListener('mousemove', this.onMouseMove.bind(this));
        this.canvas.addEventListener('mouseup', this.onMouseUp.bind(this));
        
        // Window resize handler
        window.addEventListener('resize', () => {
            this.canvas.width = container.clientWidth;
            this.canvas.height = container.clientHeight;
            this.renderLayout();
        });
        
        // Trigger initial render if data already loaded
        if (this.state.areas.length > 0 || this.state.shelves.length > 0 || this.state.bins.length > 0) {
            console.log('🎨 Data already loaded, rendering now...');
            this.renderLayout();
        }
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
        if (!this.state.showGrid) return;
        
        this.ctx.strokeStyle = '#F0F0F0';
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
        
        console.log(`📐 Area "${area.name}" at pixel (${x}, ${y}) size ${w}x${h}`);
        
        // SKUsavvy style: transparent area background
        this.ctx.fillStyle = 'rgba(232, 232, 255, 0.15)';
        this.ctx.fillRect(x, y, w, h);
        
        // Thin border
        this.ctx.strokeStyle = '#CCCCDD';
        this.ctx.lineWidth = 1;
        this.ctx.strokeRect(x, y, w, h);
        
        // Area label
        this.ctx.fillStyle = '#666';
        this.ctx.font = '12px Arial';
        this.ctx.fillText(area.name, x + 5, y + 15);
    }

    drawShelf(shelf) {
        // Unified scale: all coordinates use gridSize
        const x = shelf.position_x * this.state.gridSize;
        const y = shelf.position_y * this.state.gridSize;
        const w = shelf.width * this.state.gridSize; // Meters converted to grid units
        const h = shelf.depth * this.state.gridSize;
        
        console.log(`📦 Shelf "${shelf.code}" at pixel (${x}, ${y}) size ${Math.round(w)}x${Math.round(h)}`);
        
        // SKUsavvy style: solid purple for shelves
        this.ctx.fillStyle = '#9494FF';
        this.ctx.fillRect(x, y, w, h);
        
        this.ctx.strokeStyle = '#6C63FF';
        this.ctx.lineWidth = 2;
        this.ctx.strokeRect(x, y, w, h);
        
        // Shelf label (vertical if needed)
        this.ctx.fillStyle = '#FFF';
        this.ctx.font = 'bold 11px Arial';
        this.ctx.fillText(shelf.code, x + 3, y + 12);
    }

    drawBin(bin) {
        if (!bin.coordinates) {
            console.warn('⚠️ Bin missing coordinates:', bin);
            return;
        }
        
        // Unified scale
        const x = bin.coordinates.x * this.state.gridSize;
        const y = bin.coordinates.y * this.state.gridSize;
        const w = (bin.width || 0.5) * this.state.gridSize;
        const h = (bin.depth || 0.5) * this.state.gridSize;
        
        // Color by state (SKUsavvy style)
        let fillColor = '#D4D4FF'; // empty
        if (bin.state === 'occupied') fillColor = '#6C63FF';
        if (bin.state === 'blocked') fillColor = '#FF6B6B';
        
        this.ctx.fillStyle = bin.color || fillColor;
        this.ctx.fillRect(x, y, w, h);
        
        this.ctx.strokeStyle = '#333';
        this.ctx.lineWidth = 1;
        this.ctx.strokeRect(x, y, w, h);
    }

    highlightSelected(item) {
        if (!item || !item.data) return;
        
        const data = item.data;
        let x, y, w, h;
        
        // Get bounds based on item type
        if (item.type === 'area') {
            x = data.position_x * this.state.gridSize;
            y = data.position_y * this.state.gridSize;
            w = data.width * this.state.gridSize;
            h = data.height * this.state.gridSize;
        } else if (item.type === 'shelf') {
            x = data.position_x * this.state.gridSize;
            y = data.position_y * this.state.gridSize;
            w = data.width * this.state.gridSize;
            h = data.depth * this.state.gridSize;
        } else if (item.type === 'bin' && data.coordinates) {
            x = data.coordinates.x * this.state.gridSize;
            y = data.coordinates.y * this.state.gridSize;
            w = (data.width || 0.5) * this.state.gridSize;
            h = (data.depth || 0.5) * this.state.gridSize;
        } else {
            return;
        }
        
        // Draw selection highlight
        this.ctx.strokeStyle = this.state.isDragging ? '#00FF00' : '#FF4444';
        this.ctx.lineWidth = 3;
        this.ctx.setLineDash([8, 4]);
        this.ctx.strokeRect(x - 2, y - 2, w + 4, h + 4);
        this.ctx.setLineDash([]);
        
        // Draw corner handles for resize mode
        if (this.state.mode === 'resize') {
            const handleSize = 8;
            this.ctx.fillStyle = '#FF4444';
            // Top-left
            this.ctx.fillRect(x - handleSize/2, y - handleSize/2, handleSize, handleSize);
            // Top-right
            this.ctx.fillRect(x + w - handleSize/2, y - handleSize/2, handleSize, handleSize);
            // Bottom-left
            this.ctx.fillRect(x - handleSize/2, y + h - handleSize/2, handleSize, handleSize);
            // Bottom-right
            this.ctx.fillRect(x + w - handleSize/2, y + h - handleSize/2, handleSize, handleSize);
        }
    }

    onMouseDown(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        // Select item at mouse position
        const item = this.getItemAt(x, y);
        this.state.selectedItem = item;
        
        if (item) {
            console.log(`🎯 Selected ${item.type}: ${item.data.name || item.data.code}`);
            
            // If in move mode and item selected, prepare for drag
            if (this.state.mode === 'move') {
                this.state.isDragging = true;
                
                // Calculate offset from item's top-left to mouse position
                const itemX = (item.data.position_x || item.data.coordinates?.x || 0) * this.state.gridSize;
                const itemY = (item.data.position_y || item.data.coordinates?.y || 0) * this.state.gridSize;
                
                this.state.dragOffset.x = x - itemX;
                this.state.dragOffset.y = y - itemY;
                
                this.canvas.style.cursor = 'grabbing';
                console.log(`🖐️ Started dragging ${item.type}`);
            }
        }
        
        this.renderLayout();
    }

    onMouseMove(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        // Update cursor based on mode and hover
        if (this.state.mode === 'move' && !this.state.isDragging) {
            const item = this.getItemAt(x, y);
            this.canvas.style.cursor = item ? 'grab' : 'default';
        }
        
        // Handle dragging
        if (this.state.isDragging && this.state.selectedItem) {
            // Calculate new position with offset
            const newX = x - this.state.dragOffset.x;
            const newY = y - this.state.dragOffset.y;
            
            // Snap to grid
            const gridX = Math.round(newX / this.state.gridSize);
            const gridY = Math.round(newY / this.state.gridSize);
            
            // Update item position in state (live preview)
            const item = this.state.selectedItem.data;
            if (item.position_x !== undefined) {
                // Shelf or Area
                item.position_x = Math.max(0, gridX);
                item.position_y = Math.max(0, gridY);
            } else if (item.coordinates) {
                // Bin
                item.coordinates.x = Math.max(0, gridX);
                item.coordinates.y = Math.max(0, gridY);
            }
            
            // Re-render with new position
            this.renderLayout();
        }
    }

    onMouseUp(e) {
        if (this.state.isDragging && this.state.selectedItem) {
            console.log(`✅ Drag completed, saving position...`);
            
            // Save position to database
            this.saveItemPosition(this.state.selectedItem);
            
            // Reset drag state
            this.state.isDragging = false;
            this.canvas.style.cursor = this.state.mode === 'move' ? 'grab' : 'default';
        }
    }

    getItemAt(x, y) {
        // Check which item is at this position
        // Priority: bins > shelves > areas (top to bottom)
        
        // Check bins first (smallest items, highest priority)
        for (let bin of this.state.bins) {
            if (!bin.coordinates) continue;
            
            const bx = bin.coordinates.x * this.state.gridSize;
            const by = bin.coordinates.y * this.state.gridSize;
            const bw = (bin.width || 0.5) * this.state.gridSize;
            const bh = (bin.depth || 0.5) * this.state.gridSize;
            
            if (x >= bx && x <= bx + bw && y >= by && y <= by + bh) {
                return { type: 'bin', data: bin, model: 'stock.location' };
            }
        }
        
        // Check shelves
        for (let shelf of this.state.shelves) {
            const sx = shelf.position_x * this.state.gridSize;
            const sy = shelf.position_y * this.state.gridSize;
            const sw = shelf.width * this.state.gridSize;
            const sh = shelf.depth * this.state.gridSize;
            
            if (x >= sx && x <= sx + sw && y >= sy && y <= sy + sh) {
                return { type: 'shelf', data: shelf, model: 'warehouse.shelf' };
            }
        }
        
        // Check areas (largest, lowest priority)
        for (let area of this.state.areas) {
            const ax = area.position_x * this.state.gridSize;
            const ay = area.position_y * this.state.gridSize;
            const aw = area.width * this.state.gridSize;
            const ah = area.height * this.state.gridSize;
            
            if (x >= ax && x <= ax + aw && y >= ay && y <= ay + ah) {
                return { type: 'area', data: area, model: 'warehouse.area' };
            }
        }
        
        return null;
    }

    async saveItemPosition(item) {
        if (!item || !item.data) return;
        
        try {
            const data = item.data;
            const updates = {};
            
            // Determine which fields to update based on item type
            if (data.position_x !== undefined) {
                // Shelf or Area
                updates.position_x = data.position_x;
                updates.position_y = data.position_y;
            } else if (data.coordinates) {
                // Bin - update via stock.location
                updates.posx = data.coordinates.x;
                updates.posy = data.coordinates.y;
            }
            
            console.log(`💾 Saving ${item.type} #${data.id}:`, updates);
            
            await this.orm.write(item.model, [data.id], updates);
            
            console.log(`✅ ${item.type} position saved`);
        } catch (e) {
            console.error('❌ Failed to save position:', e);
            alert('Failed to save position. Check console for details.');
        }
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
