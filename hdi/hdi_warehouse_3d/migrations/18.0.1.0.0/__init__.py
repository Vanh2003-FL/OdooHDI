# -*- coding: utf-8 -*-

def migrate(cr, version):
    """
    Migration script for v1.0.0
    Add database indices for performance optimization
    """
    
    # Add index on warehouse.bin location_id (for fast lookup)
    cr.execute("""
        CREATE INDEX IF NOT EXISTS warehouse_bin_location_id_idx 
        ON warehouse_bin (location_id)
    """)
    
    # Add index on warehouse.bin shelf_id (for zone queries)
    cr.execute("""
        CREATE INDEX IF NOT EXISTS warehouse_bin_shelf_id_idx 
        ON warehouse_bin (shelf_id)
    """)
    
    # Add index on stock.picking.route picking_id
    cr.execute("""
        CREATE INDEX IF NOT EXISTS stock_picking_route_picking_id_idx 
        ON stock_picking_route (picking_id)
    """)
    
    # Add index on warehouse.heatmap layout_id and date
    cr.execute("""
        CREATE INDEX IF NOT EXISTS warehouse_heatmap_layout_date_idx 
        ON warehouse_heatmap (layout_id, date DESC)
    """)
    
    # Add index on warehouse.metrics layout_id and date
    cr.execute("""
        CREATE INDEX IF NOT EXISTS warehouse_metrics_layout_date_idx 
        ON warehouse_metrics (layout_id, date DESC)
    """)
    
    # Add GIN index on JSON fields for faster queries
    cr.execute("""
        CREATE INDEX IF NOT EXISTS warehouse_heatmap_data_idx 
        ON warehouse_heatmap USING gin (heatmap_data)
    """)
    
    cr.execute("""
        CREATE INDEX IF NOT EXISTS stock_picking_route_sequence_idx 
        ON stock_picking_route USING gin (optimized_sequence)
    """)

