/** @odoo-module **/

import { Component, onWillStart, onMounted, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog";

export class WarehouseLayoutView extends Component {
    static props = {
        "*": true,
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.dialog = useService("dialog");

        this.state = useState({
            mapData: null,
            loading: true,
            contextMenu: {
                visible: false,
                x: 0,
                y: 0,
                gridId: null,
                batchData: null,
            },
            searchQuery: '',
            zoomLevel: 100,
        });

        onWillStart(async () => {
            await this.loadMapData();
        });

        onMounted(() => {
            const closeMenuHandler = this.closeContextMenu.bind(this);
            document.addEventListener('click', closeMenuHandler);
            return () => {
                document.removeEventListener('click', closeMenuHandler);
            };
        });
    }

    getMapId() {
        return this.props.action?.context?.active_id
            || this.props.actionId
            || this.props.context?.active_id
            || this.state.mapData?.id
            || 1;
    }

    async loadMapData() {
        try {
            this.state.loading = true;
            const mapId = this.getMapId();
            
            const layoutData = await this.orm.read(
                'hdi.warehouse.layout',
                [mapId],
                ['name', 'warehouse_id', 'rows', 'columns', 'levels', 'total_slots', 
                 'occupied_slots', 'empty_slots', 'utilization_rate', 'location_grid_ids', 'state']
            );

            if (layoutData.length) {
                const layout = layoutData[0];
                
                // Lấy chi tiết grid cells
                const gridCells = await this.orm.read(
                    'hdi.warehouse.layout.grid',
                    layout.location_grid_ids,
                    ['row', 'column', 'level', 'location_code', 'batch_id', 'is_occupied']
                );

                // Lấy chi tiết batch
                const batchIds = gridCells
                    .filter(cell => cell.batch_id)
                    .map(cell => cell.batch_id[0]);

                let batchDetails = {};
                if (batchIds.length) {
                    const batches = await this.orm.read(
                        'hdi.batch',
                        batchIds,
                        ['id', 'name', 'product_id', 'lot_id', 'total_quantity', 'create_date']
                    );
                    batches.forEach(batch => {
                        batchDetails[batch.id] = batch;
                    });
                }

                this.state.mapData = {
                    id: layout.id,
                    name: layout.name,
                    warehouse_name: layout.warehouse_id[1],
                    rows: layout.rows,
                    columns: layout.columns,
                    levels: layout.levels,
                    total_slots: layout.total_slots,
                    occupied_slots: layout.occupied_slots,
                    empty_slots: layout.empty_slots,
                    utilization_rate: layout.utilization_rate,
                    state: layout.state,
                    rowsArray: Array.from({length: layout.rows}, (_, i) => i),
                    columnsArray: Array.from({length: layout.columns}, (_, i) => i),
                    gridCells: gridCells,
                    batchDetails: batchDetails,
                };
            }
        } catch (error) {
            this.notification.add('Lỗi khi tải dữ liệu sơ đồ kho', {
                type: 'danger',
            });
            console.error(error);
        } finally {
            this.state.loading = false;
        }
    }

    getBatchAtPosition(row, col) {
        if (!this.state.mapData || !this.state.mapData.gridCells) {
            return null;
        }

        const cell = this.state.mapData.gridCells.find(
            c => c.row === row && c.column === col
        );

        if (cell && cell.batch_id) {
            return this.state.mapData.batchDetails[cell.batch_id[0]];
        }
        return null;
    }

    getCellClass(batch, row, col) {
        let classes = ['o_warehouse_cell'];
        
        if (batch) {
            classes.push('o_warehouse_cell_occupied');
            
            // Color based on days in warehouse
            const daysInWarehouse = this.getDaysInWarehouse(batch);
            if (daysInWarehouse > 90) {
                classes.push('o_warehouse_cell_red');
            } else if (daysInWarehouse > 60) {
                classes.push('o_warehouse_cell_orange');
            } else {
                classes.push('o_warehouse_cell_green');
            }
        } else {
            classes.push('o_warehouse_cell_empty');
        }

        // Apply search filter
        if (this.state.searchQuery) {
            const batchName = batch?.name || '';
            const productName = batch?.product_id?.[1] || '';
            const query = this.state.searchQuery.toLowerCase();
            
            if (!batchName.toLowerCase().includes(query) && 
                !productName.toLowerCase().includes(query)) {
                classes.push('o_hidden');
            }
        }

        return classes.join(' ');
    }

    getDaysInWarehouse(batch) {
        if (!batch || !batch.create_date) return 0;
        const createDate = new Date(batch.create_date);
        const today = new Date();
        return Math.floor((today - createDate) / (1000 * 60 * 60 * 24));
    }

    onCellClick(ev, row, col) {
        const batch = this.getBatchAtPosition(row, col);
        
        if (batch) {
            this.showContextMenu(ev, row, col, batch);
        }
    }

    showContextMenu(ev, row, col, batch) {
        ev.stopPropagation();
        this.state.contextMenu = {
            visible: true,
            x: ev.clientX,
            y: ev.clientY,
            row: row,
            col: col,
            batchData: batch,
        };
    }

    closeContextMenu() {
        this.state.contextMenu.visible = false;
    }

    async onMenuAction(action) {
        const batch = this.state.contextMenu.batchData;
        this.closeContextMenu();

        switch(action) {
            case 'details':
                this.action.doAction({
                    type: 'ir.actions.act_window',
                    res_model: 'hdi.batch',
                    res_id: batch.id,
                    views: [[false, 'form']],
                    target: 'current',
                });
                break;
            case 'remove':
                if (confirm('Xóa sản phẩm này khỏi sơ đồ?')) {
                    try {
                        const gridCell = this.state.mapData.gridCells.find(
                            c => c.batch_id?.[0] === batch.id
                        );
                        if (gridCell) {
                            await this.orm.write(
                                'hdi.warehouse.layout.grid',
                                [gridCell.id],
                                { batch_id: false }
                            );
                            this.notification.add('Đã xóa sản phẩm', {type: 'success'});
                            await this.loadMapData();
                        }
                    } catch (error) {
                        this.notification.add('Lỗi khi xóa', {type: 'danger'});
                    }
                }
                break;
        }
    }

    updateZoom(direction) {
        const step = 10;
        if (direction === 'in' && this.state.zoomLevel < 200) {
            this.state.zoomLevel += step;
        } else if (direction === 'out' && this.state.zoomLevel > 50) {
            this.state.zoomLevel -= step;
        }
    }
}

// Đăng ký client action
registry.category("client_actions").add("warehouse_map_dialog", WarehouseLayoutView);

// Đăng ký view (optional - dự phòng)
registry.category("views").add("warehouse_layout_map", {
    type: "warehouse_layout_map",
    display_name: "Sơ đồ Kho",
    icon: "fa-th",
    multiRecord: false,
    Controller: WarehouseLayoutView,
    props: (genericProps, view, dataset) => ({
        ...genericProps,
        action: genericProps.action,
    }),
});
