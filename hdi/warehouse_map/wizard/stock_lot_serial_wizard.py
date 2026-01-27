# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime


class StockLotSerialWizard(models.TransientModel):
    _name = 'stock.lot.serial.wizard'
    _description = 'Wizard gom Serial vào Lot'

    picking_id = fields.Many2one('stock.picking', string='Phiếu nhập kho', required=True, readonly=True)
    move_line_ids = fields.Many2many('stock.move.line', string='Move Line (Serial)', required=True)
    product_id = fields.Many2one('product.product', string='Sản phẩm', related='move_line_ids.product_id', readonly=True)
    
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
    
    @api.depends('move_line_ids')
    def _compute_total_serials(self):
        """Đếm số serial được chọn"""
        for wizard in self:
            wizard.total_serials = len(wizard.move_line_ids)
    
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
        self.move_line_ids.write({'lot_id': lot.id})
        
        # Bước 3: Tạo stock.serial.item records cho từng move_line
        for idx, move_line in enumerate(self.move_line_ids, 1):
            serial_number = move_line.product_id.barcode or f'SERIAL_{idx}'
            
            # Kiểm tra serial đã tồn tại trong lot không
            existing_serial = self.env['stock.serial.item'].search([
                ('lot_id', '=', lot.id),
                ('serial_number', '=', serial_number)
            ], limit=1)
            
            if not existing_serial:
                self.env['stock.serial.item'].create({
                    'lot_id': lot.id,
                    'serial_number': serial_number,
                    'sequence': idx * 10,
                })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.lot',
            'res_id': lot.id,
            'view_mode': 'form',
            'target': 'current',
        }
