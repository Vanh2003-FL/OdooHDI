odoo.define('hdi_wms.warehouse_layout', function(require) {
    'use strict';

    var rpc = require('web.rpc');
    var core = require('web.core');
    var _t = core._t;

    /**
     * Warehouse Layout Grid Visualization
     * Renders an interactive warehouse layout grid
     */
    var WarehouseLayoutGrid = function(layout_id, cell_width, cell_height) {
        this.layout_id = layout_id;
        this.cell_width = cell_width || 100;
        this.cell_height = cell_height || 80;
        this.cells = [];
        this.selected_cell = null;
    };

    /**
     * Initialize grid with warehouse data
     */
    WarehouseLayoutGrid.prototype.init = function(container, layout_data) {
        var self = this;
        this.container = container;
        this.layout_data = layout_data;

        // Clear container
        $(container).empty();

        // Render legend
        this._render_legend(container);

        // Render statistics
        this._render_statistics(container);

        // Render grid by levels
        this._render_grid(container, layout_data);
    };

    /**
     * Render legend
     */
    WarehouseLayoutGrid.prototype._render_legend = function(container) {
        var legend_html = `
            <div class="grid_legend">
                <div class="legend_item">
                    <div class="legend_box" style="background-color: #ecf0f1;"></div>
                    <span>Empty</span>
                </div>
                <div class="legend_item">
                    <div class="legend_box" style="background-color: #f39c12;"></div>
                    <span>Partial</span>
                </div>
                <div class="legend_item">
                    <div class="legend_box" style="background-color: #e74c3c;"></div>
                    <span>Full</span>
                </div>
                <div class="legend_item">
                    <div class="legend_box" style="background-color: #3498db; border-style: dashed;"></div>
                    <span>Reserved</span>
                </div>
                <div class="legend_item">
                    <div class="legend_box" style="background-color: #2c3e50;"></div>
                    <span>Blocked</span>
                </div>
            </div>
        `;
        $(container).append(legend_html);
    };

    /**
     * Render statistics
     */
    WarehouseLayoutGrid.prototype._render_statistics = function(container) {
        var stats_html = `
            <div class="grid_statistics">
                <div class="stat_card">
                    <div class="stat_value">${this.layout_data.total_slots}</div>
                    <div class="stat_label">Total Slots</div>
                </div>
                <div class="stat_card">
                    <div class="stat_value">${this.layout_data.occupied_slots}</div>
                    <div class="stat_label">Occupied</div>
                </div>
                <div class="stat_card">
                    <div class="stat_value">${this.layout_data.empty_slots}</div>
                    <div class="stat_label">Empty</div>
                </div>
                <div class="stat_card">
                    <div class="stat_value">${this.layout_data.utilization_rate.toFixed(1)}%</div>
                    <div class="stat_label">Utilization</div>
                </div>
            </div>
        `;
        $(container).append(stats_html);
    };

    /**
     * Render grid for each level
     */
    WarehouseLayoutGrid.prototype._render_grid = function(container, layout_data) {
        var self = this;

        // Create 3D view container
        var grid_3d_html = '<div class="grid_3d_view">';

        for (var level = 1; level <= layout_data.levels; level++) {
            grid_3d_html += '<div class="level_section">';
            grid_3d_html += '<div class="level_title">Level ' + level + '</div>';
            grid_3d_html += '<div class="warehouse_layout_grid" style="grid-template-columns: repeat(' +
                layout_data.columns + ', ' + self.cell_width + 'px);">';

            // Render cells for this level
            for (var row = 1; row <= layout_data.rows; row++) {
                for (var col = 1; col <= layout_data.columns; col++) {
                    var cell_data = self._find_cell_data(layout_data, level, row, col);
                    var cell_html = self._render_cell(cell_data);
                    grid_3d_html += cell_html;
                }
            }

            grid_3d_html += '</div>'; // Close warehouse_layout_grid
            grid_3d_html += '</div>'; // Close level_section
        }

        grid_3d_html += '</div>'; // Close grid_3d_view
        $(container).append(grid_3d_html);

        // Attach event handlers
        this._attach_cell_handlers(container);
    };

    /**
     * Find cell data from grid locations
     */
    WarehouseLayoutGrid.prototype._find_cell_data = function(layout_data, level, row, col) {
        var matching = layout_data.location_grids.filter(function(grid) {
            return grid.level === level && grid.row === row && grid.column === col;
        });

        if (matching.length > 0) {
            return matching[0];
        }

        return {
            id: null,
            position_code: 'L' + level + '-R' + row + '-C' + col,
            row: row,
            column: col,
            level: level,
            batch_id: null,
            status: 'empty',
            utilization_percent: 0,
        };
    };

    /**
     * Render a single cell
     */
    WarehouseLayoutGrid.prototype._render_cell = function(cell_data) {
        var status_class = cell_data.status || 'empty';
        var batch_name = '';

        if (cell_data.batch && cell_data.batch.length > 0) {
            batch_name = cell_data.batch[0] ? cell_data.batch[0][1] : '';
        }

        var cell_html = '<div class="grid_cell ' + status_class + '" ' +
            'data-cell-id="' + (cell_data.id || '') + '" ' +
            'data-position="' + cell_data.position_code + '" ' +
            'style="width: ' + this.cell_width + 'px; height: ' + this.cell_height + 'px;" ' +
            '>';

        cell_html += '<div class="grid_cell_position">' + cell_data.position_code + '</div>';

        if (batch_name) {
            cell_html += '<div class="grid_cell_batch" title="' + batch_name + '">' + batch_name + '</div>';
            cell_html += '<div class="grid_cell_info">' + cell_data.utilization_percent.toFixed(0) + '%</div>';
        }

        cell_html += '</div>';
        return cell_html;
    };

    /**
     * Attach event handlers to cells
     */
    WarehouseLayoutGrid.prototype._attach_cell_handlers = function(container) {
        var self = this;

        $(container).on('click', '.grid_cell', function(e) {
            e.preventDefault();
            var position = $(this).attr('data-position');
            var cell_id = $(this).attr('data-cell-id');

            if (cell_id) {
                self._show_cell_context_menu(this, cell_id);
            }
        });

        // Right click context menu
        $(container).on('contextmenu', '.grid_cell', function(e) {
            e.preventDefault();
            var cell_id = $(this).attr('data-cell-id');

            if (cell_id) {
                self._show_cell_context_menu(this, cell_id);
            }
        });
    };

    /**
     * Show context menu for cell
     */
    WarehouseLayoutGrid.prototype._show_cell_context_menu = function(element, cell_id) {
        var self = this;

        // Remove existing menu
        $('.grid_cell_context_menu').remove();

        var menu_html = `
            <div class="grid_cell_context_menu">
                <div class="menu_item" data-action="place">Place Batch</div>
                <div class="menu_item" data-action="move">Move Batch</div>
                <div class="menu_item" data-action="pick">Pick Batch</div>
                <div class="menu_item" data-action="transfer">Transfer Warehouse</div>
                <div class="menu_item" data-action="details">View Details</div>
            </div>
        `;

        var menu = $(menu_html);
        $(element).append(menu);

        // Position menu near element
        var offset = $(element).offset();
        menu.css({
            top: offset.top + 10,
            left: offset.left + 10,
        });

        // Attach menu handlers
        menu.find('.menu_item').on('click', function() {
            var action = $(this).attr('data-action');
            self._handle_cell_action(action, cell_id);
            menu.remove();
        });

        // Close menu when clicking elsewhere
        $(document).one('click', function() {
            menu.remove();
        });
    };

    /**
     * Handle cell actions
     */
    WarehouseLayoutGrid.prototype._handle_cell_action = function(action, cell_id) {
        switch (action) {
            case 'place':
                this._action_place_batch(cell_id);
                break;
            case 'move':
                this._action_move_batch(cell_id);
                break;
            case 'pick':
                this._action_pick_batch(cell_id);
                break;
            case 'transfer':
                this._action_transfer_warehouse(cell_id);
                break;
            case 'details':
                this._action_view_details(cell_id);
                break;
        }
    };

    /**
     * Action: Place batch
     */
    WarehouseLayoutGrid.prototype._action_place_batch = function(cell_id) {
        var self = this;
        rpc.query({
            model: 'hdi.warehouse.location.grid',
            method: 'action_place_batch',
            args: [[cell_id]],
        }).done(function(result) {
            self._execute_action(result);
        });
    };

    /**
     * Action: Move batch
     */
    WarehouseLayoutGrid.prototype._action_move_batch = function(cell_id) {
        var self = this;
        rpc.query({
            model: 'hdi.warehouse.location.grid',
            method: 'action_move_batch',
            args: [[cell_id]],
        }).done(function(result) {
            self._execute_action(result);
        });
    };

    /**
     * Action: Pick batch
     */
    WarehouseLayoutGrid.prototype._action_pick_batch = function(cell_id) {
        var self = this;
        rpc.query({
            model: 'hdi.warehouse.location.grid',
            method: 'action_pick_batch',
            args: [[cell_id]],
        }).done(function(result) {
            self._execute_action(result);
        });
    };

    /**
     * Action: Transfer warehouse
     */
    WarehouseLayoutGrid.prototype._action_transfer_warehouse = function(cell_id) {
        var self = this;
        rpc.query({
            model: 'hdi.warehouse.location.grid',
            method: 'action_transfer_warehouse',
            args: [[cell_id]],
        }).done(function(result) {
            self._execute_action(result);
        });
    };

    /**
     * Action: View details
     */
    WarehouseLayoutGrid.prototype._action_view_details = function(cell_id) {
        var self = this;
        rpc.query({
            model: 'hdi.warehouse.location.grid',
            method: 'action_view_location_details',
            args: [[cell_id]],
        }).done(function(result) {
            self._execute_action(result);
        });
    };

    /**
     * Execute action result
     */
    WarehouseLayoutGrid.prototype._execute_action = function(result) {
        if (result && result.type === 'ir.actions.act_window') {
            // Open form/wizard
            var action = result;
            var do_action = require('web.core').action_manager.do_action;
            do_action(action);
        }
    };

    /**
     * Refresh grid
     */
    WarehouseLayoutGrid.prototype.refresh = function(layout_data) {
        this.init(this.container, layout_data);
    };

    /**
     * Export for use
     */
    return {
        WarehouseLayoutGrid: WarehouseLayoutGrid,
    };
});
