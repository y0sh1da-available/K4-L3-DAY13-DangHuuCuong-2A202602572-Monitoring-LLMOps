# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Đặng Hữu Cương
- **MSSV:** 2A202602572
- **Lớp:** K4-L3A
- **Repository URL:** https://github.com/y0sh1da-available/K4-L3-DAY13-DangHuuCuong-2A202602572-Monitoring-LLMOps.git
- **Commit SHA cuối:** `102ad3b`
- **Challenge ID:** day13-k4-l3a-monitoring-llmops-v1
- **Tên project Langfuse cá nhân:** `day13-k4-l3a-2A202602572`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.txt` |
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

- **Challenge ID:** day13-k4-l3a-monitoring-llmops-v1
- **Khoảng thời gian điều tra:** 2026-09-29 17:20:00 - 17:25:00 (UTC 10:20:00 - 10:25:00)
- **Triệu chứng từ metrics:** Trên Dashboard tại Panel 1 (Latency percentiles & TTFT), chỉ số độ trễ P95 tăng vọt từ ~208ms lên 2867.8ms (vượt ngưỡng cảnh báo 2000ms của challenge). Trong khi đó, TTFT P95 vẫn duy trì rất thấp ở mức 53.8ms, chứng tỏ bản thân mô hình LLM không bị trễ thời gian sinh token đầu tiên mà độ trễ nằm ở các bước xử lý dữ liệu trước LLM.
- **Log line và correlation ID liên quan:** Lọc log trong `data/logs.jsonl` tại thời điểm sự cố xác định request bất thường có `correlation_id: req-76bb8208`. Dòng log `response_sent`:
  `{"service": "api", "latency_ms": 3727, "ttft_ms": 50, "tokens_in": 34, "tokens_out": 85, "cost_usd": 0.001377, "quality_score": 0.9, "tool_name": "retrieval", "tool_success": true, "payload": {"answer_preview": "Starter answer. You should improve this output logic and add better quality chec..."}, "event": "response_sent", "session_id": "k4-l3a-challenge-s02", "user_id_hash": "aae0b94055a9", "feature": "monitoring", "env": "dev", "model": "claude-sonnet-4-5", "correlation_id": "req-76bb8208", "level": "info", "ts": "2026-09-29T10:21:02.444751Z"}`. Độ trễ ghi nhận lên tới 3727ms.
- **Trace ID và span gây ảnh hưởng:** Trace ID: `b4b42f617c6e861e38bd5292be297f13` (khớp chính xác thời gian `2026-09-29 10:21:02.444 UTC` với log của `req-76bb8208`). Trong cây waterfall của trace này, span gây ảnh hưởng chính là child observation `retrieve` (loại `retriever`) kéo dài **2501ms** (từ `10:20:58.716` đến `10:21:01.217`), chiếm hơn 95% tổng thời gian xử lý, trong khi span `generation` chỉ mất **153ms**.
- **Root cause:** Thành phần Retrieval (RAG / Vector search) gặp sự cố tắc nghẽn (`rag_slow`), dẫn đến bước tra cứu ngữ cảnh mất hơn 2.5 giây, làm kéo sập tail latency của toàn bộ hệ thống.
- **Fix action:** Tắt sự cố bằng lệnh `python scripts/inject_incident.py --disable`. Trong môi trường sản xuất thực tế: kiểm tra kết nối mạng tới Vector DB cluster, kiểm tra tình trạng tải CPU/Memory của vector search nodes, mở rộng replica cho vector index và tối ưu tham số tìm kiếm top-k.
- **Preventive measure:**
  1. Cấu hình timeout nghiêm ngặt cho bước retrieval (ví dụ `timeout = 1000ms`), nếu vector store phản hồi quá 1 giây thì tự động kích hoạt fallback sang tìm kiếm từ khóa (lexical search) hoặc câu trả lời mặc định an toàn.
  2. Bổ sung semantic cache cho các embedding và kết quả retrieval phổ biến để giảm tải trực tiếp cho vector database.
  3. Cấu hình alert symptom-based `HighLatencyP95` (P1) gửi cảnh báo Slack tức thời cho on-call engineer khi Latency P95 vượt 3000ms kéo dài trên 5 phút.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** Quyết định đặt processor `scrub_event` trong pipeline của structlog ngay TRƯỚC `JsonlFileProcessor()` và `JSONRenderer()`, đồng thời triển khai cơ chế làm sạch đệ quy duyệt qua toàn bộ dictionary/list trong `event_dict`. Lý do: Áp dụng triệt để nguyên tắc bảo mật Zero Trust cho dữ liệu nhạy cảm — bảo đảm mọi dữ liệu trước khi được serialize sang chuỗi JSON hoặc ghi xuống đĩa (`data/logs.jsonl`) đều đã bị che giấu PII 100%, triệt tiêu hoàn toàn rủi ro rò rỉ thông tin người dùng ra log aggregator hoặc bên thứ ba.
- **Một lỗi/blocker đã gặp:** Khi chạy load test với `--concurrency 5` trong lúc kích hoạt sự cố `rag_slow`, hàm `retrieve()` sử dụng `time.sleep(2.5)` đồng bộ gây blocking trên luồng xử lý của FastAPI, dẫn đến các request đồng thời bị xếp hàng chờ trong hàng đợi (queue delay), khiến client đo được độ trễ tổng thể lên tới hơn 16 giây.
- **Cách tìm nguyên nhân và xử lý:** So sánh giữa client latency (>16s), server log `latency_ms: 3727` và trace span `retrieve: 2500ms`. Sự chênh lệch này chỉ ra hiện tượng thread pool bị nghẽn do blocking I/O. Hướng xử lý: Trong môi trường production thực tế, toàn bộ tác vụ I/O mạng hoặc truy xuất database phải được viết bất đồng bộ (`async def retrieve` với async HTTP client hoặc đưa vào worker pool riêng) để không làm nghẽn event loop chính của web service.
- **Cách hiểu luồng Metrics → Logs → Traces:**
  1. *Metrics (Triệu chứng diện rộng):* Là radar phát hiện bất thường và khung thời gian xảy ra sự cố (Dashboard cảnh báo Latency P95 tăng vọt từ 208ms lên >2800ms vào lúc 17:21).
  2. *Logs (Request bị ảnh hưởng):* Sử dụng khung giờ từ metrics để lọc file log, trích xuất mã định danh tương quan `correlation_id` của request lỗi/chậm (tìm ra `req-76bb8208` bị chậm 3727ms).
  3. *Traces (Nguyên nhân gốc rễ):* Dùng chính `correlation_id` đó để tra cứu trace waterfall trên Langfuse, bóc tách từng span con để chỉ điểm chính xác thành phần gây lỗi (span `retrieve` kéo dài 2.5s do sự cố RAG).
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:**
  - *Prompt Versioning & Rollback:* Quản lý prompt như mã nguồn phiên bản, cho phép thử nghiệm phiên bản mới (`candidate`) và rollback tức thì về bản ổn định (`production`/`baseline`) ngay trên giao diện quản trị khi phát hiện lỗi định dạng hoặc suy giảm chất lượng mà không phải build/deploy lại container.
  - *Token & Cost Guardrails:* Mô hình LLM tiêu tốn chi phí theo lượng token tiêu thụ. Việc giám sát token/chi phí theo thời gian thực và đặt threshold cảnh báo giúp ngăn chặn sự cố cạn kiệt ngân sách hoặc vòng lặp vô tận (infinite generation loop).
  - *SLO & Error Budget:* Định lượng rõ ràng cam kết chất lượng dịch vụ (99.5% request dưới 3s), tạo căn cứ kỹ thuật minh bạch để quyết định khi nào được triển khai tính năng mới và khi nào phải ưu tiên vá lỗi độ ổn định hệ thống.
- **Điều quan trọng nhất đã học:** Nắm vững phương pháp luận Observability hiện đại cho LLM: Hiểu rõ structured logging không thay thế tracing, và metrics không thay thế logs. Sự kết hợp cả 3 trụ cột liên kết qua `correlation_id` là chìa khóa duy nhất để tháo gỡ bài toán "hộp đen" của các ứng dụng AI.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:** Bài lab hiện triển khai với FakeLLM và in-memory mock corpus thay vì cụm vector database phân tán thực tế (như Qdrant/Pinecone/Milvus) và LLM API thương mại bên ngoài.

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc commit SHA cuối.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [x] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
