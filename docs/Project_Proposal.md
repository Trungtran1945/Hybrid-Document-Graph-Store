# HỌC VIỆN CÔNG NGHỆ BƯU CHÍNH VIỄN THÔNG
## Khoa Công nghệ Thông tin 2

# ĐỀ CƯƠNG ĐỀ TÀI MÔN HỌC
## Distributed Database Project Proposal

---

## 1. Thông Tin Dự Án (Project Identity)

| Họ và tên | Trần Hữu Trung |
|---|---|
| MSSV | N23DCCN200 |
| Lớp | D23CQCN03-N |
| Môn học | Cơ sở dữ liệu phân tán |
| Giảng viên | Lê Hà Thanh |
| Mã & Loại đề tài | #140 – Hybrid Document-Graph Store |

**Tên nhóm / Team Name:** MedGraph Team

**Thành viên / Team Members:** Trần Hữu Trung (N23DCCN200)

**Tên đề tài / Project Title:** Hybrid Document-Graph Store: Xây dựng Cơ sở Tri thức Y tế Phân tán kết hợp BM25F Full-Text Search và METIS Graph Partitioning

---

## 2. Mục Tiêu & Phát Biểu Bài Toán (Objective & Problem Statement)

### Lý do thực hiện ("The Why")

Trong lĩnh vực y tế, một câu hỏi truy vấn thực tế như "Tìm tất cả bệnh nhân có triệu chứng đau ngực và liên quan đến các bệnh tim mạch" đòi hỏi phải kết hợp hai loại dữ liệu hoàn toàn khác nhau: (1) dữ liệu văn bản phi cấu trúc từ hồ sơ bệnh nhân và (2) quan hệ ngữ nghĩa phức tạp trong đồ thị tương quan bệnh. Các hệ thống đơn mô hình (chỉ document store hoặc chỉ graph database) không thể trả lời câu hỏi này một cách hiệu quả.

Đề tài này giải quyết thách thức: làm thế nào để thiết kế một hệ thống phân tán lai (hybrid) kết hợp Document Store và Graph Store, tối ưu hóa chi phí Join giữa hai engine, và đảm bảo kết quả truy vấn phản ánh cả độ liên quan ngữ nghĩa (BM25F score) lẫn khoảng cách đồ thị (graph distance)?

### Thuật toán / giao thức cốt lõi (Core Logic)

- **BM25F (Best Match 25 with Field-weighted scoring):** Thuật toán xếp hạng tài liệu đa trường, mở rộng từ BM25 chuẩn Okapi. Trong hệ thống này, MultifieldParser với OrGroup được sử dụng trên 5 trường: chief_complaint, symptoms, medical_history, initial_diagnosis, full_text với trọng số bằng nhau.

- **METIS Recursive Bisection:** Thuật toán phân vùng đồ thị đa cấp (multilevel graph partitioning) của Karypis & Kumar (1998), phân chia đồ thị bệnh tương quan thành 4 phân vùng theo chiến lược Edge-Cut, tối thiểu hóa số cạnh bị cắt ngang các phân vùng.

- **Hybrid Scoring Formula:** Kết hợp điểm BM25F và graph_importance theo công thức:
  ```
  score = w₁ × normalize(BM25F_score) + w₂ × graph_importance
  ```
  với graph_importance giảm dần theo hop distance: 0-hop=1.0, 1-hop=0.8, 2-hop=0.5, 3-hop=0.2.

---

## 3. Đặc Tả Bộ Dữ Liệu (Dataset Specification)

### Bộ dữ liệu 1: Patient_Symptoms (Document Store)

- **Nguồn (Source):** Dữ liệu tổng hợp tự sinh (synthetic data generator) – không dùng dữ liệu bệnh nhân thực vì lý do bảo mật y tế
- **Kích thước (Size):** 500 hồ sơ bệnh nhân – ~2.5 MB JSON

**Schema (Patient_Symptoms):**

| Trường (Field) | Kiểu dữ liệu | Mô tả | Lập chỉ mục |
|---|---|---|---|
| patient_id | String (ID) | Mã bệnh nhân duy nhất | Không |
| age | Integer | Tuổi bệnh nhân (18–85) | Stored |
| gender | String | Giới tính (Male/Female) | Stored |
| chief_complaint | Text | Triệu chứng chính khi nhập viện | BM25F |
| symptoms | Text | Danh sách triệu chứng mở rộng | BM25F |
| medical_history | Text | Tiền sử bệnh án | BM25F |
| current_medications | Text | Thuốc đang dùng (lưu trữ, không index BM25F) | Stored |
| initial_diagnosis | Text | Chẩn đoán bác sĩ | BM25F |
| severity | Integer (1-5) | Mức độ nghiêm trọng (1-5) | Filter |
| department | Keyword | Khoa điều trị (10 chuyên khoa) | Filter |
| admission_date | String (Date) | Ngày nhập viện | Stored |

### Bộ dữ liệu 2: Disease_Correlations (Graph Store)

- **Nguồn (Source):** Dữ liệu tổng hợp dựa trên kiến thức y học tổng quát
- **Kích thước (Size):** 200 nút (nodes), ~800 cạnh có trọng số (weighted edges) – ~0.8 MB JSON

**Schema (Disease_Correlations):**

- Node types: Disease (bệnh, ~51 nút), Symptom (triệu chứng, ~70 nút), Medical Field (lĩnh vực y tế, 10 nút), Medication (thuốc, ~40 nút).
- Edge attributes: correlation_weight (0.0–1.0), relationship_type (disease_to_symptom / disease_to_disease / symptom_to_symptom / disease_to_field / disease_to_drug).

### Chiến lược phân mảnh (Fragmentation Strategy)

- Dữ liệu bệnh nhân được phân bố theo department (10 khoa). Whoosh index hiện tại là một index tập trung duy nhất; DocumentIndexManager hỗ trợ tạo index riêng theo partition cho triển khai phân tán trong tương lai.
- **Phân mảnh đồ thị (Graph Partitioning) cho Graph Store:** METIS Edge-Cut chia đồ thị thành 4 phân vùng cân bằng. Mục tiêu: Edge-Cut Ratio (ECR) < 0.25 và Balance Factor ≤ 1.2.

---

## 4. Kiến Trúc Hệ Thống (System Architecture)

- **Số nodes mô phỏng (Nodes):** 4 phân vùng logic (METIS partitions) mô phỏng 4 site phân tán; tối thiểu 2 site active đồng thời
- **Tầng giao tiếp (Communication Layer):** HTTP/REST API qua Flask – các engine giao tiếp nội bộ qua function call (in-process); cross-partition query được log để tính Communication Cost
- **Lưu trữ (Storage):** JSON files (raw data) + Whoosh Index (inverted index on disk) + METIS partition file (partitions.txt)

### Luồng xử lý truy vấn lai:

1. **Bước 1 – Nhận request:** API Layer nhận POST /api/query với tham số query_text, target_field, traversal_algorithm, text_weight, graph_weight.
2. **Bước 2 – Document Search:** Document Engine thực hiện BM25F search trên Whoosh index, trả về top-k kết quả có điểm số.
3. **Bước 3 – Graph Traversal:** Graph Engine thực hiện BFS/DFS/Dijkstra từ target_field node, tính graph_importance cho mỗi bệnh liên quan.
4. **Bước 4 – Hybrid Join:** Hybrid Engine join hai tập kết quả theo disease name (semantic key), tính combined_score, phân tích chi phí join.
5. **Bước 5 – Trả kết quả:** Sắp xếp theo combined_score giảm dần, trả JSON về giao diện web.

---

## 5. Công Nghệ & Kế Hoạch Triển Khai (Tech Stack & Implementation Plan)

- **Ngôn ngữ lập trình (Programming Language):** Python 3.9+
- **Triển khai (Deployment):** Localhost – chạy trực tiếp bằng python run.py; hỗ trợ thêm standalone HTML (không cần cài đặt)

### Thư viện & Framework (Libraries / Frameworks):

| Thư viện / Framework | Mục đích sử dụng |
|---|---|
| Whoosh 2.7+ | BM25F full-text indexing và search engine (pure Python, không cần Java) |
| NetworkX 3.x | Graph data structure, BFS/DFS/Dijkstra traversal, centrality analysis |
| METIS (python-metis) | Multilevel graph partitioning (Edge-Cut); fallback hash partitioning nếu binary không có |
| Flask 3.x + CORS | REST API backend, routing, JSON response |
| D3.js v7 | Interactive graph visualization trên trình duyệt |
| Pandas | Phân tích chi phí join và thống kê |

---

## 6. Chỉ Số Đánh Giá & Phân Tích (Success Metrics & Analysis)

### Chỉ số định lượng (Quantitative Metrics):

| Chỉ số | Mô tả đo lường | Mục tiêu |
|---|---|---|
| Edge-Cut Ratio (ECR) | \|E_cut\| / \|E_total\| – tỉ lệ cạnh bị cắt ngang partition | ECR < 0.25 |
| Balance Factor | max(\|Pᵢ\|) / avg(\|Pⱼ\|) – độ cân bằng kích thước các partition | ≤ 1.2 |
| BM25F Precision@10 | Tỉ lệ kết quả liên quan trong top-10 với query mẫu | ≥ 0.7 |
| Join Cost (ms) | Thời gian thực thi 3 chiến lược join với cùng query | Hash Join tốt nhất khi k > 50 |
| Communication Cost | Số cross-partition edge accesses × network_latency | Tối thiểu hóa |
| Query Latency (ms) | Thời gian phản hồi end-to-end từ lúc nhận request đến trả kết quả | < 500ms với 500 docs |

### Kịch bản thất bại ("Failure Scenario") – bắt buộc thể hiện trong video demo:

- **Kịch bản 1 – METIS mất cân bằng:** "Khi số nút Medical Field tập trung vào 1-2 partition → Edge-Cut Ratio tăng vượt ngưỡng 0.25 → hệ thống log cảnh báo và hiển thị partition imbalance trong trang Analysis."
- **Kịch bản 2 – Graph distance vượt ngưỡng:** "Khi graph_distance > 3 → graph_importance tự động gán = 0.1 (fallback minimum), thay vì 0.0, để đảm bảo kết quả vẫn hữu ích dù node ở xa lĩnh vực mục tiêu."
- **Kịch bản 3 – So sánh 3 chiến lược Join:** "Filter-After-Join chậm hơn Hash Join 3–5× khi k > 50 kết quả; Index Nested-Loop tối ưu khi k < 20."
- **Kịch bản 4 – METIS binary không khả dụng:** "Hệ thống tự động fallback sang hash-based partitioning, vẫn hoạt động đúng nhưng ECR tăng lên ~0.40."

---

## 7. Các Mốc Dự Án (Project Milestones)

| Mốc | Thời gian | Nội dung công việc | Đầu ra (Deliverable) |
|---|---|---|---|
| Milestone 1 | Tuần 1–3 | Nghiên cứu lý thuyết Özsu & Valduriez; thiết kế kiến trúc hệ thống; viết đề cương; xây dựng data generator tạo 500 bệnh nhân và đồ thị 200 nút | Đề cương nộp (tuần 3); JSON dataset |
| Milestone 2 | Tuần 4–6 | Cài đặt Document Engine (Whoosh BM25F schema, indexing, search); cài đặt Graph Engine (NetworkX graph construction, METIS partitioning); tích hợp 2 engine | Document Engine + Graph Engine hoạt động độc lập |
| Milestone 3 | Tuần 7–9 | Cài đặt Hybrid Engine (3 chiến lược join, combined scoring); phát triển Flask REST API; xây dựng giao diện web (3 trang: Query, Graph, Analysis) | Hệ thống hoàn chỉnh chạy được tại localhost:5000 |
| Milestone 4 | Tuần 10–12 | Kiểm thử failure scenarios; benchmark 3 chiến lược join; hoàn thiện tài liệu (Design Doc, Analysis Report); quay video demo 3–5 phút; nộp toàn bộ | Tất cả deliverable + video demo + repository GitHub |

---

**Sinh viên thực hiện**

Trần Hữu Trung

N23DCCN200 – D23CQCN03-N
