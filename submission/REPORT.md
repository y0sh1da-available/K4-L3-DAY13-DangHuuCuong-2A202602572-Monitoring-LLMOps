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
| Dashboard validator | `evidence/03-dashboard-validator.png` |
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
| `validate_dashboard.py` | 6/6 panel | | Contract schema hợp lệ |
| `pytest` | 22 passed | 24 passed | Bổ sung test kiểm tra CCCD và Credit Card scrubbing |
| Số traces hợp lệ | 0 | | Chưa triển khai child observations cho tracing |
| Số PII leak | 0 | 0 | 0 leak trên 20 bản ghi sau load test |
| Latency P95 / TTFT P95 | ~516.4ms / N/A | | |
| Retrieval success rate | 100% | | |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Trong `CorrelationIdMiddleware` (`app/middleware.py`), trước khi xử lý mỗi request, gọi `clear_contextvars()` để xóa context cũ tránh rò rỉ giữa các request. Trích xuất `x-request-id` từ request header nếu client truyền lên, nếu không có thì tự động sinh theo định dạng `req-<8-hex>` (`f"req-{uuid.uuid4().hex[:8]}"`). Sau đó gán vào `request.state.correlation_id` và bind vào structlog contextvars thông qua `bind_contextvars(correlation_id=correlation_id)`. Khi request hoàn tất, tính duration xử lý và trả về cả `x-request-id` lẫn `x-response-time-ms` trong response headers.
- **Các metadata được ghi vào structured log:** Toàn bộ log API đều được làm giàu (enrich) tự động thông qua structlog contextvars: `correlation_id`, `ts` (ISO 8601 UTC), `level`, `service` ("api"), `event` ("request_received", "response_sent", "request_failed"), `user_id_hash` (băm SHA-256 lấy 12 ký tự hex đầu), `session_id`, `feature`, `model` ("claude-sonnet-4-5"), `env` ("dev"), cùng các chỉ số vận hành chi tiết: `latency_ms`, `ttft_ms`, `tokens_in`, `tokens_out`, `cost_usd`, `quality_score`, `tool_name`, `tool_success` và `payload`.
- **Cách bảo đảm PII được scrub trước khi ghi:** Processor `scrub_event` trong `app/logging_config.py` được cấu hình nằm ngay trước `JsonlFileProcessor()` và `structlog.processors.JSONRenderer()`. Hàm `scrub_event` duyệt đệ quy qua mọi trường và cấu trúc dữ liệu con trong event log, gọi `scrub_text()` để thay thế toàn bộ email, số điện thoại Việt Nam (+84, 09x, dấu cách, gạch nối, chấm), CCCD (12 chữ số) và thẻ thanh toán (16 chữ số phân cách hoặc viết liền) bằng các token `[REDACTED_*]`. Vì việc thay thế diễn ra trước bước render và ghi file, tuyệt đối không có dữ liệu PII thô nào lọt vào `data/logs.jsonl` hoặc console output.
- **Cách kiểm chứng kết quả:** Chạy `python scripts/validate_logs.py` đạt 100/100 điểm (0 bản ghi thiếu trường bắt buộc, 0 bản ghi thiếu context enrichment, 10/10 correlation ID phân biệt, 0 PII leak); chạy `python -m pytest -q` đạt 24/24 passed bao gồm các bộ test PII trong `tests/test_pii.py` và `tests/test_validate_logs.py`. Đồng thời kiểm tra trực tiếp file `data/logs.jsonl` thấy rõ các token `[REDACTED_EMAIL]`, `[REDACTED_PHONE_VN]`, `[REDACTED_CREDIT_CARD]`.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:**
- **Cấu trúc root/retrieval/generation observations:**
- **Cách nối trace với log:**
- **Prompt name:**
- **Version/label baseline:**
- **Version/label candidate:**
- **Trace ID của mỗi version:**
- **Cách promote và rollback `production`:**

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:**
- **SLO và lý do chọn:**
- **Cách tính error budget:**
- **Ba alert và runbook tương ứng:**

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
