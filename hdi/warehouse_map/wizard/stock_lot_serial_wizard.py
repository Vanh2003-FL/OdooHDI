# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime


class StockLotSerialWizard(models.TransientModel):
    _name = 'stock.lot.serial.wizard'
    _description = 'Wizard gom Serial vào Lot'

    picking_id = fields.Many2one('stock.picking', string='Phiếu nhập kho', required=True, readonly=True)
    move_line_ids = fields.Many2many('stock.move.line', string='Move Line (Serial)', required=True)
    
    # Chọn sản phẩm - auto detect hoặc cho user chọn
    product_id = fields.Many2one('product.product', string='Sản phẩm', 
                                  domain="[('tracking', 'in', ('lot', 'serial'))]", readonly=True)
    
    # Danh sách move_line với serial_number để user nhập
    wizard_move_line_ids = fields.One2many('stock.wizard.move.line', 'wizard_id', 
                                            string='Sản phẩm')
    
    @api.model
    def default_get(self, fields_list):
        """Auto-detect product và populate wizard_move_line"""
        result = super().default_get(fields_list)
        
        # Lấy move_line từ context
        if self._context.get('default_move_line_ids'):
            move_line_data = self._context['default_move_line_ids']
            move_line_ids = []
            
            # Handle tuple format (6, 0, [ids]) from context
            if isinstance(move_line_data, list):
                if move_line_data and isinstance(move_line_data[0], tuple):
                    # Format: [(6, 0, [1, 2, 3, ...])]
                    move_line_ids = move_line_data[0][2] if len(move_line_data[0]) > 2 else []
                else:
                    # Direct list: [1, 2, 3, ...]
                    move_line_ids = move_line_data
            
            if move_line_ids:
                # Lấy danh sách move_line record
                move_lines = self.env['stock.move.line'].browse(move_line_ids)
                
                # Filter valid move_lines
                move_lines = move_lines.exists()
                
                if move_lines:
                    # Kiểm tra tất cả cùng product không
                    products = move_lines.mapped('product_id').ids
                    if len(set(products)) == 1:
                        # Tất cả cùng product → auto detect
                        result['product_id'] = products[0]
                    
                    # Populate wizard_move_line với TẤT CẢ move_lines
                    wizard_lines = []
                    for idx, move_line in enumerate(move_lines, 1):
                        wizard_lines.append((0, 0, {
                            'move_line_id': move_line.id,
                            'product_id': move_line.product_id.id,
                            'sequence': idx * 10,
                        }))
                    result['wizard_move_line_ids'] = wizard_lines
        
        return result
    
    # Tạo hoặc chọn lot
    lot_create_option = fields.Selection([
        ('create_new', 'Tạo lot mới'),
        ('select_existing', 'Chọn lot đã tạo'),
    ], string='Tùy chọn', default='create_new', required=True)
    
    # Option: Tạo lot mới
    lot_name = fields.Char(string='Tên Lot mới')
    lot_barcode = fields.Char(string='Barcode Lot')
    
    # Option: Chọn lot từ dropdown
    existing_lot_id = fields.Many2one('stock.lot', string='Chọn Lot đã tạo',
                                       domain="[('product_id', '=', product_id)]")
    
    total_serials = fields.Integer(string='Tổng serial', compute='_compute_total_serials')
    
    @api.depends('wizard_move_line_ids')
    def _compute_total_serials(self):
        """Đếm số serial được chọn"""
        for wizard in self:
            wizard.total_serials = len(wizard.wizard_move_line_ids)
    
    @api.onchange('lot_create_option')
    def _onchange_lot_create_option(self):
        """Clear fields khi switch giữa các option"""
        if self.lot_create_option == 'create_new':
            self.existing_lot_id = False
        else:
            self.lot_name = ''
            self.lot_barcode = ''
    
    def action_confirm_assign_serials(self):
        """Gom serial vào lot và cập nhật move_line"""
        self.ensure_one()
        
        if not self.move_line_ids:
            raise UserError(_('Vui lòng chọn ít nhất 1 move_line!'))
        
        if not self.product_id:
            raise UserError(_('Vui lòng chọn sản phẩm!'))
        
        if not self.wizard_move_line_ids:
            raise UserError(_('Không có sản phẩm nào để xử lý!'))
        
        # Kiểm tra tất cả serial đã được nhập
        for wml in self.wizard_move_line_ids:
            if not wml.serial_number or not wml.serial_number.strip():
                raise UserError(_(
                    f'❌ Serial chưa được nhập cho sản phẩm: {wml.product_id.name}'
                ))
        
        # Kiểm tra serial không trùng
        serial_numbers = [wml.serial_number.strip() for wml in self.wizard_move_line_ids]
        if len(serial_numbers) != len(set(serial_numbers)):
            raise UserError(_('❌ Có serial bị trùng lặp!'))
        
        # Bước 1: Tạo hoặc lấy lot_id
        if self.lot_create_option == 'create_new':
            if not self.lot_name:
                raise UserError(_('Vui lòng nhập tên lot!'))
            
            # Tạo lot mới
            lot_vals = {
                'product_id': self.product_id.id,
                'name': self.lot_name,
            }
            
            if self.lot_barcode:
                lot_vals['barcode'] = self.lot_barcode
            
            lot = self.env['stock.lot'].create(lot_vals)
        else:
            if not self.existing_lot_id:
                raise UserError(_('Vui lòng chọn lot!'))
            lot = self.existing_lot_id
        
        # Bước 2: Cập nhật tất cả move_line với lot_id này
        filtered_move_lines = self.move_line_ids.filtered(
            lambda x: x.product_id.id == self.product_id.id
        )
        filtered_move_lines.write({'lot_id': lot.id})
        
        # Bước 3: Tạo stock.serial.item records từ wizard_move_line_ids
        for wml in self.wizard_move_line_ids:
            self.env['stock.serial.item'].create({
                'lot_id': lot.id,
                'serial_number': wml.serial_number.strip(),
                'sequence': wml.sequence,
            })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.lot',
            'res_id': lot.id,
            'view_mode': 'form',
            'target': 'current',
        }


class StockWizardMoveLine(models.TransientModel):
    _name = 'stock.wizard.move.line'
    _description = 'Move Line trong Wizard Gom Serial'
    _order = 'sequence'
    
    wizard_id = fields.Many2one('stock.lot.serial.wizard', string='Wizard', ondelete='cascade')
    move_line_id = fields.Many2one('stock.move.line', string='Move Line', readonly=True)
    product_id = fields.Many2one('product.product', string='Sản phẩm', readonly=True)
    serial_number = fields.Char(string='Serial/Barcode', required=True)
    sequence = fields.Integer(string='Thứ tự', default=10)
