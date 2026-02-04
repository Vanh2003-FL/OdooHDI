# -*- coding: utf-8 -*-
"""
🔦 Barcode Scanning for Put-Away Process
Scan product/lot → Scan destination bin → Auto-assign

Workflow:
1. Open Put-Away Wizard from Receipt
2. Scan product barcode or lot/serial
3. Scan bin location barcode
4. System auto-assigns product to that bin
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class WarehousePutAwayBarcodeWizard(models.TransientModel):
    _name = 'warehouse.putaway.barcode.wizard'
    _description = 'Put-Away with Barcode Scanning'
    
    picking_id = fields.Many2one('stock.picking', string='Receipt', required=True, readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', related='picking_id.location_dest_id.warehouse_id', store=True)
    
    # Scanning workflow state
    state = fields.Selection([
        ('scan_product', 'Scan Product/Lot'),
        ('scan_bin', 'Scan Destination Bin'),
        ('done', 'Assignment Complete')
    ], default='scan_product', string='Scan Step')
    
    scanned_barcode = fields.Char('Scanned Barcode', help='Last scanned barcode')
    current_product_id = fields.Many2one('product.product', string='Current Product', readonly=True)
    current_lot_id = fields.Many2one('stock.lot', string='Current Lot/Serial', readonly=True)
    current_move_line_id = fields.Many2one('stock.move.line', string='Current Move Line', readonly=True)
    target_bin_id = fields.Many2one('stock.location', string='Target Bin', readonly=True)
    
    assigned_line_ids = fields.One2many('warehouse.putaway.barcode.line', 'wizard_id', string='Assigned Lines')
    
    message = fields.Text('Scan Result Message', readonly=True)
    
    @api.model
    def default_get(self, fields_list):
        """Load from context"""
        res = super().default_get(fields_list)
        
        if 'picking_id' not in res and self.env.context.get('active_id'):
            res['picking_id'] = self.env.context['active_id']
        
        return res
    
    def action_scan_barcode(self):
        """
        🔦 Process barcode scan based on current state
        """
        self.ensure_one()
        
        if not self.scanned_barcode:
            self.message = '⚠️ Please scan a barcode!'
            return self._return_wizard_view()
        
        barcode = self.scanned_barcode.strip()
        
        if self.state == 'scan_product':
            return self._process_product_scan(barcode)
        elif self.state == 'scan_bin':
            return self._process_bin_scan(barcode)
        
        return self._return_wizard_view()
    
    def _process_product_scan(self, barcode):
        """
        Step 1: Scan product or lot/serial barcode
        """
        # Try to find lot/serial first
        lot = self.env['stock.lot'].search([('name', '=', barcode)], limit=1)
        
        if lot:
            # Find move line with this lot in the picking
            move_line = self.env['stock.move.line'].search([
                ('picking_id', '=', self.picking_id.id),
                ('lot_id', '=', lot.id),
                ('state', 'in', ['assigned', 'confirmed'])
            ], limit=1)
            
            if not move_line:
                self.message = f'❌ Lot/Serial {barcode} not found in this receipt!'
                return self._return_wizard_view()
            
            self.current_lot_id = lot
            self.current_product_id = move_line.product_id
            self.current_move_line_id = move_line
            self.state = 'scan_bin'
            self.message = f'✅ Scanned: {move_line.product_id.name} [{lot.name}]\n🎯 Now scan DESTINATION BIN barcode...'
            
        else:
            # Try to find product by barcode
            product = self.env['product.product'].search([
                '|', ('barcode', '=', barcode), ('default_code', '=', barcode)
            ], limit=1)
            
            if not product:
                self.message = f'❌ Product with barcode {barcode} not found!'
                return self._return_wizard_view()
            
            # Find move line with this product
            move_line = self.env['stock.move.line'].search([
                ('picking_id', '=', self.picking_id.id),
                ('product_id', '=', product.id),
                ('state', 'in', ['assigned', 'confirmed']),
                ('id', 'not in', self.assigned_line_ids.mapped('move_line_id').ids)
            ], limit=1)
            
            if not move_line:
                self.message = f'❌ Product {product.name} not found in this receipt or already assigned!'
                return self._return_wizard_view()
            
            self.current_product_id = product
            self.current_move_line_id = move_line
            self.current_lot_id = move_line.lot_id
            self.state = 'scan_bin'
            lot_info = f'[{move_line.lot_id.name}]' if move_line.lot_id else ''
            self.message = f'✅ Scanned: {product.name} {lot_info}\n🎯 Now scan DESTINATION BIN barcode...'
        
        self.scanned_barcode = ''  # Clear for next scan
        return self._return_wizard_view()
    
    def _process_bin_scan(self, barcode):
        """
        Step 2: Scan destination bin barcode
        """
        # Find location by barcode
        location = self.env['stock.location'].search([('barcode', '=', barcode)], limit=1)
        
        if not location:
            self.message = f'❌ Bin location with barcode {barcode} not found!'
            return self._return_wizard_view()
        
        if location.usage != 'internal':
            self.message = f'❌ Location {location.name} is not a valid storage bin!'
            return self._return_wizard_view()
        
        # Assign move line to this bin
        self.current_move_line_id.write({
            'location_dest_id': location.id
        })
        
        # Record assignment
        self.env['warehouse.putaway.barcode.line'].create({
            'wizard_id': self.id,
            'move_line_id': self.current_move_line_id.id,
            'product_id': self.current_product_id.id,
            'lot_id': self.current_lot_id.id if self.current_lot_id else False,
            'destination_location_id': location.id,
        })
        
        product_name = self.current_product_id.name
        lot_info = f'[{self.current_lot_id.name}]' if self.current_lot_id else ''
        bin_name = location.complete_name
        
        self.message = f'✅✅ ASSIGNED:\n{product_name} {lot_info}\n→ {bin_name}\n\n📦 Scan next product barcode...'
        
        # Reset for next product
        self.state = 'scan_product'
        self.current_product_id = False
        self.current_lot_id = False
        self.current_move_line_id = False
        self.target_bin_id = False
        self.scanned_barcode = ''
        
        return self._return_wizard_view()
    
    def _return_wizard_view(self):
        """Return to wizard view to show messages"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'warehouse.putaway.barcode.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def action_complete_putaway(self):
        """
        ✅ Complete put-away and return to picking
        """
        self.ensure_one()
        
        if not self.assigned_line_ids:
            raise UserError(_('No products have been assigned yet!'))
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'res_id': self.picking_id.id,
            'view_mode': 'form',
            'target': 'current',
        }


class WarehousePutAwayBarcodeLine(models.TransientModel):
    _name = 'warehouse.putaway.barcode.line'
    _description = 'Barcode Put-Away Assignment Record'
    
    wizard_id = fields.Many2one('warehouse.putaway.barcode.wizard', required=True, ondelete='cascade')
    move_line_id = fields.Many2one('stock.move.line', string='Move Line', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    lot_id = fields.Many2one('stock.lot', string='Lot/Serial', readonly=True)
    destination_location_id = fields.Many2one('stock.location', string='Assigned Bin', readonly=True)
    assigned_datetime = fields.Datetime('Assigned At', default=fields.Datetime.now, readonly=True)
