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
            products: [],
            loading: true,
            assignmentMode: false,
            selectedCoords: null,  // {x, y, z} from click
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
        this.state.assignmentMode = false;  // Reset assignment mode on warehouse change
        this.state.selectedCoords = null;
        await this.load3DView();
    }

    toggleAssignmentMode() {
        this.state.assignmentMode = !this.state.assignmentMode;
        this.state.selectedCoords = null;  // Clear selection when toggling
        
        // Update cursor for canvas view
        if (this.canvasElement) {
            this.canvasElement.style.cursor = this.state.assignmentMode ? 'crosshair' : 'default';
        }
        
        if (this.state.assignmentMode) {
            this.notification.add(_t("Click on a point in the 3D view to assign position"), { type: "info" });
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
            
            // Load location boxes (shelves/racks structure)
            const locationData = await rpc('/3Dstock/data', {
                company_id: company_id,
                wh_id: this.state.selectedWarehouse,
            });
            
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
                    this.init3DScene(locationData, productsData);
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

    init3DScene(locationData, productsData) {
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
            setTimeout(() => this.init3DScene(locationData, productsData), 200);
            return;
        }
        
        // Clear previous canvas
        while (container.firstChild) {
            container.removeChild(container.firstChild);
        }

        // Check if Three.js is available
        if (typeof THREE === 'undefined' || !window.THREE) {
            console.warn("Three.js library not available, showing fallback view");
            this.showFallbackView(container, productsData);
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

            // Draw location boxes (shelves/racks) - semi-transparent
            if (locationData && Object.keys(locationData).length > 0) {
                for (const [code, [posX, posY, posZ, length, width, height]] of Object.entries(locationData)) {
                const geometry = new THREE.BoxGeometry(length, height, width);
                const material = new THREE.MeshPhongMaterial({
                    color: 0xcccccc,
                    transparent: true,
                    opacity: 0.3,
                    wireframe: false,
                });
                
                const box = new THREE.Mesh(geometry, material);
                box.position.set(posX, posY + height/2, posZ);
                
                // Add edges for better visibility
                const edges = new THREE.EdgesGeometry(geometry);
                const lineMaterial = new THREE.LineBasicMaterial({ color: 0x000000, linewidth: 1 });
                const wireframe = new THREE.LineSegments(edges, lineMaterial);
                box.add(wireframe);
                
                scene.add(box);
                
                // Add label
                this.addTextLabel(scene, code, posX, posY + height + 10, posZ);
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

                if (this.state.assignmentMode) {
                    // In assignment mode, capture the clicked position
                    if (intersects.length > 0) {
                        const point = intersects[0].point;
                        this.state.selectedCoords = {
                            x: Math.round(point.x),
                            y: Math.round(point.y),
                            z: Math.round(point.z),
                        };
                        this.notification.add(
                            _t(`Position selected: X=${this.state.selectedCoords.x}, Y=${this.state.selectedCoords.y}, Z=${this.state.selectedCoords.z}`),
                            { type: "success" }
                        );
                    }
                } else {
                    // In normal mode, show product details
                    if (intersects.length > 0) {
                        const object = intersects[0].object;
                        if (object.userData && object.userData.product_name) {
                            this.showProductDetails(object.userData);
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

    showFallbackView(container, productsData) {
        // Show a Canvas-based 3D view without Three.js
        const canvas = document.createElement('canvas');
        canvas.width = container.clientWidth;
        canvas.height = container.clientHeight;
        canvas.style.cursor = this.state.assignmentMode ? 'crosshair' : 'default';
        container.appendChild(canvas);
        
        const ctx = canvas.getContext('2d');
        
        // Simple 3D isometric projection
        this.draw3DWarehouse(ctx, canvas, productsData);
        
        // Add click handler for position assignment
        canvas.addEventListener('click', (event) => {
            if (this.state.assignmentMode) {
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
                
                this.notification.add(
                    _t(`Position selected: X=${pos3dx}, Y=${pos3dy}, Z=${pos3dz}`),
                    { type: "success" }
                );
                
                // Redraw with selection indicator
                this.draw3DWarehouse(ctx, canvas, productsData);
            }
        });
        
        // Handle resize
        window.addEventListener('resize', () => {
            canvas.width = container.clientWidth;
            canvas.height = container.clientHeight;
            this.draw3DWarehouse(ctx, canvas, productsData);
        });
        
        // Store canvas reference for updates
        this.canvasElement = canvas;
        this.canvasContext = ctx;
    }
    
    draw3DWarehouse(ctx, canvas, productsData) {
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
            // Horizontal lines (isometric)
            ctx.beginPath();
            ctx.moveTo(centerX + i * gridSize, centerY - 5 * gridSize);
            ctx.lineTo(centerX + i * gridSize, centerY + 5 * gridSize);
            ctx.stroke();
            
            // Diagonal lines (isometric)
            ctx.beginPath();
            ctx.moveTo(centerX - 10 * gridSize + i * gridSize / 2, centerY - 5 * gridSize + i * gridSize / 2);
            ctx.lineTo(centerX + 10 * gridSize + i * gridSize / 2, centerY + 5 * gridSize + i * gridSize / 2);
            ctx.stroke();
        }
        
        // Draw location boxes (shelves)
        ctx.fillStyle = 'rgba(200, 200, 200, 0.3)';
        ctx.strokeStyle = '#000000';
        ctx.lineWidth = 1;
        
        // Simple shelf representation
        const shelfWidth = 150;
        const shelfHeight = 100;
        
        for (let z = 0; z < 3; z++) {
            for (let x = -1; x <= 1; x++) {
                const screenX = centerX + x * shelfWidth - z * 30;
                const screenY = centerY - z * 20;
                
                // Draw shelf box (simple rectangle for now)
                ctx.fillRect(screenX, screenY, shelfWidth, shelfHeight);
                ctx.strokeRect(screenX, screenY, shelfWidth, shelfHeight);
            }
        }
        
        // Draw products
        for (const product of productsData) {
            const color = '#' + product.color.toString(16).padStart(6, '0');
            ctx.fillStyle = color;
            ctx.strokeStyle = '#333';
            ctx.lineWidth = 2;
            
            // Calculate isometric position
            const scale = 0.3;
            const screenX = centerX + product.pos_x * scale - product.pos_z * scale * 0.5;
            const screenY = centerY + product.pos_y * scale - product.pos_z * scale * 0.5;
            
            // Draw product box
            const boxSize = 15;
            ctx.fillRect(screenX - boxSize/2, screenY - boxSize/2, boxSize, boxSize);
            ctx.strokeRect(screenX - boxSize/2, screenY - boxSize/2, boxSize, boxSize);
            
            // Draw label
            ctx.fillStyle = '#000';
            ctx.font = 'bold 10px Arial';
            ctx.textAlign = 'center';
            ctx.fillText(product.lot_name, screenX, screenY + boxSize + 12);
            ctx.font = '9px Arial';
            ctx.fillText(`Q:${product.quantity}`, screenX, screenY + boxSize + 23);
        }
        
        // Draw legend
        ctx.fillStyle = '#333';
        ctx.font = '12px Arial';
        ctx.textAlign = 'left';
        ctx.fillText('3D Warehouse Map (Canvas Render)', 20, 25);
        
        ctx.font = '10px Arial';
        ctx.fillStyle = '#00802b';
        ctx.fillRect(20, 35, 12, 12);
        ctx.fillStyle = '#333';
        ctx.fillText('High Stock (>100)', 38, 43);
        
        ctx.fillStyle = '#e6b800';
        ctx.fillRect(20, 50, 12, 12);
        ctx.fillStyle = '#333';
        ctx.fillText('Medium Stock (50-100)', 38, 58);
        
        ctx.fillStyle = '#cc0000';
        ctx.fillRect(20, 65, 12, 12);
        ctx.fillStyle = '#333';
        ctx.fillText('Low Stock (<50)', 38, 73);
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

    async assignPositionToProduct() {
        // Show dialog to select which product to assign this position to
        if (!this.state.selectedCoords) {
            this.notification.add(_t("Please select a position first"), { type: "warning" });
            return;
        }

        const ProductSelector = await import("@web/core/dialog");
        const selectedProduct = await this.dialog.add(ProductSelector, {
            title: _t("Assign Position"),
            message: _t("Select a product to assign to position X:%s, Y:%s, Z:%s", 
                this.state.selectedCoords.x, this.state.selectedCoords.y, this.state.selectedCoords.z),
            body: `
                <select id="product-selector" style="width:100%; padding:8px; margin:10px 0;">
                    <option value="">-- Select Product --</option>
                    ${this.state.products.map(p => 
                        `<option value="${p.id}">${p.product_name} (${p.lot_name})</option>`
                    ).join('')}
                </select>
            `,
            buttons: [
                {
                    text: _t("Cancel"),
                    classes: "btn-secondary",
                    close: true,
                },
                {
                    text: _t("Assign"),
                    classes: "btn-primary",
                    click: async () => {
                        const productId = document.getElementById('product-selector').value;
                        if (productId) {
                            await this.savePositionToProduct(parseInt(productId));
                        }
                    },
                },
            ],
        });
    }

    async savePositionToProduct(productId) {
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
                pos_x: this.state.selectedCoords.x,
                pos_y: this.state.selectedCoords.y,
                pos_z: this.state.selectedCoords.z,
            });

            if (result.success) {
                this.notification.add(
                    _t("Position assigned successfully"),
                    { type: "success" }
                );
                // Reload the 3D view to show updated positions
                this.state.selectedCoords = null;
                this.state.assignmentMode = false;
                await this.load3DView();
            } else {
                this.notification.add(
                    result.message || _t("Failed to assign position"),
                    { type: "danger" }
                );
            }
        } catch (error) {
            console.error("Error saving position:", error);
            this.notification.add(_t("Error: %s", error.message), { type: "danger" });
        }
    }

    onClose() {
        this.env.services.action.doAction({ type: 'ir.actions.act_window_close' });
    }
}

// Register as client action
registry.category("actions").add("stock_3d_custom_view.warehouse_3d_view", Warehouse3DView);
