# Hướng dẫn sử dụng: Gán vị trí sản phẩm từ Sơ đồ kho

## Giới thiệu
Tính năng này cho phép bạn gán vị trí lưu trữ cho sản phẩm/lot trực tiếp từ màn hình nhập kho (stock picking), thay vì gán tự động khi xác nhận hoàn tất phiếu nhập kho.

## Cách sử dụng

### 1. Mở phiếu nhập kho
- Truy cập: **Inventory > Receipts** (Phiếu nhập kho)
- Chọn hoặc tạo một phiếu nhập kho có trạng thái **Draft** hoặc **Confirmed**
- Nhập các dòng sản phẩm cần nhập kho

### 2. Gán vị trí cho sản phẩm/lot
Có 2 cách để gán vị trí:

#### Cách 1: Nhập tọa độ trực tiếp
1. Ở bảng **Operations**, chọn sản phẩm/lot cần gán vị trí
2. Nhấp nút **"📍 Gán vị trí"** ở cửa sổ hàng
3. Cửa sổ wizard sẽ mở:
   - **Sơ đồ kho**: Chọn sơ đồ kho để gán vị trí
   - **Vị trí X (Cột)**: Nhập số cột
   - **Vị trí Y (Hàng)**: Nhập số hàng
   - **Vị trí Z (Tầng)**: Nhập tầng/kệ (mặc định = 0)
4. Nhấp **"Xác nhận"** để lưu vị trí

#### Cách 2: Chọn từ sơ đồ kho (Visual)
1. Ở bảng **Operations**, chọn sản phẩm/lot cần gán vị trí
2. Nhấp nút **"📍 Gán vị trí"** ở cửa sổ hàng
3. Ở cửa sổ wizard:
   - Chọn **"Chọn từ sơ đồ kho"** (Cách chọn vị trí)
   - Chọn **Sơ đồ kho**
   - Nhấp **"Mở sơ đồ kho"**
4. Ở màn hình sơ đồ kho:
   - Nhấp vào ô (cell) cần gán vị trí
   - Vị trí sẽ được tự động cập nhật vào form wizard
5. Nhấp **"Xác nhận"** để lưu vị trí

### 3. Xác nhận phiếu nhập kho
Sau khi gán vị trí cho tất cả sản phẩm/lot cần thiết:
1. Nhấp **"Validate"** hoặc **"Mark as Todo"** để xác nhận phiếu
2. Hệ thống sẽ tự động:
   - Tạo các quant (lot) với vị trí đã gán
   - Hiển thị sản phẩm trên sơ đồ kho theo vị trí đã chọn

## Lưu ý quan trọng

1. **Chỉ áp dụng cho phiếu nhập kho (Incoming)**: Nút gán vị trí chỉ hiển thị cho phiếu loại **Incoming** (Nhập kho)
2. **Chỉ cho sản phẩm có tracking**: Chỉ có thể gán vị trí cho sản phẩm có **Tracking** (Lô/Serial), sản phẩm không tracking sẽ bỏ qua
3. **Tránh vị trí trùng lặp**: Hệ thống sẽ kiểm tra và cảnh báo nếu bạn cố gán sản phẩm/lot vào vị trí đã có sản phẩm khác
4. **Vị trí trong giới hạn**: Vị trí X, Y phải nằm trong giới hạn của sơ đồ kho đã chọn

## Cấu hình sơ đồ kho

Trước khi sử dụng chức năng này, đảm bảo đã cấu hình sơ đồ kho:

1. Truy cập: **Inventory > Sơ đồ kho > Sơ đồ kho**
2. Tạo sơ đồ mới:
   - **Tên sơ đồ**: Tên mô tả (VD: "Sơ đồ kho WH/Stock")
   - **Kho**: Chọn kho sử dụng
   - **Vị trí kho chính**: Chọn vị trí cha (parent location)
   - **Số hàng / Số cột**: Định nghĩa kích thước lưới
3. Nhấp **"Xem sơ đồ"** để kiểm tra

## FAQ

**Q: Làm sao để xem sản phẩm đã gán vị trí trên sơ đồ kho?**
A: Vào **Inventory > Sơ đồ kho > Sơ đồ kho**, chọn sơ đồ và nhấp **"Xem sơ đồ"**. Sản phẩm với vị trí sẽ hiển thị trên sơ đồ.

**Q: Có thể thay đổi vị trí sau khi xác nhận phiếu nhập kho không?**
A: Có. Vào **Inventory > Reporting > Inventory**, chọn quant (lot) và cập nhật trực tiếp các trường **Vị trí X/Y/Z**.

**Q: Sản phẩm của tôi không có lô/serial, có thể gán vị trí không?**
A: Không. Chức năng này chỉ áp dụng cho sản phẩm có tracking (lô/serial). Sản phẩm không tracking sẽ bỏ qua vị trí được gán.
