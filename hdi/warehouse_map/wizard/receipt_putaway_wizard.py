# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ReceiptPutawayWizard(models.TransientModel):
    """Wizard đặc biệt cho luồng nhập kho - tự động suggest putaway từ map"""
    _name = 'receipt.putaway.wizard'
    _description = 'Receipt Putaway Wizard'
    
    picking_id = fields.Many2one('stock.picking', string='Receipt', required=True, 
                                 domain="[('picking_type_code', '=', 'incoming')]")
    warehouse_map_id = fields.Many2one('warehouse.map', string='Warehouse Map')
    
    auto_suggest = fields.Boolean(string='Auto-suggest from Map & Putaway', default=True)
    
    putaway_line_ids = fields.One2many(
        'receipt.putaway.line',
        'wizard_id',
        string='Putaway Lines'
    )
    
    preview_map = fields.Boolean(string='Preview on Map', default=False)
    
    @api.onchange('picking_id')
    def _onchange_picking_id(self):
        """Generate putaway lines from receipt"""
        if self.picking_id:
            # Find warehouse map
            warehouse = self.picking_id.picking_type_id.warehouse_id
            if warehouse:
                self.warehouse_map_id = self.env['warehouse.map'].search([
                    ('warehouse_id', '=', warehouse.id)
                ], limit=1)
            
            lines = []
            
            for move in self.picking_id.move_ids_without_package:
                # Find best putaway location
                best_location = self._find_best_putaway_location(move.product_id)
                
                lines.append((0, 0, {
                    'move_id': move.id,
                    'product_id': move.product_id.id,
                    'quantity': move.product_uom_qty,
                    'suggested_location_id': best_location.id if best_location else False,
                    'destination_location_id': best_location.id if best_location else move.location_dest_id.id,
                }))
            
            self.putaway_line_ids = lines
    
    def _find_best_putaway_location(self, product):
        """Find best putaway location using WMS + Map data"""
        # 1. Try putaway suggestion from hdi_wms
        putaway = self.env['hdi.putaway.suggestion'].search([
            ('product_id', '=', product.id),
            ('state', '=', 'pending')
        ], order='priority desc, suggested_location_priority asc', limit=1)
        
        if putaway and putaway.suggested_location_id:
            return putaway.suggested_location_id
        
        # 2. Find available location with map coordinates
        location = self.env['stock.location'].search([
            ('usage', '=', 'internal'),
            ('is_putable', '=', True),
            ('display_on_map', '=', True),
            '|',
            ('coordinate_x', '!=', False),
            ('coordinate_y', '!=', False),
        ], order='location_priority asc, putaway_sequence asc', limit=1)
        
        if location:
            return location
        
        # 3. Fallback to any available
        return self.env['stock.location'].search([
            ('usage', '=', 'internal'),
            ('is_putable', '=', True),
        ], order='location_priority asc', limit=1)
    
    def action_apply_putaway(self):
        """Apply putaway suggestions to receipt"""
        self.ensure_one()
        
        for line in self.putaway_line_ids:
            if line.destination_location_id:
                # Update move destination
                line.move_id.write({
                    'location_dest_id': line.destination_location_id.id
                })
                
                # Update or create move lines
                if line.move_id.move_line_ids:
                    line.move_id.move_line_ids.write({
                        'location_dest_id': line.destination_location_id.id
                    })
        
        # Mark putaway as done in WMS
        self.picking_id.write({'wms_state': 'putaway_done'})
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'res_id': self.picking_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_show_on_map(self):
        """Show putaway locations on warehouse map"""
        self.ensure_one()
        
        if not self.warehouse_map_id:
            raise UserError(_('No warehouse map found!'))
        
        # Collect all destination locations
        location_ids = self.putaway_line_ids.mapped('destination_location_id').ids
        
        return {
            'type': 'ir.actions.client',
            'tag': 'warehouse_map_view',
            'name': f'Putaway Locations - {self.picking_id.name}',
            'context': {
                'active_id': self.warehouse_map_id.id,
                'highlight_location_ids': location_ids,
                'picking_id': self.picking_id.id,
                'mode': 'putaway',
            }
        }


class ReceiptPutawayLine(models.TransientModel):
    """Putaway line for receipt"""
    _name = 'receipt.putaway.line'
    _description = 'Receipt Putaway Line'
    
    wizard_id = fields.Many2one('receipt.putaway.wizard', required=True, ondelete='cascade')
    move_id = fields.Many2one('stock.move', string='Move', required=True)
    
    product_id = fields.Many2one('product.product', string='Product')
    quantity = fields.Float(string='Quantity')
    
    suggested_location_id = fields.Many2one('stock.location', string='Suggested by WMS')
    destination_location_id = fields.Many2one('stock.location', string='Destination', required=True)
    
    # Map info
    map_x = fields.Integer(related='destination_location_id.coordinate_x', string='Map X')
    map_y = fields.Integer(related='destination_location_id.coordinate_y', string='Map Y')
    map_z = fields.Integer(related='destination_location_id.coordinate_z', string='Map Z')
    
    location_priority = fields.Integer(related='destination_location_id.location_priority', string='Priority')
    storage_type = fields.Selection(related='destination_location_id.storage_type', string='Storage Type')
    
    # Display
    location_display = fields.Char(compute='_compute_location_display')
    
    @api.depends('destination_location_id', 'map_x', 'map_y')
    def _compute_location_display(self):
        """Generate display text"""
        for line in self:
            if line.destination_location_id:
                display = line.destination_location_id.complete_name
                if line.map_x or line.map_y:
                    display += f" [{line.map_x},{line.map_y},{line.map_z}]"
                if line.storage_type:
                    display += f" ({dict(line._fields['storage_type'].selection).get(line.storage_type)})"
                line.location_display = display
            else:
                line.location_display = ''
