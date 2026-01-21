/** @odoo-module **/

import { Component, onWillStart, useState, useEffect } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { xml } from "@odoo/owl";

const BATCH_SELECTOR_TEMPLATE = xml`
    <div class="batch-selector-widget">
        <t t-if="state.loading">
            <span class="text-muted">Đang tải...</span>
        </t>
        <t t-else="">
            <select 
                class="form-select"
                t-att-disabled="props.readonly"
                t-on-change="onBatchChange"
                t-att-value="state.selectedBatchId || ''">
                <option value="">-- Chọn Batch/LPN --</option>
                <t t-foreach="state.batches" t-as="batch" t-key="batch.id">
                    <option t-att-value="batch.id" t-att-selected="state.selectedBatchId === batch.id">
                        <t t-esc="batch.name"/>
                    </option>
                </t>
            </select>
        </t>
    </div>
`;

class BatchSelectorWidget extends Component {
    static template = BATCH_SELECTOR_TEMPLATE;
    static props = {
        value: { type: Number, optional: true },
        record: { type: Object, optional: false },
        readonly: { type: Boolean, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        
        // Get initial value from record data
        const initialValue = this.props.record.data.batch_id || null;
        
        this.state = useState({
            batches: [],
            loading: true,
            selectedBatchId: initialValue,
        });

        onWillStart(async () => {
            await this.loadBatches();
        });

        useEffect(() => {
            // Sync with record data changes
            const newValue = this.props.record.data.batch_id || null;
            if (this.state.selectedBatchId !== newValue) {
                this.state.selectedBatchId = newValue;
            }
        }, () => [this.props.record.data.batch_id]);
    }

    async loadBatches() {
        try {
            // Load all stored batches
            const batches = await this.orm.searchRead('hdi.batch', [['state', '=', 'stored']], ['id', 'name']);
            this.state.batches = batches;
            this.state.loading = false;
        } catch (error) {
            console.error("Error loading batches:", error);
            this.state.loading = false;
        }
    }

    onBatchChange(event) {
        const batchId = parseInt(event.target.value) || false;
        this.state.selectedBatchId = batchId;
        
        console.log('[BatchSelector] Selected batch ID:', batchId);
        
        // Update the actual record field - use the field name from props
        if (this.props.record && this.props.record.update) {
            this.props.record.update({ batch_id: batchId });
            console.log('[BatchSelector] Updated record.batch_id to', batchId);
        }
    }

    get selectedBatchName() {
        if (!this.state.selectedBatchId) return '';
        const batch = this.state.batches.find(b => b.id === this.state.selectedBatchId);
        return batch ? batch.name : '';
    }
}

registry.category("fields").add("batch_selector", {
    component: BatchSelectorWidget,
});

export { BatchSelectorWidget };
