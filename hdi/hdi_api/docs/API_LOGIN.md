# API Đăng Nhập

## 1. Mô Tả Thông Tin API

### Endpoint
- **URL**: `/api/v1/auth/login`
- **Method**: `POST`

### Header Request
```json
{
  "Content-Type": "application/json"
}
```

### Body Request
```json
{
  "login": "admin",
  "password": "tudfaj-zihda6-Medsir"
}
```

---

## 2. Mô Tả Tham Số

| Tham Số | Kiểu Dữ Liệu | Bắt Buộc | Mô Tả |
|---------|--------------|---------|-------|
| login | String | ✓ | Tên đăng nhập của người dùng |
| password | String | ✓ | Mật khẩu của người dùng |

---

## 3. Mô Tả Kết Quả Trả Về

| Tham Số | Kiểu Dữ Liệu | Mô Tả |
|---------|--------------|-------|
| code | Integer | Mã HTTP status |
| status | String | Trạng thái phản hồi (Success/Error) |
| message | String | Thông báo kết quả |
| data | Object | Dữ liệu người dùng sau khi đăng nhập thành công |
| data.access_token | String | Chuỗi token xác thực JWT |
| data.user_id | Object | Thông tin người dùng |
| data.user_id.id | Integer | ID người dùng |
| data.user_id.name | String | Tên người dùng |
| data.user_id.email | String | Email người dùng |
| data.partner_id | Object | Thông tin đối tác liên kết |
| data.partner_id.id | Integer | ID đối tác |
| data.partner_id.name | String | Tên đối tác |
| data.company_id | Object | Thông tin công ty |
| data.company_id.id | Integer | ID công ty |
| data.company_id.name | String | Tên công ty |
| data.department_id | Object | Thông tin phòng ban |
| data.department_id.id | Integer hoặc Boolean | ID phòng ban (false nếu không có) |
| data.department_id.name | String | Tên phòng ban |
| data.employee_id | Object | Thông tin nhân viên |
| data.employee_id.id | Integer hoặc Boolean | ID nhân viên (false nếu không có) |
| data.employee_id.name | String | Tên nhân viên |

---

## 4. Ví Dụ Kết Quả Trả Về

### Thành Công (200)

```json
{
  "code": 200,
  "status": "Success",
  "message": "Đăng nhập thành công",
  "data": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJsb2dpbiI6ImFkbWluIiwiZGV2aWNlX2lkIjoiUG9zdG1hbiIsInRzIjoxNzU2MTkzOTIxLjUwMzk1NH0.lujth98bSNbwIDVDlXWx4PqV6X2U849nHhIJgqTWb5E",
    "user_id": {
      "id": 2,
      "name": "Administrator",
      "email": "admin"
    },
    "partner_id": {
      "id": 3,
      "name": "Administrator"
    },
    "company_id": {
      "id": 1,
      "name": "CÔNG TY CỔ PHẦN ĐẦU TƯ VÀ DU LỊCH VẠN HƯƠNG"
    },
    "department_id": {
      "id": false,
      "name": ""
    },
    "employee_id": {
      "id": false,
      "name": ""
    }
  }
}
```

### Lỗi - Tên đăng nhập hoặc mật khẩu không hợp lệ (400)

```json
{
  "code": 400,
  "status": "Error",
  "message": "Tên đăng nhập và mật khẩu là bắt buộc"
}
```

### Lỗi - Máy chủ (500)

```json
{
  "code": 500,
  "status": "Error",
  "message": "Lỗi: [Chi tiết lỗi]"
}
```

---

## 5. Cách Sử Dụng

### Ví Dụ với cURL

```bash
curl -X POST http://localhost:8069/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "login": "admin",
    "password": "tudfaj-zihda6-Medsir"
  }'
```

### Ví Dụ với Python

```python
import requests
import json

url = "http://localhost:8069/api/v1/auth/login"
headers = {
  "Content-Type": "application/json"
}
data = {
  "login": "admin",
  "password": "tudfaj-zihda6-Medsir"
}

response = requests.post(url, headers=headers, json=data)
result = response.json()
print(json.dumps(result, indent=2))
```

### Ví Dụ với JavaScript

```javascript
const loginData = {
  login: "admin",
  password: "tudfaj-zihda6-Medsir"
};

fetch('http://localhost:8069/api/v1/auth/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(loginData)
})
.then(response => response.json())
.then(data => console.log(data))
.catch(error => console.error('Error:', error));
```

---

## 6. Ghi Chú

- **Token xác thực**: Sau khi đăng nhập thành công, sử dụng giá trị `access_token` trong header `Authorization` với dạng `Bearer <token>` cho các request tiếp theo.
- **Hết hạn token**: Token JWT có thời hạn nhất định. Khi hết hạn, sử dụng API Làm mới Token để lấy token mới.
- **Bảo mật**: Luôn gửi request qua HTTPS trong môi trường production.

---

## 7. Các API Liên Quan

- [API Làm Mới Token](#api-làm-mới-token)
- [API Đăng Xuất](#api-đăng-xuất)
- [API Lấy Thông Tin Người Dùng Hiện Tại](#api-lấy-thông-tin-người-dùng-hiện-tại)
- [API Đổi Mật Khẩu](#api-đổi-mật-khẩu)

---

# API Làm Mới Token

## 1. Mô Tả Thông Tin API

### Endpoint
- **URL**: `/api/v1/refresh-token`
- **Method**: `POST`

### Header Request
```json
{
  "Content-Type": "application/json",
  "Authorization": "Bearer <access_token>"
}
```

### Body Request
```json
{}
```

---

## 2. Mô Tả Tham Số

| Tham Số | Kiểu Dữ Liệu | Bắt Buộc | Mô Tả |
|---------|--------------|---------|-------|
| (Header) Authorization | String | ✓ | Token JWT hiện tại với format: `Bearer <token>` |

---

## 3. Mô Tả Kết Quả Trả Về

| Tham Số | Kiểu Dữ Liệu | Mô Tả |
|---------|--------------|-------|
| code | Integer | Mã HTTP status |
| status | String | Trạng thái phản hồi (Success/Error) |
| message | String | Thông báo kết quả |
| data | Object | Dữ liệu token mới |
| data.access_token | String | Chuỗi token xác thực JWT mới |

---

## 4. Ví Dụ Kết Quả Trả Về

### Thành Công (200)

```json
{
  "code": 200,
  "status": "Success",
  "message": "Làm mới token thành công",
  "data": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJsb2dpbiI6ImFkbWluIiwiZGV2aWNlX2lkIjoiUG9zdG1hbiIsInRzIjoxNzU2MTk0MDIxLjUwMzk1NH0.newTokenHashHere"
  }
}
```

### Lỗi - Token không hợp lệ (401)

```json
{
  "code": 401,
  "status": "Error",
  "message": "Lỗi: Token không hợp lệ hoặc đã hết hạn"
}
```

---

# API Đăng Xuất

## 1. Mô Tả Thông Tin API

### Endpoint
- **URL**: `/api/v1/logout`
- **Method**: `POST`

### Header Request
```json
{
  "Content-Type": "application/json",
  "Authorization": "Bearer <access_token>"
}
```

### Body Request
```json
{}
```

---

## 2. Mô Tả Tham Số

| Tham Số | Kiểu Dữ Liệu | Bắt Buộc | Mô Tả |
|---------|--------------|---------|-------|
| (Header) Authorization | String | ✓ | Token JWT hiện tại với format: `Bearer <token>` |

---

## 3. Mô Tả Kết Quả Trả Về

| Tham Số | Kiểu Dữ Liệu | Mô Tả |
|---------|--------------|-------|
| code | Integer | Mã HTTP status |
| status | String | Trạng thái phản hồi (Success/Error) |
| message | String | Thông báo kết quả |

---

## 4. Ví Dụ Kết Quả Trả Về

### Thành Công (200)

```json
{
  "code": 200,
  "status": "Success",
  "message": "Đã đăng xuất thành công"
}
```

### Lỗi - Token không hợp lệ (401)

```json
{
  "code": 401,
  "status": "Error",
  "message": "Lỗi: Token không hợp lệ hoặc đã hết hạn"
}
```

---

# API Lấy Thông Tin Người Dùng Hiện Tại

## 1. Mô Tả Thông Tin API

### Endpoint
- **URL**: `/api/v1/refresh-info`
- **Method**: `POST`

### Header Request
```json
{
  "Content-Type": "application/json",
  "Authorization": "Bearer <access_token>"
}
```

### Body Request
```json
{}
```

---

## 2. Mô Tả Tham Số

| Tham Số | Kiểu Dữ Liệu | Bắt Buộc | Mô Tả |
|---------|--------------|---------|-------|
| (Header) Authorization | String | ✓ | Token JWT hiện tại với format: `Bearer <token>` |

---

## 3. Mô Tả Kết Quả Trả Về

| Tham Số | Kiểu Dữ Liệu | Mô Tả |
|---------|--------------|-------|
| code | Integer | Mã HTTP status |
| status | String | Trạng thái phản hồi (Success/Error) |
| message | String | Thông báo kết quả |
| data | Object | Dữ liệu người dùng |
| data.user_id | Object | Thông tin người dùng |
| data.user_id.id | Integer | ID người dùng |
| data.user_id.name | String | Tên người dùng |
| data.user_id.email | String | Email người dùng |
| data.partner_id | Object | Thông tin đối tác liên kết |
| data.partner_id.id | Integer | ID đối tác |
| data.partner_id.name | String | Tên đối tác |
| data.company_id | Object | Thông tin công ty |
| data.company_id.id | Integer | ID công ty |
| data.company_id.name | String | Tên công ty |
| data.department_id | Object | Thông tin phòng ban |
| data.department_id.id | Integer hoặc Boolean | ID phòng ban (false nếu không có) |
| data.department_id.name | String | Tên phòng ban |
| data.employee_id | Object | Thông tin nhân viên |
| data.employee_id.id | Integer hoặc Boolean | ID nhân viên (false nếu không có) |
| data.employee_id.name | String | Tên nhân viên |

---

## 4. Ví Dụ Kết Quả Trả Về

### Thành Công (200)

```json
{
  "code": 200,
  "status": "Success",
  "message": "Lấy thông tin người dùng thành công",
  "data": {
    "user_id": {
      "id": 2,
      "name": "Administrator",
      "email": "admin"
    },
    "partner_id": {
      "id": 3,
      "name": "Administrator"
    },
    "company_id": {
      "id": 1,
      "name": "CÔNG TY CỔ PHẦN ĐẦU TƯ VÀ DU LỊCH VẠN HƯƠNG"
    },
    "department_id": {
      "id": false,
      "name": ""
    },
    "employee_id": {
      "id": false,
      "name": ""
    }
  }
}
```

### Lỗi - Token không hợp lệ (401)

```json
{
  "code": 401,
  "status": "Error",
  "message": "Lỗi: Token không hợp lệ hoặc đã hết hạn"
}
```

---

# API Đổi Mật Khẩu

## 1. Mô Tả Thông Tin API

### Endpoint
- **URL**: `/api/v1/change-password`
- **Method**: `POST`

### Header Request
```json
{
  "Content-Type": "application/json",
  "Authorization": "Bearer <access_token>"
}
```

### Body Request
```json
{
  "old_password": "mật_khẩu_cũ",
  "new_password": "mật_khẩu_mới",
  "confirm_password": "xác_nhận_mật_khẩu_mới"
}
```

---

## 2. Mô Tả Tham Số

| Tham Số | Kiểu Dữ Liệu | Bắt Buộc | Mô Tả |
|---------|--------------|---------|-------|
| (Header) Authorization | String | ✓ | Token JWT hiện tại với format: `Bearer <token>` |
| old_password | String | ✓ | Mật khẩu cũ của người dùng |
| new_password | String | ✓ | Mật khẩu mới muốn đặt |
| confirm_password | String | ✓ | Xác nhận mật khẩu mới (phải giống new_password) |

---

## 3. Mô Tả Kết Quả Trả Về

| Tham Số | Kiểu Dữ Liệu | Mô Tả |
|---------|--------------|-------|
| code | Integer | Mã HTTP status |
| status | String | Trạng thái phản hồi (Success/Error) |
| message | String | Thông báo kết quả |

---

## 4. Ví Dụ Kết Quả Trả Về

### Thành Công (200)

```json
{
  "code": 200,
  "status": "Success",
  "message": "Đổi mật khẩu thành công"
}
```

### Lỗi - Mật khẩu cũ không chính xác (400)

```json
{
  "code": 400,
  "status": "Error",
  "message": "Lỗi: Mật khẩu cũ không chính xác"
}
```

### Lỗi - Xác nhận mật khẩu không trùng khớp (400)

```json
{
  "code": 400,
  "status": "Error",
  "message": "Lỗi: Xác nhận mật khẩu không trùng khớp"
}
```

### Lỗi - Token không hợp lệ (401)

```json
{
  "code": 401,
  "status": "Error",
  "message": "Lỗi: Token không hợp lệ hoặc đã hết hạn"
}
```

---

# API Chấm Công (Attendance)

## 1. API Chấm Công Vào

### 1.1 Mô Tả Thông Tin API

#### Endpoint
- **URL**: `/api/v1/attendance/check-in`
- **Method**: `POST`

#### Header Request
```json
{
  "Content-Type": "application/json",
  "Authorization": "Bearer <access_token>"
}
```

#### Body Request
```json
{
  "in_latitude": "10.7769",
  "in_longitude": "106.7009",
  "check_in_location": "Văn phòng chính"
}
```

---

### 1.2 Mô Tả Tham Số

| Tham Số | Kiểu Dữ Liệu | Bắt Buộc | Mô Tả |
|---------|--------------|---------|-------|
| (Header) Authorization | String | ✓ | Token JWT với format: `Bearer <token>` |
| in_latitude | String | ✓ | Vĩ độ GPS vị trí chấm công vào |
| in_longitude | String | ✓ | Kinh độ GPS vị trí chấm công vào |
| check_in_location | String | ✓ | Tên địa điểm chấm công vào |

---

### 1.3 Mô Tả Kết Quả Trả Về

| Tham Số | Kiểu Dữ Liệu | Mô Tả |
|---------|--------------|-------|
| code | Integer | Mã HTTP status |
| status | String | Trạng thái phản hồi (Success/Error) |
| message | String | Thông báo kết quả |
| data | Object | Dữ liệu chấm công vào |
| data.id | Integer | ID bản ghi chấm công |
| data.check_in | String | Thời gian chấm công vào (format: YYYY-MM-DD HH:MM:SS) |
| data.employee_name | String | Tên nhân viên |

---

### 1.4 Ví Dụ Kết Quả Trả Về

**Thành Công (200)**
```json
{
  "code": 200,
  "status": "Success",
  "message": "Chấm công vào thành công",
  "data": {
    "id": 15,
    "check_in": "2024-01-15 08:30:45",
    "employee_name": "Nguyễn Văn A"
  }
}
```

**Lỗi - Token không hợp lệ (401)**
```json
{
  "code": 401,
  "status": "Error",
  "message": "Lỗi: Token không hợp lệ hoặc đã hết hạn"
}
```

---

## 2. API Chấm Công Ra

### 2.1 Mô Tả Thông Tin API

#### Endpoint
- **URL**: `/api/v1/attendance/check-out`
- **Method**: `POST`

#### Header Request
```json
{
  "Content-Type": "application/json",
  "Authorization": "Bearer <access_token>"
}
```

#### Body Request
```json
{
  "out_latitude": "10.7769",
  "out_longitude": "106.7009",
  "check_out_location": "Văn phòng chính"
}
```

---

### 2.2 Mô Tả Tham Số

| Tham Số | Kiểu Dữ Liệu | Bắt Buộc | Mô Tả |
|---------|--------------|---------|-------|
| (Header) Authorization | String | ✓ | Token JWT với format: `Bearer <token>` |
| out_latitude | String | ✓ | Vĩ độ GPS vị trí chấm công ra |
| out_longitude | String | ✓ | Kinh độ GPS vị trí chấm công ra |
| check_out_location | String | ✓ | Tên địa điểm chấm công ra |

---

### 2.3 Mô Tả Kết Quả Trả Về

| Tham Số | Kiểu Dữ Liệu | Mô Tả |
|---------|--------------|-------|
| code | Integer | Mã HTTP status |
| status | String | Trạng thái phản hồi (Success/Error) |
| message | String | Thông báo kết quả |
| data | Object | Dữ liệu chấm công ra |
| data.id | Integer | ID bản ghi chấm công |
| data.check_out | String | Thời gian chấm công ra (format: YYYY-MM-DD HH:MM:SS) |
| data.worked_hours | String | Tổng số giờ làm việc |
| data.employee_name | String | Tên nhân viên |

---

### 2.4 Ví Dụ Kết Quả Trả Về

**Thành Công (200)**
```json
{
  "code": 200,
  "status": "Success",
  "message": "Chấm công ra thành công",
  "data": {
    "id": 15,
    "check_out": "2024-01-15 17:30:45",
    "worked_hours": "9.0",
    "employee_name": "Nguyễn Văn A"
  }
}
```

**Lỗi - Token không hợp lệ (401)**
```json
{
  "code": 401,
  "status": "Error",
  "message": "Lỗi: Token không hợp lệ hoặc đã hết hạn"
}
```

---

## 3. API Lấy Trạng Thái Chấm Công Hiện Tại

### 3.1 Mô Tả Thông Tin API

#### Endpoint
- **URL**: `/api/v1/attendance/status`
- **Method**: `POST`

#### Header Request
```json
{
  "Content-Type": "application/json",
  "Authorization": "Bearer <access_token>"
}
```

#### Body Request
```json
{}
```

---

### 3.2 Mô Tả Tham Số

| Tham Số | Kiểu Dữ Liệu | Bắt Buộc | Mô Tả |
|---------|--------------|---------|-------|
| (Header) Authorization | String | ✓ | Token JWT với format: `Bearer <token>` |

---

### 3.3 Mô Tả Kết Quả Trả Về

| Tham Số | Kiểu Dữ Liệu | Mô Tả |
|---------|--------------|-------|
| code | Integer | Mã HTTP status |
| status | String | Trạng thái phản hồi (Success/Error) |
| message | String | Thông báo kết quả |
| data | Object | Dữ liệu trạng thái chấm công |
| data.state | String | Trạng thái hiện tại (working/not_working) |
| data.last_check_in | String | Thời gian chấm công vào gần nhất |
| data.last_check_out | String | Thời gian chấm công ra gần nhất |
| data.today_worked_hours | String | Tổng giờ làm việc hôm nay |

---

### 3.4 Ví Dụ Kết Quả Trả Về

**Thành Công (200)**
```json
{
  "code": 200,
  "status": "Success",
  "message": "Trạng thái chấm công",
  "data": {
    "state": "working",
    "last_check_in": "2024-01-15 08:30:45",
    "last_check_out": "2024-01-14 17:30:00",
    "today_worked_hours": "8.5"
  }
}
```

---

## 4. API Lấy Lịch Sử Chấm Công

### 4.1 Mô Tả Thông Tin API

#### Endpoint
- **URL**: `/api/v1/attendance/history`
- **Method**: `POST`

#### Header Request
```json
{
  "Content-Type": "application/json",
  "Authorization": "Bearer <access_token>"
}
```

#### Body Request
```json
{
  "limit": 30,
  "offset": 0,
  "from_date": "2024-01-01",
  "to_date": "2024-01-31"
}
```

---

### 4.2 Mô Tả Tham Số

| Tham Số | Kiểu Dữ Liệu | Bắt Buộc | Mô Tả |
|---------|--------------|---------|-------|
| (Header) Authorization | String | ✓ | Token JWT với format: `Bearer <token>` |
| limit | Integer |   | Số bản ghi trên một trang (mặc định: 30) |
| offset | Integer |   | Vị trí bắt đầu (mặc định: 0) |
| from_date | String |   | Ngày bắt đầu (format: YYYY-MM-DD) |
| to_date | String |   | Ngày kết thúc (format: YYYY-MM-DD) |

---

### 4.3 Mô Tả Kết Quả Trả Về

| Tham Số | Kiểu Dữ Liệu | Mô Tả |
|---------|--------------|-------|
| code | Integer | Mã HTTP status |
| status | String | Trạng thái phản hồi (Success/Error) |
| message | String | Thông báo kết quả |
| data | Object | Dữ liệu lịch sử chấm công |
| data.attendances | Array | Danh sách chấm công |
| data.attendances[].id | Integer | ID bản ghi chấm công |
| data.attendances[].check_in | String | Thời gian chấm công vào |
| data.attendances[].check_out | String | Thời gian chấm công ra |
| data.attendances[].worked_hours | String | Tổng giờ làm việc |
| data.total_record | Integer | Tổng số bản ghi |
| data.next_page | Boolean | Có trang tiếp theo hay không |

---

### 4.4 Ví Dụ Kết Quả Trả Về

**Thành Công (200)**
```json
{
  "code": 200,
  "status": "Success",
  "message": "Lịch sử chấm công",
  "data": {
    "attendances": [
      {
        "id": 15,
        "check_in": "2024-01-15 08:30:45",
        "check_out": "2024-01-15 17:30:45",
        "worked_hours": "9.0"
      },
      {
        "id": 14,
        "check_in": "2024-01-14 08:25:30",
        "check_out": "2024-01-14 17:15:20",
        "worked_hours": "8.8"
      }
    ],
    "total_record": 22,
    "next_page": true
  }
}
```

---

## 5. API Lấy Tổng Hợp Chấm Công Theo Tháng

### 5.1 Mô Tả Thông Tin API

#### Endpoint
- **URL**: `/api/v1/attendance/summary`
- **Method**: `POST`

#### Header Request
```json
{
  "Content-Type": "application/json",
  "Authorization": "Bearer <access_token>"
}
```

#### Body Request
```json
{
  "month": "2024-01"
}
```

---

### 5.2 Mô Tả Tham Số

| Tham Số | Kiểu Dữ Liệu | Bắt Buộc | Mô Tả |
|---------|--------------|---------|-------|
| (Header) Authorization | String | ✓ | Token JWT với format: `Bearer <token>` |
| month | String | ✓ | Tháng cần lấy tổng hợp (format: YYYY-MM) |

---

### 5.3 Mô Tả Kết Quả Trả Về

| Tham Số | Kiểu Dữ Liệu | Mô Tả |
|---------|--------------|-------|
| code | Integer | Mã HTTP status |
| status | String | Trạng thái phản hồi (Success/Error) |
| message | String | Thông báo kết quả |
| data | Object | Dữ liệu tổng hợp chấm công |
| data.month | String | Tháng được tổng hợp |
| data.total_days | Integer | Tổng số ngày trong tháng |
| data.worked_days | Integer | Số ngày đã chấm công |
| data.absent_days | Integer | Số ngày vắng mặt |
| data.total_hours | String | Tổng số giờ làm việc |
| data.average_hours_per_day | String | Trung bình giờ làm việc/ngày |

---

### 5.4 Ví Dụ Kết Quả Trả Về

**Thành Công (200)**
```json
{
  "code": 200,
  "status": "Success",
  "message": "Tổng hợp chấm công",
  "data": {
    "month": "2024-01",
    "total_days": 31,
    "worked_days": 20,
    "absent_days": 3,
    "total_hours": "160.5",
    "average_hours_per_day": "8.0"
  }
}
```

---

## 6. API Lấy Chi Tiết Bản Ghi Chấm Công

### 6.1 Mô Tả Thông Tin API

#### Endpoint
- **URL**: `/api/v1/attendance/detail`
- **Method**: `POST`

#### Header Request
```json
{
  "Content-Type": "application/json",
  "Authorization": "Bearer <access_token>"
}
```

#### Body Request
```json
{
  "attendance_id": 15
}
```

---

### 6.2 Mô Tả Tham Số

| Tham Số | Kiểu Dữ Liệu | Bắt Buộc | Mô Tả |
|---------|--------------|---------|-------|
| (Header) Authorization | String | ✓ | Token JWT với format: `Bearer <token>` |
| attendance_id | Integer | ✓ | ID bản ghi chấm công cần lấy chi tiết |

---

### 6.3 Mô Tả Kết Quả Trả Về

| Tham Số | Kiểu Dữ Liệu | Mô Tả |
|---------|--------------|-------|
| code | Integer | Mã HTTP status |
| status | String | Trạng thái phản hồi (Success/Error) |
| message | String | Thông báo kết quả |
| data | Object | Dữ liệu chi tiết chấm công |
| data.id | Integer | ID bản ghi chấm công |
| data.employee_name | String | Tên nhân viên |
| data.department_name | String | Tên phòng ban |
| data.check_in | String | Thời gian chấm công vào |
| data.check_in_location | String | Vị trí chấm công vào |
| data.check_out | String | Thời gian chấm công ra |
| data.check_out_location | String | Vị trí chấm công ra |
| data.worked_hours | String | Tổng giờ làm việc |

---

### 6.4 Ví Dụ Kết Quả Trả Về

**Thành Công (200)**
```json
{
  "code": 200,
  "status": "Success",
  "message": "Chi tiết bản ghi chấm công",
  "data": {
    "id": 15,
    "employee_name": "Nguyễn Văn A",
    "department_name": "Phòng Kinh Doanh",
    "check_in": "2024-01-15 08:30:45",
    "check_in_location": "Văn phòng chính",
    "check_out": "2024-01-15 17:30:45",
    "check_out_location": "Văn phòng chính",
    "worked_hours": "9.0"
  }
}
```

**Lỗi - Bản ghi không tồn tại (404)**
```json
{
  "code": 404,
  "status": "Error",
  "message": "Lỗi: Bản ghi chấm công không tồn tại"
}
```

---

# API Bảng Lương (Payslip)

## 1. API Lấy Danh Sách Bảng Lương

### 1.1 Mô Tả Thông Tin API

#### Endpoint
- **URL**: `/api/v1/payslip/list`
- **Method**: `POST`

#### Header Request
```json
{
  "Content-Type": "application/json",
  "Authorization": "Bearer <access_token>"
}
```

#### Body Request
```json
{}
```

---

### 1.2 Mô Tả Tham Số

| Tham Số | Kiểu Dữ Liệu | Bắt Buộc | Mô Tả |
|---------|--------------|---------|-------|
| (Header) Authorization | String | ✓ | Token JWT với format: `Bearer <token>` |

---

### 1.3 Mô Tả Kết Quả Trả Về

| Tham Số | Kiểu Dữ Liệu | Mô Tả |
|---------|--------------|-------|
| code | Integer | Mã HTTP status |
| status | String | Trạng thái phản hồi (Success/Error) |
| message | String | Thông báo kết quả |
| data | Object | Dữ liệu bảng lương |
| data.payslips | Array | Danh sách bảng lương |
| data.payslips[].id | Integer | ID bảng lương |
| data.payslips[].name | String | Tên bảng lương |
| data.payslips[].month | String | Tháng lương (format: YYYY-MM) |
| data.payslips[].employee_id | Integer | ID nhân viên |
| data.payslips[].employee_name | String | Tên nhân viên |
| data.payslips[].state | String | Trạng thái (draft/done/cancel) |
| data.payslips[].date_from | String | Ngày bắt đầu kỳ lương |
| data.payslips[].date_to | String | Ngày kết thúc kỳ lương |
| data.total | Integer | Tổng số bảng lương |

---

### 1.4 Ví Dụ Kết Quả Trả Về

**Thành Công (200)**
```json
{
  "code": 200,
  "status": "Success",
  "message": "Lấy danh sách bảng lương thành công",
  "data": {
    "payslips": [
      {
        "id": 1,
        "name": "Salary Slip - Nguyễn Văn A - 2024-01",
        "month": "2024-01",
        "employee_id": 5,
        "employee_name": "Nguyễn Văn A",
        "state": "done",
        "date_from": "2024-01-01",
        "date_to": "2024-01-31"
      },
      {
        "id": 2,
        "name": "Salary Slip - Trần Thị B - 2024-01",
        "month": "2024-01",
        "employee_id": 6,
        "employee_name": "Trần Thị B",
        "state": "done",
        "date_from": "2024-01-01",
        "date_to": "2024-01-31"
      }
    ],
    "total": 2
  }
}
```

**Lỗi - Token không hợp lệ (401)**
```json
{
  "code": 401,
  "status": "Error",
  "message": "Lỗi: Token không hợp lệ hoặc đã hết hạn"
}
```

---

## 2. API Lấy Chi Tiết Bảng Lương

### 2.1 Mô Tả Thông Tin API

#### Endpoint
- **URL**: `/api/v1/payslip/detail`
- **Method**: `POST`

#### Header Request
```json
{
  "Content-Type": "application/json",
  "Authorization": "Bearer <access_token>"
}
```

#### Body Request
```json
{
  "employee_id": 5,
  "month": "2024-01"
}
```

---

### 2.2 Mô Tả Tham Số

| Tham Số | Kiểu Dữ Liệu | Bắt Buộc | Mô Tả |
|---------|--------------|---------|-------|
| (Header) Authorization | String | ✓ | Token JWT với format: `Bearer <token>` |
| employee_id | Integer | ✓ | ID nhân viên cần lấy chi tiết bảng lương |
| month | String | ✓ | Tháng cần lấy chi tiết (format: YYYY-MM) |

---

### 2.3 Mô Tả Kết Quả Trả Về

| Tham Số | Kiểu Dữ Liệu | Mô Tả |
|---------|--------------|-------|
| code | Integer | Mã HTTP status |
| status | String | Trạng thái phản hồi (Success/Error) |
| message | String | Thông báo kết quả |
| data | Object | Dữ liệu chi tiết bảng lương |
| data.id | Integer | ID bảng lương |
| data.employee_id | Integer | ID nhân viên |
| data.employee_name | String | Tên nhân viên |
| data.month | String | Tháng lương |
| data.date_from | String | Ngày bắt đầu kỳ lương |
| data.date_to | String | Ngày kết thúc kỳ lương |
| data.state | String | Trạng thái bảng lương |
| data.basic_salary | Float | Lương cơ bản |
| data.gross_salary | Float | Lương thực lãnh |
| data.deductions | Float | Các khoản khấu trừ |
| data.net_salary | Float | Lương ròng |
| data.line_ids | Array | Chi tiết từng khoản |
| data.line_ids[].name | String | Tên khoản |
| data.line_ids[].amount | Float | Số tiền |
| data.line_ids[].slip_type | String | Loại khoản (earnings/deductions) |

---

### 2.4 Ví Dụ Kết Quả Trả Về

**Thành Công (200)**
```json
{
  "code": 200,
  "status": "Success",
  "message": "Lấy chi tiết bảng lương thành công",
  "data": {
    "id": 1,
    "employee_id": 5,
    "employee_name": "Nguyễn Văn A",
    "month": "2024-01",
    "date_from": "2024-01-01",
    "date_to": "2024-01-31",
    "state": "done",
    "basic_salary": 10000000,
    "gross_salary": 11000000,
    "deductions": 1000000,
    "net_salary": 10000000,
    "line_ids": [
      {
        "name": "Lương cơ bản",
        "amount": 10000000,
        "slip_type": "earnings"
      },
      {
        "name": "Phụ cấp",
        "amount": 1000000,
        "slip_type": "earnings"
      },
      {
        "name": "Bảo hiểm xã hội",
        "amount": 700000,
        "slip_type": "deductions"
      },
      {
        "name": "Thuế thu nhập cá nhân",
        "amount": 300000,
        "slip_type": "deductions"
      }
    ]
  }
}
```

**Lỗi - Bảng lương không tồn tại (404)**
```json
{
  "code": 404,
  "status": "Error",
  "message": "Lỗi: Bảng lương không tồn tại"
}
```

---

## 3. API Lấy Dữ Liệu Bảng Lương

### 3.1 Mô Tả Thông Tin API

#### Endpoint
- **URL**: `/api/v1/payslip/data`
- **Method**: `POST`

#### Header Request
```json
{
  "Content-Type": "application/json",
  "Authorization": "Bearer <access_token>"
}
```

#### Body Request
```json
{
  "employee_id": 5
}
```

---

### 3.2 Mô Tả Tham Số

| Tham Số | Kiểu Dữ Liệu | Bắt Buộc | Mô Tả |
|---------|--------------|---------|-------|
| (Header) Authorization | String | ✓ | Token JWT với format: `Bearer <token>` |
| employee_id | Integer | ✓ | ID nhân viên cần lấy dữ liệu bảng lương |

---

### 3.3 Mô Tả Kết Quả Trả Về

| Tham Số | Kiểu Dữ Liệu | Mô Tả |
|---------|--------------|-------|
| code | Integer | Mã HTTP status |
| status | String | Trạng thái phản hồi (Success/Error) |
| message | String | Thông báo kết quả |
| data | Object | Dữ liệu bảng lương nhân viên |
| data.employee_id | Integer | ID nhân viên |
| data.employee_name | String | Tên nhân viên |
| data.job_title | String | Vị trí công việc |
| data.department | String | Tên phòng ban |
| data.company_name | String | Tên công ty |
| data.contract_id | Integer | ID hợp đồng |
| data.salary_rule_ids | Array | Danh sách công thức tính lương |
| data.salary_rule_ids[].name | String | Tên công thức |
| data.salary_rule_ids[].amount | Float | Số tiền |
| data.salary_rule_ids[].category | String | Danh mục (gross, net, etc) |
| data.recent_payslips | Array | 6 bảng lương gần đây nhất |
| data.recent_payslips[].month | String | Tháng |
| data.recent_payslips[].net_salary | Float | Lương ròng |
| data.recent_payslips[].gross_salary | Float | Lương thực lãnh |

---

### 3.4 Ví Dụ Kết Quả Trả Về

**Thành Công (200)**
```json
{
  "code": 200,
  "status": "Success",
  "message": "Lấy dữ liệu bảng lương thành công",
  "data": {
    "employee_id": 5,
    "employee_name": "Nguyễn Văn A",
    "job_title": "Quản lý dự án",
    "department": "Công nghệ",
    "company_name": "CÔNG TY CỔ PHẦN ĐẦU TƯ VÀ DU LỊCH VẠN HƯƠNG",
    "contract_id": 3,
    "salary_rule_ids": [
      {
        "name": "Lương cơ bản",
        "amount": 10000000,
        "category": "gross"
      },
      {
        "name": "Phụ cấp",
        "amount": 1000000,
        "category": "gross"
      },
      {
        "name": "Bảo hiểm xã hội",
        "amount": 700000,
        "category": "deduction"
      },
      {
        "name": "Lương ròng",
        "amount": 10300000,
        "category": "net"
      }
    ],
    "recent_payslips": [
      {
        "month": "2024-01",
        "net_salary": 10300000,
        "gross_salary": 11000000
      },
      {
        "month": "2023-12",
        "net_salary": 10300000,
        "gross_salary": 11000000
      },
      {
        "month": "2023-11",
        "net_salary": 10300000,
        "gross_salary": 11000000
      },
      {
        "month": "2023-10",
        "net_salary": 10300000,
        "gross_salary": 11000000
      },
      {
        "month": "2023-09",
        "net_salary": 10300000,
        "gross_salary": 11000000
      },
      {
        "month": "2023-08",
        "net_salary": 10300000,
        "gross_salary": 11000000
      }
    ]
  }
}
```

**Lỗi - Nhân viên không tồn tại (404)**
```json
{
  "code": 404,
  "status": "Error",
  "message": "Lỗi: Nhân viên không tồn tại"
}
```

---

# API Nhân Sự (Employee)

## 1. API Lấy Danh Sách Nhân Viên

### 1.1 Mô Tả Thông Tin API

#### Endpoint
- **URL**: `/api/v1/employee/list`
- **Method**: `POST`

#### Header Request
```json
{
  "Content-Type": "application/json",
  "Authorization": "Bearer <access_token>"
}
```

#### Body Request
```json
{
  "search": "Nguyễn",
  "department_id": 2,
  "job_id": 5,
  "active": true,
  "limit": 20,
  "page": 1
}
```

---

### 1.2 Mô Tả Tham Số

| Tham Số | Kiểu Dữ Liệu | Bắt Buộc | Mô Tả |
|---------|--------------|---------|-------|
| (Header) Authorization | String | ✓ | Token JWT với format: `Bearer <token>` |
| search | String |   | Từ khóa tìm kiếm theo tên, email, hoặc điện thoại |
| department_id | Integer |   | ID phòng ban để lọc |
| job_id | Integer |   | ID vị trí công việc để lọc |
| active | Boolean |   | Lọc theo trạng thái hoạt động (mặc định: true) |
| limit | Integer |   | Số bản ghi trên một trang (mặc định: 20) |
| page | Integer |   | Số trang (mặc định: 1) |

---

### 1.3 Mô Tả Kết Quả Trả Về

| Tham Số | Kiểu Dữ Liệu | Mô Tả |
|---------|--------------|-------|
| code | Integer | Mã HTTP status |
| status | String | Trạng thái phản hồi (Success/Error) |
| message | String | Thông báo kết quả |
| data | Object | Dữ liệu danh sách nhân viên |
| data.employees | Array | Danh sách nhân viên |
| data.employees[].id | Integer | ID nhân viên |
| data.employees[].name | String | Tên nhân viên |
| data.employees[].email | String | Email nhân viên |
| data.employees[].mobile_phone | String | Số điện thoại |
| data.employees[].job_title | String | Chức danh công việc |
| data.employees[].department_id | Integer | ID phòng ban |
| data.employees[].department_name | String | Tên phòng ban |
| data.employees[].company_id | Integer | ID công ty |
| data.employees[].img_url | String | URL ảnh đại diện |
| data.employees[].active | Boolean | Trạng thái hoạt động |
| data.total_record | Integer | Tổng số bản ghi |
| data.total_page | Integer | Tổng số trang |
| data.current_page | Integer | Trang hiện tại |

---

### 1.4 Ví Dụ Kết Quả Trả Về

**Thành Công (200)**
```json
{
  "code": 200,
  "status": "Success",
  "message": "Thành công",
  "data": {
    "employees": [
      {
        "id": 5,
        "name": "Nguyễn Văn A",
        "email": "nguyenvana@company.com",
        "mobile_phone": "0912345678",
        "job_title": "Quản lý dự án",
        "department_id": 2,
        "department_name": "Công nghệ",
        "company_id": 1,
        "img_url": "https://example.com/image/employee/5",
        "active": true
      },
      {
        "id": 6,
        "name": "Nguyễn Thị B",
        "email": "nguyenthib@company.com",
        "mobile_phone": "0912345679",
        "job_title": "Lập trình viên",
        "department_id": 2,
        "department_name": "Công nghệ",
        "company_id": 1,
        "img_url": "https://example.com/image/employee/6",
        "active": true
      }
    ],
    "total_record": 42,
    "total_page": 3,
    "current_page": 1
  }
}
```

**Lỗi - Token không hợp lệ (401)**
```json
{
  "code": 401,
  "status": "Error",
  "message": "Lỗi: Token không hợp lệ hoặc đã hết hạn"
}
```

---

## 2. API Lấy Chi Tiết Nhân Viên

### 2.1 Mô Tả Thông Tin API

#### Endpoint
- **URL**: `/api/v1/employee/detail`
- **Method**: `POST`

#### Header Request
```json
{
  "Content-Type": "application/json",
  "Authorization": "Bearer <access_token>"
}
```

#### Body Request
```json
{
  "employee_id": 5
}
```

---

### 2.2 Mô Tả Tham Số

| Tham Số | Kiểu Dữ Liệu | Bắt Buộc | Mô Tả |
|---------|--------------|---------|-------|
| (Header) Authorization | String | ✓ | Token JWT với format: `Bearer <token>` |
| employee_id | Integer | ✓ | ID nhân viên cần lấy chi tiết |

---

### 2.3 Mô Tả Kết Quả Trả Về

| Tham Số | Kiểu Dữ Liệu | Mô Tả |
|---------|--------------|-------|
| code | Integer | Mã HTTP status |
| status | String | Trạng thái phản hồi (Success/Error) |
| message | String | Thông báo kết quả |
| data | Object | Dữ liệu chi tiết nhân viên |
| data.id | Integer | ID nhân viên |
| data.name | String | Tên nhân viên |
| data.email | String | Email |
| data.mobile_phone | String | Số điện thoại di động |
| data.work_phone | String | Số điện thoại công việc |
| data.job_title | String | Chức danh công việc |
| data.department_id | Integer | ID phòng ban |
| data.department_name | String | Tên phòng ban |
| data.company_id | Integer | ID công ty |
| data.company_name | String | Tên công ty |
| data.manager_id | Integer | ID quản lý trực tiếp |
| data.manager_name | String | Tên quản lý trực tiếp |
| data.birthday | String | Ngày sinh |
| data.gender | String | Giới tính (male/female) |
| data.marital | String | Tình trạng hôn nhân |
| data.identification_id | String | CCCD/Hộ chiếu |
| data.passport_id | String | Số hộ chiếu |
| data.work_location_name | String | Địa điểm làm việc |
| data.contract_ids | Array | Danh sách hợp đồng |
| data.contract_ids[].id | Integer | ID hợp đồng |
| data.contract_ids[].date_start | String | Ngày bắt đầu |
| data.contract_ids[].date_end | String | Ngày kết thúc |
| data.img_url | String | URL ảnh đại diện |
| data.active | Boolean | Trạng thái hoạt động |

---

### 2.4 Ví Dụ Kết Quả Trả Về

**Thành Công (200)**
```json
{
  "code": 200,
  "status": "Success",
  "message": "Thành công",
  "data": {
    "id": 5,
    "name": "Nguyễn Văn A",
    "email": "nguyenvana@company.com",
    "mobile_phone": "0912345678",
    "work_phone": "08123456",
    "job_title": "Quản lý dự án",
    "department_id": 2,
    "department_name": "Công nghệ",
    "company_id": 1,
    "company_name": "CÔNG TY CỔ PHẦN ĐẦU TƯ VÀ DU LỊCH VẠN HƯƠNG",
    "manager_id": 4,
    "manager_name": "Trần Văn C",
    "birthday": "1990-05-15",
    "gender": "male",
    "marital": "married",
    "identification_id": "012345678901",
    "passport_id": "C1234567",
    "work_location_name": "Hà Nội",
    "contract_ids": [
      {
        "id": 8,
        "date_start": "2022-01-01",
        "date_end": false
      }
    ],
    "img_url": "https://example.com/image/employee/5",
    "active": true
  }
}
```

**Lỗi - Nhân viên không tồn tại (404)**
```json
{
  "code": 404,
  "status": "Error",
  "message": "Lỗi: Nhân viên không tồn tại"
}
```

---

## 3. API Lấy Danh Sách Phòng Ban và Nhân Viên

### 3.1 Mô Tả Thông Tin API

#### Endpoint
- **URL**: `/api/v1/employee/get_departments_and_employee`
- **Method**: `POST`

#### Header Request
```json
{
  "Content-Type": "application/json",
  "Authorization": "Bearer <access_token>"
}
```

#### Body Request
```json
{}
```

---

### 3.2 Mô Tả Tham Số

| Tham Số | Kiểu Dữ Liệu | Bắt Buộc | Mô Tả |
|---------|--------------|---------|-------|
| (Header) Authorization | String | ✓ | Token JWT với format: `Bearer <token>` |

---

### 3.3 Mô Tả Kết Quả Trả Về

| Tham Số | Kiểu Dữ Liệu | Mô Tả |
|---------|--------------|-------|
| code | Integer | Mã HTTP status |
| status | String | Trạng thái phản hồi (Success/Error) |
| message | String | Thông báo kết quả |
| data | Object | Dữ liệu phòng ban và nhân viên |
| data.departments | Array | Danh sách phòng ban |
| data.departments[].id | Integer | ID phòng ban |
| data.departments[].name | String | Tên phòng ban |
| data.departments[].manager_id | Integer | ID quản lý phòng ban |
| data.departments[].manager_name | String | Tên quản lý phòng ban |
| data.employees | Array | Danh sách nhân viên |
| data.employees[].id | Integer | ID nhân viên |
| data.employees[].name | String | Tên nhân viên |
| data.employees[].email | String | Email nhân viên |
| data.employees[].department_id | Integer | ID phòng ban |
| data.employees[].department_name | String | Tên phòng ban |
| data.employees[].job_title | String | Chức danh công việc |
| data.employees[].mobile_phone | String | Số điện thoại |
| data.employees[].img_url | String | URL ảnh đại diện |

---

### 3.4 Ví Dụ Kết Quả Trả Về

**Thành Công (200)**
```json
{
  "code": 200,
  "status": "Success",
  "message": "Thành công",
  "data": {
    "departments": [
      {
        "id": 1,
        "name": "Công ty",
        "manager_id": false,
        "manager_name": ""
      },
      {
        "id": 2,
        "name": "Công nghệ",
        "manager_id": 4,
        "manager_name": "Trần Văn C"
      },
      {
        "id": 3,
        "name": "Kinh Doanh",
        "manager_id": 7,
        "manager_name": "Lê Thị D"
      }
    ],
    "employees": [
      {
        "id": 5,
        "name": "Nguyễn Văn A",
        "email": "nguyenvana@company.com",
        "department_id": 2,
        "department_name": "Công nghệ",
        "job_title": "Quản lý dự án",
        "mobile_phone": "0912345678",
        "img_url": "https://example.com/image/employee/5"
      },
      {
        "id": 6,
        "name": "Nguyễn Thị B",
        "email": "nguyenthib@company.com",
        "department_id": 2,
        "department_name": "Công nghệ",
        "job_title": "Lập trình viên",
        "mobile_phone": "0912345679",
        "img_url": "https://example.com/image/employee/6"
      },
      {
        "id": 7,
        "name": "Lê Thị D",
        "email": "lethid@company.com",
        "department_id": 3,
        "department_name": "Kinh Doanh",
        "job_title": "Trưởng phòng",
        "mobile_phone": "0912345680",
        "img_url": "https://example.com/image/employee/7"
      }
    ]
  }
}
```

**Lỗi - Token không hợp lệ (401)**
```json
{
  "code": 401,
  "status": "Error",
  "message": "Lỗi: Token không hợp lệ hoặc đã hết hạn"
}
```
