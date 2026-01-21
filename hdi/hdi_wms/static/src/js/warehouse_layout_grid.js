// Warehouse Layout Grid Visualization - OPTIMIZED
// Hiển thị sơ đồ kho dạng lưới với các quants, tìm kiếm, zoom

(function($) {
    'use strict';

    $(document).ready(function() {
        const warehouseMapContainer = $('.warehouse-map-container');
        if (!warehouseMapContainer.length) return;

        const gridWrapper = $('#grid-wrapper');
        const searchInput = $('.search-input');
        const zoomBtns = $('.zoom-btn');
        const zoomLevel = $('.zoom-level');
        const gridCells = $('.grid-cell');
        
        let currentZoom = 100;
        const minZoom = 50;
        const maxZoom = 200;
        const zoomStep = 10;

        // ===== ZOOM FUNCTIONALITY =====
        zoomBtns.on('click', function() {
            const action = $(this).data('zoom');
            if (action === 'plus') {
                currentZoom = Math.min(currentZoom + zoomStep, maxZoom);
            } else if (action === 'minus') {
                currentZoom = Math.max(currentZoom - zoomStep, minZoom);
            }
            updateZoom();
        });

        function updateZoom() {
            const scale = currentZoom / 100;
            zoomLevel.text(currentZoom + '%');
            $('.warehouse-grid').css('transform', `scale(${scale})`);
            $('.warehouse-grid').css('transform-origin', 'top left');
        }

        // ===== SEARCH FUNCTIONALITY =====
        let searchTimeout;
        searchInput.on('input', function() {
            clearTimeout(searchTimeout);
            const searchTerm = $(this).val().toLowerCase().trim();

            searchTimeout = setTimeout(function() {
                if (!searchTerm) {
                    // Reset - show all
                    gridCells.removeClass('search-hidden search-highlight');
                    return;
                }

                gridCells.each(function() {
                    const $cell = $(this);
                    const lot = $cell.find('.quant-lot').text().toLowerCase();
                    const product = $cell.find('.quant-product').text().toLowerCase();
                    
                    if (lot.includes(searchTerm) || product.includes(searchTerm)) {
                        $cell.removeClass('search-hidden').addClass('search-highlight');
                    } else {
                        $cell.addClass('search-hidden').removeClass('search-highlight');
                    }
                });

                // Show count
                const visibleCount = gridCells.not('.search-hidden').length;
                const totalCount = gridCells.length;
                updateSearchStatus(visibleCount, totalCount);
            }, 300);
        });

        function updateSearchStatus(visible, total) {
            const status = visible === total ? 
                `Hiển thị ${total} ô` : 
                `Tìm thấy ${visible}/${total} ô`;
            console.log(status);
        }

        // ===== CELL CLICK HANDLERS =====
        gridCells.on('click', function(e) {
            const $cell = $(this);
            const isOccupied = $cell.hasClass('occupied');
            const locationId = $cell.data('location-id');

            if (e.target.closest('.cell-action-btn')) {
                handleCellAction(e, $cell);
            } else if (!isOccupied) {
                // Empty cell - open assign wizard
                openAssignWizard($cell, locationId);
            } else {
                // Occupied - show quick info
                showCellInfo($cell);
            }
        });

        function handleCellAction(e, $cell) {
            const $btn = $(e.target).closest('.cell-action-btn');
            const action = $btn.attr('class').split(' ')[1]; // edit, move, remove

            switch(action) {
                case 'edit':
                    openEditDialog($cell);
                    break;
                case 'move':
                    openMoveDialog($cell);
                    break;
                case 'remove':
                    confirmRemoveQuant($cell);
                    break;
            }
        }

        function openAssignWizard($cell, locationId) {
            // This would trigger the assign lot wizard
            const x = $cell.data('x');
            const y = $cell.data('y');
            console.log(`Opening wizard for location ${locationId} at (${x}, ${y})`);
            // window.location.href = `/web?action=...`;
        }

        function openEditDialog($cell) {
            const batchId = $cell.find('.quant-cell').data('batch-id');
            console.log(`Edit quant: ${batchId}`);
        }

        function openMoveDialog($cell) {
            const batchId = $cell.find('.quant-cell').data('batch-id');
            console.log(`Move quant: ${batchId}`);
        }

        function confirmRemoveQuant($cell) {
            if (confirm('Xóa hàng khỏi sơ đồ?')) {
                const batchId = $cell.find('.quant-cell').data('batch-id');
                console.log(`Remove quant: ${batchId}`);
            }
        }

        function showCellInfo($cell) {
            const lot = $cell.find('.quant-lot').text();
            const product = $cell.find('.quant-product').text();
            const qty = $cell.find('.qty-total').text();
            const days = $cell.find('.quant-badge').text();
            
            console.log(`Cell Info:\nLô: ${lot}\nSP: ${product}\nSL: ${qty}\nNgày: ${days}`);
        }

        // ===== ACTION BUTTONS =====
        $('.action-btn').on('click', function() {
            const action = $(this).attr('title');
            if (action.includes('Làm mới')) {
                location.reload();
            } else if (action.includes('Tải')) {
                exportGridData();
            }
        });

        function exportGridData() {
            const data = [];
            gridCells.each(function() {
                const $cell = $(this);
                if ($cell.hasClass('occupied')) {
                    data.push({
                        x: $cell.data('x'),
                        y: $cell.data('y'),
                        lot: $cell.find('.quant-lot').text(),
                        product: $cell.find('.quant-product').text(),
                        qty: $cell.find('.qty-total').text(),
                        days: $cell.find('.quant-badge').text(),
                    });
                }
            });
            console.log('Grid data:', data);
        }

        // ===== KEYBOARD SHORTCUTS =====
        $(document).on('keydown', function(e) {
            if (!searchInput.is(':focus')) {
                // Ctrl/Cmd + F = Focus search
                if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
                    e.preventDefault();
                    searchInput.focus();
                }
                // Ctrl/Cmd + + = Zoom in
                if ((e.ctrlKey || e.metaKey) && (e.key === '+' || e.key === '=')) {
                    e.preventDefault();
                    currentZoom = Math.min(currentZoom + zoomStep, maxZoom);
                    updateZoom();
                }
                // Ctrl/Cmd + - = Zoom out
                if ((e.ctrlKey || e.metaKey) && e.key === '-') {
                    e.preventDefault();
                    currentZoom = Math.max(currentZoom - zoomStep, minZoom);
                    updateZoom();
                }
                // Escape = Clear search
                if (e.key === 'Escape' && searchInput.val()) {
                    searchInput.val('').trigger('input');
                }
            }
        });

        // ===== DRAG & DROP (Optional) =====
        gridCells.on('dragstart', function(e) {
            if (!$(this).hasClass('occupied')) return;
            const batchId = $(this).find('.quant-cell').data('batch-id');
            e.originalEvent.dataTransfer.effectAllowed = 'move';
            e.originalEvent.dataTransfer.setData('batch_id', batchId);
        });

        gridCells.on('dragover', function(e) {
            e.preventDefault();
            e.originalEvent.dataTransfer.dropEffect = 'move';
            $(this).addClass('drag-over');
        });

        gridCells.on('dragleave', function() {
            $(this).removeClass('drag-over');
        });

        gridCells.on('drop', function(e) {
            e.preventDefault();
            $(this).removeClass('drag-over');
            const batchId = e.originalEvent.dataTransfer.getData('batch_id');
            const targetLocationId = $(this).data('location-id');
            console.log(`Move batch ${batchId} to location ${targetLocationId}`);
        });

        console.log('✓ Warehouse Map Grid initialized');
    });
})(jQuery);
            }

            return grid;
        },

        /**
         * Render nội dung ô chứa quant
         */
        _renderQuantCell: function(quant, layout) {
            const daysInWarehouse = quant.days_in_warehouse || 0;
            let badgeClass = 'badge-green'; // < 60 ngày
            let badgeColor = '#28a745';

            if (daysInWarehouse > 90) {
                badgeClass = 'badge-red blink'; // > 90 ngày (nhấp nháy)
                badgeColor = '#ff6600';
            } else if (daysInWarehouse > 60) {
                badgeClass = 'badge-orange'; // 60-90 ngày
                badgeColor = '#ff9800';
            }

            let status = 'available';
            if (quant.reserved_quantity > 0) {
                status = 'reserved';
            }

            return `
                <div class="quant-cell ${status}">
                    <div class="quant-badge ${badgeClass}">${daysInWarehouse}d</div>
                    <div class="quant-info">
                        <div class="quant-lot">${quant.lot_id ? quant.lot_id[1] : 'No Lot'}</div>
                        <div class="quant-product">${quant.product_id[1]}</div>
                        <div class="quant-code">${quant.product_id[1]}</div>
                        <div class="quant-qty">
                            <span class="total">${Math.floor(quant.quantity)}</span>
                            <span class="available">(${Math.floor(quant.quantity - quant.reserved_quantity)})</span>
                        </div>
                        ${quant.reserved_quantity > 0 ? `<div class="reserved-qty">Đặt: ${Math.floor(quant.reserved_quantity)}</div>` : ''}
                        <div class="quant-date">${quant.in_date || 'N/A'}</div>
                    </div>
                </div>
            `;
        },

        /**
         * Render menu context khi click vào quant
         */
        _showQuantContextMenu: function(quant) {
            const menu = document.createElement('div');
            menu.className = 'quant-context-menu';
            menu.innerHTML = `
                <ul>
                    <li data-action="pick"><i class="fa fa-check"></i> Lấy Hàng</li>
                    <li data-action="move"><i class="fa fa-arrows"></i> Chuyển Vị trí</li>
                    <li data-action="transfer"><i class="fa fa-truck"></i> Chuyển Kho</li>
                    <li data-action="details"><i class="fa fa-info"></i> Xem Chi tiết</li>
                    <li data-action="location"><i class="fa fa-map-marker"></i> Chi tiết Vị trí</li>
                    <li data-action="remove"><i class="fa fa-trash"></i> Xóa khỏi Sơ đồ</li>
                </ul>
            `;

            document.body.appendChild(menu);
            return menu;
        },

        on_attach_callback: function() {
            this._super.apply(this, arguments);
            this._renderGrid();
        },

        _renderGrid: function() {
            // Implementation sẽ được thêm vào controller
        },
    });

    return WarehouseLayoutMapRenderer;
});

/**
 * WarehouseLayoutMapController
 */
odoo.define('hdi_wms.WarehouseLayoutMapController', function(require) {
    'use strict';

    const AbstractController = require('web.AbstractController');

    const WarehouseLayoutMapController = AbstractController.extend({
        events: {
            'click .grid-cell': '_onCellClicked',
        },

        init: function(parent, model, renderer, params) {
            this._super.apply(this, arguments);
        },

        _onCellClicked: function(ev) {
            const $cell = $(ev.currentTarget);
            const layout_id = this.model.get('layout_id');
            const pos_x = parseInt($cell.data('x'));
            const pos_y = parseInt($cell.data('y'));

            if ($cell.hasClass('occupied')) {
                // Hiển thị context menu cho quant
                this._showQuantMenu(pos_x, pos_y);
            } else {
                // Hiển thị wizard để gán lot mới
                this._showAssignLotWizard(layout_id, pos_x, pos_y);
            }
        },

        _showQuantMenu: function(x, y) {
            // TODO: Implement context menu
        },

        _showAssignLotWizard: function(layout_id, x, y) {
            // TODO: Implement wizard dialog
        },
    });

    return WarehouseLayoutMapController;
});

/**
 * WarehouseLayoutMapModel
 */
odoo.define('hdi_wms.WarehouseLayoutMapModel', function(require) {
    'use strict';

    const Model = require('web.Model');

    const WarehouseLayoutMapModel = Model.extend({
        defaults: {
            layout_id: null,
            quants: [],
        },

        init: function(parent, params) {
            this._super.apply(this, arguments);
        },

        /**
         * Load quants cho layout
         */
        loadQuants: function(layout_id) {
            const self = this;
            return this.query(['stock.quant'])
                .filter([
                    ['display_on_map', '=', true],
                    ['location_id.warehouse_id', '=', layout_id.warehouse_id],
                ])
                .all()
                .then(function(quants) {
                    self.set({ quants: quants });
                    return quants;
                });
        },
    });

    return WarehouseLayoutMapModel;
});
