# 📦 HDI Warehouse Map - Module Summary

## 🎯 Module Overview

**Module Name:** `hdi_warehouse_map`  
**Version:** 18.0.1.0.0  
**Odoo Version:** 18.0  
**Category:** Inventory/Warehouse  
**Author:** HDI  
**License:** LGPL-3

---

## ✨ Key Features

### 1. **Hierarchical Location Structure**
```
Stock (Warehouse)
└── Zone (view)
    └── Rack (view)
        └── Bin (internal) ← Actual storage location
```

### 2. **2D Warehouse Visualization**
- Interactive canvas-based map
- Drag & drop layout editor
- Stock quantity heatmap
- Real-time bin highlighting
- Click bin → view lots/serials
- Zoom & pan support

### 3. **3D Warehouse View**
- CSS 3D transforms rendering
- Mouse-controlled rotation
- Zoom with scroll wheel
- Visual-only (NO business logic)
- Bin highlighting on scan

**🔑 Bản chất 3D:**
- 📊 **Render từ dữ liệu 2D** (cùng model `stock.location.layout`)
- 📏 Chỉ **thêm trục Z** (chiều cao / tầng kệ)
- 🚫 **Không tạo nghiệp vụ mới**
- 🎨 **3D = visualization layer** trên nền 2D data

### 4. **Barcode Integration** 🔥
```
Scan Serial → Find lot_id → Read stock.quant → Get location_id → Highlight bin
```

### 5. **Layout Management**
- Model: `stock.location.layout` (1 model cho cả 2D & 3D)
- 2D base data: x, y, width, height, rotation
- 3D extension: z_level (tầng kệ), depth
- JSON format chung cho 2D/3D rendering
- Parent-child relationships

**💡 Kiến trúc:**
```
stock.location.layout (BASE)
    ├── 2D data: x, y, w, h, rotation
    ├── 3D extension: z_level, depth
    └── layout_json → render 2D hoặc 3D
```

---

## 📁 File Structure

```
hdi_warehouse_map/
├── __init__.py
├── __manifest__.py
├── README.md
├── INSTALL.md
│
├── controllers/
│   ├── __init__.py
│   └── warehouse_map_controller.py      # JSON API endpoints
│
├── data/
│   └── location_demo_data.xml           # Demo locations & layouts
│
├── models/
│   ├── __init__.py
│   ├── stock_location.py                # Extend stock.location
│   ├── stock_location_layout.py         # Layout metadata model ⭐
│   └── stock_quant.py                   # Extend stock.quant (READ ONLY)
│
├── security/
│   └── ir.model.access.csv              # Access rights
│
├── static/
│   └── src/
│       ├── css/
│       │   └── warehouse_map.css        # Styles
│       ├── js/
│       │   ├── warehouse_map_2d.js      # 2D renderer ⭐
│       │   ├── warehouse_map_3d.js      # 3D renderer ⭐
│       │   └── warehouse_map_controller.js  # Main controller
│       └── xml/
│           └── warehouse_map.xml        # Templates
│
├── tests/
│   ├── __init__.py
│   ├── test_stock_location_layout.py    # Model tests
│   └── test_warehouse_map_api.py        # API tests
│
└── views/
    ├── menu_views.xml                   # Menus
    ├── stock_location_layout_views.xml  # Layout config views
    ├── stock_location_views.xml         # Location extension
    ├── warehouse_map_templates.xml      # Web assets
    └── warehouse_map_views.xml          # Main map views
```

---

## 🗃️ Database Schema

### Model: `stock.location.layout`

**📌 1 Model duy nhất cho cả 2D và 3D**

| Field | Type | Layer | Description |
|-------|------|-------|-------------|
| `location_id` | Many2one(stock.location) | Both | Link to location |
| `warehouse_id` | Many2one(stock.warehouse) | Both | Parent warehouse |
| `location_type` | Selection | Both | 'zone', 'rack', 'bin' |
| `x`, `y` | Float | **2D Base** | Position (px) |
| `width`, `height` | Float | **2D Base** | Dimensions (px) |
| `rotation` | Float | **2D Base** | Rotation angle (degrees) |
| `z_level` | Integer | **3D Ext** | Height level (0=floor, 1,2,3=shelves) |
| `depth` | Float | **3D Ext** | 3D depth (px) |
| `color` | Char | Hex color code |
| `view_type` | Selection | '2d', '3d', 'both' |
| `layout_json` | Text | Complete JSON layout (computed) |
| `parent_layout_id` | Many2one(self) | Parent layout |
| `child_layout_ids` | One2many | Child layouts |
| `stock_quantity` | Float | Current stock (computed) |
| `lot_count` | Integer | Number of lots (computed) |

---

## 🔌 API Endpoints

### 1. Get Warehouse Layout
```
GET /warehouse_map/layout/<warehouse_id>

Response:
{
  "warehouse_id": 1,
  "zones": [
    {
      "id": 10,
      "type": "zone",
      "location_id": 50,
      "location_name": "Zone-A",
      "x": 50, "y": 50, "w": 600, "h": 400,
      "racks": [...]
    }
  ]
}
```

### 2. Scan Serial Number
```
POST /warehouse_map/scan_serial
{
  "serial_number": "SN-001"
}

Response:
{
  "lot_id": 123,
  "lot_name": "SN-001",
  "product_name": "Product A",
  "bins": [
    {
      "layout_id": 45,
      "location_id": 301,
      "location_name": "WH/Zone-A/Bin-A1-01",
      "x": 80, "y": 90, "z": 1,
      "quantity": 5
    }
  ]
}
```

### 3. Get Bin Details
```
GET /warehouse_map/bin_details/<location_id>

Response:
{
  "location_id": 301,
  "location_name": "Bin-A1-01",
  "quants": [
    {
      "product_name": "Product A",
      "lot_name": "SN-001",
      "quantity": 5,
      "available_quantity": 3
    }
  ],
  "total_quantity": 5,
  "lot_count": 1
}
```

### 4. Update Layout (Drag & Drop)
```
POST /warehouse_map/update_layout
{
  "layout_id": 45,
  "x": 150,
  "y": 200,
  "width": 120,
  "height": 100
}

Response:
{
  "success": true,
  "layout_json": {...}
}
```

### 5. Search Product
```
POST /warehouse_map/search_product
{
  "warehouse_id": 1,
  "product_name": "Product A"
}

Response:
{
  "bins": [
    {
      "layout_id": 45,
      "location_id": 301,
      "location_name": "WH/Zone-A/Bin-A1-01",
      "x": 80, "y": 90, "z": 1,
      "products": [...]
    }
  ]
}
```

### 6. Get Heatmap
```
GET /warehouse_map/heatmap/<warehouse_id>

Response:
{
  "301": 85.5,  // location_id: percentage
  "302": 42.3,
  "303": 67.8
}
```

---

## 🎨 UI Components

### Menus
```
Inventory
└── Warehouse Map
    ├── 2D Warehouse Map
    ├── 3D Warehouse View
    └── Layout Configuration (Manager only)
```

### Views
1. **2D Map View** - Canvas-based interactive map
2. **3D View** - CSS 3D transforms
3. **Layout Form** - Configure location coordinates
4. **Layout Tree** - List all layouts

### Controls
- Barcode scanner input
- Product search
- Heatmap toggle
- Labels toggle
- Edit mode toggle
- Zoom controls

---

## ⚠️ Critical Rules

### ❌ NEVER DO
```python
# FORBIDDEN - Module NEVER creates inventory
self.env['stock.quant'].create({...})
self.env['stock.move'].create({...})
self.env['stock.move.line'].create({...})
```

### ✅ ALWAYS DO
```python
# CORRECT - Only READ stock data
quants = self.env['stock.quant'].search([
    ('location_id', '=', location_id),
    ('quantity', '>', 0)
])
quantity = sum(quants.mapped('quantity'))
```

### 📌 Principles
1. **2D/3D CHỈ ĐỌC** stock.quant + lot_id
2. **KHÔNG TẠO** tồn kho
3. **Tồn kho chỉ tạo qua:**
   - Purchase Order → Receipt (validated)
   - Manufacturing Order
   - Inventory Adjustment
   - Internal Transfer (validated)

---

## 🧪 Testing

### Run All Tests
```bash
odoo-bin -d test_db -i hdi_warehouse_map --test-enable --stop-after-init
```

### Run Specific Tests
```bash
odoo-bin -d test_db --test-tags warehouse_map
```

### Test Coverage
- ✅ Model creation & validation
- ✅ JSON layout generation
- ✅ Stock computation (READ only)
- ✅ Hierarchical relationships
- ✅ Serial highlighting
- ✅ API endpoints
- ✅ Layout updates

---

## 📊 Performance Notes

### Optimizations
- JSON layout cached in computed field
- API pagination for large datasets
- Efficient canvas rendering
- CSS 3D (no WebGL overhead)

### Scalability
- **< 1000 bins:** Excellent performance
- **1000-5000 bins:** Good (consider lazy loading)
- **> 5000 bins:** Requires optimization:
  - Virtual scrolling
  - Zone-based loading
  - LOD (Level of Detail) for 3D

---

## 🔗 Dependencies

```python
'depends': [
    'stock',       # Core inventory
    'barcodes',    # Barcode scanning
    'web',         # Web framework
]
```

---

## 🚀 Deployment Checklist

- [ ] Module installed in addons path
- [ ] Database updated (`-u hdi_warehouse_map`)
- [ ] Demo data loaded (optional)
- [ ] Locations configured
- [ ] Layouts configured with coordinates
- [ ] User access rights assigned
- [ ] Barcode scanner tested
- [ ] 2D map loads correctly
- [ ] 3D view renders properly
- [ ] API endpoints responding

---

## 📞 Support & Maintenance

### Common Maintenance Tasks

**Update Layout Coordinates:**
```python
Inventory → Warehouse Map → Layout Configuration
# Select layout → Edit X/Y/Z values
```

**Add New Locations:**
```python
Inventory → Configuration → Locations
# Create → Configure Layout
```

**Troubleshoot Display Issues:**
```bash
# Clear browser cache
# Check JavaScript console
# Verify layout_json field populated
```

---

## 🎓 Training Materials

### For Warehouse Staff
1. How to read 2D map
2. Using barcode scanner
3. Finding products on map
4. Understanding heatmap colors

### For Managers
1. Configuring layouts
2. Adjusting coordinates
3. Managing locations
4. Interpreting stock data

### For Developers
1. Extending layout model
2. Customizing renderers
3. Adding new APIs
4. Integration with other modules

---

## 📝 Version History

### v18.0.1.0.0 (Initial Release)
- ✅ 2D warehouse map with drag & drop
- ✅ 3D warehouse visualization
- ✅ Barcode scanner integration
- ✅ Stock heatmap
- ✅ Hierarchical location structure
- ✅ JSON API for map data
- ✅ Demo data included

---

## 🎉 Success Metrics

After deployment, measure:
- ⏱️ Time to locate products (should decrease by 50%+)
- 📊 Inventory accuracy (should improve)
- 🚀 Pick/pack efficiency (should increase)
- 👥 User adoption rate
- 🐛 Bug reports / support tickets

---

**✨ Module Complete and Ready for Production! 🗺️**
