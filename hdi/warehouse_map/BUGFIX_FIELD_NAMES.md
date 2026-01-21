# 🔧 Bug Fixes - Field Name Corrections

## ❌ Lỗi đã sửa

### 1. Field name mismatch in hdi.putaway.suggestion

**Lỗi:**
```python
KeyError: 'Field suggested_location_id referenced in related field definition hdi.putaway.suggestion.map_posx does not exist.'
```

**Nguyên nhân:**
- Model `hdi.putaway.suggestion` sử dụng field name: `location_id`
- Code tích hợp đang dùng: `suggested_location_id` (SAI)

**Đã sửa trong:**
- ✅ `models/putaway_map_bridge.py`
- ✅ `models/stock_picking_integration.py`
- ✅ `wizard/picking_map_assignment_wizard.py`
- ✅ `wizard/receipt_putaway_wizard.py`

**Thay đổi:**
```python
# TRƯỚC (SAI):
putaway.suggested_location_id

# SAU (ĐÚNG):
putaway.location_id
```

---

### 2. State value mismatch

**Lỗi:**
- Code search với: `state='pending'`
- Model chỉ có: `state='suggested'`

**Selection values trong hdi.putaway.suggestion:**
```python
state = fields.Selection([
    ('suggested', 'Được đề xuất'),
    ('selected', 'Đã chọn'),
    ('rejected', 'Bị loại'),
])
```

**Đã sửa:**
```python
# TRƯỚC (SAI):
('state', '=', 'pending')

# SAU (ĐÚNG):
('state', '=', 'suggested')
```

---

### 3. Order field mismatch

**Lỗi:**
- Code order với: `suggested_location_priority`
- Field không tồn tại

**Order đúng:**
```python
# TRƯỚC (SAI):
order='priority desc, suggested_location_priority asc'

# SAU (ĐÚNG):
order='priority desc, score desc'
```

---

## 📋 Tóm tắt field names của hdi.putaway.suggestion

### ✅ Fields chính:
```python
batch_id           # Many2one to hdi.batch
product_id         # Many2one to product.product
quantity           # Float
location_id        # Many2one to stock.location (VỊ TRÍ ĐỀ XUẤT)
score              # Float (điểm đề xuất)
priority           # Integer (related từ location_id.location_priority)
state              # Selection: 'suggested', 'selected', 'rejected'
```

### ✅ Related fields:
```python
location_display   # related='location_id.complete_name'
coordinates        # related='location_id.coordinate_display'
```

---

## 🎯 Checklist khi tích hợp với hdi_wms

Trước khi code tích hợp, luôn kiểm tra:

1. ✅ **Field names chính xác**
   ```bash
   # Read model definition first
   grep -n "fields\." hdi_wms/models/hdi_putaway_suggestion.py
   ```

2. ✅ **Selection values**
   ```python
   # Check state values
   state = fields.Selection([...])
   ```

3. ✅ **Related fields**
   ```python
   # Ensure related field path exists
   priority = fields.Integer(related='location_id.location_priority')
   ```

4. ✅ **Order fields**
   ```python
   # Use actual field names in order
   _order = 'priority, score desc'
   ```

---

## ✨ Kết quả sau khi sửa

Module warehouse_map giờ tích hợp đúng với hdi_wms:

✅ Putaway suggestions hoạt động  
✅ Related fields sync đúng coordinates  
✅ Order/filter theo priority và score  
✅ State management đúng  
✅ Map integration hoạt động hoàn hảo  

**Có thể install module mà không lỗi!** 🎉
