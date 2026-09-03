#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pillow",
#     "pymupdf",
#     "cyclopts>=3.0",
# ]
# ///
import gc
import io
import math
import os
import re
import shutil
import sys
import time
import unicodedata
from pathlib import Path
from typing import Annotated, Literal

import cyclopts
import fitz  # PyMuPDF
from cyclopts import Parameter
from PIL import Image

try:
    from compress import compress_pdf
except ImportError:
    # Fallback: add current script's directory to sys.path to find compress.py
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from compress import compress_pdf

def sanitize_filename(name, max_len=80):
    # Normalize unicode to decompose accents
    name = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('ASCII')
    # Replace invalid filename characters with underscores
    name = re.sub(r'[\\/*?:"<>|]', '_', name)
    # Replace spaces and multiple underscores
    name = re.sub(r'\s+', '_', name)
    name = re.sub(r'_+', '_', name)
    name = name.strip('_')
    # Truncate to max_len
    if len(name) > max_len:
        name = name[:max_len].strip('_')
    return name



def parse_bookmark_title(title, part_idx, default_date="0000-00-00", kanoe_dates=None):
    title = title.strip()
    part_suffix = f"{part_idx:04d}"
    
    desc = title
    num_id = None
    isodate = None
    
    # 1. PJE Format (e.g., "PETIÇÃO INICIAL | NUM: 115465694 | 08/01/2025 14:13" or with YYYY-MM-DD date)
    pje_match = re.match(r"^(.*?)\s*\|\s*NUM:\s*(\d+)\s*\|\s*(\d{2})/(\d{2})/(\d{4})", title)
    if pje_match:
        desc = pje_match.group(1).strip()
        num_id = pje_match.group(2).strip()
        day, month, year = pje_match.group(3), pje_match.group(4), pje_match.group(5)
        isodate = f"{year}-{month}-{day}"
    else:
        pje_match_iso = re.match(r"^(.*?)\s*\|\s*NUM:\s*(\d+)\s*\|\s*(\d{4})-(\d{2})-(\d{2})", title)
        if pje_match_iso:
            desc = pje_match_iso.group(1).strip()
            num_id = pje_match_iso.group(2).strip()
            isodate = f"{pje_match_iso.group(3)}-{pje_match_iso.group(4)}-{pje_match_iso.group(5)}"

    # 2. SEI Format (e.g., "Ofício 25345 (0053210931)" or "Relatório 0053213473")
    if num_id is None:
        sei_match_paren = re.match(r"^(.*?)\s*\(\s*(\d{7,12})\s*\)\s*$", title)
        if sei_match_paren:
            desc = sei_match_paren.group(1).strip()
            num_id = sei_match_paren.group(2).strip()
        else:
            sei_match_space = re.match(r"^(.*?)\s+(\d{7,12})\s*$", title)
            if sei_match_space:
                desc = sei_match_space.group(1).strip()
                num_id = sei_match_space.group(2).strip()
    # 3. Kanoe Format (e.g., "121121280 - PETIÇÃO INICIAL (PETIÇÃO INICIAL)")
    # Check ID-first format
    if num_id is None:
        kanoe_id_match = re.match(r"^(\d{7,12})\s*-\s*(.*?)$", title)
        if kanoe_id_match:
            num_id = kanoe_id_match.group(1).strip()
            remaining = kanoe_id_match.group(2).strip()
            # Clean up common extensions in description
            desc_clean = re.sub(r'\.pdf\b', '', remaining, flags=re.IGNORECASE)
            desc_clean = re.sub(r'\.pd\b', '', desc_clean, flags=re.IGNORECASE)
            desc = desc_clean
            if kanoe_dates and num_id in kanoe_dates:
                isodate = kanoe_dates[num_id]
    if isodate is None:
        kanoe_match_date_first = re.match(r"^(\d{4}-\d{2}-\d{2})\s*-\s*(.*?)$", title)
        if kanoe_match_date_first:
            isodate = kanoe_match_date_first.group(1)
            desc = kanoe_match_date_first.group(2).strip()
        else:
            kanoe_match_date_last = re.match(r"^(.*?)\s*-\s*(\d{4}-\d{2}-\d{2})$", title)
            if kanoe_match_date_last:
                desc = kanoe_match_date_last.group(1).strip()
                isodate = kanoe_match_date_last.group(2)
            else:
                kanoe_match_slash_first = re.match(r"^(\d{2})/(\d{2})/(\d{4})\s*-\s*(.*?)$", title)
                if kanoe_match_slash_first:
                    day, month, year = kanoe_match_slash_first.group(1), kanoe_match_slash_first.group(2), kanoe_match_slash_first.group(3)
                    isodate = f"{year}-{month}-{day}"
                    desc = kanoe_match_slash_first.group(4).strip()
                else:
                    kanoe_match_slash_last = re.match(r"^(.*?)\s*-\s*(\d{2})/(\d{2})/(\d{4})$", title)
                    if kanoe_match_slash_last:
                        desc = kanoe_match_slash_last.group(1).strip()
                        day, month, year = kanoe_match_slash_last.group(2), kanoe_match_slash_last.group(3), kanoe_match_slash_last.group(4)
                        isodate = f"{year}-{month}-{day}"
    # Build filename elements: [ordinal]_[isodate-se-houver]_[ID]_[description]
    parts = [part_suffix]
    if isodate:
        parts.append(isodate)
    if num_id:
        parts.append(num_id)
    parts.append(sanitize_filename(desc))
    
    return "_".join(parts) + ".pdf"

def rasterize_pdf(input_path, output_path, dpi=150, quality=50, mode="gray"):
    doc = fitz.open(input_path)
    new_doc = fitz.open()
    
    for page in doc:
        pix = page.get_pixmap(dpi=dpi)
        img_data = pix.tobytes("png")
        
        img = Image.open(io.BytesIO(img_data))
        
        if mode == "bw":
            img = img.convert("1")
            out_io = io.BytesIO()
            img.save(out_io, format="TIFF", compression="group4")
            img_bytes = out_io.getvalue()
        elif mode == "gray":
            img = img.convert("L")
            out_io = io.BytesIO()
            img.save(out_io, format="JPEG", quality=quality, optimize=True)
            img_bytes = out_io.getvalue()
        else:
            img = img.convert("RGB")
            out_io = io.BytesIO()
            img.save(out_io, format="JPEG", quality=quality, optimize=True)
            img_bytes = out_io.getvalue()
            
        new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
        new_page.insert_image(page.rect, stream=img_bytes)
        
    new_doc.save(output_path, garbage=4, deflate=True, clean=True)
    new_doc.close()
    doc.close()

def convert_to_nup(input_path, output_path, nup=1):
    if nup <= 1:
        return
        
    src = fitz.open(input_path)
    doc = fitz.open()
    total_pages = len(src)
    
    start_idx = 0
    while start_idx < total_pages:
        ref_page = src[start_idx]
        w, h = ref_page.rect.width, ref_page.rect.height
        is_landscape = w > h
        
        if nup == 2:
            if is_landscape:
                cols, rows = 1, 2  # Stack vertically (top and bottom) -> results in portrait
            else:
                cols, rows = 2, 1  # Side-by-side -> results in landscape
        elif nup == 3:
            if is_landscape:
                cols, rows = 1, 3
            else:
                cols, rows = 3, 1
        elif nup == 4:
            cols, rows = 2, 2
        elif nup == 6:
            if is_landscape:
                cols, rows = 2, 3
            else:
                cols, rows = 3, 2
        elif nup == 8:
            if is_landscape:
                cols, rows = 2, 4
            else:
                cols, rows = 4, 2
        elif nup == 9:
            cols, rows = 3, 3
        elif nup == 12:
            if is_landscape:
                cols, rows = 3, 4
            else:
                cols, rows = 4, 3
        elif nup == 16:
            cols, rows = 4, 4
        else:
            standard_cols = int(math.ceil(math.sqrt(nup)))
            standard_rows = int(math.ceil(nup / standard_cols))
            if is_landscape:
                if standard_cols > standard_rows:
                    cols, rows = standard_rows, standard_cols
                else:
                    cols, rows = standard_cols, standard_rows
            else:
                cols, rows = standard_cols, standard_rows
                
        chunk_size = cols * rows
        out_w = w * cols
        out_h = h * rows
        
        new_page = doc.new_page(width=out_w, height=out_h)
        
        for r in range(rows):
            for c in range(cols):
                idx = start_idx + (r * cols) + c
                if idx < total_pages:
                    x0 = c * w
                    y0 = r * h
                    x1 = x0 + w
                    y1 = y0 + h
                    rect = fitz.Rect(x0, y0, x1, y1)
                    page_to_draw = src[idx]
                    orig_rotation = page_to_draw.rotation
                    if orig_rotation != 0:
                        page_to_draw.set_rotation(0)
                    new_page.show_pdf_page(rect, src, idx, rotate=(360 - orig_rotation) % 360)
                    
        start_idx += chunk_size



        
    doc.save(output_path)
    doc.close()
    src.close()


def _compress_with_size_fallback(temp_path, final_path, mode, title, max_dim, quality, threshold_kb, p_count, part_idx):
    """Compress temp_path to final_path, applying grayscale/rasterization fallbacks if still
    above threshold_kb per page afterward. Raises if the initial compress_pdf call fails."""
    compress_pdf(
        input_path=temp_path,
        output_path=final_path,
        mode=mode,
        max_dim=max_dim,
        quality=quality,
        skip_small=150,
    )
    final_size = os.path.getsize(final_path)
    size_per_page_kb = (final_size / 1024) / p_count

    is_scanned = "autos digitalizados" in title.lower() or "digitalizado" in title.lower()

    # Step a: If still heavy and color, try grayscale compression
    if size_per_page_kb > threshold_kb and mode not in ("bw", "gray"):
        print(f"Notice: Part {part_idx} is heavy after standard compression ({size_per_page_kb:.1f} KB/page).")
        print("Trying grayscale image compression to reduce size while preserving text layer...")
        temp_gray_path = final_path + ".gray.pdf"
        try:
            compress_pdf(
                input_path=temp_path,
                output_path=temp_gray_path,
                mode="gray",
                max_dim=max_dim,
                quality=quality,
                skip_small=150,
            )
            gray_size = os.path.getsize(temp_gray_path)
            if gray_size < final_size:
                reduction = (1 - gray_size / final_size) * 100
                print(f"Grayscale compression successful: reduced to {gray_size/1024/1024:.2f} MB ({reduction:.1f}% reduction).")
                if os.path.exists(final_path):
                    os.remove(final_path)
                os.replace(temp_gray_path, final_path)
                final_size = gray_size
                size_per_page_kb = (final_size / 1024) / p_count
            else:
                print("Grayscale compression did not yield a smaller file size.")
        except Exception as gray_err:
            print(f"Warning: Grayscale fallback failed: {gray_err}.", file=sys.stderr)
        finally:
            gc.collect()
            if os.path.exists(temp_gray_path):
                for attempt in range(1, 11):
                    try:
                        os.remove(temp_gray_path)
                        break
                    except PermissionError:
                        if attempt == 10:
                            print(f"Warning: Could not delete {temp_gray_path}.", file=sys.stderr)
                        else:
                            time.sleep(0.3)

    # Step b: If still heavy, apply page rasterization fallback
    if size_per_page_kb > threshold_kb:
        print(f"Notice: Part {part_idx} remains heavy ({size_per_page_kb:.1f} KB/page, limit {threshold_kb} KB/page).")
        print("Applying dynamic page rasterization fallback to bypass vector/form layout bloating...")

        temp_raster_path = final_path + ".raster.pdf"
        try:
            raster_mode = "bw" if is_scanned else "gray"
            rasterize_pdf(
                input_path=temp_path,
                output_path=temp_raster_path,
                dpi=150,
                quality=quality,
                mode=raster_mode,
            )
            raster_size = os.path.getsize(temp_raster_path)

            if raster_size < final_size:
                reduction = (1 - raster_size / final_size) * 100
                print(f"Rasterization successful: reduced to {raster_size/1024/1024:.2f} MB ({reduction:.1f}% reduction).")
                if os.path.exists(final_path):
                    os.remove(final_path)
                os.replace(temp_raster_path, final_path)
                final_size = raster_size
            else:
                print("Rasterization did not yield a smaller file size. Keeping original compressed PDF.")
        except Exception as re_err:
            print(f"Warning: Rasterization fallback failed: {re_err}. Keeping original compressed PDF.", file=sys.stderr)
        finally:
            gc.collect()
            if os.path.exists(temp_raster_path):
                for attempt in range(1, 11):
                    try:
                        os.remove(temp_raster_path)
                        break
                    except PermissionError:
                        if attempt == 10:
                            print(f"Warning: Could not delete {temp_raster_path}.", file=sys.stderr)
                        else:
                            time.sleep(0.3)

    return final_size

def split_and_compress_toc(input_pdf, output_dir, mode="auto", max_dim=1200, quality=50, threshold_kb=150, nup=1, also_plain=True):
    if not os.path.exists(input_pdf):
        print(f"Error: Input file '{input_pdf}' does not exist.", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")

    print(f"Opening original PDF: {input_pdf}...")
    doc = fitz.open(input_pdf)
    total_pages = len(doc)
    print(f"Total pages: {total_pages}")
    
    orig_total_size = os.path.getsize(input_pdf)
    print("Reading bookmarks (TOC) from PDF...")
    toc = doc.get_toc()
    
    # Try to extract date mapping from Kanoe index table if present
    kanoe_dates = {}
    try:
        start_page = None
        end_page = None
        for idx, (level, title, page) in enumerate(toc):
            if title.lower() in ('índice', 'indice'):
                start_page = page - 1
                if idx + 1 < len(toc):
                    end_page = toc[idx+1][2] - 1
                break
        if start_page is not None:
            if end_page is None:
                end_page = len(doc)
            index_text = ""
            for p in range(start_page, min(end_page, len(doc))):
                index_text += doc[p].get_text("text") + "\n"
            for m in re.finditer(r'(\d{2})/(\d{2})/(\d{4})\s+\d{2}:\d{2}:\d{2}.*?(\d{7,12})\s*-\s*', index_text, re.DOTALL):
                day, month, year, doc_id = m.group(1), m.group(2), m.group(3), m.group(4)
                kanoe_dates[doc_id] = f"{year}-{month}-{day}"
    except Exception as parse_err:
        print(f"Warning: Could not parse Kanoe index table dates: {parse_err}", file=sys.stderr)

    level1_items = [item for item in toc if item[0] == 1]
    if not level1_items:
        print("Warning: No level 1 bookmarks found in the PDF. Cannot split by chapters.", file=sys.stderr)
        doc.close()
        sys.exit(1)
        
    print(f"Found {len(level1_items)} level 1 bookmarks.")
    
    # Sort level 1 items by page number
    level1_items = sorted(level1_items, key=lambda x: x[2])
    
    # Find first valid date in TOC to use as default fallback
    default_date = "0000-00-00"
    for level, title, page in level1_items:
        date_match = re.search(r"(\d{2})/(\d{2})/(\d{4})", title)
        if date_match:
            day, month, year = date_match.group(1), date_match.group(2), date_match.group(3)
            default_date = f"{year}-{month}-{day}"
            break
            
    # Group bookmarks by starting page number to handle duplicates (same page starting points)
    grouped_bookmarks = {}
    for level, title, page in level1_items:
        if page not in grouped_bookmarks:
            grouped_bookmarks[page] = []
        grouped_bookmarks[page].append(title)
        
    sorted_pages = sorted(grouped_bookmarks.keys())
    
    parts = []
    for idx, page in enumerate(sorted_pages):
        start_page = page - 1 # 0-indexed
        
        # Determine the end page of this part
        if idx + 1 < len(sorted_pages):
            next_page = sorted_pages[idx+1]
            end_page = next_page - 1
        else:
            end_page = total_pages
            
        # Ensure range is valid
        if start_page < end_page and start_page < total_pages:
            titles = grouped_bookmarks[page]
            combined_title = " - ".join(titles)
            parts.append({
                "index": idx + 1,
                "title": combined_title,
                "start_page": start_page,
                "end_page": end_page
            })
            
    print(f"Grouped into {len(parts)} unique parts by page start.")
    
    parts_info = []       # (final_path, size, p_count_nup, title)
    parts_info_plain = [] # (final_path, size, p_count_orig, title) — nup=1 versions

    for part in parts:
        part_idx = part["index"]
        title = part["title"]
        start = part["start_page"]
        end = part["end_page"]
        p_count = end - start
        
        part_filename = parse_bookmark_title(title, part_idx, default_date, kanoe_dates=kanoe_dates)
        final_part_path = os.path.join(output_dir, part_filename)
        temp_part_path = os.path.join(output_dir, f"temp_part_{part_idx}.pdf")
        
        print(f"\n--- Processing Part {part_idx}/{len(parts)}: '{title}' (Pages {start+1} to {end}) ---")
        
        # 1. Extract the pages into a temporary file (plain, nup=1)
        part_doc = fitz.open()
        part_doc.insert_pdf(doc, from_page=start, to_page=end-1)
        part_doc.save(temp_part_path)
        part_doc.close()

        # 1a. If also_plain and nup > 1, compress the plain (nup=1) version now
        if nup > 1 and also_plain:
            plain_part_filename = part_filename[:-4] + "_plain.pdf" if part_filename.endswith(".pdf") else part_filename + "_plain.pdf"
            plain_part_path = os.path.join(output_dir, plain_part_filename)
            plain_count = end - start
            try:
                plain_mode = mode
                if "autos digitalizados" in title.lower() or "digitalizado" in title.lower():
                    plain_mode = "bw"
                plain_size = _compress_with_size_fallback(
                    temp_part_path, plain_part_path, plain_mode, title,
                    max_dim, quality, threshold_kb, plain_count, part_idx,
                )
            except Exception as plain_err:
                print(f"Warning: plain compression of part {part_idx} failed: {plain_err}. Keeping uncompressed version.", file=sys.stderr)
                shutil.copyfile(temp_part_path, plain_part_path)
                plain_size = os.path.getsize(plain_part_path)
            parts_info_plain.append((plain_part_path, plain_size, plain_count, title))

        # 1b. Group pages if nup > 1
        if nup > 1:
            print(f"Applying {nup}-up page grouping layout...")
            temp_nup_path = temp_part_path + ".nup.pdf"
            convert_to_nup(temp_part_path, temp_nup_path, nup)
            if os.path.exists(temp_part_path):
                os.remove(temp_part_path)
            os.rename(temp_nup_path, temp_part_path)
            
        # Get N-up page count
        part_check = fitz.open(temp_part_path)
        p_count_nup = len(part_check)
        part_check.close()
        
        temp_size = os.path.getsize(temp_part_path)
        
        # 2. Compress the temporary file into the final path
        try:
            part_mode = mode
            if "autos digitalizados" in title.lower() or "digitalizado" in title.lower():
                print("Forcing B&W mode ('bw') for scanned document to achieve maximum compression.")
                part_mode = "bw"

            final_size = _compress_with_size_fallback(
                temp_part_path, final_part_path, part_mode, title,
                max_dim, quality, threshold_kb, p_count_nup, part_idx,
            )

            print(f"Final part size: {final_size / 1024 / 1024:.2f} MB (Overall Reduction: {(1 - final_size / temp_size)*100:.1f}%)")
            parts_info.append((final_part_path, final_size, p_count_nup, title))
        except Exception as e:
            print(f"Error compressing part {part_idx}: {e}", file=sys.stderr)
            # Fallback: keep uncompressed version
            os.replace(temp_part_path, final_part_path)
            final_size = os.path.getsize(final_part_path)
            parts_info.append((final_part_path, final_size, p_count_nup, title))
        finally:
            gc.collect()
            if os.path.exists(temp_part_path):
                for attempt in range(1, 11):
                    try:
                        os.remove(temp_part_path)
                        break
                    except PermissionError:
                        if attempt == 10:
                            print(f"Warning: Could not delete temporary file {temp_part_path}. It remains locked.", file=sys.stderr)
                        else:
                            time.sleep(0.3)
                
    doc.close()
    
    print("\n================ SUMMARY ================")
    total_compressed_size = sum(size for _, size, _, _ in parts_info)
    print(f"Original Total Size: {orig_total_size / 1024 / 1024:.2f} MB")
    print(f"Compressed Total Size: {total_compressed_size / 1024 / 1024:.2f} MB")
    print(f"Overall Size Reduction: {(1 - total_compressed_size / orig_total_size) * 100:.1f}%")
    print(f"Total parts created: {len(parts_info)}")
    print("Top 20 largest parts:")
    sorted_parts = sorted(parts_info, key=lambda x: x[1], reverse=True)
    for path, size, p_count, _ in sorted_parts[:20]:
        print(f" - {os.path.basename(path)}: {size / 1024 / 1024:.2f} MB ({p_count} pages)")
    print("=========================================")

    def _merge_parts(parts_list, output_path):
        """Merge a list of (path, size, p_count, title) into a single bookmarked PDF."""
        merged_doc = fitz.open()
        merged_toc = []
        merged_page_offset = 0
        for final_part_path, _, p_count, part_title in parts_list:
            part_doc = fitz.open(final_part_path)
            merged_doc.insert_pdf(part_doc)
            part_doc.close()
            clean_title = part_title.replace('_', ' ').replace('-', ' ').strip()
            merged_toc.append([1, clean_title, merged_page_offset + 1])
            merged_page_offset += p_count
        merged_doc.set_toc(merged_toc)
        merged_doc.save(output_path)
        merged_doc.close()
        return os.path.getsize(output_path)

    input_dir = os.path.dirname(os.path.abspath(input_pdf))
    basename = os.path.basename(input_pdf)
    name_without_ext, ext = os.path.splitext(basename)

    # Always produce the plain _compressed version
    plain_suffix = "_compressed"
    plain_merged_path = os.path.join(input_dir, f"{name_without_ext}{plain_suffix}{ext}")

    if nup > 1 and also_plain and parts_info_plain:
        # Reassemble from the individually-compressed plain parts
        print("\nReassembling plain (no n-up) optimized parts into a single merged PDF...")
        plain_merged_size = _merge_parts(parts_info_plain, plain_merged_path)
        print(f"Plain compressed PDF: {plain_merged_path}")
        print(f"Plain Merged File Size: {plain_merged_size / 1024 / 1024:.2f} MB (Reduction: {(1 - plain_merged_size / orig_total_size)*100:.1f}%)")
        # Clean up individual plain parts
        for plain_path, _, _, _ in parts_info_plain:
            if os.path.exists(plain_path):
                os.remove(plain_path)
    elif nup <= 1:
        # nup=1 path: merge the regular compressed parts as the plain output
        print("\nReassembling optimized parts into a single merged PDF...")
        plain_merged_size = _merge_parts(parts_info, plain_merged_path)
        print(f"Successfully generated merged optimized PDF at: {plain_merged_path}")
        print(f"Merged File Size: {plain_merged_size / 1024 / 1024:.2f} MB (Reduction: {(1 - plain_merged_size / orig_total_size)*100:.1f}%)")
        return  # done — no nup version needed

    # Reassemble the n-up version
    nup_suffix = f"_compressed_{nup}up"
    merged_output_path = os.path.join(input_dir, f"{name_without_ext}{nup_suffix}{ext}")
    print(f"\nReassembling {nup}-up optimized parts into a single merged PDF...")
    merged_size = _merge_parts(parts_info, merged_output_path)
    print(f"Successfully generated {nup}-up merged PDF at: {merged_output_path}")
    print(f"Merged File Size: {merged_size / 1024 / 1024:.2f} MB (Reduction: {(1 - merged_size / orig_total_size)*100:.1f}%)")


app = cyclopts.App(name="process-pdf", help="Split PDF by bookmarks/TOC and compress each part.")


@app.default
def main(
    *,
    input_path: Annotated[Path, Parameter(name=["--input"])],
    output_dir: Path,
    mode: Literal["bw", "gray", "color", "auto"] = "auto",
    max_dim: int = 1200,
    quality: int = 50,
    threshold_kb: int = 150,
    nup: int = 1,
    no_plain: bool = False,
) -> None:
    """Split and compress.

    Parameters
    ----------
    input_path
        Path to input PDF file.
    output_dir
        Directory to save the split & compressed PDFs.
    mode
        Compression mode.
    max_dim
        Maximum dimension of images.
    quality
        JPEG quality.
    threshold_kb
        Threshold in KB per page to trigger rasterization fallback.
    nup
        N-up layout (e.g. 2, 4, 8 pages per page). When nup>1, a plain
        _compressed version is also always produced.
    no_plain
        When nup>1, skip generating the plain _compressed (nup=1) version.
    """
    split_and_compress_toc(
        input_pdf=str(input_path),
        output_dir=str(output_dir),
        mode=mode,
        max_dim=max_dim,
        quality=quality,
        threshold_kb=threshold_kb,
        nup=nup,
        also_plain=not no_plain,
    )


if __name__ == "__main__":
    app()
