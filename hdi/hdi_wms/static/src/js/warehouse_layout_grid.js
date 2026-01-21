// Warehouse Layout Grid Visualization
// Hiển thị sơ đồ kho dạng lưới với các quants

odoo.define('hdi_wms.warehouse_layout_grid', function(require) {
    'use strict';

    const AbstractView = require('web.AbstractView');
    const View = require('web.View');
    const core = require('web.core');
    const _t = core._t;

    /**
     * WarehouseLayoutMapView
     * Hiển thị sơ đồ kho dạng lưới
     */
    const WarehouseLayoutMapView = AbstractView.extend({
        display_name: _t('Warehouse Map'),
        icon: 'fa-th',
        config: {
            Controller: require('hdi_wms.WarehouseLayoutMapController'),
            Model: require('hdi_wms.WarehouseLayoutMapModel'),
            Renderer: require('hdi_wms.WarehouseLayoutMapRenderer'),
        },

        init: function(viewInfo, params) {
            this._super.apply(this, arguments);
            const self = this;
        },
    });

    View.registry.add('warehouse_map', WarehouseLayoutMapView);

    return WarehouseLayoutMapView;
});

/**
 * WarehouseLayoutMapRenderer
 * Render grid visualization
 */
odoo.define('hdi_wms.WarehouseLayoutMapRenderer', function(require) {
    'use strict';

    const AbstractRenderer = require('web.AbstractRenderer');
    const qweb = require('web.qweb');

    const WarehouseLayoutMapRenderer = AbstractRenderer.extend({
        className: 'warehouse_layout_grid_container',
        template: 'WarehouseLayoutMapTemplate',

        init: function(parent, state, params) {
            this._super.apply(this, arguments);
            this.quants = [];
        },

        /**
         * Render grid dạng HTML table
         */
        _renderGridMap: function(layout, quants) {
            const self = this;
            const grid = document.createElement('div');
            grid.className = 'warehouse-grid';

            const rows = layout.rows;
            const cols = layout.columns;

            for (let y = 0; y < rows; y++) {
                const rowDiv = document.createElement('div');
                rowDiv.className = 'grid-row';

                for (let x = 0; x < cols; x++) {
                    const cellDiv = document.createElement('div');
                    cellDiv.className = 'grid-cell';
                    cellDiv.id = `cell-${x}-${y}`;

                    // Tìm quant tại vị trí này
                    const quant = quants.find(q => q.pos_x === x && q.pos_y === y);

                    if (quant) {
                        // Ô có hàng
                        cellDiv.classList.add('occupied');
                        cellDiv.innerHTML = self._renderQuantCell(quant, layout);
                    } else {
                        // Ô trống
                        cellDiv.classList.add('empty');
                        cellDiv.innerHTML = '<span class="empty-cell">+</span>';
                    }

                    cellDiv.addEventListener('click', function() {
                        self.trigger_up('cell_clicked', {
                            layout_id: layout.id,
                            pos_x: x,
                            pos_y: y,
                            quant_id: quant ? quant.id : null,
                        });
                    });

                    rowDiv.appendChild(cellDiv);
                }

                grid.appendChild(rowDiv);
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
