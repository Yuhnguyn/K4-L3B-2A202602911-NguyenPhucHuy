# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** Finding Vinno
**Thành viên:** Ngô Hoàng Thụy Khuê, Hoàng Đức Dũng, Nguyễn Phúc Huy
**Ngày:** 20/9/2026

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Chủ đề (Domain) & Lý Do Chọn

**Chủ đề:** Chính sách đổi trả, bảo hành và quy trình xử lý yêu cầu cho khách mua và Nhà Bán trên các sàn thương mại điện tử.

**Tại sao nhóm chọn chủ đề này?**
> Chủ đề này rất phù hợp để đánh giá retrieval vì cùng một thực thể nghiệp vụ có thể xuất hiện dưới nhiều góc nhìn: khách mua, Nhà Bán và mô hình vận hành. Bên cạnh đó, dữ liệu có sẵn trong corpus chứa nhiều đoạn văn cụ thể, dễ kiểm chứng bằng metadata `audience` và `category` để so sánh độ hiệu quả của việc lọc ngữ cảnh.

### Danh sách tài liệu (Data Inventory)

| # | Tên tài liệu | Nguồn (Source URL) | Ngày lấy / Phiên bản | Số ký tự | Metadata đã gán |
|---|--------------|------------|--------------------|----------|-----------------|
| 1 | hoanghamobile-warranty-buyer.md | https://hoanghamobile.com/chinh-sach-bao-hanh | 2026-09-20 / áp dụng từ 2025-09-29 | 7.969 | `audience=buyer`, `category=warranty-policy`, `language=vi` |
| 2 | tiki-seller-warranty-faq.md | https://hocvien.tiki.vn/faq/cau-hoi-thuong-gap-ve-xu-ly-doi-tra-bao-hanh/ | 2026-09-20 / not-stated | 13.746 | `audience=seller`, `category=warranty-process`, `language=vi` |
| 3 | tiki-seller-warranty-sd.md | https://hocvien.tiki.vn/faq/huong-dan-quy-trinh-xu-ly-doi-tra-bao-hanh-mo-hinh-sd/ | 2026-09-20 / not-stated | 7.132 | `audience=seller`, `category=warranty-process`, `language=vi` |
| 4 | tiki-seller-warranty-dropship.md | https://hocvien.tiki.vn/faq/huong-dan-quy-trinh-xu-ly-doi-tra-bao-hanh-mo-hinh-dropship/ | 2026-09-20 / not-stated | 10.832 | `audience=seller`, `category=warranty-process`, `language=vi` |
| 5 | tiki-seller-warranty-fbt.md | https://hocvien.tiki.vn/faq/mo-hinh-fbt-huong-dan-quy-trinh-xu-ly-doi-tra-bao-hanh/ | 2026-09-20 / not-stated | 3.217 | `audience=seller`, `category=warranty-process`, `language=vi` |
| 6 | shopee-warranty-buyer.md | https://help.shopee.vn/portal/4/article/79046 | 2026-09-20 / not-stated | 2.949 | `audience=buyer`, `category=warranty-policy`, `language=vi` |

**Tổng:** 6 tài liệu · 45.845 ký tự (phần thân, đã trừ frontmatter) · phân bố `audience`: buyer 2 / seller 4.

> Số ký tự đếm bằng `len(body)` sau khi tách frontmatter, đối chiếu trực tiếp từ file trong `data/warranty/`. Toàn bộ 6 URL đều là trang công khai và được ghi trong `data/warranty/sources.csv` với `license_or_permission = public-source` — **không có tài liệu nội bộ nào trong corpus**.

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**
- [x] Tập tài liệu (Corpus) chỉ chứa nguồn công khai/được phép dùng và không chứa dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ.
- [x] Mỗi tài liệu có `source_url`, `retrieved_at`, `document_version` (hoặc ngày hiệu lực) trong metadata.

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho truy xuất (retrieval)? |
|----------------|------|---------------|-------------------------------|
| audience | string | buyer / seller | Giúp nhóm dữ liệu theo người dùng, giảm sai lệch giữa các chính sách khác nhau. |
| category | string | warranty-policy / warranty-process | Cho phép lọc theo loại nội dung để tránh trả lời nhầm giữa chính sách và quy trình vận hành. |
| source_url | string | https://... | Dễ kiểm tra nguyên gốc, xác thực và theo dõi phiên bản tài liệu. |
| retrieved_at | string | 2026-09-20 | Theo dõi thời điểm hợp nhất dữ liệu và sửa đổi nếu cần. |
| document_version | string | ap-dung-tu-2025-09-29 | Giúp lịch sử phiên bản và so sánh hiệu lực chính sách. |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

> Mỗi thành viên thử **một chiến lược khác nhau** trên cùng bộ tài liệu; nhóm tổng hợp và so sánh ở đây.

### Phân tích đường cơ sở (Baseline Analysis)

Chạy `ChunkingStrategyComparator().compare()` trên 2-3 tài liệu:

> Số đo thật từ `ChunkingStrategyComparator().compare(body, chunk_size=600)`, chạy trên 3 tài liệu đại diện. **Đã tách bỏ frontmatter YAML trước khi so sánh** — nếu không, khối 9 dòng metadata sẽ bị tính vào độ dài chunk và làm lệch cả ba cột.

| Tài liệu | Chiến lược (Strategy) | Số lượng Chunk | Độ dài trung bình | Giữ được ngữ cảnh không? |
|-----------|----------|-------------|------------|-------------------|
| hoanghamobile-warranty-buyer.md | FixedSizeChunker (`fixed_size`) | 14 | 569 (min 169 – max 600) | Kém — cắt theo số ký tự nên đứt giữa câu và giữa mục |
| hoanghamobile-warranty-buyer.md | SentenceChunker (`by_sentences`) | 25 | 317 (min 184 – max 573) | Khá — không bao giờ đứt giữa câu, nhưng bỏ qua ranh giới mục |
| hoanghamobile-warranty-buyer.md | RecursiveChunker (`recursive`) | 16 | 494 (min 152 – max 579) | Tốt nhất — ưu tiên cắt ở `\n\n` nên bám ranh giới đoạn |
| tiki-seller-warranty-faq.md | FixedSizeChunker (`fixed_size`) | 23 | 598 (min 546 – max 600) | Kém — chunk gần như đều tăm tắp 600 ký tự, tức cắt bừa |
| tiki-seller-warranty-faq.md | SentenceChunker (`by_sentences`) | 46 | 296 (min 110 – max 628) | Khá — nhưng chunk dễ vắt qua hai mục FAQ liền nhau |
| tiki-seller-warranty-faq.md | RecursiveChunker (`recursive`) | 27 | 504 (min 178 – max 599) | Tốt — 27 chunk xấp xỉ số mục FAQ của tài liệu |
| shopee-warranty-buyer.md | FixedSizeChunker (`fixed_size`) | 5 | 590 (min 549 – max 600) | Kém |
| shopee-warranty-buyer.md | SentenceChunker (`by_sentences`) | 9 | 326 (min 134 – max 490) | Khá |
| shopee-warranty-buyer.md | RecursiveChunker (`recursive`) | 7 | 418 (min 297 – max 539) | Tốt |

**Đọc bảng này thế nào.** Cột `min`/`max` tiết lộ nhiều hơn cột trung bình: `fixed_size` trên FAQ Tiki cho min 546 / max 600 — gần như mọi chunk đều chạm trần, nghĩa là nó cắt theo bộ đếm ký tự chứ không theo bất kỳ ranh giới ngữ nghĩa nào. Ngược lại `recursive` có min 178 / max 599, biên độ rộng vì nó *tôn trọng* độ dài tự nhiên của từng đoạn. `by_sentences` cho chunk ngắn nhất (296–326) nên thông tin đặc nhất, nhưng cũng nhiều chunk nhất, tức chi phí embedding cao nhất.

Bảng trên phớt lờ một thực tế của corpus: văn bản đã được người soạn chia sẵn thành **mục có tiêu đề** (`## 1. Điều kiện bảo hành`, `### 8. Nhà Bán có thời gian bao lâu…`). Chiến lược thứ tư của nhóm (mục "Thành viên 3" bên dưới) khai thác trực tiếp cấu trúc đó, nên bảng baseline ở đây chỉ dùng để đối chiếu ba chiến lược còn lại.

### Chiến lược của từng thành viên

**Thành viên 1 — Ngô Hoàng Thụy Khuê**
- **Loại chiến lược:** Recursive chunker + metadata filter
- **Mô tả & lý do chọn cho chủ đề này:** Chính sách và quy trình bảo hành thường có nhiều tiêu đề con, điều kiện, thời hạn và tab trạng thái. Recursive chunking giúp giữ phần đầu đề và đoạn liên quan gần nhau; bộ lọc `audience` giúp câu hỏi giới hạn đúng phía người mua hay Nhà Bán, giảm nhiễu khi nhiều tài liệu cùng đề cập chủ đề "đổi trả".

**Thành viên 2 - Hoàng Đức Dũng**
- **Loại chiến lược:** Sentence chunking (`SentenceChunker`, 4 câu/chunk) + audience filter
- **Mô tả & lý do chọn cho chủ đề này:** Cắt theo ranh giới câu thay vì theo số ký tự, vì văn bản chính sách gồm nhiều điều khoản độc lập — mỗi điều khoản thường gói gọn trong 1-3 câu và cắt giữa câu sẽ làm mất một vế điều kiện. Regex `(?<=[.!?])\s+` dùng lookbehind nên giữ lại dấu câu, và phủ được cả `". "` lẫn `".\n"` — cần thiết vì corpus tiếng Việt có nhiều đoạn xuống dòng ngay sau dấu chấm. Kết quả: 104 chunks, dài trung bình 438 ký tự — nhỏ nhất trong ba chiến lược, nên mỗi chunk đặc thông tin hơn.
- **Code snippet (nếu custom):**
```python
class SentenceChunker:
    # Câu kết thúc bằng . ! ? rồi tới khoảng trắng (space hoặc xuống dòng)
    SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")

    def __init__(self, max_sentences_per_chunk: int = 3) -> None:
        # max(1, ...) chặn slice bước 0 gây vòng lặp vô hạn
        self.max_sentences_per_chunk = max(1, max_sentences_per_chunk)

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []
        sentences = [s.strip() for s in self.SENTENCE_BOUNDARY.split(text)]
        sentences = [s for s in sentences if s]
        step = self.max_sentences_per_chunk
        return [" ".join(sentences[i:i + step]) for i in range(0, len(sentences), step)]
```

**Thành viên 3 - Nguyễn Phúc Huy**
- **Loại chiến lược:** Heading/Section chunking (`HeadingChunker`, `chunk_size=600`) + audience filter
- **Mô tả & lý do chọn cho chủ đề này:** Cắt tại mỗi dòng bắt đầu bằng `#` thay vì theo số ký tự hay dấu câu, vì văn bản chính sách đã được người soạn chia sẵn thành các mục có ý nghĩa trọn vẹn — ranh giới mục chính là ranh giới ngữ nghĩa, không cần suy đoán. Tiêu đề được giữ lại trong chunk nên chunk tự mô tả được nó nói về gì; mục nào dài hơn `chunk_size` mới cắt tiếp bằng `RecursiveChunker` và tiêu đề được gắn lại vào đầu từng mảnh con. Kết quả: 121 chunks, dài trung bình 393 ký tự (min 17 – max 669) — nhiều chunk nhất và mỗi chunk ngắn nhất trong bốn chiến lược, nên thông tin đặc hơn. Đây là chiến lược **duy nhất** lấy được câu 4 (2/2), vì nó tách được mục "1. Điều kiện bảo hành" khỏi mục "2. Những trường hợp *không* được bảo hành" — hai mục rất gần nhau về vector nhưng ngược nghĩa.
- **Code snippet (nếu custom):**
```python
class HeadingChunker:
    """
    Chia theo heading/section: mỗi mục (`##`, `###`) là một đơn vị truy xuất.

    Mục nào dài hơn chunk_size thì mới cắt tiếp bằng RecursiveChunker, và tiêu
    đề mục được gắn lại vào đầu từng mảnh con để chunk không mất ngữ cảnh —
    đây chính là chỗ SentenceChunker để rơi tiêu đề (xem failure case câu 4).
    """

    HEADING = re.compile(r"^#{1,6}\s")

    def __init__(self, chunk_size: int = 600) -> None:
        self.chunk_size = chunk_size

    def _sections(self, text: str) -> list[str]:
        sections: list[str] = []
        heading = ""
        body: list[str] = []

        def flush() -> None:
            nonlocal heading, body
            if heading or body:
                section = (heading + "\n\n" + "\n".join(body).strip()).strip()
                if section:
                    sections.append(section)
            heading = ""
            body = []

        for line in text.splitlines():
            if self.HEADING.match(line):
                flush()
                heading = line.strip()
            else:
                body.append(line.rstrip())
        flush()
        return sections

    def chunk(self, text: str) -> list[str]:
        if not text.strip():
            return []

        chunks: list[str] = []
        for section in self._sections(text):
            if len(section) <= self.chunk_size:
                chunks.append(section)
                continue

            lines = section.splitlines()
            head = lines[0].strip() if self.HEADING.match(lines[0]) else ""
            rest = "\n".join(lines[1:]).strip() if head else section
            for piece in RecursiveChunker(chunk_size=self.chunk_size).chunk(rest):
                chunks.append(f"{head}\n\n{piece}".strip() if head else piece)
        return chunks or [text.strip()]
```

Đăng ký trong `STRATEGIES` của `bench.py` — đổi đúng một dòng, theo quy ước của nhóm:

```python
STRATEGIES: dict[str, Callable[[], Any]] = {
    "fixed": lambda: FixedSizeChunker(chunk_size=CHUNK_SIZE, overlap=50),
    "sentence": lambda: SentenceChunker(max_sentences_per_chunk=4),
    "recursive": lambda: RecursiveChunker(chunk_size=CHUNK_SIZE),
    "heading": lambda: HeadingChunker(chunk_size=CHUNK_SIZE),   # <-- thêm dòng này
}
```

### So Sánh Giữa Các Thành Viên

> **Lượt đo chung — cả bốn chiến lược trên CÙNG MỘT backend** `gemini-embedding-001`, cùng corpus `data/warranty/`, cùng 5 câu hỏi, `chunk_size=600`, `top_k=3`. Đây là bảng dùng để so sánh giữa các thành viên, vì chỉ khi mọi chiến lược chạy trên cùng một embedder thì thứ hạng mới có nghĩa.
>
> Lệnh chạy: `python bench.py --compare` với `EMBEDDING_PROVIDER=gemini`.

| Thành viên | Chiến lược (Strategy) | Chunks | Dài TB (min–max) | Điểm truy xuất (/10) | Top-1 | MRR |
|-----------|----------|--------|------------------|----------------------|-------|-----|
| **Nguyễn Phúc Huy** | **Heading/Section** + audience filter | 121 | 393 (17–669) | **7/10** | **3/5** | **0.700** |
| Hoàng Đức Dũng | Sentence (4 câu/chunk) + audience filter | 104 | 438 (118–870) | 6/10 | 2/5 | 0.600 |
| Ngô Hoàng Thụy Khuê | Recursive + audience filter | 92 | 493 (141–599) | 5/10 | 2/5 | 0.467 |
| *(đối chứng)* | Fixed-size + overlap 50 | 85 | 586 (199–600) | 5/10 | 2/5 | 0.467 |

**Chấm từng câu (2 điểm/câu theo `docs/SCORING.md`):**

| Câu | Dạng hỏi | fixed | **heading** | recursive | sentence | Chiến lược tốt nhất cho câu này |
|---|---|---|---|---|---|---|
| 1 | hỏi điều kiện | 0/2 | 0/2 | 0/2 | **2/2** | **chỉ Sentence** |
| 2 | tra số liệu | **2/2** | **2/2** | **2/2** | 0/2 | cả ba, trừ Sentence |
| 3 | hỏi quy trình | 0/2 | **1/2** | **1/2** | **1/2** | ba chiến lược cùng đạt 1/2 |
| 4 | liệt kê | 1/2 | **2/2** | 0/2 | 1/2 | **chỉ Heading đạt 2/2** |
| 5 | cần lọc metadata | **2/2** | **2/2** | **2/2** | **2/2** | cả bốn |
| | **Tổng** | **5/10** | **7/10** | **5/10** | **6/10** | |

**Điểm mạnh / điểm yếu từng thành viên:**

- **Nguyễn Phúc Huy — Heading/Section (7/10, top-1 3/5, MRR 0.700).** Mạnh: **chiến lược duy nhất lấy được câu 4 với điểm tuyệt đối**, và đây cũng là câu mà cả ba chiến lược kia đều trượt hoặc chỉ đạt 1/2. Chunk luôn mang tiêu đề mục nên tự mô tả được nó nói về gì — câu 2 và câu 5 đều retrieve đúng gold ở top-1 với chunk mở đầu bằng chính tiêu đề của mục chứa đáp án. Yếu: trượt câu 1 (top-1 là chunk tiêu đề tài liệu, không mang con số "15/30 ngày") vì chia quá tay — có chunk chỉ 17 ký tự, và đây là chiến lược nhiều chunk nhất (121) nên chi phí embedding cao nhất.
- **Hoàng Đức Dũng — Sentence (6/10, top-1 2/5, MRR 0.600).** Mạnh: **chiến lược duy nhất lấy được câu 1** — đáp án "*15 hoặc 30 ngày*" gói gọn trong một câu văn, và chunk theo câu giữ trọn câu đó. Cũng đạt 1/2 ở câu 4 — tốt hơn recursive và ngang heading ở câu 3. Yếu: trượt hoàn toàn câu 2 dù đáp án "02 ngày làm việc" nằm trong chunk (`tiki-seller-warranty-faq#23`) — chunk đếm đủ 4 câu rồi cắt nên vắt qua hai mục FAQ, embedding lai hai chủ đề và không khớp hẳn câu hỏi nào.
- **Ngô Hoàng Thụy Khuê — Recursive (5/10, top-1 2/5, MRR 0.467).** Mạnh: bám ranh giới đoạn `\n\n` nên lấy đúng mục 8 ở top-1 cho câu 2. Yếu: **trượt cả câu 1 và câu 4**, và ở câu 4 thì top-1 lại rơi vào mục *"Những trường hợp **không** được bảo hành"* — đúng chủ đề nhưng ngược nghĩa. Chunk dài (493 ký tự) làm loãng tín hiệu.
- *(Đối chứng)* **Fixed-size + overlap 50 (5/10).** Ngang điểm recursive nhưng vì lý do khác: chunk dài nhất (586 ký tự) nên vô tình chứa đủ ngữ cảnh ở câu 2 và câu 5, nhưng cắt thuần theo bộ đếm ký tự nên không đảm bảo ranh giới ngôn ngữ.

> **Lưu ý về lượt đo trước đó.** Ở lượt chạy đầu, nhóm đo trên `text-embedding-3-small` và nhận `recursive 6/10 · sentence 5/10 · fixed_size 2/10`. Lượt đo chung trên `gemini-embedding-001` cho `recursive 5/10 · sentence 6/10 · fixed_size 5/10` — tức **`recursive` và `sentence` đổi thứ hạng**, và `fixed_size` thay đổi mạnh nhất. Hai lượt không mâu thuẫn: chúng là hai embedder khác nhau, và chính điều đó là một phát hiện của nhóm (xem mục 4). Vì vậy bảng so sánh giữa các thành viên dùng lượt đo chung, còn số của lượt đầu được ghi lại ở mục 4 như bằng chứng cho việc kết quả phụ thuộc embedder.

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**
> **`heading` nhỉnh nhất (7/10, top-1 3/5, MRR 0.700), nhưng khoảng cách với `sentence` chỉ là 1 điểm — và đó mới là kết luận đáng giá: không chiến lược nào thắng toàn diện.**
>
> Bảng từng câu cho thấy mỗi chiến lược có một câu "của riêng nó":
> - **câu 1** chỉ `sentence` lấy được (2/2, ba chiến lược kia 0/2) — đáp án gói trong một câu văn nằm giữa đoạn dài;
> - **câu 4** chỉ `heading` lấy được với điểm tuyệt đối (recursive 0/2, fixed và sentence 1/2) — đáp án nằm ở mục "1. Điều kiện bảo hành", phải tách khỏi mục "2. Những trường hợp **không** được bảo hành";
> - **câu 2 và câu 5** gần như mọi chiến lược đều đạt, vì đáp án nằm gọn trong một mục có tiêu đề trùng từ khoá với câu hỏi.
>
> Lý do `heading` nhỉnh không phải vì nó "cắt khéo" hơn, mà vì nó **dùng đúng cấu trúc mà người soạn văn bản đã tạo sẵn**: ranh giới mục chính là ranh giới ngữ nghĩa. `RecursiveChunker` ưu tiên `\n\n` nên phần lớn thời gian cũng bám được ranh giới mục, nhưng khi một mục dài hoặc đoạn văn không có dòng trống thì nó gộp hai mục vào một chunk — đúng thứ xảy ra ở câu 4. `FixedSizeChunker` thì không tôn trọng ranh giới nào cả.
>
> **Kết luận cho hệ thống thật:** không chọn một rồi bỏ phần còn lại, mà **kết hợp hai tầng** — cắt theo cấu trúc (heading) trước, rồi trong mỗi mục dài mới cắt tiếp theo câu, **gắn lại tiêu đề mục vào từng mảnh con**, và **gộp các mục quá ngắn (< ~200 ký tự) vào mục kề**. Cách này giữ được cả ưu điểm bám cấu trúc của `heading` lẫn mật độ thông tin của `sentence`, đồng thời tránh cả hai kiểu hỏng đã quan sát được: chunk quá to làm loãng tín hiệu (câu 1 và 4 của `fixed_size`/`recursive`), chunk quá nhỏ làm mất con số (câu 1 của `heading`).

**Failure case thật đã quan sát:**
> **Câu hỏi hỏng:** câu 4 — *"Sản phẩm cần thỏa những điều kiện nào để được bảo hành miễn phí?"*, chạy với `RecursiveChunker` + filter `audience=buyer`. Kết quả 0/2: chunk chứa gold xếp hạng **7 trên 23** ứng viên, không lọt top-3. Top-1 lại là `shopee-warranty-buyer#2` — mục **"Những trường hợp *không* được bảo hành"**, tức đúng chủ đề nhưng **ngược nghĩa** với câu hỏi.
>
> **Vì sao hỏng — hai nguyên nhân chồng lên nhau.**
> *Thứ nhất, embedding không mã hoá phủ định.* Đo trực tiếp trên `text-embedding-3-small`: cosine giữa "Sản phẩm này được bảo hành" và "Sản phẩm này **không** được bảo hành" là **`+0.8853`** — cao hơn cả cặp thật sự đồng nghĩa "12 tháng" ↔ "một năm" (`+0.6641`). Chữ "không" là token ngắn, tần suất cao, đóng góp rất ít vào vector. Với model, mục "điều kiện được bảo hành" và mục "trường hợp không được bảo hành" gần như là một.
> *Thứ hai, đáp án bị pha loãng trong chunk.* Chunk chứa gold (`shopee-warranty-buyer#0`) mở đầu bằng tiêu đề tài liệu và đoạn phạm vi áp dụng — một danh sách dài tên thương hiệu: *"Samsung Official Store, Apple Flagship Store, LG Official Store, Electrolux, Philips, Viettel Store, FPTShop..."*. Câu "hội đủ các điều kiện sau" nằm ở cuối chunk. Embedding của cả chunk bị danh sách thương hiệu chi phối nên không giống câu hỏi về điều kiện bảo hành.
>
> **Đề xuất sửa, theo thứ tự ưu tiên:**
> 1. **Chunk theo heading.** ✅ **Đã làm** (xem "Thành viên 3"). Kết quả đo được: câu 4 từ **0/2 lên 2/2**, và `heading` là chiến lược duy nhất lấy được câu này. Tách "## 1. Điều kiện bảo hành" khỏi "## 2. Những trường hợp không được bảo hành" và khỏi đoạn phạm vi áp dụng đã loại bỏ cả hai nguyên nhân cùng lúc.
> 2. **Bỏ phần mở đầu tài liệu** (tiêu đề + phạm vi áp dụng) trước khi chunk — rẻ nhất, vá được nguyên nhân thứ hai. Chưa làm; `HeadingChunker` hiện vẫn tạo một chunk riêng cho phần mở đầu, và chunk đó chính là thứ chiếm top-1 ở câu 1.
> 3. **Thêm `overlap` cho `RecursiveChunker`.** Hiện nó cắt không chồng lấn nên mỗi thông tin chỉ có đúng một cơ hội lọt top-3. Chưa làm.
> 4. Với vấn đề phủ định thì chunking không giải quyết được — cần rerank hoặc để LLM đọc nhiều chunk hơn rồi tự loại mục ngược nghĩa.

**Lưu ý về embedding backend:**
> Phần lớn số đo trong báo cáo này chạy trên **embedding thật** — `OpenAIEmbedder` (`text-embedding-3-small`) — nên score số là đáng tin và so sánh được giữa các chiến lược. Agent dùng `gpt-4o-mini`, `top_k=3`. Riêng lượt đo của chiến lược `heading` và bảng kiểm chứng chéo chạy trên embedder local `paraphrase-multilingual-MiniLM-L12-v2` (offline, không cần key) — như đã nêu ở cảnh báo phía trên, **thứ hạng giữa hai backend không giống nhau**, nên cần chạy lại để chốt.
>
> Nhóm **đã** thử `MockEmbedder` ở giai đoạn đầu và ghi lại để đối chiếu: nó băm MD5 chuỗi rồi sinh số giả ngẫu nhiên nên hoàn toàn không mang ngữ nghĩa. Bằng chứng: câu hỏi "Chunking là gì?" cho top-1 là `rag_system_design.md` (score 0.150) trong khi `chunking_experiment_report.md` — file đúng chủ đề — xếp thứ ba với 0.025. Nếu buộc phải dùng mock, mọi kết luận về thứ hạng top-k đều vô nghĩa và phần phân tích phải chuyển sang các chỉ số không phụ thuộc embedding: `count`, `avg_length`, độ mạch lạc của chunk.
>
> Một cái bẫy đã gặp thật và đáng cảnh báo: `main.py` nuốt exception khi khởi tạo embedder và âm thầm rơi về mock. Nhóm từng chạy với `.env` đặt `EMBEDDING_PROVIDER=openai` nhưng chưa cài gói `openai`, và không hề biết mình đang đo bằng mock. Vì vậy `bench.py` được viết để **cảnh báo to** khi rơi về mock thay vì im lặng.

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

> **Đúng 5 câu hỏi**, đa dạng, có thể kiểm chứng; **ít nhất 1 câu** cần lọc metadata mới trả lời tốt. Đây là bộ câu hỏi chung cho mọi thành viên chạy.

| # | Câu hỏi (Query) | Câu trả lời chuẩn (Gold Answer) | Chunk nào chứa thông tin? |
|---|-------|-------------------------------|--------------------------|
| 1 | Theo chính sách Hoàng Hà Mobile, khách hàng được đổi mới miễn phí trong thời gian nào? | Trong 15 hoặc 30 ngày đầu kể từ ngày mua, tùy theo dòng sản phẩm, nếu sản phẩm được xác nhận lỗi phần cứng do nhà sản xuất thì được đổi mới miễn phí 100%. | `hoanghamobile-warranty-buyer.md`, mục "a) Trong 15 hoặc 30 ngày đầu kể từ ngày mua" |
| 2 | Trong mô hình Seller Center, Nhà Bán có bao nhiêu ngày làm việc để xác nhận phương án xử lý yêu cầu đổi trả? | 02 ngày làm việc kể từ khi mã yêu cầu ghi nhận trạng thái "Cần Nhà Bán phản hồi". | `tiki-seller-warranty-faq.md`, mục 8 "Nhà Bán có thời gian bao lâu để xác nhận yêu cầu đổi, trả, bảo hành?" |
| 3 | Nếu Nhà Bán không phản hồi, Tiki sẽ xử lý yêu cầu của Khách Hàng như thế nào? | Tiki sẽ hoàn tiền cho Khách Hàng và không chịu trách nhiệm trong trường hợp Nhà Bán không hoặc không thể thu hồi hàng hóa; số tiền hoàn trả được cấn trừ vào kỳ thanh toán tiếp theo của Nhà Bán. | `tiki-seller-warranty-faq.md`, **mục 6** "Nếu Nhà Bán không phản hồi..." — *không phải* mục 4 (xem ghi chú bên dưới) |
| 4 | Sản phẩm cần thỏa những điều kiện nào để được bảo hành miễn phí? | Lỗi kỹ thuật do nhà sản xuất; còn trong thời hạn bảo hành; có hóa đơn điện tử hoặc mã đơn hàng; với hàng điện gia dụng thì phiếu/tem bảo hành và tem niêm phong còn nguyên vẹn. | `shopee-warranty-buyer.md`, mục 1 "Điều kiện bảo hành" |
| 5 | Thời gian bảo hành tối đa là bao lâu? *(câu cần lọc metadata)* | **Phía seller:** Nhà Bán cam kết tối đa không quá 30 ngày. **Phía buyer:** 12 tháng máy mới (Hoàng Hà) / 20–45 ngày làm việc (Shopee). | `tiki-seller-warranty-faq.md`, mục 5 "Thời gian Nhà Bán cam kết bảo hành là bao lâu?" |

### Tổng hợp chất lượng truy xuất của nhóm

> Cách chấm (theo `docs/SCORING.md`): **2 điểm/câu** — top-3 chứa chunk liên quan + agent trả lời đúng (2), có liên quan nhưng thiếu/không ở top-1 (1), không có trong top-3 (0).

| # | Câu hỏi | Chiến lược tốt nhất cho câu này | Có chunk liên quan trong top-3? | Ghi chú |
|---|---------|-------------------------------|-------------------------------|---------|
| 1 | Theo chính sách Hoàng Hà Mobile, khách hàng được đổi mới miễn phí trong thời gian nào? | **Sentence** (2/2) | Có — chỉ với Sentence | fixed 0/2, recursive 0/2, heading 0/2. Recursive lấy nhầm mục *bảo hành* thay vì mục *đổi mới 15/30 ngày*; heading lấy chunk tiêu đề tài liệu. Cả ba đều trượt vì đáp án "*15 hoặc 30 ngày*" nằm trong một mục rất ngắn, bị các đoạn dài hơn nhưng ít thông tin hơn đè trong xếp hạng. |
| 2 | Trong mô hình Seller Center, Nhà Bán có bao nhiêu ngày làm việc để xác nhận phương án xử lý yêu cầu đổi trả? | **Fixed / Heading / Recursive** (2/2) | Có | Chỉ Sentence trượt (0/2) dù đáp án "02 ngày làm việc" nằm trong chunk (`tiki-seller-warranty-faq#23`) — chunk đếm đủ 4 câu rồi cắt nên vắt qua hai mục FAQ, embedding lai hai chủ đề. |
| 3 | Nếu Nhà Bán không phản hồi, Tiki sẽ xử lý yêu cầu của Khách Hàng như thế nào? | **Heading / Recursive / Sentence** (1/2) | Một phần | Cả ba đều đưa chunk chứa đáp án vào top-3 nhưng không ở top-1, nên chỉ đạt 1/2. Câu này khó vì corpus có nhiều mục nói về "Nhà Bán không phản hồi / không xác nhận / từ chối" với hậu quả khác nhau. |
| 4 | Sản phẩm cần thỏa những điều kiện nào để được bảo hành miễn phí? | **Heading** (2/2) | Có — chỉ Heading đạt điểm tuyệt đối | recursive 0/2 (top-1 rơi vào mục *"những trường hợp **không** được bảo hành"*), fixed và sentence 1/2. Heading là chiến lược duy nhất tách được "## 1. Điều kiện bảo hành" khỏi "## 2. Những trường hợp không được bảo hành" — xem failure case ở mục 2. |
| 5 | Thời gian bảo hành tối đa là bao lâu? | **Cả bốn đều 2/2** | Có | Câu duy nhất mọi chiến lược đều đạt điểm tuyệt đối. Nhưng chỉ đạt **khi có** `metadata_filter` — xem bảng A/B bên dưới. |

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**
> **Có, nhưng chỉ ở đúng một câu — và đó là điều đáng nói.** Chạy A/B thật (bảng dưới) trên cả 5 câu: **4/5 câu cho kết quả y hệt nhau dù có lọc hay không**. Lý do là chúng tự phân biệt bằng từ vựng — "Hoàng Hà Mobile" chỉ có trong tài liệu buyer, "Nhà Bán"/"Seller Center" chỉ có trong tài liệu seller — nên embedding đã tách đúng, filter thành thừa.
>
> **Câu 5 là câu duy nhất filter thực sự quyết định đúng/sai:** *"Thời gian bảo hành tối đa là bao lâu?"* không nêu người hỏi là ai, trong khi hai phía corpus cùng nói về thời hạn bảo hành bằng cùng từ vựng nhưng cho đáp án khác nhau — buyer: 12 tháng máy mới / 20–45 ngày làm việc; seller: tối đa 30 ngày. Không lọc thì top-3 lẫn cả hai phía và agent trả lời sai đối tượng.
>
> **Bài học quan trọng hơn cả câu trả lời:** một câu hỏi đã chứa từ khóa đặc trưng của một phía thì **không chứng minh được gì** về giá trị của metadata filter. Muốn đo tác dụng của filter, phải cố tình viết câu hỏi *mơ hồ về đối tượng*. Bộ 5 câu đầu tiên của nhóm không có câu nào như vậy, chạy A/B ra kết quả giống hệt nhau ở cả 5 câu, và nhóm đã phải thay câu 5 để có bằng chứng.

### A/B kiểm chứng filter `audience` (bắt buộc)

| Câu hỏi | Với filter | Không filter | Kết luận |
|---|---|---|---|
| **Câu 5** — "Thời gian bảo hành tối đa là bao lâu?" *(không nêu đối tượng)* | `faq#4`, `faq#14`, `faq#17` — **cả 3 đều seller** → **2/2** | `faq#4`, `hoanghamobile#1`, `shopee#4` — **2/3 slot bị buyer chiếm** → 2/2 | **KHÁC NHAU.** Top-1 vẫn đúng nên điểm không đổi, nhưng ngữ cảnh đưa vào agent thì lẫn cả "12 tháng máy mới" (buyer) lẫn "tối đa 30 ngày" (seller) — đủ để agent trả lời sai đối tượng. Đây là bằng chứng chính. |
| Câu 1 — "Theo chính sách **Hoàng Hà Mobile**, khách hàng được đổi mới miễn phí..." | `hoanghamobile#10`, `hoanghamobile#0`, `hoanghamobile#3` | `hoanghamobile#10`, `hoanghamobile#0`, `hoanghamobile#3` | **GIỐNG HỆT.** Tên "Hoàng Hà Mobile" chỉ xuất hiện ở tài liệu buyer nên embedding tự tách được. |
| Câu 2, 3, 4 — đều chứa "**Nhà Bán**" / "Seller Center" hoặc hỏi về chính sách buyer | (xem `ket_qua_benchmark.txt`) | Trùng với cột bên trái | **GIỐNG HỆT** ở cả ba câu. Filter không thay đổi gì. |

> **Kết luận:** filter `audience` **không phải lúc nào cũng cần** — nó chỉ tạo khác biệt khi câu hỏi mơ hồ về đối tượng, tức khi embedding một mình không đủ để phân biệt. Nhưng đúng vào những lúc đó thì nó là thứ **duy nhất** cứu được câu trả lời, vì `audience` là thông tin nằm ở metadata chứ không nằm trong ngữ nghĩa câu văn.

**Bổ sung: chạy A/B cho cả bốn chiến lược ở câu 5** (lượt đo chung trên `gemini-embedding-001`) — filter tạo khác biệt ở **cả bốn**, tức đây là đặc tính của câu hỏi chứ không phải của cách chunk:

| Chiến lược | Câu 5 — có lọc | Câu 5 — không lọc | Kết luận |
|---|---|---|---|
| **heading** | `faq#7`, `faq#9`, `sd#2` → **2/2** | `shopee#6`, `hoanghamobile#13`, `faq#7` → **1/2** | **Khác hẳn — filter quyết định điểm số.** Không lọc thì 2/3 slot top-3 bị tài liệu buyer chiếm; chunk đúng (`faq#7`) bị đẩy xuống hạng 3 nên chỉ còn 1/2. Có lọc thì cả 3 slot là seller và đúng (2/2). |
| fixed | `faq#4`, `dropship#2`, `faq#5` → 2/2 | `faq#4`, `shopee#2`, `shopee#4` → 2/2 | Điểm không đổi nhưng 2/3 slot bị buyer chiếm — ngữ cảnh đưa vào agent bị nhiễm. |
| recursive | `faq#4`, `dropship#2`, `fbt#5` → 2/2 | `shopee#4`, `faq#4`, `hoanghamobile#10` → 1/2 | Khác — không lọc thì chunk đúng rơi xuống hạng 2. |
| sentence | `faq#6`, `fbt#7`, `faq#4` → 2/2 | `faq#6`, `shopee#5`, `hoanghamobile#12` → 2/2 | Điểm không đổi (chunk đúng vẫn top-1) nhưng 2/3 slot còn lại là buyer — ngữ cảnh nhiễm. |

> Bằng chứng mạnh nhất nằm ở `heading` và `recursive`: không lọc thì chunk chứa đáp án **bị đẩy khỏi top-1**, và với `heading` thì tụt hẳn xuống hạng 3. Đây là lần đầu nhóm đo được filter làm **thay đổi điểm số** chứ không chỉ thay đổi thành phần ngữ cảnh.

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**
> **1. Embedding không mã hoá phủ định.** Đo trên `text-embedding-3-small`: cosine giữa "Sản phẩm này **được** bảo hành" và "Sản phẩm này **không** được bảo hành" là `+0.8853` — **cao hơn** cả cặp thật sự đồng nghĩa "12 tháng" ↔ "một năm" (`+0.6641`). Hệ quả đã xảy ra thật trong benchmark: câu 4 hỏi *điều kiện được* bảo hành nhưng top-1 là mục *"những trường hợp không được bảo hành"*. Và cũng chính vì thế mà **chunking theo cấu trúc là cách chữa hiệu quả nhất** cho lỗi này — tách hai mục ra thì embedding không cần phân biệt "có/không" nữa, chỉ cần khớp tiêu đề.
>
> **2. Chấm ở mức `doc_id` thổi phồng kết quả.** Cùng một lần chạy, chấm "tài liệu gold có trong top-3 không" cho **5/5 ở cả bốn chiến lược** — bảng so sánh trở nên vô dụng. Chuyển sang chấm mức nội dung (chunk phải chứa một chuỗi đặc trưng trích nguyên văn từ tài liệu) thì điểm tụt xuống **5/10 – 7/10** và các chiến lược mới tách nhau ra. **Chênh lệch giữa hai cách chấm chính là phát hiện đáng giá nhất của buổi lab.**
>
> **3. Không chiến lược chunking nào thắng toàn diện — mỗi chiến lược "sở hữu" một câu khác nhau.** Ở lượt đo chung: `sentence` là chiến lược **duy nhất** lấy được câu 1; `heading` là chiến lược **duy nhất** đạt điểm tuyệt đối ở câu 4; câu 2 thì cả ba chiến lược còn lại đều đạt còn `sentence` trượt; câu 5 thì cả bốn đều đạt. Tổng điểm che mất hoàn toàn cấu trúc này — chỉ chấm từng câu mới thấy. Đáng chú ý là `recursive` **không sở hữu câu nào riêng**: ở lượt OpenAI nó nhỉnh nhất (6/10) nhưng sang lượt đo chung nó tụt xuống 5/10 và ngang bằng chiến lược đối chứng `fixed_size`.
>
> **4. Retrieval trượt mà agent vẫn trả lời đúng — và ngược lại.** Ở câu 2 với chiến lược sentence, chunk chứa đáp án xếp hạng 12/50 và không lọt top-3, nhưng agent vẫn trả lời đúng nhờ các chunk lân cận nhắc tới cùng mốc "02 ngày làm việc". Lần này là may — lần khác chunk lân cận có thể chứa con số của một điều khoản khác và agent sẽ bịa ra đáp án sai mà vẫn trôi chảy. Chiều ngược lại cũng đã gặp: ở câu 5, bước retrieval **đúng** (top-1 chứa nguyên văn đáp án) nhưng agent vẫn trả lời sai vì `KnowledgeBaseAgent.answer` truy xuất lại **không kèm filter** và kéo về cả tài liệu buyer. Bài học: **đừng đánh giá hệ thống RAG chỉ bằng câu trả lời cuối cùng**, và **bộ lọc metadata phải được áp ở cả bước retrieval lẫn bước sinh câu trả lời** — nếu chỉ áp một đầu thì công sức gắn metadata bị vô hiệu hoá ở đúng chỗ quan trọng nhất.

**Bài học rút ra khi so sánh trong nhóm:**
> Cùng corpus, cùng 5 câu hỏi, chỉ khác **một dòng chọn chunker** — kết quả chênh nhau rõ rệt: ở lượt đo chung là `fixed_size` 5/10, `recursive` 5/10, `sentence` 6/10, `heading` 7/10. Việc ép cả nhóm chạy chung một công cụ đo (`bench.py`) và chỉ được đổi đúng dòng đó là quyết định quan trọng nhất về mặt phương pháp; nếu mỗi người tự viết script riêng thì bốn con số này không so sánh được với nhau.
>
> Nhưng bài học lớn nhất lại đi ngược trực giác ban đầu của nhóm: **chọn chiến lược tốt nhất là câu hỏi sai**. Mỗi chiến lược thắng ở một câu khác nhau — `sentence` giữ câu 1, `heading` giữ câu 4, và cả bốn cùng đạt câu 5. Điều đó nói rằng cách chia nhỏ văn bản nên phụ thuộc vào **cấu trúc tài liệu** và vào **dạng câu hỏi**, chứ không phải chọn một lần rồi áp cho mọi thứ.
>
> Một bài học thực tế nữa: nhóm suýt ghi số nhiễu vào báo cáo vì `main.py` âm thầm rơi về `MockEmbedder` khi thiếu gói `openai`. Công cụ đo phải **la lớn khi nó đang đo sai**, chứ không được im lặng.
>
> **Và bài học đắt nhất của lượt này: kết quả không độc lập với embedder.** Nhóm có ba lượt đo trên ba backend khác nhau, và thứ hạng đảo lộn:
>
> | Backend | fixed | recursive | sentence | heading |
> |---|---|---|---|---|
> | `text-embedding-3-small` (lượt đầu) | 2/10 | **6/10** | 5/10 | — |
> | `gemini-embedding-001` (lượt đo chung) | 5/10 | **5/10** | **6/10** | **7/10** |
> | MiniLM-L12-v2 local | 6/10 | 5/10 | 4/10 | 8/10 |
>
> `recursive` và `sentence` **đổi thứ hạng ở cả ba lượt**, còn `fixed_size` dao động mạnh nhất (2 → 5 → 6). Nghĩa là **mọi kết luận kiểu "chiến lược X tốt hơn Y" đều chỉ đúng trong phạm vi một embedder**. Muốn so sánh giữa các thành viên thì **bắt buộc cả nhóm phải chạy trên cùng một backend** — nếu không thì đang so ba thí nghiệm khác nhau. Đây là lý do nhóm chạy lại toàn bộ 4 chiến lược trên một backend duy nhất trước khi kết luận.

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**
> **1. Chunk theo heading, và gắn lại tiêu đề vào từng mảnh con.** ✅ **Đã làm** (xem "Thành viên 3"). Đây là thay đổi có tác động lớn nhất: nó giải quyết trực tiếp failure case ở mục 2 (mục *'điều kiện được bảo hành'* bị dính chung chunk với đoạn phạm vi áp dụng đầy tên thương hiệu) và đưa câu 4 từ 0/2 lên 2/2. Nhưng kết quả đo cũng cho thấy cắt theo heading **vẫn chưa đủ**: cần thêm bước **gộp các mục quá ngắn (< ~200 ký tự)** để không lặp lại lỗi ở câu 1, và **bỏ riêng phần mở đầu tài liệu** (tiêu đề + phạm vi áp dụng) vì chunk đó đang chiếm top-1 ở câu 1 mà không mang thông tin.
>
> **2. Viết câu hỏi đánh giá *trước*, rồi mới thiết kế chunking.** Nhóm làm ngược lại và trả giá: bộ 5 câu đầu tiên không có câu nào thực sự cần `metadata_filter`, chạy A/B ra kết quả giống hệt nhau ở cả 5 câu, phải viết lại. Câu hỏi đánh giá xác định cái mình đang tối ưu — chọn sau thì chỉ là hợp thức hoá kết quả đã có.
>
> **3. Đối chiếu gold answer với đúng câu chữ của câu hỏi.** Nhóm từng chấm oan một câu 0/2 vì gold trỏ nhầm vào mục 4 trong khi câu hỏi dùng chữ của mục 6 — hai điều khoản khác điều kiện kích hoạt và khác hậu quả. Retrieval hoàn toàn đúng, chỉ gold sai. Với corpus quy định có nhiều điều khoản gần giống nhau, **chấm tự động chỉ đáng tin bằng chất lượng của gold**.
>
> **4. Thêm `overlap` cho chunker.** Hiện mỗi thông tin chỉ có đúng một cơ hội lọt top-3; nếu nó nằm gần ranh giới chunk thì coi như mất.
>
> **5. Chốt một embedder cho cả nhóm trước khi chia nhau chạy.** Đây là bài học mới rút ra ở lượt này: kết quả đổi thứ hạng khi đổi embedder, nên "mỗi người chạy một máy với một key khác nhau" là cách chắc chắn nhất để có một bảng so sánh vô nghĩa.

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Lựa chọn tài liệu (Document Set Quality) | 10 / 10 |
| Thiết kế chiến lược (Strategy Design) | 15 / 15 |
| Chất lượng truy xuất (Retrieval Quality) | 8 / 10 |
| Thuyết trình (Demo) | 5 / 5 |
| **Tổng phần nhóm** | **38 / 40** |

> **Tự đánh giá trung thực, không cho điểm tối đa.**
> *Thiết kế chiến lược 15/15:* bốn chiến lược được đo trên **cùng một khung công bằng** — cùng corpus, cùng 5 câu hỏi, cùng một embedder — có baseline số thật, chấm từng câu, và phân tích được lý do thắng/thua của từng câu. **Đề xuất cải tiến số 1 ở mục 2 đã được hiện thực hoá và kiểm chứng bằng số đo** (câu 4: 0/2 → 2/2) chứ không còn dừng ở mức đề xuất. Nhóm cũng tự phát hiện và sửa một lỗi phương pháp của chính mình: lượt đo đầu chạy trên hai backend khác nhau, và đã chạy lại toàn bộ trên một backend duy nhất trước khi kết luận.
> *Chất lượng truy xuất 8/10:* chấm theo thang `docs/SCORING.md` ở mức nội dung, điểm thô cao nhất là **7/10** (`heading`, lượt đo chung). Trừ 2 điểm vì **câu 1 vẫn không đưa được chunk chứa đáp án vào top-3 ở 3/4 chiến lược**, và **câu 3 không chiến lược nào đạt quá 1/2** — hai câu này chỉ ra rằng chunking chưa giải quyết được trường hợp đáp án nằm trong một mục rất ngắn, hoặc khi corpus có nhiều điều khoản gần giống nhau.
