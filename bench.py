#!/usr/bin/env python3
"""Benchmark retrieval on the warranty corpus (data/warranty).

Reads Markdown files with YAML front matter, splits the body with a selectable
chunking strategy, and runs the group's 5 benchmark queries through
EmbeddingStore.search_with_filter().

Each team member swaps only --strategy to test their own approach on the same
corpus and the same questions. Embeddings are cached on disk so re-runs and
extra strategies do not re-spend API quota.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv

from src.chunking import FixedSizeChunker, RecursiveChunker, SentenceChunker
from src.embeddings import (
    EMBEDDING_PROVIDER_ENV,
    GEMINI_EMBEDDING_MODEL,
    LOCAL_EMBEDDING_MODEL,
    OPENAI_EMBEDDING_MODEL,
    GeminiEmbedder,
    LocalEmbedder,
    OpenAIEmbedder,
    _mock_embed,
)
from src.models import Document
from src.store import EmbeddingStore

DEFAULT_DATA_DIR = Path("data/warranty")
DEFAULT_OUTPUT = Path("ket_qua_benchmark.txt")
DEFAULT_CACHE = Path(".bench_embed_cache.json")

BENCHMARK_QUERIES = [
    {
        "query": "Theo chính sách Hoàng Hà Mobile, khách hàng được đổi mới miễn phí trong thời gian nào?",
        "metadata_filter": {"audience": "buyer"},
        "expected_doc_ids": ["hoanghamobile-warranty-buyer"],
        "keywords": ["15", "30", "đổi mới"],
        "gold": (
            "Trong 15 hoặc 30 ngày đầu kể từ ngày mua, tùy theo dòng sản phẩm, nếu sản phẩm được xác nhận "
            "lỗi phần cứng do nhà sản xuất thì được đổi mới miễn phí 100%."
        ),
    },
    {
        "query": "Trong mô hình Seller Center, Nhà Bán có bao nhiêu ngày làm việc để xác nhận phương án xử lý yêu cầu đổi trả?",
        "metadata_filter": {"audience": "seller"},
        "expected_doc_ids": ["tiki-seller-warranty-faq", "tiki-seller-warranty-sd", "tiki-seller-warranty-dropship"],
        "keywords": ["02 ngày làm việc"],
        "gold": (
            "Nhà Bán có 02 ngày làm việc kể từ khi sản phẩm được cập nhật trạng thái cần Nhà Bán phản hồi để "
            "xác nhận phương án xử lý yêu cầu đổi, trả, bảo hành."
        ),
    },
    {
        "query": "Nếu Nhà Bán không phản hồi, Tiki sẽ xử lý yêu cầu của Khách Hàng như thế nào?",
        "metadata_filter": {"audience": "seller"},
        "expected_doc_ids": ["tiki-seller-warranty-faq"],
        "keywords": ["chủ động xử lý", "từ chối tiếp nhận"],
        "gold": (
            "Tiki sẽ chủ động xử lý theo yêu cầu Khách Hàng và được quyền từ chối tiếp nhận các khiếu nại của "
            "Nhà Bán; nếu không có lý do hợp lệ, Tiki có thể bồi thường cho Khách Hàng."
        ),
    },
    {
        "query": "Nhà Bán xác nhận phương án xử lý yêu cầu đổi trả qua đâu trong hệ thống?",
        "metadata_filter": {"audience": "seller"},
        "expected_doc_ids": ["tiki-seller-warranty-faq", "tiki-seller-warranty-sd", "tiki-seller-warranty-dropship"],
        "keywords": ["Seller Center", "Cần Nhà Bán phản hồi"],
        "gold": (
            "Nhà Bán xác nhận phương án xử lý qua hệ thống Seller Center, vào mục Đơn hàng > Đổi trả bảo hành, "
            "tab Cần Nhà Bán phản hồi."
        ),
    },
    {
        "query": "Theo quy trình đổi mới của Hoàng Hà Mobile, khách hàng cần làm gì trước khi nhận sản phẩm mới?",
        "metadata_filter": {"audience": "buyer"},
        "expected_doc_ids": ["hoanghamobile-warranty-buyer"],
        "keywords": ["thẩm định", "mang sản phẩm"],
        "gold": (
            "Khách hàng mang sản phẩm đến cửa hàng, nhân viên tiếp nhận và thẩm định lỗi ngay tại chỗ; nếu lỗi "
            "do nhà sản xuất và đủ điều kiện thì tiến hành đổi sản phẩm mới."
        ),
    },
]


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Split a Markdown file into front matter and body."""
    stripped = text.lstrip()
    if not stripped.startswith("---"):
        return {}, text

    lines = stripped.splitlines()
    if len(lines) < 3:
        return {}, text

    end_index = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_index = i
            break
    if end_index is None:
        return {}, text

    metadata: dict[str, str] = {}
    for raw in lines[1:end_index]:
        if not raw.strip() or ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        metadata[key.strip()] = value.strip().strip("\"'")

    return metadata, "\n".join(lines[end_index + 1 :])


def split_sections(text: str) -> list[str]:
    """Split Markdown by heading boundaries, keeping each heading with its section."""
    if not text.strip():
        return []

    lines = text.splitlines()
    sections: list[str] = []
    heading = ""
    body: list[str] = []

    def flush() -> None:
        nonlocal heading, body
        if heading or body:
            section = (heading.strip() + "\n\n" + "\n".join(body).strip()).strip()
            if section:
                sections.append(section)
        heading = ""
        body = []

    for line in lines:
        if line.startswith("#"):
            flush()
            heading = line.strip()
        else:
            body.append(line.rstrip())
    flush()
    return sections or [text.strip()]


def chunk_heading(text: str, chunk_size: int) -> list[str]:
    """Section-aware chunking: one chunk per heading, long sections split recursively."""
    chunks: list[str] = []
    for section in split_sections(text):
        if len(section) <= chunk_size:
            chunks.append(section)
            continue
        lines = section.splitlines()
        head = lines[0].strip() if lines and lines[0].startswith("#") else ""
        rest = "\n".join(lines[1:]).strip() if head else section
        for piece in RecursiveChunker(chunk_size=chunk_size).chunk(rest):
            chunks.append((head + "\n\n" + piece).strip() if head else piece)
    return chunks or [text.strip()]


def chunk_with(strategy: str, text: str, chunk_size: int) -> list[str]:
    if strategy == "heading":
        return chunk_heading(text, chunk_size)
    if strategy == "recursive":
        return RecursiveChunker(chunk_size=chunk_size).chunk(text)
    if strategy == "sentence":
        return SentenceChunker(max_sentences_per_chunk=4).chunk(text)
    if strategy == "fixed":
        return FixedSizeChunker(chunk_size=chunk_size, overlap=chunk_size // 5).chunk(text)
    raise ValueError(f"Unknown strategy: {strategy}")


class PacedEmbedder:
    """Cache embeddings on disk and pace API requests, retrying on rate limits.

    The free tier of gemini-embedding-001 allows ~100 requests per minute while the
    warranty corpus produces more chunks than that, so an unthrottled burst fails
    with HTTP 429.
    """

    def __init__(self, inner, cache_path: Path | None = None, min_interval: float = 0.7, max_retries: int = 6) -> None:
        self._inner = inner
        self._cache_path = cache_path
        self._min_interval = min_interval
        self._max_retries = max_retries
        self._last_call = 0.0
        self._dirty = False
        self._backend_name = getattr(inner, "_backend_name", inner.__class__.__name__)
        self._cache: dict[str, list[float]] = {}
        if cache_path and cache_path.exists():
            try:
                self._cache = json.loads(cache_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                self._cache = {}

    def _key(self, text: str) -> str:
        return hashlib.sha256(f"{self._backend_name}\x00{text}".encode()).hexdigest()

    @staticmethod
    def _is_rate_limit(error: Exception) -> bool:
        text = str(error)
        return "429" in text or "RESOURCE_EXHAUSTED" in text

    def _pause(self) -> None:
        gap = time.monotonic() - self._last_call
        if gap < self._min_interval:
            time.sleep(self._min_interval - gap)
        self._last_call = time.monotonic()

    def __call__(self, text: str) -> list[float]:
        key = self._key(text)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        for attempt in range(self._max_retries):
            self._pause()
            try:
                vector = self._inner(text)
            except Exception as error:
                if not self._is_rate_limit(error) or attempt == self._max_retries - 1:
                    raise
                time.sleep(15 * (attempt + 1))
                continue
            self._cache[key] = vector
            self._dirty = True
            return vector

        raise RuntimeError("embedding request failed after retries")

    def flush(self) -> None:
        if not self._cache_path or not self._dirty:
            return
        self._cache_path.write_text(json.dumps(self._cache), encoding="utf-8")
        self._dirty = False


def build_embedder(cache_path: Path | None):
    load_dotenv(override=False)
    provider = os.getenv(EMBEDDING_PROVIDER_ENV, "mock").strip().lower()
    if provider == "local":
        try:
            return PacedEmbedder(
                LocalEmbedder(model_name=os.getenv("LOCAL_EMBEDDING_MODEL", LOCAL_EMBEDDING_MODEL)),
                cache_path=cache_path,
                min_interval=0.0,
            )
        except Exception:
            return _mock_embed
    if provider == "openai":
        try:
            return PacedEmbedder(
                OpenAIEmbedder(model_name=os.getenv("OPENAI_EMBEDDING_MODEL", OPENAI_EMBEDDING_MODEL)),
                cache_path=cache_path,
            )
        except Exception:
            return _mock_embed
    if provider == "gemini":
        try:
            return PacedEmbedder(
                GeminiEmbedder(model_name=os.getenv("GEMINI_EMBEDDING_MODEL", GEMINI_EMBEDDING_MODEL)),
                cache_path=cache_path,
            )
        except Exception:
            return _mock_embed
    return _mock_embed


def build_documents(data_dir: Path, strategy: str, chunk_size: int) -> tuple[list[Document], int]:
    docs: list[Document] = []
    files = sorted(p for p in data_dir.glob("**/*.md") if p.is_file())
    for path in files:
        text = path.read_text(encoding="utf-8")
        frontmatter, body = parse_frontmatter(text)
        for index, chunk in enumerate(chunk_with(strategy, body or text, chunk_size)):
            metadata = dict(frontmatter)
            metadata["doc_id"] = frontmatter.get("doc_id") or path.stem
            metadata["source_file"] = path.name
            metadata["chunk_index"] = str(index)
            docs.append(Document(id=path.stem, content=chunk, metadata=metadata))
    return docs, len(files)


def count_keywords(keywords: list[str], text: str) -> int:
    lowered = text.lower()
    return sum(1 for keyword in keywords if keyword.lower() in lowered)


def run_strategy(data_dir: Path, strategy: str, chunk_size: int, embedder, compare_unfiltered: bool) -> tuple[str, dict]:
    documents, file_count = build_documents(data_dir, strategy, chunk_size)
    store = EmbeddingStore(collection_name=f"bench-{strategy}", embedding_fn=embedder)
    store.add_documents(documents)

    backend = getattr(embedder, "_backend_name", embedder.__class__.__name__)
    lines = [
        f"STRATEGY: {strategy} (chunk_size={chunk_size})",
        f"BACKEND: {backend}",
        f"Loaded {len(documents)} chunks from {file_count} markdown files.",
        "",
    ]

    lengths = [len(doc.content) for doc in documents]
    stats = {
        "chunks": len(documents),
        "avg_length": sum(lengths) / len(lengths) if lengths else 0.0,
        "doc_hits": 0,
        "full_hits": 0,
        "partial_hits": 0,
    }

    for number, item in enumerate(BENCHMARK_QUERIES, start=1):
        results = store.search_with_filter(item["query"], top_k=3, metadata_filter=item["metadata_filter"])
        doc_hit = any(r["metadata"].get("doc_id") in item["expected_doc_ids"] for r in results)
        top1_keywords = count_keywords(item["keywords"], results[0]["content"]) if results else 0
        top3_keywords = count_keywords(item["keywords"], " ".join(r["content"] for r in results))
        stats["doc_hits"] += int(doc_hit)
        stats["full_hits"] += int(top3_keywords == len(item["keywords"]))
        stats["partial_hits"] += int(0 < top3_keywords < len(item["keywords"]))

        lines.append(f"Q{number}: {item['query']}")
        lines.append(f"  FILTER: {item['metadata_filter']}")
        for rank, result in enumerate(results, start=1):
            snippet = re.sub(r"\s+", " ", result["content"][:260]).strip()
            lines.append(
                f"  {rank}. score={result['score']:.4f} doc_id={result['metadata'].get('doc_id')} "
                f"chunk={result['metadata'].get('chunk_index')}"
            )
            lines.append(f"     {snippet}")
        lines.append(f"  doc_id top-3: {'CO' if doc_hit else 'KHONG'}")
        lines.append(f"  tu khoa trong top-1: {top1_keywords}/{len(item['keywords'])}")
        lines.append(f"  tu khoa trong top-3: {top3_keywords}/{len(item['keywords'])}")
        lines.append(f"  GOLD: {item['gold']}")
        lines.append(f"  TỪ KHOÁ: {item['keywords']}")

        if compare_unfiltered:
            unfiltered = store.search(item["query"], top_k=3)
            ids = [r["metadata"].get("doc_id") for r in unfiltered]
            top1_unfiltered = count_keywords(item["keywords"], unfiltered[0]["content"]) if unfiltered else 0
            lines.append(f"  KHONG FILTER doc_id: {ids}")
            lines.append(f"  KHONG FILTER tu khoa top-1: {top1_unfiltered}/{len(item['keywords'])}")
        lines.append("")

    return "\n".join(lines), stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark retrieval for the warranty corpus.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--strategy", default="heading", choices=["heading", "recursive", "sentence", "fixed"])
    parser.add_argument("--chunk-size", type=int, default=650)
    parser.add_argument("--no-compare", action="store_true", help="Skip the unfiltered A/B comparison.")
    args = parser.parse_args()

    if not args.data_dir.exists():
        raise FileNotFoundError(f"Data directory not found: {args.data_dir}")

    embedder = build_embedder(args.cache)
    try:
        report, stats = run_strategy(
            args.data_dir, args.strategy, args.chunk_size, embedder, not args.no_compare
        )
    finally:
        if hasattr(embedder, "flush"):
            embedder.flush()

    header = (
        f"STRATEGY={args.strategy} chunks={stats['chunks']} avg_length={stats['avg_length']:.1f} "
        f"doc_id_hits={stats['doc_hits']}/5 keyword_full_hits={stats['full_hits']}/5 "
        f"keyword_partial_hits={stats['partial_hits']}/5"
    )
    args.output.write_text(header + "\n\n" + report + "\n", encoding="utf-8")
    print(header)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
