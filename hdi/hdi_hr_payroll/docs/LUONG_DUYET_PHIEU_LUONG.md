# 📋 LUỒNG DUYỆT PHIẾU LƯƠNG

## 🔄 Tổng quan luồng

```
DRAFT → VERIFY → DONE → PAID
  ↓       ↓        
CANCEL  CANCEL
```

## 📊 Chi tiết các trạng thái

### 1️⃣ **DRAFT** (Nháp)
- **Mô tả**: Phiếu lương mới tạo, chưa được tính toán hoặc đang chỉnh sửa
- **Quyền hạn**: HR, Kế toán có thể tạo và chỉnh sửa
- **Các nút có thể thực hiện**:
  - ✅ **Tính lương** (`compute_sheet`) - Tính toán các khoản lương
  - ✅ **Gửi duyệt** (`action_payslip_verify`) - Gửi lên cấp trên duyệt
  - ✅ **Hủy** (`action_payslip_cancel`) - Hủy phiếu lương

### 2️⃣ **VERIFY** (Chờ duyệt)
- **Mô tả**: Phiếu lương đã được gửi lên, đang chờ quản lý duyệt
- **Quyền hạn**: Chỉ quản lý mới có thể duyệt hoặc từ chối
- **Các nút có thể thực hiện**:
  - ✅ **Duyệt** (`action_payslip_done`) - Chấp nhận và xác nhận phiếu lương
  - ✅ **Hủy** (`action_payslip_cancel`) - Từ chối phiếu lương

### 3️⃣ **DONE** (Đã duyệt)
- **Mô tả**: Phiếu lương đã được duyệt, sẵn sàng để thanh toán
- **Quyền hạn**: HR, Kế toán có thể đánh dấu đã thanh toán
- **Các nút có thể thực hiện**:
  - ✅ **Đã thanh toán** (`action_payslip_paid`) - Xác nhận đã chuyển tiền

### 4️⃣ **PAID** (Đã thanh toán)
- **Mô tả**: Phiếu lương đã hoàn tất, tiền đã được chuyển cho nhân viên
- **Quyền hạn**: Chỉ đọc, không thể chỉnh sửa
- **Các nút có thể thực hiện**: Không có (trạng thái cuối)

### 5️⃣ **CANCEL** (Đã hủy)
- **Mô tả**: Phiếu lương bị hủy hoặc từ chối
- **Quyền hạn**: Có thể chuyển về Nháp để chỉnh sửa lại
- **Các nút có thể thực hiện**:
  - ✅ **Chuyển về nháp** (`action_payslip_draft`) - Để chỉnh sửa lại

---

## 🎯 Hướng dẫn sử dụng từng bước

### Bước 1: Tạo phiếu lương
1. Vào menu **Payroll → Phiếu lương → Tạo mới**
2. Chọn **Nhân viên**, **Hợp đồng**, **Thời gian**
3. Nhập các khoản bổ sung (nếu có): Thưởng, Phạt, Tạm ứng...
4. Trạng thái: **DRAFT**

### Bước 2: Tính lương
1. Click nút **"Tính lương"**
2. Hệ thống tự động:
   - Lấy ngày công từ chấm công
   - Tính lương cơ bản theo công thực tế
   - Tính phụ cấp, thưởng, phạt
   - Tính bảo hiểm (BHXH, BHYT, BHTN)
   - Tính thuế TNCN
   - Tính thực lĩnh
3. Kiểm tra kết quả trong tab **"Chi tiết lương"**
4. Vẫn ở trạng thái: **DRAFT**

### Bước 3: Gửi duyệt
1. Click nút **"Gửi duyệt"**
2. Phiếu lương chuyển sang: **VERIFY** (Chờ duyệt)
3. Hệ thống kiểm tra:
   - ✅ Có hợp đồng chưa?
   - ✅ Đã tính lương chưa (có chi tiết lương chưa)?
4. Nếu thiếu thông tin → Hiện lỗi
5. Gửi thông báo cho quản lý

### Bước 4: Quản lý duyệt
1. Quản lý vào xem phiếu lương
2. Kiểm tra các khoản tính toán
3. Lựa chọn:
   - Click **"Duyệt"** → Chấp nhận
     - Tự động tạo số phiếu lương (`sequence`)
     - Chuyển sang trạng thái: **DONE**
   - Click **"Hủy"** → Từ chối
     - Chuyển sang trạng thái: **CANCEL**

### Bước 5: Đánh dấu đã thanh toán
1. Sau khi chuyển tiền cho nhân viên
2. Click nút **"Đã thanh toán"**
3. Ghi nhận **Ngày thanh toán**
4. Chuyển sang trạng thái: **PAID** (Hoàn tất)

---

## 🔐 Phân quyền (Security)

### Vai trò: HR User (Nhân viên HR)
- ✅ Tạo phiếu lương
- ✅ Tính lương
- ✅ Gửi duyệt
- ✅ Xem phiếu lương của tất cả nhân viên
- ❌ Không được duyệt

### Vai trò: HR Officer (Quản lý HR)
- ✅ Tất cả quyền của HR User
- ✅ **Duyệt phiếu lương**
- ✅ Hủy phiếu lương
- ✅ Đánh dấu đã thanh toán

### Vai trò: Manager (Quản lý phòng ban)
- ✅ Xem phiếu lương của nhân viên trong phòng ban
- ✅ **Duyệt phiếu lương** của nhân viên dưới quyền
- ❌ Không được sửa đổi

---

## 🛠️ Các hàm xử lý trong code

### File: `models/hr_payslip.py`

```python
def action_payslip_draft(self):
    """Chuyển về nháp"""
    return self.write({'state': 'draft'})

def action_payslip_verify(self):
    """Gửi duyệt"""
    self._validate_payslip()  # Kiểm tra hợp lệ
    return self.write({'state': 'verify'})

def action_payslip_done(self):
    """Duyệt phiếu lương"""
    for payslip in self:
        if not payslip.number:
            # Tạo số phiếu tự động
            payslip.number = self.env['ir.sequence'].next_by_code('hr.payslip') or _('New')
    return self.write({'state': 'done'})

def action_payslip_cancel(self):
    """Hủy phiếu lương"""
    return self.write({'state': 'cancel'})

def action_payslip_paid(self):
    """Đánh dấu đã thanh toán"""
    return self.write({
        'state': 'paid',
        'paid_date': fields.Date.today()
    })

def _validate_payslip(self):
    """Kiểm tra tính hợp lệ trước khi duyệt"""
    for payslip in self:
        if not payslip.contract_id:
            raise ValidationError(_('Vui lòng chọn hợp đồng'))
        if not payslip.line_ids:
            raise ValidationError(_('Phiếu lương chưa có dữ liệu. Vui lòng Tính lương trước.'))
```

---

## ⚠️ Lưu ý quan trọng

### 1. Ràng buộc xóa phiếu lương
```python
def unlink(self):
    """Chỉ xóa được nếu đang ở trạng thái draft hoặc cancel"""
    if any(slip.state not in ['draft', 'cancel'] for slip in self):
        raise UserError(_('Bạn chỉ có thể xóa phiếu lương ở trạng thái Nháp hoặc Đã hủy!'))
    return super(HrPayslip, self).unlink()
```

- ✅ Có thể xóa khi: `DRAFT` hoặc `CANCEL`
- ❌ Không được xóa khi: `VERIFY`, `DONE`, `PAID`

### 2. Ràng buộc duy nhất
```python
_sql_constraints = [
    ('payslip_employee_unique', 'unique(employee_id, date_from, date_to, company_id)',
     'Mỗi nhân viên chỉ có 1 phiếu lương trong 1 kỳ!')
]
```

- Không được tạo 2 phiếu lương cho cùng 1 nhân viên trong cùng kỳ

### 3. Tracking (Theo dõi thay đổi)
- Các trường quan trọng có `tracking=True`:
  - `employee_id` - Nhân viên
  - `state` - Trạng thái
  - `net_wage` - Thực lĩnh

→ Mọi thay đổi đều được ghi log trong chatter

---

## 📱 Thông báo (Activity & Chatter)

### Khi gửi duyệt (VERIFY)
- Tạo activity cho quản lý: "Phiếu lương cần duyệt"
- Gửi email thông báo (nếu được cấu hình)

### Khi duyệt (DONE)
- Đóng activity
- Ghi log: "Phiếu lương đã được duyệt bởi [User]"

### Khi hủy (CANCEL)
- Ghi log: "Phiếu lương đã bị hủy"
- Lý do hủy (nếu có)

---

## 🎨 Hiển thị trên giao diện

### Statusbar
```xml
<field name="state" widget="statusbar" statusbar_visible="draft,verify,done,paid"/>
```

Hiển thị các trạng thái: **Nháp → Chờ duyệt → Đã duyệt → Đã thanh toán**

### Các nút (Buttons)
- Chỉ hiển thị nút phù hợp với từng trạng thái
- Sử dụng `invisible` để ẩn/hiện điều kiện
- Màu nổi bật (`oe_highlight`) cho action chính

---

## 📊 Báo cáo & Thống kê

### Dashboard cần có
1. **Phiếu lương chờ duyệt** (VERIFY)
   - Số lượng
   - Tổng tiền
   - Danh sách chi tiết

2. **Phiếu lương đã duyệt** (DONE)
   - Chưa thanh toán
   - Tổng tiền cần thanh toán

3. **Phiếu lương đã thanh toán** (PAID)
   - Theo tháng
   - Theo nhân viên
   - Theo phòng ban

---

## 🔄 Luồng hoàn chỉnh (Flowchart)

```
┌─────────────┐
│   CREATE    │ Tạo mới phiếu lương
└──────┬──────┘
       │
       ▼
┌─────────────┐
│    DRAFT    │ Nhập thông tin, tính lương
└──────┬──────┘
       │ action_payslip_verify()
       ▼
┌─────────────┐
│   VERIFY    │ Chờ quản lý duyệt
└──────┬──────┘
       │ action_payslip_done()
       ▼
┌─────────────┐
│    DONE     │ Đã duyệt, sẵn sàng thanh toán
└──────┬──────┘
       │ action_payslip_paid()
       ▼
┌─────────────┐
│    PAID     │ ✅ HOÀN TẤT
└─────────────┘

       │ Có thể hủy từ DRAFT hoặc VERIFY
       ▼
┌─────────────┐
│   CANCEL    │ Đã hủy
└──────┬──────┘
       │ action_payslip_draft()
       ▼
     DRAFT (để sửa lại)
```

---

## ✅ Checklist triển khai

- [x] Định nghĩa states trong model
- [x] Tạo các action methods
- [x] Validation trước khi chuyển state
- [x] Cấu hình buttons trong view XML
- [x] Tracking thay đổi
- [x] Ràng buộc xóa
- [x] Ràng buộc duy nhất
- [x] Sequence cho số phiếu
- [x] Ghi nhận ngày thanh toán
- [ ] Cấu hình phân quyền (security)
- [ ] Email templates
- [ ] Activity rules
- [ ] Dashboard widgets

---

**Tác giả**: HDI Development Team  
**Phiên bản**: 1.0  
**Cập nhật**: 23/12/2024
