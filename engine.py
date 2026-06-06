"""PDF operations engine. All page numbers in public API are 1-based."""

import os
import re
from pypdf import PdfReader, PdfWriter


def get_page_count(pdf_path: str) -> int:
    """Return the number of pages in a PDF file."""
    reader = PdfReader(pdf_path)
    return len(reader.pages)


def parse_page_ranges(text: str) -> list:
    """Parse a page range string like '1-3,5-7' into [[1,3],[5,7]].

    Raises ValueError on invalid syntax.
    """
    if not text.strip():
        raise ValueError("页码范围不能为空")

    ranges = []
    parts = text.split(",")
    for part in parts:
        part = part.strip()
        if not part:
            raise ValueError("页码范围格式错误（多余的逗号）")
        m = re.match(r"^(\d+)\s*-\s*(\d+)$", part)
        if m:
            start, end = int(m.group(1)), int(m.group(2))
            if start < 1:
                raise ValueError(f"页码必须 >= 1，得到 {start}")
            if end < start:
                raise ValueError(f"起始页 {start} 不能大于结束页 {end}")
            ranges.append([start, end])
        elif re.match(r"^\d+$", part):
            n = int(part)
            if n < 1:
                raise ValueError(f"页码必须 >= 1，得到 {n}")
            ranges.append([n, n])
        else:
            raise ValueError(f"无法解析 '{part}'，期望格式如 1-3 或 5")
    return ranges


def parse_page_numbers(text: str) -> list:
    """Parse a page number list like '2,5,7' into [2,5,7].

    Raises ValueError on invalid syntax.
    """
    if not text.strip():
        raise ValueError("页码不能为空")

    numbers = []
    seen = set()
    parts = text.split(",")
    for part in parts:
        part = part.strip()
        if not part:
            raise ValueError("页码格式错误（多余的逗号）")
        if not re.match(r"^\d+$", part):
            raise ValueError(f"无效页码 '{part}'，页码应为数字")
        n = int(part)
        if n < 1:
            raise ValueError(f"页码必须 >= 1，得到 {n}")
        if n in seen:
            raise ValueError(f"页码 {n} 重复了")
        seen.add(n)
        numbers.append(n)
    return sorted(numbers)


def _unique_path(dirpath: str, filename: str) -> str:
    """Return a unique file path in dirpath, appending _1, _2 etc. if needed."""
    base, ext = os.path.splitext(filename)
    path = os.path.join(dirpath, filename)
    if not os.path.exists(path):
        return path
    i = 1
    while True:
        path = os.path.join(dirpath, f"{base}_{i}{ext}")
        if not os.path.exists(path):
            return path
        i += 1


def _validate_pages_against_total(total_pages: int, pages: list, label: str):
    """Check that all page numbers are <= total_pages."""
    for p in pages:
        if isinstance(p, list):
            _validate_pages_against_total(total_pages, p, label)
        elif p > total_pages:
            raise ValueError(
                f"{label}：页码 {p} 超出范围（PDF 共 {total_pages} 页）"
            )


def split_pdf(input_path: str, ranges: list, output_dir: str) -> list:
    """Split a PDF by page ranges. Each range [start, end] (1-based, inclusive)
    produces one output file.

    Returns list of output file paths.
    """
    reader = PdfReader(input_path)
    total = len(reader.pages)
    stem = os.path.splitext(os.path.basename(input_path))[0]
    results = []

    for start, end in ranges:
        if end > total:
            raise ValueError(
                f"页码范围 {start}-{end} 超出 PDF 总页数 ({total} 页)"
            )

        writer = PdfWriter()
        for i in range(start - 1, end):
            writer.add_page(reader.pages[i])

        filename = f"{stem}_split_{start}_{end}.pdf"
        out_path = _unique_path(output_dir, filename)
        with open(out_path, "wb") as f:
            writer.write(f)
        results.append(out_path)

    return results


def merge_pdfs(input_paths: list, output_path: str) -> str:
    """Concatenate PDFs in the order given. Returns the output path."""
    merger = PdfWriter()
    for path in input_paths:
        merger.append(path)
    with open(output_path, "wb") as f:
        merger.write(f)
    return output_path


def delete_pages(input_path: str, pages_to_delete: list, output_dir: str) -> str:
    """Create a new PDF omitting the specified pages (1-based).
    Returns the output path.
    """
    reader = PdfReader(input_path)
    total = len(reader.pages)

    # Validate and convert to 0-based set
    delete_set = set()
    for p in pages_to_delete:
        if p > total:
            raise ValueError(
                f"要删除的页码 {p} 超出 PDF 总页数 ({total} 页)"
            )
        delete_set.add(p - 1)

    writer = PdfWriter()
    for i in range(total):
        if i not in delete_set:
            writer.add_page(reader.pages[i])

    stem = os.path.splitext(os.path.basename(input_path))[0]
    filename = f"{stem}_deleted.pdf"
    out_path = _unique_path(output_dir, filename)
    with open(out_path, "wb") as f:
        writer.write(f)
    return out_path


# ---------------------------------------------------------------------------
# Self-test (run with: python engine.py)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import tempfile

    # Create test PDFs
    tmpdir = tempfile.mkdtemp()
    print(f"Test directory: {tmpdir}")

    def _make_pdf(path, page_count):
        w = PdfWriter()
        for _ in range(page_count):
            w.add_blank_page(width=200, height=200)
        with open(path, "wb") as f:
            w.write(f)

    pdf_a = os.path.join(tmpdir, "a.pdf")
    pdf_b = os.path.join(tmpdir, "b.pdf")

    _make_pdf(pdf_a, 10)  # 10 pages
    _make_pdf(pdf_b, 5)   # 5 pages

    # Test get_page_count
    assert get_page_count(pdf_a) == 10
    assert get_page_count(pdf_b) == 5
    print("OK: get_page_count")

    # Test parse_page_ranges
    assert parse_page_ranges("1-3,5-7") == [[1, 3], [5, 7]]
    assert parse_page_ranges("1") == [[1, 1]]
    assert parse_page_ranges(" 2 - 4 , 6 ") == [[2, 4], [6, 6]]
    try:
        parse_page_ranges("")
        assert False, "should raise"
    except ValueError:
        pass
    try:
        parse_page_ranges("0-3")
        assert False, "should raise"
    except ValueError:
        pass
    print("OK: parse_page_ranges")

    # Test parse_page_numbers
    assert parse_page_numbers("2,5,7") == [2, 5, 7]
    assert parse_page_numbers("1") == [1]
    assert parse_page_numbers("3, 1") == [1, 3]  # sorted
    try:
        parse_page_numbers("2,2")
        assert False, "should raise"
    except ValueError:
        pass
    print("OK: parse_page_numbers")

    # Test split_pdf
    out_split = os.path.join(tmpdir, "out_split")
    os.makedirs(out_split, exist_ok=True)
    split_results = split_pdf(pdf_a, [[1, 3], [5, 7]], out_split)
    print(f"  Split results: {split_results}")
    assert len(split_results) == 2
    assert get_page_count(split_results[0]) == 3
    assert get_page_count(split_results[1]) == 3
    print("OK: split_pdf")

    # Test merge_pdfs
    out_merged = os.path.join(tmpdir, "merged.pdf")
    merge_pdfs([pdf_a, pdf_b], out_merged)
    assert get_page_count(out_merged) == 15
    print("OK: merge_pdfs")

    # Test delete_pages
    out_del = os.path.join(tmpdir, "out_delete")
    os.makedirs(out_del, exist_ok=True)
    deleted = delete_pages(pdf_a, [2, 5, 7], out_del)
    print(f"  Delete result: {deleted}")
    assert get_page_count(deleted) == 7  # 10 - 3 = 7
    print("OK: delete_pages")

    # Cleanup
    import shutil
    shutil.rmtree(tmpdir)
    print("\nAll tests passed.")
