/** @odoo-module **/

import { Component, useState, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

// Three.js sẽ được load từ CDN
let THREE = null;

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
            assignmentMode: false,  // Mode để gán vị trí từ wizard
            selectedPosition: null,  // Vị trí được chọn trong mode gán vị trí
        });

        // Three.js objects
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.raycaster = null;
        this.mouse = null;
        this.cellMeshes = [];
        this.labelSprites = [];
        this.containerRef = null;
        
        // Camera controls state
        this.isMouseDown = false;
        this.mouseX = 0;
        this.mouseY = 0;
        this.cameraRotation = { theta: Math.PI / 4, phi: Math.PI / 4 };
        this.cameraDistance = 30;
        this.autoRefreshInterval = null;  // Auto-refresh timer

        onWillStart(async () => {
            await this.loadThreeJS();
            await this.loadMapData();
            // Kiểm tra nếu trong chế độ gán vị trí từ wizard
            if (this.props.context?.move_line_warehouse_map_wizard_id) {
                this.state.assignmentMode = true;
            }
        });

        onMounted(() => {
            setTimeout(() => {
                if (this.state.mapData) {
                    this.initThreeJS();
                    this.render3DMap();
                    this.animate();
                    
                    // Handle window resize
                    this.resizeHandler = () => this.onWindowResize();
                    window.addEventListener('resize', this.resizeHandler);
                    
                    // Handle mouse events
                    if (this.containerRef) {
                        this.mouseDownHandler = (e) => this.onMouseDown(e);
                        this.mouseMoveHandler = (e) => this.onMouseMove(e);
                        this.mouseUpHandler = () => this.onMouseUp();
                        this.wheelHandler = (e) => this.onWheel(e);
                        this.clickHandler = (e) => this.onMouseClick(e);
                        
                        this.containerRef.addEventListener('mousedown', this.mouseDownHandler);
                        this.containerRef.addEventListener('mousemove', this.mouseMoveHandler);
                        this.containerRef.addEventListener('mouseup', this.mouseUpHandler);
                        this.containerRef.addEventListener('wheel', this.wheelHandler);
                        this.containerRef.addEventListener('click', this.clickHandler);
                    }
                    
                    // Auto-refresh map data mỗi 3 giây để cập nhật thay đổi
                    this.autoRefreshInterval = setInterval(() => {
                        this.refreshMapData();
                    }, 3000);
                }
            }, 0);
        });

        onWillUnmount(() => {
            // Clear auto-refresh interval
            if (this.autoRefreshInterval) {
                clearInterval(this.autoRefreshInterval);
                this.autoRefreshInterval = null;
            }
            
            if (this.resizeHandler) {
                window.removeEventListener('resize', this.resizeHandler);
            }
            if (this.containerRef) {
                if (this.mouseDownHandler) this.containerRef.removeEventListener('mousedown', this.mouseDownHandler);
                if (this.mouseMoveHandler) this.containerRef.removeEventListener('mousemove', this.mouseMoveHandler);
                if (this.mouseUpHandler) this.containerRef.removeEventListener('mouseup', this.mouseUpHandler);
                if (this.wheelHandler) this.containerRef.removeEventListener('wheel', this.wheelHandler);
                if (this.clickHandler) this.containerRef.removeEventListener('click', this.clickHandler);
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
        if (window.THREE) {
            THREE = window.THREE;
            return;
        }

        try {
            return new Promise((resolve, reject) => {
                const script = document.createElement('script');
                script.src = 'https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.min.js';
                script.onload = () => {
                    THREE = window.THREE;
                    console.log('Three.js loaded successfully');
                    resolve();
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

        // Camera
        this.camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 1000);
        const mapSize = Math.max(this.state.mapData?.columns || 10, this.state.mapData?.rows || 10) * (this.state.mapData?.cell_width || 1.2);
        this.camera.position.set(mapSize * 0.8, mapSize * 1.2, mapSize * 0.8);
        this.camera.lookAt(mapSize / 2, 0, mapSize / 2);

        // Renderer
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(width, height);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.containerRef.appendChild(this.renderer.domElement);

        // Raycaster for mouse picking
        this.raycaster = new THREE.Raycaster();
        this.mouse = new THREE.Vector2();
        
        // Update camera position based on rotation
        this.updateCameraPosition();

        // Lighting
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
        this.scene.add(ambientLight);

        const directionalLight1 = new THREE.DirectionalLight(0xffffff, 0.6);
        directionalLight1.position.set(20, 30, 20);
        directionalLight1.castShadow = true;
        this.scene.add(directionalLight1);
        
        const directionalLight2 = new THREE.DirectionalLight(0xffffff, 0.3);
        directionalLight2.position.set(-10, 20, -10);
        this.scene.add(directionalLight2);

        // Grid helper
        if (this.state.mapData?.show_grid) {
            const gridHelper = new THREE.GridHelper(50, 50);
            this.scene.add(gridHelper);
        }

        // Axes helper
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

        console.log('=== RENDER 3D MAP ===');
        console.log('lots structure:', lots);
        console.log('lots type:', typeof lots);
        console.log('lots is Array?', Array.isArray(lots));
        if (lots && Object.keys(lots).length > 0) {
            const firstKey = Object.keys(lots)[0];
            console.log('First lot key:', firstKey);
            console.log('First lot value:', lots[firstKey]);
        }
        console.log('====================');

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
                        const fillPercent = lotData.available_quantity / lotData.quantity;
                        let color, opacity;
                        
                        if (fillPercent <= 0.2) {
                            color = 0xE53935;
                            opacity = 0.85;
                        } else if (fillPercent <= 0.5) {
                            color = 0xFFB300;
                            opacity = 0.85;
                        } else {
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

                    // Add edge helper
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
        if (!text || text.length > 10) return;
        
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        canvas.width = 256;
        canvas.height = 128;
        
        context.clearRect(0, 0, canvas.width, canvas.height);
        
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
        
        this.renderer.render(this.scene, this.camera);
    }
    
    updateCameraPosition() {
        if (!this.camera) return;
        
        const mapSize = Math.max(this.state.mapData?.columns || 10, this.state.mapData?.rows || 10) * (this.state.mapData?.cell_width || 1.2);
        const centerX = mapSize / 2;
        const centerZ = mapSize / 2;
        
        const x = centerX + this.cameraDistance * Math.sin(this.cameraRotation.theta) * Math.cos(this.cameraRotation.phi);
        const y = this.cameraDistance * Math.sin(this.cameraRotation.phi);
        const z = centerZ + this.cameraDistance * Math.cos(this.cameraRotation.theta) * Math.cos(this.cameraRotation.phi);
        
        this.camera.position.set(x, y, z);
        this.camera.lookAt(centerX, 0, centerZ);
    }
    
    onMouseDown(event) {
        this.isMouseDown = true;
        this.mouseX = event.clientX;
        this.mouseY = event.clientY;
    }
    
    onMouseMove(event) {
        if (!this.isMouseDown) return;
        
        const deltaX = event.clientX - this.mouseX;
        const deltaY = event.clientY - this.mouseY;
        
        this.cameraRotation.theta -= deltaX * 0.01;
        this.cameraRotation.phi -= deltaY * 0.01;
        
        this.cameraRotation.phi = Math.max(0.1, Math.min(Math.PI / 2 - 0.1, this.cameraRotation.phi));
        
        this.mouseX = event.clientX;
        this.mouseY = event.clientY;
        
        this.updateCameraPosition();
    }
    
    onMouseUp() {
        this.isMouseDown = false;
    }
    
    onWheel(event) {
        event.preventDefault();
        
        this.cameraDistance += event.deltaY * 0.05;
        this.cameraDistance = Math.max(10, Math.min(100, this.cameraDistance));
        
        this.updateCameraPosition();
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
            
            console.log('=== CLICKED CELL ===');
            console.log('Position:', `(${userData.x}, ${userData.y}, ${userData.z})`);
            console.log('posKey:', userData.posKey);
            console.log('lotData:', userData.lotData);
            console.log('isBlocked:', userData.isBlocked);
            console.log('====== END ======');
            
            this.state.selectedCell = userData;
            
            if (this.state.assignmentMode) {
                // Trong chế độ gán vị trí từ wizard, phải chọn lô có hàng
                this.showLotSelectionForAssignment(userData);
            } else {
                // Chế độ bình thường, hiển thị thông tin ô
                this.showCellInfo(userData);
            }
        }
    }

    showLotSelectionForAssignment(cellData) {
        const { x, y, z, lotData, isBlocked } = cellData;
        
        // Nếu ô bị chặn
        if (isBlocked) {
            this.notification.add('Ô này bị chặn! Vui lòng chọn ô khác.', { type: 'warning' });
            return;
        }
        
        // Nếu ô trống, không thể gán
        if (!lotData) {
            this.notification.add('Ô này trống. Vui lòng chọn ô có lô để gán vị trí.', { type: 'warning' });
            return;
        }
        
        // Ô có lô, hiển thị thông tin lô để chọn gán
        this.showLotConfirmDialog(cellData);
    }

    showLotConfirmDialog(cellData) {
        const { x, y, z, lotData } = cellData;
        
        // Tạo dialog xác nhận chọn lô
        const dialog = document.createElement('div');
        dialog.className = 'warehouse-map-3d-confirm-dialog';
        dialog.innerHTML = `
            <div class="dialog-content">
                <h3>Chọn lô để gán vị trí 3D</h3>
                <div class="lot-selection-info">
                    <p><strong>Sản phẩm:</strong> ${lotData.product_name}</p>
                    <p><strong>Lot/Serial:</strong> ${lotData.lot_name}</p>
                    <p><strong>Số lượng:</strong> ${lotData.quantity} ${lotData.uom}</p>
                    <p><strong>Vị trí mới:</strong> (${x}, ${y}, ${z})</p>
                </div>
                <p style="color: #666; margin: 10px 0;">Bạn có muốn gán lô này vào vị trí (${x}, ${y}, ${z})?</p>
                <div class="dialog-buttons">
                    <button class="btn-confirm">Chọn lô này</button>
                    <button class="btn-cancel">Hủy</button>
                </div>
            </div>
        `;
        
        const style = document.createElement('style');
        style.textContent = `
            .warehouse-map-3d-confirm-dialog {
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: white;
                border: 2px solid #3498db;
                border-radius: 6px;
                padding: 25px;
                z-index: 10000;
                box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                min-width: 400px;
            }
            .warehouse-map-3d-confirm-dialog h3 {
                margin-top: 0;
                margin-bottom: 20px;
                color: #2c3e50;
                font-size: 18px;
                border-bottom: 2px solid #3498db;
                padding-bottom: 10px;
            }
            .warehouse-map-3d-confirm-dialog .lot-selection-info {
                background: #ecf0f1;
                padding: 15px;
                border-radius: 4px;
                margin: 15px 0;
            }
            .warehouse-map-3d-confirm-dialog .lot-selection-info p {
                margin: 8px 0;
                color: #333;
            }
            .warehouse-map-3d-confirm-dialog p {
                margin: 10px 0;
                color: #666;
            }
            .warehouse-map-3d-confirm-dialog .dialog-buttons {
                margin-top: 20px;
                display: flex;
                gap: 10px;
                justify-content: flex-end;
            }
            .warehouse-map-3d-confirm-dialog button {
                padding: 10px 20px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
                font-weight: 500;
            }
            .warehouse-map-3d-confirm-dialog .btn-confirm {
                background-color: #27ae60;
                color: white;
            }
            .warehouse-map-3d-confirm-dialog .btn-confirm:hover {
                background-color: #229954;
            }
            .warehouse-map-3d-confirm-dialog .btn-cancel {
                background-color: #95a5a6;
                color: white;
            }
            .warehouse-map-3d-confirm-dialog .btn-cancel:hover {
                background-color: #7f8c8d;
            }
        `;
        
        document.head.appendChild(style);
        document.body.appendChild(dialog);
        
        // Xử lý click nút xác nhận chọn lô
        dialog.querySelector('.btn-confirm').onclick = () => {
            this.confirmLotSelection(cellData);
            dialog.remove();
        };
        
        // Xử lý click nút hủy
        dialog.querySelector('.btn-cancel').onclick = () => {
            dialog.remove();
        };
    }

    confirmLotSelection(cellData) {
        const { x, y, z, lotData } = cellData;
        const wizardId = this.props.context?.move_line_warehouse_map_wizard_id;
        
        if (!wizardId) {
            this.notification.add('Lỗi: Không tìm thấy wizard ID.', { type: 'danger' });
            return;
        }
        
        // Gọi Odoo RPC để cập nhật vị trí và lô trong wizard
        this.orm.call('move.line.warehouse.map.wizard', 'update_position_from_3d_view', [wizardId], {
            posx: x,
            posy: y,
            posz: z,
            quant_id: lotData.quant_id,  // Gửi ID lô được chọn
        }).then(result => {
            this.notification.add(`✓ Lô ${lotData.lot_name} được gán vị trí thành công!`, { type: 'success' });
            // Đóng action/wizard sau khi gán vị trí
            setTimeout(() => {
                this.action.doAction({
                    type: 'ir.actions.act_window_close',
                });
            }, 500);
        }).catch(error => {
            this.notification.add(`Lỗi khi gán vị trí: ${error.message}`, { type: 'danger' });
        });
    }

    showCellInfo(cellData) {
        const { x, y, z, lotData, isBlocked } = cellData;
        
        // Tạo dialog hiển thị thông tin ô
        const dialog = document.createElement('div');
        dialog.className = 'warehouse-map-3d-info-dialog';
        
        let content = `<div class="dialog-content">
            <h3>📍 Thông tin vị trí (${x}, ${y}, ${z})</h3>`;
        
        if (isBlocked) {
            content += '<p class="blocked-info">🚫 Ô này bị chặn</p>';
        } else if (lotData) {
            content += `
                <div class="lot-info">
                    <p><strong>Sản phẩm:</strong> ${lotData.product_name}</p>
                    <p><strong>Lot/Serial:</strong> ${lotData.lot_name}</p>
                    <p><strong>Số lượng:</strong> ${lotData.quantity} ${lotData.uom}</p>
                    <p><strong>Khả dụng:</strong> ${lotData.available_quantity} ${lotData.uom}</p>
                    ${lotData.location_name ? `<p><strong>Vị trí kho:</strong> ${lotData.location_name}</p>` : ''}
                </div>
                <div class="action-buttons">
                    <button class="btn-action btn-move" data-action="move" data-quant-id="${lotData.quant_id}">
                        📦 Chuyển vị trí
                    </button>
                    <button class="btn-action btn-pick" data-action="pick" data-quant-id="${lotData.quant_id}">
                        🛒 Lấy hàng
                    </button>
                    <button class="btn-action btn-transfer" data-action="transfer" data-quant-id="${lotData.quant_id}">
                        🚚 Chuyển kho
                    </button>
                </div>
            `;
        } else {
            content += `
                <p class="empty-info">✓ Ô trống - sẵn sàng gán vị trí</p>
                <div class="action-buttons">
                    <button class="btn-action btn-assign-position" data-pos-x="${x}" data-pos-y="${y}" data-pos-z="${z}">
                        ➕ Chọn lô để gán
                    </button>
                </div>
            `;
        }
        
        content += '<div class="dialog-buttons"><button class="btn-close">Đóng</button></div></div>';
        
        dialog.innerHTML = content;
        
        // Thêm CSS styling nếu chưa có
        if (!document.getElementById('warehouse-map-info-dialog-style')) {
            const style = document.createElement('style');
            style.id = 'warehouse-map-info-dialog-style';
            style.textContent = `
                .warehouse-map-3d-info-dialog {
                    position: fixed;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    background: white;
                    border: 2px solid #2c3e50;
                    border-radius: 8px;
                    padding: 20px;
                    z-index: 10000;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.3);
                    min-width: 450px;
                    max-height: 80vh;
                    overflow-y: auto;
                }
                .warehouse-map-3d-info-dialog .dialog-content {
                    display: flex;
                    flex-direction: column;
                    gap: 15px;
                }
                .warehouse-map-3d-info-dialog h3 {
                    margin: 0 0 10px 0;
                    color: #2c3e50;
                    font-size: 18px;
                    border-bottom: 2px solid #3498db;
                    padding-bottom: 10px;
                }
                .warehouse-map-3d-info-dialog .lot-info,
                .warehouse-map-3d-info-dialog .blocked-info,
                .warehouse-map-3d-info-dialog .empty-info {
                    padding: 12px;
                    border-radius: 4px;
                    background: #f8f9fa;
                }
                .warehouse-map-3d-info-dialog .lot-info p {
                    margin: 8px 0;
                    color: #333;
                }
                .warehouse-map-3d-info-dialog .blocked-info {
                    background: #ffe6e6;
                    color: #d32f2f;
                    font-weight: bold;
                }
                .warehouse-map-3d-info-dialog .empty-info {
                    background: #e8f5e9;
                    color: #388e3c;
                    font-weight: bold;
                }
                .warehouse-map-3d-info-dialog .action-buttons {
                    display: flex;
                    gap: 10px;
                    margin-top: 10px;
                    justify-content: center;
                }
                .warehouse-map-3d-info-dialog .action-buttons.multi {
                    display: grid;
                    grid-template-columns: 1fr 1fr 1fr;
                }
                .warehouse-map-3d-info-dialog .btn-action {
                    padding: 10px 12px;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 13px;
                    font-weight: 500;
                    transition: all 0.2s ease;
                    white-space: nowrap;
                    flex: 1;
                }
                .warehouse-map-3d-info-dialog .btn-move {
                    background-color: #3498db;
                    color: white;
                    flex: 1;
                }
                .warehouse-map-3d-info-dialog .btn-move:hover {
                    background-color: #2980b9;
                    transform: translateY(-2px);
                }
                .warehouse-map-3d-info-dialog .btn-pick {
                    background-color: #f39c12;
                    color: white;
                    flex: 1;
                }
                .warehouse-map-3d-info-dialog .btn-pick:hover {
                    background-color: #e67e22;
                    transform: translateY(-2px);
                }
                .warehouse-map-3d-info-dialog .btn-transfer {
                    background-color: #27ae60;
                    color: white;
                    flex: 1;
                }
                .warehouse-map-3d-info-dialog .btn-transfer:hover {
                    background-color: #229954;
                    transform: translateY(-2px);
                }
                .warehouse-map-3d-info-dialog .btn-assign-position {
                    background-color: #9b59b6;
                    color: white;
                    padding: 12px 20px;
                    font-size: 14px;
                }
                .warehouse-map-3d-info-dialog .btn-assign-position:hover {
                    background-color: #8e44ad;
                    transform: translateY(-2px);
                }
                .warehouse-map-3d-info-dialog .dialog-buttons {
                    display: flex;
                    gap: 10px;
                    justify-content: flex-end;
                    margin-top: 15px;
                    padding-top: 15px;
                    border-top: 1px solid #ddd;
                }
                .warehouse-map-3d-info-dialog .btn-close {
                    padding: 8px 20px;
                    background-color: #6c757d;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 14px;
                    font-weight: 500;
                }
                .warehouse-map-3d-info-dialog .btn-close:hover {
                    background-color: #5a6268;
                }
            `;
            document.head.appendChild(style);
        }
        
        document.body.appendChild(dialog);
        
        // Xử lý click nút hành động cho lô có sẵn
        dialog.querySelectorAll('.btn-action').forEach(btn => {
            btn.onclick = (e) => {
                const action = e.target.closest('.btn-action').dataset.action;
                if (action) {
                    // Hành động cho lô có sẵn
                    const quantId = parseInt(e.target.closest('.btn-action').dataset.quantId);
                    dialog.remove();
                    this.executeQuantAction(action, quantId);
                } else {
                    // Gán vị trí cho ô trống - mở wizard với tọa độ pre-filled
                    const posX = parseInt(e.target.closest('.btn-action').dataset.posX);
                    const posY = parseInt(e.target.closest('.btn-action').dataset.posY);
                    const posZ = parseInt(e.target.closest('.btn-action').dataset.posZ);
                    dialog.remove();
                    this.openAssignPositionWizard(posX, posY, posZ);
                }
            };
        });
        
        // Đóng dialog khi click nút
        dialog.querySelector('.btn-close').onclick = () => {
            dialog.remove();
        };
        
        // Đóng dialog khi click bên ngoài
        dialog.onclick = (e) => {
            if (e.target === dialog) {
                dialog.remove();
            }
        };
    }

    openAssignPositionWizard(posX, posY, posZ) {
        // Mở wizard để chọn lô và gán vị trí với tọa độ đã được pre-fill
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: `Gán Lot vào vị trí [${posX}, ${posY}]`,
            res_model: 'move.line.warehouse.map.wizard',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'new',
            context: {
                'default_posx': posX,
                'default_posy': posY,
                'default_posz': posZ,
                'warehouse_map_3d_assign': true,
                'default_view_mode': 'warehouse_map_3d'
            },
        });
    }

    executeQuantAction(action, quantId) {
        if (action === 'move') {
            this.orm.call('stock.quant', 'action_move_location', [quantId], {}).then(result => {
                if (result) {
                    this.action.doAction(result);
                }
            }).catch(error => {
                this.notification.add(`Lỗi: ${error.message}`, { type: 'danger' });
            });
        } else if (action === 'pick') {
            this.orm.call('stock.quant', 'action_pick_products', [quantId], {}).then(result => {
                if (result) {
                    this.action.doAction(result);
                }
            }).catch(error => {
                this.notification.add(`Lỗi: ${error.message}`, { type: 'danger' });
            });
        } else if (action === 'transfer') {
            this.orm.call('stock.quant', 'action_transfer_warehouse', [quantId], {}).then(result => {
                if (result) {
                    this.action.doAction(result);
                }
            }).catch(error => {
                this.notification.add(`Lỗi: ${error.message}`, { type: 'danger' });
            });
        }
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

    async refreshMapData() {
        // Silently refresh map data mỗi vài giây để cập nhật thay đổi
        try {
            let mapId = this.getMapId();
            if (!mapId && this.state.mapData?.id) {
                mapId = this.state.mapData.id;
            }
            
            console.log('Refreshing map data - mapId:', mapId, 'state.mapData:', this.state.mapData);
            
            if (!mapId) {
                console.warn('No mapId found for refresh');
                return;
            }
            
            const data = await this.orm.call(
                'warehouse.map.3d',
                'get_map_3d_data',
                [mapId]
            );
            
            console.log('Refreshed lots data:', data.lots);
            
            // Chỉ cập nhật nếu dữ liệu thay đổi
            if (JSON.stringify(data.lots) !== JSON.stringify(this.state.mapData?.lots)) {
                console.log('Lots data changed, updating map');
                this.state.mapData = data;
                this.render3DMap();
            } else {
                console.log('Lots data unchanged');
            }
        } catch (error) {
            // Silently fail - không show error notification
            console.log('Auto-refresh failed:', error);
        }
    }

    onWarehouseChange(event) {
        console.log('Warehouse changed:', event.target.value);
    }
    
    get levelsArray() {
        if (!this.state.mapData) return [];
        return Array.from({length: this.state.mapData.levels}, (_, i) => i);
    }

    onWindowResize() {
        if (!this.containerRef || !this.camera || !this.renderer) return;

        const width = this.containerRef.clientWidth;
        const height = this.containerRef.clientHeight;

        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height);
    }

    disposeThreeJS() {
        if (this.renderer) {
            this.renderer.dispose();
            if (this.containerRef && this.renderer.domElement) {
                this.containerRef.removeChild(this.renderer.domElement);
            }
        }
        this.cellMeshes = [];
        this.labelSprites = [];
        this.scene = null;
        this.camera = null;
        this.renderer = null;
    }
}

WarehouseMap3DView.template = "warehouse_map.WarehouseMap3DView";

registry.category("actions").add("warehouse_map_3d_view", WarehouseMap3DView);
