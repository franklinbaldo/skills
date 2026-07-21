import os
import sys
import argparse
import fitz  # PyMuPDF

def make_2up(input_path, output_path):
    if not os.path.exists(input_path):
        print(f"Error: Input file '{input_path}' does not exist.", file=sys.stderr)
        sys.exit(1)
        
    print(f"Opening PDF: {input_path}...")
    src = fitz.open(input_path)
    doc = fitz.open()
    
    total_pages = len(src)
    print(f"Total pages: {total_pages}")
    
    for i in range(0, total_pages, 2):
        p1 = src[i]
        w1, h1 = p1.rect.width, p1.rect.height
        
        if i + 1 < total_pages:
            p2 = src[i+1]
            w2, h2 = p2.rect.width, p2.rect.height
        else:
            p2 = None
            w2, h2 = 0, 0
            
        out_w = w1 + w2
        out_h = max(h1, h2)
        
        if p2 is None:
            out_w = w1
            out_h = h1
            
        new_page = doc.new_page(width=out_w, height=out_h)
        orig_rot1 = p1.rotation
        if orig_rot1 != 0:
            p1.set_rotation(0)
        new_page.show_pdf_page(fitz.Rect(0, 0, w1, h1), src, i, rotate=(360 - orig_rot1) % 360)
        
        if p2 is not None:
            orig_rot2 = p2.rotation
            if orig_rot2 != 0:
                p2.set_rotation(0)
            new_page.show_pdf_page(fitz.Rect(w1, 0, w1 + w2, h2), src, i+1, rotate=(360 - orig_rot2) % 360)



            
    print(f"Saving 2-up PDF to: {output_path}...")
    doc.save(output_path)
    doc.close()
    src.close()
    print("Conversion complete!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Combine consecutive PDF pages side-by-side (2-up layout).")
    parser.add_argument("--input", required=True, help="Path to input PDF file")
    parser.add_argument("--output", required=True, help="Path to output 2-up PDF file")
    args = parser.parse_args()
    make_2up(args.input, args.output)
