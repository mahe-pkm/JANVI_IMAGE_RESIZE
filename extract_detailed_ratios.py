import os
import csv
import math
from pathlib import Path
from PIL import Image

SOURCE_DIR = Path(r"c:\Users\rough\Desktop\Logo Processing\May-20261\Resizing")
TARGET_W, TARGET_H = 1200, 1800
TARGET_RATIO = TARGET_W / TARGET_H  # 0.6666666666666666 (2:3)

def get_simplified_ratio(w, h):
    # Determine the closest standard aspect ratios for grouping
    ratio_val = w / h
    if abs(ratio_val - (2/3)) < 0.01:
        return "2:3"
    elif abs(ratio_val - (9/16)) < 0.01:
        return "9:16"
    elif abs(ratio_val - (3/4)) < 0.01:
        return "3:4"
    elif abs(ratio_val - (1/1)) < 0.01:
        return "1:1"
    
    gcd = math.gcd(w, h)
    return f"{w//gcd}:{h//gcd}"

def main():
    if not SOURCE_DIR.exists():
        print(f"Error: {SOURCE_DIR} does not exist.")
        return
        
    image_paths_set = set()
    for ext in ['*.png', '*.jpg', '*.jpeg']:
        image_paths_set.update(SOURCE_DIR.rglob(ext))
        image_paths_set.update(SOURCE_DIR.rglob(ext.upper()))
    image_paths = list(image_paths_set)
        
    total_images = len(image_paths)
    print(f"Found {total_images} source images under {SOURCE_DIR}.")
    
    seen_filenames = {}
    details = []
    skipped_duplicates = []
    
    for img_path in sorted(image_paths, key=lambda p: p.name.lower()):
        filename = img_path.name
        rel_path = img_path.relative_to(SOURCE_DIR)
        
        if filename in seen_filenames:
            skipped_duplicates.append((filename, str(rel_path), seen_filenames[filename]))
            continue
            
        seen_filenames[filename] = str(rel_path)
        try:
            folder_name = rel_path.parts[0] if len(rel_path.parts) > 1 else "Root"
            
            with Image.open(img_path) as img:
                w, h = img.size
                source_ratio = w / h
                
                # Difference percentage compared to 2:3 target (0.6667)
                diff_pct = ((source_ratio - TARGET_RATIO) / TARGET_RATIO) * 100
                abs_diff_pct = abs(diff_pct)
                
                simple_ratio = get_simplified_ratio(w, h)
                
                # Classify the action
                if abs_diff_pct < 0.1:
                    action = "Direct Scale (Exact 2:3)"
                elif diff_pct > 0:
                    action = f"Crop Width (+{diff_pct:.2f}% wider)"
                else:
                    action = f"Blur Pad Height (-{abs_diff_pct:.2f}% taller)"
                    
                details.append({
                    "Filename": filename,
                    "RelativePath": str(rel_path),
                    "Folder": folder_name,
                    "Width": w,
                    "Height": h,
                    "Resolution": f"{w}x{h}",
                    "SourceRatio": f"{source_ratio:.4f}",
                    "SimplifiedRatio": simple_ratio,
                    "DifferencePercentage": f"{diff_pct:+.2f}%" if abs_diff_pct >= 0.01 else "0.00%",
                    "Action": action,
                    "diff_pct_val": diff_pct
                })
        except Exception as e:
            print(f"Error reading {img_path}: {e}")
            
    if skipped_duplicates:
        print(f"\nSkipped {len(skipped_duplicates)} duplicate filenames:")
        for filename, dupe_path, original_path in skipped_duplicates:
            print(f" - {filename}: {dupe_path} (original: {original_path})")
            
    # Write to CSV
    csv_path = SOURCE_DIR.parent / "source_images_detailed_ratios.csv"
    fields = ["Filename", "RelativePath", "Folder", "Width", "Height", "Resolution", "SourceRatio", "SimplifiedRatio", "DifferencePercentage", "Action"]
    
    with open(csv_path, mode="w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fields)
        writer.writeheader()
        for row in details:
            # Filter the dict to only write expected fields
            row_to_write = {k: row[k] for k in fields}
            writer.writerow(row_to_write)
            
    print(f"CSV written to: {csv_path}")
    
    # Write to Markdown
    md_path = SOURCE_DIR.parent / "source_images_detailed_ratios.md"
    with open(md_path, "w", encoding="utf-8") as md_file:
        md_file.write("# Source Images Detailed Aspect Ratio & Difference Report\n\n")
        md_file.write(f"- **Total source images scanned:** {total_images}\n")
        md_file.write(f"- **Unique source images processed:** {len(details)}\n")
        md_file.write(f"- **Duplicate filenames skipped:** {len(skipped_duplicates)}\n")
        md_file.write(f"- **Target standard:** `1200x1800` (Aspect Ratio: **2:3** / `0.6667`)\n")
        md_file.write(f"- **CSV Export:** [source_images_detailed_ratios.csv](file:///{csv_path.as_posix()})\n\n")
        
        if skipped_duplicates:
            md_file.write("## ⚠️ Skipped Duplicate Filenames\n\n")
            md_file.write("The following files had duplicate names and were excluded from processing to avoid name collisions:\n\n")
            md_file.write("| Filename | Excluded Path | Processed (Original) Path |\n")
            md_file.write("| :--- | :--- | :--- |\n")
            for filename, dupe_path, original_path in skipped_duplicates:
                md_file.write(f"| `{filename}` | `{dupe_path}` | `{original_path}` |\n")
            md_file.write("\n")
            
        md_file.write("## Folder Summary\n\n")
        # Summarize by folder
        folders = sorted(list(set(row["Folder"] for row in details)))
        md_file.write("| Folder | Image Count | Avg Ratio Difference (Abs) |\n")
        md_file.write("| :--- | :---: | :---: |\n")
        for folder in folders:
            folder_rows = [r for r in details if r["Folder"] == folder]
            avg_diff = sum(abs(r["diff_pct_val"]) for r in folder_rows) / len(folder_rows) if folder_rows else 0
            md_file.write(f"| `{folder}` | {len(folder_rows)} | {avg_diff:.2f}% |\n")
            
        md_file.write("\n## Complete Image Inventory\n\n")
        md_file.write("| Filename | Folder | Resolution | Source Ratio | Target Ratio | Difference % | Suggested Action |\n")
        md_file.write("| :--- | :--- | :---: | :---: | :---: | :---: | :--- |\n")
        for row in details:
            md_file.write(
                f"| `{row['Filename']}` | `{row['Folder']}` | `{row['Resolution']}` | `{row['SourceRatio']}` | `0.6667` | **{row['DifferencePercentage']}** | {row['Action']} |\n"
            )
            
    print(f"Markdown report written to: {md_path}")

if __name__ == '__main__':
    main()
