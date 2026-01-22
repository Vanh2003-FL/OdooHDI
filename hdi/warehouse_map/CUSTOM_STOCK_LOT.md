# 📋 Hướng dẫn: Custom stock.lot với chức năng warehouse map

## ✅ Các thay đổi đã thực hiện

### 1. **Tạo model kế thừa `stock.lot`**
   - File: `hdi/warehouse_map/models/stock_lot_warehouse.py`
   - Thêm các field từ `hdi.batch` vào `stock.lot`:
     - ✅ `posx`, `posy`, `posz` (vị trí X, Y, Z)
     - ✅ `display_on_map` (hiển thị trên sơ đồ)
     - ✅ `batch_type` (loại: pallet, LPN, container)
     - ✅ `total_quantity`, `available_quantity`, `reserved_quantity` (tính toán từ quants)
     - ✅ `quant_count`, `product_count` (đếm quants và sản phẩm)
     - ✅ Các field physical: `weight`, `volume`, `height`, `width`, `length`

### 2. **Cập nhật `warehouse_map.py`**
   - Thay đổi từ `hdi.batch` → `stock.lot`
   - Dùng phương thức `get_lot_data_for_map()` để lấy dữ liệu

### 3. **Tạo views cho stock.lot**
   - File: `hdi/warehouse_map/views/stock_lot_warehouse_views.xml`
   - Thêm tab "Sơ đồ Kho" vào form stock.lot
   - Hiển thị tất cả field warehouse mapping
   - Thêm nút "Xem trên Sơ đồ Kho"

---

## 🎯 Cách sử dụng

### **Tạo 1 lot trên sơ đồ kho:**

1. **Truy cập**: Stock → Lot/Serial Numbers
2. **Tạo mới lot**:
   ```
   - Lot/Serial Number: LOT-001
   - Product: Sản phẩm A (nếu 1 sản phẩm)
   - Tab "Sơ đồ Kho":
     - Warehouse Map: Chọn sơ đồ
     - Vị trí X: 3
     - Vị trí Y: 5
     - Vị trí Z: 2 (tầng)
     - Display on Map: ✓
     - Batch Type: Pallet
   - Save
   ```

3. **Lot sẽ tự động hiển thị trên sơ đồ** ở vị trí X=3, Y=5, Z=2

### **Lot chứa nhiều sản phẩm:**

Với custom này, `stock.lot` vẫn có `product_id` (bắt buộc). Nhưng `quant_ids` có thể chứa nhiều sản phẩm:

```python
# Khi tạo quants cho lot
stock_quant.create({
    'lot_id': lot.id,
    'product_id': product_A.id,
    'location_id': loc.id,
    'quantity': 50,
})
stock_quant.create({
    'lot_id': lot.id,
    'product_id': product_B.id,
    'location_id': loc.id,
    'quantity': 30,
})

# Lot sẽ hiển thị:
# - product_count = 2
# - total_quantity = 80
```

---

## ⚙️ Tính toán tự động

### Các field được tính toán từ quants:
```python
total_quantity = SUM(quant.quantity) 
available_quantity = SUM(quant.available_quantity)
reserved_quantity = SUM(quant.reserved_quantity)
product_count = COUNT(DISTINCT product_id)
quant_count = COUNT(quant)
```

---

## 🔄 So sánh: Trước vs Sau

### **Trước (dùng hdi.batch)**
```
hdi.batch (Pallet)
├─ posx, posy, posz ✓
├─ display_on_map ✓
├─ product_id (1 sản phẩm)
├─ quant_ids (many2many gián tiếp)
└─ warehouse_map_data()
```

### **Sau (dùng stock.lot)**
```
stock.lot (Lot + Warehouse Map)
├─ posx, posy, posz ✓
├─ display_on_map ✓
├─ product_id (bắt buộc)
├─ quant_ids (many2many từ core Odoo)
├─ batch_type, weight, volume ✓
├─ total_quantity, available_qty ✓
└─ get_lot_data_for_map()
```

**✅ Lợi ích**: 
- ✓ Chỉ 1 model duy nhất
- ✓ Tích hợp sâu với Odoo (accounting, stock moves)
- ✓ Lot tracking + warehouse mapping trong 1 chỗ
- ✓ Không cần migrate từ batch sang lot

---

## 📝 Ghi chú quan trọng

1. **`product_id` vẫn bắt buộc** trong `stock.lot` (qui tắc Odoo)
   - Nếu lot có nhiều sản phẩm, set `product_id` là sản phẩm "chính"
   - Hoặc set thành sản phẩm đầu tiên

2. **`warehouse_map_id` giúp filter**
   - Khi tạo lot, có thể chọn sơ đồ kho nào sẽ chứa lot này

3. **Backward compatible**
   - Nếu vẫn dùng `hdi.batch`, không ảnh hưởng
   - Nhưng nên migrate dần sang `stock.lot`

---

## 🚀 Bước tiếp theo (nếu muốn migrate từ batch)

### Migrate dữ liệu từ `hdi.batch` → `stock.lot`:

```python
# Script migration
batches = self.env['hdi.batch'].search([])
for batch in batches:
    # Tạo lot từ batch
    lot = self.env['stock.lot'].create({
        'name': batch.name,
        'product_id': batch.product_id.id,
        'posx': batch.posx,
        'posy': batch.posy,
        'posz': batch.posz,
        'display_on_map': batch.display_on_map,
        'batch_type': batch.batch_type,
        'location_id': batch.location_id.id,
        'weight': batch.weight,
        'volume': batch.volume,
        # ... copy field khác
    })
    
    # Update quants
    quants = self.env['stock.quant'].search([('batch_id', '=', batch.id)])
    quants.write({'lot_id': lot.id})
```

---

## 📞 Hỗ trợ

Nếu có vấn đề:
1. Kiểm tra database migration (chạy update module)
2. Xóa cache browser
3. Test trên 1 lot mới trước

