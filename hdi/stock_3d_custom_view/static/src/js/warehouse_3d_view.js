/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

/**
 * Warehouse 3D View Component - Integrated with warehouse_map module
 * Shows products/lots in their actual 3D positions from warehouse_map
 */
export class Warehouse3DView extends Component {
    static template = "stock_3d_custom_view.Warehouse3DView";

    setup() {
        this.user = useService("user");
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        
        this.state = useState({
            warehouses: [],
            selectedWarehouse: null,
            products: [],
            loading: true,
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

    async loadWarehouses() {
        try {
            const company_id = this.user.context.allowed_company_ids[0];
            const warehouses = await rpc('/3Dstock/warehouse', { company_id });
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
        await this.load3DView();
    }

    async load3DView() {
        this.state.loading = true;
        
        try {
            const company_id = this.user.context.allowed_company_ids[0];
            
            // Load location boxes (shelves/racks structure)
            const locationData = await rpc('/3Dstock/data', {
                company_id: company_id,
                wh_id: this.state.selectedWarehouse,
            });
            
            // Load product positions from warehouse_map
            const productsData = await rpc('/3Dstock/data/products', {
                company_id: company_id,
                wh_id: this.state.selectedWarehouse,
            });
            
            this.state.products = productsData;
            
            // Initialize Three.js scene
            this.init3DScene(locationData, productsData);
            
        } catch (error) {
            console.error("Error loading 3D view:", error);
            this.notification.add(_t("Failed to load 3D view"), { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    init3DScene(locationData, productsData) {
        // Clean up existing scene
        const container = document.getElementById('warehouse3d-container');
        if (!container) return;
        
        // Clear previous canvas
        while (container.firstChild) {
            container.removeChild(container.firstChild);
        }

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

        // Add controls
        const controls = new THREE.OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.25;

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

            if (intersects.length > 0) {
                const object = intersects[0].object;
                if (object.userData && object.userData.product_name) {
                    this.showProductDetails(object.userData);
                }
            }
        };

        renderer.domElement.addEventListener('click', onPointerClick);

        // Animation loop
        const animate = () => {
            requestAnimationFrame(animate);
            controls.update();
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

    onClose() {
        this.env.services.action.doAction({ type: 'ir.actions.act_window_close' });
    }
}

// Register as client action
registry.category("actions").add("open_warehouse_3d_view", Warehouse3DView);
