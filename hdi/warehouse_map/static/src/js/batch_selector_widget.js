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
        value: [String, Number, { value: null }],
        record: { value: null },
        fieldName: { value: null },
        update: { value: null },
        readonly: { value: false },
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            batches: [],
            loading: true,
            selectedBatchId: this.props.value || null,
        });

        onWillStart(async () => {
            await this.loadBatches();
        });

        useEffect(() => {
            // Update state when value changes
            this.state.selectedBatchId = this.props.value || null;
        }, () => [this.props.value]);
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
        const batchId = parseInt(event.target.value) || null;
        this.state.selectedBatchId = batchId;
        
        // Update the record's batch_id field
        if (this.props.update) {
            this.props.update({ batch_id: batchId });
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
