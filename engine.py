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


def rotate_pages(input_path: str, pages: list, angle: int, output_dir: str) -> list:
    """Rotate specified pages (1-based) by 90, 180, or 270 degrees clockwise.
    Saves the entire PDF with rotations applied to the selected pages.
    """
    reader = PdfReader(input_path)
    total = len(reader.pages)
    rotate_set = set()
    for p in pages:
        if p > total:
            raise ValueError(f"页码 {p} 超出 PDF 总页数 ({total} 页)")
        rotate_set.add(p - 1)

    writer = PdfWriter()
    for i in range(total):
        page = reader.pages[i]
        if i in rotate_set:
            page.rotate(angle)
        writer.add_page(page)

    stem = os.path.splitext(os.path.basename(input_path))[0]
    filename = f"{stem}_rotated_{angle}.pdf"
    out_path = _unique_path(output_dir, filename)
    with open(out_path, "wb") as f:
        writer.write(f)
    return [out_path]


def extract_pages(input_path: str, page_numbers: list, output_dir: str) -> str:
    """Extract specified pages (1-based) into a single new PDF."""
    reader = PdfReader(input_path)
    total = len(reader.pages)

    writer = PdfWriter()
    for p in page_numbers:
        if p > total:
            raise ValueError(f"页码 {p} 超出 PDF 总页数 ({total} 页)")
        writer.add_page(reader.pages[p - 1])

    stem = os.path.splitext(os.path.basename(input_path))[0]
    filename = f"{stem}_extracted.pdf"
    out_path = _unique_path(output_dir, filename)
    with open(out_path, "wb") as f:
        writer.write(f)
    return out_path


def compress_pdf(input_path: str, quality: str, output_dir: str) -> str:
    """Compress a PDF with three quality levels.

    quality: "low" (lossless), "medium" (moderate image compression),
             "high" (aggressive image compression, lossy).
    """
    reader = PdfReader(input_path)
    writer = PdfWriter()

    for page in reader.pages:
        page.compress_content_streams()
        writer.add_page(page)

    writer.compress_identical_objects()

    if quality in ("medium", "high"):
        img_quality = 40 if quality == "high" else 70
        _recompress_images(writer, quality=img_quality)

    stem = os.path.splitext(os.path.basename(input_path))[0]
    filename = f"{stem}_compressed.pdf"
    out_path = _unique_path(output_dir, filename)
    with open(out_path, "wb") as f:
        writer.write(f)
    return out_path


def _recompress_images(writer, quality):
    """Lossy recompress images in the writer using Pillow, if available."""
    try:
        from PIL import Image
        import io
    except ImportError:
        return

    for page in writer.pages:
        for key in list(page.images.keys()):
            img = page.images[key]
            if not img.data:
                continue
            try:
                im = Image.open(io.BytesIO(img.data))
                if im.mode not in ("RGB", "RGBA", "L"):
                    im = im.convert("RGB")
                buf = io.BytesIO()
                fmt = "PNG" if im.mode == "RGBA" else "JPEG"
                save_kw = {"format": fmt, "optimize": True}
                if fmt == "JPEG":
                    save_kw["quality"] = quality
                im.save(buf, **save_kw)
                img.replace(buf.getvalue())
            except Exception:
                continue


def encrypt_pdf(input_path: str, user_password: str, owner_password: str,
                output_dir: str) -> str:
    """Add an open password to a PDF. owner_password can be empty string."""
    reader = PdfReader(input_path)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    kwargs = {"user_password": user_password}
    if owner_password:
        kwargs["owner_password"] = owner_password
    writer.encrypt(**kwargs)

    stem = os.path.splitext(os.path.basename(input_path))[0]
    filename = f"{stem}_encrypted.pdf"
    out_path = _unique_path(output_dir, filename)
    with open(out_path, "wb") as f:
        writer.write(f)
    return out_path


def decrypt_pdf(input_path: str, password: str, output_dir: str) -> str:
    """Remove password protection from a PDF. Raises ValueError on wrong password."""
    reader = PdfReader(input_path)
    if not reader.is_encrypted:
        raise ValueError("PDF 未加密，无需解密")

    result = reader.decrypt(password)
    if result == 0:
        raise ValueError("密码错误，无法解密")

    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    stem = os.path.splitext(os.path.basename(input_path))[0]
    filename = f"{stem}_decrypted.pdf"
    out_path = _unique_path(output_dir, filename)
    with open(out_path, "wb") as f:
        writer.write(f)
    return out_path


def add_text_watermark(input_path: str, text: str, position: str, opacity: float,
                        rotation: float, font_size: int, output_dir: str) -> str:
    """Overlay a text watermark on every page."""
    from PIL import Image, ImageDraw

    reader = PdfReader(input_path)
    writer = PdfWriter()

    for page in reader.pages:
        w_pt = float(page.mediabox.width)
        h_pt = float(page.mediabox.height)
        pw, ph = int(w_pt), int(h_pt)

        stamp = Image.new("RGBA", (pw, ph), (255, 255, 255, 0))
        draw = ImageDraw.Draw(stamp)
        font = _load_cjk_font(font_size)
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        alpha = int(255 * opacity)

        for tx, ty in _wm_positions(position, tw, th, pw, ph):
            _draw_rotated_text(draw, text, tx, ty, tw, th, rotation, font,
                               fill=(128, 128, 128, alpha))

        _stamp_page(writer, page, stamp, w_pt, h_pt)

    stem = os.path.splitext(os.path.basename(input_path))[0]
    filename = f"{stem}_watermarked.pdf"
    out_path = _unique_path(output_dir, filename)
    with open(out_path, "wb") as f:
        writer.write(f)
    return out_path


def add_image_watermark(input_path: str, image_path: str, position: str,
                         opacity: float, scale: float, rotation: float,
                         output_dir: str) -> str:
    """Overlay an image watermark on every page."""
    from PIL import Image

    reader = PdfReader(input_path)
    writer = PdfWriter()
    wm_orig = Image.open(image_path).convert("RGBA")

    for page in reader.pages:
        w_pt = float(page.mediabox.width)
        h_pt = float(page.mediabox.height)
        pw, ph = int(w_pt), int(h_pt)

        short = min(pw, ph)
        wm_w = int(short * scale)
        wm_h = int(wm_w * wm_orig.height / wm_orig.width) if wm_orig.width else wm_w
        wm = wm_orig.resize((wm_w, wm_h), Image.LANCZOS)

        if opacity < 1.0:
            r, g, b, a = wm.split()
            a = a.point(lambda x: int(x * opacity))
            wm = Image.merge("RGBA", (r, g, b, a))

        if rotation != 0:
            wm = wm.rotate(rotation, expand=True, resample=Image.BICUBIC)

        stamp = Image.new("RGBA", (pw, ph), (255, 255, 255, 0))
        for tx, ty in _wm_positions(position, wm.width, wm.height, pw, ph):
            stamp.paste(wm, (tx, ty), wm)

        _stamp_page(writer, page, stamp, w_pt, h_pt)

    stem = os.path.splitext(os.path.basename(input_path))[0]
    filename = f"{stem}_watermarked.pdf"
    out_path = _unique_path(output_dir, filename)
    with open(out_path, "wb") as f:
        writer.write(f)
    return out_path


def _load_cjk_font(size):
    """Try to load a CJK-capable font, fall back to Pillow default."""
    from PIL import ImageFont
    import platform

    candidates = []
    if platform.system() == "Windows":
        candidates = ["C:/Windows/Fonts/simhei.ttf", "C:/Windows/Fonts/msyh.ttc"]
    elif platform.system() == "Darwin":
        candidates = ["/System/Library/Fonts/PingFang.ttc",
                      "/System/Library/Fonts/STHeiti Light.ttc"]
    else:
        candidates = ["/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"]

    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _wm_positions(position, w, h, pw, ph):
    """Compute (left, top) pixel positions for watermark placement."""
    margin = 20
    if position == "tile":
        pts = []
        y = margin
        while y < ph:
            x = margin
            while x < pw:
                pts.append((x, y))
                x += w + 80
            y += h + 80
        return pts
    anchors = {
        "top-left":      (margin, margin),
        "top-right":     (pw - w - margin, margin),
        "center":        ((pw - w) // 2, (ph - h) // 2),
        "bottom-left":   (margin, ph - h - margin),
        "bottom-right":  (pw - w - margin, ph - h - margin),
    }
    return [anchors.get(position, anchors["center"])]


def _draw_rotated_text(draw, text, x, y, tw, th, angle, font, fill):
    """Draw text centered at (x+tw/2, y+th/2) with rotation."""
    from PIL import Image
    pad = 20
    txt_img = Image.new("RGBA", (tw + pad * 2, th + pad * 2), (255, 255, 255, 0))
    d = ImageDraw.Draw(txt_img)
    d.text((pad, pad), text, font=font, fill=fill)
    if angle != 0:
        txt_img = txt_img.rotate(angle, expand=True, resample=Image.BICUBIC,
                                 center=(tw // 2 + pad, th // 2 + pad))
    cx, cy = x + tw // 2, y + th // 2
    draw._image.paste(txt_img, (cx - txt_img.width // 2, cy - txt_img.height // 2), txt_img)


def _stamp_page(writer, page, stamp_img, w_pt, h_pt):
    """Overlay a Pillow RGBA image as a stamp onto a pypdf page."""
    import io
    # Create a blank PDF page at the correct size, then use pypdf to merge
    # Save stamp image as PDF bytes (Pillow renders at image pixels / 72 DPI)
    rgb = stamp_img.convert("RGB")
    pdf_buf = io.BytesIO()
    rgb.save(pdf_buf, format="PDF", resolution=72.0)
    pdf_buf.seek(0)

    stamp_reader = PdfReader(pdf_buf)
    stamp_page = stamp_reader.pages[0]

    # If stamp page size differs (due to rendering), scale the stamp page
    # Pillow's PDF output has dimensions matching the image pixel size at 72 DPI
    # So if stamp_img is (w_pt, h_pt) pixels, the PDF page will be w_pt x h_pt points
    page.merge_page(stamp_page, over=True)
    writer.add_page(page)


def images_to_pdf(image_paths: list, output_path: str,
                  page_size: str = "auto") -> str:
    """Combine images into a single PDF. page_size can be 'auto', 'A4', or 'Letter'."""
    import io
    from PIL import Image

    page_sizes = {"A4": (595, 842), "Letter": (612, 792)}
    merger = PdfWriter()

    for impath in image_paths:
        im = Image.open(impath).convert("RGB")
        buf = io.BytesIO()
        if page_size == "auto":
            im.save(buf, format="PDF", resolution=72.0)
        else:
            w, h = page_sizes.get(page_size, (im.width, im.height))
            canvas = Image.new("RGB", (w, h), (255, 255, 255))
            ratio = min(w / im.width, h / im.height)
            nw, nh = int(im.width * ratio), int(im.height * ratio)
            im_rs = im.resize((nw, nh), Image.LANCZOS)
            ox, oy = (w - nw) // 2, (h - nh) // 2
            canvas.paste(im_rs, (ox, oy))
            canvas.save(buf, format="PDF", resolution=72.0)
        buf.seek(0)
        reader = PdfReader(buf)
        for pg in reader.pages:
            merger.add_page(pg)

    with open(output_path, "wb") as f:
        merger.write(f)
    return output_path


def pdf_to_images(input_path: str, output_dir: str, dpi: int = 200,
                   fmt: str = "PNG") -> list:
    """Convert each PDF page to an image using PyMuPDF (fitz)."""
    import fitz  # PyMuPDF

    doc = fitz.open(input_path)
    results = []
    stem = os.path.splitext(os.path.basename(input_path))[0]
    ext = fmt.lower()

    for i in range(len(doc)):
        page = doc[i]
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        filename = f"{stem}_page_{i + 1}.{ext}"
        out_path = _unique_path(output_dir, filename)
        if ext == "png":
            pix.save(out_path)
        else:
            pix.pil_save(out_path, optimize=True)
        results.append(out_path)

    doc.close()
    return results


def pdf_to_docx(input_path: str, output_path: str) -> str:
    """Convert a PDF to a Word (.docx) document. Requires pdf2docx."""
    try:
        from pdf2docx import Converter
    except ImportError:
        raise ImportError(
            "此功能需要安装 pdf2docx 库。请运行：pip install pdf2docx"
        )

    cv = Converter(input_path)
    cv.convert(output_path)
    cv.close()
    return output_path


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
