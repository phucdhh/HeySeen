import subprocess
import os
from pathlib import Path

tex_dir = Path('/Users/m2pro/HeySeen/internet_data_test/tex_original')
pdf_dir = Path('/Users/m2pro/HeySeen/internet_data_test/pdf')

for tex_file in tex_dir.glob('*.tex'):
    base = tex_file.stem
    pdf_file = pdf_dir / f"{base}.pdf"
    try:
        # Run pdflatex, output to temp
        result = subprocess.run(['pdflatex', '-interaction=nonstopmode', '-output-directory', '/tmp', str(tex_file)], 
                                capture_output=True, text=True, timeout=60)
        temp_pdf = Path('/tmp') / f"{base}.pdf"
        if temp_pdf.exists():
            temp_pdf.rename(pdf_file)
            print(f"Compiled {base}.pdf")
        else:
            print(f"No PDF generated for {base}: {result.stderr[:200]}")
    except subprocess.TimeoutExpired:
        print(f"Timed out compiling {base}")
    except Exception as e:
        print(f"Error compiling {base}: {e}")