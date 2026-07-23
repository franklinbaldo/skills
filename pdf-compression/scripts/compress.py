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
    """Best-effort install guidance for the current system's package manager.

    jbig2enc has no PyPI wheel (it's a system package everywhere, including
    in OCRmyPDF's own docs) -- an agent with shell access should just
    install it rather than treating a missing binary as a hard blocker.
    Not every package manager actually carries it, though: Fedora's
    official repos only ship the jbig2dec *decoder*, not the jbig2enc
    encoder (https://bugzilla.redhat.com/show_bug.cgi?id=2058336), and
    Arch's official repos don't carry it either (AUR-only) -- those get
    honest build-from-source/AUR guidance instead of a command that would
    just fail.
    """
    if shutil.which("apt-get"):
        return "install it with `apt-get install -y jbig2` and re-run"
    if shutil.which("brew"):
        return "install it with `brew install jbig2enc` and re-run"
    if shutil.which("dnf"):
        return (
            "Fedora's official repos don't package the jbig2enc encoder (only the "
            "jbig2dec decoder -- see https://bugzilla.redhat.com/show_bug.cgi?id=2058336); "
            "build it from source per https://github.com/agl/jbig2enc#readme, or run this "
            "on a distro that packages it (e.g. Debian/Ubuntu)"
        )
    if shutil.which("pacman"):
        return (
            "jbig2enc isn't in Arch's official repos, only the AUR -- install with an AUR "
            "helper (e.g. `yay -S jbig2enc`) or `git clone https://aur.archlinux.org/jbig2enc.git "
            "&& cd jbig2enc && makepkg -si`"
        )
    return "install 'jbig2enc' via your OS package manager or build from source (see references/jbig2enc-licensing.md)"


_JBIG2_IMAGE_KEYS = {"Type", "Subtype", "Width", "Height", "BitsPerComponent", "ColorSpace", "Filter", "DecodeParms"}


def _set_jbig2_stream(doc, xref, jbig2_bytes, width, height):
    """Point an existing image xref at a raw JBIG2Decode-ready stream.

    Reuses the xref already wired into the page's Resources/content stream
    instead of inserting a new image object. Unlike Page.replace_image()
    (which builds a fresh object), this mutates the existing dict in
    place, so any leftover keys from the image being replaced -- /Decode,
    /ImageMask, /Mask, /SMask, and the like -- must be explicitly cleared
    first or they silently corrupt the result (a stale /Decode [1 0]
    inverts black/white; a stale /ImageMask true turns this into a
    stencil mask that conflicts with /ColorSpace). Clear everything not
    in the known-good image-XObject key set before setting our own.
    """
    for key in doc.xref_get_keys(xref):
        if key not in _JBIG2_IMAGE_KEYS:
            doc.xref_set_key(xref, key, "null")
    doc.update_stream(xref, jbig2_bytes, new=False, compress=False)
    doc.xref_set_key(xref, "Type", "/XObject")
    doc.xref_set_key(xref, "Subtype", "/Image")
    doc.xref_set_key(xref, "Filter", "/JBIG2Decode")
    doc.xref_set_key(xref, "DecodeParms", "null")
    doc.xref_set_key(xref, "Width", str(width))
    doc.xref_set_key(xref, "Height", str(height))
    doc.xref_set_key(xref, "BitsPerComponent", "1")
    doc.xref_set_key(xref, "ColorSpace", "/DeviceGray")


def _saved_image_stream_size(pdf_bytes):
    """Byte size of the (single) image stream in a one-page throwaway PDF, after save."""
    check_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        xref = check_doc[0].get_images(full=True)[0][0]
        return len(check_doc.xref_stream_raw(xref))
    finally:
        check_doc.close()


def _verify_and_measure_jbig2(jbig2_bytes, bw_img):
    """Confirm jbig2_bytes decodes pixel-exact via MuPDF, and measure the size
    it would actually occupy once saved with compress_pdf()'s own save flags.

    Returns (verified, embedded_size); embedded_size is None when verified
    is False.
    """
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
        if decoded_bw.tobytes() != bw_img.tobytes():
            return False, None

        pdf_bytes = check_doc.tobytes(garbage=4, deflate=True, clean=True)
    finally:
        check_doc.close()

    return True, _saved_image_stream_size(pdf_bytes)


def _g4_embedded_size(tiff_bytes, width, height):
    """Measure the CCITT G4 candidate's actual final size, embedded the same
    way compress_pdf() does (Page.replace_image, then the real save flags).

    MuPDF decodes the incoming TIFF and re-encodes on save (typically to
    FlateDecode over the raw bitmap) -- the TIFF's own byte count is not a
    reliable proxy for what ends up on disk, so this materializes it for real
    in a cheap one-page throwaway document instead of estimating.
    """
    doc = fitz.open()
    try:
        page = doc.new_page(width=width, height=height)
        placeholder = fitz.Pixmap(fitz.csGRAY, fitz.IRect(0, 0, width, height))
        placeholder.clear_with(255)
        xref = page.insert_image(fitz.Rect(0, 0, width, height), pixmap=placeholder)
        page.replace_image(xref, stream=tiff_bytes)
        pdf_bytes = doc.tobytes(garbage=4, deflate=True, clean=True)
    finally:
        doc.close()
    return _saved_image_stream_size(pdf_bytes)


def encode_jbig2_lossless(bw_img, g4_tiff_bytes):
    """Encode a 1-bit PIL image with jbig2enc's generic-region (lossless) coder.

    Returns the raw PDF-ready JBIG2 stream only when it's verified to decode
    back to the exact same bitmap AND confirmed smaller than the CCITT G4
    candidate once both are actually saved the way compress_pdf() saves the
    real document. Returns None if the encoder is unavailable, fails, the
    roundtrip doesn't match, or it simply doesn't win on size -- in every
    case the caller should keep using CCITT G4.
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

    verified, jbig2_size = _verify_and_measure_jbig2(jbig2_bytes, bw_img)
    if not verified:
        print("Warning: jbig2 output failed roundtrip verification. Using CCITT G4 instead.", file=sys.stderr)
        return None

    g4_size = _g4_embedded_size(g4_tiff_bytes, bw_img.width, bw_img.height)
    if jbig2_size >= g4_size:
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
            f"{_jbig2_install_hint()}. Falling back to CCITT G4 for all bw-mode pages for now.",
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
                                jbig2_bytes = encode_jbig2_lossless(bw_img, out_io.getvalue())
                                if jbig2_bytes is not None:
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
