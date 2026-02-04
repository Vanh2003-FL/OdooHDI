{
    'name': 'Warehouse Diagram',
    'version': '15.0.1.0.0',
    'category': 'Inventory',
    'description': """
        Module Sơ đồ Kho cho hệ thống quản lý tồn kho.
        Cho phép thiết kế sơ đồ 2D kho, quản lý kệ (Shelves), ô hàng (Bins), 
        và khu vực không lưu trữ (Areas).
    """,
    'author': 'HDI',
    'depends': ['stock', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/warehouse_view_views.xml',
        'views/warehouse_area_views.xml',
        'views/warehouse_shelves_views.xml',
        'views/warehouse_bin_views.xml',
        'views/warehouse_diagram_menu.xml',
    ],
    'static': {
        'description': 'Contains CSS and JS for warehouse diagram',
    },
    'installable': True,
    'auto_install': False,
    'application': False,
}
