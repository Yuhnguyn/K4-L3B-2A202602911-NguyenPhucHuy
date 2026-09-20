# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** [Tên nhóm]
**Thành viên:** [Họ tên từng thành viên]
**Ngày:** [Ngày nộp]

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

> **Ghi chú về cách chạy (quan trọng cho tính lặp lại):** toàn bộ số liệu trong báo cáo này chạy bằng **embedder thật `gemini-embedding-001`** (`EMBEDDING_PROVIDER=gemini` trong `.env`), không dùng `MockEmbedder`. Lý do: `MockEmbedder` băm MD5 trên chuỗi nên hai đoạn đồng nghĩa không hề gần nhau về vector — điểm số chỉ phản ánh trùng mặt chữ, không phản ánh ngữ nghĩa, nên mọi kết luận retrieval rút ra từ mock đều không kiểm chứng được. Script chạy: `python bench.py --strategy <heading|recursive|sentence|fixed> --chunk-size 650`.

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Chủ đề (Domain) & Lý Do Chọn

**Chủ đề:** Chính sách bảo hành — đổi trả cho **khách mua** (buyer) và **quy trình xử lý đổi trả/bảo hành cho Nhà Bán** (seller) trên các sàn thương mại điện tử.

**Tại sao nhóm chọn chủ đề này?**
> Cùng một nghiệp vụ "đổi trả – bảo hành" nhưng tồn tại dưới **hai vai hoàn toàn khác nhau**: khách mua thì quan tâm thời hạn và điều kiện được đổi mới, còn Nhà Bán thì quan tâm nghĩa vụ phản hồi, mốc thời gian và chế tài. Đây là điều kiện lý tưởng để kiểm tra xem **metadata có thực sự giải quyết được vấn đề nhiễu ngữ cảnh hay không** — thay vì chỉ chọn một chủ đề mà mọi tài liệu đều giống nhau. Ngoài ra các văn bản này có cấu trúc heading rõ, số liệu cụ thể (15/30 ngày, 02 ngày làm việc) nên **câu trả lời vàng kiểm chứng được bằng mắt**, không phải phán đoán chủ quan.

### Danh sách tài liệu (Data Inventory)

| # | Tên tài liệu | Nguồn (Source URL) | Ngày lấy / Phiên bản | Số ký tự | Metadata đã gán |
|---|--------------|------------|--------------------|----------|-----------------|
| 1 | hoanghamobile-warranty-buyer.md | https://hoanghamobile.com/chinh-sach-bao-hanh | 2026-09-20 / ap-dung-tu-2025-09-29 | 8.255 | audience=buyer, category=warranty-policy, language=vi |
| 2 | shopee-warranty-buyer.md | https://help.shopee.vn/portal/4/article/79046 | 2026-09-20 / not-stated | 3.210 | audience=buyer, category=warranty-policy, language=vi |
| 3 | tiki-seller-warranty-faq.md | https://hocvien.tiki.vn/faq/cau-hoi-thuong-gap-ve-xu-ly-doi-tra-bao-hanh/ | 2026-09-20 / not-stated | 14.054 | audience=seller, category=warranty-process, language=vi |
| 4 | tiki-seller-warranty-dropship.md | https://hocvien.tiki.vn/faq/huong-dan-quy-trinh-xu-ly-doi-tra-bao-hanh-mo-hinh-dropship/ | 2026-09-20 / not-stated | 11.229 | audience=seller, category=warranty-process, language=vi |
| 5 | tiki-seller-warranty-sd.md | https://hocvien.tiki.vn/faq/huong-dan-quy-trinh-xu-ly-doi-tra-bao-hanh-mo-hinh-sd/ | 2026-09-20 / not-stated | 7.491 | audience=seller, category=warranty-process, language=vi |
| 6 | tiki-seller-warranty-fbt.md | https://hocvien.tiki.vn/faq/mo-hinh-fbt-huong-dan-quy-trinh-xu-ly-doi-tra-bao-hanh/ | 2026-09-20 / not-stated | 3.432 | audience=seller, category=warranty-process, language=vi |

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**
- [x] Tập tài liệu (Corpus) chỉ chứa nguồn công khai/được phép dùng và không chứa dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ.
- [x] Mỗi tài liệu có `source_url`, `retrieved_at`, `document_version` (hoặc ngày hiệu lực) trong metadata.
- [x] Danh sách URL được quản lý trong `data/urls.csv`; manifest `data/warranty/sources.csv` khớp 1-1 với 6 file `.md`.

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho truy xuất (retrieval)? |
|----------------|------|---------------|-------------------------------|
| audience | string | buyer / seller | Trường lọc chính. Cùng chủ đề "đổi trả" nhưng buyer và seller có nghĩa vụ khác nhau, nên lọc theo vai giúp loại các đoạn đúng chủ đề nhưng sai đối tượng. |
| category | string | warranty-policy / warranty-process | Tách "chính sách" (điều khoản, thời hạn) khỏi "quy trình" (các bước thao tác trên hệ thống) — hai loại câu hỏi khác nhau. |
| source_url | string | https://hoanghamobile.com/... | Truy vết và xác minh câu trả lời về văn bản gốc. |
| retrieved_at | string | 2026-09-20 (YYYY-MM-DD) | Kiểm tra độ mới của dữ liệu; chính sách đổi theo thời gian. |
| document_version | string | ap-dung-tu-2025-09-29 / not-stated | Biết chính sách đang áp dụng từ mốc nào; `not-stated` khi nguồn không nêu (không bịa số hiệu). |
| chunk_index | string | 0..N | Do bước ingest sinh ra — cho phép chỉ đích danh chunk nào đã trả lời câu hỏi. |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

> Mỗi thành viên thử **một chiến lược khác nhau** trên cùng bộ tài liệu và cùng 5 câu hỏi; nhóm tổng hợp và so sánh ở đây.

### Phân tích đường cơ sở (Baseline Analysis)

Chạy `ChunkingStrategyComparator().compare(text, chunk_size=200)` trên 3 tài liệu đại diện (số liệu thực đo, không ước lượng):

| Tài liệu | Chiến lược (Strategy) | Số lượng Chunk | Độ dài trung bình | Giữ được ngữ cảnh không? |
|-----------|----------|-------------|------------|-------------------|
| hoanghamobile-warranty-buyer.md (8.255 ký tự) | FixedSizeChunker (`fixed_size`) | 42 | 196.5 | Kém — cắt giữa câu, giữa mục |
| hoanghamobile-warranty-buyer.md | SentenceChunker (`by_sentences`) | 25 | 328.4 | Khá — trọn câu nhưng có thể tách khỏi tiêu đề mục |
| hoanghamobile-warranty-buyer.md | RecursiveChunker (`recursive`) | 67 | 123.0 | Tốt về ranh giới, nhưng chunk khá nhỏ ở `chunk_size=200` |
| tiki-seller-warranty-faq.md (14.054 ký tự) | FixedSizeChunker (`fixed_size`) | 71 | 197.9 | Kém |
| tiki-seller-warranty-faq.md | SentenceChunker (`by_sentences`) | 46 | 302.7 | Khá |
| tiki-seller-warranty-faq.md | RecursiveChunker (`recursive`) | 106 | 132.4 | Tốt về ranh giới |
| shopee-warranty-buyer.md (3.210 ký tự) | FixedSizeChunker (`fixed_size`) | 17 | 188.8 | Kém |
| shopee-warranty-buyer.md | SentenceChunker (`by_sentences`) | 9 | 354.7 | Khá |
| shopee-warranty-buyer.md | RecursiveChunker (`recursive`) | 27 | 118.7 | Tốt về ranh giới |

**Đọc bảng này thế nào:** ở `chunk_size=200`, `by_sentences` vượt xa giới hạn đặt ra (avg 328–355 ký tự so với 200) vì nó nhóm theo câu chứ không theo ký tự — đúng thiết kế, nhưng cần biết để không kỳ vọng sai. `recursive` bám sát giới hạn nhất (avg 119–132). `fixed_size` cắt đúng số ký tự nhưng không biết gì về ranh giới ngôn ngữ. Vì vậy khi chạy benchmark retrieval, nhóm nâng `chunk_size` lên **650** để mọi chiến lược có đủ ngữ cảnh trả lời một câu hỏi trọn vẹn.

### Chiến lược của từng thành viên

> Mỗi thành viên điền một khối dưới đây (điền tên người phụ trách từng chiến lược).

**Thành viên 1 — [Tên]**
- **Loại chiến lược:** `RecursiveChunker(chunk_size=650)` + lọc `audience`
- **Mô tả & lý do chọn cho chủ đề này:** Văn bản chính sách có cấu trúc phân cấp (tiêu đề > mục > gạch đầu dòng) và ranh giới ý thường nằm ở `\n\n` hoặc `\n`. Tôi để `RecursiveChunker` tự thử separator theo thứ tự ưu tiên rồi gom tham lam tới 650 ký tự, nên một chunk thường chứa trọn một mục kèm các điều kiện liên quan — đúng thứ mà câu hỏi dạng "trong bao lâu / bao nhiêu ngày" cần.

**Thành viên 2 — [Tên]**
- **Loại chiến lược:** **Chunk theo heading/section** (`chunk_heading`, chunk_size=650) — chiến lược bắt buộc theo `K4_VARIANT.md`
- **Mô tả & lý do chọn:** Văn bản nguồn là chính sách pháp lý có heading rõ, nên mỗi mục (`##`, `###`) nên là một đơn vị truy xuất độc lập. Cách này giữ trọn tiêu đề trong chunk nên chunk tự mô tả được nó nói về cái gì; mục nào quá dài thì mới cắt đệ quy bên trong. Đánh đổi: tạo ra nhiều chunk rất ngắn, và đó chính là nguyên nhân lỗi ở Q1 (xem mục 3).
- **Code snippet:**
```python
def chunk_heading(text, chunk_size):
    chunks = []
    for section in split_sections(text):        # tách theo dòng bắt đầu bằng '#'
        if len(section) <= chunk_size:
            chunks.append(section)
            continue
        head = section.splitlines()[0].strip()
        rest = "\n".join(section.splitlines()[1:]).strip()
        for piece in RecursiveChunker(chunk_size=chunk_size).chunk(rest):
            chunks.append(f"{head}\n\n{piece}".strip())
    return chunks or [text.strip()]
```

**Thành viên 3 — [Tên]**
- **Loại chiến lược:** `SentenceChunker(max_sentences_per_chunk=4)` + lọc `audience`
- **Mô tả & lý do chọn:** Chính sách viết theo câu dài, nhiều điều kiện phụ nối bằng dấu phẩy/gạch đầu dòng. Nhóm theo câu giúp mỗi chunk là một phát ngôn hoàn chỉnh, dễ đọc và dễ trích dẫn. Đánh đổi: vì tách theo câu nên **tiêu đề mục bị rơi khỏi chunk**, làm mất ngữ cảnh ở các danh sách quy trình.

**Thành viên 4 — [Tên]**
- **Loại chiến lược:** `FixedSizeChunker(chunk_size=650, overlap=130)` + lọc `audience` (đối chứng)
- **Mô tả & lý do chọn:** Giữ làm **đối chứng (control)** để đo xem cắt thuần theo ký tự, không hiểu ngữ nghĩa, có thực sự tệ hơn các chiến lược có cấu trúc hay không. Overlap 20% để hạn chế mất thông tin ở ranh giới.

### So Sánh Giữa Các Thành viên

Chạy cùng 6 tài liệu, cùng 5 câu hỏi, cùng `chunk_size=650`, cùng embedder `gemini-embedding-001`. Chấm theo `docs/SCORING.md` (2 điểm/câu).

| Thành viên | Chiến lược (Strategy) | Chunks | Avg len | Retrieval (/10) | Điểm mạnh | Điểm yếu |
|-----------|----------|--------|---------|-----------------|-----------|----------|
| 1 | Recursive + audience filter | 87 | 526.9 | **9/10** | Chunk chứa trọn mục + điều kiện; **5/5 câu** có đủ từ khoá đáp án trong top-3 | Q3 không đưa được chunk đáp án lên top-1 (top-1 là đoạn "bảo hành xong" liên quan nhưng lệch trọng tâm) |
| 2 | Heading/Section | 111 | 424.4 | 8/10 | **Q2 và Q4 tốt nhất toàn nhóm** — top-1 đúng nguyên văn đoạn hỏi–đáp; chunk tự mô tả nhờ giữ heading | **Q1 thất bại hoàn toàn (0/5 từ khoá)** — chia vụn làm đoạn chứa "15/30 ngày" không lọt top-3 |
| 3 | Sentence (4 câu/chunk) | 104 | 437.6 | 8/10 | Q1 mạnh — top-1 chứa nguyên câu "Trong 15 hoặc 30 ngày đầu…" | Mất tiêu đề mục nên **Q4 thất bại** (top-1 0/2, top-3 chỉ 1/2) và Q5 tụt xuống top-2 |
| 4 | Fixed-size + overlap 20% | 90 | 630.7 | **9/10** | Bất ngờ: cắt thuần ký tự nhưng chunk to (631 ký tự) nên vẫn chứa đủ ngữ cảnh; 5/5 câu đủ từ khoá | Chunk lớn làm loãng tín hiệu — Q5 không đưa được đủ ý lên top-1; không đảm bảo ranh giới ngôn ngữ, rủi ro khi corpus đổi |

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**
> **`RecursiveChunker(chunk_size=650)` là lựa chọn tốt nhất (9/10)**, vì nó là chiến lược duy nhất đạt **5/5 câu có đủ từ khoá đáp án trong top-3** mà vẫn giữ ranh giới ngôn ngữ — hai tiêu chí mà không chiến lược nào khác đạt đồng thời. `heading` đạt điểm cao ở các câu hỏi–đáp rõ ràng (Q2, Q4) nhưng **sụp ở Q1** vì chia văn bản thành các mục quá ngắn: đoạn chứa con số quyết định ("15 hoặc 30 ngày") chỉ dài vài chục ký tự, nên bị các mục dài hơn nhưng ít thông tin hơn đè trong xếp hạng. `fixed_size` hòa điểm 9/10 nhưng bằng một con đường khác — nó không "hiểu" gì cả, chỉ may mắn là 650 ký tự đủ lớn để chứa ngữ cảnh; đây là kết quả phụ thuộc vào kích thước chứ không phải vào thiết kế, nên **không nên chọn làm chiến lược chính**.
>
> Bài học cốt lõi: **chunk nhỏ không tự động tốt hơn.** Với văn bản chính sách, đơn vị ngữ nghĩa đúng không phải "một heading" mà là "một heading cộng các điều kiện đi kèm nó".

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

> **Đúng 5 câu hỏi**, đa dạng, có thể kiểm chứng; **ít nhất 1 câu** cần lọc metadata mới trả lời tốt. Đây là bộ câu hỏi chung cho mọi thành viên chạy.

| # | Câu hỏi (Query) | Câu trả lời chuẩn (Gold Answer) | Chunk nào chứa thông tin? |
|---|-------|-------------------------------|--------------------------|
| 1 | Theo chính sách Hoàng Hà Mobile, khách hàng được đổi mới miễn phí trong thời gian nào? | Trong 15 hoặc 30 ngày đầu kể từ ngày mua, tùy theo dòng sản phẩm, nếu sản phẩm được xác nhận lỗi phần cứng do nhà sản xuất thì được đổi mới miễn phí 100%. | hoanghamobile-warranty-buyer.md — mục "II. Thời gian và chính sách đổi sản phẩm / a) Trong 15 hoặc 30 ngày đầu…" |
| 2 | Trong mô hình Seller Center, Nhà Bán có bao nhiêu ngày làm việc để xác nhận phương án xử lý yêu cầu đổi trả? | Nhà Bán có 02 ngày làm việc kể từ khi sản phẩm được cập nhật trạng thái cần Nhà Bán phản hồi để xác nhận phương án xử lý yêu cầu đổi, trả, bảo hành. | tiki-seller-warranty-faq.md — mục "8. Nhà Bán có thời gian bao lâu để xác nhận…"; tiki-seller-warranty-dropship.md — mục "1. Trường hợp KHÔNG thu hồi vật lý" |
| 3 | Nếu Nhà Bán không phản hồi, Tiki sẽ xử lý yêu cầu của Khách Hàng như thế nào? | Tiki sẽ chủ động xử lý theo yêu cầu Khách Hàng và được quyền từ chối tiếp nhận các khiếu nại của Nhà Bán; nếu không có lý do hợp lệ, Tiki có thể bồi thường cho Khách Hàng. | tiki-seller-warranty-faq.md — mục "4. Trường hợp Nhà Bán không xác nhận phương án xử lý trong 02 ngày làm việc…" |
| 4 | Nhà Bán xác nhận phương án xử lý yêu cầu đổi trả qua đâu trong hệ thống? | Nhà Bán xác nhận phương án xử lý qua hệ thống Seller Center, vào mục Đơn hàng > Đổi trả bảo hành, tab Cần Nhà Bán phản hồi. | tiki-seller-warranty-faq.md — mục "4. Nhà Bán xác nhận phương án xử lý… qua đâu?" |
| 5 | Theo quy trình đổi mới của Hoàng Hà Mobile, khách hàng cần làm gì trước khi nhận sản phẩm mới? | Khách hàng mang sản phẩm đến cửa hàng, nhân viên tiếp nhận và thẩm định lỗi ngay tại chỗ; nếu lỗi do nhà sản xuất và đủ điều kiện thì tiến hành đổi sản phẩm mới. | hoanghamobile-warranty-buyer.md — mục "3. Quy trình đổi sản phẩm 'Lỗi Đổi Liền'" |

### Tổng hợp chất lượng truy xuất của nhóm

> Cách chấm (theo `docs/SCORING.md`): **2 điểm/câu** — top-3 chứa chunk liên quan + agent trả lời đúng (2), có liên quan nhưng thiếu/không ở top-1 (1), không có trong top-3 (0).
> Cách xác định "liên quan": top-3 phải chứa **đủ các từ khoá mang thông tin quyết định của gold answer** (ví dụ Q1: `15`, `30`, `đổi mới`). Chỉ khớp `doc_id` là chưa đủ — một tài liệu đúng vẫn có thể trả về toàn đoạn không chứa câu trả lời.

**Điểm từng câu theo từng chiến lược:**

| # | Câu hỏi | Recursive | Heading | Sentence | Fixed | Chiến lược tốt nhất cho câu này |
|---|---------|:---------:|:-------:|:--------:|:-----:|---------------------------------|
| 1 | Đổi mới miễn phí trong thời gian nào? | **2** | 0 | **2** | **2** | Recursive / Sentence (top-1 chứa nguyên câu "15 hoặc 30 ngày") |
| 2 | Bao nhiêu ngày làm việc để xác nhận? | **2** | **2** | **2** | **2** | Heading (top-1 đúng mục "8. Nhà Bán có thời gian bao lâu…") |
| 3 | Nếu Nhà Bán không phản hồi thì sao? | 1 | **2** | **2** | **2** | Heading / Sentence (top-1 đúng mục "4. Trường hợp Nhà Bán không xác nhận…") |
| 4 | Xác nhận phương án qua đâu? | **2** | **2** | 1 | **2** | Heading (top-1 đúng nguyên văn mục hỏi–đáp) |
| 5 | Cần làm gì trước khi nhận sản phẩm mới? | **2** | **2** | 1 | 1 | Recursive / Heading |
| | **Tổng** | **9/10** | **8/10** | **8/10** | **9/10** | |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** **5/5** với cả 4 chiến lược (top-3 luôn đúng tài liệu); **5/5 câu đủ từ khoá đáp án** chỉ đạt được ở `recursive` và `fixed`.

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**
> **Câu trả lời trung thực: với bộ 5 câu hỏi hiện tại, lọc `audience` KHÔNG thay đổi kết quả nào cả.** Nhóm đã chạy A/B cho cả 4 chiến lược: với mỗi câu, top-3 khi lọc và khi không lọc **trùng nhau hoàn toàn về `doc_id`**.

| Câu hỏi | Với filter | Không filter | Khác biệt |
|---|---|---|---|
| Q1 (buyer) | hoanghamobile ×3 | hoanghamobile ×3 | Không |
| Q2 (seller) | faq, dropship, faq | faq, dropship, faq | Không |
| Q3 (seller) | faq ×3 | faq ×3 | Không |
| Q4 (seller) | faq, sd, dropship | faq, sd, dropship | Không |
| Q5 (buyer) | hoanghamobile ×3 | hoanghamobile ×3 | Không |

> **Vì sao?** Vì cả 5 câu hỏi đều **nêu đích danh chủ thể** ("Hoàng Hà Mobile", "Tiki", "Nhà Bán"). Với embedder thực, tên riêng trong câu hỏi đã đủ để kéo về đúng miền tài liệu, nên bộ lọc trở nên dư thừa — nó chỉ xác nhận lại điều mà retrieval đã tự làm đúng.
>
> **Nhóm đã kiểm chứng ngược lại** bằng 2 câu hỏi **không nêu tên nền tảng** để tìm trường hợp bộ lọc thực sự có tác dụng:
>
> | Câu hỏi (không nêu chủ thể) | buyer | không lọc | seller |
> |---|---|---|---|
> | "Thời hạn đổi trả hoặc đổi mới sản phẩm là bao lâu?" | hoanghamobile ×3 | hoanghamobile ×3 | **tiki-seller-faq, fbt, sd** |
> | "Bao nhiêu ngày làm việc để xác nhận phương án xử lý yêu cầu đổi trả?" | **shopee-buyer, hoanghamobile ×2** | tiki-dropship, sd, tiki-dropship | tiki-dropship, sd, tiki-dropship |
>
> Khi câu hỏi mơ hồ về chủ thể, bộ lọc **lật hẳn miền kết quả**: cùng một câu hỏi, lọc `seller` trả về bộ quy trình dành cho Nhà Bán còn lọc `buyer` trả về chính sách cho khách mua. Đây mới là giá trị thật của metadata.
>
> **Kết luận và khuyến nghị:** bộ lọc nên **giữ lại** (nó vô hại và là lớp bảo vệ khi câu hỏi mơ hồ), nhưng bộ 5 câu hỏi nên được sửa để **ít nhất một câu không nêu tên nền tảng** — nếu không, yêu cầu "có một câu cần `metadata_filter`" của L3B chỉ được thỏa mãn trên hình thức mà không chứng minh được tác dụng.

### Phân tích lỗi (Failure Analysis — Bài 3.5)

**Lỗi 1 (nặng nhất) — `heading` thất bại hoàn toàn ở Q1.**
> Truy vấn: *"Theo chính sách Hoàng Hà Mobile, khách hàng được đổi mới miễn phí trong thời gian nào?"*, lọc `audience=buyer`. Top-3 trả về: (1) mục "1. Đối tượng áp dụng", (2) mục "Nguyên tắc bảo hành", (3) tiêu đề tài liệu — **0/3 từ khoá** `15`, `30`, `đổi mới`.
>
> **Nguyên nhân:** mục chứa đáp án ("### 2. Thời gian và chính sách đổi sản phẩm — a) Trong 15 hoặc 30 ngày đầu…") là một đoạn **rất ngắn** sau khi tách heading, trong khi ba đoạn thắng lại dài hơn và chứa cụm từ chung chung ("chính sách bảo hành Hoàng Hà Mobile", "bảo hành miễn phí", "đổi sản phẩm") — trùng nhiều từ với câu hỏi hơn. Chunk ngắn bị bất lợi về mặt tín hiệu: ít token để "cãi lại" các đoạn dài cùng chủ đề.
>
> **Đề xuất:** hoặc dùng `recursive` với kích thước đủ lớn (650) để gộp các mục ngắn liền kề, hoặc giữ `heading` nhưng **gộp các mục liên tiếp cho tới một kích thước tối thiểu** (ví dụ 300 ký tự) trước khi tạo chunk.

**Lỗi 2 — `sentence` thất bại ở Q4.**
> Top-1 là một đoạn quy trình dropship ("…bấm Xác nhận giải pháp đã chọn…") với **0/2 từ khoá** (`Seller Center`, `Cần Nhà Bán phản hồi`), top-3 chỉ đạt 1/2. Trong khi `heading` xếp đúng đoạn chứa câu trả lời lên top-1 với 2/2.
>
> **Nguyên nhân:** tách theo câu làm **tiêu đề mục rơi khỏi chunk**, nên các bước quy trình của nhiều mô hình (dropship / SD / FBT) trở nên giống nhau về mặt vector. Câu trả lời nằm ở cụm "tab Cần Nhà Bán phản hồi" — chi tiết này bị pha loãng.
>
> **Đề xuất:** khi chunk theo câu, **luôn gắn tiêu đề mục hiện hành vào đầu mỗi chunk** (prepend heading) — giữ được ngữ cảnh mà vẫn tách theo câu.

**Lỗi 3 — giới hạn phương pháp luận, không phải lỗi xếp hạng.**
> Nếu chỉ đo bằng `doc_id` (top-3 có đúng tài liệu không), **cả 4 chiến lược đều đạt 5/5** và ta dễ kết luận "mọi thứ đều tốt". Nhưng khi kiểm tra **nội dung** chunk, điểm thực tế rơi xuống 8–9/10 và lộ ra hai lỗi ở trên. Bài học: thước đo phải bám vào câu trả lời, không bám vào tên file.

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**
> 1. **Chunk nhỏ không tự động tốt hơn.** Chiến lược "nghe có vẻ đúng nhất" (tách theo heading, vì văn bản có heading) lại là chiến lược duy nhất thất bại một câu hỏi hoàn toàn, vì mục chứa con số quyết định chỉ dài vài chục ký tự. Đơn vị ngữ nghĩa đúng của văn bản chính sách là "một mục **cộng các điều kiện đi kèm**", không phải "một mục".
> 2. **Metadata filter có giá trị thật, nhưng bộ câu hỏi của nhóm chưa chứng minh được điều đó.** Cả 5 câu đều nêu đích danh nền tảng nên embedder tự phân biệt được, filter đổi kết quả 0%. Phải thử câu hỏi không nêu chủ thể mới thấy filter lật hẳn miền kết quả buyer/seller. **Một cơ chế không được kiểm tra thì không nên được coi là đã hoạt động.**
> 3. **Phải chấm bằng nội dung chunk, không bằng `doc_id`.** Đo theo `doc_id` cho điểm tuyệt đối 5/5 ở cả 4 chiến lược, che mất hai lỗi retrieval thật. Đây là lỗi phương pháp luận dễ mắc nhất và cũng dễ sửa nhất.
> 4. **Embedder quyết định báo cáo có nghĩa hay không.** Lần chạy đầu nhóm dùng `MockEmbedder` và nhận được kết luận sai (rằng filter "giúp rất nhiều"). Chuyển sang `gemini-embedding-001` cho kết quả ngược lại. Điểm số từ mock là nhiễu, không phải tín hiệu.

**Bài học rút ra khi so sánh trong nhóm:**
> Cùng một corpus, cùng 5 câu hỏi, cùng một embedder, chỉ đổi cách chia nhỏ mà kết quả lệch nhau tới **9 điểm so với 8 điểm** và **thay đổi hẳn câu nào thành công, câu nào thất bại**: `heading` thắng ở Q2/Q4 nhưng thua trắng Q1, còn `recursive` ngược lại. Điều này cho thấy **không có chiến lược "tốt nhất" tuyệt đối** — chỉ có chiến lược khớp với cấu trúc văn bản *và* với kiểu câu hỏi. Vì vậy nhóm chấm theo từng câu rồi mới tổng hợp, thay vì chỉ so một con số tổng.

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**
> Thứ nhất, viết lại ít nhất một câu hỏi đánh giá **không nêu tên nền tảng**, để yêu cầu `metadata_filter` của L3B được kiểm chứng thật thay vì chỉ được thỏa mãn hình thức. Thứ hai, dùng `recursive(chunk_size=650)` làm mặc định nhưng **thêm bước gộp mục ngắn liền kề** để lấy ưu điểm của cả `heading` (giữ ranh giới mục) và `recursive` (không chia vụn). Thứ ba, tách thêm metadata `section` (tên mục gốc) để có thể lọc theo cả vai và mục, và để chunk luôn mang theo ngữ cảnh tiêu đề. Thứ tư, chốt **đo bằng nội dung chunk** ngay từ đầu thay vì `doc_id`.

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Lựa chọn tài liệu (Document Set Quality) | 10 / 10 |
| Thiết kế chiến lược (Strategy Design) | 13 / 15 |
| Chất lượng truy xuất (Retrieval Quality) | 9 / 10 |
| Thuyết trình (Demo) | 5 / 5 |
| **Tổng phần nhóm** | **37 / 40** |
