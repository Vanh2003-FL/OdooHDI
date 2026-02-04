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
        this.notification = useService("notification");
        this.action = useService("action");
        this.rpc = rpc;
        
        // Try to get user service if available
        try {
            this.user = useService("user");
        } catch (e) {
            // Fallback if user service not available
            this.user = null;
        }
        
        this.canvasRef = useRef("mapCanvas");
        this.state = useState({
            warehouseId: null,  // Will be set in onMounted
            layoutData: null,
            selectedBin: null,
            selectedBinLocationId: null,  // For opening details form
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
        
        // Track current notification to avoid stacking
        this.currentNotification = null;
        
        onMounted(() => {
            this.initializeCanvas();
            // Ensure canvas is ready before loading data
            setTimeout(() => {
                this.initializeWarehouse();
                this.setupEventHandlers();
            }, 200);
        });
    }
    
    /**
     * 🏭 Initialize warehouse ID (from props, context, or default)
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
        
        // Default to warehouse 1 (or get first available)
        try {
            const warehouses = await this.orm.search('stock.warehouse', [], { limit: 1 });
            this.state.warehouseId = (warehouses && warehouses.length > 0) ? warehouses[0] : 1;
            this.loadWarehouseLayout();
        } catch (error) {
            console.error('Failed to get warehouse:', error);
            this.state.warehouseId = 1;
            this.loadWarehouseLayout();
        }
    }
    
    /**
     * 🔔 Helper: Close previous notification
     */
    closeAllNotifications() {
        this.currentNotification = null;
    }
    
    /**
     * 🔔 Show notification (close previous, show new immediately)
     */
    showNotification(message, options = {}) {
        // Close previous notification if exists
        if (this.currentNotification) {
            try {
                this.currentNotification.close?.();
            } catch (e) {
                // Ignore errors
            }
        }
        
        this.currentNotification = this.notification.add(message, options);
        
        // Auto close after 3.5 seconds
        setTimeout(() => {
            try {
                this.currentNotification?.close?.();
            } catch (e) {
                // Ignore errors
            }
            this.currentNotification = null;
        }, 3500);
        
        return this.currentNotification;
    }
    
    /**
     * 🎨 Initialize canvas for 2D rendering
     */
    initializeCanvas() {
        // Try different ways to find canvas
        let canvas = this.canvasRef?.el;
        console.log('[Canvas] Method 1 - useRef el:', !!canvas);
        
        if (!canvas) {
            // Try querySelector
            canvas = document.querySelector('canvas.warehouse-map-canvas');
            console.log('[Canvas] Method 2 - querySelector:', !!canvas);
        }
        
        if (!canvas) {
            // Try finding by tag within container
            const container = this.$el || document.querySelector('.o_warehouse_map_2d_container');
            if (container) {
                canvas = container.querySelector('canvas');
                console.log('[Canvas] Method 3 - querySelector in container:', !!canvas);
            }
        }
        
        if (!canvas) {
            console.error('[Canvas] Canvas element not found, creating offscreen canvas...');
            // Create offscreen canvas as fallback
            canvas = document.createElement('canvas');
            canvas.className = 'warehouse-map-canvas';
            canvas.style.width = '100%';
            canvas.style.height = '600px';
            canvas.style.display = 'block';
            canvas.style.border = '1px solid #ddd';
            canvas.style.backgroundColor = '#f9f9f9';
            
            // Try to append to container
            const container = document.querySelector('.o_warehouse_map_2d_container');
            if (container) {
                // Insert at beginning
                container.insertBefore(canvas, container.firstChild);
                console.log('[Canvas] Created and inserted fallback canvas');
            } else {
                console.error('[Canvas] Could not find container to append fallback canvas');
                // Try again later
                setTimeout(() => this.initializeCanvas(), 100);
                return;
            }
        }
        
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        
        // Set canvas size - fallback to 1000 if parent width is 0
        const parentWidth = canvas.parentElement?.clientWidth || 0;
        const finalWidth = parentWidth > 0 ? parentWidth : 1000;
        
        canvas.width = finalWidth;
        canvas.height = 600;
        
        // Also set CSS size to match
        canvas.style.width = '100%';
        canvas.style.height = '600px';
        canvas.style.display = 'block';
        canvas.style.border = '1px solid #ddd';
        canvas.style.backgroundColor = '#f9f9f9';
        
        console.log('[Canvas] Initialized:', { width: canvas.width, height: canvas.height, parentWidth, ctx: !!this.ctx });
        
        // Enable smooth rendering
        if (this.ctx) {
            this.ctx.imageSmoothingEnabled = true;
        }
    }
    
    /**
     * 📡 Load warehouse layout from server
     */
    async loadWarehouseLayout() {
        const warehouseId = this.props.warehouseId || 1;
        this.state.warehouseId = warehouseId;
        console.log('[Layout] Loading warehouse layout for warehouse:', warehouseId);
        
        try {
            const data = await this.rpc('/warehouse_map/layout/' + warehouseId);
            console.log('[Layout] Received data:', data);
            
            if (!data || !data.zones || data.zones.length === 0) {
                console.warn('[Layout] No zones in data');
                this.showNotification('No warehouse layout configured', { type: 'warning' });
                this.state.layoutData = { zones: [] };
                this.render2DMap();
                return;
            }
            
            console.log('[Layout] Found zones:', data.zones.length);
            this.state.layoutData = data;
            this.render2DMap();
        } catch (error) {
            console.error('[Layout] Failed to load warehouse layout:', error);
            this.showNotification('Failed to load warehouse layout: ' + error.message, { type: 'danger' });
        }
    }
    
    /**
     * 🎨 Render 2D warehouse map
     */
    render2DMap() {
        console.log('[Render] render2DMap called, ctx:', !!this.ctx, 'data zones:', this.state.layoutData?.zones?.length || 0);
        if (!this.ctx) {
            console.warn('[Render] Canvas context not ready, retrying...');
            // Retry if context not yet ready
            setTimeout(() => this.render2DMap(), 50);
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
        
        // Draw grid always visible - even with no data
        this.drawGrid();
        console.log('[Render] Grid drawn');
        
        // Draw zones if data exists
        if (this.state.layoutData && this.state.layoutData.zones && this.state.layoutData.zones.length > 0) {
            this.state.layoutData.zones.forEach(zone => {
                this.drawZone(zone);
            });
        }
        
        // Draw resize handles if selected
        if (this.state.editMode && this.state.selectedBin) {
            this.drawResizeHandles(this.state.selectedBin);
        }
        
        // Restore context
        ctx.restore();
        
        // Draw empty state message if no zones (after restore so text appears on top)
        if (!this.state.layoutData || !this.state.layoutData.zones || this.state.layoutData.zones.length === 0) {
            this.drawEmptyStateOverlay();
        }
    }
    
    /**
     * 📭 Draw empty state message as overlay
     */
    drawEmptyStateOverlay() {
        const ctx = this.ctx;
        ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
        ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        
        ctx.fillStyle = '#fff';
        ctx.font = 'bold 18px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('📭 No warehouse layout configured', this.canvas.width / 2, this.canvas.height / 2 - 20);
        
        ctx.font = '14px Arial';
        ctx.fillStyle = '#ddd';
        ctx.fillText('👉 Click "Edit Mode" button and right-click to add zones/racks/bins', this.canvas.width / 2, this.canvas.height / 2 + 20);
    }
    
    /**
     * 📐 Draw grid for snap-to-grid
     */
    drawGrid() {
        const ctx = this.ctx;
        if (!ctx) {
            console.error('[Grid] No context to draw grid');
            return;
        }
        
        const gridSize = this.state.gridSize;
        const width = this.canvas.width / this.state.zoom;
        const height = this.canvas.height / this.state.zoom;
        
        console.log('[Grid] Drawing grid:', { gridSize, width, height, zoom: this.state.zoom });
        
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
        
        console.log('[Grid] Grid drawn successfully');
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
        console.log('[Zone] Drawing zone:', zone.location_name, {x: zone.x, y: zone.y, w: zone.w, h: zone.h, racks: zone.racks?.length || 0});
        
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
            console.log('[Zone] Drawing', zone.racks.length, 'racks');
            zone.racks.forEach(rack => {
                this.drawRack(rack);
            });
        } else {
            console.warn('[Zone] Zone has NO racks');
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
        // Context menu - skip notification (not important enough to show)
        console.log('Right-click at:', { x: Math.round(x), y: Math.round(y) });
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
     * 📦 Update rack position and move all bins inside it
     */
    updateRackPosition(rack, x, y) {
        // Calculate delta movement
        const deltaX = x - rack.x;
        const deltaY = y - rack.y;
        
        // Update rack position
        rack.x = x;
        rack.y = y;
        
        // Snap to grid
        if (this.state.snapToGrid) {
            rack.x = Math.round(rack.x / this.state.gridSize) * this.state.gridSize;
            rack.y = Math.round(rack.y / this.state.gridSize) * this.state.gridSize;
        }
        
        // Recalculate delta after grid snap
        const actualDeltaX = rack.x - (x - deltaX);
        const actualDeltaY = rack.y - (y - deltaY);
        
        // Move all bins in this rack by same delta
        if (rack.bins) {
            rack.bins.forEach(bin => {
                bin.x += actualDeltaX;
                bin.y += actualDeltaY;
            });
        }
        
        this.render2DMap();
    }
    
    /**
     * 💾 Save bin position to server (silent, no notification)
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
            // Silent save - no notification
        } catch (error) {
            console.error('Failed to save layout:', error);
            // Silent error - no notification
        }
    }
    
    /**
     * 💾 Save rack position to server (and all its bins) - silent
     */
    async saveRackPosition(rack) {
        try {
            // Save rack position
            await this.rpc('/warehouse_map/update_layout', {
                layout_id: rack.id,
                x: rack.x,
                y: rack.y,
                width: rack.w,
                height: rack.h,
            });
            
            // Save all bins in this rack
            if (rack.bins) {
                for (const bin of rack.bins) {
                    await this.rpc('/warehouse_map/update_layout', {
                        layout_id: bin.id,
                        x: bin.x,
                        y: bin.y,
                        width: bin.w,
                        height: bin.h,
                    });
                }
            }
            
            // Silent save - no notification
        } catch (error) {
            console.error('Failed to save rack position:', error);
            // Silent error - no notification
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
        let dragTargetType = null; // 'bin' or 'rack'
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
            
            // Try to drag bin first
            dragTarget = this.findBinAt(x, y);
            if (dragTarget) {
                isDragging = true;
                dragTargetType = 'bin';
                this.state.dragStartX = x - dragTarget.x;
                this.state.dragStartY = y - dragTarget.y;
                this.canvas.style.cursor = 'grabbing';
                return;
            }
            
            // If no bin, try to drag rack
            dragTarget = this.findRackAt(x, y);
            if (dragTarget) {
                isDragging = true;
                dragTargetType = 'rack';
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
            
            if (dragTargetType === 'rack') {
                // Dragging rack - move rack and all its bins
                this.updateRackPosition(dragTarget, x - this.state.dragStartX, y - this.state.dragStartY);
            } else {
                // Dragging bin
                this.updateBinPosition(dragTarget, x - this.state.dragStartX, y - this.state.dragStartY);
            }
        });
        
        this.canvas.addEventListener('mouseup', () => {
            if (this.state.isResizing && this.state.selectedBin) {
                this.saveBinPosition(this.state.selectedBin);
                this.state.isResizing = false;
                this.state.resizeHandle = null;
            }
            
            if (isDragging && dragTarget) {
                if (dragTargetType === 'rack') {
                    this.saveRackPosition(dragTarget);
                } else {
                    this.saveBinPosition(dragTarget);
                }
            }
            
            isDragging = false;
            dragTarget = null;
            dragTargetType = null;
            this.canvas.style.cursor = 'default';
        });
        
        // Zoom with mouse wheel
        this.canvas.addEventListener('wheel', (e) => {
            e.preventDefault();
            const delta = e.deltaY > 0 ? 0.9 : 1.1;
            this.state.zoom = Math.max(0.5, Math.min(3.0, this.state.zoom * delta));
            this.render2DMap();
        });
        
        // Keyboard shortcut: D for Details
        document.addEventListener('keydown', (e) => {
            if ((e.key === 'd' || e.key === 'D') && this.state.selectedBinLocationId) {
                this.openBinDetailsForm();
            }
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
     * 📦 Find rack at coordinates
     * Detect when dragging on rack (but not on bin inside it)
     */
    findRackAt(x, y) {
        if (!this.state.layoutData?.zones) return null;
        
        for (const zone of this.state.layoutData.zones) {
            if (zone.racks) {
                for (const rack of zone.racks) {
                    // Check if click is on rack border area (not inside bins)
                    if (x >= rack.x && x <= rack.x + rack.w &&
                        y >= rack.y && y <= rack.y + rack.h) {
                        
                        // If there's a bin at this position, return null (bin takes priority)
                        if (rack.bins) {
                            for (const bin of rack.bins) {
                                if (x >= bin.x && x <= bin.x + bin.w &&
                                    y >= bin.y && y <= bin.y + bin.h) {
                                    return null; // Bin found, don't drag rack
                                }
                            }
                        }
                        
                        // No bin at this position, so it's rack area
                        return rack;
                    }
                }
            }
        }
        return null;
    }
    
    /**
     * 📦 Show bin details popup
     * Khi click bin → show thông tin đơn giản
     */
    async showBinDetails(locationId) {
        try {
            const data = await this.rpc('/warehouse_map/bin_details/' + locationId);
            
            // Save location ID for opening details form
            this.state.selectedBinLocationId = locationId;
            
            // Show simple notification with bin info only
            let message = `📦 ${data.location_complete_name}\n`;
            message += `Qty: ${data.total_quantity}\n`;
            message += `(Nhấn D để xem chi tiết)`;
            
            // Show notification (auto-dismiss after 3.5 seconds)
            this.showNotification(message, { 
                type: 'info',
            });
            
        } catch (error) {
            console.error('Failed to load bin details:', error);
        }
    }
    
    /**
     * 🔍 Open bin details form in Odoo
     */
    async openBinDetailsForm() {
        if (!this.state.selectedBinLocationId) {
            this.showNotification('Please select a bin first', { type: 'warning' });
            return;
        }
        
        try {
            await this.action.doAction({
                type: 'ir.actions.act_window',
                name: 'Bin Details',
                res_model: 'stock.location',
                res_id: this.state.selectedBinLocationId,
                view_mode: 'form',
                views: [[false, 'form']],
                target: 'new',
            });
        } catch (error) {
            console.error('Failed to open bin details form:', error);
            this.showNotification('Failed to open bin details', { type: 'danger' });
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
                this.showNotification(result.error, { type: 'warning' });
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
            
            this.showNotification(message, {
                type: 'success',
                sticky: true,
            });
            
        } catch (error) {
            console.error('Failed to scan serial:', error);
            this.showNotification('Failed to scan serial number', { type: 'danger' });
        }
    }
    
    /**
     * � Save layout changes to database
     */
    async saveLayout() {
        console.log('[Save] Saving layout changes...');
        
        if (!this.state.layoutData || !this.state.layoutData.zones) {
            this.showNotification('No layout data to save', { type: 'warning' });
            return;
        }
        
        try {
            // Collect all zone/rack/bin changes
            const changes = [];
            const processed = new Set();
            
            const collectChanges = (container) => {
                if (container.zones) {
                    container.zones.forEach(zone => {
                        if (!processed.has(zone.id)) {
                            changes.push({
                                id: zone.id,
                                x: zone.x,
                                y: zone.y,
                                w: zone.w,
                                h: zone.h,
                            });
                            processed.add(zone.id);
                        }
                        
                        if (zone.racks) {
                            zone.racks.forEach(rack => {
                                if (!processed.has(rack.id)) {
                                    changes.push({
                                        id: rack.id,
                                        x: rack.x,
                                        y: rack.y,
                                        w: rack.w,
                                        h: rack.h,
                                        rotation: rack.rotation || 0,
                                    });
                                    processed.add(rack.id);
                                }
                                
                                if (rack.bins) {
                                    rack.bins.forEach(bin => {
                                        if (!processed.has(bin.id)) {
                                            changes.push({
                                                id: bin.id,
                                                x: bin.x,
                                                y: bin.y,
                                                w: bin.w,
                                                h: bin.h,
                                                capacity: bin.capacity,
                                                stage: bin.stage,
                                            });
                                            processed.add(bin.id);
                                        }
                                    });
                                }
                            });
                        }
                    });
                }
            };
            
            collectChanges(this.state.layoutData);
            
            // Send batch update to server
            const result = await this.rpc('/warehouse_map/batch_update_layout', {
                warehouse_id: this.state.warehouseId,
                changes: changes,
            });
            
            if (result.success) {
                this.showNotification(`✅ Saved ${changes.length} layout changes`, {
                    type: 'success',
                });
                console.log('[Save] Layout saved successfully:', result);
            } else {
                this.showNotification('Failed to save layout', { type: 'danger' });
            }
        } catch (error) {
            console.error('[Save] Error saving layout:', error);
            this.showNotification('Error saving layout: ' + error.message, { type: 'danger' });
        }
    }
    
    /**
     * �🔄 Toggle features
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
