# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** [Tên sinh viên]
**Nhóm:** [Tên nhóm]
**Ngày:** [Ngày nộp]

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> Điểm cosine cao nghĩa là hai vector embedding gần như cùng hướng, tức mô hình nhúng coi hai đoạn văn bản là **gần nghĩa nhau**: cùng chủ đề, cùng ý, hoặc cùng loại nội dung — bất kể độ dài và cách diễn đạt khác nhau.

**Ví dụ có độ tương tự CAO:**
- Câu A: Người mua được đổi trả hàng trong vòng 7 ngày kể từ ngày nhận hàng.
- Câu B: Thời hạn đổi trả cho người mua là 7 ngày sau khi nhận hàng.
- Tại sao tương đồng: hai câu cùng nói về một quy định (đối tượng: người mua; thời hạn: 7 ngày; mốc tính: ngày nhận hàng), chỉ khác cách diễn đạt.

**Ví dụ có độ tương tự THẤP:**
- Câu A: Người mua được đổi trả hàng trong vòng 7 ngày kể từ ngày nhận hàng.
- Câu B: Hôm nay tôi ăn phở bò ở quán gần nhà.
- Tại sao khác: hai câu thuộc hai chủ đề hoàn toàn không liên quan (chính sách đổi trả vs. việc ăn uống cá nhân), không chia sẻ khái niệm nào.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> Cosine chỉ đo **hướng** của vector và bỏ qua **độ lớn**, nên một câu ngắn và một đoạn văn dài cùng chủ đề vẫn được coi là gần nhau. Euclid đo khoảng cách tuyệt đối nên bị "phạt" bởi độ dài vector — vốn tương quan với độ dài văn bản (số từ) nhiều hơn là với ngữ nghĩa. Vì vậy cosine phản ánh độ tương đồng ngữ nghĩa ổn định hơn.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> Phép tính:
> `số chunk = ceil((10000 - 50) / (500 - 50)) = ceil(9950 / 450) = ceil(22.11) = 23`
> **Đáp án: 23 chunks.**
>
> Đã kiểm chứng bằng chính `FixedSizeChunker(chunk_size=500, overlap=50).chunk("a" * 10000)` → trả về **23** chunk, khớp công thức.

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> `ceil((10000 - 100) / (500 - 100)) = ceil(9900 / 400) = ceil(24.75) = 25` → tăng từ **23 lên 25 chunk**, vì bước nhảy `chunk_size - overlap` giảm từ 450 xuống 400 nên cần nhiều bước hơn để phủ hết tài liệu.
>
> Muốn tăng overlap để **không mất ngữ cảnh ở ranh giới chunk**: khi một câu/ý bị cắt ngang, phần còn lại vẫn xuất hiện trọn vẹn ở chunk kế bên, nên retrieval không bỏ sót thông tin. Đánh đổi: tốn thêm dung lượng lưu trữ và chi phí embed (nhiều chunk hơn, nội dung trùng lặp).

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> Dùng regex `re.split(r"(?<=[.!?])\s+", text.strip())` — lookbehind giữ dấu câu ở lại cuối câu trước, nên không mất `.`/`!`/`?` khi tách, và `\s+` bao luôn trường hợp `.\n`. Sau khi tách, tôi lọc bỏ câu rỗng/toàn khoảng trắng rồi nhóm tuần tự `max_sentences_per_chunk` câu bằng `range(0, len, step)`, ghép lại bằng `" ".join(...)` và `strip()` từng chunk.
> Edge case: văn bản rỗng hoặc chỉ có khoảng trắng → trả `[]`; `max_sentences_per_chunk` đã được `max(1, ...)` ở `__init__` nên không thể chia cho 0 bước.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> `chunk` chỉ là wrapper gọi `_split(text, self.separators)`. **Base case** của `_split`: nếu `len(current_text) <= chunk_size` thì trả nguyên đoạn đó, không cắt nữa.
> Ở mỗi tầng, tôi quét danh sách separator theo thứ tự ưu tiên và chọn **separator đầu tiên thực sự có mặt** trong văn bản (gặp `""` thì dừng và cắt cứng theo `chunk_size` — đây là đường thoát khi hết separator).
> Điểm quan trọng: khi `split`, tôi **gắn separator trở lại cuối mỗi mảnh** (`part + separator`) thay vì vứt đi, để lúc ghép lại không mất dấu câu và khoảng trắng. Sau đó tôi **gom tham lam (greedy merge)**: cộng dần các mảnh vào một buffer cho tới khi vượt `chunk_size` thì chốt chunk. Mảnh đơn lẻ nào vẫn lớn hơn `chunk_size` thì **đệ quy với các separator còn lại** (`rest`), và vì mỗi tầng đệ quy bỏ đi ít nhất một separator nên thuật toán luôn kết thúc.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> Lưu trữ **trong bộ nhớ**: `_make_record` copy `metadata` của `Document` (không sửa dict gốc của người gọi) và thêm khoá `doc_id` để phục vụ xoá/lọc sau này, rồi embed nội dung và lưu thành dict có `content`, `embedding`, `metadata`, `id`. `add_documents` append từng record và tăng `_next_index` để id không trùng.
> `search` embed câu truy vấn, chấm điểm từng record bằng **tích vô hướng** `_dot(query_embedding, record_embedding)`, sort **giảm dần** theo `score` rồi cắt `top_k` (làm trong helper `_search_records` để `search` và `search_with_filter` dùng chung một logic xếp hạng). Vì `MockEmbedder` chuẩn hoá vector về norm 1 (`value / norm` ở cuối `__call__`), tích vô hướng ở đây **chính bằng** cosine similarity.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> Lọc **trước** rồi mới tìm kiếm: dựng danh sách con gồm các record thoả **mọi** cặp key/value của `metadata_filter` (dùng `all(...)` nên hỗ trợ lọc nhiều trường), rồi chạy `_search_records` trên danh sách đó. Nếu `metadata_filter` là `None`/rỗng thì bỏ qua bước lọc và trả kết quả giống hệt `search` — đúng như test `test_no_filter_returns_all_candidates` yêu cầu.
> `delete_document` dựng danh sách mới chỉ giữ các record có `metadata["doc_id"] != doc_id`, so sánh độ dài trước/sau để biết đã xoá được gì và trả `True`/`False` tương ứng.

> **Ghi chú về quyết định thiết kế (ChromaDB):** scaffold có sẵn nhánh thử `import chromadb` và cờ `_use_chroma`. Tôi **cố ý không kích hoạt** nhánh này mà dùng thuần in-memory, vì: (1) `chromadb` không có trong `requirements.txt` nên mặc định luôn rơi vào in-memory; (2) nếu bật ChromaDB, collection được đặt tên cố định và dùng chung trong một tiến trình, nên khi bộ test tạo lại store với cùng `collection_name` ở mỗi `setUp()` thì dữ liệu bị tích luỹ và `add` trùng `id` sẽ lỗi — tức bật ChromaDB sẽ làm hỏng chính bộ test được cung cấp. Ưu tiên một đường lưu trữ duy nhất, chạy đúng và kiểm chứng được.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> `__init__` chỉ lưu tham chiếu `self.store` và `self.llm_fn` (dependency injection để test có thể truyền LLM giả). Trong `answer`: gọi `store.search(question, top_k)` để lấy các chunk liên quan, đánh số và nối chúng thành khối `Context` dạng `[1] nội dung chunk...\n\n[2] ...`.
> Prompt gồm 3 phần: chỉ thị **"chỉ trả lời dựa trên context, nếu context không có thì nói không có"**, khối `Context`, rồi `Question`. Cách này giữ câu trả lời **có căn cứ (grounded)** và hạn chế LLM bịa, đồng thời số thứ tự `[n]` giúp truy vết câu trả lời về chunk nguồn. Cuối cùng trả về `self.llm_fn(prompt)`.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0 -- D:\VinUni\K4-L3B-Data-Foundations\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\VinUni\K4-L3B-Data-Foundations
plugins: anyio-4.15.1
collected 42 items

tests/test_solution.py::TestProjectStructure::test_root_main_entrypoint_exists PASSED
tests/test_solution.py::TestProjectStructure::test_src_package_exists PASSED
tests/test_solution.py::TestClassBasedInterfaces::test_chunker_classes_exist PASSED
tests/test_solution.py::TestClassBasedInterfaces::test_mock_embedder_exists PASSED
tests/test_solution.py::TestFixedSizeChunker::test_chunks_respect_size PASSED
tests/test_solution.py::TestFixedSizeChunker::test_correct_number_of_chunks_no_overlap PASSED
tests/test_solution.py::TestFixedSizeChunker::test_empty_text_returns_empty_list PASSED
tests/test_solution.py::TestFixedSizeChunker::test_no_overlap_no_shared_content PASSED
tests/test_solution.py::TestFixedSizeChunker::test_overlap_creates_shared_content PASSED
tests/test_solution.py::TestFixedSizeChunker::test_returns_list PASSED
tests/test_solution.py::TestFixedSizeChunker::test_single_chunk_if_text_shorter PASSED
tests/test_solution.py::TestSentenceChunker::test_chunks_are_strings PASSED
tests/test_solution.py::TestSentenceChunker::test_respects_max_sentences PASSED
tests/test_solution.py::TestSentenceChunker::test_returns_list PASSED
tests/test_solution.py::TestSentenceChunker::test_single_sentence_max_gives_many_chunks PASSED
tests/test_solution.py::TestRecursiveChunker::test_chunks_within_size_when_possible PASSED
tests/test_solution.py::TestRecursiveChunker::test_empty_separators_falls_back_gracefully PASSED
tests/test_solution.py::TestRecursiveChunker::test_handles_double_newline_separator PASSED
tests/test_solution.py::TestRecursiveChunker::test_returns_list PASSED
tests/test_solution.py::TestEmbeddingStore::test_add_documents_increases_size PASSED
tests/test_solution.py::TestEmbeddingStore::test_add_more_increases_further PASSED
tests/test_solution.py::TestEmbeddingStore::test_initial_size_is_zero PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_content_key PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_score_key PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_results_sorted_by_score_descending PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_returns_at_most_top_k PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_returns_list PASSED
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_non_empty PASSED
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_returns_string PASSED
tests/test_solution.py::TestComputeSimilarity::test_identical_vectors_return_1 PASSED
tests/test_solution.py::TestComputeSimilarity::test_opposite_vectors_return_minus_1 PASSED
tests/test_solution.py::TestComputeSimilarity::test_orthogonal_vectors_return_0 PASSED
tests/test_solution.py::TestComputeSimilarity::test_zero_vector_returns_0 PASSED
tests/test_solution.py::TestCompareChunkingStrategies::test_counts_are_positive PASSED
tests/test_solution.py::TestCompareChunkingStrategies::test_each_strategy_has_count_and_avg_length PASSED
tests/test_solution.py::TestCompareChunkingStrategies::test_returns_three_strategies PASSED
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_filter_by_department PASSED
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_no_filter_returns_all_candidates PASSED
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_returns_at_most_top_k PASSED
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_reduces_collection_size PASSED
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_false_for_nonexistent_doc PASSED
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_true_for_existing_doc PASSED

============================= 42 passed in 0.16s ==============================
```

**Số lượng bài test vượt qua (pass):** **42** / 42

### So sánh 3 chiến lược chia nhỏ (chạy thực tế bằng `ChunkingStrategyComparator`, `chunk_size=200`)

| Tài liệu | fixed_size (count / avg_length) | by_sentences (count / avg_length) | recursive (count / avg_length) |
|---|---|---|---|
| `chunking_experiment_report.md` (2.282 ký tự) | 12 / 190.2 | 5 / 454.6 | 19 / 119.9 |
| `vi_retrieval_notes.md` (1.667 ký tự) | 9 / 185.2 | 5 / 331.6 | 13 / 127.9 |

Nhận xét: `by_sentences` cho chunk dài nhất (giữ trọn câu nhưng vượt xa `chunk_size`); `recursive` bám sát `chunk_size` nhất (avg ≈ 120–128) nên chunk đều và mạch lạc hơn; `fixed_size` cắt đúng theo ký tự nên có thể cắt giữa câu.

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

> Chạy bằng `compute_similarity()` với embedder thật **`gemini-embedding-001`** (`EMBEDDING_PROVIDER=gemini` trong `.env`), không dùng `MockEmbedder` — vì mock băm chuỗi bằng MD5 nên điểm gần như ngẫu nhiên và không phản ánh ngữ nghĩa.

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | Con mèo đang ngủ trên ghế sofa. | Chú mèo nằm ngủ trên đi văng. | cao | **0.8980** | Đúng |
| 2 | Người mua được đổi trả trong 7 ngày. | Thời hạn đổi trả cho người mua là 7 ngày. | cao | **0.9536** | Đúng |
| 3 | Tôi thích ăn phở vào buổi sáng. | Vector store lưu trữ embedding để tìm kiếm tương đồng. | thấp | **0.5242** | Đúng |
| 4 | Python là ngôn ngữ lập trình bậc cao. | Python là một ngôn ngữ lập trình bậc cao. | cao (cao nhất) | **0.9952** | Đúng |
| 5 | Giá cổ phiếu giảm mạnh hôm nay. | Thị trường chứng khoán lao dốc. | cao | **0.8027** | Đúng |

Thứ tự thực tế: cặp 4 (0.9952) > cặp 2 (0.9536) > cặp 1 (0.8980) > cặp 5 (0.8027) > cặp 3 (0.5242).

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> Bất ngờ nhất là **cặp 3**: hai câu hoàn toàn không liên quan vẫn đạt **0.5242**, chứ không gần 0 như tôi tưởng. Điều này cho thấy `gemini-embedding-001` không trải điểm trên toàn dải [−1, 1] mà **nén vào một vùng cao**, nên không tồn tại ngưỡng tuyệt đối kiểu "cosine > 0.5 là giống nhau" — muốn đánh giá phải so sánh **tương đối** giữa các ứng viên trong cùng một corpus, đúng như cách `EmbeddingStore.search` xếp hạng rồi mới cắt `top_k`.
>
> Ngược lại, **cặp 5** gần như không chia sẻ từ khoá nào ("cổ phiếu / giảm mạnh" so với "chứng khoán / lao dốc") mà vẫn đạt **0.8027** — embedding nắm được quan hệ **đồng nghĩa ở mức khái niệm**, không phải trùng mặt chữ. Đây chính là lý do cosine similarity được ưu tiên cho text embedding: nó đo ý nghĩa, không đo từ vựng.
>
> Cặp 4 gần như trùng nhau cho **0.9952**, và cặp 1 (cùng nội dung, khác từ ngữ) chỉ thấp hơn chút ở **0.8980** — mô hình vẫn phân biệt được mức độ khác nhau rất nhỏ giữa "gần như y hệt" và "cùng ý nhưng diễn đạt khác".

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

> Bộ 5 câu hỏi lấy đúng từ `BENCHMARK_QUERIES` trong `bench.py` của nhóm (Finding Vinno), chạy trên corpus `data/warranty/` (6 tài liệu), `top_k=3`, lọc theo `metadata_filter` mà nhóm đã chốt cho từng câu.
>
> **Cấu hình chạy:** chiến lược **Heading/Section** (`chunk_size=600`, 121 chunk) trên `src/` của tôi; embedding `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (chạy offline, chọn vì quota free tier của Gemini embedding — 1000 request/ngày — đã hết); agent dùng `gemini-3.6-flash`. Chấm theo `docs/SCORING.md` ở **mức nội dung** (`gold_phrase` phải nằm trong chunk), không chấm theo `doc_id`.

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | Theo chính sách Hoàng Hà Mobile, khách hàng được đổi mới miễn phí trong thời gian nào? | `hoanghamobile-warranty-buyer#0` — tiêu đề tài liệu + phạm vi áp dụng | +0.6831 | **Không — 0/2** | *"Không có thông tin về thời gian cụ thể khách hàng được đổi mới miễn phí."* |
| 2 | Trong mô hình Seller Center, Nhà Bán có bao nhiêu ngày làm việc để xác nhận phương án xử lý yêu cầu đổi trả? | `tiki-seller-warranty-faq#27` — mục "8. Nhà Bán có thời gian bao lâu để xác nhận…" | +0.7738 | **Có (top-1) — 2/2** | *"Nhà Bán có **02 ngày làm việc** để xác nhận yêu cầu đổi, trả (áp dụng cho cả trường hợp không thu hồi và có thu hồi sản phẩm)."* |
| 3 | Nếu Nhà Bán không phản hồi, Tiki sẽ xử lý yêu cầu của Khách Hàng như thế nào? | `tiki-seller-warranty-faq#8` — mục "6. Nếu Nhà Bán không phản hồi…" | +0.8560 | **Có (top-1) — 2/2** | *"Tiki sẽ **hoàn tiền cho Khách Hàng**, không chịu trách nhiệm nếu Nhà Bán không/không thể thu hồi hàng; số tiền được **cấn trừ vào kỳ thanh toán tiếp theo** của Nhà Bán."* |
| 4 | Sản phẩm cần thỏa những điều kiện nào để được bảo hành miễn phí? | `shopee-warranty-buyer#1` — mục "1. Điều kiện bảo hành" | +0.8071 | **Có (top-1) — 2/2** | Liệt kê đủ 4 điều kiện: lỗi kỹ thuật do nhà sản xuất; còn trong thời hạn bảo hành; có hóa đơn điện tử hoặc mã đơn hàng; hàng điện gia dụng cần phiếu/tem bảo hành và tem niêm phong còn nguyên. |
| 5 | Thời gian bảo hành tối đa là bao lâu? | `tiki-seller-warranty-faq#7` — mục "5. Thời gian Nhà Bán cam kết bảo hành là bao lâu?" | +0.6531 | **Có (top-1) — 2/2** | *"Thời gian bảo hành tối đa do Nhà Bán cam kết là **không quá 30 ngày**, tính từ khi nhận hàng đến khi bảo hành xong, không tính thời gian vận chuyển."* |

**Tổng: 8/10 điểm · top-1 4/5 · MRR 0.800** (theo thang `docs/SCORING.md`: 2 điểm nếu chunk chứa đáp án ở top-1, 1 điểm nếu có trong top-3 nhưng không ở top-1, 0 nếu không có trong top-3).

### Đối chứng: cùng 5 câu hỏi, đổi chiến lược chia nhỏ

Chạy lặp lại đúng 5 câu trên với 4 chiến lược khác nhau để biết kết quả đến từ đâu — cùng corpus, cùng embedding, chỉ khác dòng chọn chunker:

| Chiến lược | Chunks | Điểm | Top-1 | MRR |
|---|---|---|---|---|
| **Heading/Section** | 121 | **8/10** | **4/5** | **0.800** |
| Recursive (`chunk_size=600`) | 95 | 4/10 | 2/5 | 0.400 |
| Sentence (4 câu/chunk) | 104 | 4/10 | 2/5 | 0.400 |
| Fixed-size (overlap 50) | 97 | 3/10 | 1/5 | 0.267 |

Điều đáng chú ý: cả 4 chiến lược đều **đúng tài liệu** ở mọi câu (chấm theo `doc_id` sẽ ra 5/5 cho tất cả và che hết khác biệt), nhưng khi chấm theo nội dung thì chênh nhau hơn gấp đôi. **Câu 1 là câu duy nhất tôi trượt**, và nó trượt ở cả 4 chiến lược: đáp án "*15 hoặc 30 ngày*" nằm trong một mục rất ngắn, bị các đoạn dài hơn nhưng ít thông tin hơn (tiêu đề tài liệu, phạm vi áp dụng) đè trong xếp hạng. **Câu 4 thì ngược lại — chỉ Heading/Section lấy được**, vì nó tách được mục "1. Điều kiện bảo hành" khỏi mục "2. Những trường hợp *không* được bảo hành" vốn ngược nghĩa nhưng rất gần nhau về vector.

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** **4 / 5** (trượt câu 1).

### Một lỗi tôi tìm ra và đã sửa trong `src/agent.py`

> Khi chạy lần đầu, **câu 5 lấy đúng chunk chứa đáp án ở top-1 (2/2) nhưng agent vẫn trả lời sai** — nó khẳng định "không có thông tin về thời gian bảo hành tối đa" và trích dẫn nhầm số liệu của Hoàng Hà (buyer). Nguyên nhân: `KnowledgeBaseAgent.answer` chỉ gọi `store.search()` mà **không truyền được `metadata_filter`**, nên bước sinh câu trả lời truy xuất không lọc và kéo về cả tài liệu buyer, làm nhiễu ngữ cảnh dù bước retrieval đã đúng.
>
> Tôi thêm tham số tuỳ chọn `metadata_filter` vào `answer()` và cho nó gọi `search_with_filter()` — chạy lại thì câu 5 trả lời đúng ("không quá 30 ngày"). Bài học: **bộ lọc metadata phải được áp dụng ở cả bước retrieval và bước sinh câu trả lời**; nếu chỉ áp ở một đầu thì công sức gắn metadata bị vô hiệu hoá ở đúng chỗ quan trọng nhất.

**Một quan sát về chất lượng căn cứ dữ liệu (grounding):** ở câu 1, retrieval trượt (top-3 không có chunk chứa đáp án) và agent **nói thẳng là không có thông tin** thay vì bịa. Đây là hành vi đúng — nhưng nó cũng cho thấy chất lượng câu trả lời cuối cùng **không thể tốt hơn chất lượng retrieval**, nên chấm điểm chỉ bằng câu trả lời của agent là không đủ.

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> So sánh trong nhóm cho thấy **không có chiến lược nào thắng toàn diện**: mỗi chiến lược có một câu "của riêng nó" — Sentence thắng câu 1, Heading thắng câu 4, còn câu 2/3/5 nhiều chiến lược cùng đạt. Vì vậy hướng đúng không phải chọn một rồi bỏ phần còn lại, mà là **kết hợp hai tầng**: cắt theo cấu trúc (heading) trước, rồi trong mỗi mục dài mới cắt tiếp theo câu và **gắn lại tiêu đề mục vào từng mảnh con** — giữ được cả ranh giới ngữ nghĩa của heading lẫn mật độ thông tin của sentence.
>
> Bài học thứ hai đắt hơn: **chấm ở mức `doc_id` thổi phồng kết quả.** Cùng một lần chạy, chấm "tài liệu có trong top-3 không" cho 5/5 ở cả 4 chiến lược và bảng so sánh trở nên vô nghĩa; chuyển sang chấm mức nội dung thì điểm tụt xuống 3–8/10 và các chiến lược mới tách ra. Chênh lệch giữa hai cách chấm chính là phát hiện đáng giá nhất của buổi lab.

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 10 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | 5 / 5 |
| Kết quả truy xuất của tôi (Competition Results) | *chờ nhóm chốt corpus + 5 câu hỏi* |
| **Tổng phần cá nhân** | **50 / 60 + mục 5** |
