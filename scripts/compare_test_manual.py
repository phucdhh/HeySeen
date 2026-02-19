
import re
import sys
from pathlib import Path
from difflib import SequenceMatcher

def read_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading {path}: {e}")
        return ""

def extract_math_blocks(content):
    """
    Extract display math blocks: \[...\], $$...$$, \begin{equation}...\end{equation}, \begin{align}...\end{align}, \begin{cases}, \begin{pmatrix}
    Note: Standard regexes might miss nested environments if not careful.
    """
    formulas = []
    
    # Pattern 1: \[ ... \]
    p1 = re.compile(r'\\\[(.*?)\\\]', re.DOTALL)
    formulas.extend(p1.findall(content))
    
    # Pattern 2: $$ ... $$
    p2 = re.compile(r'\$\$(.*?)\$\$', re.DOTALL)
    formulas.extend(p2.findall(content))
    
    # Pattern 3: environments
    envs = ['equation', 'align', 'align*', 'gather', 'gather*', 'multline', 'multline*']
    for env in envs:
        p3 = re.compile(r'\\begin\{' + re.escape(env) + r'\}(.*?)\\end\{' + re.escape(env) + r'\}', re.DOTALL)
        formulas.extend(p3.findall(content))
        
    return formulas

def normalize(latex):
    """Normalize latex string for comparison"""
    # Remove whitespace
    s = "".join(latex.split())
    
    # Common replacements
    replacements = [
        (r'\left(', '('), (r'\right)', ')'),
        (r'\left[', '['), (r'\right]', ']'),
        (r'\left\{', '{'), (r'\right\}', '}'),
        (r'\left|', '|'), (r'\right|', '|'),
        (r'\operatorname*', r'\operatorname'),
        (r'\operatorname{lim}', r'\lim'),
        (r'\to', r'\rightarrow'), # Standardize arrow
        (r'\dots', r'\ldots'), # Standardize dots
        (r'\cdots', r'\ldots'), # Standardize centered dots to ldots for comparison
        (r'^{\prime\prime}', r"''"), # Standardize double prime
        (r'^{\prime}', r"'"), # Standardize single prime
        (r'\ce', r'\mathrm'), # Treat chemical formulas as text/math
        (r'\,', ''), (r'\;', ''), (r'\:', ''), (r'\ ', ''), # Remove spacing
        (r'\text', r'\mathrm'), # Treat text as rm
        (r'\iff', r'\Longleftrightarrow'), 
        (r'\implies', r'\Longrightarrow'),
        (r'\le', r'\leq'),
        (r'\ge', r'\geq'),
        (r'dx', r'd x'), # Texify often outputs "d x"
    ]
    
    for old, new in replacements:
        s = s.replace(old, new)
        
    # Remove label/tag
    s = re.sub(r'\\label\{.*?\}', '', s)
    s = re.sub(r'\\tag\{.*?\}', '', s)
    
    return s

def compare_lists(gt_list, out_list):
    """
    Compare two lists of formulas.
    Returns (matches, missing, total_gt)
    """
    # Use simple normalization first
    gt_norm = [normalize(f) for f in gt_list]
    out_norm = [normalize(f) for f in out_list]
    
    matches = 0
    missing_indices = []
    
    used_out_indices = set()
    
    for i, gt in enumerate(gt_norm):
        found = False
        # Try exact match
        for j, out in enumerate(out_norm):
            if j in used_out_indices:
                continue
            if gt == out:
                matches += 1
                used_out_indices.add(j)
                found = True
                break
        
        # Try fuzzy match if not found
        if not found:
            best_ratio = 0
            best_idx = -1
            
            for j, out in enumerate(out_norm):
                if j in used_out_indices:
                    continue
                ratio = SequenceMatcher(None, gt, out).ratio()
                if ratio > 0.85: # High threshold for "match"
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_idx = j
            
            if best_idx != -1:
                matches += 1
                used_out_indices.add(best_idx)
                found = True
        
        if not found:
            missing_indices.append(i)
            
    return matches, missing_indices, len(gt_list)

def main():
    if len(sys.argv) < 3:
        print("Usage: python script.py <generated_tex> <original_tex>")
        return

    gen_path = Path(sys.argv[1])
    orig_path = Path(sys.argv[2])

    print(f"Comparing Math Formulas:")
    print(f"Generated: {gen_path}")
    print(f"Original : {orig_path}")
    print("-" * 40)

    gen_content = read_file(gen_path)
    orig_content = read_file(orig_path)

    gen_formulas = extract_math_blocks(gen_content)
    orig_formulas = extract_math_blocks(orig_content)

    print(f"Found {len(orig_formulas)} formulas in Original.")
    print(f"Found {len(gen_formulas)} formulas in Generated.")
    
    matches, missing, total = compare_lists(orig_formulas, gen_formulas)
    
    accuracy = (matches / total * 100) if total > 0 else 0
    print(f"Match Accuracy: {accuracy:.1f}% ({matches}/{total})")
    
    if missing:
        print("\nMissing / Mismatched Formulas (Original Indices):")
        for idx in missing:
            print(f"--- Example [{idx+1}] ---")
            print(f"GT: {orig_formulas[idx].strip()}")
            # Find closest candidate
            gt_norm = normalize(orig_formulas[idx])
            best_ratio = 0
            best_candidate = "None"
            for out in gen_formulas:
                out_norm = normalize(out)
                ratio = SequenceMatcher(None, gt_norm, out_norm).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_candidate = out
            
            if best_ratio > 0.4:
                print(f"Best Candidate (Sim={best_ratio:.2f}): {best_candidate.strip()}")
            else:
                print("No close match found.")
            print()

if __name__ == "__main__":
    main()
