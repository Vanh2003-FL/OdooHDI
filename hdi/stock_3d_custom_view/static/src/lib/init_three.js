// Initialize THREE.js as global variable for OrbitControls
if (typeof THREE !== 'undefined') {
    window.THREE = THREE;
    console.log('THREE.js initialized globally');
}
