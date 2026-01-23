/** @odoo-module **/

import { Component, useState, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

// Three.js sẽ được load từ CDN trong template
let THREE = null;
let OrbitControls = null;

export class WarehouseMap3DView extends Component {
    static props = {
        "*": true,
    };
    
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        
        this.state = useState({
            mapData: null,
            loading: true,
            selectedCell: null,
            currentLevel: 0,
            showAllLevels: true,
        });

        // Three.js objects
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.raycaster = null;
        this.mouse = null;
        this.cellMeshes = [];
        this.labelSprites = [];
        this.containerRef = null;

        onWillStart(async () => {
            await this.loadThreeJS();
            await this.loadMapData();
        });

        onMounted(() => {
            // Đợi DOM render xong rồi mới init
            setTimeout(() => {
                if (this.state.mapData) {
                    this.initThreeJS();
                    this.render3DMap();
                    this.animate();
                    
                    // Handle window resize
                    this.resizeHandler = () => this.onWindowResize();
                    window.addEventListener('resize', this.resizeHandler);
                    
                    // Handle mouse events
                    this.clickHandler = (event) => this.onMouseClick(event);
                    if (this.containerRef) {
                        this.containerRef.addEventListener('click', this.clickHandler);
                    }
                }
            }, 0);
        });

        onWillUnmount(() => {
            if (this.resizeHandler) {
                window.removeEventListener('resize', this.resizeHandler);
            }
            if (this.clickHandler && this.containerRef) {
                this.containerRef.removeEventListener('click', this.clickHandler);
            }
            this.disposeThreeJS();
        });
    }

    getMapId() {
        const activeId = 
            this.props.action?.context?.active_id ||
            this.props.context?.active_id ||
            this.props.action?.res_id ||
            this.props.res_id;
        
        if (activeId) {
            return activeId;
        }
        
        console.warn('No active_id found for 3D warehouse map');
        return null;
    }

    async loadThreeJS() {
        // Load Three.js from CDN if not already loaded
        if (window.THREE) {
            THREE = window.THREE;
            if (window.THREE.OrbitControls) {
                OrbitControls = window.THREE.OrbitControls;
            }
            return;
        }

        try {
            return new Promise((resolve, reject) => {
                // Load Three.js
                const script = document.createElement('script');
                script.src = 'https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.min.js';
                script.onload = () => {
                    THREE = window.THREE;
                    
                    // Load OrbitControls
                    const controlsScript = document.createElement('script');
                    controlsScript.src = 'https://cdn.jsdelivr.net/npm/three@0.160.0/examples/js/controls/OrbitControls.js';
                    controlsScript.onload = () => {
                        OrbitControls = THREE.OrbitControls;
                        resolve();
                    };
                    controlsScript.onerror = () => reject(new Error('Failed to load OrbitControls'));
                    document.head.appendChild(controlsScript);
                };
                script.onerror = () => reject(new Error('Failed to load Three.js'));
                document.head.appendChild(script);
            });
        } catch (error) {
            console.error('Error loading Three.js:', error);
            this.notification.add('Không thể tải thư viện 3D. Vui lòng kiểm tra kết nối internet.', {
                type: 'danger',
            });
        }
    }

    async loadMapData() {
        try {
            this.state.loading = true;
            let mapId = this.getMapId();
            
            if (!mapId) {
                const maps = await this.orm.search('warehouse.map.3d', [], {limit: 1, order: 'sequence,name'});
                
                if (!maps || maps.length === 0) {
                    this.notification.add('Không có sơ đồ kho 3D nào. Vui lòng tạo sơ đồ kho 3D trước.', {
                        type: 'warning',
                    });
                    this.state.mapData = null;
                    this.state.loading = false;
                    return;
                }
                mapId = maps[0];
            }
            
            const data = await this.orm.call(
                'warehouse.map.3d',
                'get_map_3d_data',
                [mapId]
            );
            
            this.state.mapData = data;
            this.state.loading = false;
        } catch (error) {
            console.error('Error loading 3D map data:', error);
            this.notification.add(`Lỗi khi tải dữ liệu sơ đồ 3D: ${error.message}`, {
                type: 'danger',
            });
            this.state.loading = false;
        }
    }

    initThreeJS() {
        this.containerRef = document.getElementById('warehouse-map-3d-container');
        if (!this.containerRef) {
            console.error('Container not found: warehouse-map-3d-container');
            return;
        }
        if (!THREE) {
            console.error('THREE.js not loaded');
            return;
        }

        const width = this.containerRef.clientWidth;
        const height = this.containerRef.clientHeight;

        // Scene
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0xf0f0f0);

        // Camera - góc nhìn isometric giống mẫu
        this.camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 1000);
        const mapSize = Math.max(this.state.mapData?.columns || 10, this.state.mapData?.rows || 10) * (this.state.mapData?.cell_width || 1.2);
        this.camera.position.set(mapSize * 0.8, mapSize * 1.2, mapSize * 0.8);
        this.camera.lookAt(mapSize / 2, 0, mapSize / 2);

        // Renderer
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(width, height);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.containerRef.appendChild(this.renderer.domElement);

        // Controls
        if (OrbitControls) {
            this.controls = new OrbitControls(this.camera, this.renderer.domElement);
            this.controls.enableDamping = true;
            this.controls.dampingFactor = 0.05;
            this.controls.maxPolarAngle = Math.PI / 2;
        }

        // Raycaster for mouse picking
        this.raycaster = new THREE.Raycaster();
        this.mouse = new THREE.Vector2();

        // Lighting - cải thiện ánh sáng
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
        this.scene.add(ambientLight);

        const directionalLight1 = new THREE.DirectionalLight(0xffffff, 0.6);
        directionalLight1.position.set(20, 30, 20);
        directionalLight1.castShadow = true;
        this.scene.add(directionalLight1);
        
        const directionalLight2 = new THREE.DirectionalLight(0xffffff, 0.3);
        directionalLight2.position.set(-10, 20, -10);
        this.scene.add(directionalLight2);

        // Grid helper (if enabled)
        if (this.state.mapData?.show_grid) {
            const gridHelper = new THREE.GridHelper(50, 50);
            this.scene.add(gridHelper);
        }

        // Axes helper (if enabled)
        if (this.state.mapData?.show_axes) {
            const axesHelper = new THREE.AxesHelper(10);
            this.scene.add(axesHelper);
        }
    }

    render3DMap() {
        if (!this.state.mapData || !this.scene || !THREE) {
            console.log('Cannot render 3D map:', {
                hasMapData: !!this.state.mapData,
                hasScene: !!this.scene,
                hasTHREE: !!THREE
            });
            return;
        }

        const { columns, rows, levels, cell_width, cell_depth, cell_height, lots, blocked_cells } = this.state.mapData;

        // Clear previous meshes
        this.cellMeshes.forEach(mesh => this.scene.remove(mesh));
        this.cellMeshes = [];

        // Create cells
        for (let z = 0; z < levels; z++) {
            for (let y = 0; y < rows; y++) {
                for (let x = 0; x < columns; x++) {
                    const posKey = `${x}_${y}_${z}`;
                    const isBlocked = blocked_cells && blocked_cells[posKey];
                    const lotData = lots && lots[posKey];

                    // Skip if showing single level and this isn't it
                    if (!this.state.showAllLevels && z !== this.state.currentLevel) {
                        continue;
                    }

                    const geometry = new THREE.BoxGeometry(cell_width * 0.9, cell_height * 0.9, cell_depth * 0.9);
                    let material;

                    if (isBlocked) {
                        material = new THREE.MeshPhongMaterial({ 
                            color: 0x9E9E9E,
                            transparent: true,
                            opacity: 0.6,
                            shininess: 30
                        });
                    } else if (lotData) {
                        // Color based on quantity or availability - giống mẫu
                        const fillPercent = lotData.available_quantity / lotData.quantity;
                        let color, opacity;
                        
                        if (fillPercent <= 0.2) {
                            // Overload - Đỏ
                            color = 0xE53935;
                            opacity = 0.85;
                        } else if (fillPercent <= 0.5) {
                            // Almost Full - Vàng/Cam
                            color = 0xFFB300;
                            opacity = 0.85;
                        } else {
                            // Free Space Available - Xanh lá
                            color = 0x43A047;
                            opacity = 0.75;
                        }
                        
                        material = new THREE.MeshPhongMaterial({ 
                            color: color,
                            transparent: true,
                            opacity: opacity,
                            shininess: 40
                        });
                    } else {
                        // Empty cell - No Product/Load
                        material = new THREE.MeshPhongMaterial({ 
                            color: 0xBDBDBD,
                            transparent: true,
                            opacity: 0.3,
                            shininess: 10
                        });
                    }

                    const cube = new THREE.Mesh(geometry, material);
                    cube.position.set(
                        x * cell_width,
                        z * cell_height + cell_height / 2,
                        y * cell_depth
                    );

                    // Store metadata
                    cube.userData = {
                        x: x,
                        y: y,
                        z: z,
                        posKey: posKey,
                        lotData: lotData,
                        isBlocked: isBlocked
                    };

                    // Add edge helper for better visibility - đậm hơn
                    const edges = new THREE.EdgesGeometry(geometry);
                    const line = new THREE.LineSegments(
                        edges,
                        new THREE.LineBasicMaterial({ 
                            color: 0x333333,
                            linewidth: 2,
                            transparent: true,
                            opacity: 0.8
                        })
                    );
                    cube.add(line);

                    this.scene.add(cube);
                    this.cellMeshes.push(cube);

                    // Add labels if enabled
                    if (this.state.mapData.show_labels && lotData) {
                        this.addLabel(cube.position, lotData.product_code || lotData.lot_name);
                    }
                }
            }
        }
    }

    addLabel(position, text) {
        if (!text || text.length > 10) return; // Skip nếu text quá dài
        
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        canvas.width = 256;
        canvas.height = 128;
        
        // Background trong suốt
        context.clearRect(0, 0, canvas.width, canvas.height);
        
        // Text shadow cho độ nổi
        context.shadowColor = 'rgba(0, 0, 0, 0.5)';
        context.shadowBlur = 4;
        context.shadowOffsetX = 2;
        context.shadowOffsetY = 2;
        
        context.font = 'Bold 32px Arial';
        context.fillStyle = '#333333';
        context.textAlign = 'center';
        context.textBaseline = 'middle';
        context.fillText(text, canvas.width / 2, canvas.height / 2);
        
        const texture = new THREE.CanvasTexture(canvas);
        const spriteMaterial = new THREE.SpriteMaterial({ 
            map: texture,
            transparent: true,
            depthTest: false,
            depthWrite: false
        });
        const sprite = new THREE.Sprite(spriteMaterial);
        
        sprite.position.copy(position);
        sprite.position.y += 1.5;
        sprite.scale.set(1.5, 0.75, 1);
        
        this.scene.add(sprite);
        this.labelSprites.push(sprite);
    }

    animate() {
        if (!this.renderer || !this.scene || !this.camera) return;
        
        requestAnimationFrame(() => this.animate());
        
        if (this.controls) {
            this.controls.update();
        }
        
        this.renderer.render(this.scene, this.camera);
    }

    onWindowResize() {
        if (!this.containerRef || !this.camera || !this.renderer) return;

        const width = this.containerRef.clientWidth;
        const height = this.containerRef.clientHeight;

        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height);
    }

    onMouseClick(event) {
        if (!this.containerRef || !this.raycaster || !this.camera) return;

        const rect = this.containerRef.getBoundingClientRect();
        this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

        this.raycaster.setFromCamera(this.mouse, this.camera);
        const intersects = this.raycaster.intersectObjects(this.cellMeshes);

        if (intersects.length > 0) {
            const mesh = intersects[0].object;
            const userData = mesh.userData;
            
            this.state.selectedCell = userData;
            this.showCellInfo(userData);
        }
    }

    showCellInfo(cellData) {
        const { x, y, z, lotData, isBlocked } = cellData;
        
        let message = `Vị trí: (${x}, ${y}, ${z})`;
        
        if (isBlocked) {
            message += '\nÔ bị chặn';
        } else if (lotData) {
            message += `\nSản phẩm: ${lotData.product_name}`;
            message += `\nLot: ${lotData.lot_name}`;
            message += `\nSố lượng: ${lotData.quantity} ${lotData.uom}`;
            message += `\nKhả dụng: ${lotData.available_quantity} ${lotData.uom}`;
        } else {
            message += '\nÔ trống';
        }
        
        this.notification.add(message, { type: 'info' });
    }

    toggleLevel(level) {
        this.state.currentLevel = level;
        this.state.showAllLevels = false;
        this.render3DMap();
    }

    showAllLevels() {
        this.state.showAllLevels = true;
        this.render3DMap();
    }

    async refreshMap() {
        await this.loadMapData();
        this.render3DMap();
    }

    onWarehouseChange(event) {
        // Future: Load different warehouse map
        console.log('Warehouse changed:', event.target.value);
    }
    
    // Getter for template to create level array
    get levelsArray() {
        if (!this.state.mapData) return [];
        return Array.from({length: this.state.mapData.levels}, (_, i) => i);
    }

    disposeThreeJS() {
        if (this.renderer) {
            this.renderer.dispose();
            if (this.containerRef && this.renderer.domElement) {
                this.containerRef.removeChild(this.renderer.domElement);
            }
        }
        if (this.controls) {
            this.controls.dispose();
        }
        this.cellMeshes = [];
        this.labelSprites = [];
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
    }
}

WarehouseMap3DView.template = "warehouse_map.WarehouseMap3DView";

registry.category("actions").add("warehouse_map_3d_view", WarehouseMap3DView);
