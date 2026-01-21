// Warehouse 3D Visualization - Simple Canvas-based
// Dependencies: None (Pure JavaScript)

class Warehouse3DViewer {
    constructor(container_id, data) {
        this.container = document.getElementById(container_id);
        this.data = data;
        this.canvas = null;
        this.ctx = null;
        this.zoom = 1;
        this.offsetX = 0;
        this.offsetY = 0;
        this.selectedLocation = null;
        
        this.init();
    }

    init() {
        // Create canvas
        this.canvas = document.createElement('canvas');
        this.canvas.id = 'warehouse-3d-canvas';
        this.canvas.width = this.container.clientWidth - 20;
        this.canvas.height = this.container.clientHeight - 20;
        this.canvas.style.border = '1px solid #ccc';
        this.canvas.style.cursor = 'move';
        this.canvas.style.backgroundColor = '#f5f5f5';
        
        this.container.appendChild(this.canvas);
        this.ctx = this.canvas.getContext('2d');
        
        // Event listeners
        this.canvas.addEventListener('wheel', (e) => this.handleZoom(e));
        this.canvas.addEventListener('mousemove', (e) => this.handleMouseMove(e));
        this.canvas.addEventListener('click', (e) => this.handleClick(e));
        
        this.offsetX = this.canvas.width / 2;
        this.offsetY = this.canvas.height / 2;
        
        this.render();
    }

    render() {
        // Clear canvas
        this.ctx.fillStyle = '#ffffff';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Draw grid
        this.drawGrid();
        
        // Draw locations
        this.drawLocations();
        
        // Draw batches
        this.drawBatches();
        
        // Draw legend
        this.drawLegend();
    }

    drawGrid() {
        const warehouse = this.data.warehouse;
        const gridSize = 20;
        const scale = this.zoom * 10;
        
        this.ctx.strokeStyle = '#e0e0e0';
        this.ctx.lineWidth = 1;
        
        // Vertical lines
        for (let x = 0; x <= warehouse.max_x; x++) {
            const px = this.offsetX + x * scale;
            this.ctx.beginPath();
            this.ctx.moveTo(px, this.offsetY);
            this.ctx.lineTo(px, this.offsetY + warehouse.max_y * scale);
            this.ctx.stroke();
        }
        
        // Horizontal lines
        for (let y = 0; y <= warehouse.max_y; y++) {
            const py = this.offsetY + y * scale;
            this.ctx.beginPath();
            this.ctx.moveTo(this.offsetX, py);
            this.ctx.lineTo(this.offsetX + warehouse.max_x * scale, py);
            this.ctx.stroke();
        }
        
        // Draw axis labels
        this.ctx.fillStyle = '#666';
        this.ctx.font = '12px Arial';
        for (let x = 0; x <= warehouse.max_x; x += 5) {
            const px = this.offsetX + x * scale;
            this.ctx.fillText(x, px - 5, this.offsetY - 5);
        }
        for (let y = 0; y <= warehouse.max_y; y += 5) {
            const py = this.offsetY + y * scale;
            this.ctx.fillText(y, this.offsetX - 20, py + 5);
        }
    }

    drawLocations() {
        const scale = this.zoom * 10;
        const boxSize = Math.max(15, 20 * this.zoom);
        
        this.data.locations.forEach(loc => {
            const x = this.offsetX + loc.x * scale;
            const y = this.offsetY + loc.y * scale;
            
            // Convert hex color
            const color = loc.color || '#4CAF50';
            
            // Draw box
            this.ctx.fillStyle = color;
            this.ctx.globalAlpha = 0.7;
            this.ctx.fillRect(x - boxSize/2, y - boxSize/2, boxSize, boxSize);
            this.ctx.globalAlpha = 1;
            
            // Draw border
            this.ctx.strokeStyle = '#333';
            this.ctx.lineWidth = 2;
            if (this.selectedLocation === loc.id) {
                this.ctx.strokeStyle = '#FF5733';
                this.ctx.lineWidth = 3;
            }
            this.ctx.strokeRect(x - boxSize/2, y - boxSize/2, boxSize, boxSize);
            
            // Draw Z level indicator
            if (loc.z > 0) {
                this.ctx.fillStyle = '#333';
                this.ctx.font = 'bold 10px Arial';
                this.ctx.textAlign = 'center';
                this.ctx.fillText(`Z${loc.z}`, x, y + 3);
            }
            
            // Store location rect for click detection
            if (!loc.rect) {
                loc.rect = {
                    x: x - boxSize/2,
                    y: y - boxSize/2,
                    w: boxSize,
                    h: boxSize
                };
            }
        });
    }

    drawBatches() {
        const scale = this.zoom * 10;
        const circleRadius = Math.max(8, 12 * this.zoom);
        
        this.data.batches.forEach(batch => {
            const x = this.offsetX + batch.x * scale;
            const y = this.offsetY + batch.y * scale;
            
            // Draw circle
            this.ctx.fillStyle = batch.color || '#FF9800';
            this.ctx.globalAlpha = 0.6;
            this.ctx.beginPath();
            this.ctx.arc(x, y, circleRadius, 0, Math.PI * 2);
            this.ctx.fill();
            this.ctx.globalAlpha = 1;
            
            // Draw border
            this.ctx.strokeStyle = '#E65100';
            this.ctx.lineWidth = 1;
            this.ctx.stroke();
        });
    }

    drawLegend() {
        const legendX = this.canvas.width - 200;
        const legendY = 20;
        
        this.ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
        this.ctx.fillRect(legendX - 10, legendY - 10, 200, 120);
        
        this.ctx.strokeStyle = '#999';
        this.ctx.lineWidth = 1;
        this.ctx.strokeRect(legendX - 10, legendY - 10, 200, 120);
        
        this.ctx.fillStyle = '#333';
        this.ctx.font = 'bold 12px Arial';
        this.ctx.fillText('Legend', legendX, legendY + 10);
        
        // Location box
        this.ctx.fillStyle = '#4CAF50';
        this.ctx.fillRect(legendX, legendY + 20, 15, 15);
        this.ctx.fillStyle = '#333';
        this.ctx.font = '11px Arial';
        this.ctx.fillText('Location', legendX + 20, legendY + 32);
        
        // Batch circle
        this.ctx.fillStyle = '#FF9800';
        this.ctx.beginPath();
        this.ctx.arc(legendX + 7, legendY + 55, 7, 0, Math.PI * 2);
        this.ctx.fill();
        this.ctx.fillStyle = '#333';
        this.ctx.fillText('Batch', legendX + 20, legendY + 60);
        
        // Info
        this.ctx.font = '10px Arial';
        this.ctx.fillStyle = '#666';
        this.ctx.fillText(`Zoom: ${(this.zoom * 100).toFixed(0)}%`, legendX, legendY + 95);
    }

    handleZoom(e) {
        e.preventDefault();
        const delta = e.deltaY > 0 ? 0.9 : 1.1;
        this.zoom *= delta;
        this.zoom = Math.max(0.5, Math.min(3, this.zoom));
        this.render();
    }

    handleMouseMove(e) {
        if (e.buttons === 1) {
            this.offsetX += e.movementX;
            this.offsetY += e.movementY;
            this.render();
        }
    }

    handleClick(e) {
        const rect = this.canvas.getBoundingClientRect();
        const clickX = e.clientX - rect.left;
        const clickY = e.clientY - rect.top;
        
        // Check if clicked on location
        this.data.locations.forEach(loc => {
            if (loc.rect && 
                clickX >= loc.rect.x && clickX <= loc.rect.x + loc.rect.w &&
                clickY >= loc.rect.y && clickY <= loc.rect.y + loc.rect.h) {
                this.selectedLocation = loc.id;
                this.showLocationDetails(loc);
                this.render();
            }
        });
    }

    showLocationDetails(location) {
        const infoBox = document.getElementById('location-info');
        if (infoBox) {
            infoBox.innerHTML = `
                <h4>${location.location_name}</h4>
                <p><strong>Tọa độ:</strong> (${location.x}, ${location.y}, ${location.z})</p>
                <p><strong>Dung lượng sử dụng:</strong> ${location.capacity_pct.toFixed(1)}%</p>
                <p><strong>Lô hàng:</strong> ${location.batch_count}</p>
                <p><strong>Có thể đặt hàng:</strong> ${location.is_putable ? 'Có' : 'Không'}</p>
                <p><strong>Dung lượng sẵn:</strong> ${location.available_volume.toFixed(2)} m³</p>
            `;
        }
    }

    reset() {
        this.zoom = 1;
        this.offsetX = this.canvas.width / 2;
        this.offsetY = this.canvas.height / 2;
        this.selectedLocation = null;
        this.render();
    }
}

// Export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Warehouse3DViewer;
}
