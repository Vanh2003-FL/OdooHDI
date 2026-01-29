/** @odoo-module **/

import { Component, useState, onMounted, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * Warehouse 2D Viewer using SVG
 * 
 * Features:
 * - Top-down 2D map of warehouse layout
 * - SVG rendering of bins, racks, aisles
 * - Drag-and-drop bin repositioning
 * - Color-coded bins by status/heatmap
 * - Pan and zoom with mouse/touch
 * - Click to select and edit bins
 */
export class Warehouse2DViewer extends Component {
    static template = "hdi_warehouse_3d.Warehouse2DViewerTemplate";
    static props = {
        layoutId: { type: Number },
        editable: { type: Boolean, optional: true },
        showHeatmap: { type: Boolean, optional: true },
    };

    setup() {
        this.rpc = useService("rpc");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            error: null,
            layoutData: null,
            selectedBin: null,
            showHeatmap: this.props.showHeatmap || false,
            scale: 1.0,
            panX: 0,
            panY: 0,
        });

        this.svgRef = useRef("svgContainer");
        this.bins = new Map(); // bin_id -> SVG element
        this.isDragging = false;
        this.draggedBin = null;
        this.lastMousePos = { x: 0, y: 0 };

        onMounted(async () => {
            await this.loadLayoutData();
            this.renderMap();
            this.setupEventHandlers();
        });
    }

    /**
     * Load warehouse layout data
     */
    async loadLayoutData() {
        try {
            this.state.loading = true;
            const data = await this.rpc(`/warehouse_3d/layout/${this.props.layoutId}`, {});
            this.state.layoutData = data;
            
            if (this.state.showHeatmap) {
                const heatmapData = await this.rpc(`/warehouse_3d/heatmap/${this.props.layoutId}`, {});
                this.state.heatmapData = heatmapData;
            }
            
            this.state.loading = false;
        } catch (error) {
            console.error('Failed to load layout data:', error);
            this.state.error = error.message;
            this.state.loading = false;
        }
    }

    /**
     * Render 2D SVG map
     */
    renderMap() {
        if (!this.state.layoutData || !this.svgRef.el) return;

        const svg = this.svgRef.el;
        const layout = this.state.layoutData;

        // Set SVG viewBox
        const padding = 5;
        svg.setAttribute('viewBox', 
            `${-padding} ${-padding} ${layout.width + padding * 2} ${layout.depth + padding * 2}`
        );

        // Clear existing content
        while (svg.firstChild) {
            svg.removeChild(svg.firstChild);
        }

        // Create background
        const background = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        background.setAttribute('x', '0');
        background.setAttribute('y', '0');
        background.setAttribute('width', layout.width);
        background.setAttribute('height', layout.depth);
        background.setAttribute('fill', '#f5f5f5');
        background.setAttribute('stroke', '#ddd');
        background.setAttribute('stroke-width', '0.1');
        svg.appendChild(background);

        // Render grid
        this.renderGrid(svg, layout);

        // Render zones (optional - as background areas)
        if (layout.zones) {
            layout.zones.forEach(zone => this.renderZone(svg, zone));
        }

        // Render aisles (as paths/corridors)
        if (layout.aisles) {
            layout.aisles.forEach(aisle => this.renderAisle(svg, aisle));
        }

        // Render bins
        layout.bins.forEach(binData => {
            this.renderBin(svg, binData);
        });

        // Apply heatmap if enabled
        if (this.state.showHeatmap && this.state.heatmapData) {
            this.applyHeatmap();
        }
    }

    /**
     * Render grid lines
     */
    renderGrid(svg, layout) {
        const gridGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        gridGroup.setAttribute('class', 'grid');
        gridGroup.setAttribute('opacity', '0.3');

        const gridSize = 1; // 1 meter grid
        const numVertical = Math.ceil(layout.width / gridSize);
        const numHorizontal = Math.ceil(layout.depth / gridSize);

        // Vertical lines
        for (let i = 0; i <= numVertical; i++) {
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', i * gridSize);
            line.setAttribute('y1', '0');
            line.setAttribute('x2', i * gridSize);
            line.setAttribute('y2', layout.depth);
            line.setAttribute('stroke', '#ccc');
            line.setAttribute('stroke-width', '0.05');
            gridGroup.appendChild(line);
        }

        // Horizontal lines
        for (let i = 0; i <= numHorizontal; i++) {
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', '0');
            line.setAttribute('y1', i * gridSize);
            line.setAttribute('x2', layout.width);
            line.setAttribute('y2', i * gridSize);
            line.setAttribute('stroke', '#ccc');
            line.setAttribute('stroke-width', '0.05');
            gridGroup.appendChild(line);
        }

        svg.appendChild(gridGroup);
    }

    /**
     * Render zone as colored area
     */
    renderZone(svg, zone) {
        const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        rect.setAttribute('x', zone.position_x || 0);
        rect.setAttribute('y', zone.position_z || 0);
        rect.setAttribute('width', zone.width || 10);
        rect.setAttribute('height', zone.depth || 10);
        rect.setAttribute('fill', zone.color || '#e3f2fd');
        rect.setAttribute('opacity', '0.3');
        rect.setAttribute('stroke', '#1976d2');
        rect.setAttribute('stroke-width', '0.1');
        rect.setAttribute('class', 'zone');
        svg.appendChild(rect);

        // Zone label
        const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text.setAttribute('x', (zone.position_x || 0) + (zone.width || 10) / 2);
        text.setAttribute('y', (zone.position_z || 0) + 1);
        text.setAttribute('text-anchor', 'middle');
        text.setAttribute('font-size', '0.8');
        text.setAttribute('fill', '#666');
        text.textContent = zone.name;
        svg.appendChild(text);
    }

    /**
     * Render aisle as corridor/path
     */
    renderAisle(svg, aisle) {
        const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        rect.setAttribute('x', aisle.position_x || 0);
        rect.setAttribute('y', aisle.position_z || 0);
        rect.setAttribute('width', aisle.width || 2);
        rect.setAttribute('height', aisle.length || 10);
        rect.setAttribute('fill', '#fff');
        rect.setAttribute('stroke', '#999');
        rect.setAttribute('stroke-width', '0.05');
        rect.setAttribute('class', 'aisle');
        svg.appendChild(rect);
    }

    /**
     * Render bin as rectangle
     */
    renderBin(svg, binData) {
        const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        group.setAttribute('class', 'bin');
        group.setAttribute('data-bin-id', binData.id);

        // Bin rectangle
        const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        rect.setAttribute('x', binData.position_x || 0);
        rect.setAttribute('y', binData.position_z || 0);
        rect.setAttribute('width', binData.width || 1.0);
        rect.setAttribute('height', binData.depth || 1.0);
        
        // Color by status
        let fill = '#4CAF50'; // green - empty
        if (binData.bin_status === 'partial') {
            fill = '#FFC107'; // yellow
        } else if (binData.bin_status === 'full') {
            fill = '#F44336'; // red
        }
        rect.setAttribute('fill', fill);
        rect.setAttribute('stroke', '#333');
        rect.setAttribute('stroke-width', '0.05');
        rect.setAttribute('opacity', '0.8');
        
        if (this.props.editable) {
            rect.style.cursor = 'move';
        }
        
        group.appendChild(rect);

        // Bin label
        const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text.setAttribute('x', (binData.position_x || 0) + (binData.width || 1.0) / 2);
        text.setAttribute('y', (binData.position_z || 0) + (binData.depth || 1.0) / 2);
        text.setAttribute('text-anchor', 'middle');
        text.setAttribute('dominant-baseline', 'middle');
        text.setAttribute('font-size', '0.4');
        text.setAttribute('fill', '#fff');
        text.setAttribute('pointer-events', 'none');
        text.textContent = binData.name;
        group.appendChild(text);

        // Store bin data
        group.binData = binData;
        group.rect = rect;
        
        svg.appendChild(group);
        this.bins.set(binData.id, group);
    }

    /**
     * Apply heatmap colors to bins
     */
    applyHeatmap() {
        if (!this.state.heatmapData || !this.state.heatmapData.heatmap_data) return;

        const maxPicks = this.state.heatmapData.max_picks || 1;
        
        Object.entries(this.state.heatmapData.heatmap_data).forEach(([binId, picks]) => {
            const binGroup = this.bins.get(parseInt(binId));
            if (!binGroup) return;

            const intensity = picks / maxPicks;
            
            // Color gradient
            let color;
            if (intensity < 0.25) {
                color = '#2196F3'; // blue
            } else if (intensity < 0.5) {
                color = '#4CAF50'; // green
            } else if (intensity < 0.75) {
                color = '#FFC107'; // yellow
            } else {
                color = '#F44336'; // red
            }

            binGroup.rect.setAttribute('fill', color);
        });
    }

    /**
     * Setup event handlers for drag, zoom, pan
     */
    setupEventHandlers() {
        const svg = this.svgRef.el;
        if (!svg) return;

        // Click to select bin
        svg.addEventListener('click', (e) => {
            const binGroup = e.target.closest('.bin');
            if (binGroup && binGroup.binData) {
                this.selectBin(binGroup.binData);
            }
        });

        if (this.props.editable) {
            // Drag-and-drop for bin repositioning
            svg.addEventListener('mousedown', this.onMouseDown.bind(this));
            svg.addEventListener('mousemove', this.onMouseMove.bind(this));
            svg.addEventListener('mouseup', this.onMouseUp.bind(this));
            svg.addEventListener('mouseleave', this.onMouseUp.bind(this));
        }

        // Zoom with mouse wheel
        svg.addEventListener('wheel', this.onWheel.bind(this));
    }

    /**
     * Select bin and show details
     */
    selectBin(binData) {
        // Deselect previous
        this.bins.forEach(group => {
            group.rect.setAttribute('stroke-width', '0.05');
        });

        // Highlight selected
        const binGroup = this.bins.get(binData.id);
        if (binGroup) {
            binGroup.rect.setAttribute('stroke-width', '0.2');
            binGroup.rect.setAttribute('stroke', '#2196F3');
        }

        this.state.selectedBin = binData;
        this.notification.add(`Selected: ${binData.name}`, { type: 'info' });
    }

    /**
     * Mouse down - start dragging
     */
    onMouseDown(e) {
        if (!this.props.editable) return;

        const binGroup = e.target.closest('.bin');
        if (binGroup) {
            this.isDragging = true;
            this.draggedBin = binGroup;
            this.lastMousePos = this.getSVGCoordinates(e);
            binGroup.rect.setAttribute('opacity', '0.5');
        }
    }

    /**
     * Mouse move - drag bin
     */
    onMouseMove(e) {
        if (!this.isDragging || !this.draggedBin) return;

        const currentPos = this.getSVGCoordinates(e);
        const dx = currentPos.x - this.lastMousePos.x;
        const dy = currentPos.y - this.lastMousePos.y;

        // Update bin position
        const rect = this.draggedBin.rect;
        const currentX = parseFloat(rect.getAttribute('x'));
        const currentY = parseFloat(rect.getAttribute('y'));
        
        rect.setAttribute('x', currentX + dx);
        rect.setAttribute('y', currentY + dy);

        // Update label position
        const text = this.draggedBin.querySelector('text');
        if (text) {
            const textX = parseFloat(text.getAttribute('x'));
            const textY = parseFloat(text.getAttribute('y'));
            text.setAttribute('x', textX + dx);
            text.setAttribute('y', textY + dy);
        }

        this.lastMousePos = currentPos;
    }

    /**
     * Mouse up - finish dragging
     */
    async onMouseUp(e) {
        if (!this.isDragging || !this.draggedBin) return;

        this.isDragging = false;
        this.draggedBin.rect.setAttribute('opacity', '0.8');

        // Save new position to backend
        const rect = this.draggedBin.rect;
        const newX = parseFloat(rect.getAttribute('x'));
        const newY = parseFloat(rect.getAttribute('y'));
        const binData = this.draggedBin.binData;

        try {
            await this.rpc('/web/dataset/call_kw', {
                model: 'warehouse.bin',
                method: 'write',
                args: [[binData.id], {
                    position_x: newX,
                    position_z: newY,
                }],
                kwargs: {},
            });
            this.notification.add(`Bin ${binData.name} moved successfully`, { type: 'success' });
        } catch (error) {
            console.error('Failed to update bin position:', error);
            this.notification.add('Failed to save bin position', { type: 'danger' });
            // Revert position
            this.renderMap();
        }

        this.draggedBin = null;
    }

    /**
     * Mouse wheel - zoom
     */
    onWheel(e) {
        e.preventDefault();
        const delta = e.deltaY > 0 ? 0.9 : 1.1;
        this.state.scale *= delta;
        this.state.scale = Math.max(0.1, Math.min(10, this.state.scale));
        
        // Apply zoom transform
        const svg = this.svgRef.el;
        svg.style.transform = `scale(${this.state.scale})`;
    }

    /**
     * Get SVG coordinates from mouse event
     */
    getSVGCoordinates(event) {
        const svg = this.svgRef.el;
        const pt = svg.createSVGPoint();
        pt.x = event.clientX;
        pt.y = event.clientY;
        const transformed = pt.matrixTransform(svg.getScreenCTM().inverse());
        return { x: transformed.x, y: transformed.y };
    }

    /**
     * Toggle heatmap
     */
    toggleHeatmap() {
        this.state.showHeatmap = !this.state.showHeatmap;
        if (this.state.showHeatmap) {
            this.loadLayoutData();
        } else {
            this.renderMap();
        }
    }
}
