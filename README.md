# Hybrid Document-Graph Store: Cơ Sở Tri Thức Y Tế Phân Tán

<!-- Badges -->
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-REST%20API-green.svg)](https://flask.palletsprojects.com/)

**Đề án môn học Cơ Sở Dữ Liệu Phân Tán – Học viện Công nghệ Bưu chính Viễn thông, Kho Công nghệ thông tin 2, 2025-2026**
**Sinh viên: Trần Hữu Trung – MSSV: N23DCCN200 | Giảng viên: Lê Hà Thanh**

Hệ thống lai phân tán kết hợp **Document Store** (Triệu chứng Bệnh nhân với BM25F) và **Graph Store** (Tương quan Bệnh với phân vùng METIS), dựa trên lý thuyết **Özsu & Valduriez – Principles of Distributed Database Systems**.

---

## Mục lục

1. [Hướng dẫn thiết lập - Cài đặt & Chạy hệ thống](#1-hướng-dẫn-thiết-lập--cài-đặt--chạy-hệ-thống)
2. [Tính năng chính](#2-tính-năng-chính)
3. [Cấu trúc dự án](#3-cấu-trúc-dự-án)
4. [API Endpoints](#4-api-endpoints)
5. [Hướng dẫn quay video demo (Screen Recording)](#5-hướng-dẫn-quay-video-demo-screen-recording)
6. [Xử lý sự cố](#6-xử-lý-sự-cố)

---

## 1. Hướng dẫn thiết lập – Cài đặt & Chạy hệ thống

### Phương án A: Chạy nhanh bằng trình duyệt (Không cần cài đặt)

Nếu chỉ muốn xem demo nhanh mà không cần cài Python:

1. Mở file `index.html` trong thư mục gốc của dự án bằng trình duyệt (Chrome, Firefox, Edge đều được).
2. Hệ thống sẽ tự động tạo 500 hồ sơ bệnh nhân và đồ thị tương quan bệnh ngay khi mở.
3. Giao diện gồm 3 tab: **Truy vấn**, **Đồ thị**, **Phân tích**.

> **Lưu ý:** Phiên bản `index.html` chạy độc lập trên trình duyệt, sử dụng dữ liệu được tạo sẵn và lưu trong LocalStorage. Phiên bản đầy đủ với Flask API (phương án B) hỗ trợ thêm các tính năng phân tích chi phí ghép nối và API endpoints đầy đủ hơn.

### Phương án B: Chạy với Flask API (Khuyến nghị cho demo đầy đủ)

#### Bước 1: Kiểm tra và cài đặt Python

Yêu cầu: **Python 3.9 trở lên**.

```powershell
# Kiểm tra phiên bản Python
python --version
```

Nếu chưa có Python, tải và cài đặt từ [python.org](https://www.python.org/downloads/).

#### Bước 2: Tạo môi trường ảo (khuyến nghị)

```powershell
# Tạo môi trường ảo
python -m venv venv

# Kích hoạt môi trường ảo
# Trên Windows:
.\venv\Scripts\activate

# Trên macOS/Linux:
source venv/bin/activate
```

#### Bước 3: Cài đặt các thư viện phụ thuộc

```powershell
pip install -r requirements.txt
```

#### Bước 4: Chạy server

```powershell
python run.py
```

Khi chạy thành công, terminal sẽ hiển thị:

```
Starting Hybrid Document-Graph Store API Server
URL: http://0.0.0.0:5000
```

#### Bước 5: Truy cập giao diện web

Mở trình duyệt và truy cập:

- **Trang chính (Truy vấn):** [http://localhost:5000](http://localhost:5000)
- **Trang đồ thị:** [http://localhost:5000/graph](http://localhost:5000/graph)
- **Trang phân tích:** [http://localhost:5000/analysis](http://localhost:5000/analysis)

---

## 2. Tính năng chính

### 2.1 Document Engine (Whoosh BM25F)

- Tìm kiếm toàn văn bản trên 500 hồ sơ triệu chứng bệnh nhân với thuật toán BM25F
- Lọc theo khoa (department), mức độ nghiêm trọng (severity 1-5), giới tính
- Chỉ mục đầy đủ trên các trường tìm kiếm (searchable): `chief_complaint`, `symptoms`, `medical_history`, `initial_diagnosis`, `full_text`
- Các trường lọc (filterable): `department`, `severity`, `gender`
- Thống kê chỉ mục và phân tích truy vấn chi tiết

### 2.2 Graph Engine (NetworkX + METIS)

- Đồ thị tương quan bệnh với **200 nút** và **~800 cạnh** có trọng số
- **4 loại nút:** Disease (bệnh), Symptom (triệu chứng), Medical Field (lĩnh vực y tế), Drug (thuốc)
- **10 lĩnh vực y tế:** Cardiology, Neurology, Oncology, Pulmonology, Gastroenterology, Orthopedics, Infectious_Disease, Endocrinology, Nephrology, Rheumatology
- **Phân vùng METIS** recursive bisection thành 4 phân vùng (Edge-Cut partitioning)
- 3 thuật toán duyệt: **BFS** (Breadth-First Search), **DFS** (Depth-First Search), **Dijkstra** (Đường đi ngắn nhất)
- Trực quan hóa đồ thị tương tác với D3.js, tô màu theo phân vùng và loại nút

### 2.3 Hybrid Query Engine (Động cơ truy vấn lai)

- Kết hợp điểm liên quan văn bản (BM25F) với tầm quan trọng khoảng cách đồ thị
- **Công thức chấm điểm:**

```
Combined Score = text_weight × normalize(text_score) + graph_weight × graph_importance
```

- **Trọng số khoảng cách đồ thị:**
  - Khoảng cách 0 (Nút lĩnh vực y tế) → 1.0
  - Khoảng cách 1 (1 hop) → 0.8
  - Khoảng cách 2 (2 hops) → 0.5
  - Khoảng cách 3 (3 hops) → 0.2

- **3 chiến lược ghép nối:**
  - Filter-After-Join: Ghép nối trước, lọc sau theo khoảng cách
  - Index Nested-Loop: Duyệt document theo chỉ mục, khớp với đồ thị
  - Hash Join: Sử dụng bảng băm cho kết quả đồ thị lớn

### 2.4 Phân tích chi phí ghép nối (Join Cost Analysis)

- **Chi phí quét document:** Số thao tác tra cứu chỉ mục Whoosh
- **Chi phí duyệt đồ thị:** Số nút và cạnh đã duyệt qua
- **Chi phí ghép nối:** Số tra cứu hash và khớp bản ghi
- **Chi phí truyền mạng:** Overhead truy cập cross-partition (edge-cut)
- **Tỷ lệ Edge-Cut:** Số cạnh cắt ngang phân vùng / tổng số cạnh
- So sánh chi phí giữa 3 chiến lược ghép nối bằng biểu đồ cột và biểu đồ tròn

---

## 3. Cấu trúc dự án

```
Hybrid Document-Graph Store/
├── config.yaml              # Tất cả cấu hình hệ thống
├── requirements.txt          # Các thư viện Python phụ thuộc
├── run.py                   # Điểm khởi đầu chính – chạy server
├── index.html               # Phiên bản chạy độc lập trên trình duyệt
│
├── data/
│   ├── raw/
│   │   ├── patient_symptoms.json    # 500 hồ sơ bệnh nhân (JSON)
│   │   └── disease_graph.json       # Đồ thị tương quan bệnh (JSON)
│   └── processed/
│       ├── documents_index/          # Chỉ mục Whoosh BM25F
│       ├── graph_data.gpickle       # Đồ thị NetworkX đã phân vùng
│       └── partitions.txt           # Kết quả phân vùng METIS
│
├── src/
│   ├── core/
│   │   ├── config.py        # Trình tải & quản lý cấu hình (config.yaml)
│   │   └── models.py        # Định nghĩa mô hình dữ liệu
│   │
│   ├── engines/
│   │   ├── data_generator.py    # Sinh dữ liệu tổng hợp (500 bệnh nhân, đồ thị bệnh)
│   │   ├── document_engine.py   # Động cơ tìm kiếm Whoosh BM25F
│   │   ├── graph_engine.py      # Động cơ đồ thị NetworkX + METIS partitioning
│   │   └── hybrid_engine.py     # Động cơ truy vấn lai + phân tích chi phí
│   │
│   ├── api/
│   │   └── app.py           # Flask REST API – tất cả endpoints
│   │
│   └── frontend/
│       ├── templates/
│       │   ├── index.html       # Trang Truy vấn (tab đầu tiên)
│       │   ├── graph.html       # Trang Đồ thị (trực quan hóa D3.js)
│       │   └── analysis.html    # Trang Phân tích (biểu đồ chi phí)
│       └── static/
│           ├── css/style.css
│           └── js/app.js
│
├── docs/                    # Tài liệu nộp bài
│   ├── 01_Project_Proposal.docx
│   ├── 02_Design_Document.docx
│   ├── 03_Analysis_Report.docx
│   ├── 04_Recording_Script.docx
│   └── 05_Submission_Form.docx
│
├── tests/
│   ├── __init__.py
│   └── test_models.py       # Các bài kiểm thử đơn vị
│
└── logs/                    # Log hoạt động của hệ thống
```

---

## 4. API Endpoints

### 4.1 Truy vấn lai (Hybrid Query)

```bash
POST /api/query
Content-Type: application/json

{
    "query_text": "chest pain fever",
    "target_field": "Cardiology",
    "max_graph_distance": 3,
    "text_weight": 0.5,
    "graph_weight": 0.5,
    "traversal_algorithm": "bfs"
}
```

**Phản hồi:** Danh sách bệnh nhân được chấm điểm kết hợp (text + graph), kèm chi phí ghép nối.

### 4.2 Phân tích chi phí ghép nối (Join Cost Analysis)

```bash
POST /api/analyze/join-cost
Content-Type: application/json

{
    "query_text": "headache",
    "target_field": "Neurology"
}
```

**Phản hồi:** So sánh chi phí 3 chiến lược ghép nối (Filter-After-Join, Index Nested-Loop, Hash Join) với biểu đồ chi phí.

### 4.3 Duyệt đồ thị (Graph Traversal)

```bash
POST /api/graph/traverse
Content-Type: application/json

{
    "field_name": "Cardiology",
    "max_depth": 3,
    "algorithm": "bfs"
}
```

**Phản hồi:** Các nút được duyệt, khoảng cách đến nút gốc, thông tin phân vùng, phân bố độ sâu và bao phủ phân vùng.

### 4.4 Thống kê đồ thị

```bash
GET /api/graph/statistics    # Thống kê tổng quan (số nút, cạnh, mật độ, phân bố loại nút/cạnh, centrality)
GET /api/graph/partitions    # Phân bố nút theo phân vùng METIS (số nút, cạnh nội bộ, cạnh cắt)
GET /api/graph/export        # Xuất dữ liệu đồ thị (nodes, links, partitions) dưới dạng JSON
```

### 4.5 Tìm kiếm document

```bash
GET /api/documents/search?q=fever&department=Infectious_Disease&severity=3
```

**Phản hồi:** Danh sách bệnh nhân phù hợp với truy vấn BM25F, kèm điểm liên quan.

### 4.6 Các endpoint bổ sung

```bash
GET /api/graph/distance?disease=Hypertension&field=Cardiology
# Khoảng cách đồ thị giữa một bệnh và một lĩnh vực y tế

GET /api/graph/correlation-matrix
# Ma trận tương quan bệnh-bệnh và lĩnh vực-lĩnh vực (cho trực quan hóa heatmap)

GET /api/analyze/field-coverage
# Thống kê bao phủ theo lĩnh vực y tế (số bệnh, triệu chứng, bệnh nhân mỗi lĩnh vực)

GET /api/documents/<patient_id>
# Lấy thông tin chi tiết một bệnh nhân theo patient_id

GET /api/health
# Kiểm tra trạng thái hoạt động của hệ thống

GET /api/info
# Thông tin tổng quan hệ thống (số document, thống kê đồ thị, số phân vùng)
```

---

## 5. Hướng dẫn quay video demo (Screen Recording)

### 5.1 Tổng quan kịch bản demo

Video demo dài **3-5 phút** cần thể hiện hai phần chính:

- **Phần 1 (1-2 phút):** Truy vấn lai cơ bản – tìm bệnh nhân theo triệu chứng, kết hợp với lọc khoảng cách đồ thị.
- **Phần 2 (2-3 phút):** **TRƯỜNG HỢP THẤT BẠI (Failure Case)** – trực quan hóa đồ thị, phân vùng METIS, và thao tác khi một phân vùng (tương đương "Node B") bị mất kết nối / không khả dụng.

### 5.2 Công cụ cần chuẩn bị

| Công cụ | Mục đích | Ghi chú |
|---------|---------|---------|
| **OBS Studio** (miễn phí) hoặc **Camtasia** | Quay màn hình | Thiết lập độ phân giải 1280×720 hoặc 1920×1080, 30fps |
| **Flask API** (`python run.py`) | Chạy server cục bộ | Cổng 5000 |
| **Trình duyệt** (Chrome/Edge khuyến nghị) | Giao diện web | Có thể dùng thêm tab API testing (Postman/curl) |

### 5.3 Phần 1: Demo truy vấn lai cơ bản (1-2 phút)

**Bước 1: Khởi động hệ thống** (~15 giây)

1. Mở terminal, chạy `python run.py`.
2. Chờ thông báo `Open http://localhost:5000`.
3. Mở trình duyệt tại `http://localhost:5000`.

**Bước 2: Thực hiện truy vấn BM25F** (~30 giây)

1. Tại tab **Truy vấn** (trang chính), nhập từ khóa: `fever` hoặc `chest pain`.
2. Chọn **Lĩnh vực y tế mục tiêu** (ví dụ: `Cardiology` hoặc `Infectious_Disease`).
3. Điều chỉnh thanh trượt **Text Weight = 0.7, Graph Weight = 0.3**.
4. Chọn thuật toán duyệt: `BFS`.
5. Nhấn **Tìm kiếm**.
6. **GIẢI THÍCH BẰNG LỜI:** "Hệ thống tìm kiếm 500 hồ sơ bệnh nhân bằng BM25F, sau đó ghép nối với đồ thị tương quan bệnh để tính điểm khoảng cách đồ thị. Cột 'Graph Dist' cho thấy bệnh nhân cách lĩnh vực mục tiêu bao xa trong đồ thị bệnh."

**Bước 3: So sánh chiến lược ghép nối** (~30 giây)

1. Nhấn nút **"Phân tích chi phí"** bên dưới kết quả (hoặc chuyển sang tab **Phân tích**).
2. Nhập lại từ khóa cùng lĩnh vực, nhấn **"So sánh chiến lược"**.
3. **GIẢI THÍCH BẰNG LỜI:** "Biểu đồ so sánh 3 chiến lược ghép nối: Filter-After-Join, Index Nested-Loop, và Hash Join. Mỗi chiến lược có chi phí thành phần khác nhau (document scan, graph traversal, join operation, network transfer). Điểm sáng (màu xanh) là chiến lược tối ưu cho truy vấn này."

### 5.4 Phần 2: Demo trường hợp thất bại – "Kill Node B" (2-3 phút)

> **Khái niệm nền tảng (Distributed Database Theory - Özsu & Valduriez):**
> Trong hệ thống phân tán, khi một node (phân vùng) bị ngừng hoạt động (kill/failure), hệ thống cần xử lý graceful degradation. Trong hệ thống này, mỗi phân vùng METIS tương đương với một "node" trong mô hình phân tán. Edge-Cut partitioning có ưu điểm là giảm cross-partition traffic nhưng vẫn có edge cut – nghĩa là một số truy vấn phải truy cập nhiều phân vùng.

**Bước 4: Truy cập trang đồ thị, giới thiệu cấu trúc phân vùng** (~30 giây)

1. Chuyển sang tab **Đồ thị** (`/graph`).
2. **GIẢI THÍCH BẰNG LỜI (chỉ vào màn hình):**
   - "Đồ thị tương quan bệnh gồm 200 nút và ~800 cạnh, được phân thành **4 phân vùng METIS** (Edge-Cut). Mỗi phân vùng được tô màu khác nhau: Đỏ, Xanh ngọc, Xanh dương, Xanh lá."
   - "Các nút lớn màu xanh lá là **lĩnh vực y tế** (Medical Field). Tất cả các bệnh và triệu chứng kết nối vào đây."
   - "Các cạnh màu xám giữa các phân vùng là **edge cut** – những cạnh phải đi qua nhiều phân vùng."

**Bước 5: Chạy BFS từ một lĩnh vực, thể hiện bao phủ phân vùng** (~20 giây)

1. Chọn **Lĩnh vực bắt đầu:** `Cardiology`.
2. Chọn thuật toán: `BFS`.
3. Đặt **Độ sâu tối đa:** `3`.
4. Nhấn **Chạy BFS**.
5. Quan sát các nút được tô sáng theo từng lớp, màu phân vùng hiển thị rõ.
6. **GIẢI THÍCH BẰNG LỜI:** "BFS khám phá từng lớp một. Ta thấy BFS cần truy cập nhiều phân vùng để bao phủ đồ thị. Mỗi phân vùng được truy cập khi có cạnh edge-cut đi qua."

**Bước 6: TRỌNG TÂM – Thao tác khi "Kill Node B" (1-2 phút)**

Đây là phần quan trọng nhất của demo, thể hiện sự hiểu biết về distributed database failure handling.

**6.1. Xác định Node B (một phân vùng METIS):**

1. Tại tab **Phân tích** (`/analysis`), xem mục **"Phân bố phân vùng METIS"**.
2. Xác định phân vùng nào chứa nhiều nút nhất (ví dụ: Partition 2).
3. **GIẢI THÍCH BẰNG LỜI:** "**Node B** tương ứng với **Partition 2** trong phân vùng METIS. Phân vùng này chứa N nút và M cạnh nội bộ."

**6.2. Mô phỏng thao tác Kill Node B:**

Cách 1 – Thông qua cấu hình (mô phỏng):

1. Mở file `config.yaml` trong trình soạn thảo (VS Code).
2. Tìm mục `graph_engine.partitioning`, thay đổi tạm thời `n_parts` từ `4` thành `3`.
3. Lưu file → **Kill terminal Flask** (Ctrl+C) → Khởi động lại `python run.py`.
4. **GIẢI THÍCH BẰNG LỜI:** "Khi **Node B bị kill** (Partition 2 ngừng hoạt động), hệ thống chỉ còn **3 phân vùng**. Đồ thị tự động được phân bố lại."
5. Quay lại tab **Đồ thị**, quan sát đồ thị giảm kích thước, số nút hiển thị ít hơn.
6. **GIẢI THÍCH BẰNG LỜI:** "Hệ thống tự động tái phân bố dữ liệu. Các truy vấn trả về kết quả từ 3 phân vùng còn lại. **Graceful degradation** – hệ thống không crash mà tiếp tục phục vụ với dữ liệu bị thiếu."

Cách 2 – Quan sát tác động trực tiếp qua giao diện:

1. Quay lại tab **Truy vấn**.
2. Nhập từ khóa: `stroke` (để test truy vấn có thể liên quan đến Partition 2).
3. Chọn `target_field: Neurology`.
4. Nhấn **Tìm kiếm**.
5. **GIẢI THÍCH BẰNG LỜI:** "Khi Node B down, một số cạnh edge-cut bị mất – đường đi giữa các lĩnh vực bị gián đoạn. Kết quả truy vấn vẫn trả về từ các phân vùng còn lại nhưng **graph distance** bị ảnh hưởng. Một số nút không còn trong phạm vi duyệt."

**6.3. Thể hiện chi phí tăng khi xử lý cross-partition:**

1. Chuyển sang tab **Phân tích**.
2. Nhấn **"So sánh chiến lược"** với cùng truy vấn.
3. **GIẢI THÍCH BẰNG LỜI:**
   - "Khi Node B down, chi phí **network transfer** tăng vì hệ thống phải truy cập nhiều phân vùng hơn để bù đắp dữ liệu bị mất."
   - "Tỷ lệ **edge-cut** tăng đột biến vì các cạnh trước đây nội bộ (internal) trong Partition 2 giờ trở thành edge-cut."
   - "Thuật toán **Hash Join** trở nên kém hiệu quả hơn vì bảng băm không đầy đủ."

**6.4. Khôi phục Node B (Optional, nếu còn thời gian):**

1. Khôi phục `config.yaml`: thay `n_parts` từ `3` về `4`.
2. Kill và restart Flask.
3. **GIẢI THÍCH BẰNG LỜI:** "Khi Node B được khôi phục, hệ thống tự động rebalancing. Tỷ lệ edge-cut trở về mức tối ưu. Đây là cơ chế **self-healing** trong hệ thống phân tán."

### 5.5 Lưu ý khi quay video

| Hạng mục | Yêu cầu |
|---------|---------|
| **Thời lượng** | 3-5 phút (không quá 5 phút) |
| **Độ phân giải** | Tối thiểu 1280×720, ưu tiên 1920×1080 |
| **Âm thanh** | Bật micro, nói rõ ràng từng bước thao tác và giải thích lý thuyết |
| **Tốc độ** | Thao tác vừa phải, có thời gian để người xem theo dõi |
| **Phần giải thích** | BẮT BUỘC có lời giải thích bằng miệng – không chỉ thao tác im lặng |
| **Kết thúc** | Tóm tắt ngắn gọn: "Hệ thống đã xử lý thành công truy vấn lai và graceful degradation khi Node B thất bại" |

### 5.6 Kịch bản mẫu (Script gợi ý cho phần nói)

> **Mở đầu (10s):**
> "Xin chào, tôi sẽ demo hệ thống Hybrid Document-Graph Store – một hệ thống Cơ sở dữ liệu phân tán kết hợp Document Store và Graph Store cho cơ sở tri thức y tế."

> **Phần 1 – Truy vấn lai (1 phút 30s):**
> "Đầu tiên, hệ thống khởi động với 500 hồ sơ bệnh nhân được lập chỉ mục bằng Whoosh BM25F và đồ thị tương quan bệnh 200 nút phân vùng METIS thành 4 phần... Tôi tìm kiếm 'fever' với lĩnh vực mục tiêu là Infectious Disease... Kết quả được chấm điểm kết hợp giữa độ liên quan văn bản và khoảng cách đồ thị..."

> **Phần 2 – Kill Node B (2 phút 30s):**
> "Bây giờ, tôi sẽ trình bày **trường hợp thất bại**: điều gì xảy ra khi Node B – tức Partition 2 – bị ngừng hoạt động. Theo lý thuyết Özsu & Valduriez, hệ thống phân tán cần có cơ chế graceful degradation... [thao tác kill Node B]... Như các bạn thấy, hệ thống không crash mà tiếp tục trả về kết quả từ 3 phân vùng còn lại. Chi phí cross-partition tăng, tỷ lệ edge-cut tăng – đây là hệ quả tất yếu của việc mất một phân vùng trong mô hình Edge-Cut..."

---

## 6. Xử lý sự cố

### METIS không khả dụng

Hệ thống tự động quay về **hash-based partitioning** (phân vùng ngẫu nhiên cân bằng) nếu METIS binary không được tìm thấy. Chức năng vẫn hoạt động đúng nhưng chất lượng phân vùng thấp hơn.

Để cài METIS:

```bash
# Ubuntu/Debian
sudo apt install metis

# macOS
brew install metis

# Windows: tải từ https://github.com/KarypisLab/METIS/releases
```

### Lỗi CORS khi dùng Flask

Đảm bảo Flask chạy với CORS enabled – đã được cấu hình mặc định trong `src/api/app.py`.

### Dữ liệu không load

Xóa thư mục `data/processed/` và khởi động lại server (`python run.py`) để tái tạo toàn bộ dữ liệu và chỉ mục.

### Cổng 5000 đã bị chiếm

Nếu cổng 5000 đã sử dụng, thay đổi trong `config.yaml`:

```yaml
server:
  port: 5001   # hoặc cổng khác
```

Sau đó chạy `python run.py` và truy cập `http://localhost:5001`.

---

## Giấy phép

MIT License – Tự do sử dụng cho mục đích học tập.
