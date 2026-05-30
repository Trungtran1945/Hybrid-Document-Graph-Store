"""
Generate PowerPoint presentation for Hybrid Document-Graph Store project defense.
v2.0 - Fixed overlapping, Vietnamese localization, added missing content + video slide.
"""
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
import os

OUTPUT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Hybrid_Document_Graph_Store_Bao_Ve.pptx")

# ── Color palette ──────────────────────────────────────────────────────────
C_PRIMARY   = RGBColor(0x1A, 0x47, 0x8A)
C_SECONDARY = RGBColor(0x2E, 0x86, 0xC1)
C_ACCENT    = RGBColor(0x17, 0xA2, 0xB8)
C_LIGHT_BG  = RGBColor(0xF0, 0xF4, 0xF8)
C_WHITE     = RGBColor(0xFF, 0xFF, 0xFF)
C_BLACK     = RGBColor(0x33, 0x33, 0x33)
C_GRAY      = RGBColor(0x66, 0x66, 0x66)
C_GREEN     = RGBColor(0x27, 0xAE, 0x60)
C_RED       = RGBColor(0xE7, 0x4C, 0x3C)
C_ORANGE    = RGBColor(0xF3, 0x9C, 0x12)
C_BORDER    = RGBColor(0xDD, 0xDD, 0xDD)

prs = Presentation()
prs.slide_width  = Inches(13.333)
prs.slide_height = Inches(7.5)
W = prs.slide_width
H = prs.slide_height


# ── Helper functions ───────────────────────────────────────────────────────
def add_bg(slide, color=C_WHITE):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_shape(slide, left, top, width, height, fill_color=None, line_color=None, shape_type=MSO_SHAPE.RECTANGLE):
    shape = slide.shapes.add_shape(shape_type, left, top, width, height)
    if fill_color:
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill_color
    else:
        shape.fill.background()
    if line_color:
        shape.line.color.rgb = line_color
        shape.line.width = Pt(1)
    else:
        shape.line.fill.background()
    return shape


def add_text_box(slide, left, top, width, height, text, font_size=18, bold=False, color=C_BLACK, align=PP_ALIGN.LEFT, font_name="Calibri"):
    txbox = slide.shapes.add_textbox(left, top, width, height)
    tf = txbox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.bold = bold
    p.font.color.rgb = color
    p.font.name = font_name
    p.alignment = align
    return txbox


def add_para(tf, text, font_size=16, bold=False, color=C_BLACK, align=PP_ALIGN.LEFT, space_before=Pt(4), space_after=Pt(4), font_name="Calibri"):
    p = tf.add_paragraph()
    p.text = text
    p.font.size = Pt(font_size)
    p.font.bold = bold
    p.font.color.rgb = color
    p.font.name = font_name
    p.alignment = align
    if space_before:
        p.space_before = space_before
    if space_after:
        p.space_after = space_after
    return p


def add_title_bar(slide, title_text, subtitle_text=None):
    add_shape(slide, 0, 0, W, Inches(1.3), fill_color=C_PRIMARY)
    add_text_box(slide, Inches(0.7), Inches(0.15), Inches(11.5), Inches(0.7),
                 title_text, font_size=30, bold=True, color=C_WHITE)
    if subtitle_text:
        add_text_box(slide, Inches(0.7), Inches(0.75), Inches(11.5), Inches(0.4),
                     subtitle_text, font_size=16, bold=False, color=RGBColor(0xBB, 0xD5, 0xF0))
    add_shape(slide, 0, Inches(1.3), W, Inches(0.06), fill_color=C_ACCENT)


def add_footer(slide, slide_num, total=15):
    add_text_box(slide, Inches(0.5), Inches(7.05), Inches(5), Inches(0.35),
                 "Hybrid Document-Graph Store | CSDL Phân Tán | PTIT 2025-2026",
                 font_size=9, color=C_GRAY)
    add_text_box(slide, Inches(11.5), Inches(7.05), Inches(1.5), Inches(0.35),
                 f"{slide_num}/{total}", font_size=9, color=C_GRAY, align=PP_ALIGN.RIGHT)


def add_bullet_card(slide, left, top, width, height, title, items, title_color=C_PRIMARY, bg_color=None):
    if bg_color:
        card = add_shape(slide, left, top, width, height, fill_color=bg_color, line_color=C_BORDER)
        card.shadow.inherit = False
    add_text_box(slide, left + Inches(0.2), top + Inches(0.1), width - Inches(0.4), Inches(0.4),
                 title, font_size=16, bold=True, color=title_color)
    txbox = add_text_box(slide, left + Inches(0.2), top + Inches(0.5), width - Inches(0.4), height - Inches(0.6),
                         "", font_size=14, color=C_BLACK)
    tf = txbox.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        if i == 0:
            tf.paragraphs[0].text = f"\u2022  {item}"
            tf.paragraphs[0].font.size = Pt(14)
            tf.paragraphs[0].font.color.rgb = C_BLACK
            tf.paragraphs[0].font.name = "Calibri"
        else:
            add_para(tf, f"\u2022  {item}", font_size=14)


def add_table(slide, left, top, width, height, headers, rows, col_widths=None):
    n_rows = len(rows) + 1
    n_cols = len(headers)
    table_shape = slide.shapes.add_table(n_rows, n_cols, left, top, width, height)
    table = table_shape.table
    if col_widths:
        for i, cw in enumerate(col_widths):
            table.columns[i].width = cw
    for j, h in enumerate(headers):
        cell = table.cell(0, j)
        cell.text = h
        for paragraph in cell.text_frame.paragraphs:
            paragraph.font.size = Pt(13)
            paragraph.font.bold = True
            paragraph.font.color.rgb = C_WHITE
            paragraph.font.name = "Calibri"
            paragraph.alignment = PP_ALIGN.CENTER
        cell.fill.solid()
        cell.fill.fore_color.rgb = C_PRIMARY
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = table.cell(i + 1, j)
            cell.text = str(val)
            for paragraph in cell.text_frame.paragraphs:
                paragraph.font.size = Pt(12)
                paragraph.font.color.rgb = C_BLACK
                paragraph.font.name = "Calibri"
                paragraph.alignment = PP_ALIGN.CENTER
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            if i % 2 == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = RGBColor(0xEE, 0xF2, 0xF7)
            else:
                cell.fill.solid()
                cell.fill.fore_color.rgb = C_WHITE
    return table


# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 1: BÌA (Cover)
# ═══════════════════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide, C_PRIMARY)

add_shape(slide, 0, Inches(2.6), W, Inches(0.08), fill_color=C_ACCENT)

add_text_box(slide, Inches(1), Inches(0.8), Inches(11), Inches(0.5),
             "HỌC VIỆN CÔNG NGHỆ BƯU CHÍNH VIỄN THÔNG", font_size=18, bold=True,
             color=RGBColor(0xBB, 0xD5, 0xF0), align=PP_ALIGN.CENTER)
add_text_box(slide, Inches(1), Inches(1.3), Inches(11), Inches(0.4),
             "Khoa Công nghệ Thông tin 2", font_size=14, color=RGBColor(0x99, 0xBB, 0xDD),
             align=PP_ALIGN.CENTER)
add_text_box(slide, Inches(1), Inches(1.9), Inches(11), Inches(0.5),
             "ĐỀ ÁN MÔN HỌC CƠ SỞ DỮ LIỆU PHÂN TÁN", font_size=16, bold=True, color=C_ACCENT,
             align=PP_ALIGN.CENTER)
add_text_box(slide, Inches(1), Inches(2.9), Inches(11), Inches(1.2),
             "Hybrid Document-Graph Store:\nXây dựng Cơ sở Tri thức Y tế Phân tán\nkết hợp BM25F và METIS Graph Partitioning",
             font_size=28, bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)
add_text_box(slide, Inches(1), Inches(4.3), Inches(11), Inches(0.4),
             "Hybrid Document-Graph Store: Distributed Medical Knowledge Base", font_size=14,
             color=RGBColor(0x99, 0xBB, 0xDD), align=PP_ALIGN.CENTER)

info_box = add_text_box(slide, Inches(3.5), Inches(5.0), Inches(6), Inches(2.0), "", font_size=14,
                        color=C_WHITE, align=PP_ALIGN.CENTER)
tf = info_box.text_frame
tf.word_wrap = True
tf.paragraphs[0].alignment = PP_ALIGN.CENTER
tf.paragraphs[0].space_after = Pt(4)
lines = [
    "Giảng viên: Lê Hà Thanh",
    "Sinh viên: Trần Hữu Trung  \u2013  MSSV: N23DCCN200",
    "Lớp: D23CQCN03-N",
    "Học kỳ: 2025-2026",
]
for i, line in enumerate(lines):
    if i == 0:
        tf.paragraphs[0].text = line
        tf.paragraphs[0].font.size = Pt(15)
        tf.paragraphs[0].font.bold = True
        tf.paragraphs[0].font.color.rgb = C_WHITE
        tf.paragraphs[0].font.name = "Calibri"
    else:
        add_para(tf, line, font_size=14, color=RGBColor(0xDD, 0xDD, 0xDD), align=PP_ALIGN.CENTER)


# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 2: GIỚI THIỆU (Introduction)
# ═══════════════════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_title_bar(slide, "Giới thiệu", "Bài toán, Mục tiêu, Phạm vi")
add_footer(slide, 2)

# Left - Problem
add_shape(slide, Inches(0.5), Inches(1.7), Inches(5.8), Inches(5.0),
          fill_color=RGBColor(0xFD, 0xED, 0xEC), line_color=C_RED)
add_text_box(slide, Inches(0.7), Inches(1.8), Inches(5.4), Inches(0.4),
             "Vấn đề", font_size=20, bold=True, color=C_RED)
problem_items = [
    'Truy vấn y tế thực tế cần kết hợp văn bản phi cấu trúc (hồ sơ bệnh nhân) với quan hệ ngữ nghĩa (đồ thị tương quan bệnh)',
    'Hệ thống đơn mô hình (Document hoặc Graph) không thể trả lời hiệu quả câu hỏi lai',
    'Cần thiết kế hệ thống phân tán kết hợp, tối ưu chi phí Join giữa 2 engine',
    'Phải xử lý được trường hợp thất bại (node failure) trong môi trường phân tán',
]
txbox = add_text_box(slide, Inches(0.7), Inches(2.3), Inches(5.4), Inches(4.0), "", font_size=14, color=C_BLACK)
tf = txbox.text_frame; tf.word_wrap = True
for i, item in enumerate(problem_items):
    p = tf.paragraphs[0] if i == 0 else add_para(tf, f"\u2022  {item}", font_size=14, space_after=Pt(6))
    if i == 0:
        p.text = f"\u2022  {item}"; p.font.size = Pt(14); p.font.color.rgb = C_BLACK; p.font.name = "Calibri"; p.space_after = Pt(6)

# Right - Objective
add_shape(slide, Inches(6.8), Inches(1.7), Inches(5.9), Inches(5.0),
          fill_color=RGBColor(0xE8, 0xF5, 0xE9), line_color=C_GREEN)
add_text_box(slide, Inches(7.0), Inches(1.8), Inches(5.5), Inches(0.4),
             "Mục tiêu", font_size=20, bold=True, color=C_GREEN)
obj_items = [
    'Xây dựng Hybrid Document-Graph Store cho tri thức y tế',
    'Document Engine: tìm kiếm toàn văn BM25F (Whoosh)',
    'Graph Engine: duyệt đồ thị + phân vùng METIS Edge-Cut (NetworkX)',
    'Hybrid Engine: chấm điểm kết hợp + 3 chiến lược Join',
    'Phân tích chi phí Join & kịch bản graceful degradation',
]
txbox = add_text_box(slide, Inches(7.0), Inches(2.3), Inches(5.5), Inches(4.0), "", font_size=14, color=C_BLACK)
tf = txbox.text_frame; tf.word_wrap = True
for i, item in enumerate(obj_items):
    p = tf.paragraphs[0] if i == 0 else add_para(tf, f"\u2022  {item}", font_size=14, space_after=Pt(6))
    if i == 0:
        p.text = f"\u2022  {item}"; p.font.size = Pt(14); p.font.color.rgb = C_BLACK; p.font.name = "Calibri"; p.space_after = Pt(6)


# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 3: CƠ SỞ LÝ THUYẾT (Theory)
# ═══════════════════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_title_bar(slide, "Cơ sở Lý thuyết", "Özsu & Valduriez  \u2013  Principles of Distributed Database Systems")
add_footer(slide, 3)

cols_data = [
    (Inches(0.4), "BM25F (Robertson & Zaragoza, 2009)", [
        "Xếp hạng tài liệu đa trường (5 trường văn bản y tế)",
        "Mở rộng từ BM25 Okapi chuẩn",
        "k\u2081=1.2 (bão hòa TF), b=0.75 (chuẩn hóa độ dài)",
        "MultifieldParser + OrGroup cho token matching",
        "Hiệu quả hơn TF-IDF nhờ field-weight và saturation",
    ]),
    (Inches(4.5), "METIS (Karypis & Kumar, 1998)", [
        "Phân vùng đồ thị đa cấp (Multilevel Graph Partitioning)",
        "Recursive Bisection: 3 bước Coarsening \u2192 Partition \u2192 Refinement",
        "Edge-Cut partitioning: tối thiểu hóa cạnh cắt ngang phân vùng",
        "Heavy Edge Matching + Kernighan-Lin Refinement",
        "Phù hợp đồ thị thưa (density ~0.04)",
    ]),
    (Inches(8.6), "Hybrid Scoring Formula", [
        "score = w\u2081 \u00D7 norm(BM25F) + w\u2082 \u00D7 graph_importance",
        "Trọng số khoảng cách (hop distance):",
        "  0-hop (cùng lĩnh vực) \u2192 1.0",
        "  1-hop \u2192 0.8  |  2-hop \u2192 0.5",
        "  3-hop \u2192 0.2  |  ngoài đồ thị \u2192 0.1",
        "Mặc định: w\u2081 = w\u2082 = 0.5 (cân bằng)",
    ]),
]
for left, title, items in cols_data:
    add_bullet_card(slide, left, Inches(1.6), Inches(3.9), Inches(5.2), title, items,
                    title_color=C_PRIMARY, bg_color=C_LIGHT_BG)


# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 4: KIẾN TRÚC HỆ THỐNG (Architecture) - FIXED OVERLAP
# ═══════════════════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_title_bar(slide, "Kiến trúc Hệ thống", "Kiến trúc 4 tầng (4-Tier Architecture)")
add_footer(slide, 4)

# Use tighter spacing to avoid overlap: card height=1.0, spacing=1.15
layers = [
    ("Tầng 4: User Interface Layer", "Flask Templates + D3.js + Bootstrap 5", RGBColor(0x2E, 0x86, 0xC1)),
    ("Tầng 3: API Layer", "Flask REST Endpoints | CORS", RGBColor(0x17, 0xA2, 0xB8)),
    ("Tầng 2: Engine Layer", "Document Engine (Whoosh) + Graph Engine (NetworkX) + Hybrid Engine", RGBColor(0x1A, 0x47, 0x8A)),
    ("Tầng 1: Data Layer", "JSON files + Whoosh Index + METIS partitions (.gpickle, partitions.txt)", RGBColor(0x27, 0xAE, 0x60)),
]

for i, (title, desc, color) in enumerate(layers):
    y = Inches(1.6) + Inches(i * 1.15)
    add_shape(slide, Inches(1.5), y, Inches(10.3), Inches(0.95), fill_color=color)
    add_text_box(slide, Inches(1.8), y + Inches(0.08), Inches(9.8), Inches(0.35), title,
                 font_size=17, bold=True, color=C_WHITE)
    add_text_box(slide, Inches(1.8), y + Inches(0.48), Inches(9.8), Inches(0.35), desc,
                 font_size=13, color=RGBColor(0xDD, 0xEE, 0xFF))

# Side labels - adjusted positions to avoid overlap
add_text_box(slide, Inches(0.2), Inches(2.5), Inches(1.2), Inches(1.5),
             "Trình\nduyệt\n(Client)", font_size=11, bold=True, color=C_PRIMARY, align=PP_ALIGN.CENTER)
add_text_box(slide, Inches(12), Inches(3.7), Inches(1.2), Inches(1.5),
             "Dữ liệu\n(Disk)", font_size=11, bold=True, color=C_GREEN, align=PP_ALIGN.CENTER)

# Flow annotation at bottom - moved down to avoid overlap (bottom card ends at y=6.2)
add_shape(slide, Inches(0.5), Inches(6.3), Inches(12.3), Inches(0.7),
          fill_color=RGBColor(0xFD, 0xF2, 0xE9), line_color=C_ORANGE)
add_text_box(slide, Inches(0.7), Inches(6.35), Inches(12), Inches(0.5),
             "Luồng: POST /api/query \u2192 Document Search (BM25F) \u2192 Graph Traversal (BFS/DFS) \u2192 Hybrid Join & Scoring \u2192 JSON Response",
             font_size=13, color=C_BLACK, align=PP_ALIGN.CENTER)


# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 5: CÔNG NGHỆ & DỮ LIỆU (Tech Stack + Dataset)
# ═══════════════════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_title_bar(slide, "Công nghệ & Dữ liệu", "Tech Stack | 500 hồ sơ bệnh nhân, 200 nút, ~800 cạnh")
add_footer(slide, 5)

headers = ["Công nghệ", "Phiên bản", "Mục đích"]
rows = [
    ["Python", "3.9+", "Ngôn ngữ lập trình chính"],
    ["Flask", "3.0.3", "REST API + CORS"],
    ["Whoosh", "2.7.4", "BM25F full-text search"],
    ["NetworkX", "3.3", "Đồ thị & traversal algorithms"],
    ["METIS", "0.2a5", "Edge-Cut graph partitioning"],
    ["NumPy / Numba", "1.26.4 / 0.59.1", "Tính toán khoa học + JIT"],
    ["Pandas", "2.2.2", "Phân tích chi phí Join"],
    ["Faker", "25.2.0", "Sinh dữ liệu tổng hợp"],
    ["D3.js / Chart.js", "v7 / 4.4", "Visualization đồ thị & biểu đồ"],
    ["Bootstrap 5", "5.3.3", "Giao diện Dark Theme"],
]
tbl_left = Inches(0.8)
tbl_width = Inches(7.5)
add_table(slide, tbl_left, Inches(1.7), tbl_width, Inches(5.2), headers, rows,
          col_widths=[Inches(2.2), Inches(1.5), Inches(3.8)])

# Right side - Dataset summary
add_text_box(slide, Inches(8.8), Inches(1.7), Inches(4.0), Inches(0.4),
             "Bộ dữ liệu", font_size=18, bold=True, color=C_PRIMARY)
ds_items = [
    "500 hồ sơ bệnh nhân tổng hợp",
    "18-85 tuổi, 3 giới tính",
    "Mức độ: 1 (5%) \u2192 5 (15%)",
    "~200 nút đồ thị (bệnh, triệu chứng, ...)",
    "~800 cạnh có trọng số (0.0-1.0)",
    "10 lĩnh vực y tế (Cardiology, ...)",
    "4 phân vùng METIS (Edge-Cut)",
    "51 bệnh, 70 triệu chứng, 40 thuốc",
]
txbox = add_text_box(slide, Inches(8.8), Inches(2.2), Inches(4.0), Inches(4.5), "", font_size=13, color=C_BLACK)
tf = txbox.text_frame; tf.word_wrap = True
for i, item in enumerate(ds_items):
    if i == 0:
        tf.paragraphs[0].text = f"\u2022  {item}"; tf.paragraphs[0].font.size = Pt(13)
        tf.paragraphs[0].font.color.rgb = C_BLACK; tf.paragraphs[0].font.name = "Calibri"; tf.paragraphs[0].space_after = Pt(4)
    else:
        add_para(tf, f"\u2022  {item}", font_size=13, space_after=Pt(4))


# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 6: DOCUMENT ENGINE
# ═══════════════════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_title_bar(slide, "Document Engine", "Whoosh BM25F  |  Tìm kiếm toàn văn trên 500 hồ sơ bệnh nhân")
add_footer(slide, 6)

add_text_box(slide, Inches(0.5), Inches(1.6), Inches(6), Inches(0.4),
             "Schema BM25F (5 trường searchable, boost=1.0)", font_size=16, bold=True, color=C_PRIMARY)
doc_headers = ["Trường", "Kiểu", "Ghi chú"]
doc_rows = [
    ["chief_complaint", "TEXT", "Triệu chứng chính"],
    ["symptoms", "TEXT", "Danh sách triệu chứng"],
    ["medical_history", "TEXT", "Tiền sử bệnh án"],
    ["initial_diagnosis", "TEXT", "Chẩn đoán bác sĩ"],
    ["full_text", "TEXT", "Toàn văn (tổng hợp 4 trường)"],
    ["department", "KEYWORD", "Lọc: 10 chuyên khoa"],
    ["severity", "NUMERIC", "Lọc: mức độ 1-5"],
    ["gender", "KEYWORD", "Lọc: Nam/Nữ"],
]
add_table(slide, Inches(0.5), Inches(2.1), Inches(6.0), Inches(3.8), doc_headers, doc_rows,
          col_widths=[Inches(2.2), Inches(1.2), Inches(2.6)])

features = [
    "Thuật toán BM25F (k\u2081=1.2, b=0.75) với saturation effect",
    "MultifieldParser + OrGroup cho tìm kiếm đa trường",
    "StemmingAnalyzer cho văn bản y tế tiếng Anh",
    "Lọc theo khoa, mức độ nghiêm trọng, giới tính",
    "Whoosh: pure Python, không cần cài Elasticsearch",
    "Chỉ mục bền vững (persistent) + thống kê truy vấn",
    "DocumentIndexManager hỗ trợ chỉ mục phân tán sau này",
]
add_bullet_card(slide, Inches(6.8), Inches(1.6), Inches(5.8), Inches(5.2), "Đặc điểm", features,
                title_color=C_SECONDARY, bg_color=C_LIGHT_BG)


# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 7: GRAPH ENGINE (NetworkX + 3 Traversal Algorithms)
# ═══════════════════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_title_bar(slide, "Graph Engine & Duyệt đồ thị", "NetworkX  |  200 nút, ~800 cạnh, 3 thuật toán duyệt")
add_footer(slide, 7)

add_text_box(slide, Inches(0.5), Inches(1.6), Inches(5.5), Inches(0.4),
             "Cấu trúc đồ thị", font_size=16, bold=True, color=C_PRIMARY)
g_headers = ["Loại nút", "Số lượng"]
g_rows = [
    ["Lĩnh vực y tế (Medical Field)", "10 (Cardiology, Neurology, ...)"],
    ["Bệnh (Disease)", "~51"],
    ["Triệu chứng (Symptom)", "~70"],
    ["Thuốc (Drug)", "~40"],
    ["Tổng", "~200"],
]
add_table(slide, Inches(0.5), Inches(2.1), Inches(5.5), Inches(2.6), g_headers, g_rows,
          col_widths=[Inches(2.8), Inches(2.7)])
add_text_box(slide, Inches(0.5), Inches(4.9), Inches(5.5), Inches(0.3),
             "Loại cạnh: disease_to_symptom, disease_to_disease, symptom_to_symptom, disease_to_field, disease_to_drug",
             font_size=11, color=C_GRAY)

# Right - Traversal algorithms
add_text_box(slide, Inches(6.5), Inches(1.6), Inches(6), Inches(0.4),
             "3 thuật toán duyệt đồ thị", font_size=16, bold=True, color=C_PRIMARY)
algo_headers = ["Thuật toán", "Độ phức tạp", "Kết quả", "Dùng khi"]
algo_rows = [
    ["BFS (mặc định)", "O(V+E)", "Đường đi ngắn (theo hop)", "Cần hop distance, đồ thị thưa"],
    ["DFS", "O(V+E)", "Duyệt sâu toàn bộ", "Khám phá subgraph đầy đủ"],
    ["Dijkstra", "O((V+E)logV)", "Đường đi ngắn (có trọng số)", "Cạnh correlation weight"],
]
add_table(slide, Inches(6.5), Inches(2.1), Inches(6.3), Inches(2.2), algo_headers, algo_rows,
          col_widths=[Inches(1.8), Inches(1.5), Inches(2.0), Inches(4.5)])

# Right bottom - traversal features
trav_features = [
    "BFS mặc định: đảm bảo hop count chính xác nhất",
    "Hỗ trợ lọc theo loại nút khi duyệt",
    "Đo lường depth distribution và partition coverage",
    "Tính graph_importance từ khoảng cách đến lĩnh vực mục tiêu",
]
add_bullet_card(slide, Inches(6.5), Inches(4.6), Inches(6.3), Inches(2.2), "Tính năng duyệt", trav_features,
                title_color=C_SECONDARY, bg_color=C_LIGHT_BG)


# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 8: METIS PARTITIONING (Edge-Cut vs Vertex-Cut)
# ═══════════════════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_title_bar(slide, "Phân vùng METIS", "Edge-Cut vs Vertex-Cut  |  Recursive Bisection  |  4 phân vùng")
add_footer(slide, 8)

# Left - Edge-Cut vs Vertex-Cut table
add_text_box(slide, Inches(0.5), Inches(1.6), Inches(6.5), Inches(0.4),
             "So sánh Edge-Cut vs Vertex-Cut", font_size=16, bold=True, color=C_PRIMARY)
ev_headers = ["Tiêu chí", "Edge-Cut (Lựa chọn)", "Vertex-Cut"]
ev_rows = [
    ["Định nghĩa", "Mỗi nút thuộc 1 partition", "Mỗi cạnh thuộc 1 partition"],
    ["Chi phí", "Chỉ trả phí cut edges", "Phải replicate vertex metadata"],
    ["Phù hợp", "Đồ thị thưa (~0.04 density)", "Đồ thị dày (social graph)"],
    ["Đồ thị y tế", "Phù hợp (ECR < 0.25 mục tiêu)", "Không tối ưu"],
    ["Cài đặt", "gpmetis trực tiếp", "Cần tiền xử lý phức tạp"],
]
add_table(slide, Inches(0.5), Inches(2.1), Inches(6.5), Inches(2.8), ev_headers, ev_rows,
          col_widths=[Inches(1.5), Inches(2.5), Inches(2.5)])

# Left bottom - 3-step bisection
add_text_box(slide, Inches(0.5), Inches(5.1), Inches(6.5), Inches(0.3),
             "Recursive Bisection: 3 bước", font_size=15, bold=True, color=C_PRIMARY)
bisection_steps = [
    "Bước 1 - Coarsening: Heavy Edge Matching giảm G \u2192 G' (< 100 nút)",
    "Bước 2 - Initial Partitioning: Greedy Graph Growing chia G' thành k=4",
    "Bước 3 - Uncoarsening & Refinement: Kernighan-Lin tối thiểu hóa edge-cut",
]
txbox = add_text_box(slide, Inches(0.5), Inches(5.45), Inches(6.5), Inches(1.5), "", font_size=12, color=C_BLACK)
tf = txbox.text_frame; tf.word_wrap = True
for i, step in enumerate(bisection_steps):
    if i == 0:
        tf.paragraphs[0].text = f"{i+1}. {step}"; tf.paragraphs[0].font.size = Pt(12)
        tf.paragraphs[0].font.color.rgb = C_BLACK; tf.paragraphs[0].font.name = "Calibri"; tf.paragraphs[0].space_after = Pt(3)
    else:
        add_para(tf, f"{i+1}. {step}", font_size=12, space_after=Pt(3))

# Right - Quality metrics
add_text_box(slide, Inches(7.5), Inches(1.6), Inches(5.5), Inches(0.4),
             "Chỉ số chất lượng phân vùng", font_size=16, bold=True, color=C_PRIMARY)

metrics_items = [
    "Edge-Cut Ratio (ECR) = |E_cut| / |E_total|",
    "  Mục tiêu: ECR < 0.25",
    "Balance Factor = max(|Pi|) / avg(|Pj|)",
    "  Mục tiêu: Balance Factor \u2264 1.2",
    "Intra-Partition Density > 0.3",
    "",
    "Thông tin mỗi phân vùng:",
    "  - Số nút, số cạnh nội bộ, số cạnh cắt",
    "  - Edge-Cut Ratio toàn cục",
]
txbox = add_text_box(slide, Inches(7.5), Inches(2.1), Inches(5.5), Inches(4.0), "", font_size=13, color=C_BLACK)
tf = txbox.text_frame; tf.word_wrap = True
for i, item in enumerate(metrics_items):
    if i == 0:
        tf.paragraphs[0].text = item; tf.paragraphs[0].font.size = Pt(13)
        tf.paragraphs[0].font.color.rgb = C_BLACK; tf.paragraphs[0].font.name = "Calibri"; tf.paragraphs[0].space_after = Pt(2)
    else:
        add_para(tf, item, font_size=13, space_after=Pt(2))

# Importance box
add_shape(slide, Inches(7.5), Inches(5.3), Inches(5.3), Inches(1.0),
          fill_color=RGBColor(0xFD, 0xF2, 0xE9), line_color=C_ORANGE)
add_text_box(slide, Inches(7.7), Inches(5.35), Inches(5.0), Inches(0.9),
             "Mô phỏng 4 nút phân tán (distributed nodes).\nFallback hash-based partitioning khi METIS không khả dụng (ECR ~0.40).",
             font_size=12, color=C_BLACK)


# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 9: HYBRID QUERY ENGINE (Pipeline + Formula)
# ═══════════════════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_title_bar(slide, "Hybrid Query Engine", "Quy trình 4 bước & Công thức chấm điểm kết hợp")
add_footer(slide, 9)

# Pipeline
pipe_steps = [
    ("Bước 1\nNhận request", "query_text\ntarget_field\nweights"),
    ("Bước 2\nDocument Search", "BM25F trên\nWhoosh index\nTop-k kết quả"),
    ("Bước 3\nGraph Traversal", "BFS/DFS từ\ntarget_field\nmax_depth=3"),
    ("Bước 4\nHybrid Join", "Join theo\ntên bệnh\nCombined score"),
]
for i, (title, desc) in enumerate(pipe_steps):
    x = Inches(0.5) + Inches(i * 3.2)
    add_shape(slide, x, Inches(1.7), Inches(2.8), Inches(1.8), fill_color=C_PRIMARY)
    add_text_box(slide, x + Inches(0.1), Inches(1.75), Inches(2.6), Inches(0.8), title,
                 font_size=15, bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)
    add_text_box(slide, x + Inches(0.1), Inches(2.5), Inches(2.6), Inches(0.8), desc,
                 font_size=12, color=RGBColor(0xCC, 0xDD, 0xEE), align=PP_ALIGN.CENTER)
    if i < 3:
        add_text_box(slide, x + Inches(2.8), Inches(2.3), Inches(0.4), Inches(0.4), "\u25B6",
                     font_size=20, color=C_ACCENT, align=PP_ALIGN.CENTER)

# Formula box
add_shape(slide, Inches(0.5), Inches(3.9), Inches(12.3), Inches(1.4),
          fill_color=RGBColor(0xFD, 0xF2, 0xE9), line_color=C_ORANGE)
add_text_box(slide, Inches(0.7), Inches(3.95), Inches(12), Inches(0.35),
             "Công thức chấm điểm kết hợp", font_size=16, bold=True, color=C_PRIMARY)
add_text_box(slide, Inches(0.7), Inches(4.35), Inches(12), Inches(0.35),
             "Combined Score = text_weight \u00D7 normalize(BM25F_score) + graph_weight \u00D7 graph_importance",
             font_size=16, bold=True, color=C_ACCENT, align=PP_ALIGN.CENTER)
add_text_box(slide, Inches(0.7), Inches(4.75), Inches(12), Inches(0.35),
             "Trọng số: 0-hop \u2192 1.0  |  1-hop \u2192 0.8  |  2-hop \u2192 0.5  |  3-hop \u2192 0.2  |  ngoài đồ thị \u2192 0.1  |  mặc định: w\u2081=w\u2082=0.5",
             font_size=13, color=C_BLACK, align=PP_ALIGN.CENTER)

# Join strategy & traversal summary
add_shape(slide, Inches(0.5), Inches(5.6), Inches(5.8), Inches(1.3),
          fill_color=C_LIGHT_BG, line_color=C_BORDER)
add_text_box(slide, Inches(0.7), Inches(5.65), Inches(5.4), Inches(1.2),
             "3 chiến lược Join: Filter-After-Join (N\u00D7G), Index Nested-Loop (k\u00D7logG), Hash Join (G+k)\n"
             "3 thuật toán duyệt: BFS (mặc định), DFS, Dijkstra\n"
             "Khóa Join: tên bệnh (disease name) \u2013 khóa ngữ nghĩa xuyên suốt 2 engine",
             font_size=13, color=C_BLACK)

add_shape(slide, Inches(6.8), Inches(5.6), Inches(6.0), Inches(1.3),
          fill_color=C_LIGHT_BG, line_color=C_BORDER)
add_text_box(slide, Inches(7.0), Inches(5.65), Inches(5.6), Inches(1.2),
             "Điểm mạnh: Kết hợp độ liên quan ngữ nghĩa (BM25F score)\n"
             "với tầm quan trọng khoảng cách đồ thị (graph distance)\n"
             "Lọc theo khoa, mức độ nghiêm trọng, giới tính",
             font_size=13, color=C_BLACK)


# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 10: JOIN COST ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_title_bar(slide, "Phân tích Chi phí Ghép nối (Join Cost)", "So sánh 3 chiến lược & Mô hình chi phí")
add_footer(slide, 10)

join_headers = ["Chiến lược", "Độ phức tạp", "Chi phí I/O", "Chi phí CPU", "Chi phí Mạng", "Dùng khi"]
join_rows = [
    ["Filter-After-Join", "O(N\u00D7G)", "Cao (full scan)", "Thấp", "Thấp", "N < 50, query mơ hồ"],
    ["Index Nested-Loop", "O(k\u00D7logG)", "Trung bình", "Trung bình", "Trung bình", "k = 20-50, G lớn"],
    ["Hash Join (tối ưu)", "O(G + k)", "Thấp (build hash)", "Cao (hash build)", "Thấp", "k > 50, cả 2 lớn"],
]
add_table(slide, Inches(0.5), Inches(1.7), Inches(12.3), Inches(2.0), join_headers, join_rows,
          col_widths=[Inches(2.2), Inches(1.5), Inches(2.0), Inches(2.0), Inches(2.0), Inches(2.6)])

add_text_box(slide, Inches(0.5), Inches(3.9), Inches(12.3), Inches(0.4),
             "Mô hình chi phí 3 thành phần (Özsu & Valduriez, 2020)", font_size=16, bold=True, color=C_PRIMARY)

cost_items = [
    "Chi phí I/O = N_docs \u00D7 t_seek + k \u00D7 t_transfer = 500 \u00D7 0.1ms + k \u00D7 0.01ms",
    "Chi phí CPU = (n_terms \u00D7 n_docs) \u00D7 0.001ms + (V_visited + E_visited) \u00D7 0.001ms",
    "Chi phí mạng = |E_cut| \u00D7 latency = cut_edges \u00D7 1ms (local network)",
    "",
    "Cost Tier (phân loại chi phí): LOW < 100 ops  |  MEDIUM < 1000 ops  |  HIGH \u2265 1000 ops",
    "Edge-Cut Ratio (ECR) trong cost: network_cost = partition_access \u00D7 50.0 \u00D7 ECR",
]
txbox = add_text_box(slide, Inches(0.5), Inches(4.3), Inches(12.3), Inches(2.8), "", font_size=13, color=C_BLACK)
tf = txbox.text_frame; tf.word_wrap = True
for i, item in enumerate(cost_items):
    if i == 0:
        tf.paragraphs[0].text = f"\u2022  {item}"; tf.paragraphs[0].font.size = Pt(13)
        tf.paragraphs[0].font.color.rgb = C_BLACK; tf.paragraphs[0].font.name = "Consolas"; tf.paragraphs[0].space_after = Pt(3)
    else:
        add_para(tf, f"\u2022  {item}", font_size=13, font_name="Consolas", space_after=Pt(3))


# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 11: KỊCH BẢN LỖI (Failure Scenarios) - EXPANDED
# ═══════════════════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_title_bar(slide, "Kịch bản Thất bại (Failure Scenarios)", "Graceful Degradation trong Hệ thống Phân tán")
add_footer(slide, 11)

scenarios = [
    ("Kịch bản 1: METIS mất cân bằng",
     "Khi Medical Field tập trung vào 1-2 partition \u2192 ECR t\u0103ng > 0.25.\n"
     "Hệ thống log cảnh báo + hiển thị partition imbalance trong Analysis page.\n"
     "Khắc phục: tái cấu hình phân vùng hoặc fallback hash partitioning.",
     C_RED),
    ("Kịch bản 2: Kill Node B (Partition Down)",
     "Giả lập mất 1 partition METIS: thay đổi n_parts t\u1EEB 4 \u2192 3 trong config.yaml.\n"
     "Hệ thống t\u1EF1 động rebalance, phục vụ t\u1EEB 3 partitions còn l\u1EA1i (graceful degradation).\n"
     "Tác động: network cost t\u0103ng (internal edges tr\u1EDF thành cut edges), ECR t\u0103ng.\n"
     "Khi khôi phục: t\u1EF1 động rebalancing v\u1EC1 tr\u1EA1ng thái t\u1ED1i ưu (self-healing).",
     C_ORANGE),
    ("Kịch bản 3: METIS binary không khả dụng",
     "Tự động fallback sang hash-based partitioning (degree-based stratified).\n"
     "Hệ thống vẫn hoạt động đúng chức năng, không crash.\n"
     "Tác động: ECR tăng từ < 0.25 lên ~0.40, chất lượng phân vùng giảm.",
     C_SECONDARY),
    ("Kịch bản 4: Graph distance vượt ngưỡng",
     "Khi graph_distance > 3 hops, graph_importance tự động = 0.1 (fallback).\n"
     "Đảm bảo node ở xa lĩnh vực mục tiêu vẫn có điểm số dương.\n"
     "Kết quả truy vấn vẫn hữu ích dù không nằm trong vùng lân cận.",
     C_GREEN),
]

for i, (title, desc, color) in enumerate(scenarios):
    y = Inches(1.55) + Inches(i * 1.4)
    add_shape(slide, Inches(0.4), y, Inches(0.08), Inches(1.2), fill_color=color)
    add_shape(slide, Inches(0.55), y, Inches(12.2), Inches(1.2), fill_color=C_LIGHT_BG, line_color=C_BORDER)
    add_text_box(slide, Inches(0.8), y + Inches(0.05), Inches(11.8), Inches(0.3), title,
                 font_size=16, bold=True, color=color)
    add_text_box(slide, Inches(0.8), y + Inches(0.35), Inches(11.8), Inches(0.8), desc,
                 font_size=12, color=C_BLACK)


# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 12: DEMO VIDEO - TRỐNG (dành cho bạn tự chèn)
# ═══════════════════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_title_bar(slide, "Demo Video: Kill Node B & Graceful Degradation",
              "Quay video mô phỏng trường hợp thất bại trong hệ thống phân tán")
add_footer(slide, 12)

# Video placeholder
add_shape(slide, Inches(2.5), Inches(2.0), Inches(8.3), Inches(4.5),
          fill_color=RGBColor(0x22, 0x22, 0x22), line_color=C_ACCENT)
add_text_box(slide, Inches(3.5), Inches(3.2), Inches(6.3), Inches(0.5),
             "\u25B6  CHÈN VIDEO DEMO TẠI ĐÂY", font_size=24, bold=True, color=C_ACCENT, align=PP_ALIGN.CENTER)
add_text_box(slide, Inches(3.5), Inches(3.8), Inches(6.3), Inches(0.8),
             "Kịch bản Kill Node B: mất Partition 2, graceful degradation, phục hồi\n"
             "Thời lượng: 3-5 phút  |  Độ phân giải: 1280\u00D7720 trở lên",
             font_size=14, color=RGBColor(0x99, 0x99, 0x99), align=PP_ALIGN.CENTER)


# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 13: ĐÁNH GIÁ THEO TIÊU CHÍ ÖZSU & VALDURIEZ
# ═══════════════════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_title_bar(slide, "Đánh giá theo Tiêu chí Özsu & Valduriez", "7 tiêu chí cho Hệ quản trị CSDL Phân tán (DDBMS)")
add_footer(slide, 13)

eval_headers = ["#", "Tiêu chí", "Triển khai trong đề tài", "Đánh giá"]
eval_rows = [
    ["1", "Distribution Transparency", "/api/query ẩn hoàn toàn partition logic khỏi người dùng", "\u2705 Đạt"],
    ["2", "Replication Transparency", "Fallback METIS \u2192 hash partitioning đảm bảo availability", "\u26A0 Một phần"],
    ["3", "Fragmentation Transparency", "METIS partitions hoàn toàn trong suốt với người dùng", "\u2705 Đạt"],
    ["4", "Design Autonomy", "Document Engine và Graph Engine có schema độc lập", "\u2705 Đạt"],
    ["5", "Query Optimization", "3 chiến lược Join + phân tích chi phí (Hash Join tối ưu)", "\u2705 Đạt"],
    ["6", "Transaction Management", "Read-only queries (trong scope đề tài)", "\u2753 N/A"],
    ["7", "Performance & Scalability", "Whoosh O(logN) + METIS giảm traversal cost", "\u2705 Đạt"],
]
add_table(slide, Inches(0.5), Inches(1.7), Inches(12.3), Inches(4.0), eval_headers, eval_rows,
          col_widths=[Inches(0.5), Inches(2.8), Inches(6.5), Inches(2.5)])

add_text_box(slide, Inches(0.5), Inches(5.9), Inches(12.3), Inches(0.8),
             "Dựa trên 12 quy tắc của Date (1987) và 7 tiêu chí Özsu & Valduriez (2020)\n"
             "Kết luận: 5/7 tiêu chí đạt, 1 phần, 1 N/A",
             font_size=13, color=C_GRAY, align=PP_ALIGN.CENTER)


# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 14: KẾT LUẬN (Conclusion + Grading)
# ═══════════════════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_title_bar(slide, "Kết luận", "Thành tựu, Hạn chế, Hướng phát triển & Tiêu chí đánh giá")
add_footer(slide, 14)

# Left - Achievements
add_shape(slide, Inches(0.3), Inches(1.6), Inches(4.2), Inches(2.7),
          fill_color=RGBColor(0xE8, 0xF5, 0xE9), line_color=C_GREEN)
add_text_box(slide, Inches(0.5), Inches(1.65), Inches(3.8), Inches(0.35), "Thành tựu chính",
             font_size=15, bold=True, color=C_GREEN)
achievements = [
    "Hệ thống Hybrid Document + Graph hoàn chỉnh",
    "BM25F multi-field (500 hồ sơ bệnh nhân)",
    "METIS Edge-Cut (200 nút, ~800 cạnh, 4 PV)",
    "3 chiến lược Join + Combined scoring",
    "Giao diện web 3 trang (D3.js, Chart.js)",
    "2 chế độ: Flask API + Standalone HTML",
]
txbox = add_text_box(slide, Inches(0.5), Inches(2.05), Inches(3.8), Inches(2.1), "", font_size=12, color=C_BLACK)
tf = txbox.text_frame; tf.word_wrap = True
for i, item in enumerate(achievements):
    if i == 0:
        tf.paragraphs[0].text = f"\u2705 {item}"; tf.paragraphs[0].font.size = Pt(12)
        tf.paragraphs[0].font.color.rgb = C_BLACK; tf.paragraphs[0].font.name = "Calibri"; tf.paragraphs[0].space_after = Pt(2)
    else:
        add_para(tf, f"\u2705 {item}", font_size=12, space_after=Pt(2))

# Middle - Limitations
add_shape(slide, Inches(4.7), Inches(1.6), Inches(4.2), Inches(2.7),
          fill_color=RGBColor(0xFD, 0xED, 0xEC), line_color=C_RED)
add_text_box(slide, Inches(4.9), Inches(1.65), Inches(3.8), Inches(0.35), "Hạn chế",
             font_size=15, bold=True, color=C_RED)
limitations = [
    "Dữ liệu tổng hợp (500 BN), chưa validation thực tế",
    "Phân tán logic (1 máy), chưa network overhead thực",
    "Read-only, chưa distributed transaction",
    "Join key (disease name) dễ lỗi chuẩn hóa",
    "METIS dependency (fallback hash kém hơn)",
]
txbox = add_text_box(slide, Inches(4.9), Inches(2.05), Inches(3.8), Inches(2.1), "", font_size=12, color=C_BLACK)
tf = txbox.text_frame; tf.word_wrap = True
for i, item in enumerate(limitations):
    if i == 0:
        tf.paragraphs[0].text = f"\u274C {item}"; tf.paragraphs[0].font.size = Pt(12)
        tf.paragraphs[0].font.color.rgb = C_BLACK; tf.paragraphs[0].font.name = "Calibri"; tf.paragraphs[0].space_after = Pt(2)
    else:
        add_para(tf, f"\u274C {item}", font_size=12, space_after=Pt(2))

# Right - Future
add_shape(slide, Inches(9.1), Inches(1.6), Inches(4.2), Inches(2.7),
          fill_color=RGBColor(0xE3, 0xF2, 0xFD), line_color=C_SECONDARY)
add_text_box(slide, Inches(9.3), Inches(1.65), Inches(3.8), Inches(0.35), "Hướng phát triển",
             font_size=15, bold=True, color=C_SECONDARY)
futures = [
    "Triển khai multi-node (Kafka/gRPC)",
    "Tích hợp LLM embedding (FAISS)",
    "Graph Neural Network cho scoring",
    "Federated Learning (quyền riêng tư y tế)",
    "Thêm chiều thời gian (temporal analysis)",
]
txbox = add_text_box(slide, Inches(9.3), Inches(2.05), Inches(3.8), Inches(2.1), "", font_size=12, color=C_BLACK)
tf = txbox.text_frame; tf.word_wrap = True
for i, item in enumerate(futures):
    if i == 0:
        tf.paragraphs[0].text = f"\U0001F4A1 {item}"; tf.paragraphs[0].font.size = Pt(12)
        tf.paragraphs[0].font.color.rgb = C_BLACK; tf.paragraphs[0].font.name = "Calibri"; tf.paragraphs[0].space_after = Pt(2)
    else:
        add_para(tf, f"\U0001F4A1 {item}", font_size=12, space_after=Pt(2))

# Bottom - Grading criteria
add_shape(slide, Inches(0.3), Inches(4.5), Inches(12.8), Inches(2.3),
          fill_color=C_LIGHT_BG, line_color=C_BORDER)
add_text_box(slide, Inches(0.5), Inches(4.55), Inches(12.5), Inches(0.35),
             "Tiêu chí đánh giá đồ án (thang điểm 100)", font_size=15, bold=True, color=C_PRIMARY)

grade_headers = ["Tiêu chí", "Điểm", "Nội dung"]
grade_rows = [
    ["METIS Graph Partitioning", "/15", "Edge-Cut, Recursive Bisection, 4 partitions, ECR"],
    ["Multi-Model Integration", "/15", "Join Document + Graph qua disease name"],
    ["Graph Traversal Algorithms", "/15", "BFS, DFS, Dijkstra + distance scoring"],
    ["Join Cost Analysis", "/15", "3 strategies: Filter, Index Nested-Loop, Hash"],
    ["Tài liệu (Proposal + Design + Report)", "/15", "3 tài liệu docx + slide bảo vệ"],
    ["Source Code & README", "/10", "Code quality, docstring, hướng dẫn cài đặt"],
    ["Video Demo (3-5 phút, failure cases)", "/10", "Demo Kill Node B, graceful degradation"],
]
add_table(slide, Inches(0.5), Inches(4.95), Inches(12.5), Inches(1.7), grade_headers, grade_rows,
          col_widths=[Inches(3.5), Inches(1.0), Inches(8.0)])


# ═══════════════════════════════════════════════════════════════════════════
# SLIDE 15: TÀI LIỆU THAM KHẢO & Q&A
# ═══════════════════════════════════════════════════════════════════════════
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide, C_PRIMARY)

add_shape(slide, 0, Inches(2.5), W, Inches(0.08), fill_color=C_ACCENT)

add_text_box(slide, Inches(0.5), Inches(0.6), Inches(12), Inches(0.5),
             "Tài liệu Tham khảo", font_size=24, bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)

refs = [
    "[1] M. T. Özsu and P. Valduriez, Principles of Distributed Database Systems, 4th ed. Springer, 2020.",
    "[2] G. Karypis and V. Kumar, \"A Fast and High Quality Multilevel Scheme for Partitioning Irregular Graphs,\" SIAM J. Sci. Comput., 1998.",
    "[3] S. Robertson and H. Zaragoza, \"The Probabilistic Relevance Framework: BM25 and Beyond,\" FnT IR, 2009.",
    "[4] R. Angles and C. Gutierrez, \"Survey of Graph Database Models,\" ACM Comput. Surv., 2008.",
    "[5] C. J. Date, \"Twelve Rules for a Distributed Data Base,\" Computerworld, 1987.",
    "[6] Whoosh Library Documentation, https://whoosh.readthedocs.io/",
    "[7] NetworkX Documentation, https://networkx.org/documentation/stable/",
    "[8] METIS Serial Graph Partitioning, http://glaros.dtc.umn.edu/gkhome/metis/metis/overview",
]
txbox = add_text_box(slide, Inches(0.8), Inches(1.0), Inches(11.5), Inches(3.5), "", font_size=13, color=RGBColor(0xDD, 0xE8, 0xF5))
tf = txbox.text_frame; tf.word_wrap = True
for i, ref in enumerate(refs):
    p = tf.paragraphs[0] if i == 0 else add_para(tf, ref, font_size=12, color=RGBColor(0xDD, 0xE8, 0xF5), space_after=Pt(5))
    if i == 0:
        p.text = ref; p.font.size = Pt(12); p.font.color.rgb = RGBColor(0xDD, 0xE8, 0xF5); p.font.name = "Calibri"; p.space_after = Pt(5)

add_text_box(slide, Inches(0.5), Inches(4.8), Inches(12), Inches(0.5),
             "Cảm ơn Thầy và các bạn đã lắng nghe!",
             font_size=28, bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)
add_text_box(slide, Inches(0.5), Inches(5.5), Inches(12), Inches(0.4),
             "Q & A  \u2013  Trần Hữu Trung (N23DCCN200)  \u2013  trungth.dev@gmail.com",
             font_size=16, color=C_ACCENT, align=PP_ALIGN.CENTER)
add_text_box(slide, Inches(0.5), Inches(6.1), Inches(12), Inches(0.4),
             "Mã nguồn: https://github.com/trungth/Hybrid-Document-Graph-Store",
             font_size=14, color=RGBColor(0x99, 0xBB, 0xDD), align=PP_ALIGN.CENTER)


# ── Save ──────────────────────────────────────────────────────────────────
prs.save(OUTPUT_PATH)
print(f"PPTX saved to: {OUTPUT_PATH}")
