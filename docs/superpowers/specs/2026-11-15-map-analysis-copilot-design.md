# Map Analysis Copilot: agent và knowledge base source of truth

## 1. Mục tiêu

Xây dựng một agent hội thoại trong TideAware để người dùng:

- hỏi và hiểu các lớp dữ liệu SAR đang hiển thị;
- truy vấn scene theo thời gian, khu vực, band và trạng thái xử lý bằng ngôn ngữ tự nhiên;
- điều khiển những thao tác bản đồ an toàn như đổi HHHH/HVHV/RGB, bật/tắt lớp, chọn scene và mở thống kê;
- đọc kết quả analytics thật từ backend và giải thích kèm nguồn, scene ID, band, thời gian và trạng thái dữ liệu.

Agent không tự phân loại rừng ngập mặn, không tự kết luận mất rừng và không thay thế các phép tính raster. Candidate change vẫn chỉ là vùng cần kiểm chứng.

## 2. Phạm vi MVP

### Có trong MVP

1. Copilot dạng sidebar trên desktop; có thể mở bằng nút bong bóng ở màn hình hẹp.
2. Hỏi đáp về scene đang chọn, lớp hiện tại, HHHH/HVHV, dB, mask, nodata, AOI và footprint.
3. Truy vấn timeline và bộ lọc scene.
4. Action có kiểm soát:
   - đổi band `HHHH`, `HVHV`, `COMPOSITE`;
   - bật/tắt basemap, AOI, raster radar;
   - chọn scene trong timeline;
   - mở region statistics, profile hoặc pixel inspector.
5. Trích provenance trong mỗi câu trả lời.
6. Knowledge base phiên bản hóa từ tài liệu NASA/JPL và ASF.
7. Live context lấy từ backend API, không nhúng toàn bộ HDF5/raster vào prompt.

### Chưa có trong MVP

- agent tự chạy change detection không cần người dùng xác nhận;
- comparison/change-detection action trong chatbot; comparison vẫn có thể được dùng từ UI hiện hữu ở ngoài copilot;
- agent tự gắn nhãn mất rừng/phá rừng;
- agent tự thu thập dữ liệu thực địa hoặc gửi báo cáo ra bên ngoài;
- model phân loại rừng ngập mặn;
- trả lời dựa trên nguồn web không nằm trong allowlist.

## 3. Nguyên tắc source of truth

Agent dùng bốn lớp nguồn, theo thứ tự ưu tiên:

### Lớp A — Product truth

Định nghĩa khoa học và cấu trúc sản phẩm lấy từ:

- [NASA/JPL NISAR Level-2 GCOV Product Specification](https://cumulus.asf.earthdatacloud.nasa.gov/PUBLIC/DATA/NISAR/NISAR_D-102274_RevF_NASA_SDS_Product_Specification_L2_GCOV_w-esigs.pdf)
- [ASF GCOV Data User Guide](https://hyp3-docs.asf.alaska.edu/nisar-docs/gcov/)
- [ASF NISAR HDF5 Data Format](https://nisar-docs-test.asf.alaska.edu/data-format)
- [ASF QGIS/NISAR visualization guidance](https://hyp3-docs.asf.alaska.edu/nisar-docs/using-qgis/)

Đây là nguồn để giải thích HHHH/HVHV, covariance terms, gamma-naught power, RTC, mask, number of looks, frequency A/B, pixel spacing và cách đọc HDF5.

### Lớp B — Catalog truth

Metadata scene lấy từ ASF Search API và NASA CMR, gồm scene ID, thời gian, footprint, track/orbit/frame, collection, processing level và các liên kết dữ liệu.

- [ASF public Search API](https://asf.alaska.edu/services/)
- [ASF Search API manual](https://docs.asf.alaska.edu/api/cookbook/)
- [NASA CMR Search API](https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html)

CMR hỗ trợ tìm granule theo polygon, thời gian, collection, orbit và paging; vì vậy agent chỉ được lấy catalog qua backend đã chuẩn hóa, không tự gọi URL tùy ý từ trình duyệt.

### Lớp C — Scene truth

Giá trị cụ thể của scene phải lấy từ HDF5 hoặc GeoTIFF đã georeference:

- band và frequency thực tế;
- CRS, transform, resolution;
- nodata và mask;
- valid coverage;
- power, dB, histogram, percentile;
- pixel/profile/region statistics.

Nếu metadata tài liệu nói một quy tắc chung nhưng raster scene có attribute cụ thể, scene metadata được ưu tiên cho câu trả lời về scene đó.

### Lớp D — Product policy truth

Các quy tắc của TideAware được lưu trong code/config có version:

- candidate change không đồng nghĩa mất rừng;
- tide `UNKNOWN` nếu chưa có nguồn xác thực;
- rừng ngập mặn và bất thường tắt khi chưa có model thật;
- styling không làm thay đổi giá trị phân tích;
- nodata không chuyển thành số 0.

## 4. Knowledge base

### 4.1. Cấu trúc tài liệu

Mỗi tài liệu được lưu dưới dạng bản ghi có metadata:

```json
{
  "documentId": "asf-gcov-guide",
  "title": "Geocoded Polarimetric Covariance (GCOV)",
  "authority": "ASF / NASA",
  "canonicalUrl": "https://hyp3-docs.asf.alaska.edu/nisar-docs/gcov/",
  "documentVersion": "2026-06-xx",
  "retrievedAt": "2026-11-15T00:00:00Z",
  "status": "approved",
  "topics": ["GCOV", "HHHH", "HVHV", "mask", "pixel-spacing"],
  "contentHash": "sha256:..."
}
```

Mỗi chunk phải giữ:

- tiêu đề section;
- trang hoặc anchor;
- đoạn văn nguồn;
- URL canonical;
- version/retrievedAt;
- authority;
- danh sách claim mà chunk hỗ trợ.

Không đưa screenshot Vertex hoặc câu trả lời do LLM tạo trước đó vào knowledge base chuẩn.

### 4.4. Quy trình snapshot và phê duyệt nguồn

`knowledge/sources.json` chỉ là allowlist, không phải nội dung đã được index. Mỗi tài liệu phải đi qua quy trình:

1. chỉ tải từ canonical URL trong allowlist, hoặc được đặt thủ công trong `knowledge/documents/`;
2. lưu snapshot bất biến cùng `retrievedAt`, URL, version và SHA-256;
3. chạy kiểm tra checksum, metadata và nguồn;
4. được review/đánh dấu `approved`;
5. mới được `index_knowledge.py` đưa vào index.

Không fetch URL do LLM đề xuất. Citation luôn trỏ về canonical URL và snapshot/anchor đã được duyệt.

### 4.2. Claim registry

Tạo registry cho các phát biểu quan trọng, ví dụ:

```json
{
  "claimId": "gcov-diagonal-terms",
  "statement": "HHHH và HVHV là các diagonal covariance terms thực, mô tả cường độ backscatter theo polarization.",
  "sourceDocumentId": "asf-gcov-guide",
  "sourceAnchor": "data-layers/geocoded-polarimetric-covariance-terms",
  "authority": "ASF/NASA",
  "allowedAnswerTypes": ["explanation", "tooltip"],
  "reviewStatus": "approved"
}
```

Agent chỉ được dùng claim đã `approved`. Nếu không có claim hoặc live tool tương ứng, agent phải trả lời “chưa có dữ liệu đủ để kết luận”.

### 4.3. Retrieval

MVP có thể dùng hybrid retrieval:

- full-text/BM25 cho tên dataset, đường dẫn HDF5, scene metadata;
- vector retrieval cho câu hỏi diễn giải;
- metadata filter bắt buộc theo `authority`, `status`, `topic` và `documentVersion`.

Không dùng vector search để trả lời giá trị pixel, diện tích hoặc thời gian scene. Các giá trị đó luôn phải đến từ live tools.

## 5. Agent architecture

```text
Map UI / Chat sidebar
        |
        v
POST /api/v1/copilot/chat
        |
        +--> intent + permission gate
        +--> retrieve approved knowledge chunks
        +--> call read-only live tools
        +--> validate structured result
        +--> LLM composes answer + citations
        |
        v
answer, citations, actions, provenance, uncertainty
```

### 5.1. Backend components

Tách thành các module:

- `api/copilot.py`: request/response, conversation, streaming output;
- `api/copilot_tools.py`: tool schemas và permission checks;
- `api/copilot_sources.py`: source registry và citation mapping;
- `api/knowledge_base.py`: indexing, retrieval, document versions;
- `api/copilot_policy.py`: claim policy, uncertainty và prohibited claims;
- `api/copilot_audit.py`: lưu tool calls, source IDs, latency và answer version.

MVP dùng OpenRouter qua API tương thích OpenAI. Interface nội bộ vẫn giữ để test bằng mock và có thể thay provider sau này:

```python
class LlmProvider(Protocol):
    async def stream(self, messages, tools, response_schema) -> AsyncIterator[str]: ...
```

Adapter production dùng `POST https://openrouter.ai/api/v1/chat/completions`, Bearer token và các trường `model`, `messages`, `tools`, `tool_choice`, `stream`. Cấu hình chỉ đọc ở backend: `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `OPENROUTER_BASE_URL`, tùy chọn `OPENROUTER_SITE_URL` và `OPENROUTER_SITE_NAME`. App tự thực thi tool call rồi gửi `tool` result lại cho OpenRouter; model không được gọi tool nội bộ trực tiếp. Không dùng OpenRouter server tools/web search cho MVP vì mọi knowledge phải qua allowlist và mọi scene value phải qua backend TideAware.

Do hỗ trợ structured output/strict schema thay đổi theo model/provider, mọi tool call và final answer vẫn phải validate bằng Pydantic ở backend; `response_format` chỉ là tối ưu tùy model, không phải hàng rào an toàn.

## 6. Live tools bắt buộc

Các tool chỉ đọc, trả JSON có schema cố định:

### `get_current_map_context`

Trả về scene, band, layer visibility, AOI, viewport và thời điểm context.

### `search_scenes`

Nhận filter đã validate:

```json
{
  "startTime": "2026-06-01T00:00:00Z",
  "endTime": "2026-10-31T23:59:59Z",
  "bands": ["HHHH", "HVHV"],
  "track": 155,
  "aoi": "<GeoJSON Polygon>"
}
```

### `get_scene_metadata`

Trả catalog metadata và metadata raster thật, bao gồm CRS, resolution, bands, mask, source URL, cache status và freshness.

### `get_radar_profile`

Trả profile HHHH/HVHV theo chiều dài raster, đơn vị dB, valid count và statistics.

### `get_region_stats`

Trả valid coverage, min/max, mean, median, P10/P90, histogram và diện tích hợp lệ.

### `get_pixel_values`

Nhận lon/lat WGS84, trả power, dB, mask, nodata, row/column, scene và source.

### `explain_layer`

Kết hợp layer ID với claim registry, không tự suy luận từ màu sắc.

## 7. Action tools có kiểm soát

Action phải được frontend validate trước khi thực hiện:

```json
{
  "action": "set_radar_band",
  "arguments": { "band": "HVHV" },
  "requiresConfirmation": false,
  "undoable": true
}
```

MVP chỉ cho phép:

- `set_radar_band`;
- `toggle_layer`;
- `select_scene`;
- `set_timeline_index`;
- `open_region_stats`;
- `open_pixel_inspector`;

Không cho phép agent tự:

- xóa cache;
- sửa AOI vĩnh viễn;
- tải dữ liệu ra bên ngoài;
- gửi email/báo cáo;
- thay đổi ngưỡng change detection;
- gọi endpoint tùy ý;
- truy cập Earthdata token.

## 8. Chuẩn citation trong câu trả lời

Mỗi câu trả lời có tối đa ba loại citation:

### Citation tài liệu

```text
[ASF GCOV Guide, Data Layers]
```

### Citation scene

```text
Scene: NISAR_L2_PR_GCOV_034_047...
Band: HVHV · Frequency A
Acquired: 2026-10-27 11:23:21 UTC
Source: cached GeoTIFF from ASF/Harmony
```

### Citation analytics

```text
Processed by: TideAware analytics v1
Raster hash: sha256:...
Valid coverage: 87.4%
```

Nếu câu trả lời có phần diễn giải và phần đo lường, phải tách hai phần rõ ràng:

```text
Theo tài liệu ASF: HVHV là cross-polarized covariance term.
Với scene hiện tại: median = -17.4 dB, valid coverage = 87.4%.
```

## 9. Guardrails và uncertainty

Agent phải dùng các trạng thái sau:

- `KNOWN`: có live data hoặc approved claim;
- `PARTIAL`: có dữ liệu nhưng coverage/mask không đầy đủ;
- `UNKNOWN`: không có nguồn xác thực;
- `BLOCKED`: tool hoặc compatibility gate chặn thao tác;
- `INTERPRETATION`: diễn giải khoa học, không phải đo lường trực tiếp.

Các câu hỏi về candidate change phải dùng mẫu:

> Đây là vùng thay đổi ứng viên vượt ngưỡng phân tích, cần kiểm chứng thêm; chưa thể gọi là mất rừng hoặc phá rừng.

Nếu user hỏi “có phải mất rừng không?”, agent phải trả lời rằng app hiện chưa có model phân loại rừng ngập mặn/ground truth nên không thể kết luận.

## 10. Conversation memory

Chỉ lưu:

- câu hỏi gần đây;
- scene/band/AOI người dùng đang chọn;
- các action đã thực hiện;
- source IDs và analytics request IDs.

Không lưu Earthdata token, toàn bộ HDF5, hay dữ liệu pixel thô ngoài thời gian cần thiết.

Session context có TTL ngắn và phải có `contextVersion` để tránh agent dùng scene cũ sau khi timeline thay đổi.

## 11. API contract đề xuất

### Request

```http
POST /api/v1/copilot/chat
Accept: text/event-stream
Content-Type: application/json
```

```json
{
  "conversationId": "conv_123",
  "message": "HVHV này có ý nghĩa gì và vùng đang xem có bao nhiêu pixel hợp lệ?",
  "mapContext": {
    "sceneId": "...",
    "band": "HVHV",
    "aoi": "<GeoJSON Polygon>",
    "layerState": {"radar": true, "basemap": true}
  }
}
```

### Stream events

```text
event: status
data: {"stage":"retrieving_sources"}

event: tool
data: {"name":"get_region_stats","status":"started"}

event: token
data: {"text":"HVHV là..."}

event: citation
data: {"sourceId":"asf-gcov-guide","anchor":"..."}

event: done
data: {"answerId":"ans_123","status":"KNOWN"}
```

### Response object cuối

```json
{
  "answer": "...",
  "status": "KNOWN",
  "citations": [],
  "provenance": [],
  "actions": [],
  "warnings": [],
  "latencyMs": 842
}
```

## 12. UI/UX

### Sidebar desktop

- mở rộng/thu gọn độc lập với sidebar chi tiết;
- có context chip: scene, band, thời gian;
- câu trả lời ngắn trước, phần “Chi tiết nguồn” mở rộng sau;
- action hiển thị như nút có thể hoàn tác;
- tool đang chạy hiển thị trạng thái, không để người dùng tưởng agent bị treo.

### Bong bóng chat

- dùng ở màn hình hẹp;
- mở thành drawer;
- không che control map khi đang xem ảnh;
- giữ câu hỏi gần nhất nhưng không tự chạy lại action sau reload.

## 13. Cache và hiệu năng

- Cache retrieval theo `query + knowledgeVersion`.
- Cache live tool theo `sceneId + band + AOI hash + analyticsVersion`.
- Không gửi HDF5/raster vào prompt; chỉ gửi summaries và IDs.
- Deduplicate các tool call trùng trong cùng một lượt.
- Stream status và token ngay khi có kết quả.
- Hủy tool call cũ khi scene/timeline thay đổi.
- Giới hạn context: scene hiện tại, tối đa N scene liên quan và các nguồn cần thiết.

Mục tiêu MVP:

- first status event < 300 ms khi backend sẵn sàng;
- câu trả lời metadata/cache < 2 s;
- câu trả lời cần analytics < 5 s khi analytics đã cache;
- không chặn map render trong lúc agent đang trả lời.

## 14. Audit và observability

Ghi log không chứa token:

- conversation ID;
- user/session ID đã hash;
- source IDs/version;
- tool calls và latency;
- prompt/knowledge version;
- answer status;
- action được chấp nhận/từ chối;
- lỗi parser/schema;
- cache hit/miss.

Dashboard cần phân biệt:

- LLM latency;
- retrieval latency;
- live analytics latency;
- ASF/CMR latency;
- frontend render latency.

## 15. Kiểm thử

### Source and retrieval tests

- câu hỏi HHHH/HVHV lấy đúng chunk ASF/NASA;
- nguồn bị `deprecated` không được retrieve;
- citation có URL/anchor/version;
- câu hỏi ngoài knowledge trả `UNKNOWN`.

### Tool tests

- scene không tồn tại;
- raster chưa cache;
- band không có trong scene;
- pixel nodata;
- AOI ngoài footprint;
- stale context sau khi đổi timeline;
- comparison request bị từ chối vì comparison action chưa nằm trong copilot MVP.

### Safety tests

- agent không gọi HHHV/HVHV nhầm;
- không gọi candidate change là mất rừng;
- không biến màu map thành giá trị dB;
- không bịa tide;
- không lộ token hoặc URL có credential.

### UI tests

- streaming answer;
- stop/cancel;
- retry;
- action undo;
- reload không tự chạy lại action;
- sidebar không làm mất plot radar.

## 16. Các phase triển khai

### Phase 0 — Source registry và policy

- chốt allowlist NASA/JPL, ASF, CMR;
- tạo document registry, claim registry và versioning;
- viết policy `KNOWN/PARTIAL/UNKNOWN/BLOCKED`;
- không thêm LLM vào UI.

### Phase 1 — Read-only copilot

- backend `/api/v1/copilot/chat`;
- tool metadata/profile/stats/pixel;
- retrieval tài liệu chuẩn;
- trả lời có citation và provenance;
- sidebar chỉ đọc.

### Phase 2 — Map actions

- đổi band;
- bật/tắt lớp;
- chọn scene/timeline;
- mở stats/profile/pixel inspector;
- undo và action audit.

### Phase 3 — Comparison assistant (deferred)

Tạm hoãn toàn bộ comparison action/tool trong copilot. Khi mở lại phase này mới bổ sung compatibility, delta và candidate change; các chức năng đó không được xuất hiện trong tool schema hoặc UI action allowlist của MVP.

### Phase 4 — Evaluation và hardening

- bộ câu hỏi chuẩn bằng tiếng Việt;
- kiểm tra citation accuracy;
- đo hallucination/unsupported claim rate;
- load test streaming;
- security review token và prompt injection;
- rollout sau feature flag.

## 17. Acceptance criteria

- Agent trả lời đúng nguồn cho HHHH/HVHV và dB.
- Mọi số liệu scene đều có scene ID, band, thời gian và source.
- Không có số liệu pixel/histogram nào do LLM tự tạo.
- Câu hỏi không đủ dữ liệu trả `UNKNOWN` thay vì suy đoán.
- Agent điều khiển được band/timeline/layer trong phạm vi action allowlist.
- Agent không thể truy cập Earthdata token.
- Candidate change luôn được mô tả là ứng viên cần kiểm chứng.
- Reload, cache miss, nodata và backend error đều hiển thị rõ.
- Tài liệu đã hết hiệu lực không được retrieve.
- Có thể kiểm tra lại câu trả lời từ audit log.

## 18. Quyết định cần người dùng duyệt trước khi triển khai

Các quyết định đã chốt: sidebar desktop + bong bóng mobile; OpenRouter production với mock provider cho test; action bản đồ an toàn thực hiện ngay và undo được; knowledge base filesystem versioned; citation gồm canonical link, snapshot/anchor và provenance scene.

## 19. Quyết định đã chốt

### Action policy

Đã chọn phương án A:

- Action UI an toàn được thực hiện ngay khi agent nhận diện rõ ý định.
- Mọi action UI phải undo được hoặc có trạng thái khôi phục.
- Action thay đổi dữ liệu, chạy comparison/change detection, tải dữ liệu hoặc tạo kết quả mới không nằm trong chatbot MVP.
- Nếu câu lệnh mơ hồ, agent hỏi lại thay vì tự chọn scene hoặc band.

Ví dụ được chạy ngay:

- “Chuyển sang HVHV.”
- “Ẩn bản đồ nền.”
- “Mở thống kê khu vực.”

Các yêu cầu comparison/change detection phải được trả lời là chức năng chưa được bật trong copilot, không được tự tạo confirmation action hoặc khởi chạy job.

Quyết định này nhằm giữ cảm giác chatbot nhanh và tự nhiên, nhưng tránh việc agent tự khởi động các tác vụ nặng hoặc tạo kết quả phân tích mà người dùng chưa yêu cầu rõ.

## 20. Chốt lại theo mục tiêu chatbot

### 20.1. Chatbot là sản phẩm chính

Knowledge base và agent runtime chỉ phục vụ ba trải nghiệm người dùng nhìn thấy trực tiếp:

1. Hỏi “lớp này là gì?” và nhận giải thích có nguồn.
2. Hỏi “scene hiện tại có gì?” và nhận số liệu thật từ live tools.
3. Nói một câu tự nhiên để điều khiển bản đồ, ví dụ “chuyển sang HVHV”, “chọn scene tháng 10” hoặc “mở thống kê”.

Không xây knowledge base như một kho số liệu scene. Scene data luôn đến từ backend analytics/catalog.

### 20.2. Context thống nhất của bản đồ

Copilot API nhận một `mapContext` duy nhất ở mỗi lượt chat:

```json
{
  "sceneId": "NISAR_L2_PR_GCOV_...",
  "sceneDate": "2026-10-27T11:23:21Z",
  "band": "HVHV",
  "aoi": "<GeoJSON Polygon>",
  "layerState": {
    "radar": true,
    "basemap": true,
    "aoi": true,
    "candidateChange": false
  },
  "timelineIndex": 20,
  "timelineCount": 21,
  "rasterStyle": "heatmap",
  "catalogMode": "earthdata",
  "assetMode": "cached",
  "dataStatus": "ready",
  "contextVersion": 12
}
```

`contextVersion` tăng mỗi khi scene, band, AOI hoặc layer state thay đổi. Tool result có context version cũ không được dùng để trả lời hoặc thực hiện action mới.

### 20.3. Phân biệt nguồn dữ liệu

Mọi live tool response phải có:

```json
{
  "catalogMode": "earthdata",
  "assetMode": "cached",
  "dataStatus": "ready",
  "source": "cached-geotiff",
  "freshness": "2026-11-15T02:10:00Z",
  "sceneId": "...",
  "cacheKey": "..."
}
```

Không gộp nguồn catalog với trạng thái asset. Các giá trị hợp lệ là:

- `catalogMode`: `earthdata`, `demo`, `error`;
- `assetMode`: `live`, `cached`, `unavailable`;
- `dataStatus`: `ready`, `partial`, `unknown`, `error`.

Một scene có thể có `catalogMode=earthdata` và `assetMode=cached`. Nếu catalog là `demo`, agent phải nói rõ dữ liệu mô phỏng; nếu nguồn lỗi, agent trả lỗi thay vì fallback ngầm sang demo. `assetMode=unavailable` không được tạo số liệu raster.

### 20.4. Tách live tools và UI commands

#### Live tools, chỉ đọc dữ liệu

- `get_current_map_context`;
- `search_scenes`;
- `get_scene_metadata`;
- `get_radar_profile`;
- `get_region_stats`;
- `get_pixel_values`;
- `explain_layer`.

#### UI commands, chỉ thay đổi trạng thái frontend

- `set_radar_band`;
- `toggle_layer`;
- `select_scene`;
- `set_timeline_index`;
- `open_region_stats`;
- `open_pixel_inspector`;

UI command không được gọi endpoint tùy ý. Frontend kiểm tra schema, allowlist, `contextVersion` và khả năng undo trước khi thực thi. Backend không chịu trách nhiệm thay đổi DOM hoặc MapLibre state.

### 20.5. Quy tắc trả lời khi thiếu dữ liệu

Agent phải dùng các trạng thái sau, không thay bằng câu suy đoán:

- `KNOWN`: có approved claim hoặc live result hợp lệ;
- `PARTIAL`: có dữ liệu nhưng thiếu coverage hoặc bị mask;
- `UNKNOWN`: chưa có nguồn xác thực;
- `BLOCKED`: policy hoặc compatibility gate chặn;
- `ERROR`: nguồn hoặc tool lỗi.

Các tình huống bắt buộc trả `UNKNOWN`, `PARTIAL` hoặc `BLOCKED`:

- scene chưa có GeoTIFF cache;
- band không tồn tại trong scene;
- pixel là nodata;
- AOI không giao raster;
- chưa có model rừng ngập mặn;
- chưa có nguồn tide đã xác thực;
- candidate change chưa hoàn tất;
- dữ liệu chỉ là demo.

Agent không được đổi nodata thành `0`, không được tự tạo dB, không được suy ra số liệu từ màu bản đồ và không được biến candidate change thành kết luận mất rừng.

### 20.6. Citation và provenance bắt buộc

Mỗi câu trả lời có số liệu phải tách thành hai phần:

```text
Kiến thức nền:
Theo ASF GCOV Guide, HVHV là cross-polarized covariance term.

Dữ liệu scene:
Scene: NISAR_L2_PR_GCOV_...
Band: HVHV
Median: -17.4 dB
Valid coverage: 87.4%
Source: cached GeoTIFF
```

Citation tài liệu phải có `sourceDocumentId`, URL canonical, version và anchor. Citation scene phải có scene ID, band, acquisition time, source và processing/cache version.

### 20.7. Streaming trạng thái

Copilot API dùng SSE. Trước khi có câu trả lời cuối, frontend hiển thị từng bước:

```text
Đang đọc context bản đồ...
Đang tìm nguồn giải thích...
Đang đọc metadata scene...
Đang lấy profile HVHV...
Đang tính thống kê AOI...
Đang hoàn tất...
```

Mỗi bước có thể bị hủy khi user đổi scene hoặc band. UI không hiển thị spinner vô hạn; sau timeout phải trả trạng thái `ERROR` kèm request ID.

### 20.8. Ranh giới cứng của LLM

LLM không được:

- đọc hoặc nhìn thấy Earthdata token;
- tự gọi URL, ASF API hoặc CMR;
- tính raster, dB, histogram hoặc diện tích;
- tự tạo scene ID, tọa độ hoặc timestamp;
- tự chạy comparison/change detection hoặc task nặng;
- tự kết luận rừng ngập mặn, mất rừng hoặc phá rừng;
- dùng nội dung metadata ngoài allowlist làm instruction.

LLM chỉ chọn intent/tool từ schema, diễn giải kết quả đã validate và tạo câu trả lời có citation.

## 21. Quyết định phạm vi MVP

Đã chốt:

- MVP phục vụ nhóm nội bộ.
- Một user/session tại một thời điểm.
- Chưa cần login, multi-user permission hoặc phân quyền theo scene/AOI.
- Conversation memory chỉ tồn tại trong session hiện tại.
- Cache và audit gắn với session/context hiện tại, không xây hệ thống chia sẻ dữ liệu giữa người dùng ở giai đoạn này.
- Earthdata token và LLM provider key vẫn chỉ nằm ở backend, không gửi xuống browser hoặc prompt.

Khi mở rộng cho nhiều người dùng, cần bổ sung authentication, authorization, tách cache theo user/project, retention policy và audit access trước khi bật production.

## 22. Chốt kỹ thuật bổ sung sau review

### 22.1. Provider OpenRouter

Production provider là OpenRouter, dùng endpoint tương thích OpenAI:

- `OPENROUTER_API_KEY` chỉ ở backend;
- `OPENROUTER_MODEL` bắt buộc khi bật copilot;
- `OPENROUTER_BASE_URL` mặc định `https://openrouter.ai/api/v1`;
- `OPENROUTER_SITE_URL` và `OPENROUTER_SITE_NAME` là header attribution tùy chọn.

Backend gửi `stream=true`, `tools` và `tool_choice`; tool được thực thi trong TideAware rồi kết quả mới được gửi lại cho model. Không bật server tools của OpenRouter, web search hoặc web fetch trong MVP. Khi thiếu API key, copilot chuyển sang `disabled` và map/analytics vẫn hoạt động độc lập.

### 22.2. AOI registry và session

Frontend chỉ gửi `aoiId` và `aoiHash`. Backend giữ GeoJSON trong registry theo session, kiểm tra hash trước khi gọi analytics và không đưa polygon đầy đủ vào system prompt. `conversationId` được bind vào session hiện tại, có TTL và không cho phép client đọc lịch sử session khác.

### 22.3. Giới hạn runtime

Mỗi lượt chat có tối đa 4 vòng tool, 6 tool call, giới hạn độ dài message/answer, timeout tổng và cơ chế hủy khi client đổi scene/band. Đây là giới hạn bắt buộc để OpenRouter không tạo vòng lặp hoặc làm chậm map.

### 22.4. Comparison bị loại khỏi chatbot MVP

Copilot không có `get_comparison_status`, `open_comparison`, `start_comparison` hoặc action tương đương. Khi người dùng yêu cầu so sánh/change detection, agent trả `BLOCKED` với giải thích ngắn rằng chức năng chưa bật trong copilot; không tạo confirmation action và không khởi chạy job. Các API comparison hiện hữu của app không bị xóa và vẫn có thể được mở rộng ở phase sau.

### 22.5. Tiêu chuẩn kiểm thử tối thiểu

- Frontend dùng Vitest + React Testing Library; E2E dùng Playwright với mock provider.
- 100% câu trả lời có số liệu phải có provenance.
- 100% câu trả lời từ demo phải ghi rõ demo.
- 100% nodata không được sinh số liệu thay thế.
- Không lộ token, không gọi URL tùy ý, không có comparison tool/action trong MVP.

OpenRouter API contract được tham chiếu từ [Chat Completions API](https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request?explorer=true) và [Tool Calling guide](https://openrouter.ai/blog/tutorials/tool-calling/). Server tools là một capability riêng và không nằm trong allowlist của TideAware ([OpenRouter Server Tools](https://openrouter.ai/docs/guides/features/server-tools/overview)).
