import argparse
import fitz
import io
import os
import shutil
import subprocess
import sys
import tempfile
from PIL import Image

JBIG2_BIN = shutil.which("jbig2")


def _jbig2_install_hint():
    """Best-guess one-line install command for the current system's package manager.

    jbig2enc has no PyPI wheel (it's a system package everywhere, including
    in OCRmyPDF's own docs) -- an agent with shell access should just run
    this command rather than treating a missing binary as a hard blocker.
    """
    if shutil.which("apt-get"):
        return "apt-get install -y jbig2"
    if shutil.which("brew"):
        return "brew install jbig2enc"
    if shutil.which("dnf"):
        return "dnf install -y jbig2enc"
    if shutil.which("pacman"):
        return "pacman -S --noconfirm jbig2enc"
    return "install 'jbig2enc' via your OS package manager (see references/jbig2enc-licensing.md)"


def _set_jbig2_stream(doc, xref, jbig2_bytes, width, height):
    """Point an existing image xref at a raw JBIG2Decode-ready stream.

    Reuses the xref already wired into the page's Resources/content stream
    instead of inserting a new image object.
    """
    doc.update_stream(xref, jbig2_bytes, new=False, compress=False)
    doc.xref_set_key(xref, "Filter", "/JBIG2Decode")
    doc.xref_set_key(xref, "DecodeParms", "null")
    doc.xref_set_key(xref, "Width", str(width))
    doc.xref_set_key(xref, "Height", str(height))
    doc.xref_set_key(xref, "BitsPerComponent", "1")
    doc.xref_set_key(xref, "ColorSpace", "/DeviceGray")


def _jbig2_roundtrips_losslessly(jbig2_bytes, bw_img):
    """Decode jbig2_bytes via MuPDF's own JBIG2 decoder and compare pixel-for-pixel."""
    width, height = bw_img.size
    check_doc = fitz.open()
    try:
        page = check_doc.new_page(width=width, height=height)
        placeholder = fitz.Pixmap(fitz.csGRAY, fitz.IRect(0, 0, width, height))
        placeholder.clear_with(255)
        xref = page.insert_image(fitz.Rect(0, 0, width, height), pixmap=placeholder)
        _set_jbig2_stream(check_doc, xref, jbig2_bytes, width, height)
        pix = page.get_pixmap(dpi=72, colorspace=fitz.csGRAY)
        decoded = Image.frombytes("L", (pix.width, pix.height), pix.samples)
        decoded_bw = decoded.convert("1", dither=Image.Dither.NONE)
    finally:
        check_doc.close()
    return decoded_bw.tobytes() == bw_img.tobytes()


def encode_jbig2_lossless(bw_img):
    """Encode a 1-bit PIL image with jbig2enc's generic-region (lossless) coder.

    Returns the raw PDF-ready JBIG2 stream, verified to decode back to the
    exact same bitmap, or None if the encoder is unavailable, fails, or the
    roundtrip check doesn't match (in which case the caller should keep
    using CCITT G4).
    """
    with tempfile.TemporaryDirectory() as tmp:
        src_path = os.path.join(tmp, "page.pbm")
        bw_img.save(src_path, format="PPM")
        try:
            result = subprocess.run(
                [JBIG2_BIN, "-p", src_path],
                capture_output=True, timeout=60, check=True,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as e:
            print(f"Warning: jbig2 encoding failed ({e}). Using CCITT G4 instead.", file=sys.stderr)
            return None
        jbig2_bytes = result.stdout

    if not jbig2_bytes:
        return None

    if not _jbig2_roundtrips_losslessly(jbig2_bytes, bw_img):
        print("Warning: jbig2 output failed roundtrip verification. Using CCITT G4 instead.", file=sys.stderr)
        return None

    return jbig2_bytes


def is_scanned_page(page):
    """
    Detects if a PDF page is a scanned document page or a native digital page.
    Heuristics:
    1. If the page has no text at all, it's considered scanned (if it has images).
    2. If there is a giant image covering > 85% of the page area, and the amount of
       text is relatively small (< 800 characters), it's likely a scanned page with OCR text.
    """
    text = page.get_text().strip()
    if not text:
        return True
        
    images = page.get_images(full=True)
    if images:
        page_area = page.rect.width * page.rect.height
        for img in images:
            xref = img[0]
            rects = page.get_image_rects(xref)
            if rects:
                rect = rects[0]
                img_area = rect.width * rect.height
                # If image covers most of the page and text is sparse
                if (img_area / page_area) > 0.85 and len(text) < 800:
                    return True
    return False

def compress_pdf(input_path, output_path, mode="auto", max_dim=1200, quality=50, skip_small=150, denoise=False, enhance_contrast=False, use_jbig2=False):
    if not os.path.exists(input_path):
        print(f"Error: Input file '{input_path}' does not exist.", file=sys.stderr)
        sys.exit(1)

    if use_jbig2 and not JBIG2_BIN:
        print(
            "Warning: --jbig2 was requested but the 'jbig2' binary is not on PATH. "
            f"Install it first (e.g. `{_jbig2_install_hint()}`) and re-run -- falling back to "
            "CCITT G4 for all bw-mode pages for now.",
            file=sys.stderr,
        )
        use_jbig2 = False

    print(f"Opening PDF: {input_path}...")
    try:
        doc = fitz.open(input_path)
    except Exception as e:
        print(f"Error opening PDF: {e}", file=sys.stderr)
        sys.exit(1)
        
    total_pages = len(doc)
    print(f"Total pages: {total_pages}")
    
    # Classify pages to decide on compression strategy
    print("Classifying pages (scanned vs native digital)...")
    page_classifications = {}
    for page_idx in range(total_pages):
        page_classifications[page_idx] = "scanned" if is_scanned_page(doc[page_idx]) else "digital"
        
    scanned_count = sum(1 for c in page_classifications.values() if c == "scanned")
    print(f"Classification summary: {scanned_count} scanned pages, {total_pages - scanned_count} native digital pages.")
    
    # Map unique xrefs to first page index they appear on
    image_to_page = {}
    for page_idx in range(total_pages):
        for img in doc[page_idx].get_images(full=True):
            xref = img[0]
            if xref not in image_to_page:
                image_to_page[xref] = page_idx
                
    unique_xrefs = list(image_to_page.keys())
    total_unique = len(unique_xrefs)
    print(f"Found {total_unique} unique images.")
    
    replaced_count = 0
    skipped_count = 0
    jbig2_count = 0

    for count, xref in enumerate(unique_xrefs, 1):
        page_idx = image_to_page[xref]
        page = doc[page_idx]
        
        if count % 100 == 0 or count == 1:
            print(f"Processing image {count}/{total_unique} (xref: {xref}, page: {page_idx})...")
            sys.stdout.flush()
            
        try:
            base_image = doc.extract_image(xref)
            img_data = base_image["image"]
            width = base_image["width"]
            height = base_image["height"]
            
            # Skip very small images (like icons, bullets)
            if width <= skip_small and height <= skip_small:
                skipped_count += 1
                continue
                
            img = Image.open(io.BytesIO(img_data))
            
            # Downscale if needed
            if width > max_dim or height > max_dim:
                img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
                
            # Handle alpha channels / transparency
            if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "RGBA":
                    background.paste(img, mask=img.split()[-1])
                else:
                    background.paste(img.convert("RGBA"), mask=img.convert("RGBA").split()[-1])
                img = background
                
            # Determine best strategy
            current_mode = mode
            if mode == "auto":
                page_type = page_classifications[page_idx]
                if page_type == "scanned":
                    current_mode = "bw"
                else:
                    # For digital pages, keep grayscale if original is grayscale, color otherwise
                    if img.mode in ("L", "1"):
                        current_mode = "gray"
                    else:
                        current_mode = "color"
            
            compressed_bytes = None
            jbig2_replacement = None

            # Compression loop with fallback logic
            while compressed_bytes is None:
                try:
                    out_io = io.BytesIO()
                    if current_mode == "bw":
                        # Try OpenCV adaptive thresholding first for better text quality
                        try:
                            import cv2
                            import numpy as np
                            # Convert PIL image to grayscale numpy array
                            gray_arr = np.array(img.convert("L"))
                            
                            # Optional: Denoising
                            if denoise:
                                gray_arr = cv2.fastNlMeansDenoising(gray_arr, None, h=10, templateWindowSize=7, searchWindowSize=21)
                                
                            # Optional: Contrast Enhancement (CLAHE)
                            if enhance_contrast:
                                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                                gray_arr = clahe.apply(gray_arr)
                                
                            # Apply Gaussian Adaptive Thresholding
                            thresh_arr = cv2.adaptiveThreshold(
                                gray_arr, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY, 21, 15
                            )
                            
                            # Optional: Post-binarization Median Blur
                            if denoise:
                                thresh_arr = cv2.medianBlur(thresh_arr, 3)
                                
                            bw_img = Image.fromarray(thresh_arr).convert("1")
                        except Exception as e:
                            # Fallback to standard Pillow thresholding if cv2/numpy fails
                            print(f"Warning: OpenCV adaptive threshold failed ({e}). Falling back to simple threshold.", file=sys.stderr)
                            gray_img = img.convert("L")
                            bw_img = gray_img.point(lambda x: 0 if x < 128 else 255, mode="1")
                        
                        bw_img.save(out_io, format="TIFF", compression="group4")

                        if use_jbig2:
                            try:
                                jbig2_bytes = encode_jbig2_lossless(bw_img)
                                if jbig2_bytes is not None and len(jbig2_bytes) < out_io.tell():
                                    jbig2_replacement = (jbig2_bytes, bw_img.width, bw_img.height)
                            except Exception as e:
                                print(f"Warning: JBIG2 backend raised an unexpected error ({e}). Using CCITT G4 instead.", file=sys.stderr)
                    elif current_mode == "gray":
                        gray_img = img.convert("L")
                        try:
                            import cv2
                            import numpy as np
                            gray_arr = np.array(gray_img)
                            if denoise:
                                gray_arr = cv2.fastNlMeansDenoising(gray_arr, None, h=10, templateWindowSize=7, searchWindowSize=21)
                            if enhance_contrast:
                                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                                gray_arr = clahe.apply(gray_arr)
                            gray_img = Image.fromarray(gray_arr)
                        except Exception:
                            pass
                        gray_img.save(out_io, format="JPEG", quality=quality, optimize=True)
                    else:  # color
                        color_img = img.convert("RGB")
                        color_img.save(out_io, format="JPEG", quality=quality, optimize=True)
                        
                    compressed_bytes = out_io.getvalue()
                except Exception as e:
                    print(f"Warning: Mode '{current_mode}' failed for image {xref}: {e}. Trying fallback...", file=sys.stderr)
                    if current_mode == "bw":
                        current_mode = "gray"
                    elif current_mode == "gray":
                        current_mode = "color"
                    else:
                        raise e
            
            if jbig2_replacement is not None:
                jbig2_bytes, jbig2_width, jbig2_height = jbig2_replacement
                _set_jbig2_stream(doc, xref, jbig2_bytes, jbig2_width, jbig2_height)
                jbig2_count += 1
            else:
                page.replace_image(xref, stream=compressed_bytes)
            replaced_count += 1
            
        except Exception as e:
            print(f"Error compressing image {xref} on page {page_idx}: {e}", file=sys.stderr)
            sys.stdout.flush()
            
    jbig2_note = f", JBIG2: {jbig2_count}" if use_jbig2 else ""
    print(f"\nProcessing complete. Replaced: {replaced_count}, Skipped: {skipped_count}{jbig2_note}")
    print(f"Saving optimized PDF to: {output_path}...")
    sys.stdout.flush()
    
    try:
        doc.save(output_path, garbage=4, deflate=True, clean=True)
        print("Save complete!")
        
        orig_size = os.path.getsize(input_path)
        new_size = os.path.getsize(output_path)
        print(f"Original size: {orig_size / 1024 / 1024:.2f} MB")
        print(f"Compressed size: {new_size / 1024 / 1024:.2f} MB")
        print(f"Reduction: {(1 - new_size/orig_size)*100:.1f}%")
        doc.close()
    except Exception as e:
        print(f"Error saving PDF: {e}", file=sys.stderr)
        doc.close()
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compress PDF with smart scanned vs. native page optimization.")
    parser.add_argument("--input", required=True, help="Path to input PDF file")
    parser.add_argument("--output", required=True, help="Path to output compressed PDF file")
    parser.add_argument("--mode", choices=["bw", "gray", "color", "auto"], default="auto", help="Compression mode (default: auto)")
    parser.add_argument("--max-dim", type=int, default=1200, help="Maximum dimension of images (default: 1200)")
    parser.add_argument("--quality", type=int, default=50, help="JPEG quality for color/gray modes (default: 50)")
    parser.add_argument("--skip-small", type=int, default=150, help="Skip images smaller than this threshold (default: 150)")
    parser.add_argument("--denoise", action="store_true", help="Apply NLM denoising to scanned pages")
    parser.add_argument("--enhance-contrast", action="store_true", help="Apply contrast enhancement to scanned pages")
    parser.add_argument("--jbig2", action="store_true", help="For bw-mode pages, also try JBIG2 lossless encoding (requires the 'jbig2' binary on PATH) and use it instead of CCITT G4 whenever it verifies bit-exact via a MuPDF roundtrip decode and comes out smaller. See references/jbig2enc-licensing.md.")

    args = parser.parse_args()
    compress_pdf(
        input_path=args.input,
        output_path=args.output,
        mode=args.mode,
        max_dim=args.max_dim,
        quality=args.quality,
        skip_small=args.skip_small,
        denoise=args.denoise,
        enhance_contrast=args.enhance_contrast,
        use_jbig2=args.jbig2
    )
