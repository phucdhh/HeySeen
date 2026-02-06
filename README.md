# 👁️ HeySeen: PDF → TeX + Images (Offline, Apple Silicon)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Platform: macOS](https://img.shields.io/badge/platform-macOS-lightgrey.svg)](https://www.apple.com/macos/)

> **Offline-first PDF to LaTeX converter optimized for Apple Silicon**

**HeySeen** là ứng dụng chuyển đổi PDF (bài báo khoa học, sách chuyên ngành) thành **thư mục gồm file TeX và ảnh** (nếu có), chạy **hoàn toàn offline trên macOS (Apple Silicon)**. Mục tiêu là tạo pipeline tái hiện nội dung học thuật (text + math + figures) để dễ biên tập, lưu trữ và tái sử dụng—không cần API cloud, không phụ thuộc subscription.

---

## ✅ Tính khả thi

**Khả thi ở mức sản phẩm offline** nếu tập trung vào các tiêu chí sau:

- **Chấp nhận độ chính xác thực tế**: OCR math và layout vẫn có lỗi; cần cơ chế hậu kiểm.
- **Batch + caching**: xử lý theo trang, lưu kết quả trung gian để tránh rerun.
- **Tách nhiệm vụ**: layout → text OCR → math OCR → hình ảnh → tái dựng TeX.

Apple Silicon (M2 Pro) đủ mạnh để chạy inference offline, đặc biệt khi tối ưu **MPS** và batching.

### 🎯 Use Cases (Trường hợp sử dụng)

1. **Nghiên cứu sinh/học viên**: Chuyển paper PDF sang TeX để trích dẫn, chỉnh sửa công thức, hoặc tích hợp vào thesis.
2. **Nhà xuất bản học thuật**: Batch convert sách/tài liệu cũ (scan) sang TeX để tái bản.
3. **Thư viện/Archive**: Số hóa tài liệu riêng tư mà không upload lên cloud của bên thứ ba.
4. **Giảng viên**: Trích xuất đề thi/bài giảng từ PDF sang LaTeX để chỉnh sửa nhanh.

---

## 🥊 HeySeen có cạnh tranh được với Mathpix không?

**Có thể cạnh tranh theo hướng khác**, không phải đối đầu trực tiếp về “độ chính xác tuyệt đối”.

| Tiêu chí | HeySeen (định hướng) | Mathpix | Nhận xét |
|---|---|---|---|
| Offline & bảo mật | ✅ | ❌ | Lợi thế rõ ràng cho nội bộ/nhạy cảm |
| Chi phí dài hạn | ✅ (local) | ❌ (subscription) | Lợi thế nếu xử lý khối lượng lớn |
| Độ chính xác tổng thể | ⚠️ (phụ thuộc model) | ✅ | Mathpix dẫn đầu |
| UX hoàn chỉnh | ⚠️ (tự xây) | ✅ | Cần đầu tư UI + workflow |
| Tùy biến pipeline | ✅ | ❌ | Lợi thế nghiên cứu nội bộ |

**Kết luận thực tế**: HeySeen có thể **cạnh tranh trong phân khúc offline + privacy + bulk processing**, còn **Mathpix vẫn mạnh ở độ chính xác và trải nghiệm người dùng**.

---

## 🚀 Deployment (Production)

HeySeen is configured to run as a persistent service on macOS.

### Quick Start

Use the management scripts in the project root:

```bash
./start.sh     # Start all services (Backend + Cloudflare Tunnel)
./stop.sh      # Stop all services
./status.sh    # Check service status
./restart.sh   # Restart all services
```

### 1. Operations

**Main Management Scripts** (recommended):
- `./start.sh` - Starts Backend API + Cloudflare Tunnel
- `./stop.sh` - Safely stops all processes
- `./status.sh` - View detailed service status
- `./restart.sh` - Restart all services

**Additional Scripts** in `deploy/` folder:
- `./deploy/health_check.sh` - Extended health diagnostics
- `./deploy/start_tunnel_bg.sh` - Restart only the Cloudflare Tunnel

### 2. Monitoring
- **Backend Log**: `server_data/server.log`
- **Tunnel Log**: `deploy/tunnel.log`
- **Local URL**: `http://localhost:5555`
- **Public URL**: `https://<your-tunnel-url>.trycloudflare.com` (Check `tunnel.log` or Dashboard)

### 3. Auto-start (Persistence)
Services are configured to auto-start on login via `launchd`:
- `~/Library/LaunchAgents/vn.edu.truyenthong.heyseen.server.plist`
- `~/Library/LaunchAgents/vn.edu.truyenthong.heyseen.tunnel.plist`

If services do not start automatically after a reboot, you can verify them:
```bash
launchctl list | grep heyseen
# If missing:
./deploy/install_autostart.sh
```

---

## 🎯 Mục tiêu sản phẩm

- Chuyển PDF → thư mục kết quả:
	- `main.tex` (text + math)
	- `images/` (figure, diagram, table image)
	- `meta.json` (mapping trang → block)
- Chạy offline trên macOS, tối ưu MPS.
- Có pipeline đánh giá chất lượng và log lỗi.

---

## 🧠 Kiến trúc đề xuất

1. **PDF Parsing**: tách trang, render ảnh.
2. **Layout Analysis**: phát hiện block (text, math, figure, table).
3. **Text OCR**: nhận dạng paragraph.
4. **Math OCR**: nhận dạng công thức → LaTeX.
5. **Image Extract**: cắt figure/table ra thư mục.
6. **Reconstruction**: tạo `main.tex` theo thứ tự reading order.

---

## 💻 Yêu cầu kỹ thuật & Cài đặt (Dev Setup)

**Môi trường khuyến nghị:**
- **Hardware**: Mac M1/M2/M3 (Pro/Max khuyến nghị cho batch size lớn), RAM ≥ 16GB.
- **OS**: macOS Sonoma trở lên.
- **Python**: 3.10+ (quản lý qua `venv`).

**Cài đặt Dependencies:**
Cần cài đặt `poppler` và `tesseract` để hỗ trợ xử lý PDF và OCR cơ bản.

```bash
# 1. System packages
brew install poppler tesseract

# 2. Python environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install PyTorch with MPS support (Nightly often has better MPS fixes)
pip install --pre torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/nightly/cpu

# 4. Install Core Libraries
pip install marker-pdf surya-ocr
```

---

## 🔧 Nguồn công nghệ tham khảo

- **Marker**: https://github.com/datalab-to/marker
- **Surya** (layout analysis)
- **Texify** (math recognition)

---

## 🧪 Đánh giá chất lượng

- **Accuracy**: WER cho text, LaTeX match rate cho math.
- **Layout fidelity**: độ đúng thứ tự khối nội dung.
- **Speed**: trang/giây trên M2 Pro.

### 📊 Benchmark Baseline (Dự kiến)

| Model/Step | Throughput | Accuracy (Est.) | Memory |
|---|---|---|---|
| Surya Layout | ~2-3 pages/sec | 85-90% block detection | ~4GB |
| Texify Math OCR | ~1-2 formulas/sec | 75-85% LaTeX match | ~3GB |
| Text OCR (Tesseract) | ~10 pages/sec | 90-95% WER | ~1GB |
| **Total Pipeline** | **~0.5-1 page/sec** | **Varies by document** | **~8-10GB** |

*Lưu ý: Số liệu ước tính dựa trên tài liệu học thuật tiêu chuẩn (2-column, moderate math). Actual performance phụ thuộc vào độ phức tạp.*

---

## 🚧 Hạn chế kỹ thuật (Known Limitations)

1. **Chữ viết tay (Handrwriting)**: Các model hiện tại (marker/surya) chưa tối ưu tốt cho chữ viết tay so với Mathpix.
2. **Layout phức tạp**: Sách giáo khoa có layout nhiều cột lồng nhau hoặc text bao quanh ảnh có thể bị sai thứ tự (reading order).
3. **Tiêu tốn RAM**: Chạy model Surya/Texify song song có thể ăn >10GB RAM, cần quản lý bộ nhớ thủ công để tránh swap trên máy 16GB.

---

## 🗺️ Lộ trình đề xuất

**Phase 1 — Pipeline MVP**
- Chạy được PDF → TeX + images với batch CLI.
- Logging + lưu kết quả trung gian.

**Phase 2 — Quality & UX**
- Hậu kiểm (diff viewer).
- Sửa lỗi nhanh (interactive fixes).

**Phase 3 — Optimization**
- Batching + caching + MPS tuning.
- Plugin export (Word, Markdown).

---

## 📂 Cấu trúc output dự kiến

```
output/
	main.tex
	images/
		page_01_fig_01.png
		page_03_table_01.png
	meta.json
```

---

## ⚠️ Lưu ý pháp lý

- Chỉ xử lý tài liệu hợp pháp hoặc thuộc quyền sử dụng của bạn.
- OCR có thể sai; cần hậu kiểm nếu dùng vào xuất bản.

---

## 🔍 FAQ & Troubleshooting

**Q: Tại sao không dùng Tesseract trực tiếp?**  
A: Tesseract yếu ở layout phức tạp và math OCR. HeySeen dùng Surya (layout) + Texify (math) cho độ chính xác cao hơn.

**Q: RAM 16GB có đủ không?**  
A: Đủ cho xử lý tuần tự (1 page/batch). Nếu muốn batch lớn (>5 pages), cần 32GB.

**Q: MPS (Metal) có nhanh hơn CPU?**  
A: Có, thường nhanh gấp 2-3 lần. Dùng `PYTORCH_ENABLE_MPS_FALLBACK=1` để tránh crash với ops không hỗ trợ.

**Q: Làm sao biết pipeline đang chạy đúng?**  
A: Kiểm tra `meta.json` output—nếu có `block_types` và `bbox`, layout analysis đã hoạt động.

---

## 📌 Trạng thái hiện tại

**Status**: 🟡 In Development (Phase 0 - Planning)

- [x] Nghiên cứu công nghệ (Marker, Surya, Texify)
- [x] Định hình kiến trúc pipeline
- [ ] Implementation Phase 1 (xem [PLAN.md](PLAN.md))
- [ ] Benchmark trên M2 Pro với test dataset

---

## 🤝 Contributing

Dự án đang ở giai đoạn đầu. Nếu quan tâm:
1. **Issues**: Report bugs hoặc đề xuất features qua GitHub Issues.
2. **Pull Requests**: Chào đón PR cho bug fixes, optimization, hoặc documentation.
3. **Testing**: Cần volunteers test với các loại PDF khác nhau (textbook, paper, thesis).

Xem chi tiết triển khai tại [PLAN.md](PLAN.md).





