# -*- coding: utf-8 -*-
{
    'name': 'Warehouse 3D Layout & Optimization',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Warehouse',
    'summary': '3D warehouse layout visualization, bin management, and picking route optimization',
    'description': '''
        Advanced warehouse management system featuring:
        - 3D/2D warehouse layout visualization
        - Bin-level inventory management
        - Intelligent picking route optimization (FIFO/LIFO/Zone/Optimal)
        - Real-time heatmap analytics
        - Warehouse performance metrics
        - Cross-dock support
    ''',
    'author': 'HDI',
    'license': 'LGPL-3',
    'depends': [
        'stock',
        'web',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/warehouse_advanced_access.csv',
        'data/ir_sequence.xml',
        'data/ir_cron.xml',
        'data/crossdock_cron.xml',
        'data/server_action.xml',
        'views/dashboard_action.xml',
        'views/menu.xml',
        'views/warehouse_layout_views.xml',
        'views/warehouse_bin_views.xml',
        'views/stock_location_views.xml',
        'views/stock_warehouse_views.xml',
        'views/stock_picking_views.xml',
        'views/warehouse_analytics_views.xml',
        'views/warehouse_advanced_views.xml',
        'data/warehouse_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # Three.js library (CDN or local copy)
            ('include', 'web._assets_primary_variables'),
            # Core viewers
            'hdi_warehouse_3d/static/src/js/warehouse_3d_viewer.js',
            'hdi_warehouse_3d/static/src/js/warehouse_2d_viewer.js',
            'hdi_warehouse_3d/static/src/js/route_animator.js',
            # Field widgets and components
            'hdi_warehouse_3d/static/src/js/warehouse_field_widget.js',
            'hdi_warehouse_3d/static/src/js/warehouse_dashboard.js',
            'hdi_warehouse_3d/static/src/js/bin_editor.js',
            'hdi_warehouse_3d/static/src/js/camera_controls.js',
            # OWL templates
            'hdi_warehouse_3d/static/src/xml/warehouse_viewer_templates.xml',
            'hdi_warehouse_3d/static/src/xml/field_widget_templates.xml',
            # Styles
            'hdi_warehouse_3d/static/src/scss/warehouse_3d.scss',
            'hdi_warehouse_3d/static/src/scss/field_widgets.scss',
        ],
    },
    'external_dependencies': {
        'python': ['numpy'],  # For routing algorithms
    },
    'installable': True,
    'auto_install': False,
    'images': ['static/description/icon.png'],
}
