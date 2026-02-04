/** @odoo-module **/
/**
 * 🗺️ HDI Warehouse Map 2D Renderer
 * ================================
 * Interactive 2D warehouse visualization with drag & drop, stock heatmap
 * Inspired by SKUSavvy architecture
 */

import { registry } from "@web/core/registry";
import { Component, useState, onMounted, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

export class WarehouseMap2D extends Component {
    setup() {
        this.orm = useService("orm");
        this.user = useService("user");
        this.notification = useService("notification");
        this.action = useService("action");
        this.rpc = rpc;
        
        this.canvasRef = useRef("mapCanvas");
        this.state = useState({
            warehouseId: null,  // Will be set in onMounted
            layoutData: null,
            selectedBin: null,
            highlightedBins: [],
            editMode: false,
            showHeatmap: false,
            showLabels: true,
            zoom: 1.0,
            panX: 0,
            panY: 0,
            // Edit mode properties
            gridSize: 20,
            snapToGrid: true,
            isResizing: false,
            resizeHandle: null,
            dragStartX: 0,
            dragStartY: 0,
        });
        
        onMounted(() => {
            this.initializeCanvas();
            this.initializeWarehouse();
            this.setupEventHandlers();
        });
    }
    
    /**
     * 🏭 Initialize warehouse ID (from props, context, or user's default)
     */
    async initializeWarehouse() {
        // Try to get warehouse ID from props
        if (this.props.warehouseId) {
            this.state.warehouseId = this.props.warehouseId;
            this.loadWarehouseLayout();
            return;
        }
        
        // Try to get from context/action
        if (this.props.context?.default_warehouse_id) {
            this.state.warehouseId = this.props.context.default_warehouse_id;
            this.loadWarehouseLayout();
            return;
        }
        
        // Get user's default warehouse
        try {
            const userId = this.user.userId;
            const user = await this.orm.read('res.users', [userId], ['warehouse_id']);
            if (user && user[0] && user[0].warehouse_id) {
                this.state.warehouseId = user[0].warehouse_id[0];
            } else {
                // Get first warehouse
                const warehouses = await this.orm.search('stock.warehouse', [], { limit: 1 });
                this.state.warehouseId = warehouses[0] || 1;
            }
            this.loadWarehouseLayout();
        } catch (error) {
            console.error('Failed to get user warehouse:', error);
            this.state.warehouseId = 1;
            this.loadWarehouseLayout();
        }
    }
    
    /**
     * 🎨 Initialize canvas for 2D rendering
     */
    initializeCanvas() {
        const canvas = this.canvasRef.el;
        if (!canvas) return;
        
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        
        // Set canvas size
        canvas.width = canvas.parentElement.clientWidth;
        canvas.height = 600;
        
        // Enable smooth rendering
        this.ctx.imageSmoothingEnabled = true;
    }
    
    /**
     * 📡 Load warehouse layout from server
     */
    async loadWarehouseLayout() {
        const warehouseId = this.props.warehouseId || 1;
        this.state.warehouseId = warehouseId;
        
        try {
            console.log('Loading warehouse layout for warehouse:', warehouseId);
            const data = await this.rpc('/warehouse_map/layout/' + warehouseId);
            console.log('Warehouse layout data:', data);
            
            if (!data || !data.zones || data.zones.length === 0) {
                this.notification.add('No warehouse layout configured', { type: 'warning' });
                this.state.layoutData = { zones: [] };
                this.render2DMap();
                return;
            }
            
            this.state.layoutData = data;
            this.render2DMap();
        } catch (error) {
            console.error('Failed to load warehouse layout:', error);
            this.notification.add('Failed to load warehouse layout: ' + error.message, { type: 'danger' });
        }
    }
    
    /**
     * 🎨 Render 2D warehouse map
     */
    render2DMap() {
        if (!this.ctx) return;
        if (!this.state.layoutData) {
            this.drawEmptyState();
            return;
        }
        
        const ctx = this.ctx;
        const { zoom, panX, panY } = this.state;
        
        // Clear canvas
        ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Apply transformations
        ctx.save();
        ctx.translate(panX, panY);
        ctx.scale(zoom, zoom);
        
        // Draw warehouse background
        ctx.fillStyle = '#f9f9f9';
        ctx.fillRect(0, 0, this.canvas.width / zoom, this.canvas.height / zoom);
        
        // Draw grid always visible for layout reference
        this.drawGrid();
        
        // Draw zones
        if (this.state.layoutData.zones && this.state.layoutData.zones.length > 0) {
            this.state.layoutData.zones.forEach(zone => {
                this.drawZone(zone);
            });
        } else {
            // No zones configured
            ctx.restore();
            this.drawEmptyState();
            return;
        }
        
        // Draw resize handles if selected
        if (this.state.editMode && this.state.selectedBin) {
            this.drawResizeHandles(this.state.selectedBin);
        }
        
        // Restore context
        ctx.restore();
    }
    
    /**
     * 📭 Draw empty state message
     */
    drawEmptyState() {
        const ctx = this.ctx;
        ctx.fillStyle = '#999';
        ctx.font = '16px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('No warehouse layout configured', this.canvas.width / 2, this.canvas.height / 2);
        ctx.fillText('Click Edit Mode and use right-click to add zones/racks/bins', this.canvas.width / 2, this.canvas.height / 2 + 30);
    }
    
    /**
     * 📐 Draw grid for snap-to-grid
     */
    drawGrid() {
        const ctx = this.ctx;
        const gridSize = this.state.gridSize;
        const width = this.canvas.width / this.state.zoom;
        const height = this.canvas.height / this.state.zoom;
        
        // Lighter grid in normal mode, darker in edit mode
        ctx.strokeStyle = this.state.editMode ? '#ccc' : '#e8e8e8';
        ctx.lineWidth = 0.5;
        
        // Vertical lines
        for (let x = 0; x <= width; x += gridSize) {
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, height);
            ctx.stroke();
        }
        
        // Horizontal lines
        for (let y = 0; y <= height; y += gridSize) {
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(width, y);
            ctx.stroke();
        }
    }
    
    /**
     * 🔲 Draw resize handles around selected bin
     */
    drawResizeHandles(bin) {
        const ctx = this.ctx;
        const handleSize = 8;
        
        ctx.fillStyle = '#2196F3';
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 2;
        
        // 8 handles: corners + midpoints
        const handles = [
            { x: bin.x, y: bin.y, pos: 'nw' },
            { x: bin.x + bin.w/2, y: bin.y, pos: 'n' },
            { x: bin.x + bin.w, y: bin.y, pos: 'ne' },
            { x: bin.x + bin.w, y: bin.y + bin.h/2, pos: 'e' },
            { x: bin.x + bin.w, y: bin.y + bin.h, pos: 'se' },
            { x: bin.x + bin.w/2, y: bin.y + bin.h, pos: 's' },
            { x: bin.x, y: bin.y + bin.h, pos: 'sw' },
            { x: bin.x, y: bin.y + bin.h/2, pos: 'w' },
        ];
        
        handles.forEach(handle => {
            ctx.fillRect(
                handle.x - handleSize/2,
                handle.y - handleSize/2,
                handleSize,
                handleSize
            );
            ctx.strokeRect(
                handle.x - handleSize/2,
                handle.y - handleSize/2,
                handleSize,
                handleSize
            );
        });
    }
    
    /**
     * 🏢 Draw a zone with its racks and bins
     */
    drawZone(zone) {
        const ctx = this.ctx;
        
        // Draw zone boundary
        ctx.strokeStyle = zone.color || '#3498db';
        ctx.lineWidth = 3;
        ctx.strokeRect(zone.x, zone.y, zone.w, zone.h);
        
        // Draw zone label
        if (this.state.showLabels) {
            ctx.fillStyle = zone.color || '#3498db';
            ctx.font = 'bold 16px Arial';
            ctx.fillText(zone.location_name, zone.x + 10, zone.y - 10);
        }
        
        // Draw racks
        if (zone.racks) {
            zone.racks.forEach(rack => {
                this.drawRack(rack);
            });
        }
    }
    
    /**
     * 📦 Draw a rack with its bins
     */
    drawRack(rack) {
        const ctx = this.ctx;
        
        // Draw rack
        ctx.save();
        ctx.translate(rack.x + rack.w / 2, rack.y + rack.h / 2);
        ctx.rotate((rack.rotation || 0) * Math.PI / 180);
        ctx.translate(-(rack.x + rack.w / 2), -(rack.y + rack.h / 2));
        
        ctx.fillStyle = rack.color || '#e74c3c';
        ctx.globalAlpha = 0.3;
        ctx.fillRect(rack.x, rack.y, rack.w, rack.h);
        ctx.globalAlpha = 1.0;
        
        ctx.strokeStyle = rack.color || '#e74c3c';
        ctx.lineWidth = 2;
        ctx.strokeRect(rack.x, rack.y, rack.w, rack.h);
        
        ctx.restore();
        
        // Draw rack label
        if (this.state.showLabels) {
            ctx.fillStyle = '#333';
            ctx.font = '14px Arial';
            ctx.fillText(rack.location_name, rack.x + 5, rack.y + 20);
        }
        
        // Draw bins
        if (rack.bins) {
            rack.bins.forEach(bin => {
                this.drawBin(bin);
            });
        }
    }
    
    /**
     * 📦 Draw a bin (storage location)
     */
    drawBin(bin) {
        const ctx = this.ctx;
        
        // Validate bin has required properties
        if (!bin || bin.x === undefined || bin.y === undefined || bin.w === undefined || bin.h === undefined) {
            return;
        }
        
        // Determine bin color (stock heatmap or default)
        let fillColor = bin.color || '#95a5a6';
        
        if (this.state.showHeatmap && bin.stock_intensity !== undefined) {
            fillColor = this.getHeatmapColor(bin.stock_intensity);
        }
        
        // Highlight if selected or highlighted
        if (this.state.selectedBin && this.state.selectedBin.id === bin.id) {
            fillColor = '#3498db';
        } else if (this.state.highlightedBins.includes(bin.location_id)) {
            fillColor = '#f39c12';
        }
        
        // Draw bin
        ctx.fillStyle = fillColor;
        ctx.globalAlpha = 0.7;
        ctx.fillRect(bin.x, bin.y, bin.w, bin.h);
        ctx.globalAlpha = 1.0;
        
        ctx.strokeStyle = '#7f8c8d';
        ctx.lineWidth = 1;
        ctx.strokeRect(bin.x, bin.y, bin.w, bin.h);
        
        // Draw bin label
        if (this.state.showLabels) {
            ctx.fillStyle = '#000';
            ctx.font = '11px Arial';
            ctx.fillText(bin.location_name || 'Unknown', bin.x + 3, bin.y + 12);
            
            // Show stock quantity if available
            if (bin.total_quantity) {
                ctx.fillStyle = '#e74c3c';
                ctx.font = 'bold 10px Arial';
                ctx.fillText(`${bin.total_quantity}`, bin.x + 3, bin.y + 24);
            }
        }
    }
    
    /**
     * 🔍 Get resize handle at position
     */
    getResizeHandle(bin, x, y) {
        const handleSize = 12;
        const handles = [
            { x: bin.x, y: bin.y, pos: 'nw' },
            { x: bin.x + bin.w/2, y: bin.y, pos: 'n' },
            { x: bin.x + bin.w, y: bin.y, pos: 'ne' },
            { x: bin.x + bin.w, y: bin.y + bin.h/2, pos: 'e' },
            { x: bin.x + bin.w, y: bin.y + bin.h, pos: 'se' },
            { x: bin.x + bin.w/2, y: bin.y + bin.h, pos: 's' },
            { x: bin.x, y: bin.y + bin.h, pos: 'sw' },
            { x: bin.x, y: bin.y + bin.h/2, pos: 'w' },
        ];
        
        for (const handle of handles) {
            if (Math.abs(x - handle.x) < handleSize && Math.abs(y - handle.y) < handleSize) {
                return handle.pos;
            }
        }
        return null;
    }
    
    /**
     * 🖱️ Get cursor style for resize handle
     */
    getResizeCursor(handle) {
        const cursors = {
            'nw': 'nw-resize', 'n': 'n-resize', 'ne': 'ne-resize',
            'e': 'e-resize', 'se': 'se-resize', 's': 's-resize',
            'sw': 'sw-resize', 'w': 'w-resize'
        };
        return cursors[handle] || 'default';
    }
    
    /**
     * 📏 Resize bin based on handle drag
     */
    resizeBin(bin, x, y, handle) {
        const minSize = 40;
        
        switch(handle) {
            case 'nw':
                bin.w = Math.max(minSize, bin.w + (bin.x - x));
                bin.h = Math.max(minSize, bin.h + (bin.y - y));
                bin.x = x;
                bin.y = y;
                break;
            case 'n':
                bin.h = Math.max(minSize, bin.h + (bin.y - y));
                bin.y = y;
                break;
            case 'ne':
                bin.w = Math.max(minSize, x - bin.x);
                bin.h = Math.max(minSize, bin.h + (bin.y - y));
                bin.y = y;
                break;
            case 'e':
                bin.w = Math.max(minSize, x - bin.x);
                break;
            case 'se':
                bin.w = Math.max(minSize, x - bin.x);
                bin.h = Math.max(minSize, y - bin.y);
                break;
            case 's':
                bin.h = Math.max(minSize, y - bin.y);
                break;
            case 'sw':
                bin.w = Math.max(minSize, bin.w + (bin.x - x));
                bin.h = Math.max(minSize, y - bin.y);
                bin.x = x;
                break;
            case 'w':
                bin.w = Math.max(minSize, bin.w + (bin.x - x));
                bin.x = x;
                break;
        }
        
        // Snap to grid
        if (this.state.snapToGrid) {
            bin.x = Math.round(bin.x / this.state.gridSize) * this.state.gridSize;
            bin.y = Math.round(bin.y / this.state.gridSize) * this.state.gridSize;
            bin.w = Math.round(bin.w / this.state.gridSize) * this.state.gridSize;
            bin.h = Math.round(bin.h / this.state.gridSize) * this.state.gridSize;
        }
        
        this.render2DMap();
    }
    
    /**
     * 📋 Show context menu for adding rack/bin
     */
    showContextMenu(x, y, screenX, screenY) {
        // Will be implemented with action service to open dialog
        this.notification.add(
            'Right-click menu: Add Rack/Bin at (' + Math.round(x) + ', ' + Math.round(y) + ')',
            { type: 'info' }
        );
    }
    
    /**
     * ➕ Add new rack to warehouse
     */
    async addRack(x, y) {
        try {
            const result = await this.action.doAction({
                type: 'ir.actions.act_window',
                name: 'Add Rack',
                res_model: 'stock.location.layout',
                view_mode: 'form',
                views: [[false, 'form']],
                target: 'new',
                context: {
                    default_warehouse_id: this.state.warehouseId,
                    default_location_type: 'rack',
                    default_x: Math.round(x),
                    default_y: Math.round(y),
                    default_width: 200,
                    default_height: 100,
                }
            });
            
            if (result) {
                await this.loadWarehouseLayout();
            }
        } catch (error) {
            console.error('Failed to add rack:', error);
        }
    }
    
    /**
     * ➕ Add new bin to warehouse
     */
    async addBin(x, y) {
        try {
            const result = await this.action.doAction({
                type: 'ir.actions.act_window',
                name: 'Add Bin',
                res_model: 'stock.location.layout',
                view_mode: 'form',
                views: [[false, 'form']],
                target: 'new',
                context: {
                    default_warehouse_id: this.state.warehouseId,
                    default_location_type: 'bin',
                    default_x: Math.round(x),
                    default_y: Math.round(y),
                    default_width: 80,
                    default_height: 60,
                }
            });
            
            if (result) {
                await this.loadWarehouseLayout();
            }
        } catch (error) {
            console.error('Failed to add bin:', error);
        }
    }
    
    /**
     * ✏️ Update bin position (drag & drop in edit mode)
     */
    updateBinPosition(bin, x, y) {
        bin.x = x;
        bin.y = y;
        
        // Snap to grid
        if (this.state.snapToGrid) {
            bin.x = Math.round(bin.x / this.state.gridSize) * this.state.gridSize;
            bin.y = Math.round(bin.y / this.state.gridSize) * this.state.gridSize;
        }
        
        this.render2DMap();
    }
    
    /**
     * 💾 Save bin position to server
     */
    async saveBinPosition(bin) {
        try {
            await this.rpc('/warehouse_map/update_layout', {
                layout_id: bin.id,
                x: bin.x,
                y: bin.y,
                width: bin.w,
                height: bin.h,
            });
            
            this.notification.add('Layout updated', { type: 'success' });
        } catch (error) {
            console.error('Failed to save layout:', error);
            this.notification.add('Failed to save layout', { type: 'danger' });
        }
    }
    
    /**
     * 🎨 Get heatmap color based on intensity
     */
    getHeatmapColor(intensity) {
        // Green (low) -> Yellow -> Red (high)
        if (intensity < 0.5) {
            const r = Math.floor(intensity * 2 * 255);
            return `rgb(${r}, 255, 0)`;
        } else {
            const g = Math.floor((1 - intensity) * 2 * 255);
            return `rgb(255, ${g}, 0)`;
        }
    }
    
    /**
     * 🖱️ Setup event handlers for interaction
     */
    setupEventHandlers() {
        if (!this.canvas) return;
        
        // Click handler - select bin
        this.canvas.addEventListener('click', (e) => {
            const rect = this.canvas.getBoundingClientRect();
            const x = (e.clientX - rect.left - this.state.panX) / this.state.zoom;
            const y = (e.clientY - rect.top - this.state.panY) / this.state.zoom;
            
            this.handleCanvasClick(x, y);
        });
        
        // Right-click context menu for edit mode
        this.canvas.addEventListener('contextmenu', (e) => {
            if (!this.state.editMode) return;
            e.preventDefault();
            
            const rect = this.canvas.getBoundingClientRect();
            const x = (e.clientX - rect.left - this.state.panX) / this.state.zoom;
            const y = (e.clientY - rect.top - this.state.panY) / this.state.zoom;
            
            this.showContextMenu(x, y, e.clientX, e.clientY);
        });
        
        // Drag handler (for edit mode - move or resize)
        let isDragging = false;
        let dragTarget = null;
        let resizeHandle = null;
        
        this.canvas.addEventListener('mousedown', (e) => {
            if (!this.state.editMode) return;
            
            const rect = this.canvas.getBoundingClientRect();
            const x = (e.clientX - rect.left - this.state.panX) / this.state.zoom;
            const y = (e.clientY - rect.top - this.state.panY) / this.state.zoom;
            
            // Check if clicking resize handle
            if (this.state.selectedBin) {
                resizeHandle = this.getResizeHandle(this.state.selectedBin, x, y);
                if (resizeHandle) {
                    this.state.isResizing = true;
                    this.state.resizeHandle = resizeHandle;
                    this.state.dragStartX = x;
                    this.state.dragStartY = y;
                    return;
                }
            }
            
            // Otherwise try to drag bin
            dragTarget = this.findBinAt(x, y);
            if (dragTarget) {
                isDragging = true;
                this.state.dragStartX = x - dragTarget.x;
                this.state.dragStartY = y - dragTarget.y;
                this.canvas.style.cursor = 'grabbing';
            }
        });
        
        this.canvas.addEventListener('mousemove', (e) => {
            const rect = this.canvas.getBoundingClientRect();
            const x = (e.clientX - rect.left - this.state.panX) / this.state.zoom;
            const y = (e.clientY - rect.top - this.state.panY) / this.state.zoom;
            
            // Handle resize
            if (this.state.isResizing && this.state.selectedBin) {
                this.resizeBin(this.state.selectedBin, x, y, this.state.resizeHandle);
                return;
            }
            
            // Handle drag
            if (!isDragging || !dragTarget) {
                // Update cursor for resize handles
                if (this.state.editMode && this.state.selectedBin) {
                    const handle = this.getResizeHandle(this.state.selectedBin, x, y);
                    this.canvas.style.cursor = handle ? this.getResizeCursor(handle) : 'default';
                }
                return;
            }
            
            this.updateBinPosition(dragTarget, x - this.state.dragStartX, y - this.state.dragStartY);
        });
        
        this.canvas.addEventListener('mouseup', () => {
            if (this.state.isResizing && this.state.selectedBin) {
                this.saveBinPosition(this.state.selectedBin);
                this.state.isResizing = false;
                this.state.resizeHandle = null;
            }
            
            if (isDragging && dragTarget) {
                this.saveBinPosition(dragTarget);
            }
            
            isDragging = false;
            dragTarget = null;
            this.canvas.style.cursor = 'default';
        });
        
        // Zoom with mouse wheel
        this.canvas.addEventListener('wheel', (e) => {
            e.preventDefault();
            const delta = e.deltaY > 0 ? 0.9 : 1.1;
            this.state.zoom = Math.max(0.5, Math.min(3.0, this.state.zoom * delta));
            this.render2DMap();
        });
    }
    
    /**
     * 🖱️ Handle canvas click - select bin and show details
     */
    async handleCanvasClick(x, y) {
        const bin = this.findBinAt(x, y);
        
        if (bin) {
            this.state.selectedBin = bin;
            this.render2DMap();
            
            // Load bin details
            await this.showBinDetails(bin.location_id);
        }
    }
    
    /**
     * 🔍 Find bin at coordinates
     */
    findBinAt(x, y) {
        if (!this.state.layoutData?.zones) return null;
        
        for (const zone of this.state.layoutData.zones) {
            if (zone.racks) {
                for (const rack of zone.racks) {
                    if (rack.bins) {
                        for (const bin of rack.bins) {
                            if (x >= bin.x && x <= bin.x + bin.w &&
                                y >= bin.y && y <= bin.y + bin.h) {
                                return bin;
                            }
                        }
                    }
                }
            }
        }
        return null;
    }
    
    /**
     * 📦 Show bin details popup
     * Khi click bin → show danh sách lot/serial
     */
    async showBinDetails(locationId) {
        try {
            const data = await this.rpc('/warehouse_map/bin_details/' + locationId);
            
            // Show notification with bin info
            let message = `📦 ${data.location_complete_name}\n`;
            message += `Total Qty: ${data.total_quantity}\n`;
            message += `Lots/Serials: ${data.lot_count}\n\n`;
            
            if (data.quants && data.quants.length > 0) {
                message += 'Items:\n';
                data.quants.slice(0, 5).forEach(q => {
                    message += `• ${q.product_name}`;
                    if (q.lot_name) {
                        message += ` [${q.lot_name}]`;
                    }
                    message += `: ${q.quantity} ${q.uom}\n`;
                });
                
                if (data.quants.length > 5) {
                    message += `... and ${data.quants.length - 5} more`;
                }
            }
            
            this.notification.add(message, { 
                type: 'info',
                sticky: true,
            });
            
        } catch (error) {
            console.error('Failed to load bin details:', error);
        }
    }
    
    /**
     * 🔦 Highlight bin by serial number (barcode scan)
     * Scan Serial → Find lot_id → Find location → Highlight bin
     */
    async highlightBySerial(serialNumber) {
        try {
            const result = await this.rpc('/warehouse_map/scan_serial', {
                serial_number: serialNumber
            });
            
            if (result.error) {
                this.notification.add(result.error, { type: 'warning' });
                return;
            }
            
            // Highlight bins containing this serial
            this.state.highlightedBins = result.bins.map(b => b.location_id);
            this.render2DMap();
            
            // Show notification
            let message = `🔦 Found: ${result.product_name}\n`;
            message += `Serial: ${result.lot_name}\n`;
            message += `Locations:\n`;
            result.bins.forEach(bin => {
                message += `• ${bin.location_name}: ${bin.quantity} units\n`;
            });
            
            this.notification.add(message, {
                type: 'success',
                sticky: true,
            });
            
        } catch (error) {
            console.error('Failed to scan serial:', error);
            this.notification.add('Failed to scan serial number', { type: 'danger' });
        }
    }
    
    /**
     * 🔄 Toggle features
     */
    toggleEditMode() {
        this.state.editMode = !this.state.editMode;
        const canvas = this.canvasRef.el;
        if (canvas) {
            canvas.style.cursor = this.state.editMode ? 'move' : 'default';
        }
    }
    
    toggleHeatmap() {
        this.state.showHeatmap = !this.state.showHeatmap;
        this.render2DMap();
    }
    
    toggleLabels() {
        this.state.showLabels = !this.state.showLabels;
        this.render2DMap();
    }
    
    resetView() {
        this.state.zoom = 1.0;
        this.state.panX = 0;
        this.state.panY = 0;
        this.render2DMap();
    }
}

WarehouseMap2D.template = "hdi_warehouse_map.WarehouseMap2D";
WarehouseMap2D.props = {
    warehouseId: { type: Number, optional: true },
};

registry.category("actions").add("warehouse_map_2d", WarehouseMap2D);
