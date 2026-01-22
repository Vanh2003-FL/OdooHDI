# 📦 Migration: hdi.batch → stock.lot

## ✅ Những gì đã thay đổi

### 1. **Disabled hdi.batch workflow trong phiếu kho**
- ❌ Loại bỏ các action: `action_create_batch`, `action_suggest_putaway_all`
- ❌ Comment out fields: `batch_ids`, `batch_count`, `use_batch_management`
- ❌ Disable batch creation wizard
- ✅ Workflow lấy hàng vẫn hoạt động bình thường

### 2. **Thay thế bằng `stock.lot` + warehouse_map**
- ✅ Tạo `stock.lot` trực tiếp trong **Stock → Lot/Serial Numbers**
- ✅ Gán vị trí trên sơ đồ (X, Y, Z) từ tab **"Sơ đồ Kho"**
- ✅ Hiển thị trực tiếp trên sơ đồ kho 3D

### 3. **Cập nhật wizard**
- `assign_lot_position_wizard.py`: Thay `hdi.batch` → `stock.lot`
- View: Đổi `batch_id` → `lot_id`, `batch_name` → `lot_name`

---

## 🎯 Quy trình sử dụng mới

### **Trước (dùng hdi.batch)**
```
1. Tạo phiếu nhập kho
2. Ấn "Create Batch" → Wizard tạo batch
3. Gán vị trí cho batch từ sơ đồ
4. Batch hiển thị trên map
```

### **Sau (dùng stock.lot)**
```
1. Tạo phiếu nhập kho (bình thường)
2. Nhập hàng → tạo quants
3. Tạo Lot/Pallet từ Stock → Lot/Serial Numbers
   (Hoặc auto-create từ phiếu nhập)
4. Mở Lot → Tab "Sơ đồ Kho"
   - Chọn Warehouse Map
   - Nhập vị trí X, Y, Z
   - Ấn Save
5. Lot hiển thị trên map (có thể click để gán vị trí)
```

---

## 📝 Phiếu nhập kho (Stock Picking)

### **Workflow không thay đổi:**
- ✅ Tạo phiếu nhập/xuất kho
- ✅ Quét barcode sản phẩm
- ✅ Tạo quants
- ✅ Confirm phiếu
- ✅ Lấy hàng / Đóng gói

### **Phần thay đổi:**
- ❌ **KHÔNG** ấn "Create Batch" (bị disable)
- ✅ Thay thế bằng: Tạo Lot trong Stock menu

---

## 🔄 Chuyển dữ liệu cũ (nếu cần)

Nếu có dữ liệu `hdi.batch` cũ muốn migrate sang `stock.lot`:

```python
# Script migration
batches = self.env['hdi.batch'].search([])
for batch in batches:
    lot_vals = {
        'name': batch.name,
        'product_id': batch.product_id.id,  # Sản phẩm chính
        'posx': batch.posx,
        'posy': batch.posy,
        'posz': batch.posz,
        'display_on_map': batch.display_on_map,
        'batch_type': batch.batch_type,
        'location_id': batch.location_id.id,
        'weight': batch.weight,
        'volume': batch.volume,
    }
    
    # Tạo lot
    lot = self.env['stock.lot'].create(lot_vals)
    
    # Update quants: batch_id → lot_id
    quants = self.env['stock.quant'].search([('batch_id', '=', batch.id)])
    quants.write({'lot_id': lot.id})
    
    print(f"✓ Migrated batch {batch.name} → lot {lot.name}")
```

---

## ⚠️ Lưu ý quan trọng

1. **`stock.lot` có product_id bắt buộc**
   - Nếu lot có nhiều sản phẩm, set `product_id` = sản phẩm "chính"
   - Quants vẫn có thể chứa nhiều sản phẩm

2. **Warehouse Map filter theo `warehouse_map_id`**
   - Khi tạo lot, chọn warehouse map sẽ hiển thị trên đó

3. **`hdi.batch` vẫn tồn tại (backward compat)**
   - Không bị xóa, chỉ disabled workflow
   - Nếu code khác dùng, vẫn hoạt động

4. **Các wizard batch không hoạt động**
   - `hdi.batch.creation.wizard` → Dùng Lot form
   - `hdi.putaway.wizard` → Dùng Lot assignment wizard

---

## 🚀 Lợi ích

✅ **Đơn giản hơn** - Dùng sẵn model chuẩn của Odoo  
✅ **Tích hợp tốt** - Lot tracking + accounting + warehouse map  
✅ **Ít phụ thuộc** - Không cần batch-specific code  
✅ **Dễ mở rộng** - Có thể thêm field vào stock.lot  

---

## 📞 Troubleshooting

### **Q: Phiếu nhập kho không tạo batch tự động?**
A: ✓ Đó là bình thường. Tạo Lot từ menu Stock → Lot/Serial Numbers

### **Q: Làm sao tạo Lot từ phiếu nhập?**
A: Có 2 cách:
1. Manual: Sau khi confirm phiếu, tạo Lot mới
2. Auto: Thêm button "Create Lot" vào picking (tuỳ chỉnh)

### **Q: Dữ liệu batch cũ sao?**
A: Vẫn trong hệ thống. Nếu muốn dùng, chạy script migration ở trên.

### **Q: Widget batch_selector không hoạt động?**
A: Đổi sang `lot_selector` hoặc `Many2one` selector thông thường.

