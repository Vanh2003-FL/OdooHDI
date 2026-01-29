/** @odoo-module **/

import { Component, useState, onMounted, onWillUnmount, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { RouteAnimator } from "./route_animator";
import { Warehouse2DViewer } from "./warehouse_2d_viewer";

/**
 * Warehouse 3D Viewer using Three.js
 * 
 * Features:
 * - 3D warehouse layout rendering with bins, racks, aisles
 * - Interactive camera controls (orbit, pan, zoom)
 * - Route visualization with animated path
 * - Heatmap coloring by pick frequency
 * - Click to select bins and show details
 * - Real-time stock status updates
 */
export class Warehouse3DViewer extends Component {
    static template = "hdi_warehouse_3d.Warehouse3DViewerTemplate";
    static components = { Warehouse2DViewer };
    static props = {
        layoutId: { type: Number },
        viewMode: { type: String, optional: true }, // '3d' or '2d'
        showHeatmap: { type: Boolean, optional: true },
        pickingId: { type: Number, optional: true },
    };

    setup() {
        this.notification = useService("notification");
        this.containerRef = useRef("viewer3d");
        
        this.state = useState({
            loading: true,
            error: null,
            layoutData: null,
            selectedBin: null,
            viewMode: this.props.viewMode || '3d',
            showHeatmap: this.props.showHeatmap || false,
        });

        // Three.js objects
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.binMeshes = new Map(); // bin_id -> mesh
        this.routeAnimator = null;
        this.animationFrameId = null;

        onMounted(async () => {
            await this.loadLayoutData();
            this.initThreeJS();
            this.renderWarehouse();
            this.startRenderLoop();
        });

        onWillUnmount(() => {
            this.cleanup();
        });
    }

    /**
     * Load warehouse layout data from backend API
     */
    async loadLayoutData() {
        try {
            this.state.loading = true;
            const data = await rpc("/warehouse_3d/layout/" + this.props.layoutId);
            this.state.layoutData = data;
            
            if (this.props.pickingId && this.state.viewMode === '3d') {
                const routeData = await rpc("/warehouse_3d/route/" + this.props.pickingId);
                this.state.routeData = routeData;
            }
            
            if (this.state.showHeatmap) {
                const heatmapData = await rpc("/warehouse_3d/heatmap/" + this.props.layoutId);
                this.state.heatmapData = heatmapData;
            }
            
            this.state.loading = false;
        } catch (error) {
            console.error('Failed to load layout data:', error);
            this.state.error = error.message || 'Failed to load warehouse layout';
            this.state.loading = false;
            this.notification.add(this.state.error, { type: 'danger' });
        }
    }

    /**
     * Initialize Three.js scene, camera, renderer, controls
     */
    initThreeJS() {
        const container = this.containerRef.el;
        if (!container) return;

        // Scene
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0xf0f0f0);
        this.scene.fog = new THREE.Fog(0xf0f0f0, 50, 200);

        // Camera
        const width = container.clientWidth;
        const height = container.clientHeight;
        this.camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 1000);
        this.camera.position.set(30, 40, 30);
        this.camera.lookAt(0, 0, 0);

        // Renderer
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(width, height);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        container.appendChild(this.renderer.domElement);

        // Lights
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
        this.scene.add(ambientLight);

        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight.position.set(50, 100, 50);
        directionalLight.castShadow = true;
        directionalLight.shadow.mapSize.width = 2048;
        directionalLight.shadow.mapSize.height = 2048;
        this.scene.add(directionalLight);

        // Grid and axes
        const gridHelper = new THREE.GridHelper(100, 50, 0x888888, 0xcccccc);
        this.scene.add(gridHelper);
        
        const axesHelper = new THREE.AxesHelper(10);
        this.scene.add(axesHelper);

        // OrbitControls
        this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.minDistance = 10;
        this.controls.maxDistance = 200;

        // Raycaster for click detection
        this.raycaster = new THREE.Raycaster();
        this.mouse = new THREE.Vector2();

        // Route animator
        this.routeAnimator = new RouteAnimator(this.scene, this.camera);

        // Event listeners
        this.renderer.domElement.addEventListener('click', this.onMouseClick.bind(this));
        window.addEventListener('resize', this.onWindowResize.bind(this));
    }

    /**
     * Render warehouse layout
     */
    renderWarehouse() {
        if (!this.state.layoutData) return;

        const layout = this.state.layoutData;
        
        // Floor
        const floorGeometry = new THREE.PlaneGeometry(layout.width, layout.depth);
        const floorMaterial = new THREE.MeshStandardMaterial({ 
            color: 0xdddddd,
            roughness: 0.8,
        });
        const floor = new THREE.Mesh(floorGeometry, floorMaterial);
        floor.rotation.x = -Math.PI / 2;
        floor.receiveShadow = true;
        this.scene.add(floor);

        // Bins
        layout.bins.forEach(binData => this.renderBin(binData));

        // Route
        if (this.state.routeData) {
            const positions = this.state.routeData.optimized_sequence.map(binId => {
                const mesh = this.binMeshes.get(binId);
                return mesh ? mesh.position.clone() : null;
            }).filter(p => p !== null);
            
            if (positions.length > 0) {
                this.routeAnimator.loadRoute(positions);
                this.routeAnimator.start();
            }
        }

        // Heatmap
        if (this.state.showHeatmap && this.state.heatmapData) {
            this.applyHeatmap(this.state.heatmapData);
        }
    }

    /**
     * Render individual bin
     */
    renderBin(binData) {
        const geometry = new THREE.BoxGeometry(
            binData.width || 1.0,
            binData.height || 2.0,
            binData.depth || 1.0
        );

        let color = 0x4CAF50;
        if (binData.bin_status === 'partial') color = 0xFFC107;
        else if (binData.bin_status === 'full') color = 0xF44336;

        const material = new THREE.MeshStandardMaterial({
            color: color,
            roughness: 0.5,
            metalness: 0.3,
            transparent: true,
            opacity: 0.85,
        });

        const mesh = new THREE.Mesh(geometry, material);
        mesh.position.set(
            binData.position_x || 0,
            (binData.height || 2.0) / 2,
            binData.position_z || 0
        );
        mesh.castShadow = true;
        mesh.receiveShadow = true;
        mesh.userData = { binId: binData.id, binData: binData };

        this.scene.add(mesh);
        this.binMeshes.set(binData.id, mesh);
    }

    /**
     * Apply heatmap colors
     */
    applyHeatmap(heatmapData) {
        if (!heatmapData.heatmap_data) return;

        const maxPicks = heatmapData.max_picks || 1;
        
        Object.entries(heatmapData.heatmap_data).forEach(([binId, picks]) => {
            const mesh = this.binMeshes.get(parseInt(binId));
            if (!mesh) return;

            const intensity = picks / maxPicks;
            let color;
            if (intensity < 0.25) color = new THREE.Color(0x2196F3);
            else if (intensity < 0.5) color = new THREE.Color(0x4CAF50);
            else if (intensity < 0.75) color = new THREE.Color(0xFFC107);
            else color = new THREE.Color(0xF44336);

            mesh.material.color = color;
            mesh.material.needsUpdate = true;
        });
    }

    /**
     * Handle mouse click
     */
    onMouseClick(event) {
        const rect = this.renderer.domElement.getBoundingClientRect();
        this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

        this.raycaster.setFromCamera(this.mouse, this.camera);
        const intersects = this.raycaster.intersectObjects(Array.from(this.binMeshes.values()));

        if (intersects.length > 0) {
            const clickedMesh = intersects[0].object;
            this.state.selectedBin = clickedMesh.userData.binData;
            this.highlightBin(clickedMesh);
        }
    }

    /**
     * Highlight selected bin
     */
    highlightBin(mesh) {
        this.binMeshes.forEach(m => {
            if (m.userData.highlighted) {
                m.scale.set(1, 1, 1);
                m.userData.highlighted = false;
            }
        });

        mesh.scale.set(1.1, 1.1, 1.1);
        mesh.userData.highlighted = true;
    }

    /**
     * Window resize
     */
    onWindowResize() {
        const container = this.containerRef.el;
        if (!container) return;

        const width = container.clientWidth;
        const height = container.clientHeight;

        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height);
    }

    /**
     * Render loop
     */
    startRenderLoop() {
        const animate = () => {
            this.animationFrameId = requestAnimationFrame(animate);
            
            if (this.controls) this.controls.update();
            if (this.renderer && this.scene && this.camera) {
                this.renderer.render(this.scene, this.camera);
            }
        };
        animate();
    }

    /**
     * Cleanup
     */
    cleanup() {
        if (this.animationFrameId) cancelAnimationFrame(this.animationFrameId);
        if (this.routeAnimator) this.routeAnimator.clear();
        
        this.scene?.traverse(object => {
            if (object.geometry) object.geometry.dispose();
            if (object.material) {
                if (Array.isArray(object.material)) {
                    object.material.forEach(m => m.dispose());
                } else {
                    object.material.dispose();
                }
            }
        });

        if (this.renderer) this.renderer.dispose();
        window.removeEventListener('resize', this.onWindowResize.bind(this));
    }

    toggleViewMode() {
        this.state.viewMode = this.state.viewMode === '3d' ? '2d' : '3d';
    }

    toggleHeatmap() {
        this.state.showHeatmap = !this.state.showHeatmap;
        this.loadLayoutData();
    }
}

registry.category("fields").add("warehouse_3d_viewer", {
    component: Warehouse3DViewer,
});
