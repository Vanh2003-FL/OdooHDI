/** @odoo-module **/
/**
 * 🎮 HDI Warehouse Map 3D Renderer
 * ================================
 * 3D warehouse visualization (Visual only - NO business logic)
 * Uses basic CSS 3D transforms for rendering
 */

import { registry } from "@web/core/registry";
import { Component, useState, onMounted, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class WarehouseMap3D extends Component {
    setup() {
        this.orm = useService("orm");
        this.rpc = useService("rpc");
        this.notification = useService("notification");
        
        this.containerRef = useRef("map3dContainer");
        this.state = useState({
            warehouseId: null,
            layoutData: null,
            selectedBin: null,
            highlightedBins: [],
            rotationX: 45,
            rotationY: 45,
            zoom: 1.0,
        });
        
        onMounted(() => {
            this.loadWarehouseLayout();
            this.setupControls();
        });
    }
    
    /**
     * 📡 Load warehouse layout from server
     */
    async loadWarehouseLayout() {
        const warehouseId = this.props.warehouseId || 1;
        this.state.warehouseId = warehouseId;
        
        try {
            const data = await this.rpc('/warehouse_map/layout/' + warehouseId);
            this.state.layoutData = data;
            this.render3DMap();
        } catch (error) {
            console.error('Failed to load warehouse layout:', error);
            this.notification.add('Failed to load warehouse layout', { type: 'danger' });
        }
    }
    
    /**
     * 🎨 Render 3D warehouse view
     * ⚠️ 3D KHÔNG LÀM NGHIỆP VỤ - Chỉ visual và highlight
     */
    render3DMap() {
        const container = this.containerRef.el;
        if (!container || !this.state.layoutData) return;
        
        // Clear existing content
        container.innerHTML = '';
        
        // Create 3D scene container
        const scene = document.createElement('div');
        scene.className = 'warehouse-3d-scene';
        scene.style.cssText = `
            width: 100%;
            height: 100%;
            perspective: 1200px;
            perspective-origin: 50% 50%;
            position: relative;
            background: linear-gradient(to bottom, #2c3e50 0%, #34495e 100%);
        `;
        
        // Create warehouse world
        const world = document.createElement('div');
        world.className = 'warehouse-3d-world';
        world.style.cssText = `
            width: 100%;
            height: 100%;
            position: absolute;
            transform-style: preserve-3d;
            transform: rotateX(${this.state.rotationX}deg) rotateY(${this.state.rotationY}deg) scale(${this.state.zoom});
            transition: transform 0.3s ease;
        `;
        
        // Draw floor
        this.create3DFloor(world);
        
        // Draw zones and structures
        if (this.state.layoutData.zones) {
            this.state.layoutData.zones.forEach(zone => {
                this.create3DZone(world, zone);
            });
        }
        
        scene.appendChild(world);
        container.appendChild(scene);
        
        // Store reference for updates
        this.scene3D = scene;
        this.world3D = world;
    }
    
    /**
     * 🏢 Create 3D floor plane
     */
    create3DFloor(parent) {
        const floor = document.createElement('div');
        floor.className = 'warehouse-floor';
        floor.style.cssText = `
            position: absolute;
            width: 1400px;
            height: 500px;
            background: 
                repeating-linear-gradient(
                    0deg,
                    #34495e 0px,
                    #34495e 1px,
                    transparent 1px,
                    transparent 50px
                ),
                repeating-linear-gradient(
                    90deg,
                    #34495e 0px,
                    #34495e 1px,
                    transparent 1px,
                    transparent 50px
                );
            transform: rotateX(90deg) translateZ(-50px);
            transform-style: preserve-3d;
        `;
        parent.appendChild(floor);
    }
    
    /**
     * 🏗️ Create 3D zone structure
     */
    create3DZone(parent, zone) {
        const zoneEl = document.createElement('div');
        zoneEl.className = 'warehouse-zone-3d';
        zoneEl.dataset.zoneId = zone.location_id;
        
        // Zone base
        const zoneBase = this.create3DBox({
            x: zone.x,
            y: zone.y,
            z: 0,
            width: zone.w,
            depth: zone.h,
            height: 20,
            color: zone.color || '#3498db',
            opacity: 0.2,
            label: zone.location_name,
        });
        
        zoneEl.appendChild(zoneBase);
        
        // Draw racks
        if (zone.racks) {
            zone.racks.forEach(rack => {
                const rackEl = this.create3DRack(rack);
                zoneEl.appendChild(rackEl);
            });
        }
        
        parent.appendChild(zoneEl);
    }
    
    /**
     * 📦 Create 3D rack with bins
     */
    create3DRack(rack) {
        const rackEl = document.createElement('div');
        rackEl.className = 'warehouse-rack-3d';
        rackEl.dataset.rackId = rack.location_id;
        
        // Rack structure (frame)
        const rackFrame = this.create3DBox({
            x: rack.x,
            y: rack.y,
            z: rack.z || 0,
            width: rack.w,
            depth: rack.h,
            height: 150,
            color: rack.color || '#e74c3c',
            opacity: 0.3,
            label: rack.location_name,
            wireframe: true,
        });
        
        rackEl.appendChild(rackFrame);
        
        // Draw bins
        if (rack.bins) {
            rack.bins.forEach(bin => {
                const binEl = this.create3DBin(bin);
                rackEl.appendChild(binEl);
            });
        }
        
        return rackEl;
    }
    
    /**
     * 📍 Create 3D bin (storage location)
     * 🔦 Can be highlighted when scanned
     */
    create3DBin(bin) {
        const isHighlighted = this.state.highlightedBins.includes(bin.location_id);
        const isSelected = this.state.selectedBin?.location_id === bin.location_id;
        
        // Calculate color intensity based on stock
        let color = bin.color || '#f39c12';
        let opacity = 0.6;
        
        if (bin.stock_qty > 0) {
            opacity = 0.8;
        }
        
        if (isHighlighted) {
            color = '#ffff00';  // Yellow highlight
            opacity = 0.9;
        }
        
        if (isSelected) {
            color = '#00ff00';  // Green selection
            opacity = 1.0;
        }
        
        const binEl = this.create3DBox({
            x: bin.x,
            y: bin.y,
            z: (bin.z || 1) * 50,  // Convert Z level to height
            width: bin.w,
            depth: bin.h,
            height: 80,
            color: color,
            opacity: opacity,
            label: bin.location_name,
            stockQty: bin.stock_qty,
            lotCount: bin.lot_count,
        });
        
        binEl.dataset.binId = bin.location_id;
        binEl.dataset.binLayoutId = bin.id;
        binEl.style.cursor = 'pointer';
        
        // Click handler - show bin details
        binEl.addEventListener('click', () => {
            this.handleBinClick(bin);
        });
        
        return binEl;
    }
    
    /**
     * 📦 Create 3D box primitive
     */
    create3DBox(options) {
        const {
            x, y, z = 0,
            width, depth, height,
            color, opacity = 0.7,
            label = '',
            stockQty = 0,
            lotCount = 0,
            wireframe = false,
        } = options;
        
        const box = document.createElement('div');
        box.className = 'box-3d';
        box.style.cssText = `
            position: absolute;
            width: ${width}px;
            height: ${height}px;
            transform-style: preserve-3d;
            transform: translate3d(${x}px, ${y}px, ${z}px);
        `;
        
        // Create 6 faces
        const faces = [
            { name: 'front', transform: `rotateY(0deg) translateZ(${depth/2}px)` },
            { name: 'back', transform: `rotateY(180deg) translateZ(${depth/2}px)` },
            { name: 'right', transform: `rotateY(90deg) translateZ(${width/2}px)` },
            { name: 'left', transform: `rotateY(-90deg) translateZ(${width/2}px)` },
            { name: 'top', transform: `rotateX(90deg) translateZ(${height/2}px)` },
            { name: 'bottom', transform: `rotateX(-90deg) translateZ(${height/2}px)` },
        ];
        
        faces.forEach(face => {
            const faceEl = document.createElement('div');
            faceEl.className = `box-face box-face-${face.name}`;
            faceEl.style.cssText = `
                position: absolute;
                width: ${face.name === 'right' || face.name === 'left' ? depth : width}px;
                height: ${face.name === 'top' || face.name === 'bottom' ? depth : height}px;
                background: ${wireframe ? 'transparent' : color};
                border: ${wireframe ? '2px solid ' + color : '1px solid rgba(0,0,0,0.2)'};
                opacity: ${opacity};
                transform: ${face.transform};
                transform-style: preserve-3d;
                backface-visibility: hidden;
            `;
            
            // Add label on front face
            if (face.name === 'front' && label) {
                const labelEl = document.createElement('div');
                labelEl.className = 'box-label';
                labelEl.textContent = label;
                labelEl.style.cssText = `
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    color: white;
                    font-weight: bold;
                    font-size: 12px;
                    text-align: center;
                    text-shadow: 1px 1px 2px rgba(0,0,0,0.8);
                    pointer-events: none;
                `;
                faceEl.appendChild(labelEl);
                
                // Show stock info
                if (stockQty > 0) {
                    const stockEl = document.createElement('div');
                    stockEl.textContent = `Qty: ${stockQty}`;
                    if (lotCount > 0) {
                        stockEl.textContent += ` | Lots: ${lotCount}`;
                    }
                    stockEl.style.cssText = `
                        position: absolute;
                        top: 65%;
                        left: 50%;
                        transform: translate(-50%, -50%);
                        color: #fff;
                        font-size: 10px;
                        text-shadow: 1px 1px 2px rgba(0,0,0,0.8);
                        pointer-events: none;
                    `;
                    faceEl.appendChild(stockEl);
                }
            }
            
            box.appendChild(faceEl);
        });
        
        return box;
    }
    
    /**
     * 🖱️ Handle bin click in 3D view
     * Click bin → open bin detail (NO nghiệp vụ)
     */
    async handleBinClick(bin) {
        this.state.selectedBin = bin;
        this.render3DMap();
        
        // Show bin details
        try {
            const data = await this.rpc('/warehouse_map/bin_details/' + bin.location_id);
            
            let message = `📦 ${data.location_complete_name}\n`;
            message += `Total Qty: ${data.total_quantity}\n`;
            message += `Lots/Serials: ${data.lot_count}`;
            
            this.notification.add(message, {
                type: 'info',
                sticky: true,
            });
        } catch (error) {
            console.error('Failed to load bin details:', error);
        }
    }
    
    /**
     * 🔦 Highlight bins by serial scan
     * Scan Serial → Find location → Highlight bin trên 3D
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
            
            // Highlight bins
            this.state.highlightedBins = result.bins.map(b => b.location_id);
            this.render3DMap();
            
            // Show notification
            this.notification.add(
                `🔦 Found: ${result.product_name}\nSerial: ${result.lot_name}`,
                { type: 'success', sticky: true }
            );
            
        } catch (error) {
            console.error('Failed to scan serial:', error);
        }
    }
    
    /**
     * 🎮 Setup 3D controls (rotation, zoom)
     */
    setupControls() {
        const container = this.containerRef.el;
        if (!container) return;
        
        let isDragging = false;
        let lastX = 0;
        let lastY = 0;
        
        container.addEventListener('mousedown', (e) => {
            isDragging = true;
            lastX = e.clientX;
            lastY = e.clientY;
            container.style.cursor = 'grabbing';
        });
        
        container.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            
            const deltaX = e.clientX - lastX;
            const deltaY = e.clientY - lastY;
            
            this.state.rotationY += deltaX * 0.5;
            this.state.rotationX -= deltaY * 0.5;
            
            // Clamp rotation
            this.state.rotationX = Math.max(-90, Math.min(90, this.state.rotationX));
            
            lastX = e.clientX;
            lastY = e.clientY;
            
            this.updateTransform();
        });
        
        container.addEventListener('mouseup', () => {
            isDragging = false;
            container.style.cursor = 'grab';
        });
        
        container.addEventListener('mouseleave', () => {
            isDragging = false;
            container.style.cursor = 'default';
        });
        
        // Zoom with mouse wheel
        container.addEventListener('wheel', (e) => {
            e.preventDefault();
            const delta = e.deltaY > 0 ? 0.9 : 1.1;
            this.state.zoom = Math.max(0.3, Math.min(2.0, this.state.zoom * delta));
            this.updateTransform();
        });
        
        container.style.cursor = 'grab';
    }
    
    /**
     * 🔄 Update 3D transform
     */
    updateTransform() {
        if (this.world3D) {
            this.world3D.style.transform = `
                rotateX(${this.state.rotationX}deg) 
                rotateY(${this.state.rotationY}deg) 
                scale(${this.state.zoom})
            `;
        }
    }
    
    /**
     * 🔄 Reset view
     */
    resetView() {
        this.state.rotationX = 45;
        this.state.rotationY = 45;
        this.state.zoom = 1.0;
        this.updateTransform();
    }
}

WarehouseMap3D.template = "hdi_warehouse_map.WarehouseMap3D";
WarehouseMap3D.props = {
    warehouseId: { type: Number, optional: true },
};

registry.category("actions").add("warehouse_map_3d", WarehouseMap3D);
