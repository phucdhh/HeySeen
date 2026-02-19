"""
TeX Builder Module

Reconstructs LaTeX documents from extracted content.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from pathlib import Path
import json
import re
from datetime import datetime

from .content_extractor import ExtractedContent
from .layout_analyzer import LayoutBlock


@dataclass
class TeXDocument:
    """LaTeX document metadata and content"""
    
    title: str = "Converted Document"
    author: str = "HeySeen"
    date: str = ""
    pages: List[Dict] = None
    
    def __post_init__(self):
        if not self.date:
            self.date = datetime.now().strftime("%Y-%m-%d")
        if self.pages is None:
            self.pages = []


class TeXBuilder:
    """Build LaTeX documents from extracted content"""
    
    def __init__(self, output_dir: Path, verbose: bool = True):
        """
        Initialize TeX builder.
        
        Args:
            output_dir: Directory to save output files
            verbose: Print progress messages
        """
        self.output_dir = Path(output_dir)
        self.verbose = verbose
        
        # Create output directory structure
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir = self.output_dir / "images"
        self.images_dir.mkdir(exist_ok=True)
        
        if verbose:
            print(f"✓ Output directory: {output_dir}")
    
    def build_document(
        self,
        contents_per_page: List[List[ExtractedContent]],
        blocks_per_page: List[List[LayoutBlock]],
        document_info: Optional[Dict] = None,
    ) -> Path:
        """
        Build complete LaTeX document.
        
        Args:
            contents_per_page: Extracted content for each page
            blocks_per_page: Layout blocks for each page (for metadata)
            document_info: Optional document metadata
            
        Returns:
            Path to main.tex file
        """
        if self.verbose:
            print(f"\n→ Building LaTeX document...")
        
        # Create document structure
        doc = TeXDocument()
        if document_info:
            doc.title = document_info.get("title", doc.title)
            doc.author = document_info.get("author", doc.author)
        
        # Generate LaTeX content (minimal mode)
        tex_content = self._generate_preamble(doc, minimal=True)
        tex_content += "\n\\begin{document}\n\n"
        tex_content += self._generate_title_page(doc, skip=True)
        tex_content += "\n"
        
        # Process each page
        for page_num, (contents, blocks) in enumerate(zip(contents_per_page, blocks_per_page), 1):
            if self.verbose:
                print(f"  Page {page_num}: {len(contents)} blocks")
            
            page_tex = self._generate_page(page_num, contents, blocks)
            tex_content += page_tex
            tex_content += "\n\\newpage\n\n"
            
            # Store metadata
            doc.pages.append({
                "page_num": page_num,
                "blocks": len(blocks),
                "text_blocks": sum(1 for c in contents if c.text),
                "latex_blocks": sum(1 for c in contents if c.latex),
                "image_blocks": sum(1 for c in contents if c.image_path),
            })
        
        tex_content += "\\end{document}\n"
        
        # Write main.tex
        main_tex_path = self.output_dir / "main.tex"
        with open(main_tex_path, "w", encoding="utf-8") as f:
            f.write(tex_content)
        
        # Write metadata
        meta_path = self.output_dir / "meta.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump({
                "title": doc.title,
                "author": doc.author,
                "date": doc.date,
                "total_pages": len(doc.pages),
                "pages": doc.pages,
                "generated_by": "HeySeen v0.1.0",
                "timestamp": datetime.now().isoformat(),
            }, f, indent=2, ensure_ascii=False)
        
        if self.verbose:
            print(f"✓ LaTeX document created: {main_tex_path}")
            print(f"✓ Metadata saved: {meta_path}")
        
        return main_tex_path
    
    def _generate_preamble(self, doc: TeXDocument, minimal: bool = True) -> str:
        """Generate LaTeX preamble with packages and settings"""
        if minimal:
            # Minimal preamble for clean comparison
            preamble = r"""\documentclass[12pt,a4paper]{article}
\usepackage{amsmath,amssymb,amsfonts,amsthm}
\usepackage{graphicx}
\usepackage{geometry}
\geometry{margin=2.5cm}
\setlength{\parindent}{0pt}
\setlength{\parskip}{6pt}

\newtheorem{theorem}{Theorem}[section]
\newtheorem{lemma}[theorem]{Lemma}
\newtheorem*{proof_custom}{Proof}
\renewcommand{\abstractname}{\Large\bfseries Abstract}

"""
        else:
            # Full preamble with all features
            preamble = r"""\documentclass[12pt,a4paper]{article}

% Essential packages
%\usepackage[utf8]{inputenc}
%\usepackage[T1]{fontenc}
%\usepackage[vietnamese]{babel}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{graphicx}
\usepackage{hyperref}
\usepackage{xcolor}
\usepackage{geometry}

% Page layout
\geometry{margin=2.5cm}
\setlength{\parindent}{0pt}
\setlength{\parskip}{6pt}

% Hyperref settings
\hypersetup{
    colorlinks=true,
    linkcolor=blue,
    urlcolor=blue,
    citecolor=blue
}

% Custom commands
\newcommand{\blocktitle}[1]{\textbf{\large #1}\par\vspace{6pt}}
\newcommand{\blockcaption}[1]{\textit{#1}\par\vspace{4pt}}

"""
        return preamble
    
    def _generate_title_page(self, doc: TeXDocument, skip: bool = True) -> str:
        """Generate title page (optional)"""
        if skip:
            return ""  # No title page for clean comparison
        
        return f"""\\title{{{doc.title}}}
\\author{{{doc.author}}}
\\date{{{doc.date}}}
\\maketitle

\\tableofcontents
\\newpage

"""
    
    def _generate_page(
        self,
        page_num: int,
        contents: List[ExtractedContent],
        blocks: List[LayoutBlock],
    ) -> str:
        """Generate LaTeX for a single page with smart merging"""
        page_tex = f"% Page {page_num}\n"
        
        # Merge consecutive text blocks into paragraphs
        merged_items = self._merge_text_blocks(contents, blocks)
        
        # Apply Semantic Refinement (Abstract, Theorem, Proof, TOC fix)
        merged_items = self._refine_semantics(merged_items, page_num)
        
        # Extract first title as section heading
        first_title = None
        for item in merged_items[:]: # Iterate over a copy to allow modification
            if item and item.get('type') == 'title':
                first_title = item['text']
                merged_items.remove(item)
                break
        
        if first_title:
            page_tex += f"\\section*{{{self._escape_latex(first_title)}}}\n\n"
        # Removed auto-generated Page section
        
        # Generate content with structure awareness
        in_list = False
        in_abstract = False
        
        for item in merged_items:
            # Handle Abstract Environment
            if item.get('type') == 'abstract':
                if not in_abstract:
                     page_tex += "\\begin{abstract}\n"
                     in_abstract = True
                
                text = item['text']
                # Strip prefix
                text = re.sub(r'^(Abstract|Tóm tắt)[:.]?\s*', '', text, flags=re.IGNORECASE)
                page_tex += f"{self._escape_latex(text)}\n"
                continue # Stay in abstract until non-abstract item
            else:
                 if in_abstract:
                     page_tex += "\\end{abstract}\n\n"
                     in_abstract = False
            
            if item['type'] == 'title':
                # Close any open list
                if in_list:
                    page_tex += "\\end{itemize}\n\n"
                    in_list = False
                page_tex += f"\\subsection*{{{self._escape_latex(item['text'])}}}\n\n"

            elif item['type'] == 'theorem':
                # Close any open list
                if in_list:
                    page_tex += "\\end{itemize}\n\n"
                    in_list = False
                
                # Parse title from text (Theorem 1.1: ...)
                text = item['text']
                match = re.search(r'^(Định lý|Theorem|Lemma|Bổ đề|Tính chất|Hệ quả)(.*?)(:|.)\s*(.*)', text, re.IGNORECASE | re.DOTALL)
                
                env_name = "theorem"
                if match:
                    prefix_type = match.group(1).lower()
                    if "lemma" in prefix_type or "bổ đề" in prefix_type:
                        env_name = "lemma"
                    
                    label = match.group(2).strip()
                    content = match.group(4).strip()
                    opt_arg = f"[{label}]" if label and len(label) < 20 else ""
                    
                    page_tex += f"\\begin{{{env_name}}}{opt_arg}\n{self._escape_latex(content)}\n\\end{{{env_name}}}\n\n"
                else:
                    page_tex += f"\\begin{{theorem}}\n{self._escape_latex(text)}\n\\end{{theorem}}\n\n"

            elif item['type'] == 'proof':
                 # Close any open list
                if in_list:
                    page_tex += "\\end{itemize}\n\n"
                    in_list = False
                
                text = item['text']
                # Strip "Proof." prefix
                text = re.sub(r'^(Proof|Tóm tắt|Chứng minh)(\s*[.:])?\s*', '', text, flags=re.IGNORECASE)
                page_tex += f"\\begin{{proof}}\n{self._escape_latex(text)}\n\\end{{proof}}\n\n"
            
            elif item['type'] == 'section':
                # Close any open list
                if in_list:
                    page_tex += "\\end{itemize}\n\n"
                    in_list = False
                page_tex += f"\\section{{{self._escape_latex(item['text'])}}}\n\n"
            
            elif item['type'] == 'subsection':
                # Close any open list
                if in_list:
                    page_tex += "\\end{itemize}\n\n"
                    in_list = False
                page_tex += f"\\subsection{{{self._escape_latex(item['text'])}}}\n\n"
            
            elif item['type'] == 'subsubsection':
                # Close any open list
                if in_list:
                    page_tex += "\\end{itemize}\n\n"
                    in_list = False
                page_tex += f"\\subsubsection{{{self._escape_latex(item['text'])}}}\n\n"
            
            elif item['type'] == 'list-item':
                # Open list if needed
                if not in_list:
                    page_tex += "\\begin{itemize}\n"
                    in_list = True
                # Remove bullet/number from text
                text = item['text'].lstrip('•-* ').lstrip('0123456789.abcABC.) ')
                page_tex += f"  \\item {self._escape_latex(text)}\n"
            
            elif item['type'] == 'paragraph':
                # Close any open list
                if in_list:
                    page_tex += "\\end{itemize}\n\n"
                    in_list = False
                # Add paragraph with proper spacing
                # Check for "References" title
                if re.match(r'^(References|Tài liệu tham khảo|Bibliography)', item['text'], re.IGNORECASE):
                     page_tex += f"\\section*{{{self._escape_latex(item['text'])}}}\n\n"
                else:
                     escaped = self._escape_latex(item['text'])
                     page_tex += f"{escaped}\n\n"
            elif item['type'] == 'math':
                # Close any open list
                if in_list:
                    page_tex += "\\end{itemize}\n\n"
                    in_list = False
                # latex is already cleaned (no outer $$ delimiters)
                latex = item['latex'].strip()
                if latex:  # Skip empty math blocks
                    page_tex += f"\\[\\n{latex}\\n\\]\n\n"
            
            elif item['type'] == 'table':
                # Close any open list
                if in_list:
                    page_tex += "\\end{itemize}\n\n"
                    in_list = False
                
                # Insert table latex directly if available
                if item['latex']:
                    page_tex += f"\n{item['latex']}\n\n"
            
            elif item['type'] == 'raw_latex':
                 # Close any open list
                if in_list:
                    page_tex += "\\end{itemize}\n\n"
                    in_list = False
                # Insert raw latex directly
                if item.get('latex'):
                    page_tex += f"\n{item['latex']}\n\n"

                # Handle Fallback where type is 'table' but has text content (Rejected by TATR)
                elif item.get('text'):
                     # Treat like a paragraph
                     escaped = self._escape_latex(item['text'])
                     page_tex += f"{escaped}\n\n"
                     
                # Fallback to Image (handled by separate 'image' type usually, but just in case)
                elif item.get('image_path'):
                     # Call image handler logic (duplicated slightly for safety)
                     image_path = Path(item['image_path'])
                     rel_path = image_path.relative_to(self.output_dir) if image_path.is_absolute() else image_path
                     
                     page_tex += f"\\begin{{figure}}[h]\n"
                     page_tex += f"  \\centering\n"
                     page_tex += f"  \\includegraphics[width=0.8\\textwidth]{{{rel_path}}}\n"
                     page_tex += f"  \\caption{{Figure from page {page_num}}}\n"
                     page_tex += f"\\end{{figure}}\n\n"
            
            elif item['type'] == 'image':
                # Close any open list
                if in_list:
                    page_tex += "\\end{itemize}\n\n"
                    in_list = False
                image_path = Path(item['image_path'])
                rel_path = image_path.relative_to(self.output_dir) if image_path.is_absolute() else image_path
                
                page_tex += f"\\begin{{figure}}[h]\n"
                page_tex += f"  \\centering\n"
                page_tex += f"  \\includegraphics[width=0.8\\textwidth]{{{rel_path}}}\n"
                page_tex += f"  \\caption{{Figure from page {page_num}}}\n"
                page_tex += f"\\end{{figure}}\n\n"
        
        # Cleanup abstract close
        if in_abstract:
            page_tex += "\\end{abstract}\n\n"
        
        # Close any remaining open list
        if in_list:
            page_tex += "\\end{itemize}\n\n"
        
        return page_tex
    
    def _merge_text_blocks(
        self,
        contents: List[ExtractedContent],
        blocks: List[LayoutBlock],
    ) -> List[Dict]:
        """
        Merge consecutive text blocks into paragraphs with structure awareness.
        
        Breaks paragraphs when:
        - Encountering math/images
        - Large vertical gap (> 2x line height)
        - Horizontal position change (column switch)
        - Structure change (title/section/text)
        """
        merged = []
        current_paragraph = []
        prev_block = None
        
        import re
        noise_pattern = re.compile(r'^\s*\d+\s*$')
        # Robust equation number pattern: (1.1), [1.1], (1 . 1)
        eq_num_pattern = re.compile(r'^\s*[\(\[]\s*(\d+(?:[\.\s]\d+)*)\s*[\)\]][\.\,\;]?\s*$')
        
        # Pattern to detect "Title 1" -> "1 Title" (Reading order fix)
        # Matches: Any text (non-dot end) + space + Number (e.g. "1", "2.1")
        # Excludes "Equation 1" if it might be a reference, but generally for headers this is safe
        trailing_num_re = re.compile(r'^([^\.]+?)\s+(\d+(\.\d+)*)$')

        for content, block in zip(contents, blocks):
            # 0. Noise Cleaning (Standalone Page Numbers)
            if content.text and noise_pattern.match(content.text):
                # Only if at very top or bottom of page (approx)
                if block.bbox.y0 < 0.1 or block.bbox.y0 > 0.9:
                    continue
            
            # 0.1 Structural Repair (Reading Order Swaps)
            if content.text and len(content.text) < 80:
                # Check for "Text Number" pattern
                m = trailing_num_re.match(content.text.strip())
                if m:
                    text_part = m.group(1).strip()
                    num_part = m.group(2)
                    # Heuristic: Only swap if text looks like a title (starts capital) 
                    # or contains Header keywords
                    if text_part and (text_part[0].isupper() or "Trang" in text_part):
                        content.text = f"{num_part} {text_part}"

            # 0.5 Tagging Detection (Eq Number detection)
            if content.text and eq_num_pattern.match(content.text):
                tag_match = eq_num_pattern.match(content.text)
                tag_val = tag_match.group(1)
                
                # Attach to PREVIOUS element if possible
                if current_paragraph:
                    # Append as string, though this is rare inside paragraph unless inline
                    # Better to treat as display math tag?
                    # If current paragraph is open, just append it? No, tags go on Math.
                    # If this line is JUST a number, it shouldn't break the paragraph?
                    # OR if we just finished a math block?
                    pass
                
                # Check if we should attach to the LAST added merged item (likely a math block)
                # Flush current paragraph first?
                if not current_paragraph and merged and merged[-1]['type'] == 'math':
                     # We can't easily inject \tag into texify output string without parsing.
                     # But we can append \tag{} to the latex string.
                     last_item = merged[-1]
                     # Check if it already has a tag?
                     if 'latex' in last_item:
                         last_item['latex'] += f" \\tag{{{tag_val}}}"
                         continue # Consumed this block
            
            # Calculate gap and decide whether to break paragraph
            should_break = False
            
            if prev_block and current_paragraph:
                # 1. Physical Layout Checks
                v_gap = block.bbox.y0 - prev_block.bbox.y1
                x_diff = abs(block.bbox.x0 - prev_block.bbox.x0)
                
                is_large_gap = v_gap > 0.04          # > 4% page height
                is_huge_gap = v_gap > 0.10           # > 10% page height (definite break)
                is_col_change = x_diff > 0.10        # > 10% page width
                
                # 2. Structure/Type Check
                # Ignore trivial type changes (e.g. Text -> Section-header) if sentence continues
                start_structure_element = False
                
                # 3. Linguistic Check (Sentence Continuity)
                prev_text = current_paragraph[-1].strip()
                # Check if previous line ends with sentence terminator
                ends_sentence = prev_text.endswith(('.', '!', '?', ':')) or prev_text.endswith(('."', '!"', '?"'))
                ends_hyphen = prev_text.endswith('-')
                
                # Check for Uppercase Header (force break)
                is_uppercase_header = False
                if content.text:
                    text_strip = content.text.strip()
                    # Heuristic: Uppercase, not too short (avoid "A"), not too long, looks like header
                    # Allow 20% tolerance for OCR noise (e.g. "TiTLE")
                    upper_chars = sum(1 for c in text_strip if c.isupper())
                    total_alpha = sum(1 for c in text_strip if c.isalpha())
                    
                    if total_alpha > 0 and (upper_chars / total_alpha) > 0.8:
                        if len(text_strip) > 3 and len(text_strip) < 150:
                            is_uppercase_header = True

                # --- DECISION LOGIC ---
                if is_col_change:
                    should_break = True
                elif is_huge_gap:
                    should_break = True
                elif is_uppercase_header:
                    should_break = True
                elif ends_hyphen:
                    should_break = False  # Always merge hyphenated lines
                elif not ends_sentence:
                    # Sentence definitely continues (no punctuation)
                    # Force merge unless gap is suspicious
                    if is_large_gap:
                        should_break = True # Gap too big for mid-sentence
                    else:
                        should_break = False # Merge!
                else:
                    # Sentence ended. 
                    # Break if gap is visible OR structure changes
                    if is_large_gap:
                        should_break = True
                    elif block.block_type != prev_block.block_type:
                        should_break = True
            
            if content.text:
                # Check block type for special handling
                block_classification = self._classify_text_block(block, content.text)
                
                # Handle structural elements (title, section, etc.)
                if block_classification in ["title", "section", "subsection", "list-item"]:
                    # Flush current paragraph
                    if current_paragraph:
                        merged.append({
                            'type': 'paragraph',
                            'text': ' '.join(current_paragraph)
                        })
                        current_paragraph = []
                    
                    # Add structured element
                    # Normalize text for headers too
                    clean_text = " ".join(content.text.split())
                    merged.append({
                        'type': block_classification,
                        'text': clean_text,
                        'metadata': {
                            'raw_label': block.raw_label,
                            'font_size': block.font_size,
                            'is_bold': block.is_bold
                        }
                    })
                    prev_block = block
                else:
                    # Regular text - break paragraph if needed
                    if should_break and current_paragraph:
                        merged.append({
                            'type': 'paragraph',
                            'text': ' '.join(current_paragraph)
                        })
                        current_paragraph = []
                    
                    # Accumulate text for paragraph
                    # Normalize whitespace to prevent accidental line breaks
                    clean_text = " ".join(content.text.split())
                    current_paragraph.append(clean_text)
                    prev_block = block
            
            elif content.latex:
                pending_tag = None
                
                # Flush paragraph before math
                if current_paragraph:
                    # Check if paragraph is just a tag (Leading Tag)
                    joined_text = ' '.join(current_paragraph).strip()
                    m_tag = eq_num_pattern.match(joined_text)
                    if m_tag:
                         # It is a tag! capture it for THIS math block
                         pending_tag = m_tag.group(1).replace(" ", "")
                         current_paragraph = [] # Consumed
                    else:
                        merged.append({
                            'type': 'paragraph',
                            'text': ' '.join(current_paragraph)
                        })
                        current_paragraph = []
                
                # Distinguish between math and table
                block_type = 'table' if block.block_type == 'table' else 'math'
                
                final_latex = content.latex
                if pending_tag and block_type == 'math':
                    final_latex += f" \\tag{{{pending_tag}}}"
                
                # TABLE-MATH MERGE LOGIC (Heuristic)
                # If we just added a table, and this is a math block
                if block_type == 'math' and merged and merged[-1]['type'] == 'table':
                    last_table = merged[-1]
                    # Check vertical proximity
                    # Assuming we don't have bounding box of previous merged item easily available?
                    # But we have `prev_block`
                    v_gap = block.bbox.y0 - prev_block.bbox.y1
                    
                    # Logic 1: Very close vertical gap (e.g. < 2% page height)
                    is_very_close = v_gap < 0.02
                    
                    if is_very_close:
                        pass

                merged.append({
                    'type': block_type,
                    'latex': final_latex
                })
                prev_block = block
            
            elif content.image_path:
                # Flush paragraph before image
                if current_paragraph:
                    merged.append({
                        'type': 'paragraph',
                        'text': ' '.join(current_paragraph)
                    })
                    current_paragraph = []
                
                merged.append({
                    'type': 'image',
                    'image_path': content.image_path
                })
        
        # Flush remaining paragraph
        if current_paragraph:
            merged.append({
                'type': 'paragraph',
                'text': ' '.join(current_paragraph)
            })
        
        return merged
    
    def _refine_semantics(self, items: List[Dict], page_num: int) -> List[Dict]:
        """
        Refine types based on text content (Semantic Parsing).
        Converts generic 'paragraph' or 'table' to 'abstract', 'proof', etc.
        """
        
        refined_items = []
        
        # Regex Patterns
        abstract_pattern = re.compile(r'^(Abstract|Tóm tắt)(\s*[:.])?', re.IGNORECASE)
        theorem_pattern = re.compile(r'^(Định lý|Theorem|Lemma|Bổ đề|Tính chất|Hệ quả)\b', re.IGNORECASE)
        # Refined Proof Pattern: Handles formatting chars like *, \, { and \textit{...}
        proof_pattern = re.compile(r'^(\\textit\{|\\textbf\{|[\*\\\{])*(Chứng minh|Proof|Lời giải)[\*\}\.]*(\s*[:.])?$', re.IGNORECASE)
        proof_start_pattern = re.compile(r'^(\\textit\{|\\textbf\{|[\*\\\{])*(Chứng minh|Proof|Lời giải)[\*\}\.]*(\s*[:.])', re.IGNORECASE)
        toc_line_pattern = re.compile(r'(\.\s*){4,}|…{3,}')
        
        # New Patterns for Phase 2.7
        explicit_section_pattern = re.compile(r'^(PHẦN|PHỤ LỤC|CHƯƠNG|SECTION|APPENDIX)\s+([A-Z0-9\.]+)', re.IGNORECASE)
        paragraph_header_pattern = re.compile(r'^([^\.]+?):') # "Note:", "Ghi chú:" pattern

        for i, item in enumerate(items):
            text = item.get('text', '').strip()
            
            # Skip empty
            if not text and not item.get('latex') and not item.get('image_path'):
                continue
            
            # 0. Strip leading Latex formatting for detection (heuristic)
            clean_text_for_check = re.sub(r'\\[a-zA-Z]+\{', '', text).replace('}', '')

            # 1. Abstract Detection
            if page_num == 1 and abstract_pattern.match(text):
                 item['type'] = 'abstract'
            
            # --- Phase 2.7: Explicit Structural Markers (High Priority) ---
            
            # 1b. Explicit Section Keywords (Phụ lục, Phần...)
            # These override standard paragraph detection
            if explicit_section_pattern.match(text):
                 item['type'] = 'section'

            # 1c. Paragraph Headers (Bold/Short start with colon)
            # Checks for "Something short:" at the start
            if item['type'] == 'paragraph':
                 m = paragraph_header_pattern.match(text)
                 if m:
                     header = m.group(1)
                     # Heuristic: Header must be short (< 5 words) and remaining text exists
                     if len(header.split()) < 6 and len(text) > len(header) + 2:
                         # We can't change 'type' to paragraph_header directly supported by LaTeX easily 
                         # unless we use \paragraph{Header} text.
                         # Instead, let's inject valid latex \paragraph.
                         # But wait, self._escape_latex is called later on item['text'].
                         # If we assume item is processed, we can try to mark it.
                         # OR we define a new type 'paragraph-with-header'.
                         # Simpler: just bold it manually here if we can't change type logic.
                         # BUT better: Make it a 'section' type? No, \paragraph is distinct.
                         # Let's use 'raw_latex' to control output perfectly.
                         # Reconstruct text: \paragraph{Header} Rest
                         escaped_header = self._escape_latex(header)
                         escaped_rest = self._escape_latex(text[len(header)+1:].strip())
                         # Use raw_latex
                         item['type'] = 'raw_latex'
                         item['latex'] = f"\\paragraph{{{escaped_header}:}} {escaped_rest}"
                         item['text'] = None # Suppress text output

            # 2. Theorem/Lemma Detection
            # Look for "Theorem 1.1" or "Định lý [ABC]"
            # Use clean text to avoid Latex noise
            if theorem_pattern.match(clean_text_for_check):
                 # Check length - Theorems are usually > 10 chars
                 if len(clean_text_for_check) > 10:
                     item['type'] = 'theorem'

            # 3. Proof Detection
            if proof_start_pattern.match(text) or proof_pattern.match(text):
                 item['type'] = 'proof'
                 
            # 4. TOC Fix (Table False Positive)
            # If it's a "table" but contains lots of dots "......" -> likely TOC or index
            if item['type'] == 'table':
                 # Check if latex source contains dots
                 table_content = item.get('latex', '') or item.get('text', '')
                 if toc_line_pattern.search(table_content):
                      # It's a TOC or similar list.
                      item['type'] = 'raw_latex' # Use raw latex injection
                      
                      if item.get('latex'):
                          # Convert Table to formatted list using \dotfill
                          raw = item['latex']
                          # Strip environments
                          raw = re.sub(r'\\begin\{tabular\}.*?(\n|$)', '', raw)
                          raw = raw.replace(r'\end{tabular}', '')
                          raw = raw.replace(r'\begin{center}', '').replace(r'\end{center}', '')
                          raw = re.sub(r'\\hline', '', raw)
                          
                          # Convert & to \dotfill
                          # Typical TOC row: "Section Name & ... & Page \\"
                          lines = []
                          for line in raw.split(r'\\'):
                              if not line.strip(): continue
                              # Replace splitters
                              parts = line.split('&')
                              if len(parts) > 1:
                                  # Name \dotfill Page
                                  clean_line = f"{parts[0].strip()} \\dotfill {parts[-1].strip()}"
                                  lines.append(clean_line)
                              else:
                                  lines.append(line.strip())
                          
                          item['latex'] = "\n\n".join(lines)
                      
                      elif item.get('text'):
                          # Fallback for missing latex
                          clean_text = item['text']
                          # Try to guess structure? Just return text as is for now
                          item['type'] = 'paragraph' # Fallback
            
            # 5. Uppercase Section Inference (Rule: Short, Uppercase, >3 words)
            if item['type'] == 'paragraph' and len(text) < 100:
                # Check if it looks like a math equation -> Skip promotion
                is_math = any(op in text for op in ['=', '<', '>', '≤', '≥', '∫', '∑'])
                
                if not is_math:
                    words = text.split()
                    if len(words) >= 3:
                         # Check if mostly uppercase (exclude small numbers or symbols)
                         # Allow up to 1 non-uppercase word (like "and")
                         upper_count = sum(1 for w in words if w.isupper() or not w.isalpha())
                         if upper_count >= len(words) - 1:
                             # It is likely a Section Header
                             item['type'] = 'section'

            # Phase 3: Smart Section Splitting (Also applies to paragraphs that LOOK like sections but ran long)
            # If a Section is too long (> 20 words) OR a paragraph starts with a Section Pattern
            should_check_splitting = False
            
            # Vietnamese Uppercase Charset
            VN_UPPER = "A-ZÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬĐÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝỲỶỸỴ"
            
            if item['type'] == 'section':
                should_check_splitting = True
            elif item['type'] == 'paragraph' and len(text) > 100:
                # Check if it STARTS with Uppercase Header?
                # Pattern: "UPPERCASE HEADER Text continues..."
                # Handle Vietnamese chars
                pattern = fr'^([{VN_UPPER}\s\(\)0-9\.]{{5,50}}?)\s+([A-ZÁ-Ỹ][a-zá-ỹ].*)'
                m_start_upper = re.match(pattern, clean_text_for_check, re.DOTALL)
                if m_start_upper and len(m_start_upper.group(1).split()) > 2:
                    # Potential Section Candidate! Promote check
                    should_check_splitting = True

            if should_check_splitting:
                words = text.split()
                if len(words) > 20: 
                    # Attempt to split Header from Body
                    header_txt = None
                    body_txt = None

                    # Heuristic 1: Split by first newline (if OCR preserved line breaks in block)
                    if '\n' in text:
                        parts = text.split('\n', 1)
                        possible_header = parts[0].strip()
                        # Use simple upper check (won't work perfectly for VN but decent proxy)
                        # or check against VN_UPPER regex
                        if len(possible_header.split()) < 20 and re.match(fr'^[{VN_UPPER}\s0-9\.]+$', possible_header):
                             header_txt = possible_header
                             body_txt = parts[1].strip()
                    
                    if not header_txt:
                        # Heuristic 2: Split by first sentence ending or colon
                        # Match: "HEADER: Body text..." or "HEADER. Body text..."
                        # Look for punctuation followed by space
                        # Only accept if PRE-punctuation part is UPPERCASE or Bold-like
                        m = re.match(r'^(.{5,50}?)(:|.)\s+(.*)', text, re.DOTALL)
                        if m:
                            candidate_header = m.group(1) + m.group(2)
                            # Check if candidate is "Section-like" (Uppercase)
                            if re.match(fr'^[{VN_UPPER}\s0-9\.\:]+$', candidate_header) or explicit_section_pattern.match(candidate_header):
                                header_txt = candidate_header
                                body_txt = m.group(3)
                        
                        if not header_txt:
                             # Heuristic 3: Transition from Upper to Mixed case
                             # "SECTION HEADER This is body"
                             pattern = fr'^([{VN_UPPER}\s\(\)0-9\.]{{5,50}}?)\s+([A-ZÁ-Ỹ][a-zá-ỹ].*)'
                             m_upper = re.match(pattern, text, re.DOTALL)
 
                             if m_upper:
                                 h_cand = m_upper.group(1).strip()
                                 if len(h_cand.split()) < 15 and len(h_cand) > 5:
                                     header_txt = h_cand
                                     body_txt = m_upper.group(2).strip()
                    
                    if header_txt and body_txt:
                        # Update current item to be just Header and FORCE type to section
                        item['type'] = 'section'
                        item['text'] = header_txt
                        refined_items.append(item)
                        
                        # Add new Paragraph item for Body
                        refined_items.append({
                            'type': 'paragraph', 
                            'text': body_txt,
                            'latex': None,
                            'image_path': None
                        })
                        continue # Skip appending original 'item'

            refined_items.append(item)
            
        return refined_items

    def _classify_text_block(self, block: LayoutBlock, text: str) -> str:
        """
        Classify text block based on structure metadata.
        
        Combines:
        1. Surya's raw_label (Title, Section-header, etc.)
        2. Font size estimation
        3. Text length + position heuristics
        
        Returns:
            One of: "title", "section", "subsection", "list-item", "text"
        """
        # CRITICAL: Prioritize Surya labels FIRST (most reliable)
        # But verify with text content check (avoid classifying lowercase text as section)
        text_start = text.strip()
        is_lowercase_start = text_start and text_start[0].islower()
        
        if block.raw_label:
            label = block.raw_label
            if label == "Title":
                return "title"
            elif label == "Section-header":
                 # Downgrade to text if it starts with lower case (misclassification)
                if is_lowercase_start:
                    return "text"
                return "section"
            elif label == "List-item":
                return "list-item"
            # If Text or other, continue to heuristics
        
        # Don't classify math content as sections
        if '$' in text or '\\[' in text or '\\(' in text:
            return "text"
            
        # Don't classify lowercase starting lines as sections (continuation of prev line)
        if is_lowercase_start:
            return "text"
            
        # Regex-based Section Detection (Suggestion Feature)
        # Matches: 1. Title, 1.1 Subtitle, A. Part A, I. Roman
        import re
        section_pattern = r'^(\d+(\.\d+)*|[IVX]+\.|[A-Z]\.)\s+[A-ZÀ-Ỹ]'
        if re.match(section_pattern, text_start) and len(text_start) < 80:
            # EXCEPTION: Date detection (Year start)
            # Avoids "2026 February..." being Section 2026
            if re.match(r'^(19|20)\d{2}', text_start):
                 return "text"

            # Count dots to determine level for numeric sections
            if re.match(r'^\d', text_start):
                 dot_count = text_start.split(' ')[0].count('.')
                 if dot_count > 1:
                     return "subsection"
            return "section"
        
        text_len = len(text.strip())
        
        # Very strict section detection:
        # Must be SHORT (<80 chars) AND in upper page
        if text_len < 80 and block.bbox.y0 < 0.3:
            # Check font size if available  
            if block.font_size:
                # Strong indicators: bold + large font
                if block.is_bold and block.font_size > 16:
                    return "title"
                elif block.is_bold and block.font_size > 13:
                    return "section"
                # Font size alone (without bold) - must be very large
                elif block.font_size > 20:
                    return "title"
                elif block.font_size > 17:
                    return "section"
            
            # Position-based fallback: ONLY for very top + short text + NO font data
            # This should rarely trigger if font analyzer is working
            if not block.font_size:
                if block.bbox.y0 < 0.05 and text_len < 40:
                    return "title"
                elif text_len < 30 and block.bbox.y0 < 0.10:
                    return "section"
        
        # Phase 2.6: Title Heuristic Fallback
        # If text is at the very top of Page 1 and looks substantial, assume it's Title
        if block.page_num == 0 and block.bbox.y0 < 0.15 and text_len > 20 and text_len < 200:
             # If Surya didn't already label it
             if block.raw_label not in ["Figure", "Table", "Page-header"]:
                  # Check if it's the largest/boldest block seen so far? (Hard in stateless)
                  # Just check if it's centered or bold? 
                  if block.is_bold:
                      return "title"
                  # Or simply if it's the first block?
                  if block.bbox.y0 < 0.1: # Very top
                      return "title"

        # Check for list patterns
        text_start = text.strip()[:3]
        if text_start.startswith(("• ", "- ", "* ", "1.", "a.", "i.")):
            return "list-item"
        
        # Default: everything else is body text
        return "text"
    
    def _escape_latex(self, text: str) -> str:
        """Escape special LaTeX characters, preserving math content"""
        import re
        
        # Phase 2.6: HTML Tag Cleanup
        # <sup...>...</sup> -> \textsuperscript{...}
        # We perform this REPLACEMENT before splitting logic so it stays as part of "text"
        # BUT we must treat \textsuperscript as a command to NOT escape?
        # Actually easier to use the _process_rich_text logic OR placeholders.
        
        # Strategy: Replace <sup> with unique alphanumeric placeholders that survive escape
        # Using XYZ prefix to avoid collision with real text
        text = re.sub(r'<sup\b[^>]*>(.*?)</sup>', r'XYZSUPSTART\1XYZSUPEND', text, flags=re.IGNORECASE)
        text = re.sub(r'<sub\b[^>]*>(.*?)</sub>', r'XYZSUBSTART\1XYZSUBEND', text, flags=re.IGNORECASE)
        text = text.replace('&nbsp;', ' ')
        
        # Fix common Vietnamese encoding issues
        text = self._fix_vietnamese_encoding(text)
        
        # Pattern to match <math> tags OR $...$ delimiters
        # Note: We use a non-greedy match for $...$ to avoid spanning multiple formulas
        # We also handle escaped \$ to allow money symbols, but for now simplify.
        math_pattern = r'(<math(?:\s+display="(?:block|inline)")?>.+?</math>|\$.+?\$|\\\(.+?\\\))'
        
        # Find all math sections (split text by these patterns)
        parts = re.split(math_pattern, text, flags=re.DOTALL)
        
        result = []
        for part in parts:
            if not part: continue
            
            # Check if this part is a math block
            if part.startswith('<math') or part.startswith('$') or part.startswith(r'\('):
                 # It's math, don't escape content (except normalizing delimiters)
                 if part.startswith('<math'):
                     match = re.search(r'>((?:.|\n)+?)</math>', part)
                     if match:
                         content = match.group(1)
                         is_display = 'display="block"' in part
                     else:
                         # Malformed math tag, treat as text
                         content = part
                         is_display = False
                 elif part.startswith('$'):
                     content = part.strip('$')
                     is_display = False # Assume inline for single $
                 else:
                     content = part[2:-2]
                     is_display = False
                 
                 # Clean math
                 # Don't clean_math for inline simple variables to avoid heavy regex on small things?
                 # content = self._clean_math(content) 
                 
                 if is_display:
                     result.append(f"\n\\[ {content} \\]\n")
                 else:
                     result.append(f"${content}$")
            else:
                 # It's text, process rich text and escape
                 result.append(self._process_rich_text(part))
        
        final_text = "".join(result)
        
        # Restore structural placeholders
        final_text = final_text.replace("[[ITEM]]", "\n\\item ")
        
        # Restore HTML superscript/subscript placeholders
        final_text = final_text.replace("XYZSUPSTART", "\\textsuperscript{").replace("XYZSUPEND", "}")
        final_text = final_text.replace("XYZSUBSTART", "\\textsubscript{").replace("XYZSUBEND", "}")
        
        return final_text

    def _process_rich_text(self, text: str) -> str:
        """Handle HTML-like tags in text (<b>, <i>) and escape the rest"""
        import re
        
        # Remove any stray <math> tags that weren't caught (e.g. malformed or inside text)
        text = re.sub(r'</?math.*?>', '', text)
        
        # Split by bold and italic tags
        # Note: This is a simple parser, doesn't handle nesting perfectly but works for OCR output
        parts = re.split(r'(<b>.*?</b>|<i>.*?</i>)', text, flags=re.DOTALL)
        
        result = []
        for part in parts:
            if part.startswith('<b>') and part.endswith('</b>'):
                content = part[3:-4]
                result.append(r'\textbf{' + self._escape_simple(content) + '}')
            elif part.startswith('<i>') and part.endswith('</i>'):
                content = part[3:-4]
                result.append(r'\textit{' + self._escape_simple(content) + '}')
            else:
                result.append(self._escape_simple(part))
                
        return "".join(result)
    
    def _fix_vietnamese_encoding(self, text: str) -> str:
        """Fix common Vietnamese encoding issues and OCR formatting errors"""
        import re
        
        # 1. Fix escaped characters that should be Unicode
        replacements = {
            r"n\\'eu": "nếu",
            r"\\'": "'",
        }
        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text)

        # 2. Fix common OCR Hallucinations & Broken Vietnamese (Fuzzy replacements)
        # Use regex boundary \b where appropriate
        ocr_fixes = {
            # Characters
            r"\bNhửn diửn\b": "Nhận diện",
            r"\bkứ hứu\b": "ký hiệu",
            r"\bký h iệu\b": "ký hiệu",
            r"toận": "toán",
            r"thuộng": "thường",
            r"Phân biửt": "Phân biệt",
            r"chử": "chữ",
            
            # Phase 3: Enhanced Dictionary Mapping
            r"h\.t\.d": "h.t.đ",
            r"v'oi": "với",
            r"vòi": "với",
            r"khì": "khi",
            r"tại": "tại", # Prevent "t?i"
            r"\bva\b": "và",
            r"công thúc": "công thức",
            r"đinh lý": "định lý",
            r"già sử": "giả sử",
            r"mênh đề": "mệnh đề",
            r"hàm sô": "hàm số",
            r"Phuong trình": "Phương trình",
            r"nghiêm": "nghiệm",
            r"tôn tại": "tồn tại",
            r"khong gian": "không gian",
            
            # Common OCR Errors
            r"vửét": "viết",
            r"đirợc": "được",
            r"dược": "được",
            r"cùa": "của",
            r"với": "với",
            
            # Common Math-context words
            r"\bma trân\b": "ma trận",
            r"\bĐinh nghĩa\b": "Định nghĩa",
            r"\bDjnh nghia\b": "Định nghĩa",
            r"\bDinh ly\b": "Định lý",
            r"\bBô dề\b": "Bổ đề",
            r"\bHê quả\b": "Hệ quả",
            
            # Specific Math Fixes (Group Theory)
            # Fix italic 'g' recognized as 'q' in Texify
            r"q\s*\\in\s*G": r"g \\in G",
            r"q\s*h\s*q\^{-1}": r"g h g^{-1}",
            r"qhq\^{-1}": r"ghg^{-1}",
            
            # Missing Integrals (Gauss Theorem context)
            r"=_{\\partial V}": r"= \\oiint_{\\partial V}",
            r"=_{\\partial S}": r"= \\oint_{\\partial S}",
            
            # Broken formatting
            r"•": "[[ITEM]]",  # Convert bullet points to placeholder
                             # (Will be restored to \item after escaping)
        }
        
        for pattern, replacement in ocr_fixes.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        return text
    
    def _clean_math(self, math: str) -> str:
        """Clean up math LaTeX for better formatting"""
        import re
        
        # Add space in differentials: dx → d x
        math = re.sub(r'\bd([xyz])\b', r'd \1', math)
        
        # Use \to instead of \rightarrow for consistency with Mathpix style
        # (Actually both are fine, but keep our current \to)
        
        return math.strip()
    
    def _escape_simple(self, text: str) -> str:
        """Escape basic LaTeX special characters"""
        replacements = {
            "\\": "\\textbackslash{}",
            "&": "\\&",
            "%": "\\%",
            "$": "\\$",
            "#": "\\#",
            "_": "\\_",
            "{": "\\{",
            "}": "\\}",
            "~": "\\textasciitilde{}",
            "^": "\\textasciicircum{}",
            "<": "\\textless{}",
            ">": "\\textgreater{}",
        }
        
        for char, replacement in replacements.items():
            text = text.replace(char, replacement)
        
        return text


def build_tex_document(
    contents_per_page: List[List[ExtractedContent]],
    blocks_per_page: List[List[LayoutBlock]],
    output_dir: Path,
    document_info: Optional[Dict] = None,
    verbose: bool = True,
) -> Path:
    """
    Convenience function to build a LaTeX document.
    
    Args:
        contents_per_page: Extracted content for each page
        blocks_per_page: Layout blocks for each page
        output_dir: Directory to save output files
        document_info: Optional document metadata
        verbose: Print progress messages
        
    Returns:
        Path to main.tex file
    """
    builder = TeXBuilder(output_dir, verbose=verbose)
    return builder.build_document(contents_per_page, blocks_per_page, document_info)
