import os
import sys
import re
import argparse
import subprocess

def clean_text(text):
    """Clean repeating headers, footers and typical system stamps from court documents."""
    # Remove ComunicaAPI URLs and Certidão stamps
    text = re.sub(r'https://comunicaapi\.pje\.jus\.br/api/v1/comunicacao/\S+', '', text)
    text = re.sub(r'Código da certidão:\s*\S+', '', text)
    
    # Remove repeating page headers/footers from DJEN/STJ
    text = re.sub(r'Poder Judiciário\s*Superior Tribunal de Justiça\s*Diário de Justiça Eletrônico Nacional de \d\d/\d\d/\d\d\d\d\s*Certidão de publicação \d+', '', text)
    
    # Remove double newlines/whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def split_and_save_documents(pages_data, outdir, base_pdf_name):
    """Split the extracted pages into separate documents based on detected titles."""
    # Common document markers that start a new court document
    doc_markers = [
        r'INTIMAÇÃO',
        r'SENTENÇA',
        r'DECISÃO',
        r'DESPACHO',
        r'PETIÇÃO',
        r'CONTRARRAZÕES',
        r'PROCURAÇÃO',
        r'ATA DE DISTRIBUIÇÃO',
        r'CERTIDÃO',
        r'PARECER',
        r'MANIFESTAÇÃO',
        r'OFÍCIO'
    ]
    
    # Combine markers into regex
    marker_regex = re.compile(r'^\s*(' + '|'.join(doc_markers) + r')\b', re.IGNORECASE | re.MULTILINE)
    
    current_doc_title = "Documento_Geral"
    current_doc_pages = []
    doc_counter = 0
    index_entries = []
    
    def save_current_doc():
        nonlocal doc_counter
        if not current_doc_pages:
            return
        
        doc_counter += 1
        clean_title = re.sub(r'[^a-zA-Z0-9_]', '_', current_doc_title.strip().replace(" ", "_")).lower()
        # Truncate title
        clean_title = clean_title[:40]
        filename = f"{doc_counter:02d}_{clean_title}.md"
        filepath = os.path.join(outdir, filename)
        
        content = "\n\n".join(current_doc_pages)
        content = clean_text(content)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# {current_doc_title.upper()}\n\n")
            f.write(content)
            
        print(f"  Saved: {filename} ({len(content)} chars)")
        
        # Add to index entries: (sequence, title, filename, snippet)
        snippet = content[:150].replace('\n', ' ') + '...'
        index_entries.append((doc_counter, current_doc_title, filename, snippet))
        
        current_doc_pages.clear()

    for idx, page_text in enumerate(pages_data):
        page_num = idx + 1
        # Try to find a new document title at the beginning of the page (first 300 characters)
        start_of_page = page_text[:300]
        match = marker_regex.search(start_of_page)
        
        if match:
            # We found a new document start! Save the previous one first.
            save_current_doc()
            # Determine title: extract the line containing the marker
            matched_line = ""
            for line in start_of_page.splitlines():
                if match.group(1).lower() in line.lower():
                    matched_line = line.strip()
                    break
            
            current_doc_title = matched_line if matched_line else match.group(1).title()
            # Clean up title if it contains numbers or weird punctuation
            current_doc_title = re.sub(r'[\r\n\t]', ' ', current_doc_title)
            current_doc_title = re.sub(r'\s+', ' ', current_doc_title)
            current_doc_title = current_doc_title.strip(":- ")
            if not current_doc_title:
                current_doc_title = match.group(1).title()
                
        current_doc_pages.append(f"<!-- Page {page_num} -->\n{page_text}")
        
    # Save the last document
    save_current_doc()
    
    # Generate INDEX.md
    generate_index(outdir, base_pdf_name, index_entries)

def generate_index(outdir, base_pdf_name, index_entries):
    index_path = os.path.join(outdir, "INDEX.md")
    case_number = base_pdf_name.replace(".pdf", "")
    
    # Simple formatting of case number if it fits standard CNJ pattern
    formatted_case = case_number
    if len(case_number) == 20 and case_number.isdigit():
        formatted_case = f"{case_number[0:7]}-{case_number[7:9]}.{case_number[9:13]}.{case_number[13:14]}.{case_number[14:16]}.{case_number[16:20]}"
        
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(f"# Processo Judicial: {formatted_case}\n\n")
        f.write(f"Documentos extraídos do arquivo original: `{base_pdf_name}`\n\n")
        f.write("## Índice de Documentos\n\n")
        f.write("| # | Documento | Arquivo | Resumo / Início |\n")
        f.write("|---|-----------|---------|-----------------|\n")
        for seq, title, filename, snippet in index_entries:
            f.write(f"| {seq} | **{title}** | [{filename}](./{filename}) | {snippet} |\n")
            
    print(f"  Generated INDEX.md successfully.")

def convert_with_markitdown(pdf_path, keep_data_uris=False, docintel_endpoint=None, cu_endpoint=None):
    """Try to convert PDF with markitdown via uv run."""
    print("Attempting high-fidelity conversion using markitdown via uv...")
    try:
        # We run markitdown using uv run so we don't need it installed globally
        cmd = ["uv", "run", "--no-project", "--with", "markitdown[pdf]", "markitdown"]
        
        if keep_data_uris:
            cmd.append("--keep-data-uris")
        if docintel_endpoint:
            cmd.extend(["-d", "-e", docintel_endpoint])
        if cu_endpoint:
            cmd.extend(["--use-cu", "--cu-endpoint", cu_endpoint])
            
        cmd.append(pdf_path)
        
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
        if result.returncode == 0:
            print("Successfully converted PDF with markitdown.")
            # Splitting markitdown output by pages (usually uses '---' or page breaks)
            # Since markitdown produces single text, we will split by typical page break marker
            pages = result.stdout.split('\n---\n')
            if len(pages) <= 1:
                pages = result.stdout.split('\f') # form feed
            return pages
        else:
            print(f"markitdown failed with code {result.returncode}: {result.stderr}")
            return None
    except Exception as e:
        print(f"Could not execute markitdown via uv: {e}")
        return None

def convert_with_pymupdf(pdf_path):
    """Fallback: convert PDF using PyMuPDF (fitz)."""
    print("Falling back to PyMuPDF (fitz) for conversion...")
    try:
        import fitz
        doc = fitz.open(pdf_path)
        pages_data = []
        for page in doc:
            pages_data.append(page.get_text())
        print(f"Successfully extracted {len(pages_data)} pages using PyMuPDF.")
        return pages_data
    except Exception as e:
        print(f"PyMuPDF extraction failed: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Convert court process PDFs into clean structured Markdown folders.")
    parser.add_argument("--input", required=True, help="Path to the input PDF file.")
    parser.add_argument("--outdir", required=True, help="Directory to save the markdown files.")
    parser.add_argument("--keep-data-uris", action="store_true", help="Keep data URIs in output.")
    parser.add_argument("--docintel-endpoint", help="Azure Document Intelligence Endpoint URL.")
    parser.add_argument("--cu-endpoint", help="Azure Content Understanding Endpoint URL.")
    
    args = parser.parse_args()
    
    pdf_path = os.path.abspath(args.input)
    outdir = os.path.abspath(args.outdir)
    
    if not os.path.exists(pdf_path):
        print(f"Error: Input file does not exist: {pdf_path}")
        sys.exit(1)
        
    os.makedirs(outdir, exist_ok=True)
    base_pdf_name = os.path.basename(pdf_path)
    
    print(f"Processing: {base_pdf_name}")
    print(f"Output directory: {outdir}")
    
    # Try markitdown first, fallback to PyMuPDF
    pages_data = convert_with_markitdown(
        pdf_path,
        keep_data_uris=args.keep_data_uris,
        docintel_endpoint=args.docintel_endpoint,
        cu_endpoint=args.cu_endpoint
    )
    if not pages_data:
        pages_data = convert_with_pymupdf(pdf_path)
        
    if not pages_data:
        print("Error: All conversion methods failed.")
        sys.exit(1)
        
    split_and_save_documents(pages_data, outdir, base_pdf_name)
    print("\nConversion finished successfully!")

if __name__ == "__main__":
    main()
