# -*- coding: utf-8 -*-
{
    'name': 'HDI Warehouse 3D Visualization',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Warehouse',
    'summary': '3D Warehouse Layout & Bin Visualization for Odoo Stock',
    'description': """
        3D Warehouse Layout Management
        ================================
        * Manage warehouse Areas, Shelves, and Bins
        * 3D visualization of stock.quant (inventory)
        * Visual mapping with stock.location
        * Real-time bin status display
    """,
    'author': 'HDI',
    'website': 'https://www.hdi.vn',
    'depends': ['base', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/warehouse_area_views.xml',
        'views/warehouse_shelf_views.xml',
        'views/stock_location_views.xml',
        'views/warehouse_3d_templates.xml',
        'views/menu_views.xml',
        'data/warehouse_3d_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hdi_warehouse_3d/static/src/js/warehouse_3d_widget.js',
            'hdi_warehouse_3d/static/src/css/warehouse_3d.css',
            'hdi_warehouse_3d/static/src/xml/warehouse_3d_templates.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
