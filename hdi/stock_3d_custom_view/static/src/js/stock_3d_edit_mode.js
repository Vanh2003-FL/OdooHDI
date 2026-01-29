/** @odoo-module **/

/**
 * Enhanced 3D Form View with Edit Mode
 * Cho phép edit vị trí trực tiếp trên 3D scene
 * - Drag-drop repositioning
 * - Add/Edit/Delete locations
 * - Properties panel
 * - Save/Cancel
 */

import { Component, onWillStart, onMounted, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

export class Stock3DEditMode {
    constructor(scene, data, camera, renderer) {
        this.scene = scene;
        this.data = data;
        this.camera = camera;
        this.renderer = renderer;
        
        this.isEditMode = false;
        this.selectedObject = null;
        this.draggedObject = null;
        this.dragPlane = null;
        this.raycaster = new THREE.Raycaster();
        this.mouse = new THREE.Vector2();
        
        this.undoStack = [];
        this.redoStack = [];
        
        this.locationsList = [];  // All locations data
    }
    
    /**
     * Bật/tắt Edit Mode
     */
    toggleEditMode() {
        this.isEditMode = !this.isEditMode;
        console.log(`Edit Mode: ${this.isEditMode ? 'ON' : 'OFF'}`);
        
        if (this.isEditMode) {
            this.enableEditMode();
        } else {
            this.disableEditMode();
        }
        
        return this.isEditMode;
    }
    
    enableEditMode() {
        // Thêm event listeners
        this.renderer.domElement.addEventListener('click', (e) => this.onCanvasClick(e));
        this.renderer.domElement.addEventListener('mousemove', (e) => this.onMouseMove(e));
        this.renderer.domElement.addEventListener('mousedown', (e) => this.onMouseDown(e));
        this.renderer.domElement.addEventListener('mouseup', (e) => this.onMouseUp(e));
        
        // Highlight tất cả editable objects
        this.scene.children.forEach(child => {
            if (child.userData.loc_id) {
                child.material.transparent = true;
                child.material.opacity = 0.6;
            }
        });
        
        // Show edit toolbar
        this.showEditToolbar();
    }
    
    disableEditMode() {
        // Xóa event listeners
        this.renderer.domElement.removeEventListener('click', (e) => this.onCanvasClick(e));
        this.renderer.domElement.removeEventListener('mousemove', (e) => this.onMouseMove(e));
        this.renderer.domElement.removeEventListener('mousedown', (e) => this.onMouseDown(e));
        this.renderer.domElement.removeEventListener('mouseup', (e) => this.onMouseUp(e));
        
        // Deselect
        this.deselect();
        
        // Hide edit toolbar & properties panel
        this.hideEditToolbar();
        this.hidePropertiesPanel();
    }
    
    /**
     * Click trên canvas để chọn location
     */
    onCanvasClick(event) {
        // Tính toán mouse position
        const rect = this.renderer.domElement.getBoundingClientRect();
        this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
        
        // Ray casting
        this.raycaster.setFromCamera(this.mouse, this.camera);
        const intersects = this.raycaster.intersectObjects(this.scene.children);
        
        if (intersects.length > 0) {
            const clickedObject = intersects[0].object;
            
            if (clickedObject.userData.loc_id) {
                this.selectObject(clickedObject);
            }
        } else {
            this.deselect();
        }
    }
    
    /**
     * Chọn 1 location object
     */
    selectObject(obj) {
        // Deselect previous
        if (this.selectedObject) {
            this.selectedObject.material.color.set(this.selectedObject.userData.color);
            this.selectedObject.material.emissive.setHex(0x000000);
        }
        
        // Select new
        this.selectedObject = obj;
        obj.material.color.set(0x00ffff);  // Cyan
        obj.material.emissive.setHex(0x00ffff);
        obj.material.emissiveIntensity = 0.5;
        
        // Hiển thị properties panel
        this.showPropertiesPanel(obj.userData);
    }
    
    /**
     * Bỏ chọn
     */
    deselect() {
        if (this.selectedObject) {
            this.selectedObject.material.color.set(this.selectedObject.userData.color);
            this.selectedObject.material.emissive.setHex(0x000000);
            this.selectedObject = null;
        }
        this.hidePropertiesPanel();
    }
    
    /**
     * Mouse down - bắt đầu drag
     */
    onMouseDown(event) {
        if (!this.selectedObject) return;
        
        // Lưu state vào undo stack
        this.saveUndoState(this.selectedObject);
        
        this.draggedObject = this.selectedObject;
        
        // Tạo drag plane (Y = 0)
        const planeNormal = new THREE.Vector3(0, 1, 0);
        this.dragPlane = new THREE.Plane(planeNormal, 0);
        
        this.renderer.domElement.style.cursor = 'grabbing';
    }
    
    /**
     * Mouse move - drag object
     */
    onMouseMove(event) {
        if (!this.draggedObject) return;
        
        const rect = this.renderer.domElement.getBoundingClientRect();
        this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
        
        // Tính intersection với drag plane
        this.raycaster.setFromCamera(this.mouse, this.camera);
        const intersection = new THREE.Vector3();
        this.raycaster.ray.intersectPlane(this.dragPlane, intersection);
        
        // Update position
        this.draggedObject.position.x = intersection.x;
        this.draggedObject.position.z = intersection.z;
        
        // Update properties panel real-time
        this.updatePropertiesPanelValues({
            pos_x: intersection.x,
            pos_y: intersection.y,
            pos_z: intersection.z
        });
    }
    
    /**
     * Mouse up - kết thúc drag
     */
    onMouseUp(event) {
        if (this.draggedObject) {
            this.draggedObject = null;
            this.renderer.domElement.style.cursor = 'default';
        }
    }
    
    /**
     * Hiển thị Properties Panel
     */
    showPropertiesPanel(data) {
        let panel = document.getElementById('properties-panel');
        
        if (!panel) {
            panel = document.createElement('div');
            panel.id = 'properties-panel';
            panel.className = 'properties-panel';
            document.querySelector('.o_content').appendChild(panel);
        }
        
        const html = `
            <div class="properties-header">
                <h4>Location Properties</h4>
                <button class="btn-close" onclick="this.parentElement.parentElement.style.display='none'">×</button>
            </div>
            <div class="properties-body">
                <div class="form-group">
                    <label>Location Code:</label>
                    <input type="text" id="prop-code" value="${data.location_code || ''}" placeholder="e.g., LOC-001" />
                </div>
                
                <div class="form-row">
                    <div class="form-group">
                        <label>X Position:</label>
                        <input type="number" id="prop-pos-x" value="${data.pos_x || 0}" step="10" />
                    </div>
                    <div class="form-group">
                        <label>Y Position:</label>
                        <input type="number" id="prop-pos-y" value="${data.pos_y || 0}" step="10" />
                    </div>
                    <div class="form-group">
                        <label>Z Position:</label>
                        <input type="number" id="prop-pos-z" value="${data.pos_z || 0}" step="10" />
                    </div>
                </div>
                
                <div class="form-row">
                    <div class="form-group">
                        <label>Length (m):</label>
                        <input type="number" id="prop-length" value="${data.length || 1}" step="0.1" min="0.1" />
                    </div>
                    <div class="form-group">
                        <label>Width (m):</label>
                        <input type="number" id="prop-width" value="${data.width || 1}" step="0.1" min="0.1" />
                    </div>
                    <div class="form-group">
                        <label>Height (m):</label>
                        <input type="number" id="prop-height" value="${data.height || 1}" step="0.1" min="0.1" />
                    </div>
                </div>
                
                <div class="form-group">
                    <label>Max Capacity (units):</label>
                    <input type="number" id="prop-capacity" value="${data.max_capacity || 0}" step="1" min="0" />
                </div>
                
                <div class="properties-footer">
                    <button class="btn btn-primary" onclick="this.saveLocationProperties()">
                        💾 Save Location
                    </button>
                    <button class="btn btn-danger" onclick="this.deleteLocation()">
                        🗑️ Delete
                    </button>
                </div>
            </div>
        `;
        
        panel.innerHTML = html;
        panel.style.display = 'block';
        
        // Attach event listeners
        document.getElementById('prop-length')?.addEventListener('change', 
            (e) => this.updateGeometry(this.selectedObject, 'length', parseFloat(e.target.value)));
        
        document.getElementById('prop-width')?.addEventListener('change', 
            (e) => this.updateGeometry(this.selectedObject, 'width', parseFloat(e.target.value)));
        
        document.getElementById('prop-height')?.addEventListener('change', 
            (e) => this.updateGeometry(this.selectedObject, 'height', parseFloat(e.target.value)));
    }
    
    /**
     * Cập nhật values trên properties panel real-time (khi drag)
     */
    updatePropertiesPanelValues(values) {
        if (values.pos_x !== undefined) {
            const input = document.getElementById('prop-pos-x');
            if (input) input.value = Math.round(values.pos_x);
        }
        if (values.pos_y !== undefined) {
            const input = document.getElementById('prop-pos-y');
            if (input) input.value = Math.round(values.pos_y);
        }
        if (values.pos_z !== undefined) {
            const input = document.getElementById('prop-pos-z');
            if (input) input.value = Math.round(values.pos_z);
        }
    }
    
    /**
     * Cập nhật geometry của location (thay đổi kích thước)
     */
    updateGeometry(obj, dimension, value) {
        if (!obj) return;
        
        const scale = 7.558;  // conversion factor
        const scaledValue = value * scale;
        
        // Update geometry
        if (dimension === 'length') {
            obj.geometry.scale(scaledValue / obj.userData.length_px, 1, 1);
            obj.userData.length_px = scaledValue;
            obj.userData.length = value;
        } else if (dimension === 'width') {
            obj.geometry.scale(1, 1, scaledValue / obj.userData.width_px);
            obj.userData.width_px = scaledValue;
            obj.userData.width = value;
        } else if (dimension === 'height') {
            obj.geometry.scale(1, scaledValue / obj.userData.height_px, 1);
            obj.userData.height_px = scaledValue;
            obj.userData.height = value;
        }
    }
    
    /**
     * Ẩn properties panel
     */
    hidePropertiesPanel() {
        const panel = document.getElementById('properties-panel');
        if (panel) panel.style.display = 'none';
    }
    
    /**
     * Hiển thị edit toolbar
     */
    showEditToolbar() {
        if (document.getElementById('edit-toolbar')) return;
        
        const toolbar = document.createElement('div');
        toolbar.id = 'edit-toolbar';
        toolbar.className = 'edit-toolbar';
        toolbar.innerHTML = `
            <button class="btn btn-success" title="Add new location">
                ➕ Add Location
            </button>
            <button class="btn btn-warning" title="Undo changes">
                ↶ Undo
            </button>
            <button class="btn btn-warning" title="Redo changes">
                ↷ Redo
            </button>
            <button class="btn btn-primary" title="Save all changes">
                💾 Save
            </button>
            <button class="btn btn-secondary" title="Exit edit mode">
                ❌ Cancel
            </button>
        `;
        
        document.querySelector('.o_content').insertBefore(
            toolbar,
            document.querySelector('.o_content').firstChild
        );
        
        // Attach events
        toolbar.querySelectorAll('button')[0].addEventListener('click', () => this.showAddLocationDialog());
        toolbar.querySelectorAll('button')[1].addEventListener('click', () => this.undo());
        toolbar.querySelectorAll('button')[2].addEventListener('click', () => this.redo());
        toolbar.querySelectorAll('button')[3].addEventListener('click', () => this.saveAllChanges());
        toolbar.querySelectorAll('button')[4].addEventListener('click', () => this.toggleEditMode());
    }
    
    /**
     * Ẩn edit toolbar
     */
    hideEditToolbar() {
        document.getElementById('edit-toolbar')?.remove();
    }
    
    /**
     * Dialog để thêm location mới
     */
    showAddLocationDialog() {
        const dialog = document.createElement('div');
        dialog.className = 'modal modal-edit-location';
        dialog.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Add New Location</h3>
                    <button class="btn-close">×</button>
                </div>
                <div class="modal-body">
                    <div class="form-group">
                        <label>Location Code (required):</label>
                        <input type="text" id="new-code" placeholder="e.g., LOC-001" required />
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label>X Position:</label>
                            <input type="number" id="new-x" value="0" step="10" />
                        </div>
                        <div class="form-group">
                            <label>Y Position:</label>
                            <input type="number" id="new-y" value="0" step="10" />
                        </div>
                        <div class="form-group">
                            <label>Z Position:</label>
                            <input type="number" id="new-z" value="0" step="10" />
                        </div>
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label>Length (m):</label>
                            <input type="number" id="new-length" value="1" step="0.1" min="0.1" />
                        </div>
                        <div class="form-group">
                            <label>Width (m):</label>
                            <input type="number" id="new-width" value="1" step="0.1" min="0.1" />
                        </div>
                        <div class="form-group">
                            <label>Height (m):</label>
                            <input type="number" id="new-height" value="1" step="0.1" min="0.1" />
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Max Capacity:</label>
                        <input type="number" id="new-capacity" value="100" step="1" min="0" />
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-primary" id="btn-create-location">Create</button>
                    <button class="btn btn-secondary" id="btn-cancel-location">Cancel</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(dialog);
        
        dialog.querySelector('.btn-close').addEventListener('click', () => dialog.remove());
        dialog.querySelector('#btn-cancel-location').addEventListener('click', () => dialog.remove());
        dialog.querySelector('#btn-create-location').addEventListener('click', () => {
            this.createNewLocation({
                code: document.getElementById('new-code').value,
                pos_x: parseFloat(document.getElementById('new-x').value),
                pos_y: parseFloat(document.getElementById('new-y').value),
                pos_z: parseFloat(document.getElementById('new-z').value),
                length: parseFloat(document.getElementById('new-length').value),
                width: parseFloat(document.getElementById('new-width').value),
                height: parseFloat(document.getElementById('new-height').value),
                capacity: parseInt(document.getElementById('new-capacity').value)
            });
            dialog.remove();
        });
    }
    
    /**
     * Tạo location mới trên 3D scene
     */
    async createNewLocation(data) {
        const scale = 7.558;
        
        const geometry = new THREE.BoxGeometry(
            data.length * scale,
            data.height * scale,
            data.width * scale
        );
        geometry.translate(0, (data.height * scale) / 2, 0);
        
        const material = new THREE.MeshBasicMaterial({
            color: 0x00802b,  // Green
            transparent: true,
            opacity: 0.6
        });
        
        const mesh = new THREE.Mesh(geometry, material);
        mesh.position.set(data.pos_x, data.pos_y, data.pos_z);
        
        mesh.userData = {
            location_code: data.code,
            pos_x: data.pos_x,
            pos_y: data.pos_y,
            pos_z: data.pos_z,
            length: data.length,
            width: data.width,
            height: data.height,
            length_px: data.length * scale,
            width_px: data.width * scale,
            height_px: data.height * scale,
            max_capacity: data.capacity,
            color: 0x00802b,
            is_new: true
        };
        
        this.scene.add(mesh);
        this.selectObject(mesh);
        
        console.log('New location created:', data.code);
    }
    
    /**
     * Xóa location (bỏ khỏi scene)
     */
    deleteLocation() {
        if (!this.selectedObject) return;
        
        if (confirm('Bạn chắc chắn muốn xóa vị trí này?')) {
            const toRemove = this.selectedObject;
            this.scene.remove(toRemove);
            toRemove.geometry.dispose();
            toRemove.material.dispose();
            
            this.selectedObject = null;
            this.hidePropertiesPanel();
            
            console.log('Location deleted');
        }
    }
    
    /**
     * Lưu tất cả thay đổi lên backend
     */
    async saveAllChanges() {
        if (!confirm('Lưu tất cả thay đổi vị trí?')) return;
        
        const changes = [];
        
        this.scene.children.forEach(child => {
            if (child.userData.loc_id || child.userData.is_new) {
                changes.push({
                    id: child.userData.loc_id || null,
                    code: child.userData.location_code,
                    pos_x: Math.round(child.position.x),
                    pos_y: Math.round(child.position.y),
                    pos_z: Math.round(child.position.z),
                    length: child.userData.length,
                    width: child.userData.width,
                    height: child.userData.height,
                    capacity: child.userData.max_capacity,
                    is_new: child.userData.is_new || false
                });
            }
        });
        
        try {
            const result = await rpc('/3Dstock/save-3d-layout', {
                warehouse_id: localStorage.getItem('company_id'),
                changes: changes
            });
            
            if (result.success) {
                alert('✓ Đã lưu tất cả thay đổi!');
                // Reload
                location.reload();
            } else {
                alert('❌ Lỗi: ' + result.error);
            }
        } catch (error) {
            alert('❌ Lỗi lưu: ' + error);
        }
    }
    
    /**
     * Undo/Redo Management
     */
    saveUndoState(obj) {
        this.undoStack.push({
            obj: obj,
            pos: { x: obj.position.x, y: obj.position.y, z: obj.position.z },
            scale: { x: obj.scale.x, y: obj.scale.y, z: obj.scale.z }
        });
        this.redoStack = [];  // Clear redo stack
    }
    
    undo() {
        if (this.undoStack.length === 0) return;
        
        const state = this.undoStack.pop();
        this.redoStack.push({
            obj: state.obj,
            pos: { x: state.obj.position.x, y: state.obj.position.y, z: state.obj.position.z },
            scale: { x: state.obj.scale.x, y: state.obj.scale.y, z: state.obj.scale.z }
        });
        
        state.obj.position.set(state.pos.x, state.pos.y, state.pos.z);
        state.obj.scale.set(state.scale.x, state.scale.y, state.scale.z);
        
        console.log('Undo executed');
    }
    
    redo() {
        if (this.redoStack.length === 0) return;
        
        const state = this.redoStack.pop();
        this.undoStack.push({
            obj: state.obj,
            pos: { x: state.obj.position.x, y: state.obj.position.y, z: state.obj.position.z },
            scale: { x: state.obj.scale.x, y: state.obj.scale.y, z: state.obj.scale.z }
        });
        
        state.obj.position.set(state.pos.x, state.pos.y, state.pos.z);
        state.obj.scale.set(state.scale.x, state.scale.y, state.scale.z);
        
        console.log('Redo executed');
    }
}

export default Stock3DEditMode;
