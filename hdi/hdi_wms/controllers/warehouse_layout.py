# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
import json


class WarehouseLayoutController(http.Controller):

    @http.route('/hdi_wms/warehouse_3d/<int:layout_id>', auth='user', type='http')
    def warehouse_3d_view(self, layout_id, **kwargs):
        """Display 3D warehouse viewer"""
        layout = request.env['warehouse.layout'].browse(layout_id)
        
        if not layout.exists():
            return request.not_found()
        
        # Generate 3D data
        data_3d = layout.generate_3d_data()
        
        # Render template
        return request.render('hdi_wms.warehouse_3d_viewer_template', {
            'layout_name': layout.name,
            'warehouse_name': layout.warehouse_id.name,
            'max_x': layout.max_x,
            'max_y': layout.max_y,
            'max_z': layout.max_z,
            'warehouse_data_json': json.dumps(data_3d),
        })
