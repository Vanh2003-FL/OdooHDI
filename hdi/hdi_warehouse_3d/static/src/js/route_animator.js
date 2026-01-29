/** @odoo-module **/

/**
 * Route Animation Module
 * 
 * Animates picking routes in 3D scene with smooth path following
 * and visual indicators for progression
 */

export class RouteAnimator {
    constructor(scene, camera) {
        this.scene = scene;
        this.camera = camera;
        this.isAnimating = false;
        this.currentStep = 0;
        this.animationSpeed = 2.0; // meters per second
        this.routePath = [];
        this.routeMarkers = [];
        this.vehicleMesh = null;
        this.pathLine = null;
        this.completedPath = null;
    }

    /**
     * Load and prepare route for animation
     * @param {Array} binPositions - Array of {x, y, z} positions
     */
    loadRoute(binPositions) {
        this.clear();
        this.routePath = binPositions;
        this.currentStep = 0;

        // Create route line
        this.createRouteLine();
        
        // Create route markers
        this.createRouteMarkers();
        
        // Create vehicle/picker mesh
        this.createVehicle();
    }

    /**
     * Create line showing the route path
     */
    createRouteLine() {
        const points = this.routePath.map(pos => 
            new THREE.Vector3(pos.x, pos.y + 0.5, pos.z)
        );

        // Full route (gray)
        const geometry = new THREE.BufferGeometry().setFromPoints(points);
        const material = new THREE.LineDashedMaterial({
            color: 0x999999,
            linewidth: 2,
            dashSize: 0.5,
            gapSize: 0.3,
        });
        this.pathLine = new THREE.Line(geometry, material);
        this.pathLine.computeLineDistances();
        this.scene.add(this.pathLine);

        // Completed path (blue - will grow during animation)
        const completedMaterial = new THREE.LineBasicMaterial({
            color: 0x2196F3,
            linewidth: 3,
        });
        this.completedPath = new THREE.Line(
            new THREE.BufferGeometry().setFromPoints([points[0]]),
            completedMaterial
        );
        this.scene.add(this.completedPath);
    }

    /**
     * Create markers at each route stop
     */
    createRouteMarkers() {
        this.routePath.forEach((pos, index) => {
            const geometry = new THREE.SphereGeometry(0.4, 16, 16);
            
            // Color markers: green (start), red (end), blue (intermediate)
            let color;
            if (index === 0) {
                color = 0x4CAF50; // green - start
            } else if (index === this.routePath.length - 1) {
                color = 0xF44336; // red - end
            } else {
                color = 0x2196F3; // blue - waypoint
            }

            const material = new THREE.MeshStandardMaterial({
                color: color,
                emissive: color,
                emissiveIntensity: 0.3,
            });

            const marker = new THREE.Mesh(geometry, material);
            marker.position.set(pos.x, pos.y + 0.5, pos.z);
            marker.castShadow = true;
            
            this.scene.add(marker);
            this.routeMarkers.push(marker);

            // Add label (step number)
            this.createMarkerLabel(marker, index + 1);
        });
    }

    /**
     * Create text label for marker
     */
    createMarkerLabel(marker, number) {
        // Create sprite with text canvas
        const canvas = document.createElement('canvas');
        canvas.width = 64;
        canvas.height = 64;
        const context = canvas.getContext('2d');
        
        // Draw circle background
        context.fillStyle = '#fff';
        context.beginPath();
        context.arc(32, 32, 28, 0, 2 * Math.PI);
        context.fill();
        
        // Draw text
        context.fillStyle = '#333';
        context.font = 'bold 32px Arial';
        context.textAlign = 'center';
        context.textBaseline = 'middle';
        context.fillText(number.toString(), 32, 32);

        const texture = new THREE.CanvasTexture(canvas);
        const spriteMaterial = new THREE.SpriteMaterial({ map: texture });
        const sprite = new THREE.Sprite(spriteMaterial);
        sprite.scale.set(1, 1, 1);
        sprite.position.y = 1.5;
        
        marker.add(sprite);
    }

    /**
     * Create vehicle/picker mesh
     */
    createVehicle() {
        // Simple forklift/picker representation
        const group = new THREE.Group();

        // Body
        const bodyGeometry = new THREE.BoxGeometry(0.8, 1.2, 1.2);
        const bodyMaterial = new THREE.MeshStandardMaterial({
            color: 0xFFEB3B, // yellow
            metalness: 0.5,
        });
        const body = new THREE.Mesh(bodyGeometry, bodyMaterial);
        body.castShadow = true;
        group.add(body);

        // Wheels
        const wheelGeometry = new THREE.CylinderGeometry(0.2, 0.2, 0.1, 16);
        const wheelMaterial = new THREE.MeshStandardMaterial({ color: 0x333333 });
        
        const positions = [
            [-0.4, -0.5, 0.5],
            [0.4, -0.5, 0.5],
            [-0.4, -0.5, -0.5],
            [0.4, -0.5, -0.5],
        ];
        
        positions.forEach(pos => {
            const wheel = new THREE.Mesh(wheelGeometry, wheelMaterial);
            wheel.position.set(pos[0], pos[1], pos[2]);
            wheel.rotation.z = Math.PI / 2;
            group.add(wheel);
        });

        // Position at start
        if (this.routePath.length > 0) {
            group.position.set(
                this.routePath[0].x,
                this.routePath[0].y + 0.6,
                this.routePath[0].z
            );
        }

        this.vehicleMesh = group;
        this.scene.add(group);
    }

    /**
     * Start animation
     */
    start() {
        if (this.routePath.length < 2) {
            console.warn('Route must have at least 2 points');
            return;
        }

        this.isAnimating = true;
        this.currentStep = 0;
        this.animate();
    }

    /**
     * Pause animation
     */
    pause() {
        this.isAnimating = false;
    }

    /**
     * Resume animation
     */
    resume() {
        if (!this.isAnimating && this.currentStep < this.routePath.length - 1) {
            this.isAnimating = true;
            this.animate();
        }
    }

    /**
     * Stop and reset animation
     */
    stop() {
        this.isAnimating = false;
        this.currentStep = 0;
        
        if (this.vehicleMesh && this.routePath.length > 0) {
            this.vehicleMesh.position.set(
                this.routePath[0].x,
                this.routePath[0].y + 0.6,
                this.routePath[0].z
            );
        }

        // Reset completed path
        if (this.completedPath) {
            const points = [new THREE.Vector3(
                this.routePath[0].x,
                this.routePath[0].y + 0.5,
                this.routePath[0].z
            )];
            this.completedPath.geometry.setFromPoints(points);
        }
    }

    /**
     * Animation loop
     */
    animate() {
        if (!this.isAnimating) return;

        if (this.currentStep >= this.routePath.length - 1) {
            this.isAnimating = false;
            this.onComplete();
            return;
        }

        const startPos = this.routePath[this.currentStep];
        const endPos = this.routePath[this.currentStep + 1];
        
        const distance = Math.sqrt(
            Math.pow(endPos.x - startPos.x, 2) +
            Math.pow(endPos.y - startPos.y, 2) +
            Math.pow(endPos.z - startPos.z, 2)
        );

        const duration = (distance / this.animationSpeed) * 1000; // ms
        const startTime = Date.now();

        const step = () => {
            if (!this.isAnimating) return;

            const elapsed = Date.now() - startTime;
            const progress = Math.min(elapsed / duration, 1.0);

            // Interpolate position
            const x = startPos.x + (endPos.x - startPos.x) * progress;
            const y = startPos.y + (endPos.y - startPos.y) * progress;
            const z = startPos.z + (endPos.z - startPos.z) * progress;

            // Update vehicle position
            if (this.vehicleMesh) {
                this.vehicleMesh.position.set(x, y + 0.6, z);
                
                // Rotate vehicle to face movement direction
                const angle = Math.atan2(endPos.z - startPos.z, endPos.x - startPos.x);
                this.vehicleMesh.rotation.y = angle - Math.PI / 2;
            }

            // Update completed path
            this.updateCompletedPath();

            // Highlight current marker
            this.highlightMarker(this.currentStep + 1);

            if (progress < 1.0) {
                requestAnimationFrame(step);
            } else {
                this.currentStep++;
                this.animate();
            }
        };

        requestAnimationFrame(step);
    }

    /**
     * Update completed path line
     */
    updateCompletedPath() {
        if (!this.completedPath || !this.vehicleMesh) return;

        const points = [];
        
        // Add all completed waypoints
        for (let i = 0; i <= this.currentStep; i++) {
            points.push(new THREE.Vector3(
                this.routePath[i].x,
                this.routePath[i].y + 0.5,
                this.routePath[i].z
            ));
        }
        
        // Add current vehicle position
        points.push(new THREE.Vector3(
            this.vehicleMesh.position.x,
            this.vehicleMesh.position.y - 0.1,
            this.vehicleMesh.position.z
        ));

        this.completedPath.geometry.setFromPoints(points);
    }

    /**
     * Highlight current marker with pulsing effect
     */
    highlightMarker(index) {
        this.routeMarkers.forEach((marker, i) => {
            if (i === index) {
                const scale = 1.0 + Math.sin(Date.now() / 200) * 0.2;
                marker.scale.set(scale, scale, scale);
            } else if (i < index) {
                // Visited markers - make semi-transparent
                marker.material.opacity = 0.5;
                marker.material.transparent = true;
            } else {
                marker.scale.set(1, 1, 1);
            }
        });
    }

    /**
     * Called when animation completes
     */
    onComplete() {
        console.log('Route animation completed');
        
        // Flash final marker
        const finalMarker = this.routeMarkers[this.routeMarkers.length - 1];
        let count = 0;
        const flash = setInterval(() => {
            finalMarker.visible = !finalMarker.visible;
            count++;
            if (count > 6) {
                clearInterval(flash);
                finalMarker.visible = true;
            }
        }, 200);
    }

    /**
     * Clear all animation objects
     */
    clear() {
        // Remove path lines
        if (this.pathLine) {
            this.scene.remove(this.pathLine);
            this.pathLine.geometry.dispose();
            this.pathLine.material.dispose();
        }

        if (this.completedPath) {
            this.scene.remove(this.completedPath);
            this.completedPath.geometry.dispose();
            this.completedPath.material.dispose();
        }

        // Remove markers
        this.routeMarkers.forEach(marker => {
            this.scene.remove(marker);
            marker.geometry.dispose();
            marker.material.dispose();
        });
        this.routeMarkers = [];

        // Remove vehicle
        if (this.vehicleMesh) {
            this.scene.remove(this.vehicleMesh);
            this.vehicleMesh.traverse(child => {
                if (child.geometry) child.geometry.dispose();
                if (child.material) child.material.dispose();
            });
        }

        this.isAnimating = false;
        this.currentStep = 0;
    }

    /**
     * Set animation speed
     * @param {number} speed - Speed in meters per second
     */
    setSpeed(speed) {
        this.animationSpeed = Math.max(0.5, Math.min(speed, 10));
    }

    /**
     * Get animation progress (0-1)
     */
    getProgress() {
        return this.routePath.length > 1 
            ? this.currentStep / (this.routePath.length - 1)
            : 0;
    }
}
