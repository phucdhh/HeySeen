import requests
import xml.etree.ElementTree as ET
import tarfile
import zipfile
import os
import shutil
from pathlib import Path

def download_tex_files(num_files=100):
    base_url = "http://export.arxiv.org/api/query"
    params = {
        'search_query': 'cat:math*',
        'start': 0,
        'max_results': num_files,
        'sortBy': 'submittedDate',
        'sortOrder': 'descending'
    }
    
    response = requests.get(base_url, params=params)
    if response.status_code != 200:
        print("Failed to query arXiv API")
        return
    
    root = ET.fromstring(response.content)
    ns = {'atom': 'http://www.w3.org/2005/Atom'}
    
    entries = root.findall('atom:entry', ns)
    tex_dir = Path('/Users/m2pro/HeySeen/internet_data_test/tex_original')
    
    for entry in entries:
        id_elem = entry.find('atom:id', ns)
        if id_elem is None:
            continue
        arxiv_id = id_elem.text.split('/')[-1].split('v')[0]  # e.g., 2602.10103
        
        source_url = f"https://arxiv.org/e-print/{arxiv_id}"
        print(f"Downloading {source_url}")
        
        try:
            source_response = requests.get(source_url)
            if source_response.status_code != 200:
                print(f"Failed to download {source_url}")
                continue
            
            # Save the tar.gz
            temp_file = tex_dir / f"{arxiv_id}.tar.gz"
            with open(temp_file, 'wb') as f:
                f.write(source_response.content)
            
            # Extract
            extract_dir = tex_dir / f"temp_{arxiv_id}"
            extract_dir.mkdir(exist_ok=True)
            
            try:
                with tarfile.open(temp_file, 'r:gz') as tar:
                    tar.extractall(extract_dir)
                
                # Find main.tex or the main file
                tex_files = list(extract_dir.rglob('*.tex'))
                if tex_files:
                    main_tex = None
                    for tf in tex_files:
                        if tf.name.lower() in ['main.tex', 'paper.tex', f"{arxiv_id.split('_')[-1]}.tex"]:
                            main_tex = tf
                            break
                    if not main_tex:
                        main_tex = tex_files[0]  # take first
                    
                    # Copy to tex_original
                    shutil.copy(main_tex, tex_dir / f"{arxiv_id}.tex")
                    print(f"Saved {arxiv_id}.tex")
                else:
                    print(f"No .tex files in {arxiv_id}")
            
            except Exception as e:
                print(f"Error extracting {arxiv_id}: {e}")
            
            # Clean up
            if temp_file.exists():
                temp_file.unlink()
            if extract_dir.exists():
                shutil.rmtree(extract_dir)
        
        except Exception as e:
            print(f"Error downloading {arxiv_id}: {e}")

if __name__ == "__main__":
    download_tex_files(20)