# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class StockMoveLineIntegration(models.Model):
    """Tích hợp stock.move.line với warehouse map"""
    _inherit = 'stock.move.line'
    
    # Map position for source location
    source_map_x = fields.Integer(
        related='location_id.coordinate_x',
        string='Source X',
        readonly=True
    )
    
    source_map_y = fields.Integer(
        related='location_id.coordinate_y',
        string='Source Y',
        readonly=True
    )
    
    # Map position for destination location
    dest_map_x = fields.Integer(
        related='location_dest_id.coordinate_x',
        string='Dest X',
        readonly=True
    )
    
    dest_map_y = fields.Integer(
        related='location_dest_id.coordinate_y',
        string='Dest Y',
        readonly=True
    )
    
    # Show map positions
    show_map_positions = fields.Boolean(
        compute='_compute_show_map_positions',
        help='Show if locations have map coordinates'
    )
    
    map_movement_path = fields.Char(
        compute='_compute_map_movement_path',
        string='Map Path',
        help='Movement path on warehouse map'
    )
    
    @api.depends('location_id.coordinate_x', 'location_dest_id.coordinate_x')
    def _compute_show_map_positions(self):
        """Check if locations have map coordinates"""
        for line in self:
            line.show_map_positions = bool(
                (line.location_id.coordinate_x or line.location_id.coordinate_y) and
                (line.location_dest_id.coordinate_x or line.location_dest_id.coordinate_y)
            )
    
    @api.depends('source_map_x', 'source_map_y', 'dest_map_x', 'dest_map_y')
    def _compute_map_movement_path(self):
        """Generate map movement path display"""
        for line in self:
            if line.show_map_positions:
                line.map_movement_path = f"[{line.source_map_x},{line.source_map_y}] → [{line.dest_map_x},{line.dest_map_y}]"
            else:
                line.map_movement_path = False
    
    def action_show_movement_on_map(self):
        """Show movement path on warehouse map"""
        self.ensure_one()
        
        # Find warehouse map
        warehouse = self.picking_id.picking_type_id.warehouse_id
        if not warehouse:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Warehouse'),
                    'message': _('Cannot find warehouse for this move.'),
                    'type': 'warning',
                }
            }
        
        warehouse_map = self.env['warehouse.map'].search([
            ('warehouse_id', '=', warehouse.id)
        ], limit=1)
        
        if not warehouse_map:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Map'),
                    'message': _('No warehouse map configured for this warehouse.'),
                    'type': 'warning',
                }
            }
        
        return {
            'type': 'ir.actions.client',
            'tag': 'warehouse_map_view',
            'name': f'Movement - {self.product_id.name}',
            'context': {
                'active_id': warehouse_map.id,
                'highlight_location_ids': [self.location_id.id, self.location_dest_id.id],
                'show_movement_path': True,
                'movement_source': [self.source_map_x, self.source_map_y],
                'movement_dest': [self.dest_map_x, self.dest_map_y],
            }
        }
    
    def _action_done(self):
        """Override to update map after move done"""
        # Call parent
        result = super()._action_done()
        
        # Update warehouse map
        self._update_map_after_move()
        
        return result
    
    def _update_map_after_move(self):
        """Update warehouse map display after move completion"""
        for line in self:
            if line.quantity == 0:
                continue
            
            # Update destination quant position
            if line.location_dest_id.usage == 'internal':
                domain = [
                    ('location_id', '=', line.location_dest_id.id),
                    ('product_id', '=', line.product_id.id),
                    ('quantity', '>', 0),
                ]
                
                if line.lot_id:
                    domain.append(('lot_id', '=', line.lot_id.id))
                
                quants = self.env['stock.quant'].search(domain)
                
                for quant in quants:
                    # Auto-assign map position from location if not set
                    if not quant.posx and not quant.posy:
                        if line.location_dest_id.coordinate_x or line.location_dest_id.coordinate_y:
                            quant.write({
                                'posx': line.location_dest_id.coordinate_x or 0,
                                'posy': line.location_dest_id.coordinate_y or 0,
                                'posz': line.location_dest_id.coordinate_z or 0,
                                'display_on_map': True,
                            })
