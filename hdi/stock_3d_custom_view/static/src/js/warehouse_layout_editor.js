import { Component, onWillStart, onMounted, useState, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/xml";

export class WarehouseLayoutEditor extends Component {
    static template = "stock_3d_custom_view.warehouse_layout_editor_main";

    setup() {
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        
        // Get warehouse ID from action - try multiple locations
        let warehouseId = null;
        let companyId = null;
        
        // Priority order for finding warehouse_id:
        // 1. props.action.context.active_id (Odoo converts warehouse_id to active_id)
        // 2. props.warehouse_id (direct property)
        // 3. props.action.warehouse_id (nested in action)
        // 4. props.action.context.warehouse_id (nested in context)
        if (this.props.action?.context?.active_id) {
            warehouseId = this.props.action.context.active_id;
        } else if (this.props.warehouse_id) {
            warehouseId = this.props.warehouse_id;
            companyId = this.props.company_id;
        } else if (this.props.action?.warehouse_id) {
            warehouseId = this.props.action.warehouse_id;
            companyId = this.props.action.company_id;
        } else if (this.props.action?.context?.warehouse_id) {
            warehouseId = this.props.action.context.warehouse_id;
            companyId = this.props.action.context.company_id;
        }
        
        console.log('WarehouseLayoutEditor - warehouse_id found:', warehouseId);
        
        if (!warehouseId) {
            console.error('warehouse_id not found in any location. Props:', this.props);
            this.notification.add(_t('Error: Warehouse ID not found'), { type: 'danger' });
        }
        
        this.state = useState({
            warehouseId: warehouseId,
            companyId: companyId,
            warehouseName: '',
            locations: [],
            products: [],
            is3DView: false,
            selectedLocation: null,
            canvasWidth: 1200,
            canvasHeight: 800,
        });

        this.canvasRef = useRef('canvas_2d_editor');
        this.canvas3DRef = useRef('canvas_3d_viewer');
        
        onWillStart(async () => {
            if (this.state.warehouseId) {
                await this.loadWarehouseData();
                await this.loadInventoryData();
            }
        });

        onMounted(() => {
            this.initCanvas2D();
            this.initCanvas3D();
            this.attachEventListeners();
        });
    }

    async loadWarehouseData() {
        // Load warehouse and its locations from database
        try {
            const warehouse = await this.orm.read(
                'stock.warehouse',
                [this.state.warehouseId],
                ['name', 'layout_width', 'layout_height', 'is_2d_configured']
            );
            
            if (warehouse.length) {
                const wh = warehouse[0];
                this.state.warehouseName = wh.name;
                this.state.canvasWidth = wh.layout_width || 1200;
                this.state.canvasHeight = wh.layout_height || 800;
            }

            const locations = await this.orm.searchRead(
                'stock.location',
                [['warehouse_id', '=', this.state.warehouseId], ['usage', '=', 'internal']],
                ['id', 'name', 'unique_code', 'length', 'width', 'height', 'pos_x', 'pos_y', 'pos_z', 'max_capacity']
            );
            
            this.state.locations = locations;
        } catch (error) {
            console.error('Error loading warehouse data:', error);
            this.notification.add(_t('Error loading warehouse data'), { type: 'danger' });
        }
    }

    async loadInventoryData() {
        // Load stock quantity and products
        try {
            const products = await this.orm.searchRead(
                'product.product',
                [['type', '=', 'product']],
                ['id', 'name', 'default_code', 'image_1920'],
                { limit: 100 }
            );
            
            this.state.products = products;
        } catch (error) {
            console.error('Error loading inventory data:', error);
        }
    }

    initCanvas2D() {
        // Initialize 2D canvas for layout editing
        const canvas = document.getElementById('canvas_2d_editor');
        if (!canvas) return;

        canvas.width = this.state.canvasWidth;
        canvas.height = this.state.canvasHeight;
        
        const ctx = canvas.getContext('2d');
        this.canvas2DContext = ctx;
        
        this.drawGridBackground(ctx);
        
        this.state.locations.forEach(location => {
            this.drawLocation(ctx, location);
        });

        canvas.addEventListener('click', (e) => this.onCanvasClick(e, canvas));
        canvas.addEventListener('mousemove', (e) => this.onCanvasMouseMove(e, canvas));
        canvas.addEventListener('mousedown', (e) => this.onCanvasMouseDown(e, canvas));
        canvas.addEventListener('mouseup', (e) => this.onCanvasMouseUp(e, canvas));
        
        this.canvas2D = canvas;
    }
    
    redrawCanvas2D() {
        // Redraw 2D canvas when data changes
        if (!this.canvas2D) return;
        
        const ctx = this.canvas2DContext;
        ctx.clearRect(0, 0, this.canvas2D.width, this.canvas2D.height);
        
        this.drawGridBackground(ctx);
        
        this.state.locations.forEach(location => {
            this.drawLocation(ctx, location);
        });
        
        if (this.state.selectedLocation) {
            this.highlightLocation(this.state.selectedLocation);
        }
    }

    drawGridBackground(ctx) {
        // Draw grid background on canvas
        const gridSize = 20;
        ctx.strokeStyle = '#e0e0e0';
        ctx.lineWidth = 0.5;

        for (let x = 0; x <= this.state.canvasWidth; x += gridSize) {
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, this.state.canvasHeight);
            ctx.stroke();
        }

        for (let y = 0; y <= this.state.canvasHeight; y += gridSize) {
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(this.state.canvasWidth, y);
            ctx.stroke();
        }
    }

    drawLocation(ctx, location) {
        // Draw a location (shelf/bin) on canvas
        const x = location.pos_x || 50;
        const y = location.pos_y || 50;
        const width = location.length * 30 || 60;
        const height = location.width * 30 || 40;

        ctx.fillStyle = '#667eea';
        ctx.fillRect(x, y, width, height);

        ctx.strokeStyle = '#333';
        ctx.lineWidth = 2;
        ctx.strokeRect(x, y, width, height);

        ctx.fillStyle = '#fff';
        ctx.font = 'bold 12px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(location.unique_code || location.name, x + width / 2, y + height / 2);
    }

    onCanvasClick(event, canvas) {
        // Handle canvas click
        const rect = canvas.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;

        const clickedLocation = this.getLocationAtPoint(x, y);
        if (clickedLocation) {
            this.state.selectedLocation = clickedLocation;
            this.highlightLocation(clickedLocation);
            this.showLocationProperties(clickedLocation);
        }
    }

    onCanvasMouseMove(event, canvas) {
        // Handle canvas mouse move
        const rect = canvas.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;

        const location = this.getLocationAtPoint(x, y);
        if (location) {
            canvas.style.cursor = 'pointer';
        } else {
            canvas.style.cursor = 'crosshair';
        }
    }

    onCanvasMouseDown(event, canvas) {
        // Handle canvas mouse down for dragging
        const rect = canvas.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;

        const location = this.getLocationAtPoint(x, y);
        if (location && event.button === 0) {
            this.state.selectedLocation = location;
            this.isDragging = true;
            this.dragOffsetX = x - (location.pos_x || 50);
            this.dragOffsetY = y - (location.pos_y || 50);
            this.highlightLocation(location);
        }
    }

    onCanvasMouseUp(event, canvas) {
        // Handle canvas mouse up - auto save
        if (this.isDragging && this.state.selectedLocation) {
            this.isDragging = false;
            this.saveLocationPosition(this.state.selectedLocation);
            this.refresh3DView();
        }
    }
    
    onCanvasDrag(event, canvas) {
        // Handle canvas drag - real-time position update
        if (!this.isDragging || !this.state.selectedLocation) return;
        
        const rect = canvas.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;
        
        this.state.selectedLocation.pos_x = Math.max(0, x - this.dragOffsetX);
        this.state.selectedLocation.pos_y = Math.max(0, y - this.dragOffsetY);
        
        this.redrawCanvas2D();
    }

    getLocationAtPoint(x, y) {
        // Get location at coordinates
        for (const location of this.state.locations) {
            const locX = location.pos_x || 50;
            const locY = location.pos_y || 50;
            const width = location.length * 30 || 60;
            const height = location.width * 30 || 40;

            if (x >= locX && x <= locX + width && y >= locY && y <= locY + height) {
                return location;
            }
        }
        return null;
    }

    highlightLocation(location) {
        // Highlight selected location on canvas
        const canvas = document.getElementById('canvas_2d_editor');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        this.drawGridBackground(ctx);

        this.state.locations.forEach(loc => {
            if (loc.id === location.id) {
                const x = loc.pos_x || 50;
                const y = loc.pos_y || 50;
                const width = loc.length * 30 || 60;
                const height = loc.width * 30 || 40;

                ctx.strokeStyle = '#ff6b6b';
                ctx.lineWidth = 3;
                ctx.strokeRect(x, y, width, height);
            } else {
                this.drawLocation(ctx, loc);
            }
        });
    }

    showLocationProperties(location) {
        // Show location properties in modal
        const modalHtml = `
            <div class="modal" role="dialog">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Location: ${location.unique_code}</h5>
                            <button type="button" class="close" data-dismiss="modal">
                                <span>&times;</span>
                            </button>
                        </div>
                        <div class="modal-body">
                            <form>
                                <div class="form-group">
                                    <label>Location Code</label>
                                    <input type="text" class="form-control" value="${location.unique_code || ''}" id="edit_location_code"/>
                                </div>
                                <div class="form-group">
                                    <label>X Position (px)</label>
                                    <input type="number" class="form-control" value="${location.pos_x || 0}" id="edit_pos_x"/>
                                </div>
                                <div class="form-group">
                                    <label>Y Position (px)</label>
                                    <input type="number" class="form-control" value="${location.pos_y || 0}" id="edit_pos_y"/>
                                </div>
                                <div class="form-group">
                                    <label>Length (M)</label>
                                    <input type="number" class="form-control" value="${location.length || 0}" step="0.1" id="edit_length"/>
                                </div>
                                <div class="form-group">
                                    <label>Width (M)</label>
                                    <input type="number" class="form-control" value="${location.width || 0}" step="0.1" id="edit_width"/>
                                </div>
                            </form>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-primary" id="btn_save_location_props">Save</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        console.log('Show modal for location:', location);
    }

    initCanvas3D() {
        // Initialize 3D canvas using Three.js
        const container = document.getElementById('canvas_3d_viewer');
        if (!container) return;

        const width = container.clientWidth;
        const height = container.clientHeight;

        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x667eea);

        this.camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000);
        this.camera.position.set(10, 8, 10);
        this.camera.lookAt(0, 0, 0);

        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(width, height);
        this.renderer.shadowMap.enabled = true;
        container.appendChild(this.renderer.domElement);

        const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
        this.scene.add(ambientLight);

        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight.position.set(10, 15, 10);
        directionalLight.castShadow = true;
        this.scene.add(directionalLight);

        const gridHelper = new THREE.GridHelper(20, 20);
        this.scene.add(gridHelper);

        this.state.locations.forEach(location => {
            this.add3DLocation(location);
        });

        if (typeof OrbitControls !== 'undefined') {
            this.controls = new OrbitControls(this.camera, this.renderer.domElement);
            this.controls.autoRotate = false;
            this.controls.enableDamping = true;
            this.controls.dampingFactor = 0.05;
        }

        const animate = () => {
            requestAnimationFrame(animate);
            if (this.controls) {
                this.controls.update();
            }
            this.renderer.render(this.scene, this.camera);
        };
        animate();

        window.addEventListener('resize', () => {
            const newWidth = container.clientWidth;
            const newHeight = container.clientHeight;
            this.camera.aspect = newWidth / newHeight;
            this.camera.updateProjectionMatrix();
            this.renderer.setSize(newWidth, newHeight);
        });
    }

    attachEventListeners() {
        // Attach event listeners
        const btnToggle2D3D = document.getElementById('btn_toggle_2d_3d');
        const btnSaveLayout = document.getElementById('btn_save_layout');
        const btnDelete = document.getElementById('btn_delete');
        const btnClearAll = document.getElementById('btn_clear_all');

        if (btnToggle2D3D) {
            btnToggle2D3D.addEventListener('click', () => this.toggle2D3D());
        }
        if (btnSaveLayout) {
            btnSaveLayout.addEventListener('click', () => this.saveLayout());
        }
        if (btnDelete) {
            btnDelete.addEventListener('click', () => this.deleteSelectedLocation());
        }
        if (btnClearAll) {
            btnClearAll.addEventListener('click', () => this.clearAllLocations());
        }

        const canvas2D = document.getElementById('canvas_2d_editor');
        if (canvas2D) {
            canvas2D.addEventListener('mousemove', (e) => this.onCanvasDrag(e, canvas2D));
        }
    }

    toggle2D3D() {
        // Toggle between 2D and 3D view
        this.state.is3DView = !this.state.is3DView;
        
        const canvas2D = document.getElementById('canvas_2d_editor');
        const canvas3D = document.getElementById('canvas_3d_viewer');

        if (this.state.is3DView) {
            if (canvas2D) canvas2D.style.display = 'none';
            if (canvas3D) canvas3D.style.display = 'block';
        } else {
            if (canvas2D) canvas2D.style.display = 'block';
            if (canvas3D) canvas3D.style.display = 'none';
        }
    }

    async saveLayout() {
        // Save entire layout to database
        try {
            await this.orm.write('stock.warehouse', [this.state.warehouseId], {
                is_2d_configured: true,
                layout_width: this.state.canvasWidth,
                layout_height: this.state.canvasHeight,
            });

            for (const location of this.state.locations) {
                await this.orm.write('stock.location', [location.id], {
                    pos_x: location.pos_x || 0,
                    pos_y: location.pos_y || 0,
                    pos_z: location.pos_z || 0,
                    length: location.length || 1,
                    width: location.width || 1,
                    height: location.height || 1,
                });
            }

            this.notification.add(_t('Layout saved successfully'), { type: 'success' });
        } catch (error) {
            console.error('Error saving layout:', error);
            this.notification.add(_t('Error saving layout'), { type: 'danger' });
        }
    }

    async deleteSelectedLocation() {
        // Delete selected location
        if (!this.state.selectedLocation) {
            this.notification.add(_t('Please select a location first'), { type: 'warning' });
            return;
        }

        if (confirm(_t('Are you sure?'))) {
            try {
                await this.orm.unlink('stock.location', [this.state.selectedLocation.id]);
                this.state.locations = this.state.locations.filter(
                    loc => loc.id !== this.state.selectedLocation.id
                );
                this.state.selectedLocation = null;
                this.redrawCanvas2D();
                this.refresh3DView();
                this.notification.add(_t('Location deleted'), { type: 'info' });
            } catch (error) {
                console.error('Error deleting location:', error);
                this.notification.add(_t('Error deleting location'), { type: 'danger' });
            }
        }
    }

    async saveLocationPosition(location) {
        // Auto-save location position
        try {
            await this.orm.write('stock.location', [location.id], {
                pos_x: location.pos_x || 0,
                pos_y: location.pos_y || 0,
                pos_z: location.pos_z || 0,
            });
        } catch (error) {
            console.error('Error saving location position:', error);
        }
    }

    refresh3DView() {
        // Refresh 3D viewer
        if (this.scene) {
            const objectsToRemove = [];
            this.scene.traverse(obj => {
                if (obj.userData && obj.userData.isLocation) {
                    objectsToRemove.push(obj);
                }
            });
            objectsToRemove.forEach(obj => this.scene.remove(obj));
        }

        this.state.locations.forEach(location => {
            this.add3DLocation(location);
        });

        if (this.renderer) {
            this.renderer.render(this.scene, this.camera);
        }
    }

    add3DLocation(location) {
        // Add location to 3D scene
        if (!this.scene) return;

        const x = (location.pos_x || 50) / 100;
        const y = (location.pos_z || 0);
        const z = (location.pos_y || 50) / 100;

        const width = location.length || 1;
        const depth = location.width || 1;
        const height = location.height || 1;

        const geometry = new THREE.BoxGeometry(width, height, depth);
        const material = new THREE.MeshPhongMaterial({
            color: 0x667eea,
            opacity: 0.8,
            transparent: true
        });

        const mesh = new THREE.Mesh(geometry, material);
        mesh.position.set(x, y, z);
        mesh.userData.isLocation = true;
        mesh.userData.locationId = location.id;
        mesh.userData.locationName = location.unique_code || location.name;

        this.scene.add(mesh);
    }

    async clearAllLocations() {
        // Clear all locations
        if (confirm(_t('Delete ALL locations?'))) {
            try {
                const locationIds = this.state.locations.map(loc => loc.id);
                if (locationIds.length > 0) {
                    await this.orm.unlink('stock.location', locationIds);
                }
                this.state.locations = [];
                this.state.selectedLocation = null;
                this.redrawCanvas2D();
                this.notification.add(_t('All locations cleared'), { type: 'info' });
            } catch (error) {
                console.error('Error clearing locations:', error);
                this.notification.add(_t('Error clearing locations'), { type: 'danger' });
            }
        }
    }
}

// Register the client action
registry.category('actions').add('open_warehouse_layout_editor', WarehouseLayoutEditor);
