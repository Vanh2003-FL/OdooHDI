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

export class WarehouseMap2D extends Component {
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.action = useService("action");
        
        this.canvasRef = useRef("mapCanvas");
        this.state = useState({
            warehouseId: this.props.warehouseId || 1,
            layoutData: null,
            selectedBin: null,
            highlightedBins: [],
            editMode: false,
            showHeatmap: false,
            showLabels: true,
            zoom: 1.0,
            panX: 0,
            panY: 0,
        });
        
        onMounted(() => {
            this.initializeCanvas();
            this.loadWarehouseLayout();
            this.setupEventHandlers();
        });
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
            const data = await this.env.services.rpc('/warehouse_map/layout/' + warehouseId);
            this.state.layoutData = data;
            this.render2DMap();
        } catch (error) {
            console.error('Failed to load warehouse layout:', error);
            this.notification.add('Failed to load warehouse layout', { type: 'danger' });
        }
    }
    
    /**
     * 🎨 Render 2D warehouse map
     */
    render2DMap() {
        if (!this.ctx || !this.state.layoutData) return;
        
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
        
        // Draw zones
        if (this.state.layoutData.zones) {
            this.state.layoutData.zones.forEach(zone => {
                this.drawZone(zone);
            });
        }
        
        // Restore context
        ctx.restore();
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
     * 📍 Draw a bin (storage location)
     */
    drawBin(bin) {
        const ctx = this.ctx;
        
        // Check if bin is highlighted
        const isHighlighted = this.state.highlightedBins.includes(bin.location_id);
        const isSelected = this.state.selectedBin?.location_id === bin.location_id;
        
        // Determine color based on stock quantity (heatmap)
        let fillColor = bin.color || '#f39c12';
        if (this.state.showHeatmap && bin.stock_qty > 0) {
            const intensity = Math.min(bin.stock_qty / 100, 1.0);
            fillColor = this.getHeatmapColor(intensity);
        }
        
        // Draw bin
        ctx.fillStyle = fillColor;
        ctx.globalAlpha = isSelected ? 0.9 : (isHighlighted ? 0.7 : 0.5);
        ctx.fillRect(bin.x, bin.y, bin.w, bin.h);
        ctx.globalAlpha = 1.0;
        
        // Draw border
        ctx.strokeStyle = isSelected ? '#000' : (isHighlighted ? '#ff0' : '#666');
        ctx.lineWidth = isSelected ? 3 : (isHighlighted ? 2 : 1);
        ctx.strokeRect(bin.x, bin.y, bin.w, bin.h);
        
        // Draw bin label
        if (this.state.showLabels) {
            ctx.fillStyle = '#fff';
            ctx.font = 'bold 12px Arial';
            ctx.textAlign = 'center';
            ctx.fillText(bin.location_name, bin.x + bin.w / 2, bin.y + bin.h / 2);
            
            // Show stock quantity
            if (bin.stock_qty > 0) {
                ctx.font = '10px Arial';
                ctx.fillText(`Qty: ${bin.stock_qty}`, bin.x + bin.w / 2, bin.y + bin.h / 2 + 15);
            }
            
            // Show lot count
            if (bin.lot_count > 0) {
                ctx.fillText(`Lots: ${bin.lot_count}`, bin.x + bin.w / 2, bin.y + bin.h / 2 + 28);
            }
        }
    }
    
    /**
     * 🌡️ Get heatmap color based on intensity (0-1)
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
        
        // Drag handler (for edit mode)
        let isDragging = false;
        let dragTarget = null;
        
        this.canvas.addEventListener('mousedown', (e) => {
            if (!this.state.editMode) return;
            
            const rect = this.canvas.getBoundingClientRect();
            const x = (e.clientX - rect.left - this.state.panX) / this.state.zoom;
            const y = (e.clientY - rect.top - this.state.panY) / this.state.zoom;
            
            dragTarget = this.findBinAt(x, y);
            if (dragTarget) {
                isDragging = true;
                this.canvas.style.cursor = 'grabbing';
            }
        });
        
        this.canvas.addEventListener('mousemove', (e) => {
            if (!isDragging || !dragTarget) return;
            
            const rect = this.canvas.getBoundingClientRect();
            const x = (e.clientX - rect.left - this.state.panX) / this.state.zoom;
            const y = (e.clientY - rect.top - this.state.panY) / this.state.zoom;
            
            this.updateBinPosition(dragTarget, x, y);
        });
        
        this.canvas.addEventListener('mouseup', () => {
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
            const data = await this.env.services.rpc('/warehouse_map/bin_details/' + locationId);
            
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
            const result = await this.env.services.rpc('/warehouse_map/scan_serial', {
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
     * ✏️ Update bin position (drag & drop in edit mode)
     */
    updateBinPosition(bin, x, y) {
        bin.x = x - bin.w / 2;
        bin.y = y - bin.h / 2;
        this.render2DMap();
    }
    
    /**
     * 💾 Save bin position to server
     */
    async saveBinPosition(bin) {
        try {
            await this.env.services.rpc('/warehouse_map/update_layout', {
                layout_id: bin.id,
                x: bin.x,
                y: bin.y
            });
            
            this.notification.add('Bin position saved', { type: 'success' });
        } catch (error) {
            console.error('Failed to save bin position:', error);
            this.notification.add('Failed to save position', { type: 'danger' });
        }
    }
    
    /**
     * 🔄 Toggle features
     */
    toggleEditMode() {
        this.state.editMode = !this.state.editMode;
        this.canvas.style.cursor = this.state.editMode ? 'move' : 'default';
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
