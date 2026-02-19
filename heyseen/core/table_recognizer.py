"""
Table Recognizer Module

Uses Microsoft's Table Transformer (TATR) to detect table structure 
and reconstructs LaTeX tables using HeySeen's OCR for cell content.
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional, Callable, Dict
import torch
from PIL import Image
import numpy as np
import logging

from .model_manager import ModelManager

logger = logging.getLogger(__name__)

@dataclass
class TableCell:
    """A cell in a detected table"""
    bbox: List[float] # [x0, y0, x1, y1] original image coordinates
    row_idx: int = -1
    col_idx: int = -1
    row_span: int = 1
    col_span: int = 1
    content: str = ""
    is_header: bool = False

class TableRecognizer:
    def __init__(self, device: str = "mps", manager: Optional[ModelManager] = None):
        if manager is None:
            manager = ModelManager.get_instance(device)
            
        self.device = device
        self.model, self.processor = manager.get_table_model()
        
        if not self.model:
            logger.warning("Table Transformer model not available.")

    def process_table(self, image: Image.Image, ocr_callback: Callable[[Image.Image], str]) -> str:
        """
        Process a table image Crop -> LaTeX code.
        
        Args:
            image: PIL Image of the table region
            ocr_callback: Function that takes an image crop and returns text content
            
        Returns:
            LaTeX tabular code, or "" if not a valid table.
        """
        if not self.model:
            return "% Table recognition unavailable (Model failed to load)\n"
        
        # 1. Structure Recognition (now returns list of tables)
        tables_cells = self._detect_tables(image)
        if not tables_cells:
            return "" 
            
        logger.info(f"TATR: Detected {len(tables_cells)} distinct tables.")
        
        latex_outputs = []
        
        for idx, cells in enumerate(tables_cells):
            logger.info(f"TATR: Processing Table {idx+1} ({len(cells)} cells)...")
            
            # 2. OCR Content for each cell
            cells_with_content = []
            for i, cell in enumerate(cells):
                # Crop cell
                # bbox is [x0, y0, x1, y1]
                crop_box = (
                    max(0, int(cell.bbox[0])),
                    max(0, int(cell.bbox[1])),
                    min(image.width, int(cell.bbox[2])),
                    min(image.height, int(cell.bbox[3]))
                )
                
                # Avoid invalid crops
                if crop_box[2] <= crop_box[0] or crop_box[3] <= crop_box[1]:
                    continue
                
                # Pad crop significantly to capture edges
                pad = 12
                # Ensure we don't pad outside image
                padded_box = (
                    max(0, crop_box[0] - pad),
                    max(0, crop_box[1] - pad),
                    min(image.width, crop_box[2] + pad),
                    min(image.height, crop_box[3] + pad)
                )
                
                cell_img = image.crop(padded_box)
                # Run OCR
                cell.content = ocr_callback(cell_img).strip()
                cells_with_content.append(cell)
            
            # 3. Post-OCR Validation
            if self._is_false_positive_table(cells_with_content):
                logger.info(f"TATR: Rejected Table {idx+1} based on content heuristics.")
                continue

            # 4. Generate LaTeX
            latex_outputs.append(self._build_latex(cells_with_content))

        return "\n\n".join(latex_outputs)
        
    def _detect_tables(self, image: Image.Image) -> List[List[TableCell]]:
        """
        Run TATR inference and parse results into List of Tables.
        Includes logic to handle merged cells (spanning rows/cols) and Header semantics.
        """
        # Ensure RGB for model compatibility
        if image.mode != "RGB":
            image = image.convert("RGB")
            
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            
        target_sizes = torch.tensor([image.size[::-1]])
        
        # Threshold: 0.5 is standard. Use a lower threshold for spanning cells?
        results = self.processor.post_process_object_detection(outputs, threshold=0.1, target_sizes=target_sizes)[0]
        
        scores = results["scores"]
        labels = results["labels"]
        boxes = results["boxes"]
        
        # 1. Collect Objects
        table_boxes = []
        rows = []
        cols = []
        spanning_cells = [] # Stores [bbox, label_name, score]
        header_rows = [] # Stores y-coordinates or bboxes of header rows
        
        for score, label, box in zip(scores, labels, boxes):
            if score < 0.5: continue # Skip low confidence standard objects

            box = box.tolist()
            lbl = label.item()
            label_name = self.model.config.id2label[lbl]
            
            if label_name == "table":
                table_boxes.append(box)
            elif label_name == "table row":
                rows.append(box)
            elif label_name == "table row header":
                rows.append(box)
                header_rows.append(box)
            elif label_name == "table column":
                cols.append(box)
            elif label_name == "table spanning cell":
                # Spanning cells might have lower confidence, but let's trust > 0.5
                spanning_cells.append(box)
                
        # Sort objects
        rows.sort(key=lambda b: (b[1] + b[3])/2)
        cols.sort(key=lambda b: (b[0] + b[2])/2)
        table_boxes.sort(key=lambda b: b[1])
        
        # 2. Define Table Regions (Cluster fallback)
        if not table_boxes and rows:
             rows.sort(key=lambda b: (b[1] + b[3])/2)
             clusters = []
             if rows:
                 current_cluster = [rows[0]]
                 for i in range(1, len(rows)):
                     prev = rows[i-1]
                     curr = rows[i]
                     gap = curr[1] - prev[3]
                     if gap > 1.5 * (prev[3] - prev[1]) or gap > 50: 
                         clusters.append(current_cluster)
                         current_cluster = [curr]
                     else:
                         current_cluster.append(curr)
                 clusters.append(current_cluster)
             
             for cluster in clusters:
                 y0 = min(r[1] for r in cluster)
                 y1 = max(r[3] for r in cluster)
                 table_boxes.append([0, max(0, y0 - 10), image.width, min(image.height, y1 + 10)])
                 
        if not table_boxes:
            # Last resort
            if rows and cols:
                table_boxes = [[0, 0, image.width, image.height]]
            else:
                 return []
            
        # 3. Process each table region
        all_tables_cells = []
        
        for t_idx, t_box in enumerate(table_boxes):
            # Clip container
            t_box = [max(0, t_box[0]), max(0, t_box[1]), min(image.width, t_box[2]), min(image.height, t_box[3])]

            # Filter rows/cols that belong to this table
            t_rows = [r for r in rows if self._is_contained(r, t_box)]
            t_cols = [c for c in cols if self._is_contained(c, t_box)]
            
            # Filter spanning cells for this table
            t_spans = [s for s in spanning_cells if self._is_contained(s, t_box)]
            
            if not t_rows or not t_cols:
                continue
                
            # Re-sort for this table
            t_rows.sort(key=lambda b: (b[1] + b[3])/2)
            t_cols.sort(key=lambda b: (b[0] + b[2])/2)
            
            # --- STRUCTURE RECONSTRUCTION V2 (Soft Grid + Spans) ---
            
            cells = []
            
            # Identify Header Indices
            header_row_indices = set()
            for r_idx, r_box in enumerate(t_rows):
                # check if this row box is in header_rows list
                for hb in header_rows:
                    if self._is_same_box(r_box, hb):
                        header_row_indices.add(r_idx)
                        break

            # Create Base Grid Map (Row-Col Intersections)
            # key: (r_idx, c_idx) -> bbox
            grid_map = {}
            for r_idx, r_box in enumerate(t_rows):
                for c_idx, c_box in enumerate(t_cols):
                    x0 = max(c_box[0], r_box[0])
                    y0 = max(c_box[1], r_box[1])
                    x1 = min(c_box[2], r_box[2])
                    y1 = min(c_box[3], r_box[3])
                    
                    if x1 > x0 and y1 > y0:
                        grid_map[(r_idx, c_idx)] = [x0, y0, x1, y1]
            
            # Generate Final Cells taking Spans into account
            # We track which grid cells have been "consumed" by a spanning cell
            consumed_grid_cells = set() # Set of (r, c)
            
            final_cells = []
            
            # 1. Process Spanning Cells First (High Priority)
            for span_box in t_spans:
                # Find which rows/cols this span covers
                covered_rows = []
                for r_idx, r_box in enumerate(t_rows):
                    if self._overlap_y(span_box, r_box) > 0.5: # 50% vertical overlap
                        covered_rows.append(r_idx)
                
                covered_cols = []
                for c_idx, c_box in enumerate(t_cols):
                    if self._overlap_x(span_box, c_box) > 0.5: # 50% horizontal overlap
                        covered_cols.append(c_idx)
                
                if not covered_rows or not covered_cols:
                    continue
                    
                r_start = min(covered_rows)
                r_end = max(covered_rows)
                c_start = min(covered_cols)
                c_end = max(covered_cols)
                
                # Create the Merged Cell
                # Bbox should be Union of covered grid cells to be precise, 
                # or just the detected span_box. Let's use strict grid union for alignment.
                # Find union bbox
                u_x0, u_y0, u_x1, u_y1 = span_box # Default
                
                # Check grid alignment
                valid_grid = False
                gx0, gy0, gx1, gy1 = 10000, 10000, 0, 0
                
                for r in range(r_start, r_end + 1):
                    for c in range(c_start, c_end + 1):
                        if (r, c) in grid_map:
                            valid_grid = True
                            gb = grid_map[(r, c)]
                            gx0 = min(gx0, gb[0])
                            gy0 = min(gy0, gb[1])
                            gx1 = max(gx1, gb[2])
                            gy1 = max(gy1, gb[3])
                            
                        consumed_grid_cells.add((r, c))
                
                if valid_grid:
                     # Use grid-snapped bbox for better OCR alignment
                     final_bbox = [gx0, gy0, gx1, gy1]
                else:
                     final_bbox = span_box
                     
                final_cells.append(TableCell(
                    bbox=final_bbox,
                    row_idx=r_start,
                    col_idx=c_start,
                    row_span=(r_end - r_start + 1),
                    col_span=(c_end - c_start + 1),
                    is_header=(r_start in header_row_indices)
                ))

            # 2. Fill gaps with standard grid cells
            for r_idx in range(len(t_rows)):
                for c_idx in range(len(t_cols)):
                    if (r_idx, c_idx) in consumed_grid_cells:
                        continue
                    
                    if (r_idx, c_idx) in grid_map:
                        bbox = grid_map[(r_idx, c_idx)]
                        final_cells.append(TableCell(
                            bbox=bbox,
                            row_idx=r_idx,
                            col_idx=c_idx,
                            row_span=1,
                            col_span=1,
                            is_header=(r_idx in header_row_indices)
                        ))
            
            if final_cells:
                # Sort cells by reading order (row then col)
                final_cells.sort(key=lambda c: (c.row_idx, c.col_idx))
                all_tables_cells.append(final_cells)

        return all_tables_cells

    def _is_same_box(self, b1, b2, thr=2.0):
        return abs(b1[0]-b2[0]) < thr and abs(b1[1]-b2[1]) < thr and abs(b1[2]-b2[2]) < thr and abs(b1[3]-b2[3]) < thr

    def _overlap_y(self, box1, box2):
        # Vertical overlap ratio relative to smaller box
        y0 = max(box1[1], box2[1])
        y1 = min(box1[3], box2[3])
        if y1 <= y0: return 0.0
        h1 = box1[3] - box1[1]
        h2 = box2[3] - box2[1]
        return (y1 - y0) / min(h1, h2)

    def _overlap_x(self, box1, box2):
        # Horizontal overlap ratio
        x0 = max(box1[0], box2[0])
        x1 = min(box1[2], box2[2])
        if x1 <= x0: return 0.0
        w1 = box1[2] - box1[0]
        w2 = box2[2] - box2[0]
        return (x1 - x0) / min(w1, w2)

    def _is_false_positive_table(self, cells: List[TableCell]) -> bool:
        """
        Check if the detected table is likely just a text paragraph.
        """
        if not cells: return True
        
        # Filter empty cells
        filled_cells = [c for c in cells if c.content]
        if not filled_cells: return True
        
        total_filled = len(filled_cells)
        
        # Heuristic 1: Lowercase start ratio
        lowercase_starts = 0
        valid_cells_count = 0
        
        for cell in filled_cells:
            text = cell.content.strip()
            
            # Skip if it looks like a LaTeX command or math
            if any(sym in text for sym in ['\\', '$', '=', '^', '_', '{', '}']):
                valid_cells_count += 1
                continue
                
            # Check first char
            clean_text = ''.join(c for c in text if c.isalpha())
            if clean_text:
                if clean_text[0].islower():
                    lowercase_starts += 1
                valid_cells_count += 1
        
        if valid_cells_count == 0:
            return False # All were math/empty, assume valid table
            
        lowercase_ratio = lowercase_starts / valid_cells_count
        
        # Threshold: Relaxed to 80% to handle descriptions in tables
        # or specific languages where lowercase is common.
        if lowercase_ratio > 0.80:
             return True
             
        # Heuristic 2: 1-Column Table Rejection
        columns_indices = set(c.col_idx for c in cells)
        rows_indices = set(c.row_idx for c in cells)
        if len(columns_indices) <= 1 and len(rows_indices) > 2:
            return True
            
        return False

    def _is_contained(self, box, container, threshold=0.5):
        """Check if box is largely inside container query"""
        # box, container: [x0, y0, x1, y1]
        x0 = max(box[0], container[0])
        y0 = max(box[1], container[1])
        x1 = min(box[2], container[2])
        y1 = min(box[3], container[3])
        
        if x1 <= x0 or y1 <= y0:
            return False
            
        intersection_area = (x1 - x0) * (y1 - y0)
        box_area = (box[2] - box[0]) * (box[3] - box[1])
        if box_area <= 0: return False
        
        return (intersection_area / box_area) > threshold

    def _clean_content(self, text: str) -> str:
        """Clean HTML tags and artifacts from OCR result"""
        if not text: return ""
        # Remove HTML tags common in some OCR outputs
        cleaned = text.replace("<b>", "").replace("</b>", "")
        cleaned = cleaned.replace("<i>", "").replace("</i>", "")
        cleaned = cleaned.replace("<u>", "").replace("</u>", "")
        # Replace breaks with space
        cleaned = cleaned.replace("<br>", " ").replace("\n", " ")
        # Fix spacing
        cleaned = " ".join(cleaned.split())
        return cleaned

    def _build_latex(self, cells: List[TableCell]) -> str:
        """Construct LaTeX tabular environment with Multirow/Multicolumn support"""
        if not cells:
            return ""
            
        max_row = max(c.row_idx for c in cells)
        max_col = max(c.col_idx + c.col_span - 1 for c in cells)
        num_cols = max_col + 1
        
        # Initialize grid with placeholders
        # We store (content, spans) or None if covered by another cell
        grid_state = [[None for _ in range(num_cols)] for _ in range(max_row + 1)]
        
        for cell in cells:
            clean_text = self._clean_content(cell.content)
            
            # Escape LaTeX special chars if not math
            # But assume callback returns valid Latex if it's math
            # We trust the callback/Cleaner to handle escaping if it's text.
            # Here we apply bold if header
            if cell.is_header and clean_text:
                 # Check if not already bold or math
                 if not clean_text.startswith("\\textbf") and "$" not in clean_text:
                     clean_text = f"\\textbf{{{clean_text}}}"

            grid_state[cell.row_idx][cell.col_idx] = {
                'text': clean_text,
                'r_span': cell.row_span,
                'c_span': cell.col_span
            }
            # Mark covered cells as Occupied
            for r in range(cell.row_idx, cell.row_idx + cell.row_span):
                for c in range(cell.col_idx, cell.col_idx + cell.col_span):
                    if r == cell.row_idx and c == cell.col_idx: continue
                    grid_state[r][c] = {'occupied': True}

        # Build Body
        tex_lines = []
        tex_lines.append("\\begin{center}")
        # Use simple |c|c|...
        col_def = "|" + "c|" * num_cols
        tex_lines.append(f"\\begin{{tabular}}{{{col_def}}}")
        tex_lines.append("\\hline")
        
        for r in range(max_row + 1):
            row_items = []
            c = 0
            while c < num_cols:
                cell_data = grid_state[r][c]
                
                if cell_data is None:
                    # Empty/Missing cell
                    row_items.append(" ")
                    c += 1
                elif 'occupied' in cell_data:
                    # Covered by a span from left or top
                    # If vertical span (multirow), we typically output empty cell in LateX
                    # If horizontal span, we skip columns
                    # Wait, for \multicolumn, we skip subsequent columns in this row
                    # For \multirow, we put empty cells in subsequent ROWS
                    
                    # Logic: 
                    # If this is occupied by a column span started in THIS row, it is skipped by the loop increment below.
                    # If occupied by a ROW span from ABOVE, we need an empty cell (or \cline logic).
                    # But if we iterate 1 by 1... 
                    # Standard Latex:
                    # \multirow{2}{*}{Text} & Col2 \\
                    #                       & Col2_Row2 \\
                    
                    # So if occupied, we check source?
                    # Simply appending empty string "" works for Multirow placeholders.
                    row_items.append(" ")
                    c += 1
                else:
                    # It is a start of a cell
                    text = cell_data['text']
                    rs = cell_data['r_span']
                    cs = cell_data['c_span']
                    
                    cell_tex = text
                    
                    # Handle Multirow (vertical merge)
                    if rs > 1:
                        cell_tex = f"\\multirow{{{rs}}}{{*}}{{{text}}}"
                    
                    # Handle Multicolumn (horizontal merge)
                    if cs > 1:
                        # Align center for merged cells generally
                        # Syntax: \multicolumn{cols}{pos}{text}
                        # If multirow is also present?
                        # \multicolumn{2}{|c|}{\multirow{2}{*}{Text}}
                        align = "c|" if c + cs - 1 == max_col else "c" # Last col needs pipe?
                        # Actually simple approach:
                        align_str = "c|" # With border
                        if c == 0: align_str = "|c|" # First col needs left border
                        
                        # Fix border logic: simplest is just "c|" and ensure global table has borders.
                        # Let's use 'c|' for all intermediates.
                        
                        # Combine Multirow inside Multicolumn
                        content = cell_tex # Contains multirow if needed
                        cell_tex = f"\\multicolumn{{{cs}}}{{c|}}{{{content}}}"
                    
                    row_items.append(cell_tex)
                    c += cs # Skip columns covered by this cell
            
            row_str = " & ".join(row_items) + " \\\\"
            tex_lines.append(row_str)
            tex_lines.append("\\hline")
            
        tex_lines.append("\\end{tabular}")
        tex_lines.append("\\end{center}")
        
        return "\n".join(tex_lines)
