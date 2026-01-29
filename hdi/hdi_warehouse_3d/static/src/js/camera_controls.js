/** @odoo-module **/

import { Component, useState } from "@odoo/owl";

/**
 * Camera Controls Component
 * Provides preset camera views and controls for 3D viewer
 */
export class CameraControls extends Component {
    static template = "hdi_warehouse_3d.CameraControls";
    static props = {
        camera: { type: Object },
        controls: { type: Object },
        target: { type: Object, optional: true },
    };

    setup() {
        this.state = useState({
            currentPreset: 'perspective',
            fov: 60,
            autoRotate: false,
        });

        this.presets = {
            perspective: {
                name: 'Perspective',
                icon: 'fa-cube',
                position: { x: 30, y: 40, z: 30 },
            },
            top: {
                name: 'Top View',
                icon: 'fa-arrow-down',
                position: { x: 0, y: 80, z: 0 },
            },
            front: {
                name: 'Front View',
                icon: 'fa-arrow-right',
                position: { x: 0, y: 20, z: 60 },
            },
            side: {
                name: 'Side View',
                icon: 'fa-arrow-left',
                position: { x: 60, y: 20, z: 0 },
            },
            isometric: {
                name: 'Isometric',
                icon: 'fa-cubes',
                position: { x: 40, y: 40, z: 40 },
            },
        };
    }

    applyPreset(presetKey) {
        const preset = this.presets[presetKey];
        if (!preset || !this.props.camera) return;

        this.state.currentPreset = presetKey;

        // Animate camera to position
        this.animateCameraTo(preset.position);
    }

    animateCameraTo(targetPos, duration = 1000) {
        const camera = this.props.camera;
        const startPos = {
            x: camera.position.x,
            y: camera.position.y,
            z: camera.position.z,
        };

        const startTime = Date.now();

        const animate = () => {
            const elapsed = Date.now() - startTime;
            const progress = Math.min(elapsed / duration, 1.0);
            
            // Easing function (ease-in-out)
            const eased = progress < 0.5
                ? 2 * progress * progress
                : 1 - Math.pow(-2 * progress + 2, 2) / 2;

            camera.position.x = startPos.x + (targetPos.x - startPos.x) * eased;
            camera.position.y = startPos.y + (targetPos.y - startPos.y) * eased;
            camera.position.z = startPos.z + (targetPos.z - startPos.z) * eased;

            if (this.props.target) {
                camera.lookAt(this.props.target.x, this.props.target.y, this.props.target.z);
            }

            if (progress < 1.0) {
                requestAnimationFrame(animate);
            }
        };

        animate();
    }

    zoomIn() {
        if (!this.props.controls) return;
        
        const camera = this.props.camera;
        const controls = this.props.controls;
        
        const distance = camera.position.distanceTo(controls.target);
        const newDistance = distance * 0.8;
        
        const direction = new THREE.Vector3()
            .subVectors(camera.position, controls.target)
            .normalize();
        
        camera.position.copy(controls.target).add(direction.multiplyScalar(newDistance));
    }

    zoomOut() {
        if (!this.props.controls) return;
        
        const camera = this.props.camera;
        const controls = this.props.controls;
        
        const distance = camera.position.distanceTo(controls.target);
        const newDistance = distance * 1.25;
        
        const direction = new THREE.Vector3()
            .subVectors(camera.position, controls.target)
            .normalize();
        
        camera.position.copy(controls.target).add(direction.multiplyScalar(newDistance));
    }

    resetCamera() {
        this.applyPreset('perspective');
    }

    toggleAutoRotate() {
        if (!this.props.controls) return;
        
        this.state.autoRotate = !this.state.autoRotate;
        this.props.controls.autoRotate = this.state.autoRotate;
        this.props.controls.autoRotateSpeed = 1.0;
    }

    adjustFov(delta) {
        if (!this.props.camera) return;
        
        this.state.fov = Math.max(30, Math.min(120, this.state.fov + delta));
        this.props.camera.fov = this.state.fov;
        this.props.camera.updateProjectionMatrix();
    }

    takeScreenshot() {
        // Trigger screenshot in parent component
        this.props.onScreenshot?.();
    }

    toggleFullscreen() {
        const container = document.querySelector('.warehouse-3d-viewer');
        if (!container) return;

        if (!document.fullscreenElement) {
            container.requestFullscreen();
        } else {
            document.exitFullscreen();
        }
    }
}
