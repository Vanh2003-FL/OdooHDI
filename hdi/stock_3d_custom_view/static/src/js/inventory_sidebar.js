// Inventory Sidebar Component
// Display products list with stock quantity, SKU, images

export class InventorySidebar {
    constructor(containerId, orm, state) {
        this.containerId = containerId;
        this.orm = orm;
        this.state = state;
        this.inventoryData = [];
        this.filteredData = [];
        this.init();
    }

    async init() {
        await this.loadInventoryData();
        this.render();
        this.attachEventListeners();
    }

    async loadInventoryData() {
        // Load products with stock quantities
        try {
            const quants = await this.orm.search_read(
                'stock.quant',
                [
                    ['warehouse_id', '=', this.state.warehouseId],
                    ['quantity', '>', 0]
                ],
                ['id', 'product_id', 'location_id', 'quantity', 'reserved_quantity'],
                { limit: 200 }
            );

            const inventoryMap = new Map();
            
            for (const quant of quants) {
                const productId = quant.product_id[0];
                
                if (!inventoryMap.has(productId)) {
                    inventoryMap.set(productId, {
                        productId: productId,
                        productName: quant.product_id[1],
                        sku: '',
                        image: '',
                        totalQuantity: 0,
                        reservedQuantity: 0,
                        locations: []
                    });
                }

                const item = inventoryMap.get(productId);
                item.totalQuantity += quant.quantity;
                item.reservedQuantity += quant.reserved_quantity;
                item.locations.push({
                    locationId: quant.location_id[0],
                    locationName: quant.location_id[1],
                    quantity: quant.quantity
                });
            }

            const productIds = Array.from(inventoryMap.keys());
            if (productIds.length > 0) {
                const products = await this.orm.read(
                    'product.product',
                    productIds,
                    ['default_code', 'image_1920']
                );

                for (const product of products) {
                    const item = inventoryMap.get(product.id);
                    if (item) {
                        item.sku = product.default_code || 'N/A';
                        item.image = product.image_1920 || null;
                    }
                }
            }

            this.inventoryData = Array.from(inventoryMap.values());
            this.filteredData = [...this.inventoryData];
        } catch (error) {
            console.error('Error loading inventory data:', error);
        }
    }

    render() {
        // Render inventory items
        const container = document.getElementById(this.containerId);
        if (!container) return;

        const html = `
            <div class="inventory-items">
                ${this.filteredData.length === 0 ? 
                    '<div class="empty-state"><i class="fa fa-inbox"></i><p>No inventory items</p></div>' :
                    this.filteredData.map(item => this.renderItemCard(item)).join('')
                }
            </div>
        `;

        container.innerHTML = html;
    }

    renderItemCard(item) {
        // Render single inventory item card
        const imageUrl = item.image ? 
            `data:image/png;base64,${item.image.substr(0, 100)}...` : 
            'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"%3E%3Crect fill="%23e0e0e0" width="100" height="100"/%3E%3C/svg%3E';

        return `
            <div class="inventory-item-card" data-product-id="${item.productId}">
                <div class="item-image">
                    <img src="${imageUrl}" alt="${item.productName}" />
                </div>
                <div class="item-details">
                    <h6 class="item-name" title="${item.productName}">${item.productName}</h6>
                    <p class="item-sku"><strong>SKU:</strong> <span>${item.sku}</span></p>
                    <p class="item-quantity">
                        <strong>Stock:</strong> 
                        <span class="badge badge-info">${Math.floor(item.totalQuantity)}</span>
                    </p>
                    <p class="item-reserved">
                        <strong>Reserved:</strong> 
                        <span class="badge badge-warning">${Math.floor(item.reservedQuantity)}</span>
                    </p>
                </div>
                <div class="item-actions">
                    <button class="btn btn-xs btn-primary" 
                            data-product-id="${item.productId}"
                            title="View Details">
                        <i class="fa fa-eye"></i>
                    </button>
                </div>
            </div>
        `;
    }

    attachEventListeners() {
        // Attach event listeners
        const container = document.getElementById(this.containerId);
        const searchInput = document.getElementById('search_inventory');

        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.filterBySearch(e.target.value);
            });
        }

        container.addEventListener('click', (e) => {
            const button = e.target.closest('[data-product-id]');
            if (button) {
                const productId = parseInt(button.dataset.productId);
                this.showProductDetails(productId);
            }
        });
    }

    filterBySearch(searchText) {
        // Filter inventory items by search text
        const query = searchText.toLowerCase().trim();

        if (!query) {
            this.filteredData = [...this.inventoryData];
        } else {
            this.filteredData = this.inventoryData.filter(item => {
                const name = item.productName.toLowerCase();
                const sku = (item.sku || '').toLowerCase();
                return name.includes(query) || sku.includes(query);
            });
        }

        this.render();
        this.attachEventListeners();
    }

    showProductDetails(productId) {
        // Show detailed information about product
        const item = this.inventoryData.find(i => i.productId === productId);
        if (!item) return;

        const detailsHtml = `
            <div class="product-details-modal">
                <div class="modal" role="dialog">
                    <div class="modal-dialog modal-lg">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">${item.productName}</h5>
                                <button type="button" class="close" data-dismiss="modal">
                                    <span>&times;</span>
                                </button>
                            </div>
                            <div class="modal-body">
                                <div class="row">
                                    <div class="col-md-4">
                                        <img src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 200'%3E%3Crect fill='%23e0e0e0' width='200' height='200'/%3E%3C/svg%3E" 
                                             class="img-fluid" alt="${item.productName}"/>
                                    </div>
                                    <div class="col-md-8">
                                        <table class="table table-sm">
                                            <tr>
                                                <td><strong>SKU:</strong></td>
                                                <td>${item.sku}</td>
                                            </tr>
                                            <tr>
                                                <td><strong>Total Stock:</strong></td>
                                                <td>${Math.floor(item.totalQuantity)}</td>
                                            </tr>
                                            <tr>
                                                <td><strong>Reserved:</strong></td>
                                                <td>${Math.floor(item.reservedQuantity)}</td>
                                            </tr>
                                            <tr>
                                                <td><strong>Available:</strong></td>
                                                <td>${Math.floor(item.totalQuantity - item.reservedQuantity)}</td>
                                            </tr>
                                        </table>

                                        <h6 class="mt-3">Location Details:</h6>
                                        <table class="table table-sm table-striped">
                                            <thead>
                                                <tr>
                                                    <th>Location</th>
                                                    <th>Quantity</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                ${item.locations.map(loc => `
                                                    <tr>
                                                        <td>${loc.locationName}</td>
                                                        <td>${Math.floor(loc.quantity)}</td>
                                                    </tr>
                                                `).join('')}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        console.log('Show product details:', item);
    }

    refreshInventory() {
        // Refresh inventory data
        this.loadInventoryData().then(() => {
            this.render();
            this.attachEventListeners();
        });
    }
}
