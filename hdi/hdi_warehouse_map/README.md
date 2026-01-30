# HDI Warehouse Map & Bin Management

Mô-đun quản lý sơ đồ kho với visualization 2D/3D cho Odoo 18.

## Tính năng chính

### 1. Quản lý cấu trúc vị trí kho (FR-1, FR-2, FR-3)
- Cấu trúc phân cấp: **Zone → Aisle → Rack → Level → Bin**
- Mỗi Bin tương ứng duy nhất với một `stock.location`
- Mỗi Bin có mã định danh và tọa độ không gian (X, Y, Z)

### 2. Ràng buộc SKU và Lot/Sê-ri (FR-4, FR-5, FR-6)
- **FR-4**: Một Bin chỉ được chứa một SKU tại một thời điểm
- **FR-5**: Cấu hình tùy chọn: một Bin chỉ chứa một Lot (enforce_single_lot)
- **FR-6**: Validation để không cho phép phát sinh stock move vi phạm ràng buộc Bin

### 3. Đề xuất vị trí Putaway (FR-7, FR-8)
- Hệ thống đề xuất Bin dựa trên SKU, Category và Zone
- Bin được đề xuất được highlight trên sơ đồ 2D khi nhập kho
- Wizard hỗ trợ chọn bin tự động

### 4. Picking và chiến lược xuất kho (FR-9, FR-10)
- Tuân thủ removal strategy của Odoo (FIFO, FEFO)
- Highlight Bin được chọn khi picking trên warehouse map

### 5. Hiển thị sơ đồ kho 2D / 3D (FR-11, FR-12, FR-13, FR-14)
- **FR-11**: Hiển thị kho dạng lưới 2D với các zones, aisles, racks, levels
- **FR-12**: Khung sườn sẵn sàng cho hiển thị 3D (cần tích hợp Three.js)
- **FR-13**: Mỗi Bin có màu sắc thể hiện trạng thái (Empty, Available, Full, Blocked)
- **FR-14**: Click / hover Bin để xem SKU, Lot, số lượng chi tiết

### 6. Block Bin / Block Lot (FR-15, FR-16, FR-17)
- **FR-15, FR-16**: Quản lý có thể block/unblock Bin, Bin bị block không cho phép nhập/xuất
- **FR-17**: Lot bị block không được picking
- Wizard hỗ trợ block/unblock với lý do

### 7. Truy xuất và lịch sử di chuyển (FR-18, FR-19)
- **FR-18**: Xem lịch sử di chuyển theo Bin
- **FR-19**: Xem lịch sử di chuyển theo Lot/Sê-ri
- Tự động ghi log mọi stock move vào/ra bins

## Cài đặt

1. Copy module vào thư mục addons của Odoo
2. Update Apps List
3. Tìm và cài đặt "HDI Warehouse Map & Bin Management"

## Cấu hình ban đầu

1. Vào **Warehouse Map → Configuration → Zones** để tạo zones
2. Tạo Aisles trong mỗi zone
3. Tạo Racks trong mỗi aisle
4. Tạo Levels cho mỗi rack
5. Tạo Bins cho mỗi level
6. Link mỗi Bin với một Stock Location

## Sử dụng

### Xem sơ đồ kho
- Menu: **Warehouse Map → Warehouse Map**
- Chuyển đổi giữa 2D và 3D view
- Zoom in/out để xem chi tiết
- Click vào bin để xem thông tin

### Putaway Suggestion
- Khi tạo Receipt (Nhập kho), click **Suggest Bins**
- Hệ thống sẽ tự động đề xuất bins phù hợp
- Bins được highlight trên warehouse map

### Picking với Map
- Mở Delivery Order / Internal Transfer
- Click **Warehouse Map** để xem vị trí cần lấy hàng
- Bins nguồn được highlight màu vàng

### Block Bin/Lot
- Vào bin cần block
- Click **Block Bin** và nhập lý do
- Bin bị block sẽ không thể sử dụng cho đến khi unblock

### Xem lịch sử
- **Warehouse Map → Bin History**: Lịch sử theo bin
- **Warehouse Map → Lot History**: Lịch sử theo lot
- Trên form Bin: click **History** button

## Mở rộng

### Tích hợp Three.js cho 3D
Để kích hoạt view 3D đầy đủ:
```bash
npm install three
```
Sau đó customize file `warehouse_map_3d.js` để render 3D warehouse.

### Custom Putaway Strategy
Override method `_get_suggested_putaway_bin()` trong `stock.move` model.

## Technical Details

- **Models**: warehouse.zone, warehouse.aisle, warehouse.rack, warehouse.level, warehouse.bin
- **History**: bin.history, lot.history
- **Extends**: stock.location, stock.quant, stock.move, stock.picking, stock.lot
- **Controllers**: /warehouse_map/get_data, /warehouse_map/get_bin_details
- **Assets**: JavaScript (OWL components), CSS

## License
LGPL-3

## Author
HDI Team

## Version
18.0.1.0.0
