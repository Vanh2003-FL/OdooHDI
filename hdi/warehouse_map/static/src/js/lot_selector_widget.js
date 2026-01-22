/** @odoo-module **/

import { Component, onWillStart, useState, useEffect } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { xml } from "@odoo/owl";

const LOT_SELECTOR_TEMPLATE = xml`
    <div class="lot-selector-widget">
        <t t-if="state.loading">
            <span class="text-muted">Đang tải...</span>
        </t>
        <t t-else="">
            <select 
                class="form-select"
                t-att-disabled="props.readonly"
                t-on-change="onLotChange"
                t-att-value="state.selectedLotId || ''">
                <option value="">-- Chọn Lot/Pallet/LPN --</option>
                <t t-foreach="state.lots" t-as="lot" t-key="lot.id">
                    <option t-att-value="lot.id" t-att-selected="state.selectedLotId === lot.id">
                        <t t-esc="lot.name"/>
                    </option>
                </t>
            </select>
        </t>
    </div>
`;

class LotSelectorWidget extends Component {
    static template = LOT_SELECTOR_TEMPLATE;
    static props = {
        value: { type: Number, optional: true },
        record: { type: Object, optional: false },
        readonly: { type: Boolean, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        
        // Get initial value from record data
        const initialValue = this.props.record.data.lot_id || null;
        
        this.state = useState({
            lots: [],
            loading: true,
            selectedLotId: initialValue,
        });

        onWillStart(async () => {
            await this.loadLots();
        });

        useEffect(
            () => {
                // Update state if value changes from parent
                const newValue = this.props.record.data.lot_id || null;
                if (this.state.selectedLotId !== newValue) {
                    this.state.selectedLotId = newValue;
                }
            }, () => [this.props.record.data.lot_id]
        );
    }

    async loadLots() {
        try {
            // Load all lots (stock.lot with display_on_map = True)
            const lots = await this.orm.searchRead('stock.lot', [['display_on_map', '=', true]], ['id', 'name']);
            this.state.lots = lots;
            this.state.loading = false;
        } catch (error) {
            console.error("Error loading lots:", error);
            this.state.loading = false;
        }
    }

    onLotChange(event) {
        const lotId = parseInt(event.target.value) || false;
        this.state.selectedLotId = lotId;

        // Update the parent record
        console.log('[LotSelector] Selected lot ID:', lotId);
        this.props.record.update({ lot_id: lotId });
    }
}

registry.category("fields").add("lot_selector", LotSelectorWidget);

export default LotSelectorWidget;
