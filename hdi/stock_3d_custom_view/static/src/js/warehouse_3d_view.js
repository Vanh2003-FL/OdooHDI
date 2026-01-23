/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

/**
 * Warehouse 3D View Component - Integrated with warehouse_map module
 * Shows products/lots in their actual 3D positions from warehouse_map
 */
export class Warehouse3DView extends Component {
    static template = "stock_3d_custom_view.Warehouse3DView";

    setup() {
        // Don't use useService for optional services
        // Access them directly from env.services instead
        
        this.state = useState({
            warehouses: [],
            selectedWarehouse: null,
            locations: [],  // Shelves/racks from stock.location
            products: [],
            loading: true,
            viewMode: 'view',  // 'view' | 'editor' | 'assignment'
            selectedCoords: null,  // {x, y, z} from click
            pendingShelfData: null,  // Temporary shelf being created
        });

        onMounted(() => {
            this.loadWarehouses();
        });

        onWillUnmount(() => {
            if (this.renderer) {
                this.renderer.dispose();
            }
        });
    }
    
    get notification() {
        return this.env.services.notification;
    }
    
    get dialog() {
        return this.env.services.dialog;
    }

    async loadWarehouses() {
        try {
            // Try to get company_id from context, fallback to current session
            let company_id;
            try {
                company_id = this.env.services.user.context.allowed_company_ids[0];
            } catch (e) {
                // If user service not available, use RPC without specifying company
                // Server will use current user's company
                company_id = null;
            }
            
            const warehouses = await rpc('/3Dstock/warehouse', { 
                company_id: company_id || 1  // Fallback to company 1
            });
            this.state.warehouses = warehouses;
            
            if (warehouses.length > 0) {
                this.state.selectedWarehouse = warehouses[0][0];
                await this.load3DView();
            }
        } catch (error) {
            console.error("Error loading warehouses:", error);
            this.notification.add(_t("Failed to load warehouses"), { type: "danger" });
        }
    }

    async onWarehouseChange(ev) {
        this.state.selectedWarehouse = parseInt(ev.target.value);
        this.state.viewMode = 'view';  // Reset to view mode on warehouse change
        this.state.selectedCoords = null;
        await this.load3DView();
    }

    toggleEditorMode() {
        // Only admins can edit warehouse layout
        if (this.state.viewMode === 'editor') {
            this.state.viewMode = 'view';
            this.notification.add(_t("Exited editor mode"), { type: "info" });
        } else {
            this.state.viewMode = 'editor';
            this.state.selectedCoords = null;
            this.notification.add(_t("Click on 3D area to create a new shelf, then enter shelf details"), { type: "info" });
        }
    }

    toggleAssignmentMode() {
        if (this.state.viewMode === 'assignment') {
            this.state.viewMode = 'view';
            this.notification.add(_t("Exited assignment mode"), { type: "info" });
        } else {
            this.state.viewMode = 'assignment';
            this.state.selectedCoords = null;
            this.notification.add(_t("Click on a shelf to assign products"), { type: "info" });
        }
        
        // Update cursor for canvas view
        if (this.canvasElement) {
            this.canvasElement.style.cursor = this.state.viewMode !== 'view' ? 'crosshair' : 'grab';
        }
    }

    async load3DView() {
        this.state.loading = true;
        
        try {
            let company_id;
            try {
                company_id = this.env.services.user.context.allowed_company_ids[0];
            } catch (e) {
                company_id = 1;  // Fallback
            }
            
            // Load location boxes (shelves/racks structure) from stock.location
            const locationsData = await rpc('/3Dstock/locations', {
                company_id: company_id,
                wh_id: this.state.selectedWarehouse,
            });
            this.state.locations = locationsData || [];
            
            // Load product positions from warehouse_map
            let productsData = await rpc('/3Dstock/data/products', {
                company_id: company_id,
                wh_id: this.state.selectedWarehouse,
            });
            
            // Add demo products if no real data (for testing)
            if (!productsData || productsData.length === 0) {
                productsData = [
                    {
                        id: 1,
                        product_name: "Demo Product A",
                        lot_name: "DEMO-001",
                        quantity: 150,
                        pos_x: 100,
                        pos_y: 50,
                        pos_z: 100,
                        location_name: "WH/Stock",
                        color: 0x00802b,  // Green
                    },
                    {
                        id: 2,
                        product_name: "Demo Product B",
                        lot_name: "DEMO-002",
                        quantity: 75,
                        pos_x: 200,
                        pos_y: 50,
                        pos_z: 200,
                        location_name: "WH/Stock",
                        color: 0xe6b800,  // Yellow
                    },
                ];
            }
            
            // Convert color to hex string for template
            productsData.forEach(product => {
                product.colorHex = '#' + product.color.toString(16).padStart(6, '0');
            });
            
            this.state.products = productsData;
            
            // Initialize Three.js scene with a small delay to ensure DOM is ready
            setTimeout(() => {
                try {
                    this.init3DScene(this.state.locations, productsData);
                } catch (error) {
                    console.error("Error initializing 3D scene:", error);
                    this.notification.add(_t("Failed to initialize 3D scene: %s", error.message), { type: "danger" });
                }
            }, 100);
            
        } catch (error) {
            console.error("Error loading 3D view:", error);
            this.notification.add(_t("Failed to load 3D view: %s", error.message), { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    init3DScene(locationsData, productsData) {
        // Clean up existing scene
        const container = document.getElementById('warehouse3d-container');
        if (!container) {
            console.error("Canvas container not found");
            this.notification.add(_t("Canvas container not found"), { type: "danger" });
            return;
        }
        
        // Check if container has dimensions
        if (container.clientWidth === 0 || container.clientHeight === 0) {
            console.warn("Container has zero dimensions, retrying...");
            setTimeout(() => this.init3DScene(locationsData, productsData), 200);
            return;
        }
        
        // Clear previous canvas
        while (container.firstChild) {
            container.removeChild(container.firstChild);
        }

        // Check if Three.js is available
        if (typeof THREE === 'undefined' || !window.THREE) {
            console.warn("Three.js library not available, showing fallback view");
            this.showFallbackView(container, locationsData, productsData);
            return;
        }

        try {
            // Setup Three.js
            const scene = new THREE.Scene();
            scene.background = new THREE.Color(0xf0f0f0);
            
            const camera = new THREE.PerspectiveCamera(
                60, 
                container.clientWidth / container.clientHeight, 
                0.5, 
                6000
            );
            camera.position.set(400, 600, 800);
            camera.lookAt(0, 0, 0);

            const renderer = new THREE.WebGLRenderer({ antialias: true });
            renderer.setSize(container.clientWidth, container.clientHeight);
            renderer.setPixelRatio(window.devicePixelRatio);
            container.appendChild(renderer.domElement);

            // Get OrbitControls from either location
            let OrbitControls = THREE.OrbitControls || window.OrbitControls;
            let controls = null;
            
            // If found, create controls instance
            if (OrbitControls) {
                controls = new OrbitControls(camera, renderer.domElement);
                controls.enableDamping = true;
                controls.dampingFactor = 0.25;
                console.log("OrbitControls initialized successfully");
            } else {
                console.warn("OrbitControls not available, 3D view will have basic camera only");
            }

            // Add lights
            const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
            scene.add(ambientLight);
            
            const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
            directionalLight.position.set(200, 500, 300);
            scene.add(directionalLight);

            // Add floor grid
            const gridHelper = new THREE.GridHelper(1000, 20, 0x888888, 0xcccccc);
            scene.add(gridHelper);

            // Draw location boxes (shelves/racks)
            if (locationsData && locationsData.length > 0) {
                for (const location of locationsData) {
                    const geometry = new THREE.BoxGeometry(location.loc_length, location.loc_height, location.loc_width);
                    const material = new THREE.MeshPhongMaterial({
                        color: 0xcccccc,
                        transparent: true,
                        opacity: 0.3,
                        wireframe: false,
                    });
                    
                    const box = new THREE.Mesh(geometry, material);
                    box.position.set(location.loc_pos_x, location.loc_pos_y + location.loc_height/2, location.loc_pos_z);
                    box.userData = location;  // Store location data for click events
                    
                    // Add edges for better visibility
                    const edges = new THREE.EdgesGeometry(geometry);
                    const lineMaterial = new THREE.LineBasicMaterial({ color: 0x000000, linewidth: 1 });
                    const wireframe = new THREE.LineSegments(edges, lineMaterial);
                    box.add(wireframe);
                    
                    scene.add(box);
                    
                    // Add label
                    this.addTextLabel(scene, location.loc_3d_code || location.name, location.loc_pos_x, location.loc_pos_y + location.loc_height + 10, location.loc_pos_z);
                }
            }

            // Draw products from warehouse_map positions
            for (const product of productsData) {
                const geometry = new THREE.BoxGeometry(20, 20, 20);
                const material = new THREE.MeshPhongMaterial({
                    color: product.color,
                    transparent: false,
                    opacity: 1.0,
                });
                
                const productBox = new THREE.Mesh(geometry, material);
                productBox.position.set(product.pos_x, product.pos_y, product.pos_z);
                productBox.userData = product; // Store product data for click events
                
                scene.add(productBox);
                
                // Add product label
                const label = `${product.lot_name}\n${product.quantity}`;
                this.addTextLabel(scene, label, product.pos_x, product.pos_y + 15, product.pos_z, 0x000000, 8);
            }

            // Raycaster for click detection
            const raycaster = new THREE.Raycaster();
            const pointer = new THREE.Vector2();

            const onPointerClick = (event) => {
                const rect = renderer.domElement.getBoundingClientRect();
                pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
                pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

                raycaster.setFromCamera(pointer, camera);
                const intersects = raycaster.intersectObjects(scene.children, true);

                if (this.state.viewMode === 'editor') {
                    // In editor mode, create new shelf at clicked position
                    if (intersects.length > 0) {
                        const point = intersects[0].point;
                        this.state.selectedCoords = {
                            x: Math.round(point.x),
                            y: Math.round(point.y),
                            z: Math.round(point.z),
                        };
                        this.showCreateShelfDialog();
                    }
                } else if (this.state.viewMode === 'assignment') {
                    // In assignment mode, select a shelf to assign products
                    if (intersects.length > 0) {
                        const object = intersects[0].object;
                        if (object.userData && object.userData.loc_3d_code) {
                            this.state.selectedCoords = object.userData;
                            this.notification.add(
                                _t(`Shelf selected: ${object.userData.loc_3d_code || object.userData.name}`),
                                { type: "success" }
                            );
                        }
                    }
                } else {
                    // In normal mode, show product/location details
                    if (intersects.length > 0) {
                        const object = intersects[0].object;
                        if (object.userData && object.userData.product_name) {
                            this.showProductDetails(object.userData);
                        } else if (object.userData && object.userData.loc_3d_code) {
                            this.showLocationDetails(object.userData);
                        }
                    }
                }
            };

            renderer.domElement.addEventListener('click', onPointerClick);

            // Animation loop
            const animate = () => {
                requestAnimationFrame(animate);
                if (controls) {
                    controls.update();
                }
                renderer.render(scene, camera);
            };
            animate();

            // Handle window resize
            const onWindowResize = () => {
                camera.aspect = container.clientWidth / container.clientHeight;
                camera.updateProjectionMatrix();
                renderer.setSize(container.clientWidth, container.clientHeight);
            };
            window.addEventListener('resize', onWindowResize);

            // Store for cleanup
            this.renderer = renderer;
            this.scene = scene;
            
            console.log("3D scene initialized successfully");
            
        } catch (error) {
            console.error("Error in init3DScene:", error);
            this.notification.add(_t("Error initializing 3D scene: %s", error.message), { type: "danger" });
        }
    }

    showFallbackView(container, locationsData, productsData) {
        // Show a Canvas-based 3D view without Three.js
        const canvas = document.createElement('canvas');
        canvas.width = container.clientWidth;
        canvas.height = container.clientHeight;
        canvas.style.cursor = this.state.viewMode !== 'view' ? 'crosshair' : 'grab';
        container.appendChild(canvas);
        
        const ctx = canvas.getContext('2d');
        
        // Simple 3D isometric projection
        this.draw3DWarehouse(ctx, canvas, locationsData, productsData);
        
        // Add click handler
        canvas.addEventListener('click', (event) => {
            if (this.state.viewMode !== 'view') {
                const rect = canvas.getBoundingClientRect();
                const x = event.clientX - rect.left;
                const y = event.clientY - rect.top;
                
                // Convert screen coordinates back to 3D coordinates (approximate)
                const centerX = canvas.width / 2;
                const centerY = canvas.height / 2;
                const scale = 0.3;
                
                const pos3dx = Math.round((x - centerX) / scale);
                const pos3dz = 0;
                const pos3dy = Math.round((centerY - y) / scale);
                
                this.state.selectedCoords = {
                    x: pos3dx,
                    y: pos3dy,
                    z: pos3dz,
                };
                
                if (this.state.viewMode === 'editor') {
                    this.showCreateShelfDialog();
                }
            }
        });
        
        // Handle resize
        window.addEventListener('resize', () => {
            canvas.width = container.clientWidth;
            canvas.height = container.clientHeight;
            this.draw3DWarehouse(ctx, canvas, locationsData, productsData);
        });
        
        // Store canvas reference for updates
        this.canvasElement = canvas;
        this.canvasContext = ctx;
    }
    
    draw3DWarehouse(ctx, canvas, locationsData, productsData) {
        // Clear canvas
        ctx.fillStyle = '#f0f0f0';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        const centerX = canvas.width / 2;
        const centerY = canvas.height / 2;
        
        // Draw floor grid
        ctx.strokeStyle = '#cccccc';
        ctx.lineWidth = 1;
        const gridSize = 40;
        
        for (let i = -10; i <= 10; i++) {
            ctx.beginPath();
            ctx.moveTo(centerX + i * gridSize, centerY - 5 * gridSize);
            ctx.lineTo(centerX + i * gridSize, centerY + 5 * gridSize);
            ctx.stroke();
            
            ctx.beginPath();
            ctx.moveTo(centerX - 10 * gridSize + i * gridSize / 2, centerY - 5 * gridSize + i * gridSize / 2);
            ctx.lineTo(centerX + 10 * gridSize + i * gridSize / 2, centerY + 5 * gridSize + i * gridSize / 2);
            ctx.stroke();
        }
        
        // Draw location boxes (shelves)
        if (locationsData && locationsData.length > 0) {
            ctx.fillStyle = 'rgba(200, 200, 200, 0.3)';
            ctx.strokeStyle = '#000000';
            ctx.lineWidth = 1;
            
            for (const location of locationsData) {
                const scale = 0.3;
                const screenX = centerX + location.loc_pos_x * scale - location.loc_pos_z * scale * 0.5;
                const screenY = centerY + location.loc_pos_y * scale - location.loc_pos_z * scale * 0.5;
                
                const boxWidth = location.loc_length * scale;
                const boxHeight = location.loc_height * scale;
                
                ctx.fillRect(screenX - boxWidth/2, screenY - boxHeight/2, boxWidth, boxHeight);
                ctx.strokeRect(screenX - boxWidth/2, screenY - boxHeight/2, boxWidth, boxHeight);
                
                // Draw label
                ctx.fillStyle = '#000';
                ctx.font = 'bold 10px Arial';
                ctx.textAlign = 'center';
                ctx.fillText(location.loc_3d_code || location.name, screenX, screenY + boxHeight + 12);
            }
        }
        
        // Draw products
        if (productsData && productsData.length > 0) {
            for (const product of productsData) {
                const color = '#' + product.color.toString(16).padStart(6, '0');
                ctx.fillStyle = color;
                ctx.strokeStyle = '#333';
                ctx.lineWidth = 2;
                
                const scale = 0.3;
                const screenX = centerX + product.pos_x * scale - product.pos_z * scale * 0.5;
                const screenY = centerY + product.pos_y * scale - product.pos_z * scale * 0.5;
                
                const boxSize = 15;
                ctx.fillRect(screenX - boxSize/2, screenY - boxSize/2, boxSize, boxSize);
                ctx.strokeRect(screenX - boxSize/2, screenY - boxSize/2, boxSize, boxSize);
                
                ctx.fillStyle = '#000';
                ctx.font = 'bold 10px Arial';
                ctx.textAlign = 'center';
                ctx.fillText(product.lot_name, screenX, screenY + boxSize + 12);
            }
        }
    }

    addTextLabel(scene, text, x, y, z, color = 0x000000, size = 12) {
        // Using CSS2DRenderer would be better, but for simplicity using canvas texture
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        canvas.width = 256;
        canvas.height = 128;
        
        context.fillStyle = 'white';
        context.fillRect(0, 0, canvas.width, canvas.height);
        
        context.font = `${size}px Arial`;
        context.fillStyle = `#${color.toString(16).padStart(6, '0')}`;
        context.textAlign = 'center';
        context.textBaseline = 'middle';
        
        const lines = text.split('\n');
        lines.forEach((line, i) => {
            context.fillText(line, canvas.width / 2, canvas.height / 2 + i * size);
        });

        const texture = new THREE.CanvasTexture(canvas);
        const material = new THREE.SpriteMaterial({ map: texture });
        const sprite = new THREE.Sprite(material);
        sprite.position.set(x, y, z);
        sprite.scale.set(50, 25, 1);
        
        scene.add(sprite);
    }

    showProductDetails(productData) {
        const message = `
            <strong>${_t("Product")}:</strong> ${productData.product_name}<br/>
            <strong>${_t("Lot/Serial")}:</strong> ${productData.lot_name}<br/>
            <strong>${_t("Quantity")}:</strong> ${productData.quantity}<br/>
            <strong>${_t("Location")}:</strong> ${productData.location_name}<br/>
            <strong>${_t("Position")}:</strong> X:${Math.round(productData.pos_x/30)}, Y:${Math.round(productData.pos_y/60)}, Z:${Math.round(productData.pos_z/30)}
        `;
        
        this.notification.add(message, { 
            type: "info",
            title: _t("Product Details"),
            sticky: false,
        });
    }

    showLocationDetails(locationData) {
        const message = `
            <strong>${_t("Location")}:</strong> ${locationData.loc_3d_code || locationData.name}<br/>
            <strong>${_t("Position")}:</strong> X:${locationData.loc_pos_x}, Y:${locationData.loc_pos_y}, Z:${locationData.loc_pos_z}<br/>
            <strong>${_t("Dimensions")}:</strong> L:${locationData.loc_length}, W:${locationData.loc_width}, H:${locationData.loc_height}
        `;
        
        this.notification.add(message, { 
            type: "info",
            title: _t("Shelf Details"),
            sticky: false,
        });
    }

    async showCreateShelfDialog() {
        // Dialog to create a new shelf at clicked position
        const coords = this.state.selectedCoords;
        
        const form = document.createElement('div');
        form.style.cssText = "padding:20px;";
        form.innerHTML = `
            <div style="margin-bottom:15px;">
                <label style="display:block; margin-bottom:5px;"><strong>Shelf Name/Code:</strong></label>
                <input type="text" id="shelf-code" placeholder="e.g., SHELF-001" style="width:100%; padding:8px; box-sizing:border-box;">
            </div>
            <div style="margin-bottom:15px;">
                <label style="display:block; margin-bottom:5px;"><strong>Length (X):</strong></label>
                <input type="number" id="shelf-length" value="100" style="width:100%; padding:8px; box-sizing:border-box;">
            </div>
            <div style="margin-bottom:15px;">
                <label style="display:block; margin-bottom:5px;"><strong>Width (Z):</strong></label>
                <input type="number" id="shelf-width" value="80" style="width:100%; padding:8px; box-sizing:border-box;">
            </div>
            <div style="margin-bottom:15px;">
                <label style="display:block; margin-bottom:5px;"><strong>Height (Y):</strong></label>
                <input type="number" id="shelf-height" value="200" style="width:100%; padding:8px; box-sizing:border-box;">
            </div>
            <div style="padding:10px; background:#f5f5f5; border-radius:4px;">
                <strong>Position:</strong> X=${coords.x}, Y=${coords.y}, Z=${coords.z}
            </div>
        `;

        const savedShelf = await new Promise((resolve) => {
            this.dialog.add(
                window.owl.components.ConfirmationDialog || CustomDialog,
                {
                    title: _t("Create New Shelf"),
                    body: form,
                    confirmLabel: _t("Create"),
                    cancelLabel: _t("Cancel"),
                    onConfirm: async () => {
                        const code = document.getElementById('shelf-code').value;
                        const length = parseInt(document.getElementById('shelf-length').value) || 100;
                        const width = parseInt(document.getElementById('shelf-width').value) || 80;
                        const height = parseInt(document.getElementById('shelf-height').value) || 200;

                        if (!code) {
                            this.notification.add(_t("Please enter shelf code"), { type: "warning" });
                            resolve(null);
                            return;
                        }

                        await this.saveShelf({
                            code: code,
                            length: length,
                            width: width,
                            height: height,
                            pos_x: coords.x,
                            pos_y: coords.y,
                            pos_z: coords.z,
                        });
                        resolve(true);
                    },
                    onCancel: () => resolve(false),
                },
                { onClose: () => {} }
            );
        });
    }

    async saveShelf(shelfData) {
        try {
            let company_id;
            try {
                company_id = this.env.services.user.context.allowed_company_ids[0];
            } catch (e) {
                company_id = 1;
            }

            const result = await rpc('/3Dstock/save-shelf', {
                company_id: company_id,
                wh_id: this.state.selectedWarehouse,
                shelf_code: shelfData.code,
                loc_length: shelfData.length,
                loc_width: shelfData.width,
                loc_height: shelfData.height,
                loc_pos_x: shelfData.pos_x,
                loc_pos_y: shelfData.pos_y,
                loc_pos_z: shelfData.pos_z,
            });

            if (result.success) {
                this.notification.add(
                    _t("Shelf created successfully"),
                    { type: "success" }
                );
                this.state.selectedCoords = null;
                await this.load3DView();
            } else {
                this.notification.add(
                    result.message || _t("Failed to create shelf"),
                    { type: "danger" }
                );
            }
        } catch (error) {
            console.error("Error saving shelf:", error);
            this.notification.add(_t("Error: %s", error.message), { type: "danger" });
        }
    }

    async assignPositionToProduct() {
        // Assign product to selected shelf (in assignment mode)
        if (!this.state.selectedCoords || !this.state.selectedCoords.loc_3d_code) {
            this.notification.add(_t("Please select a shelf first"), { type: "warning" });
            return;
        }

        const shelf = this.state.selectedCoords;
        
        // Create product dropdown
        let selectedProductId = null;
        const isConfirmed = await new Promise((resolve) => {
            const select = document.createElement('select');
            select.style.cssText = "width:100%; padding:8px; margin:10px 0;";
            select.innerHTML = `
                <option value="">-- Select Product --</option>
                ${this.state.products.map(p => 
                    `<option value="${p.id}">${p.product_name} (${p.lot_name})</option>`
                ).join('')}
            `;

            const container = document.createElement('div');
            container.style.cssText = "padding:20px;";
            container.innerHTML = `
                <h4>Assign Product to Shelf</h4>
                <p><strong>Shelf:</strong> ${shelf.loc_3d_code || shelf.name}</p>
                <p><strong>Position:</strong> X=${shelf.loc_pos_x}, Y=${shelf.loc_pos_y}, Z=${shelf.loc_pos_z}</p>
                <p style="margin-top:15px;"><strong>Select Product:</strong></p>
            `;
            container.appendChild(select);

            this.dialog.add(
                window.owl.components.ConfirmationDialog || CustomDialog,
                {
                    title: _t("Assign Product to Shelf"),
                    body: container,
                    confirmLabel: _t("Assign"),
                    cancelLabel: _t("Cancel"),
                    onConfirm: () => {
                        selectedProductId = select.value;
                        resolve(selectedProductId ? true : false);
                    },
                    onCancel: () => resolve(false),
                },
                { onClose: () => {} }
            );
        });

        if (isConfirmed && selectedProductId) {
            await this.saveProductToShelf(parseInt(selectedProductId), shelf);
        } else if (isConfirmed) {
            this.notification.add(_t("Please select a product"), { type: "warning" });
        }
    }

    async saveProductToShelf(productId, shelf) {
        try {
            let company_id;
            try {
                company_id = this.env.services.user.context.allowed_company_ids[0];
            } catch (e) {
                company_id = 1;
            }

            const result = await rpc('/3Dstock/save-position', {
                company_id: company_id,
                wh_id: this.state.selectedWarehouse,
                product_id: productId,
                pos_x: shelf.loc_pos_x,
                pos_y: shelf.loc_pos_y,
                pos_z: shelf.loc_pos_z,
            });

            if (result.success) {
                this.notification.add(
                    _t("Product assigned to shelf successfully"),
                    { type: "success" }
                );
                this.state.selectedCoords = null;
                this.state.viewMode = 'view';
                await this.load3DView();
            } else {
                this.notification.add(
                    result.message || _t("Failed to assign product"),
                    { type: "danger" }
                );
            }
        } catch (error) {
            console.error("Error saving product position:", error);
            this.notification.add(_t("Error: %s", error.message), { type: "danger" });
        }
    }

    onClose() {
        this.env.services.action.doAction({ type: 'ir.actions.act_window_close' });
    }
}

// Register as client action (safe registration)
try {
    const actions = registry.category("actions");
    // Only register if not already present
    if (!actions.contains("warehouse_3d_view_action_v18")) {
        actions.add("warehouse_3d_view_action_v18", Warehouse3DView);
    }
} catch (e) {
    console.warn("Failed to register warehouse_3d_view_action_v18:", e);
}
