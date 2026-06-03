import argparse
import fitz
import io
import os
import sys
from PIL import Image

def compress_pdf(input_path, output_path, mode="bw", max_dim=1200, quality=50, skip_small=150):
    if not os.path.exists(input_path):
        print(f"Error: Input file '{input_path}' does not exist.", file=sys.stderr)
        sys.exit(1)
        
    print(f"Opening PDF: {input_path}...")
    try:
        doc = fitz.open(input_path)
    except Exception as e:
        print(f"Error opening PDF: {e}", file=sys.stderr)
        sys.exit(1)
        
    total_pages = len(doc)
    print(f"Total pages: {total_pages}")
    
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
                
            # Compress based on mode with fallbacks
            compressed_bytes = None
            current_mode = mode
            
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
                            # Apply Gaussian Adaptive Thresholding
                            # Block size 21 is a good balance; C=15 helps clear background noise
                            thresh_arr = cv2.adaptiveThreshold(
                                gray_arr, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY, 21, 15
                            )
                            bw_img = Image.fromarray(thresh_arr).convert("1")
                        except Exception as e:
                            # Fallback to standard Pillow thresholding if cv2/numpy fails
                            print(f"Warning: OpenCV adaptive threshold failed ({e}). Falling back to simple threshold.", file=sys.stderr)
                            gray_img = img.convert("L")
                            bw_img = gray_img.point(lambda x: 0 if x < 128 else 255, mode="1")
                        
                        bw_img.save(out_io, format="TIFF", compression="group4")
                    elif current_mode == "gray":
                        gray_img = img.convert("L")
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
                        raise e  # If everything fails, propagate exception
            
            page.replace_image(xref, stream=compressed_bytes)
            replaced_count += 1
            
        except Exception as e:
            print(f"Error compressing image {xref} on page {page_idx}: {e}", file=sys.stderr)
            sys.stdout.flush()
            
    print(f"\nProcessing complete. Replaced: {replaced_count}, Skipped: {skipped_count}")
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
    except Exception as e:
        print(f"Error saving PDF: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compress PDF by downscaling and re-encoding images.")
    parser.add_argument("--input", required=True, help="Path to input PDF file")
    parser.add_argument("--output", required=True, help="Path to output compressed PDF file")
    parser.add_argument("--mode", choices=["bw", "gray", "color"], default="bw", help="Compression mode (default: bw / CCITT Group 4)")
    parser.add_argument("--max-dim", type=int, default=1200, help="Maximum dimension (width/height) of images (default: 1200)")
    parser.add_argument("--quality", type=int, default=50, help="JPEG quality for color/gray modes (default: 50)")
    parser.add_argument("--skip-small", type=int, default=150, help="Skip images smaller than this width/height (default: 150)")
    
    args = parser.parse_args()
    compress_pdf(
        input_path=args.input,
        output_path=args.output,
        mode=args.mode,
        max_dim=args.max_dim,
        quality=args.quality,
        skip_small=args.skip_small
    )
