/** @odoo-module **/

import { Component, onWillStart, onMounted, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import "./lot_selector_widget";  // Import lot selector widget

export class WarehouseMapView extends Component {
    static props = {
        "*": true,  // Accept all props from Odoo framework
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            mapData: null,
            loading: true,
            contextMenu: {
                visible: false,
                x: 0,
                y: 0,
                locationId: null,
                lotData: null,
            }
        });

        onWillStart(async () => {
            await this.loadMapData();
        });

        onMounted(() => {
            // Close context menu when clicking outside
            const closeMenuHandler = this.closeContextMenu.bind(this);
            document.addEventListener('click', closeMenuHandler);

            // Cleanup function để xóa event listener khi component unmount (Odoo 18)
            return () => {
                document.removeEventListener('click', closeMenuHandler);
            };
        });
    }

    getMapId() {
        // Get map ID from various possible sources
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
            const data = await this.orm.call(
                'warehouse.map',
                'get_map_data',
                [mapId]
            );

            // Tạo arrays cho rows và columns để có thể iterate trong template
            data.rowsArray = Array.from({length: data.rows}, (_, i) => i);
            data.columnsArray = Array.from({length: data.columns}, (_, i) => i);

            this.state.mapData = data;
        } catch (error) {
            this.notification.add('Lỗi khi tải dữ liệu sơ đồ kho', {
                type: 'danger',
            });
            console.error(error);
        } finally {
            this.state.loading = false;
        }
    }

    async refreshCell(row, col) {
        // Refresh only specific cell data without full reload
        try {
            console.log(`[RefreshCell] Updating cell [${col}, ${row}]`);
            const mapId = this.getMapId();
            console.log(`[RefreshCell] Map ID: ${mapId}`);

            const data = await this.orm.call(
                'warehouse.map',
                'get_map_data',
                [mapId]
            );

            console.log(`[RefreshCell] Data loaded:`, {
                lots: Object.keys(data.lots || {}).length,
                blocked_cells: Object.keys(data.blocked_cells || {}).length
            });

            // Tạo arrays cho rows và columns
            data.rowsArray = Array.from({length: data.rows}, (_, i) => i);
            data.columnsArray = Array.from({length: data.columns}, (_, i) => i);

            // Update entire mapData object to trigger OWL reactivity
            this.state.mapData = data;
            console.log('[RefreshCell] State updated, triggering re-render');

            // Always show success notification after refresh
            this.notification.add(
                'Đã cập nhật thành công',
                { type: 'success' }
            );
        } catch (error) {
            console.error('[RefreshCell] Error:', error);
            this.notification.add(
                'Lỗi khi cập nhật ô',
                { type: 'danger' }
            );
        }
    }

    getLotAtPosition(row, col) {
        if (!this.state.mapData || !this.state.mapData.lots) {
            return null;
        }

        // Tìm lot có vị trí x=col, y=row
        const positionKey = `${col}_${row}_0`; // z=0 mặc định
        return this.state.mapData.lots[positionKey] || null;
    }

    onCellClick(ev, row, col) {
        const lot = this.getLotAtPosition(row, col);
        const blockedCell = this.getBlockedCellAtPosition(row, col);

        // Nếu là blocked cell, hiển thị menu để unblock
        if (blockedCell) {
            ev.preventDefault();
            ev.stopPropagation();

            this.state.contextMenu = {
                visible: true,
                x: ev.clientX,
                y: ev.clientY,
                blockedCell: blockedCell,
                row: row,
                col: col,
            };
            return;
        }

        // Nếu ô trống, hiển thị menu: gán lot HOẶC chặn ô
        if (!lot) {
            ev.preventDefault();
            ev.stopPropagation();

            this.state.contextMenu = {
                visible: true,
                x: ev.clientX,
                y: ev.clientY,
                emptyCell: true,
                row: row,
                col: col,
            };
            return;
        }

        // Nếu có lot, hiển thị context menu thông thường
        ev.preventDefault();
        ev.stopPropagation();

        this.state.contextMenu = {
            visible: true,
            x: ev.clientX,
            y: ev.clientY,
            lotData: lot,
        };
    }

    async openAssignPositionWizard(row, col) {
        // Call Python method to create wizard record with all necessary data
        // This avoids RPC_ERROR from readonly field context defaults
        
        const lotId = this.props.context?.default_lot_id || false;
        
        // IMPORTANT: Ensure all IDs are integers, not objects
        const mapId = parseInt(this.state.mapData.id);
        const finalLotId = lotId ? parseInt(lotId) : false;
        
        console.log('[AssignWizard] Opening wizard for cell:', { row, col, finalLotId });
        console.log('[AssignWizard] Map ID:', mapId, 'Type:', typeof mapId);
        console.log('[AssignWizard] Lot ID:', finalLotId, 'Type:', typeof finalLotId);
        
        try {
            const action = await this.orm.call(
                'assign.lot.position.wizard',
                'create_from_map_click',
                [],
                {
                    warehouse_map_id: mapId,
                    posx: col,
                    posy: row,
                    posz: 0,
                    lot_id: finalLotId,
                }
            );
            
            console.log('[AssignWizard] Action received:', action);
            
            // Execute the returned action
            await this.action.doAction(action, {
                onClose: async () => {
                    console.log('[AssignWizard] onClose called');
                    await new Promise(resolve => setTimeout(resolve, 300));
                    console.log('[AssignWizard] Executing refresh...');
                    await this.refreshCell(row, col);
                }
            });
            
            console.log('[AssignWizard] Action executed successfully');
        } catch (error) {
            console.error('[AssignWizard] Error:', error);
            this.notification.add('Lỗi khi mở form gán vị trí', {
                type: 'danger',
            });
        }
    }

    async openBlockCellWizard(row, col) {
        this.closeContextMenu();

        await this.action.doAction(
            {
                name: `Chặn/Bỏ chặn ô [${col}, ${row}]`,
                type: 'ir.actions.act_window',
                res_model: 'block.cell.wizard',
                view_mode: 'form',
                views: [[false, 'form']],
                target: 'new',
                context: {
                    default_warehouse_map_id: this.state.mapData.id,
                    default_posx: col,
                    default_posy: row,
                    default_posz: 0,
                }
            },
            {
                onClose: async () => {
                    console.log('[BlockWizard] onClose called');
                    // Trong Odoo 17, onClose có thể không nhận result từ transient wizard
                    // Workaround: Luôn refresh với delay nhỏ
                    console.log('[BlockWizard] Waiting 300ms for wizard to complete...');
                    await new Promise(resolve => setTimeout(resolve, 300));
                    console.log('[BlockWizard] Executing refresh...');
                    await this.refreshCell(row, col);
                }
            }
        );
    }

    closeContextMenu() {
        this.state.contextMenu.visible = false;
    }

    async executeAction(actionType) {
        const { lotData } = this.state.contextMenu;

        if (!lotData) return;

        this.closeContextMenu();

        let actionData = {
            name: this.getActionName(actionType),
            type: 'ir.actions.act_window',
            res_model: 'location.action.wizard',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'new',
            context: {
                default_location_id: lotData.location_id,
                default_product_id: lotData.product_id,
                default_lot_id: lotData.lot_id,
                default_quantity: lotData.available_quantity,
                default_action_type: actionType,
            }
        };

        await this.action.doAction(actionData);

        // Reload map sau khi thực hiện action
        //setTimeout(() => this.loadMapData(), 1000);
    }

    async viewStock() {
        const { lotData } = this.state.contextMenu;
        if (!lotData) return;

        this.closeContextMenu();

        await this.action.doAction({
            name: 'Chi tiết Lot',
            type: 'ir.actions.act_window',
            res_model: 'stock.quant',
            res_id: lotData.quant_id,
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'current',
        });
    }

    async viewLocation() {
        const { lotData } = this.state.contextMenu;
        if (!lotData) return;

        this.closeContextMenu();

        await this.action.doAction({
            name: 'Vị trí kho',
            type: 'ir.actions.act_window',
            res_model: 'stock.location',
            res_id: lotData.location_id,
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'current',
        });
    }

    async removeFromMap() {
        const { lotData } = this.state.contextMenu;
        if (!lotData) return;

        this.closeContextMenu();

        // Confirm dialog
        const confirmed = confirm(`Xóa lot "${lotData.lot_name}" khỏi sơ đồ?\n\n(Hàng vẫn còn trong kho, chỉ ẩn khỏi sơ đồ)`);

        if (confirmed) {
            try {
                console.log('[RemoveFromMap] Removing lot from map:', lotData);

                // Get position before removal
                const row = lotData.y;
                const col = lotData.x;

                await this.orm.write('stock.quant', [lotData.quant_id], {
                    display_on_map: false,
                    posx: false,
                    posy: false,
                });

                console.log(`[RemoveFromMap] Removed, refreshing cell [${col}, ${row}]`);

                // Wait a bit for write to complete
                await new Promise(resolve => setTimeout(resolve, 200));

                // Refresh only affected cell (skip notification, we'll show our own)
                await this.refreshCell(row, col, true);

                // Show specific success message
                this.notification.add('Đã xóa lot khỏi sơ đồ', {
                    type: 'success',
                });
            } catch (error) {
                console.error('[RemoveFromMap] Error:', error);
                this.notification.add('Lỗi khi xóa lot khỏi sơ đồ', {
                    type: 'danger',
                });
            }
        }
    }

    getActionName(actionType) {
        const names = {
            'pick': 'Lấy hàng',
            'move': 'Chuyển vị trí',
            'transfer': 'Chuyển kho',
        };
        return names[actionType] || 'Action';
    }

    getCellClass(lot, row, col) {
        const classes = ['o_warehouse_map_cell'];

        // Kiểm tra blocked cell (priority cao nhất)
        if (this.isBlockedCell(row, col)) {
            classes.push('blocked_cell');
            return classes.join(' ');
        }

        if (!lot) return classes.join(' ');

        if (lot.quantity > 0) {
            classes.push('has_stock');
        }

        // Kiểm tra có hàng reserved không
        if (lot.reserved_quantity > 0) {
            classes.push('has_reserved');
        }

        return classes.join(' ');
    }

    formatQuantity(qty) {
        return parseFloat(qty).toFixed(2);
    }

    shouldAddRowSpacing(row) {
        const interval = this.state.mapData.row_spacing_interval;
        if (!interval || interval <= 0) return false;
        return (row + 1) % interval === 0 && (row + 1) < this.state.mapData.rows;
    }

    shouldAddColumnSpacing(col) {
        const interval = this.state.mapData.column_spacing_interval;
        if (!interval || interval <= 0) return false;
        return (col + 1) % interval === 0 && (col + 1) < this.state.mapData.columns;
    }

    getBlockedCellAtPosition(row, col) {
        const position_key = `${col}_${row}_0`;
        return this.state.mapData.blocked_cells?.[position_key] || null;
    }

    isBlockedCell(row, col) {
        return !!this.getBlockedCellAtPosition(row, col);
    }
}

WarehouseMapView.template = "warehouse_map.WarehouseMapView";
WarehouseMapView.components = {};

// Register the view as a client action (Odoo 18 requires both registries)
registry.category("actions").add("warehouse_map_view", WarehouseMapView);
registry.category("client_actions").add("warehouse_map_view", WarehouseMapView);

export { WarehouseMapView };