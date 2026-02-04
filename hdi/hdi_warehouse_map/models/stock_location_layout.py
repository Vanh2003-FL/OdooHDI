# -*- coding: utf-8 -*-
"""
📌 STOCK LOCATION LAYOUT - CHÌA KHÓA CHO 2D/3D
================================================
Model này lưu trữ metadata tọa độ cho warehouse map visualization.
Odoo KHÔNG CÓ khái niệm tọa độ mặc định → phải thêm model này.

Inspired by SKUSavvy architecture.
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import json


class StockLocationLayout(models.Model):
    _name = 'stock.location.layout'
    _description = 'Warehouse Location Layout Metadata'
    _order = 'warehouse_id, location_type, sequence'
    _rec_name = 'name'
    
    name = fields.Char(
        string='Layout Name',
        compute='_compute_name',
        store=True
    )
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        required=True,
        ondelete='cascade',
        index=True
    )
    location_id = fields.Many2one(
        'stock.location',
        string='Location',
        required=True,
        ondelete='cascade',
        domain="[('usage', '=', 'internal')]",
        index=True
    )
    location_type = fields.Selection([
        ('zone', 'Zone'),
        ('rack', 'Rack'),
        ('bin', 'Bin'),
    ], string='Location Type', required=True, default='bin')
    
    # 📐 2D Coordinates
    x = fields.Float(string='X Position', default=0.0, help='Horizontal position (px)')
    y = fields.Float(string='Y Position', default=0.0, help='Vertical position (px)')
    width = fields.Float(string='Width', default=100.0, help='Width (px)')
    height = fields.Float(string='Height', default=100.0, help='Height (px)')
    rotation = fields.Float(string='Rotation', default=0.0, help='Rotation angle (degrees)')
    
    # 📦 3D Coordinates
    z_level = fields.Integer(string='Z Level', default=0, help='Height level for 3D view (0=ground)')
    depth = fields.Float(string='Depth', default=50.0, help='Depth for 3D (px)')
    
    # 🎨 Visualization
    view_type = fields.Selection([
        ('2d', '2D View'),
        ('3d', '3D View'),
        ('both', 'Both 2D & 3D'),
    ], string='View Type', default='both')
    
    color = fields.Char(
        string='Color',
        default='#3498db',
        help='Hex color for visualization'
    )
    
    # 📋 Layout Data (JSON)
    layout_json = fields.Text(
        string='Layout JSON',
        help='Complete layout configuration in JSON format',
        compute='_compute_layout_json',
        store=True
    )
    
    # 🔢 Hierarchy
    parent_layout_id = fields.Many2one(
        'stock.location.layout',
        string='Parent Layout',
        ondelete='cascade',
        index=True
    )
    child_layout_ids = fields.One2many(
        'stock.location.layout',
        'parent_layout_id',
        string='Child Layouts'
    )
    
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(default=True)
    
    # 📊 Stock Information (Read-only, for visualization)
    stock_quantity = fields.Float(
        string='Stock Quantity',
        compute='_compute_stock_info',
        help='Total quantity in this location'
    )
    lot_count = fields.Integer(
        string='Lot/Serial Count',
        compute='_compute_stock_info',
        help='Number of lots/serials in this location'
    )
    
    @api.depends('location_id', 'location_type', 'warehouse_id')
    def _compute_name(self):
        for layout in self:
            if layout.location_id:
                loc_type = layout.location_type or 'location'
                layout.name = f"{loc_type.upper()}: {layout.location_id.name}"
            elif layout.location_type:
                layout.name = f"New {layout.location_type}"
            else:
                layout.name = "New Layout"
    
    @api.depends('location_id', 'x', 'y', 'width', 'height', 'z_level', 'rotation', 'location_type', 'child_layout_ids')
    def _compute_layout_json(self):
        """
        📌 Generate JSON layout for 2D/3D visualization
        This is the KEY data structure that 2D/3D viewers will consume.
        """
        for layout in self:
            # Skip if record not saved yet (NewId)
            if not layout.id or isinstance(layout.id, type(layout.id)) and not isinstance(layout.id, int):
                layout.layout_json = '{}'
                continue
            
            if not layout.location_id or not layout.location_id.id:
                layout.layout_json = '{}'
                continue
            
            data = {
                'id': layout.id,
                'type': layout.location_type,
                'location_id': layout.location_id.id,
                'location_name': layout.location_id.name,
                'location_complete_name': layout.location_id.complete_name,
                'x': layout.x,
                'y': layout.y,
                'w': layout.width,
                'h': layout.height,
                'z': layout.z_level,
                'rotation': layout.rotation,
                'color': layout.color,
                'view_type': layout.view_type,
                'stock_qty': layout.stock_quantity,
                'lot_count': layout.lot_count,
            }
            
            # Add children for hierarchical structures (Rack contains Bins)
            if layout.location_type == 'rack' and layout.child_layout_ids:
                data['bins'] = []
                for child in layout.child_layout_ids.sorted('sequence'):
                    if child.location_type == 'bin':
                        data['bins'].append({
                            'id': child.id,
                            'location_id': child.location_id.id,
                            'location_name': child.location_id.name,
                            'x': child.x,
                            'y': child.y,
                            'w': child.width,
                            'h': child.height,
                            'z': child.z_level,
                            'color': child.color,
                            'stock_qty': child.stock_quantity,
                            'lot_count': child.lot_count,
                        })
            
            # Add racks for zones
            if layout.location_type == 'zone' and layout.child_layout_ids:
                data['racks'] = []
                for child in layout.child_layout_ids.sorted('sequence'):
                    if child.location_type == 'rack':
                        rack_data = {
                            'id': child.id,
                            'location_id': child.location_id.id,
                            'location_name': child.location_id.name,
                            'x': child.x,
                            'y': child.y,
                            'w': child.width,
                            'h': child.height,
                            'z': child.z_level,
                            'rotation': child.rotation,
                            'color': child.color,
                            'bins': []
                        }
                        # Add bins in this rack
                        for bin_layout in child.child_layout_ids.sorted('sequence'):
                            if bin_layout.location_type == 'bin':
                                rack_data['bins'].append({
                                    'id': bin_layout.id,
                                    'location_id': bin_layout.location_id.id,
                                    'location_name': bin_layout.location_id.name,
                                    'x': bin_layout.x,
                                    'y': bin_layout.y,
                                    'w': bin_layout.width,
                                    'h': bin_layout.height,
                                    'z': bin_layout.z_level,
                                    'color': bin_layout.color,
                                    'stock_qty': bin_layout.stock_quantity,
                                    'lot_count': bin_layout.lot_count,
                                })
                        data['racks'].append(rack_data)
            
            layout.layout_json = json.dumps(data, ensure_ascii=False, indent=2)
    
    def _compute_stock_info(self):
        """
        ⚠️ CHÚ Ý: CHỈ ĐỌC stock.quant - KHÔNG BAO GIỜ TẠO!
        Read stock information for visualization purposes only.
        """
        for layout in self:
            if not layout.location_id:
                layout.stock_quantity = 0.0
                layout.lot_count = 0
                continue
            
            # 📖 READ ONLY - Get quants in this location
            quants = self.env['stock.quant'].search([
                ('location_id', '=', layout.location_id.id),
                ('quantity', '>', 0)
            ])
            
            layout.stock_quantity = sum(quants.mapped('quantity'))
            layout.lot_count = len(quants.filtered('lot_id').mapped('lot_id'))
    
    @api.constrains('x', 'y', 'width', 'height')
    def _check_dimensions(self):
        for layout in self:
            if layout.width <= 0 or layout.height <= 0:
                raise ValidationError(_('Width and Height must be positive values.'))
    
    def action_open_location_quants(self):
        """
        🔍 Open quants in this bin/location
        Khi click bin trên map → show danh sách lot/serial
        """
        self.ensure_one()
        return {
            'name': _('Stock in %s') % self.location_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'stock.quant',
            'view_mode': 'list,form',
            'domain': [
                ('location_id', '=', self.location_id.id),
                ('quantity', '>', 0)
            ],
            'context': {
                'default_location_id': self.location_id.id,
            }
        }
    
    def action_open_location_lots(self):
        """
        📦 Show lots/serials in this bin
        Click bin → domain: stock.quant(location_id=bin, lot_id!=False)
        """
        self.ensure_one()
        quants = self.env['stock.quant'].search([
            ('location_id', '=', self.location_id.id),
            ('lot_id', '!=', False),
            ('quantity', '>', 0)
        ])
        lot_ids = quants.mapped('lot_id').ids
        
        return {
            'name': _('Lots/Serials in %s') % self.location_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'stock.lot',
            'view_mode': 'list,form',
            'domain': [('id', 'in', lot_ids)],
            'context': {
                'default_location_id': self.location_id.id,
            }
        }
    
    def get_warehouse_layout_data(self, warehouse_id):
        """
        🗺️ Get complete warehouse layout for 2D/3D rendering
        Returns hierarchical structure: Warehouse > Zones > Racks > Bins
        Includes stock heatmap intensity for each bin
        """
        layouts = self.search([
            ('warehouse_id', '=', warehouse_id),
            ('active', '=', True)
        ], order='location_type desc, sequence')
        
        # Build hierarchical structure
        zones = layouts.filtered(lambda l: l.location_type == 'zone')
        
        result = {
            'warehouse_id': warehouse_id,
            'zones': []
        }
        
        for zone in zones:
            zone_data = json.loads(zone.layout_json)
            
            # Compute heatmap intensity for racks and bins
            if 'racks' in zone_data:
                for rack in zone_data['racks']:
                    if 'bins' in rack:
                        for bin_item in rack['bins']:
                            # Calculate stock intensity (0-1)
                            if bin_item['stock_qty'] > 0:
                                # Find layout to get capacity reference (max 1000 units per bin)
                                bin_layout = self.browse(bin_item['id'])
                                intensity = min(1.0, bin_item['stock_qty'] / 1000.0)
                                bin_item['stock_intensity'] = intensity
                                bin_item['total_quantity'] = bin_item['stock_qty']
                            else:
                                bin_item['stock_intensity'] = 0.0
                                bin_item['total_quantity'] = 0
            
            result['zones'].append(zone_data)
        
        return result
    
    def highlight_bin_by_serial(self, serial_number):
        """
        🔦 Highlight bin when scanning serial number
        
        Workflow:
        1. Scan Serial → Odoo xác định lot_id
        2. Tìm stock.quant
        3. Lấy location_id (bin)
        4. Highlight bin trên map
        """
        lot = self.env['stock.lot'].search([('name', '=', serial_number)], limit=1)
        if not lot:
            return {'error': 'Serial number not found'}
        
        # 📖 READ stock.quant to find location
        quants = self.env['stock.quant'].search([
            ('lot_id', '=', lot.id),
            ('quantity', '>', 0),
            ('location_id.usage', '=', 'internal')
        ])
        
        if not quants:
            return {'error': 'Serial not in stock'}
        
        # Find layouts for these locations
        bin_layouts = self.search([
            ('location_id', 'in', quants.mapped('location_id').ids),
            ('location_type', '=', 'bin')
        ])
        
        result = {
            'lot_id': lot.id,
            'lot_name': lot.name,
            'product_id': lot.product_id.id,
            'product_name': lot.product_id.name,
            'bins': []
        }
        
        for layout in bin_layouts:
            quant = quants.filtered(lambda q: q.location_id == layout.location_id)
            result['bins'].append({
                'layout_id': layout.id,
                'location_id': layout.location_id.id,
                'location_name': layout.location_id.complete_name,
                'x': layout.x,
                'y': layout.y,
                'z': layout.z_level,
                'quantity': sum(quant.mapped('quantity')),
            })
        
        return result
