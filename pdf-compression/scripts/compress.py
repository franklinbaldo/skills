import argparse
import io
import os
import sys

import fitz
from PIL import Image


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


def compress_pdf(
    input_path,
    output_path,
    mode="auto",
    max_dim=1200,
    quality=50,
    skip_small=150,
    denoise=False,
    enhance_contrast=False,
):
    if not os.path.exists(input_path):
        print(f"Error: Input file '{input_path}' does not exist.", file=sys.stderr)
        sys.exit(1)

    print(f"Opening PDF: {input_path}...")
    try:
        doc = fitz.open(input_path)
    except (RuntimeError, OSError) as e:
        print(f"Error opening PDF: {e}", file=sys.stderr)
        sys.exit(1)

    total_pages = len(doc)
    print(f"Total pages: {total_pages}")

    # Classify pages to decide on compression strategy
    print("Classifying pages (scanned vs native digital)...")
    page_classifications = {}
    for page_idx in range(total_pages):
        page_classifications[page_idx] = (
            "scanned" if is_scanned_page(doc[page_idx]) else "digital"
        )

    scanned_count = sum(1 for c in page_classifications.values() if c == "scanned")
    print(
        f"Classification summary: {scanned_count} scanned pages, {total_pages - scanned_count} native digital pages."
    )

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

    for count, xref in enumerate(unique_xrefs, 1):
        page_idx = image_to_page[xref]
        page = doc[page_idx]

        if count % 100 == 0 or count == 1:
            print(
                f"Processing image {count}/{total_unique} (xref: {xref}, page: {page_idx})..."
            )
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
            if img.mode in ("RGBA", "LA") or (
                img.mode == "P" and "transparency" in img.info
            ):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "RGBA":
                    background.paste(img, mask=img.split()[-1])
                else:
                    background.paste(
                        img.convert("RGBA"), mask=img.convert("RGBA").split()[-1]
                    )
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
                                gray_arr = cv2.fastNlMeansDenoising(
                                    gray_arr,
                                    None,
                                    h=10,
                                    templateWindowSize=7,
                                    searchWindowSize=21,
                                )

                            # Optional: Contrast Enhancement (CLAHE)
                            if enhance_contrast:
                                clahe = cv2.createCLAHE(
                                    clipLimit=2.0, tileGridSize=(8, 8)
                                )
                                gray_arr = clahe.apply(gray_arr)

                            # Apply Gaussian Adaptive Thresholding
                            thresh_arr = cv2.adaptiveThreshold(
                                gray_arr,
                                255,
                                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY,
                                21,
                                15,
                            )

                            # Optional: Post-binarization Median Blur
                            if denoise:
                                thresh_arr = cv2.medianBlur(thresh_arr, 3)

                            bw_img = Image.fromarray(thresh_arr).convert("1")
                        except (
                            ImportError,
                            AttributeError,
                            ValueError,
                            TypeError,
                        ) as e:
                            # Fallback to standard Pillow thresholding if cv2/numpy fails
                            print(
                                f"Warning: OpenCV adaptive threshold failed ({e}). Falling back to simple threshold.",
                                file=sys.stderr,
                            )
                            gray_img = img.convert("L")
                            bw_img = gray_img.point(
                                lambda x: 0 if x < 128 else 255, mode="1"
                            )

                        bw_img.save(out_io, format="TIFF", compression="group4")
                    elif current_mode == "gray":
                        gray_img = img.convert("L")
                        try:
                            import cv2
                            import numpy as np

                            gray_arr = np.array(gray_img)
                            if denoise:
                                gray_arr = cv2.fastNlMeansDenoising(
                                    gray_arr,
                                    None,
                                    h=10,
                                    templateWindowSize=7,
                                    searchWindowSize=21,
                                )
                            if enhance_contrast:
                                clahe = cv2.createCLAHE(
                                    clipLimit=2.0, tileGridSize=(8, 8)
                                )
                                gray_arr = clahe.apply(gray_arr)
                            gray_img = Image.fromarray(gray_arr)
                        except (ImportError, AttributeError, ValueError, TypeError):
                            pass
                        gray_img.save(
                            out_io, format="JPEG", quality=quality, optimize=True
                        )
                    else:  # color
                        color_img = img.convert("RGB")
                        color_img.save(
                            out_io, format="JPEG", quality=quality, optimize=True
                        )

                    compressed_bytes = out_io.getvalue()
                except Exception as e:
                    print(
                        f"Warning: Mode '{current_mode}' failed for image {xref}: {e}. Trying fallback...",
                        file=sys.stderr,
                    )
                    if current_mode == "bw":
                        current_mode = "gray"
                    elif current_mode == "gray":
                        current_mode = "color"
                    else:
                        raise

            page.replace_image(xref, stream=compressed_bytes)
            replaced_count += 1

        except Exception as e:  # noqa: BLE001
            print(
                f"Error compressing image {xref} on page {page_idx}: {e}",
                file=sys.stderr,
            )
            sys.stdout.flush()

    print(
        f"\nProcessing complete. Replaced: {replaced_count}, Skipped: {skipped_count}"
    )
    print(f"Saving optimized PDF to: {output_path}...")
    sys.stdout.flush()

    try:
        doc.save(output_path, garbage=4, deflate=True, clean=True)
        print("Save complete!")

        orig_size = os.path.getsize(input_path)
        new_size = os.path.getsize(output_path)
        print(f"Original size: {orig_size / 1024 / 1024:.2f} MB")
        print(f"Compressed size: {new_size / 1024 / 1024:.2f} MB")
        print(f"Reduction: {(1 - new_size / orig_size) * 100:.1f}%")
        doc.close()
    except (RuntimeError, OSError) as e:
        print(f"Error saving PDF: {e}", file=sys.stderr)
        doc.close()
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compress PDF with smart scanned vs. native page optimization."
    )
    parser.add_argument("--input", required=True, help="Path to input PDF file")
    parser.add_argument(
        "--output", required=True, help="Path to output compressed PDF file"
    )
    parser.add_argument(
        "--mode",
        choices=["bw", "gray", "color", "auto"],
        default="auto",
        help="Compression mode (default: auto)",
    )
    parser.add_argument(
        "--max-dim",
        type=int,
        default=1200,
        help="Maximum dimension of images (default: 1200)",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=50,
        help="JPEG quality for color/gray modes (default: 50)",
    )
    parser.add_argument(
        "--skip-small",
        type=int,
        default=150,
        help="Skip images smaller than this threshold (default: 150)",
    )
    parser.add_argument(
        "--denoise", action="store_true", help="Apply NLM denoising to scanned pages"
    )
    parser.add_argument(
        "--enhance-contrast",
        action="store_true",
        help="Apply contrast enhancement to scanned pages",
    )

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
    )
