# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Đặng Hữu Cương
- **MSSV:** 2A202602572
- **Lớp:** K4-L3A
- **Repository URL:** https://github.com/y0sh1da-available/K4-L3-DAY13-DangHuuCuong-2A202602572-Monitoring-LLMOps.git
- **Commit SHA cuối:**
- **Challenge ID:**
- **Tên project Langfuse cá nhân:** `day13-k4-l3a-2A202602572`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.png` |
| Log validator | `evidence/02-log-validator.txt` |
| Dashboard validator | `evidence/03-dashboard-validator.txt` |
| Structured log | `evidence/04-structured-log.png` |
| PII redaction | `evidence/05-pii-redaction.png` |
| Trace list | `evidence/06-trace-list.png` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | `evidence/08-trace-metadata.png` |
| Prompt versions | `evidence/09-prompt-versions.png` |
| Prompt rollback | `evidence/10-prompt-rollback.png` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.png` |
| Incident log | `evidence/13-incident-log.png` |
| Incident trace | `evidence/14-incident-trace.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 30/100 | 100/100 | Đã bổ sung middleware correlation ID, enrich metadata và đăng ký PII scrubber |
| `validate_dashboard.py` | 6/6 panel | 6/6 panel | Hợp lệ theo dashboard contract schema |
| `pytest` | 22 passed | 24 passed | Bổ sung test kiểm tra CCCD và Credit Card scrubbing |
| Số traces hợp lệ | 0 | 12+ traces | Đã tạo workload trên project cá nhân với root, retriever và generation |
| Số PII leak | 0 | 0 | 0 leak trên toàn bộ logs |
| Latency P95 / TTFT P95 | ~516.4ms / N/A | ~208ms / 50ms | Độ trễ đo từ tail latency và first token |
| Retrieval success rate | 100% | 100% | Toàn bộ truy vấn retrieval thành công |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Trong `CorrelationIdMiddleware` (`app/middleware.py`), trước khi xử lý mỗi request, gọi `clear_contextvars()` để xóa context cũ tránh rò rỉ giữa các request. Trích xuất `x-request-id` từ request header nếu client truyền lên, nếu không có thì tự động sinh theo định dạng `req-<8-hex>` (`f"req-{uuid.uuid4().hex[:8]}"`). Sau đó gán vào `request.state.correlation_id` và bind vào structlog contextvars thông qua `bind_contextvars(correlation_id=correlation_id)`. Khi request hoàn tất, tính duration xử lý và trả về cả `x-request-id` lẫn `x-response-time-ms` trong response headers.
- **Các metadata được ghi vào structured log:** Toàn bộ log API đều được làm giàu (enrich) tự động thông qua structlog contextvars: `correlation_id`, `ts` (ISO 8601 UTC), `level`, `service` ("api"), `event` ("request_received", "response_sent", "request_failed"), `user_id_hash` (băm SHA-256 lấy 12 ký tự hex đầu), `session_id`, `feature`, `model` ("claude-sonnet-4-5"), `env` ("dev"), cùng các chỉ số vận hành chi tiết: `latency_ms`, `ttft_ms`, `tokens_in`, `tokens_out`, `cost_usd`, `quality_score`, `tool_name`, `tool_success` và `payload`.
- **Cách bảo đảm PII được scrub trước khi ghi:** Processor `scrub_event` trong `app/logging_config.py` được cấu hình nằm ngay trước `JsonlFileProcessor()` và `structlog.processors.JSONRenderer()`. Hàm `scrub_event` duyệt đệ quy qua mọi trường và cấu trúc dữ liệu con trong event log, gọi `scrub_text()` để thay thế toàn bộ email, số điện thoại Việt Nam (+84, 09x, dấu cách, gạch nối, chấm), CCCD (12 chữ số) và thẻ thanh toán (16 chữ số phân cách hoặc viết liền) bằng các token `[REDACTED_*]`. Vì việc thay thế diễn ra trước bước render và ghi file, tuyệt đối không có dữ liệu PII thô nào lọt vào `data/logs.jsonl` hoặc console output.
- **Cách kiểm chứng kết quả:** Chạy `python scripts/validate_logs.py` đạt 100/100 điểm (0 bản ghi thiếu trường bắt buộc, 0 bản ghi thiếu context enrichment, 10/10 correlation ID phân biệt, 0 PII leak); chạy `python -m pytest -q` đạt 24/24 passed bao gồm các bộ test PII trong `tests/test_pii.py` và `tests/test_validate_logs.py`. Đồng thời kiểm tra trực tiếp file `data/logs.jsonl` thấy rõ các token `[REDACTED_EMAIL]`, `[REDACTED_PHONE_VN]`, `[REDACTED_CREDIT_CARD]`.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** Traces được ghi trực tiếp vào project Langfuse cá nhân mang tên `day13-k4-l3a-2A202602572`. API key pair của project được cấu hình riêng trong `.env`. Mọi traces sinh ra từ workload có tag `['lab', feature, 'claude-sonnet-4-5']` và metadata `correlation_id` khớp chính xác với từng request ghi nhận tại `data/logs.jsonl` của máy tôi.
- **Cấu trúc root/retrieval/generation observations:**
  - *Root observation:* `lab-agent-run` (type `agent`), bao bọc toàn bộ luồng thực thi trong `LabAgent.run()`.
  - *Child observation 1:* `retrieve` (type `retriever`), đo thời gian thực thi của tác vụ truy xuất tri thức và ghi nhận metadata `doc_count`.
  - *Child observation 2:* `generation` (type `generation`), bao bọc cuộc gọi `FakeLLM.generate()`, ghi nhận model `claude-sonnet-4-5`, input/output prompt đã được tóm tắt khử PII (`summarize_text`), chi tiết token usage (`input`, `output`, `total`), ước tính chi phí `cost_usd` và liên kết trực tiếp với đối tượng managed prompt.
- **Cách nối trace với log:** Sử dụng trường định danh tương quan `correlation_id` (`req-<8-hex>`). Trong log, giá trị này nằm ở trường `correlation_id` qua structlog contextvars. Trong Langfuse, middleware và agent truyền `correlation_id` vào `propagate_attributes(metadata={"correlation_id": correlation_id})`, giúp liên kết 1-1 giữa mỗi dòng log và một trace cụ thể trên Langfuse.
- **Prompt name:** `day13-chat`
- **Version/label baseline:** Version 1 (`Feature={{feature}}\nDocs={{docs}}\nQuestion={{message}}`), labels: `baseline`, `production`.
- **Version/label candidate:** Version 2 (thêm chỉ dẫn định dạng phản hồi ngắn gọn: `Answer concisely and accurately:`), labels: `candidate`, `latest`.
- **Trace ID của mỗi version:**
  - Version 1 (`production`/`baseline`): request với `correlation_id` `req-a6330389`.
  - Version 2 (`candidate`): Trace ID `230f35370e3db909d710e2b5647704d0` (request với `correlation_id` `req-7c40262a` như trong ảnh `07-trace-waterfall.png` và `08-trace-metadata.png`).
- **Cách promote và rollback `production`:**
  - *Promote:* Trên Langfuse (hoặc qua hàm `update_prompt`), cập nhật Version 2 gắn thêm label `production` (`new_labels=['candidate', 'production']`). Các request tiếp theo khi gọi label `production` sẽ tự động kéo Version 2.
  - *Rollback:* Khi cần hoàn nguyên về bản ổn định, cập nhật Version 1 gắn lại label `production` (`new_labels=['baseline', 'production']`). Hệ thống tự động phục hồi về prompt Version 1 an toàn mà không cần sửa code ứng dụng.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** Dựng đủ 6 panel theo đúng contract `config/dashboard.yaml` sử dụng nguồn dữ liệu chuẩn `data/logs.jsonl`:
  1. *Latency percentiles and TTFT* (ms): Thể hiện P50, P95, P99 và TTFT P95. Threshold: P95 <= 3000 ms.
  2. *Request traffic* (requests/phút): Thể hiện tổng request và tốc độ trung bình theo phút. Threshold: rate >= 1 req/min.
  3. *Error rate and retrieval success* (%): Tỷ lệ request thất bại (error rate %) và tỷ lệ retrieval thành công (tool_success_rate %). Threshold: error_rate <= 2.0% và retrieval >= 90%.
  4. *Cost over time* (USD): Tổng chi phí lũy kế và chi phí trung bình theo phút. Threshold: total <= $2.50 USD.
  5. *Input and output tokens* (tokens): Thống kê tổng token vào/ra và tổng tích lũy. Threshold: total <= 50,000 tokens.
  6. *Quality proxy* (thang điểm 0–1): Điểm đánh giá chất lượng phản hồi trung bình. Threshold: mean >= 0.75.
- **SLO và lý do chọn:** Primary SLO là `fast_successful_requests`: 99.5% requests thành công và có `latency_ms <= 3000ms` trong cửa sổ 28 ngày. Lý do chọn: Độ trễ dưới 3 giây và không gặp lỗi là yếu tố then chốt quyết định sự hài lòng của người dùng cuối trong ứng dụng AI đàm thoại.
- **Cách tính error budget:**
  - Với mục tiêu SLO = 99.5%, Error Budget cho phép là `100% - 99.5% = 0.5%`.
  - Trong cửa sổ 28 ngày với tổng số request là $N$, số lượng request bị suy thoái (chậm quá 3000ms hoặc gặp lỗi HTTP 500) tối đa được chấp nhận là $N \times 0.005$. Nếu số lượng request lỗi vượt qua ngưỡng này, ngân sách lỗi bị cạn kiệt (burn rate > 1), kích hoạt chính sách đóng băng triển khai tính năng mới để tập trung cải thiện độ ổn định.
- **Ba alert và runbook tương ứng:**
  1. `HighLatencyP95` (critical/P1): Điều kiện `latency_p95 > 3000`, duy trì 5 phút. Kênh Slack `#llmops-alerts`. Runbook: `docs/alerts.md#alert-1`.
  2. `HighErrorRate` (critical/P1): Điều kiện `error_rate_pct > 2 or retrieval_success_rate_pct < 90`, duy trì 3 phút. Kênh Slack `#llmops-alerts`. Runbook: `docs/alerts.md#alert-2`.
  3. `CostSpike` (warning/P2): Điều kiện `cost_usd_total > 2.5`, duy trì 10 phút. Kênh Slack `#llmops-finops`. Runbook: `docs/alerts.md#alert-3`.

## 7. Điều tra challenge

- **Challenge ID:**
- **Khoảng thời gian điều tra:**
- **Triệu chứng từ metrics:**
- **Log line và correlation ID liên quan:**
- **Trace ID và span gây ảnh hưởng:**
- **Root cause:**
- **Fix action:**
- **Preventive measure:**

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:**
- **Một lỗi/blocker đã gặp:**
- **Cách tìm nguyên nhân và xử lý:**
- **Cách hiểu luồng Metrics → Logs → Traces:**
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:**
- **Điều quan trọng nhất đã học:**
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:**

## 9. Checklist trước khi nộp

- [ ] Kết quả và evidence thuộc commit SHA cuối.
- [ ] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [ ] Incident evidence nối đúng metric → log → trace.
- [ ] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [ ] Repository chạy lại được theo README.
- [ ] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [ ] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
