# LUỒNG 3D CHI TIẾT CỦA STOCK_3D_CUSTOM_VIEW (ĐÃ KIỂM TRA CODE)

## 📋 TỔNG QUAN LUỒNG

```
FLOW 1: LIST VIEW (Preview Layout từ Locations list)
┌─────────────────────────────────────────────────┐
│ USER CLICKS "Preview Layout" BUTTON              │
│ (trong Locations list view)                      │
└─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│ listview_3d.js: open3DView() function           │
└─────────────────────────────────────────────────┘
    ├─ 1️⃣ RPC /3Dstock/warehouse → Get warehouse list
    │      (user có thể select warehouse từ dropdown)
    │
    ├─ 2️⃣ RPC /3Dstock/data → Get location dimensions + positions
    │      (dữ liệu tất cả locations)
    │
    ├─ 3️⃣ FOR EACH LOCATION: RPC /3Dstock/data/quantity
    │      (lấy stock quantity để tính load%)
    │
    └─ 4️⃣ Create Three.js Scene + Render 3D
           - Create base floor (800×800 px)
           - For each location: create 3D box
           - Color based on load% (RED/YELLOW/GREEN/GRAY)
           - Add location code label text
           - Setup OrbitControls for interaction

---

FLOW 2: FORM VIEW (Preview Layout từ Location form)
┌─────────────────────────────────────────────────┐
│ USER CLICKS "Preview Layout" BUTTON              │
│ (trong Location form, single location)           │
└─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│ form_3d_view.js: Open3DView() function          │
└─────────────────────────────────────────────────┘
    ├─ 1️⃣ RPC /3Dstock/data/standalone → Get ALL locations
    │      (của warehouse này, cho context)
    │      Input: company_id, loc_id
    │
    ├─ 2️⃣ FOR EACH LOCATION: RPC /3Dstock/data/quantity
    │      (lấy stock quantity)
    │
    └─ 3️⃣ Create Three.js Scene + Render 3D
           (tương tự LIST VIEW)

---

USER INTERACTIONS:
├─ Drag Mouse: Rotate 3D view (OrbitControls)
├─ Scroll: Zoom in/out
├─ Click Box: Show location details modal
│          (via RPC /3Dstock/data/product)
└─ Select Warehouse Dropdown: Reload scene for new warehouse
```

---

## 🔧 BACKEND LAYER - MODELS

### File: `models/stock_location.py`

**Thêm các fields 3D vào stock.location:**

```python
class StockLocation(models.Model):
    _inherit = 'stock.location'
    
    # DIMENSION FIELDS (Size of location)
    length = fields.Float()  # Chiều dài (meter)
    width = fields.Float()   # Chiều rộng (meter)
    height = fields.Float()  # Chiều cao (meter)
    
    # POSITION FIELDS (Where is location in warehouse)
    pos_x = fields.Float()   # X axis position (pixel)
    pos_y = fields.Float()   # Y axis position (pixel)
    pos_z = fields.Float()   # Z axis position (pixel)
    
    # IDENTIFICATION FIELDS
    unique_code = fields.Char()  # Location Code (e.g., "LOC001") ← CRITICAL!
    max_capacity = fields.Integer()  # Max units allowed
    
    # SQL CONSTRAINT: unique_code phải unique per company
    _sql_constraints = [
        ('unique_code', 'UNIQUE(unique_code)',
         "The location code must be unique per company !"),
    ]
```

**Nút Action:**
```python
def action_view_location_3d_button(self):
    return {
        'type': 'ir.actions.client',
        'tag': 'open_form_3d_view',  # ← Trigger JS Client Action
        'context': {
            'loc_id': self.id,
            'company_id': self.company_id.id,
        }
    }
```

---

## 🌐 API ENDPOINTS - CONTROLLERS (5 ENDPOINTS)

### File: `controllers/stock_3d_view.py`

#### 1️⃣ ENDPOINT: `/3Dstock/warehouse`
**Lấy danh sách kho trong công ty**

```python
@http.route('/3Dstock/warehouse', type='json', auth='public')
def get_warehouse_data(self, company_id):
    # INPUT: company_id
    # LOGIC:
    # 1. Search all warehouses
    # 2. Filter by company_id
    # 3. Return list of (warehouse_id, warehouse_name)
    
    # RESPONSE:
    # [
    #     (1, "San Francisco"),
    #     (2, "New York")
    # ]
    
    # USAGE: Populate warehouse dropdown ở 3D view
```

---

#### 2️⃣ ENDPOINT: `/3Dstock/data`
**Lấy DIMENSION + POSITION của tất cả INTERNAL LOCATIONS (dùng cho LIST VIEW)**

```python
@http.route('/3Dstock/data', type='json', auth='public')
def get_stock_data(self, company_id, wh_id):
    # INPUT: company_id, wh_id (selected warehouse)
    # LOGIC:
    # 1. Get warehouse by wh_id
    # 2. Search locations:
    #    - company_id = company_id
    #    - active = true
    #    - usage = 'internal'  ← ONLY INTERNAL
    # 3. Filter out system locations:
    #    - lot_stock_id (Main/Bin location)
    #    - wh_input_stock_loc_id (Input location)
    #    - wh_qc_stock_loc_id (QC location)
    #    - wh_pack_stock_loc_id (Packing location)
    #    - wh_output_stock_loc_id (Output location)
    # 4. Convert dimensions from meter to pixel:
    #    length_px = length_meter * 3.779 * 2
    #    width_px = width_meter * 3.779 * 2
    #    height_px = height_meter * 3.779 * 2
    #    (3.779 là conversion factor từ meter to inch, *2 để scale up)
    # 5. Return dictionary
    
    # RESPONSE FORMAT:
    # {
    #     "LOC001": [0, 0, 0, 37, 30, 22],
    #     "LOC002": [100, 0, 0, 37, 30, 22],
    #     "LOC003": [200, 0, 0, 37, 30, 22]
    # }
    # WHERE: [pos_x, pos_y, pos_z, length_px, width_px, height_px]
    
    # USAGE: List view 3D scene initialization
    # CALLED: Once per warehouse selection
```

---

#### 3️⃣ ENDPOINT: `/3Dstock/data/quantity`
**Lấy STOCK QUANTITY + CAPACITY + LOAD% của 1 location**

```python
@http.route('/3Dstock/data/quantity', type='json', auth='public')
def get_stock_count_data(self, loc_code):
    # INPUT: loc_code (e.g., "LOC001") - unique_code field
    # LOGIC:
    # 1. Find all stock.quant with location_id.unique_code = loc_code
    # 2. Sum all quantities: total_qty = sum(all_quant.quantity)
    # 3. Get max_capacity từ location
    # 4. Calculate load percentage:
    #    load% = (total_qty * 100) / max_capacity
    # 5. Special case:
    #    - If capacity = 0: return (0, -1) nếu qty > 0
    #    - If capacity = 0: return (0, 0) nếu qty = 0
    
    # RESPONSE:
    # (capacity, load%)
    #
    # EXAMPLES:
    # LOC001: capacity=1000, qty=150 → (1000, 15)   ← 15% GREEN
    # LOC002: capacity=1000, qty=600 → (1000, 60)   ← 60% YELLOW
    # LOC003: capacity=1000, qty=1200 → (1000, 120) ← 120% RED
    # LOC007: capacity=1000, qty=0 → (1000, 0)      ← 0% GRAY
    
    # USAGE: Color determination logic
    # CALLED: For EACH location, nhiều lần
```

---

#### 4️⃣ ENDPOINT: `/3Dstock/data/product`
**Lấy CHI TIẾT PRODUCTS của 1 location (dùng cho MODAL)**

```python
@http.route('/3Dstock/data/product', type='json', auth='public')
def get_stock_product_data(self, loc_code):
    # INPUT: loc_code (e.g., "LOC001")
    # LOGIC:
    # 1. Find all stock.quant with location_id.unique_code = loc_code
    # 2. Build product_list = [(product_name, qty), ...]
    # 3. Calculate:
    #    total_load = sum(all_quant.quantity)
    #    space_left = capacity - total_load
    
    # RESPONSE:
    # {
    #     "capacity": 1000,
    #     "space": 850,
    #     "product_list": [
    #         ("Product A", 150),
    #         ("Product B", 0)
    #     ]
    # }
    
    # USAGE: Display in modal when user clicks on 3D box
    # CALLED: When user clicks a location box
```

---

#### 5️⃣ ENDPOINT: `/3Dstock/data/standalone`
**Lấy dữ liệu LOCATIONS của FORM (single location context)**

```python
@http.route('/3Dstock/data/standalone', type='json', auth='public')
def get_standalone_stock_data(self, company_id, loc_id):
    # INPUT: company_id, loc_id (location record ID, không phải unique_code)
    # LOGIC:
    # 1. Find location by loc_id
    # 2. Get warehouse của location này
    # 3. Search ALL locations trong warehouse + company:
    #    - company_id = company_id
    #    - active = true
    #    - usage = 'internal'
    # 4. Convert dimensions (meter → pixel)
    # 5. Return với location.id thêm vào (index 6)
    
    # RESPONSE FORMAT:
    # {
    #     "LOC001": [0, 0, 0, 37, 30, 22, 1],
    #     "LOC002": [100, 0, 0, 37, 30, 22, 2],
    # }
    # WHERE: [pos_x, pos_y, pos_z, length_px, width_px, height_px, location_id]
    
    # DIFFERENCE FROM /3Dstock/data:
    # - Takes loc_id instead of wh_id
    # - Auto-determines warehouse from location context
    # - Includes location.id in response
    
    # USAGE: Form view 3D scene initialization
    # CALLED: When user clicks "Preview Layout" on Location form
```

---

## 🎨 FRONTEND LAYER - JavaScript & Three.js

### File: `static/src/js/listview_3d.js`

**Main workflow:**

```javascript
// STEP 1: Fetch warehouse list
await rpc('/3Dstock/warehouse', {'company_id': company_id})
  .then(data => { wh_data = data; });
// wh_data = [(1, "San Francisco"), (2, "New York")]

// STEP 2: Create THREE.Scene
scene = new THREE.Scene();
scene.background = new THREE.Color(0xdfdfdf);

// STEP 3: Setup camera + renderer
camera = new THREE.PerspectiveCamera(60, width/height, 0.5, 6000);
camera.position.set(0, 200, 300);
renderer = new THREE.WebGLRenderer({antialias: true});
renderer.setSize(window.innerWidth, window.innerHeight/1.164);

// STEP 4: Create base floor
const baseGeometry = new THREE.BoxGeometry(800, 0, 800);
const baseMesh = new THREE.Mesh(baseGeometry, baseMaterial);
scene.add(baseMesh);

// STEP 5: Fetch location dimensions
await rpc('/3Dstock/data', {'company_id': company_id, 'wh_id': wh_id})
  .then(data => { locations_data = data; });
// locations_data = {"LOC001": [0,0,0,37,30,22], "LOC002": [100,0,0,37,30,22]}

// STEP 6: FOR EACH LOCATION → Create 3D box
for (let [key, value] of Object.entries(locations_data)) {
    // key = "LOC001", value = [0, 0, 0, 37, 30, 22]
    
    // STEP 7: Fetch stock quantity
    await rpc('/3Dstock/data/quantity', {'loc_code': key})
        .then(quant_data => { loc_quant = quant_data; });
    // loc_quant = (1000, 15)  ← capacity, load%
    
    // STEP 8: DETERMINE COLOR based on load%
    if (loc_quant[0] > 0) {  // If capacity > 0
        const load% = loc_quant[1];
        
        if (load% > 100) {
            loc_color = 0xcc0000;  // 🔴 RED (Overload)
            loc_opacity = 0.8;
        } else if (load% > 50) {
            loc_color = 0xe6b800;  // 🟡 YELLOW (Almost Full)
            loc_opacity = 0.8;
        } else {
            loc_color = 0x00802b;  // 🟢 GREEN (Free Space)
            loc_opacity = 0.8;
        }
    } else {
        loc_color = 0x8c8c8c;  // ⚫ GRAY (No Product/Empty)
        loc_opacity = 0.5;
    }
    
    // STEP 9: Create 3D box geometry
    const geometry = new THREE.BoxGeometry(
        value[3],  // length
        value[5],  // height
        value[4]   // width
    );
    geometry.translate(0, value[5]/2, 0);
    
    // STEP 10: Create material + mesh
    const material = new THREE.MeshBasicMaterial({
        color: loc_color,
        transparent: true,
        opacity: loc_opacity
    });
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.set(value[0], value[1], value[2]);
    mesh.name = key;
    mesh.userData = {color: loc_color};
    
    // STEP 11: Add edges (outline)
    const edges = new THREE.EdgesGeometry(geometry);
    const line = new THREE.LineSegments(edges, 
        new THREE.LineBasicMaterial({color: 0x404040}));
    line.position.set(value[0], value[1], value[2]);
    
    // STEP 12: Add text label (location code)
    // Load font từ Three.js CDN
    // Create text geometry: key (e.g., "LOC001")
    // Position text on top of box
    
    // STEP 13: Add to scene
    scene.add(mesh);
    scene.add(line);
    scene.add(text);
    group.add(mesh);
}

// STEP 14: Setup interaction controls
controls = new THREE.OrbitControls(camera, renderer.domElement);

// STEP 15: Setup warehouse dropdown change handler
dropdown.addEventListener("change", warehouseChange);
// warehouseChange() calls start() lại với wh_id mới

// STEP 16: Setup click handler
document.addEventListener('dblclick', onPointerMove);
// Click on box → show modal with product details

// STEP 17: Render loop
animate();
// requestAnimationFrame(animate) → renderer.render(scene, camera)
```

---

### File: `static/src/js/form_3d_view.js`

**Tương tự LIST VIEW nhưng:**
- Dùng `/3Dstock/data/standalone` thay vì `/3Dstock/data`
- Không có warehouse dropdown (single location context)
- Store context vào localStorage

---

## 🎯 COLOR LOGIC (Công thức tính màu)

```javascript
if (capacity > 0) {
    load% = (quantity * 100) / capacity;
    
    if (load% > 100) {
        color = 0xcc0000;  // 🔴 RED (Overload - vượt capacity)
        opacity = 0.8;
    } else if (load% > 50) {
        color = 0xe6b800;  // 🟡 YELLOW (Almost Full - 50-100%)
        opacity = 0.8;
    } else {
        color = 0x00802b;  // 🟢 GREEN (Free Space - <50%)
        opacity = 0.8;
    }
} else {
    color = 0x8c8c8c;  // ⚫ GRAY (No capacity or empty)
    opacity = 0.5;
}
```

| Load % | Color | Hex | Status |
|--------|-------|-----|--------|
| > 100% | 🔴 RED | #cc0000 | Overload |
| 50-100% | 🟡 YELLOW | #e6b800 | Almost Full |
| < 50% | 🟢 GREEN | #00802b | Free Space |
| 0% (no qty) | ⚫ GRAY | #8c8c8c | Empty |

---

## 📊 COMPLETE DATA FLOW

```
USER ACTION: Click "Preview Layout"
    ↓
ROUTE TRIGGERED: listview_3d.js open3DView() OR form_3d_view.js Open3DView()
    ↓
RPC #1: /3Dstock/warehouse (get warehouse list)
    ↓ (Backend) stock_3d_view.py: get_warehouse_data()
    ├─ Search stock.warehouse by company_id
    └─ Return: [(wh_id, wh_name), ...]
    ↓
RPC #2: /3Dstock/data (get location dimensions - LIST VIEW)
        OR /3Dstock/data/standalone (get location dimensions - FORM VIEW)
    ↓ (Backend) stock_3d_view.py: get_stock_data() / get_standalone_stock_data()
    ├─ Search stock.location by warehouse + company
    ├─ Filter internal locations
    ├─ Exclude system locations
    ├─ Convert meter to pixel
    └─ Return: {unique_code: [pos_x, pos_y, pos_z, length_px, width_px, height_px]}
    ↓
FOR EACH LOCATION in response:
    ├─ RPC #3: /3Dstock/data/quantity (get stock quantity)
    │   ↓ (Backend)
    │   ├─ Search stock.quant by location_code
    │   ├─ Sum quantities
    │   ├─ Calculate load% = (qty * 100) / capacity
    │   └─ Return: (capacity, load%)
    │   ↓
    ├─ DETERMINE COLOR based on load%
    ├─ CREATE THREE.JS BOX with color
    ├─ POSITION box at (pos_x, pos_y, pos_z)
    ├─ SIZE box (length_px, height_px, width_px)
    ├─ ADD text label (location code)
    └─ Add to scene
    ↓
RENDER Three.js Scene
    ↓
DISPLAY 3D VISUALIZATION with controls
    ├─ Drag to rotate (OrbitControls)
    ├─ Scroll to zoom
    ├─ Click box:
    │   ├─ RPC /3Dstock/data/product
    │   ├─ Show modal with product details
    │   └─ Modal displays: capacity, space, product list
    └─ Warehouse dropdown: reload scene
```

---

## 📋 REQUIRED DATA FOR 3D TO WORK

### Location Record
```python
{
    'name': 'LOC001',
    'unique_code': 'LOC001',    # ← CRITICAL: Must match name
    'usage': 'internal',         # ← MUST BE 'internal'
    'active': True,              # ← MUST BE TRUE
    'length': 5.0,               # meter
    'width': 4.0,                # meter
    'height': 3.0,               # meter
    'pos_x': 0.0,                # pixel
    'pos_y': 0.0,                # pixel
    'pos_z': 0.0,                # pixel
    'max_capacity': 1000,        # ← MUST BE > 0 for load calculation
    'warehouse_id': 1,           # Must belong to warehouse
}
```

### Stock Quant Record
```python
{
    'location_id': 1,           # References location by ID
    'product_id': 1,            # References product
    'quantity': 150,            # Current quantity at location
}
```

---

## 🚨 DEBUGGING CHECKLIST

### ❌ Blank Screen (Màn hình trắng)

**Nguyên nhân:**
- ❌ unique_code empty hoặc không match name
- ❌ max_capacity = 0 hoặc NULL
- ❌ length/width/height = 0 (dimension sai)
- ❌ Location không active
- ❌ Location không internal type

**Fix:**
```
For each location (LOC001-LOC007):
✅ unique_code = "LOC001" (MUST match name)
✅ usage = "Internal Location"
✅ active = checked
✅ max_capacity ≥ 1000
✅ length = 5.0, width = 4.0, height = 3.0
✅ pos_x, pos_y, pos_z = filled (default 0,0,0)
✅ SAVE location
✅ Refresh page
```

### ❌ API Returns Empty

**Fix:**
- Check location.warehouse_id is correct
- Check location.company_id matches user company
- Check location không phải system location (input/output/QC/pack)

### ❌ All Boxes Gray

**Nguyên nhân:**
- Chưa tạo stock quants
- Hoặc stock quant quantity = 0

**Fix:**
- Create stock.quant records for each location
- Set quantity > 0 để test colors

### ❌ Console Errors

Check:
1. Three.js library loaded (check Network tab)
2. OrbitControls loaded
3. Font loading từ CDN success

---

## 🎬 COMPLETE TESTING WORKFLOW

```
1️⃣ CREATE WAREHOUSE
   Inventory → Warehouse → Warehouses → New
   Name: "San Francisco"
   Save

2️⃣ CREATE 7 LOCATIONS (LOC001-LOC007)
   Inventory → Warehouse → Locations → New
   
   For LOC001:
   - Name: LOC001
   - Usage: Internal Location
   - Location Code: LOC001
   - Capacity: 1000
   - Dimension: L=5.0, W=4.0, H=3.0
   - Position: X=0, Y=0, Z=0
   
   For LOC002:
   - Position: X=100, Y=0, Z=0
   
   ... (adjust X for each location)
   
   For LOC007:
   - Position: X=600, Y=0, Z=0
   
   Save all

3️⃣ CREATE 3 PRODUCTS
   Inventory → Products → Products → New
   
   Product A: Code=PA001, Tracking=By Lot
   Product B: Code=PB001, Tracking=By Lot
   Product C: Code=PC001, Tracking=By Lot
   
   Save all

4️⃣ CREATE STOCK QUANTS
   Inventory → Stock → Stock Quants → New
   
   LOC001: qty=150 (15% GREEN)
   LOC002: qty=600 (60% YELLOW)
   LOC003: qty=1200 (120% RED)
   LOC004: qty=800 (80% YELLOW)
   LOC005: qty=400 (40% GREEN)
   LOC006: qty=550 (55% YELLOW)
   LOC007: qty=0 (0% GRAY)
   
   Save all

5️⃣ VIEW 3D
   Inventory → Warehouse → Locations → List
   Click "Preview Layout" button
   
   EXPECTED RESULT:
   - 7 colored boxes in 3D space
   - LOC003: 🔴 RED (120%)
   - LOC002, LOC004, LOC006: 🟡 YELLOW (50-100%)
   - LOC001, LOC005: 🟢 GREEN (<50%)
   - LOC007: ⚫ GRAY (0%)
   
   INTERACTIONS:
   - Drag mouse: rotate view
   - Scroll: zoom in/out
   - Double-click box: show product modal
   - Select warehouse: reload scene
```

---

## 📝 KEY POINTS

✅ **unique_code MUST be unique** - used as location identifier in 3D system
✅ **max_capacity MUST > 0** - required for load% calculation
✅ **Dimensions MUST > 0** - required for box rendering
✅ **usage MUST = 'internal'** - only internal locations shown
✅ **Module manages by PRODUCT** - not by lot (total qty at location)
✅ **Color based on load% only** - no product-specific coloring
✅ **5 RPC endpoints** - warehouse, data, quantity, product, standalone

