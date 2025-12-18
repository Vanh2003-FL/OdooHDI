# ⚡ QUICKSTART - HDI PAYROLL

## 🎯 MODULE ĐÃ TẠO XONG - 1 MODULE DUY NHẤT!

```
✅ hdi_payroll/
   ├── 10 models Python (hr_employee, hr_contract, hr_payslip...)
   ├── 15+ salary rules (BASIC, ALW, INSURANCE, TAX, NET...)
   ├── 6 data XML (categories, structures, tax brackets...)
   ├── Wizard tạo batch payslips
   └── Security & access rights
```

---

## 📋 CHECKLIST SỬ DỤNG

### ✅ BƯỚC 1: Cài module
```bash
# Module tại: /workspaces/OdooHDI/hdi/hdi_payroll
# Odoo → Apps → Update Apps List → Search "HDI Payroll" → Install
```

### ✅ BƯỚC 2: Kiểm tra data đã load
- Menu: **Payroll → Cấu hình**
  - ✅ Biểu thuế TNCN: 7 bậc (5% → 35%)
  - ✅ Loại phụ cấp: Ăn, Xe, Phone, Housing...
  - ✅ Quy tắc tính lương: 15+ rules

### ✅ BƯỚC 3: Thiết lập hợp đồng
**Menu:** Employees → Contracts → Create/Edit

```python
# Tab "Salary Information"
Wage: 15,000,000  # Lương cơ bản

# Phụ cấp
Phụ cấp ăn trưa: 730,000
Phụ cấp xăng xe: 1,000,000
Phụ cấp điện thoại: 300,000

# Bảo hiểm (tự động tính)
Mức lương đóng BHXH: 15,730,000  # = wage + meal
BHXH Công ty: 17.5%
BHXH NV: 8%
BHYT Công ty: 3%
BHYT NV: 1.5%
BHTN Công ty: 1%
BHTN NV: 1%
```

### ✅ BƯỚC 4: Thêm người phụ thuộc (nếu có)
**Menu:** Employees → Chọn NV → Người phụ thuộc

```python
Họ tên: Nguyễn Văn A
Quan hệ: Con
Ngày sinh: 01/01/2010
Giảm trừ từ: 01/01/2024
```

### ✅ BƯỚC 5: Tạo phiếu lương
**Menu:** Payroll → Tất cả phiếu lương → Create

```python
Nhân viên: [Chọn]
Từ ngày: 01/12/2024
Đến ngày: 31/12/2024
Công chuẩn: 22.5
```

### ✅ BƯỚC 6: Tính lương
**Trong Payslip → Click nút "Tính lương"**

Hệ thống tự động:
1. Lấy worked days từ `hr.work.entry`
2. Chạy 15+ salary rules
3. Tính: BASIC → ALW → GROSS → INSURANCE → TAX → NET

### ✅ BƯỚC 7: Kiểm tra kết quả
**Tab "Chi tiết lương"**

```
Lương cơ bản         14,666,667
PC ăn trưa              713,778
PC xăng xe            1,000,000
PC điện thoại           300,000
─────────────────────────────
TỔNG THU NHẬP      16,680,445

BHXH (8%)           -1,258,400
BHYT (1.5%)           -235,950
BHTN (1%)             -157,300
─────────────────────────────
BẢO HIỂM           -1,651,650

Thuế TNCN                    0
─────────────────────────────
THỰC LĨNH          15,028,795
```

### ✅ BƯỚC 8: Duyệt & Thanh toán
```
1. Click "Gửi duyệt" (state = verify)
2. Manager click "Duyệt" (state = done)
3. Chuyển tiền
4. Click "Đã thanh toán" (state = paid)
```

---

## 🔥 TÍNH NĂNG ĐẶC BIỆT

### 1️⃣ Tạm ứng tự động trừ lương
```python
Menu: Payroll → Tạm ứng & Vay → Create
Số tiền: 5,000,000
Số kỳ trả: 2
→ Auto trừ 2,500,000/tháng
```

### 2️⃣ Thưởng tự động cộng
```python
Menu: Payroll → Khen thưởng → Create
Số tiền: 3,000,000
Cộng vào lương: Yes
→ Auto add vào GROSS
```

### 3️⃣ Phạt tự động khấu trừ
```python
Menu: Payroll → Kỷ luật → Create
Số tiền phạt: 500,000
Trừ vào lương: Yes
→ Auto deduct
```

### 4️⃣ Batch tạo hàng loạt
```python
Menu: Payroll → Batch tính lương → Create
→ Click "Tạo phiếu lương hàng loạt"
→ Chọn phòng ban
→ Create all payslips cùng lúc
```

---

## 📊 CÔNG THỨC CỐT LÕI

Tất cả trong file: `data/hr_salary_rule_data.xml`

### Rule 1: BASIC (Lương cơ bản)
```python
result = (contract.wage / payslip.standard_days) * worked_days.WORK100.number_of_days
```

### Rule 2: ALW_MEAL (PC ăn)
```python
result = (contract.meal_allowance / payslip.standard_days) * worked_days.WORK100.number_of_days
```

### Rule 3: GROSS (Tổng thu nhập)
```python
result = categories.BASIC + categories.ALW + categories.BONUS
```

### Rule 4: SI_EMP (BHXH nhân viên)
```python
result = -(contract.insurance_salary * contract.si_employee_rate / 100)
```

### Rule 5: PIT (Thuế TNCN)
```python
taxable_income = categories.GROSS - abs(categories.INSURANCE) - employee.total_deduction
result = -TaxBracket.calculate_tax(taxable_income)
```

### Rule 6: NET (Thực lĩnh)
```python
result = categories.GROSS + categories.INSURANCE + categories.DED + categories.TAX
```

---

## ⚙️ TÙY CHỈNH

### Thay đổi tỷ lệ BH:
**File:** `models/hr_contract.py`
```python
si_company_rate = fields.Float(default=17.5)  # Sửa thành 20
si_employee_rate = fields.Float(default=8.0)  # Sửa thành 10
```

### Thay đổi giảm trừ thuế:
**File:** `models/hr_employee.py`
```python
personal_deduction = fields.Monetary(default=11000000)  # Sửa thành 13tr
dependent_deduction = fields.Monetary(default=4400000)  # Sửa thành 5tr
```

### Thêm rule mới:
**File:** `data/hr_salary_rule_data.xml`
```xml
<record id="rule_my_custom" model="hr.salary.rule">
    <field name="name">Phụ cấp mới</field>
    <field name="code">MY_CUSTOM</field>
    <field name="amount_python_compute">
result = 1000000  # Logic tùy chỉnh
    </field>
</record>
```

---

## 🐛 TROUBLESHOOTING

### ❌ Lỗi: Module not found
**Fix:** Restart Odoo server
```bash
sudo systemctl restart odoo
```

### ❌ Lỗi: Không có worked days
**Fix:** Tạo `hr.work.entry` với state='validated'
Hoặc nhập thủ công trong tab "Ngày công"

### ❌ Lỗi: Thuế tính sai
**Fix:** Kiểm tra `hr.tax.bracket` đã có 7 bậc chưa
Menu: Payroll → Cấu hình → Biểu thuế TNCN

### ❌ Lỗi: Rule không chạy
**Fix:** Kiểm tra điều kiện `condition_python`
Hoặc check rule đã gán vào structure chưa

---

## 📚 TÀI LIỆU

- **README.md** - Giới thiệu module
- **SUMMARY.md** - Tóm tắt chi tiết
- **USAGE.md** - Hướng dẫn sử dụng đầy đủ
- **QUICKSTART.md** - File này

---

## 🎉 KẾT LUẬN

**Module hdi_payroll đã SẴN SÀNG!**

✅ **10 models** hoàn chỉnh
✅ **15+ salary rules** tự động
✅ **Biểu thuế VN 2024**
✅ **Tính BH chuẩn**
✅ **Vay, thưởng, phạt**

**CHỈ CẦN**: Cài → Setup → Tính!

**KHÔNG CẦN** module nào khác!

---

**🚀 BẮT ĐẦU NGAY:**
1. Install module
2. Tạo contract (wage + allowances)
3. Create payslip
4. Click "Tính lương"
5. DONE! ✨
