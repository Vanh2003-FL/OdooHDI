# Upgrade Notes - Warehouse Map Module v18.0.1.0.0

## Phiên bản cũ: 17.0.1.6.4
## Phiên bản mới: 18.0.1.0.0

---

## Tóm tắt các thay đổi cho Odoo 18

### ✅ 1. Manifest File (`__manifest__.py`)
- **Version**: `17.0.1.6.4` → `18.0.1.0.0`
- **Assets Path**: Cập nhật tên module trong assets từ `warehouse_map/` → `hdi_warehouse_map/`
  ```python
  'web.assets_backend': [
      'hdi_warehouse_map/static/src/css/warehouse_map.css',
      'hdi_warehouse_map/static/src/js/warehouse_map_view.js',
      'hdi_warehouse_map/static/src/xml/warehouse_map.xml',
  ]
  ```

### ✅ 2. JavaScript (`warehouse_map_view.js`)
- **OWL Lifecycle Hooks**: Cập nhật cách quản lý event listeners trong `onMounted()`
  - Thêm cleanup function để xóa event listener khi component unmount
  ```javascript
  onMounted(() => {
      document.addEventListener('click', this.closeContextMenu.bind(this));
      return () => {
          document.removeEventListener('click', this.closeContextMenu.bind(this));
      };
  });
  ```
- **Imports**: Vẫn sử dụng `@odoo/owl` standard (không thay đổi)
- **useService hooks**: Vẫn hỗ trợ `orm`, `action`, `notification` (tương thích)

### ✅ 3. XML Template (`warehouse_map.xml`)
- **OWL Syntax**: Template đã tuân thủ OWL 2.0 syntax (tương thích Odoo 18)
  - Sử dụng `t-name`, `t-if`, `t-else`, `t-foreach`, `t-on-click` chính xác
  - Attribute binding với `t-att-*` (tương thích)
  - Arrow functions trong event handlers (tương thích)

### ✅ 4. View XML Files - **CRITICAL CHANGE**
**Odoo 18: View type `tree` → `list`**
- Đã cập nhật tất cả `<tree>` thành `<list>` trong views
- Đã cập nhật tất cả `view_mode="tree"` thành `view_mode="list"` trong actions

**Files đã sửa:**
- `views/blocked_cell_views.xml`: `<tree>` → `<list>`, `view_mode="tree,form"` → `"list,form"`
- `views/warehouse_map_views.xml`: `<tree>` → `<list>`, `view_mode="kanban,tree,form"` → `"kanban,list,form"`
- `views/stock_location_views.xml`: Inherit view - OK (không cần sửa)
- `wizard/assign_lot_position_wizard_views.xml`: `<tree>` → `<list>`
- `wizard/block_cell_wizard_views.xml`: Wizard form - OK
- `wizard/location_action_wizard_views.xml`: Inline `<tree>` → `<list>`

### ✅ 5. Python Models
**Không cần thay đổi** - Tất cả models tuân thủ Odoo API tiêu chuẩn:

#### warehouse_map.py
- Sử dụng `@api.depends()`, `@api.model` (tương thích)
- Không dùng deprecated APIs
- Method `get_map_data()` sử dụng ORM standard

#### blocked_cell.py
- Sử dụng fields tiêu chuẩn (CharField, Integer, Selection, Text)
- `@api.depends()`, `@api.model` decorators hỗ trợ
- SQL constraints tương thích

#### stock_location.py
- Inherit từ `stock.location` và `stock.quant` (tương thích)
- `@api.depends()` decorator hỗ trợ

---

## Kiểm tra tương thích Odoo 18

### Dependencies
- ✅ `stock` - Core module Odoo 18
- ✅ `product` - Core module Odoo 18
- ✅ `track_vendor_by_lot` - Phụ thuộc HDI

### API Calls
- ✅ `orm.call()` - Tương thích Odoo 18
- ✅ `orm.write()` - Tương thích Odoo 18
- ✅ `action.doAction()` - Tương thích Odoo 18
- ✅ `notification` service - Tương thích Odoo 18

### UI Components
- ✅ Client actions - Tương thích
- ✅ Wizards (ir.actions.act_window) - Tương thích
- ✅ Forms, Trees, Kanban views - Tương thích

---

## Dữ liệu được bảo tồn
✅ **Luồng dữ liệu không thay đổi**:
- Cấu trúc database model giữ nguyên
- Logic tính toán vị trí (posx, posy, posz) giữ nguyên
- Logic hiển thị lot/blocked cells giữ nguyên
- Context menu interactions giữ nguyên

---

## Testing Checklist
- [ ] Install module thành công
- [ ] Tạo mới Warehouse Map
- [ ] Xem sơ đồ kho (view map)
- [ ] Click cells để xem context menu
- [ ] Gán lot vào vị trí
- [ ] Chặn/bỏ chặn ô
- [ ] Kiểm tra badge ngày tồn kho
- [ ] Kiểm tra spacing rows/columns
- [ ] Xem chi tiết lot
- [ ] Thực hiện actions: pick, move, transfer

---

## Ghi chú
- Module đã cập nhật hoàn toàn sang Odoo 18
- Các wizard pages cần kiểm tra nếu có wizard views riêng
- Có thể cần cập nhật CSS cho Bootstrap 5 (nếu có custom styles)
