import os
import sys
import argparse
import re
import unicodedata
import fitz  # PyMuPDF
from PIL import Image
import io

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

def parse_bookmark_title(title, part_idx, default_date="0000-00-00"):
    match = re.match(r"^(.*?)\s*\|\s*NUM:\s*(\d+)\s*\|\s*(\d{2})/(\d{2})/(\d{4})", title)
    if match:
        desc = match.group(1).strip()
        num_id = match.group(2).strip()
        day, month, year = match.group(3), match.group(4), match.group(5)
        isodate = f"{year}-{month}-{day}"
    else:
        desc = title.strip()
        num_id = "00000000"
        isodate = default_date
        
    desc_sanitized = sanitize_filename(desc)
    part_suffix = f"part_{part_idx:04d}"
    filename = f"{isodate}_{num_id}_{desc_sanitized}_{part_suffix}.pdf"
    return filename

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

def split_and_compress_toc(input_pdf, output_dir, mode="auto", max_dim=1200, quality=50, threshold_kb=150):
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
    print(f"Original file size: {orig_total_size / 1024 / 1024:.2f} MB")
    
    # Extract TOC
    print("Reading bookmarks (TOC) from PDF...")
    toc = doc.get_toc()
    
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
    
    parts_info = []

    for part in parts:
        part_idx = part["index"]
        title = part["title"]
        start = part["start_page"]
        end = part["end_page"]
        p_count = end - start
        
        part_filename = parse_bookmark_title(title, part_idx, default_date)
        
        temp_part_path = os.path.join(output_dir, f"temp_part_{part_idx:03d}.pdf")
        final_part_path = os.path.join(output_dir, part_filename)
        
        print(f"\n--- Processing Part {part_idx}/{len(parts)}: '{title}' (Pages {start+1} to {end}) ---")
        
        # 1. Extract the pages into a temporary file
        part_doc = fitz.open()
        part_doc.insert_pdf(doc, from_page=start, to_page=end-1)
        part_doc.save(temp_part_path)
        part_doc.close()
        
        temp_size = os.path.getsize(temp_part_path)
        
        # 2. Compress the temporary file into the final path
        try:
            part_mode = mode
            if "autos digitalizados" in title.lower() or "digitalizado" in title.lower():
                print("Forcing B&W mode ('bw') for scanned document to achieve maximum compression.")
                part_mode = "bw"
                
            compress_pdf(
                input_path=temp_part_path,
                output_path=final_part_path,
                mode=part_mode,
                max_dim=max_dim,
                quality=quality,
                skip_small=150
            )
            final_size = os.path.getsize(final_part_path)
            size_per_page_kb = (final_size / 1024) / p_count
            
            # Step 2a: If still heavy and color, try grayscale compression
            if size_per_page_kb > threshold_kb and part_mode not in ("bw", "gray"):
                print(f"Notice: Part {part_idx} is heavy after standard compression ({size_per_page_kb:.1f} KB/page).")
                print("Trying grayscale image compression to reduce size while preserving text layer...")
                temp_gray_path = final_part_path + ".gray.pdf"
                try:
                    compress_pdf(
                        input_path=temp_part_path,
                        output_path=temp_gray_path,
                        mode="gray",
                        max_dim=max_dim,
                        quality=quality,
                        skip_small=150
                    )
                    gray_size = os.path.getsize(temp_gray_path)
                    if gray_size < final_size:
                        reduction = (1 - gray_size / final_size) * 100
                        print(f"Grayscale compression successful: reduced to {gray_size/1024/1024:.2f} MB ({reduction:.1f}% reduction).")
                        if os.path.exists(final_part_path):
                            os.remove(final_part_path)
                        os.rename(temp_gray_path, final_part_path)
                        final_size = gray_size
                        size_per_page_kb = (final_size / 1024) / p_count
                    else:
                        print("Grayscale compression did not yield a smaller file size.")
                except Exception as gray_err:
                    print(f"Warning: Grayscale fallback failed: {gray_err}.", file=sys.stderr)
                finally:
                    if os.path.exists(temp_gray_path):
                        os.remove(temp_gray_path)
            
            # Step 2b: If still heavy, apply page rasterization fallback
            if size_per_page_kb > threshold_kb:
                print(f"Notice: Part {part_idx} remains heavy ({size_per_page_kb:.1f} KB/page, limit {threshold_kb} KB/page).")
                print("Applying dynamic page rasterization fallback to bypass vector/form layout bloating...")
                
                temp_raster_path = final_part_path + ".raster.pdf"
                try:
                    raster_mode = "bw" if ("autos digitalizados" in title.lower() or "digitalizado" in title.lower()) else "gray"
                    rasterize_pdf(
                        input_path=temp_part_path,
                        output_path=temp_raster_path,
                        dpi=150,
                        quality=quality,
                        mode=raster_mode
                    )
                    raster_size = os.path.getsize(temp_raster_path)
                    
                    if raster_size < final_size:
                        reduction = (1 - raster_size / final_size) * 100
                        print(f"Rasterization successful: reduced to {raster_size/1024/1024:.2f} MB ({reduction:.1f}% reduction).")
                        if os.path.exists(final_part_path):
                            os.remove(final_part_path)
                        os.rename(temp_raster_path, final_part_path)
                        final_size = raster_size
                    else:
                        print("Rasterization did not yield a smaller file size. Keeping original compressed PDF.")
                except Exception as re_err:
                    print(f"Warning: Rasterization fallback failed: {re_err}. Keeping original compressed PDF.", file=sys.stderr)
                finally:
                    if os.path.exists(temp_raster_path):
                        os.remove(temp_raster_path)
            
            print(f"Final part size: {final_size / 1024 / 1024:.2f} MB (Overall Reduction: {(1 - final_size / temp_size)*100:.1f}%)")
            parts_info.append((final_part_path, final_size, p_count))
        except Exception as e:
            print(f"Error compressing part {part_idx}: {e}", file=sys.stderr)
            # Fallback: keep uncompressed version
            os.rename(temp_part_path, final_part_path)
            final_size = os.path.getsize(final_part_path)
            parts_info.append((final_part_path, final_size, p_count))
        finally:
            import gc
            import time
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
    total_compressed_size = sum(size for _, size, _ in parts_info)
    print(f"Original Total Size: {orig_total_size / 1024 / 1024:.2f} MB")
    print(f"Compressed Total Size: {total_compressed_size / 1024 / 1024:.2f} MB")
    print(f"Overall Size Reduction: {(1 - total_compressed_size / orig_total_size) * 100:.1f}%")
    print(f"Total parts created: {len(parts_info)}")
    print("Top 20 largest parts:")
    sorted_parts = sorted(parts_info, key=lambda x: x[1], reverse=True)
    for path, size, p_count in sorted_parts[:20]:
        print(f" - {os.path.basename(path)}: {size / 1024 / 1024:.2f} MB ({p_count} pages)")
    print("=========================================")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Split PDF by bookmarks/TOC and compress each part.")
    parser.add_argument("--input", required=True, help="Path to input PDF file")
    parser.add_argument("--output-dir", required=True, help="Directory to save the split & compressed PDFs")
    parser.add_argument("--mode", choices=["bw", "gray", "color", "auto"], default="auto", help="Compression mode (default: auto)")
    parser.add_argument("--max-dim", type=int, default=1200, help="Maximum dimension of images (default: 1200)")
    parser.add_argument("--quality", type=int, default=50, help="JPEG quality (default: 50)")
    parser.add_argument("--threshold-kb", type=int, default=150, help="Threshold in KB per page to trigger rasterization fallback (default: 150)")

    args = parser.parse_args()
    split_and_compress_toc(
        input_pdf=args.input,
        output_dir=args.output_dir,
        mode=args.mode,
        max_dim=args.max_dim,
        quality=args.quality,
        threshold_kb=args.threshold_kb
    )
