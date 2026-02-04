/** @odoo-module **/
/**
 * 🎮 Warehouse Map Controller
 * ===========================
 * Main controller integrating 2D/3D views with barcode scanner
 */

import { registry } from "@web/core/registry";
import { Component, useState, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { WarehouseMap2D } from "./warehouse_map_2d";
import { WarehouseMap3D } from "./warehouse_map_3d";

export class WarehouseMapController extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.notification = useService("notification");
        
        this.state = useState({
            warehouseId: this.props.warehouseId || 1,
            viewMode: this.props.viewMode || '2d',
            scanInput: '',
        });
        
        onMounted(() => {
            this.setupBarcodeScanner();
            this.setupSearchHandler();
        });
    }
    
    /**
     * 📱 Setup barcode scanner integration
     * Khi scan barcode → tìm serial → highlight bin
     */
    setupBarcodeScanner() {
        const scanInput = document.getElementById('scan_input');
        const scanButton = document.querySelector('.o_scan_button');
        
        if (scanInput) {
            // Scan on Enter key
            scanInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.handleBarcodeScan(scanInput.value.trim());
                    scanInput.value = '';
                }
            });
            
            // Auto-focus for barcode scanner
            scanInput.focus();
        }
        
        if (scanButton) {
            scanButton.addEventListener('click', () => {
                if (scanInput) {
                    this.handleBarcodeScan(scanInput.value.trim());
                    scanInput.value = '';
                }
            });
        }
        
        // Setup heatmap toggle
        const heatmapToggle = document.getElementById('heatmap_toggle');
        if (heatmapToggle) {
            heatmapToggle.addEventListener('change', (e) => {
                this.toggleHeatmap(e.target.checked);
            });
        }
        
        // Setup labels toggle
        const labelsToggle = document.getElementById('labels_toggle');
        if (labelsToggle) {
            labelsToggle.addEventListener('change', (e) => {
                this.toggleLabels(e.target.checked);
            });
        }
    }
    
    /**
     * 🔍 Setup product search handler
     */
    setupSearchHandler() {
        const searchInput = document.getElementById('product_search');
        const searchButton = document.querySelector('.o_search_button');
        
        if (searchInput) {
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.handleProductSearch(searchInput.value.trim());
                }
            });
        }
        
        if (searchButton) {
            searchButton.addEventListener('click', () => {
                if (searchInput) {
                    this.handleProductSearch(searchInput.value.trim());
                }
            });
        }
    }
    
    /**
     * 🔦 Handle barcode scan
     * 🔥 CÁI NÀY LÀ ĐIỂM ĂN TIỀN NHẤT
     * 
     * Workflow:
     * 1. Scan Serial → Odoo xác định lot_id
     * 2. Tìm stock.quant
     * 3. Lấy location_id (bin)
     * 4. Highlight bin trên map
     */
    async handleBarcodeScan(barcode) {
        if (!barcode) return;
        
        this.notification.add(`🔍 Scanning: ${barcode}...`, { type: 'info' });
        
        try {
            const result = await this.rpc('/warehouse_map/scan_serial', {
                serial_number: barcode
            });
            
            if (result.error) {
                this.notification.add(`❌ ${result.error}`, { type: 'warning' });
                return;
            }
            
            // Get current map view and trigger highlight
            const currentView = this.getCurrentMapView();
            if (currentView && currentView.highlightBySerial) {
                await currentView.highlightBySerial(barcode);
            }
            
        } catch (error) {
            console.error('Barcode scan error:', error);
            this.notification.add('Failed to process barcode', { type: 'danger' });
        }
    }
    
    /**
     * 🔍 Handle product search
     */
    async handleProductSearch(productName) {
        if (!productName) return;
        
        try {
            const result = await this.rpc('/warehouse_map/search_product', {
                warehouse_id: this.state.warehouseId,
                product_name: productName
            });
            
            if (result.error) {
                this.notification.add(result.error, { type: 'warning' });
                return;
            }
            
            if (result.bins && result.bins.length > 0) {
                let message = `Found in ${result.bins.length} location(s):\n`;
                result.bins.forEach(bin => {
                    message += `• ${bin.location_name}\n`;
                });
                
                this.notification.add(message, {
                    type: 'success',
                    sticky: true,
                });
                
                // Highlight bins on map
                const currentView = this.getCurrentMapView();
                if (currentView) {
                    currentView.state.highlightedBins = result.bins.map(b => b.location_id);
                    if (currentView.render2DMap) {
                        currentView.render2DMap();
                    } else if (currentView.render3DMap) {
                        currentView.render3DMap();
                    }
                }
            } else {
                this.notification.add('Product not found in warehouse', { type: 'info' });
            }
            
        } catch (error) {
            console.error('Product search error:', error);
            this.notification.add('Search failed', { type: 'danger' });
        }
    }
    
    /**
     * 🗺️ Get current map view instance
     */
    getCurrentMapView() {
        // This would need to be connected to the actual view instances
        // Implementation depends on how views are mounted
        const container2D = document.querySelector('.o_warehouse_map_2d');
        const container3D = document.querySelector('.o_warehouse_map_3d');
        
        if (this.state.viewMode === '2d' && container2D) {
            return container2D.__mapInstance__;
        } else if (this.state.viewMode === '3d' && container3D) {
            return container3D.__mapInstance__;
        }
        
        return null;
    }
    
    /**
     * 🎨 Toggle heatmap visualization
     */
    toggleHeatmap(enabled) {
        const currentView = this.getCurrentMapView();
        if (currentView && currentView.toggleHeatmap) {
            currentView.toggleHeatmap();
        }
    }
    
    /**
     * 🏷️ Toggle location labels
     */
    toggleLabels(enabled) {
        const currentView = this.getCurrentMapView();
        if (currentView && currentView.toggleLabels) {
            currentView.toggleLabels();
        }
    }
    
    /**
     * 🔄 Switch between 2D and 3D views
     */
    switchView(viewMode) {
        this.state.viewMode = viewMode;
        
        // Show/hide appropriate containers
        const container2D = document.querySelector('.o_warehouse_map_2d');
        const container3D = document.querySelector('.o_warehouse_map_3d');
        
        if (container2D) {
            container2D.style.display = viewMode === '2d' ? 'block' : 'none';
        }
        
        if (container3D) {
            container3D.style.display = viewMode === '3d' ? 'block' : 'none';
        }
    }
}

WarehouseMapController.template = "hdi_warehouse_map.WarehouseMapController";
WarehouseMapController.components = { WarehouseMap2D, WarehouseMap3D };
WarehouseMapController.props = {
    warehouseId: { type: Number, optional: true },
    viewMode: { type: String, optional: true },
};

registry.category("actions").add("warehouse_map_controller", WarehouseMapController);

// Initialize on page load
if (typeof document !== 'undefined') {
    document.addEventListener('DOMContentLoaded', () => {
        console.log('🗺️ HDI Warehouse Map Module Loaded');
    });
}
