# -*- coding: utf-8 -*-
"""
🧪 Test Stock Location Layout Model
====================================
Tests for the core layout model and its methods
"""

from odoo.tests import TransactionCase, tagged
from odoo.exceptions import ValidationError
import json


@tagged('post_install', '-at_install', 'warehouse_map')
class TestStockLocationLayout(TransactionCase):
    
    def setUp(self):
        super().setUp()
        
        # Create warehouse
        self.warehouse = self.env['stock.warehouse'].create({
            'name': 'Test Warehouse',
            'code': 'TWH',
        })
        
        # Create locations
        self.zone = self.env['stock.location'].create({
            'name': 'Zone-Test',
            'location_id': self.warehouse.lot_stock_id.id,
            'usage': 'view',
            'location_type': 'zone',
        })
        
        self.rack = self.env['stock.location'].create({
            'name': 'Rack-T1',
            'location_id': self.zone.id,
            'usage': 'view',
            'location_type': 'rack',
        })
        
        self.bin = self.env['stock.location'].create({
            'name': 'Bin-T1-01',
            'location_id': self.rack.id,
            'usage': 'internal',
            'location_type': 'bin',
        })
        
        # Create product with serial tracking
        self.product = self.env['product.product'].create({
            'name': 'Test Product',
            'type': 'product',
            'tracking': 'serial',
        })
        
        # Create serial
        self.serial = self.env['stock.lot'].create({
            'name': 'TEST-SERIAL-001',
            'product_id': self.product.id,
            'company_id': self.env.company.id,
        })
    
    def test_create_layout(self):
        """Test creating a basic layout"""
        layout = self.env['stock.location.layout'].create({
            'warehouse_id': self.warehouse.id,
            'location_id': self.bin.id,
            'location_type': 'bin',
            'x': 100.0,
            'y': 150.0,
            'width': 80.0,
            'height': 100.0,
            'z_level': 1,
            'color': '#f39c12',
        })
        
        self.assertTrue(layout.id)
        self.assertEqual(layout.x, 100.0)
        self.assertEqual(layout.y, 150.0)
        self.assertEqual(layout.location_type, 'bin')
    
    def test_layout_json_generation(self):
        """Test JSON layout generation"""
        layout = self.env['stock.location.layout'].create({
            'warehouse_id': self.warehouse.id,
            'location_id': self.bin.id,
            'location_type': 'bin',
            'x': 100.0,
            'y': 150.0,
            'width': 80.0,
            'height': 100.0,
        })
        
        # Check JSON is valid
        self.assertTrue(layout.layout_json)
        data = json.loads(layout.layout_json)
        
        self.assertEqual(data['type'], 'bin')
        self.assertEqual(data['x'], 100.0)
        self.assertEqual(data['y'], 150.0)
        self.assertEqual(data['location_id'], self.bin.id)
    
    def test_dimension_constraint(self):
        """Test width/height must be positive"""
        with self.assertRaises(ValidationError):
            self.env['stock.location.layout'].create({
                'warehouse_id': self.warehouse.id,
                'location_id': self.bin.id,
                'location_type': 'bin',
                'x': 100.0,
                'y': 150.0,
                'width': -50.0,  # Invalid
                'height': 100.0,
            })
    
    def test_stock_quantity_computation(self):
        """Test stock quantity is computed correctly"""
        layout = self.env['stock.location.layout'].create({
            'warehouse_id': self.warehouse.id,
            'location_id': self.bin.id,
            'location_type': 'bin',
            'x': 100.0,
            'y': 150.0,
        })
        
        # Initially no stock
        self.assertEqual(layout.stock_quantity, 0.0)
        self.assertEqual(layout.lot_count, 0)
        
        # ⚠️ Create quant using proper Odoo method (NOT direct create)
        # In real scenario, this happens through validated picking
        self.env['stock.quant']._update_available_quantity(
            self.product,
            self.bin,
            10.0,
            lot_id=self.serial
        )
        
        # Recompute
        layout._compute_stock_info()
        
        self.assertEqual(layout.stock_quantity, 10.0)
        self.assertEqual(layout.lot_count, 1)
    
    def test_hierarchical_layout(self):
        """Test parent-child layout relationship"""
        rack_layout = self.env['stock.location.layout'].create({
            'warehouse_id': self.warehouse.id,
            'location_id': self.rack.id,
            'location_type': 'rack',
            'x': 50.0,
            'y': 50.0,
        })
        
        bin_layout = self.env['stock.location.layout'].create({
            'warehouse_id': self.warehouse.id,
            'location_id': self.bin.id,
            'location_type': 'bin',
            'parent_layout_id': rack_layout.id,
            'x': 60.0,
            'y': 60.0,
        })
        
        self.assertEqual(bin_layout.parent_layout_id, rack_layout)
        self.assertIn(bin_layout, rack_layout.child_layout_ids)
    
    def test_highlight_by_serial(self):
        """Test highlighting bin by serial number scan"""
        layout = self.env['stock.location.layout'].create({
            'warehouse_id': self.warehouse.id,
            'location_id': self.bin.id,
            'location_type': 'bin',
            'x': 100.0,
            'y': 150.0,
        })
        
        # Add stock with serial
        self.env['stock.quant']._update_available_quantity(
            self.product,
            self.bin,
            1.0,
            lot_id=self.serial
        )
        
        # Test highlight
        result = layout.highlight_bin_by_serial('TEST-SERIAL-001')
        
        self.assertFalse('error' in result)
        self.assertEqual(result['lot_name'], 'TEST-SERIAL-001')
        self.assertTrue(len(result['bins']) > 0)
        self.assertEqual(result['bins'][0]['location_id'], self.bin.id)
    
    def test_highlight_by_nonexistent_serial(self):
        """Test scanning non-existent serial"""
        layout = self.env['stock.location.layout'].create({
            'warehouse_id': self.warehouse.id,
            'location_id': self.bin.id,
            'location_type': 'bin',
        })
        
        result = layout.highlight_bin_by_serial('NONEXISTENT')
        
        self.assertTrue('error' in result)
        self.assertEqual(result['error'], 'Serial number not found')
    
    def test_action_open_location_quants(self):
        """Test opening quants view for a bin"""
        layout = self.env['stock.location.layout'].create({
            'warehouse_id': self.warehouse.id,
            'location_id': self.bin.id,
            'location_type': 'bin',
        })
        
        action = layout.action_open_location_quants()
        
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'stock.quant')
        self.assertIn(('location_id', '=', self.bin.id), action['domain'])
    
    def test_action_open_location_lots(self):
        """Test opening lots/serials view for a bin"""
        layout = self.env['stock.location.layout'].create({
            'warehouse_id': self.warehouse.id,
            'location_id': self.bin.id,
            'location_type': 'bin',
        })
        
        # Add stock
        self.env['stock.quant']._update_available_quantity(
            self.product,
            self.bin,
            1.0,
            lot_id=self.serial
        )
        
        action = layout.action_open_location_lots()
        
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'stock.lot')
        self.assertIn(self.serial.id, action['domain'][0][2])
    
    def test_get_warehouse_layout_data(self):
        """Test getting complete warehouse layout"""
        zone_layout = self.env['stock.location.layout'].create({
            'warehouse_id': self.warehouse.id,
            'location_id': self.zone.id,
            'location_type': 'zone',
            'x': 0.0,
            'y': 0.0,
        })
        
        data = self.env['stock.location.layout'].get_warehouse_layout_data(
            self.warehouse.id
        )
        
        self.assertEqual(data['warehouse_id'], self.warehouse.id)
        self.assertTrue('zones' in data)
        self.assertTrue(len(data['zones']) > 0)
