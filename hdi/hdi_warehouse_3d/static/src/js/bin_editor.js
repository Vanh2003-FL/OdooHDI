/** @odoo-module **/

import { Component, useState, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * Bin Editor Component
 * Interactive tool for creating, moving, and editing bins in 2D map
 */
export class BinEditor extends Component {
    static template = "hdi_warehouse_3d.BinEditor";
    static props = {
        layoutId: { type: Number },
        onClose: { type: Function, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.rpc = useService("rpc");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        
        this.svgRef = useRef("editorSvg");
        
        this.state = useState({
            loading: true,
            mode: 'select', // 'select', 'create', 'move', 'delete'
            layoutData: null,
            selectedBin: null,
            bins: new Map(),
            gridSize: 1.0,
            snapToGrid: true,
            showGrid: true,
        });

        this.creatingBin = null;
        this.movingBin = null;
        this.startPos = null;
    }

    async loadLayout() {
        try {
            this.state.loading = true;
            const data = await this.rpc(`/warehouse_3d/layout/${this.props.layoutId}`, {});
            this.state.layoutData = data;
            this.renderEditor();
            this.state.loading = false;
        } catch (error) {
            console.error('Failed to load layout:', error);
            this.state.loading = false;
        }
    }

    renderEditor() {
        if (!this.state.layoutData || !this.svgRef.el) return;

        const svg = this.svgRef.el;
        const layout = this.state.layoutData;

        // Set viewBox
        svg.setAttribute('viewBox', `0 0 ${layout.width} ${layout.depth}`);

        // Clear
        while (svg.firstChild) {
            svg.removeChild(svg.firstChild);
        }

        // Background
        const bg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        bg.setAttribute('width', layout.width);
        bg.setAttribute('height', layout.depth);
        bg.setAttribute('fill', '#fafafa');
        svg.appendChild(bg);

        // Grid
        if (this.state.showGrid) {
            this.renderGrid(svg, layout);
        }

        // Bins
        layout.bins.forEach(bin => this.renderBin(svg, bin));
    }

    renderGrid(svg, layout) {
        const grid = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        grid.setAttribute('class', 'grid');
        grid.setAttribute('opacity', '0.3');

        for (let x = 0; x <= layout.width; x += this.state.gridSize) {
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', x);
            line.setAttribute('y1', '0');
            line.setAttribute('x2', x);
            line.setAttribute('y2', layout.depth);
            line.setAttribute('stroke', '#ccc');
            line.setAttribute('stroke-width', '0.05');
            grid.appendChild(line);
        }

        for (let y = 0; y <= layout.depth; y += this.state.gridSize) {
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', '0');
            line.setAttribute('y1', y);
            line.setAttribute('x2', layout.width);
            line.setAttribute('y2', y);
            line.setAttribute('stroke', '#ccc');
            line.setAttribute('stroke-width', '0.05');
            grid.appendChild(line);
        }

        svg.appendChild(grid);
    }

    renderBin(svg, binData) {
        const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        group.setAttribute('class', 'bin editable');
        group.setAttribute('data-bin-id', binData.id);

        const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        rect.setAttribute('x', binData.position_x || 0);
        rect.setAttribute('y', binData.position_z || 0);
        rect.setAttribute('width', binData.width || 1.0);
        rect.setAttribute('height', binData.depth || 1.0);
        rect.setAttribute('fill', '#4CAF50');
        rect.setAttribute('stroke', '#333');
        rect.setAttribute('stroke-width', '0.1');
        rect.setAttribute('opacity', '0.8');
        rect.style.cursor = 'pointer';
        
        group.appendChild(rect);

        // Label
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

        group.binData = binData;
        group.rect = rect;
        
        svg.appendChild(group);
        this.state.bins.set(binData.id, group);
    }

    setMode(mode) {
        this.state.mode = mode;
        
        // Update cursor
        const svg = this.svgRef.el;
        if (!svg) return;

        if (mode === 'create') {
            svg.style.cursor = 'crosshair';
        } else if (mode === 'delete') {
            svg.style.cursor = 'not-allowed';
        } else {
            svg.style.cursor = 'default';
        }
    }

    onSvgClick(event) {
        const pos = this.getSVGCoordinates(event);

        if (this.state.mode === 'create') {
            this.createBinAt(pos);
        } else if (this.state.mode === 'delete') {
            const bin = event.target.closest('.bin');
            if (bin) {
                this.deleteBin(bin.binData.id);
            }
        } else if (this.state.mode === 'select') {
            const bin = event.target.closest('.bin');
            if (bin) {
                this.selectBin(bin.binData);
            }
        }
    }

    async createBinAt(pos) {
        if (this.state.snapToGrid) {
            pos.x = Math.round(pos.x / this.state.gridSize) * this.state.gridSize;
            pos.y = Math.round(pos.y / this.state.gridSize) * this.state.gridSize;
        }

        try {
            // Create location first
            const location = await this.orm.create('stock.location', [{
                name: `New Bin ${Date.now()}`,
                usage: 'internal',
                warehouse_id: this.state.layoutData.warehouse_id,
            }]);

            // Create bin
            const bin = await this.orm.create('warehouse.bin', [{
                name: `BIN-${Date.now()}`,
                location_id: location[0],
                position_x: pos.x,
                position_y: 0,
                position_z: pos.y,
                width: 1.0,
                height: 2.0,
                depth: 1.0,
            }]);

            this.notification.add('Bin created successfully', { type: 'success' });
            await this.loadLayout();
        } catch (error) {
            console.error('Failed to create bin:', error);
            this.notification.add('Failed to create bin', { type: 'danger' });
        }
    }

    async deleteBin(binId) {
        const result = await this.dialog.confirm({
            title: 'Delete Bin',
            body: 'Are you sure you want to delete this bin?',
        });

        if (!result) return;

        try {
            await this.orm.unlink('warehouse.bin', [binId]);
            this.notification.add('Bin deleted successfully', { type: 'success' });
            await this.loadLayout();
        } catch (error) {
            console.error('Failed to delete bin:', error);
            this.notification.add('Failed to delete bin', { type: 'danger' });
        }
    }

    selectBin(binData) {
        // Deselect all
        this.state.bins.forEach(group => {
            group.rect.setAttribute('stroke-width', '0.1');
            group.rect.setAttribute('stroke', '#333');
        });

        // Select
        const group = this.state.bins.get(binData.id);
        if (group) {
            group.rect.setAttribute('stroke-width', '0.3');
            group.rect.setAttribute('stroke', '#2196F3');
        }

        this.state.selectedBin = binData;
    }

    async updateBinProperties(properties) {
        if (!this.state.selectedBin) return;

        try {
            await this.orm.write('warehouse.bin', [this.state.selectedBin.id], properties);
            this.notification.add('Bin updated successfully', { type: 'success' });
            await this.loadLayout();
        } catch (error) {
            console.error('Failed to update bin:', error);
            this.notification.add('Failed to update bin', { type: 'danger' });
        }
    }

    toggleGrid() {
        this.state.showGrid = !this.state.showGrid;
        this.renderEditor();
    }

    toggleSnapToGrid() {
        this.state.snapToGrid = !this.state.snapToGrid;
    }

    getSVGCoordinates(event) {
        const svg = this.svgRef.el;
        const pt = svg.createSVGPoint();
        pt.x = event.clientX;
        pt.y = event.clientY;
        const transformed = pt.matrixTransform(svg.getScreenCTM().inverse());
        return { x: transformed.x, y: transformed.y };
    }

    close() {
        if (this.props.onClose) {
            this.props.onClose();
        }
    }
}
