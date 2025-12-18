# 🚀 HƯỚNG DẪN SỬ DỤNG HDI_PAYROLL

## ✅ ĐÃ HOÀN THÀNH

Module **hdi_payroll** đã được tạo RÚT GỌN vào **1 module duy nhất** với:

### 📊 THỐNG KÊ
- ✅ **15 file Python** (10 models + 2 wizard + 3 init)
- ✅ **37 files tổng cộng**
- ✅ **6 file Data XML** (categories, structure, rules, tax, allowance)
- ✅ **1 file Salary Rules** quan trọng nhất

### 🎯 CÁC MODELS CHÍNH

| Model | Mô tả | File |
|-------|-------|------|
| `hr.employee` | Mở rộng: thuế, người phụ thuộc, vay | `hr_employee.py` |
| `hr.contract` | Mở rộng: phụ cấp, bảo hiểm | `hr_contract.py` |
| `hr.payroll.structure` | Cấu trúc lương | `hr_payroll_structure.py` |
| `hr.salary.rule` | Quy tắc tính lương | `hr_salary_rule.py` |
| `hr.payslip` | **PHIẾU LƯƠNG (CORE)** | `hr_payslip.py` |
| `hr.payslip.run` | Batch tính lương | `hr_payslip_run.py` |
| `hr.allowance.type` | Loại phụ cấp | `hr_allowance.py` |
| `hr.loan` | Vay/tạm ứng | `hr_loan.py` |
| `hr.discipline` | Kỷ luật | `hr_discipline.py` |
| `hr.reward` | Khen thưởng | `hr_discipline.py` |
| `hr.tax.bracket` | Biểu thuế lũy tiến | `hr_tax.py` |
| `hr.employee.dependent` | Người phụ thuộc | `hr_tax.py` |

---

## 🔧 CÀI ĐẶT

### Bước 1: Cập nhật module list
```bash
cd /workspaces/OdooHDI
# Module đã có tại: hdi/hdi_payroll
```

### Bước 2: Cài đặt trong Odoo
1. Vào **Apps** → **Update Apps List**
2. Tìm: **"HDI Payroll Management"**
3. Click **Install**

### Bước 3: Kiểm tra
- Menu **Payroll** xuất hiện trên top bar
- Có sub-menu: Phiếu lương, Batch, Cấu hình...

---

## 📝 LUỒNG SỬ DỤNG CƠ BẢN

### 1️⃣ CẤU HÌNH BAN ĐẦU

#### A. Thiết lập Biểu thuế (tự động load)
- **Menu:** Payroll → Cấu hình → Biểu thuế TNCN
- ✅ Đã có sẵn 7 bậc thuế 2024

#### B. Thiết lập Loại phụ cấp (tự động load)
- **Menu:** Payroll → Cấu hình → Loại phụ cấp
- ✅ Đã có: Ăn trưa, Xăng xe, Điện thoại, Nhà ở, Chức vụ...

#### C. Kiểm tra Salary Rules
- **Menu:** Payroll → Cấu hình → Quy tắc tính lương
- ✅ Đã có sẵn các rules:
  - `BASIC` - Lương cơ bản
  - `ALW_MEAL` - PC ăn trưa
  - `SI_EMP` - BHXH nhân viên
  - `PIT` - Thuế TNCN
  - `NET` - Thực lĩnh

---

### 2️⃣ THIẾT LẬP NHÂN VIÊN

#### A. Thông tin thuế
**Menu:** Employees → Chọn nhân viên → Tab "Thuế"

```python
Mã số thuế: 0123456789
Giảm trừ bản thân: 11,000,000  # Tự động
Giảm trừ người PT: 4,400,000   # Tự động
```

#### B. Thêm người phụ thuộc
**Menu:** Employees → Chọn NV → Người phụ thuộc → Create

```python
Họ tên: Nguyễn Văn A
Quan hệ: Con
Ngày sinh: 01/01/2010
Giảm trừ từ ngày: 01/01/2024
```

---

### 3️⃣ THIẾT LẬP HỢP ĐỒNG

**Menu:** Employees → Chọn NV → Contracts → Create

```python
# LƯƠNG CƠ BẢN
Wage: 15,000,000

# PHỤ CẤP
Phụ cấp ăn trưa: 730,000
Phụ cấp xăng xe: 1,000,000
Phụ cấp điện thoại: 300,000

# BẢO HIỂM
Mức lương đóng BHXH: 15,730,000  # Tự động = wage + meal
BHXH - Công ty: 17.5%
BHXH - NV: 8%
BHYT - Công ty: 3%
BHYT - NV: 1.5%
BHTN - Công ty: 1%
BHTN - NV: 1%
```

---

### 4️⃣ CHẤM CÔNG (Tùy chọn)

**Nếu có module hr_attendance:**
- Dữ liệu chấm công → `hr.work.entry` (validated)
- Payslip sẽ tự lấy số ngày công

**Nếu chưa có:**
- Payslip dùng công chuẩn = 22.5 ngày
- Hoặc nhập thủ công trong Payslip

---

### 5️⃣ TÍNH LƯƠNG HÀNG LOẠT

#### Cách 1: Tạo Batch
**Menu:** Payroll → Batch tính lương → Create

```python
Tên: Lương tháng 12/2024
Từ ngày: 01/12/2024
Đến ngày: 31/12/2024
```

**→ Click "Tạo phiếu lương hàng loạt"**
- Chọn phòng ban hoặc nhân viên
- → Create

#### Cách 2: Tạo từng phiếu lương
**Menu:** Payroll → Tất cả phiếu lương → Create

```python
Nhân viên: [Chọn]
Từ ngày: 01/12/2024
Đến ngày: 31/12/2024
Công chuẩn: 22.5
```

---

### 6️⃣ TÍNH TOÁN & DUYỆT LƯƠNG

**Trong Payslip:**
1. Click **"Tính lương"** → Hệ thống tự động:
   - Lấy worked days
   - Chạy tất cả salary rules
   - Tính BASIC, ALW, GROSS, INSURANCE, TAX, NET

2. Kiểm tra kết quả trong tab **"Chi tiết lương"**

3. Click **"Gửi duyệt"** → Chờ manager approve

4. Manager click **"Duyệt"** → Phiếu lương confirmed

5. Click **"Đã thanh toán"** khi chuyển tiền xong

---

## 🧮 CÔNG THỨC TÍNH LƯƠNG MẪU

### File quan trọng nhất:
📁 `data/hr_salary_rule_data.xml`

### Ví dụ tính lương thực tế:

```python
# NHÂN VIÊN: Nguyễn Văn A
# HỢP ĐỒNG:
wage = 15,000,000  # Lương CB
meal_allowance = 730,000
transport_allowance = 1,000,000
phone_allowance = 300,000

# CHẤM CÔNG:
worked_days = 22  # Ngày công thực tế
standard_days = 22.5  # Công chuẩn

# BH:
insurance_salary = 15,730,000  # wage + meal

# THUẾ:
dependent_count = 2  # 2 người phụ thuộc

# ---------------- TÍNH TOÁN ----------------

# 1. LƯƠNG CƠ BẢN
BASIC = (15,000,000 / 22.5) * 22 = 14,666,667

# 2. PHỤ CẤP
ALW_MEAL = (730,000 / 22.5) * 22 = 713,778
ALW_TRANSPORT = 1,000,000
ALW_PHONE = 300,000

# 3. TỔNG THU NHẬP
GROSS = 14,666,667 + 713,778 + 1,000,000 + 300,000
      = 16,680,445

# 4. BẢO HIỂM NV ĐÓNG
SI_EMP = 15,730,000 * 8% = -1,258,400
HI_EMP = 15,730,000 * 1.5% = -235,950
UI_EMP = 15,730,000 * 1% = -157,300
INSURANCE = -1,651,650

# 5. THU NHẬP TÍNH THUẾ
Taxable = 16,680,445 - 1,651,650 - 11,000,000 - (2 * 4,400,000)
        = 16,680,445 - 1,651,650 - 19,800,000
        = -4,771,205  # < 0 → Không đóng thuế

PIT = 0

# 6. THỰC LĨNH
NET = 16,680,445 + (-1,651,650) + 0
    = 15,028,795 VNĐ
```

---

## 🎯 CÁC TÍNH NĂNG NÂNG CAO

### 1. Tạm ứng lương
**Menu:** Payroll → Tạm ứng & Vay → Create

```python
Loại: Tạm ứng lương
Số tiền: 5,000,000
Số kỳ trả: 2
Phương thức: Tự động từ lương
```
→ Sẽ tự động trừ 2,500,000/tháng vào payslip

### 2. Khen thưởng
**Menu:** Payroll → Khen thưởng → Create

```python
Loại: Thành tích
Số tiền: 3,000,000
Cộng vào lương: Yes
Chịu thuế: Yes
```
→ Cộng vào GROSS, tính thuế

### 3. Kỷ luật - Phạt
**Menu:** Payroll → Kỷ luật → Create

```python
Loại: Phạt tiền
Số tiền phạt: 500,000
Trừ vào lương: Yes
```
→ Khấu trừ trong payslip

---

## ⚙️ TÙY CHỈNH SALARY RULES

### Sửa rule có sẵn:
**Menu:** Payroll → Cấu hình → Quy tắc tính lương → Chọn rule

**Ví dụ: Thay đổi tỷ lệ BHXH**
```python
# File: data/hr_salary_rule_data.xml
# Rule: SI_EMP

amount_python_compute:
result = -(contract.insurance_salary * 10.5 / 100.0)  # Thay 8% → 10.5%
```

### Thêm rule mới:
```xml
<record id="rule_overtime" model="hr.salary.rule">
    <field name="name">Làm thêm giờ</field>
    <field name="code">OVERTIME</field>
    <field name="sequence">16</field>
    <field name="category_id" ref="category_allowance"/>
    <field name="amount_python_compute">
# Lương giờ = Lương CB / 208 giờ
hourly_wage = contract.wage / 208.0

# Lấy số giờ OT từ work entry
ot_hours = 0
if hasattr(worked_days, 'OVERTIME'):
    ot_hours = worked_days.OVERTIME.number_of_hours

# OT 150%
result = hourly_wage * ot_hours * 1.5
    </field>
</record>
```

---

## 📊 BÁO CÁO

### In phiếu lương cá nhân:
**Payslip → Print → Payslip**

### Xuất Excel tổng hợp:
*Sẽ implement sau trong views/reports*

---

## ❓ TROUBLESHOOTING

### Lỗi: "Không có dữ liệu Worked Days"
→ Cần tạo `hr.work.entry` với state='validated'
→ Hoặc nhập thủ công trong tab "Ngày công"

### Lỗi: "Module hdi_payroll not found"
→ Kiểm tra: `hdi/hdi_payroll/__manifest__.py` tồn tại
→ Restart Odoo server

### Lỗi khi tính thuế:
→ Kiểm tra `hr.tax.bracket` đã load chưa
→ Kiểm tra năm trong biểu thuế

---

## 🎓 KẾT LUẬN

Module **hdi_payroll** đã tích hợp SẴN:

✅ **10 models** xử lý đầy đủ nghiệp vụ
✅ **15+ salary rules** tính tự động
✅ **Biểu thuế VN 2024** (7 bậc)
✅ **Tính BH theo quy định**
✅ **Quản lý vay, thưởng, phạt**

**KHÔNG CẦN** cài thêm module nào khác!

**CHỈ CẦN**: Cài module → Thiết lập hợp đồng → Tính lương!

---

📧 **Support:** Liên hệ HDI Development Team
