# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockPickingIntegration(models.Model):
    """Tích hợp warehouse_map vào toàn bộ luồng picking"""
    _inherit = 'stock.picking'
    
    # Link to warehouse map
    warehouse_map_id = fields.Many2one(
        'warehouse.map',
        string='Sơ đồ kho',
        compute='_compute_warehouse_map',
        store=True,
        help='Sơ đồ kho tương ứng với picking này'
    )
    
    # Map integration status
    map_integration_enabled = fields.Boolean(
        string='Map Integration',
        compute='_compute_map_integration',
        help='Picking này có tích hợp với warehouse map không'
    )
    
    # Show map button
    show_warehouse_map = fields.Boolean(
        compute='_compute_show_warehouse_map',
        help='Hiển thị nút mở warehouse map'
    )
    
    # Suggested locations from map
    suggested_location_ids = fields.Many2many(
        'stock.location',
        compute='_compute_suggested_locations',
        string='Vị trí gợi ý từ Map',
        help='Các vị trí được gợi ý dựa trên warehouse map và putaway strategy'
    )
    
    @api.depends('location_dest_id', 'picking_type_id')
    def _compute_warehouse_map(self):
        """Tìm warehouse map tương ứng"""
        for picking in self:
            warehouse = picking.picking_type_id.warehouse_id
            if warehouse:
                warehouse_map = self.env['warehouse.map'].search([
                    ('warehouse_id', '=', warehouse.id)
                ], limit=1)
                picking.warehouse_map_id = warehouse_map.id if warehouse_map else False
            else:
                picking.warehouse_map_id = False
    
    @api.depends('warehouse_map_id', 'picking_type_id')
    def _compute_map_integration(self):
        """Check if map integration is enabled"""
        for picking in self:
            picking.map_integration_enabled = bool(picking.warehouse_map_id)
    
    @api.depends('map_integration_enabled', 'state')
    def _compute_show_warehouse_map(self):
        """Show map button if integration enabled and picking is not done/cancel"""
        for picking in self:
            picking.show_warehouse_map = (
                picking.map_integration_enabled and 
                picking.state not in ('done', 'cancel')
            )
    
    @api.depends('picking_type_code', 'location_dest_id', 'move_ids_without_package')
    def _compute_suggested_locations(self):
        """Tính toán các vị trí gợi ý dựa trên map và putaway"""
        for picking in self:
            if not picking.map_integration_enabled:
                picking.suggested_location_ids = False
                continue
            
            # Chỉ suggest cho incoming pickings (receipt)
            if picking.picking_type_code != 'incoming':
                picking.suggested_location_ids = False
                continue
            
            # Get products in this picking
            products = picking.move_ids_without_package.mapped('product_id')
            
            if not products:
                picking.suggested_location_ids = False
                continue
            
            # Find available locations from putaway suggestions
            suggested_locations = self.env['stock.location']
            
            for product in products:
                # Get putaway suggestion
                putaway = self.env['hdi.putaway.suggestion'].search([
                    ('product_id', '=', product.id),
                    ('state', '=', 'suggested')
                ], order='priority desc, score desc', limit=3)
                
                if putaway:
                    suggested_locations |= putaway.mapped('location_id')
                else:
                    # Fallback: find best available location
                    available = self.env['stock.location'].search([
                        ('location_id', 'child_of', picking.location_dest_id.id),
                        ('usage', '=', 'internal'),
                        ('is_putable', '=', True),
                        ('display_on_map', '=', True),
                    ], order='location_priority asc', limit=3)
                    suggested_locations |= available
            
            picking.suggested_location_ids = suggested_locations
    
    def action_open_warehouse_map(self):
        """Mở warehouse map với highlight các vị trí liên quan"""
        self.ensure_one()
        
        if not self.warehouse_map_id:
            raise UserError(_('Không tìm thấy warehouse map cho picking này!'))
        
        # Prepare context with locations to highlight
        location_ids = []
        
        if self.picking_type_code == 'incoming':
            # Highlight destination locations
            location_ids = self.move_line_ids_without_package.mapped('location_dest_id').ids
            # Add suggested locations
            location_ids += self.suggested_location_ids.ids
        elif self.picking_type_code == 'outgoing':
            # Highlight source locations
            location_ids = self.move_line_ids_without_package.mapped('location_id').ids
        else:
            # Internal transfer: highlight both
            location_ids = self.move_line_ids_without_package.mapped('location_id').ids
            location_ids += self.move_line_ids_without_package.mapped('location_dest_id').ids
        
        return {
            'type': 'ir.actions.client',
            'tag': 'warehouse_map_view',
            'name': f'Sơ đồ kho - {self.name}',
            'context': {
                'active_id': self.warehouse_map_id.id,
                'highlight_location_ids': location_ids,
                'picking_id': self.id,
                'picking_type': self.picking_type_code,
            }
        }
    
    def action_assign_from_map(self):
        """Wizard để chọn locations từ map cho picking"""
        self.ensure_one()
        
        return {
            'name': _('Chọn vị trí từ Map'),
            'type': 'ir.actions.act_window',
            'res_model': 'picking.map.assignment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_picking_id': self.id,
                'default_warehouse_map_id': self.warehouse_map_id.id,
            }
        }
    
    def button_validate(self):
        """Override to update map after validation"""
        # Call parent method
        result = super().button_validate()
        
        # Update warehouse map after validation
        self._update_warehouse_map_after_validate()
        
        return result
    
    def _update_warehouse_map_after_validate(self):
        """Update warehouse map display after picking validation"""
        for picking in self:
            if not picking.map_integration_enabled:
                continue
            
            # Update quant positions on map
            for move_line in picking.move_line_ids_without_package:
                # For incoming: update destination location quants
                if picking.picking_type_code == 'incoming':
                    self._auto_assign_map_position(
                        move_line.location_dest_id,
                        move_line.product_id,
                        move_line.lot_id
                    )
                
                # For outgoing: clear source location if empty
                elif picking.picking_type_code == 'outgoing':
                    self._check_and_clear_map_position(
                        move_line.location_id,
                        move_line.product_id,
                        move_line.lot_id
                    )
                
                # For internal: update both
                else:
                    self._check_and_clear_map_position(
                        move_line.location_id,
                        move_line.product_id,
                        move_line.lot_id
                    )
                    self._auto_assign_map_position(
                        move_line.location_dest_id,
                        move_line.product_id,
                        move_line.lot_id
                    )
    
    def _auto_assign_map_position(self, location, product, lot=False):
        """Tự động gán vị trí trên map cho quant"""
        # Find quant
        domain = [
            ('location_id', '=', location.id),
            ('product_id', '=', product.id),
            ('quantity', '>', 0),
        ]
        if lot:
            domain.append(('lot_id', '=', lot.id))
        
        quants = self.env['stock.quant'].search(domain)
        
        for quant in quants:
            # If quant doesn't have position, assign from location coordinates
            if not quant.posx and not quant.posy:
                if location.coordinate_x or location.coordinate_y:
                    quant.write({
                        'posx': location.coordinate_x or 0,
                        'posy': location.coordinate_y or 0,
                        'posz': location.coordinate_z or 0,
                        'display_on_map': True,
                    })
    
    def _check_and_clear_map_position(self, location, product, lot=False):
        """Check nếu location empty thì clear position trên map"""
        domain = [
            ('location_id', '=', location.id),
            ('product_id', '=', product.id),
            ('quantity', '>', 0),
        ]
        if lot:
            domain.append(('lot_id', '=', lot.id))
        
        quants = self.env['stock.quant'].search(domain)
        
        # If no more stock, can optionally clear map display
        if not quants:
            pass  # Keep position for history, just quantity = 0
