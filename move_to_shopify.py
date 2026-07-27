import os
import re
import shutil
import sys
from pathlib import Path

# Common patterns to strip from folder names to get the product name
SUFFIX_REGEX = re.compile(
    r'_(selected_images|selected_image|selected|images_resized|images|resized)(\s*\(\d+\))?$',
    re.IGNORECASE
)

def clean_product_name(folder_name: str) -> str:
    """
    Returns the folder name directly as the product name.
    """
    return folder_name.strip()

def get_export_folders(src_dir) -> list:
    """
    Scans for all unique parent directories containing images under the source root.
    """
    src_path = Path(src_dir)
    if not src_path.exists():
        return []
    extensions = ('*.png', '*.jpg', '*.jpeg', '*.gif', '*.webp', '*.PNG', '*.JPG', '*.JPEG', '*.GIF', '*.WEBP')
    all_files = []
    for ext in extensions:
        all_files.extend(list(src_path.rglob(ext)))
    
    unique_folders = sorted(list(set(f.parent for f in all_files)), key=lambda p: str(p).lower())
    return unique_folders

def get_product_name_for_folder(export_folder: Path, src_dir: Path) -> str:
    """
    Determines the clean product name for a given export folder.
    If the export folder is named 'Untitled Export' (or similar), its parent folder is the product.
    Otherwise, the folder itself is the product.
    """
    name_lower = export_folder.name.lower()
    is_export_subfolder = (name_lower == "untitled export" or "export" in name_lower or "untitled" in name_lower)
    
    if is_export_subfolder:
        product_folder = export_folder.parent
    else:
        product_folder = export_folder
        
    folder_name = product_folder.name
    
    # Fallback if folder name is empty (e.g. root of a drive or relative path resolution error)
    if not folder_name or folder_name.lower() in ('', '.', '..') or len(folder_name) <= 1:
        folder_name = export_folder.name
        
    product_name = clean_product_name(folder_name)
    
    if not product_name:
        product_name = "Product"
        
    return product_name

def run_export(src_dir: str, dest_dir: str, dry_run: bool = True, delete_empty_src: bool = True, log_callback=print):
    """
    Executes the reconstructed Shopify export flow:
    1. Scan recursively for all image files.
    2. Group files by parent folder.
    3. Identify if the group is inside an export subfolder or directly in a product folder.
    4. Copy/Rename files flatly to dest_dir with counter indices.
    5. Avoid filename conflicts.
    6. Delete original files and empty export folders.
    """
    src_path = Path(src_dir)
    dest_path = Path(dest_dir)
    
    log_callback(f"Starting export run.")
    log_callback(f"Source Root: {src_path}")
    log_callback(f"Destination: {dest_path}")
    log_callback(f"Dry Run: {dry_run}")
    
    if not src_path.exists():
        log_callback(f"Error: Source directory {src_path} does not exist.")
        return 0
        
    if not dry_run:
        dest_path.mkdir(parents=True, exist_ok=True)
        
    # Scan for all image files recursively under the source directory
    extensions = ('*.png', '*.jpg', '*.jpeg', '*.gif', '*.webp', '*.PNG', '*.JPG', '*.JPEG', '*.GIF', '*.WEBP')
    all_files = []
    for ext in extensions:
        all_files.extend(list(src_path.rglob(ext)))
        
    # Deduplicate file matches
    all_files = sorted(list(set(all_files)), key=lambda f: str(f).lower())
    log_callback(f"Found {len(all_files)} total image files under source root.")
    
    if not all_files:
        log_callback("No images found to process.")
        return 0
        
    # Group files by their containing folder
    groups = {}
    for file in all_files:
        parent = file.parent
        groups.setdefault(parent, []).append(file)
        
    log_callback(f"Grouped into {len(groups)} folders containing images.")
    
    files_copied = 0
    folders_cleaned = 0
    
    for export_folder, files in sorted(groups.items(), key=lambda x: str(x[0]).lower()):
        # Determine the clean product name for this group
        product_name = get_product_name_for_folder(export_folder, src_path)
        
        log_callback(f"Processing folder '{export_folder.name}' -> Product name: '{product_name}' ({len(files)} files)")
        
        for idx, file in enumerate(files, start=1):
            ext = file.suffix.lower()
            
            # Generate unique filename in the destination directory
            counter = idx
            dest_file = dest_path / f"{product_name}_{counter}{ext}"
            
            # If the file already exists, increment the counter to avoid overwriting
            while dest_file.exists():
                counter += 1
                dest_file = dest_path / f"{product_name}_{counter}{ext}"
                
            log_callback(f"  {'[DRY RUN] Would copy' if dry_run else 'Copying'}:")
            log_callback(f"    From: {file.relative_to(src_path)}")
            log_callback(f"    To:   {dest_file.name}")
            
            if not dry_run:
                try:
                    shutil.copy2(file, dest_file)
                    files_copied += 1
                except Exception as e:
                    log_callback(f"  Error copying {file.name}: {e}")
                    
        # Clean up source files and export folders if requested
        if not dry_run and delete_empty_src:
            for file in files:
                try:
                    file.unlink()
                except Exception as e:
                    log_callback(f"  Error deleting original file {file.name}: {e}")
            
            # Delete the export folder only if it is an export subfolder
            name_lower = export_folder.name.lower()
            is_export_subfolder = (name_lower == "untitled export" or "export" in name_lower or "untitled" in name_lower)
            
            if is_export_subfolder:
                try:
                    export_folder.rmdir()
                    log_callback(f"  Removed empty export folder: {export_folder.relative_to(src_path)}")
                    folders_cleaned += 1
                except Exception as e:
                    log_callback(f"  Could not remove export folder: {e}")
                    
        log_callback("-" * 50)
        
    log_callback(f"Export finished. Total files copied: {files_copied}. Folders cleaned: {folders_cleaned}")
    return files_copied

def main():
    # Local CLI entry point for manual testing
    src = str(Path(r"c:\Users\rough\Desktop\Logo Processing\May-20261\Re-sized\With Logo"))
    dest = str(Path(r"c:\Users\rough\Desktop\Logo Processing\May-20261\Re-sized\Final For Shopify"))
    
    execute = "--execute" in sys.argv
    no_delete = "--no-delete" in sys.argv
    
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    if len(args) >= 1:
        src = args[0]
    if len(args) >= 2:
        dest = args[1]
        
    run_export(
        src_dir=src,
        dest_dir=dest,
        dry_run=not execute,
        delete_empty_src=not no_delete,
        log_callback=print
    )

if __name__ == "__main__":
    main()
