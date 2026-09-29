# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert 1

- Tên: HighLatencyP95
- Severity: critical (P1)
- Duration: 5m
- Kênh thông báo: Slack (#llmops-alerts)
- SLI/SLO liên quan: Primary SLO `fast_successful_requests` (latency <= 3000ms trong 99.5% requests)
- Điều kiện và thời gian duy trì: Latency P95 > 3000ms kéo dài liên tục trên 5 phút
- Ảnh hưởng tới người dùng: Người dùng trải nghiệm độ trễ phản hồi cao, hội thoại gián đoạn hoặc quá thời gian chờ (timeout)
- Ba bước kiểm tra đầu tiên:
  1. Mở Panel Latency trên Dashboard để xác định thời điểm bắt đầu tăng tail latency và so sánh TTFT với total latency.
  2. Lọc file `data/logs.jsonl` tìm các log line `response_sent` có `latency_ms > 3000`, trích xuất `correlation_id` đại diện.
  3. Mở Langfuse trace tương ứng với `correlation_id` đó, kiểm tra waterfall span tree để khoanh vùng độ trễ xuất phát từ `retrieve` hay `generation`.
- Mitigation tạm thời: Kích hoạt fallback cache/lexical search nhanh cho RAG nếu vector store bị nghẽn, hoặc giảm max output tokens của LLM call.
- Owner: oncall-engineer

## Alert 2

- Tên: HighErrorRate
- Severity: critical (P1)
- Duration: 3m
- Kênh thông báo: Slack (#llmops-alerts)
- SLI/SLO liên quan: Guardrail `error_rate_pct_max` (<= 2%) và `retrieval_success_rate_pct_min` (>= 90%)
- Điều kiện và thời gian duy trì: Error rate > 2% hoặc Retrieval success rate < 90% kéo dài liên tục trên 3 phút
- Ảnh hưởng tới người dùng: Người dùng nhận mã lỗi HTTP 500 hoặc thông báo lỗi hệ thống, không nhận được câu trả lời cho truy vấn
- Ba bước kiểm tra đầu tiên:
  1. Mở Panel Errors trên Dashboard để kiểm tra tỷ lệ lỗi và breakdown theo `error_type` cùng `tool_success_rate_pct`.
  2. Tìm log line `request_failed` trong `data/logs.jsonl` để xem chi tiết exception message (`payload.detail`) và `correlation_id`.
  3. Tìm trace trên Langfuse theo `correlation_id` để kiểm tra span gặp lỗi (ví dụ span `retrieve` timeout hoặc `generation` fail).
- Mitigation tạm thời: Chuyển hướng traffic sang mô hình fallback, bypass bước retrieval sang câu trả lời mặc định an toàn nếu vector DB sập.
- Owner: oncall-engineer

## Alert 3

- Tên: CostSpike
- Severity: warning (P2)
- Duration: 10m
- Kênh thông báo: Slack (#llmops-finops)
- SLI/SLO liên quan: Guardrail `daily_cost_usd_max` (<= $2.5/ngày)
- Điều kiện và thời gian duy trì: Tổng chi phí tích lũy `cost_usd_total > 2.5` USD hoặc tốc độ tiêu tốn chi phí tăng vọt 4x kéo dài trên 10 phút
- Ảnh hưởng tới người dùng: Không ảnh hưởng trực tiếp tới độ trễ, nhưng đe dọa cạn kiệt ngân sách dự án và vi phạm guardrails FinOps
- Ba bước kiểm tra đầu tiên:
  1. Mở Panel Cost và Tokens trên Dashboard để xác định chi phí tăng do `tokens_in` (prompt quá dài) hay `tokens_out` (generation lặp vô tận / verbose).
  2. Lọc các log `response_sent` có `cost_usd` cao bất thường trong `data/logs.jsonl`, trích xuất `correlation_id`.
  3. Mở Langfuse trace để kiểm tra prompt version đang active và số lượng tokens được tạo ra từ generation span.
- Mitigation tạm thời: Rollback prompt về version baseline gọn hơn, hoặc siết chặt `max_tokens` của LLM generation trong cấu hình.
- Owner: finops-lead
