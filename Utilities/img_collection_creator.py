import os
import shutil
from tqdm import tqdm

def collect_images(input_path, output_path):
    """
    Collects all images from nested folders and copies them to a single output folder,
    prefixing filenames with parent folder names.
    
    Args:
        input_path (str): Root directory containing folders with images
        output_path (str): Output directory where all images will be copied
    """
    
    os.makedirs(output_path, exist_ok=True)
    
    all_image_files = []
    for root, dirs, files in os.walk(input_path):
        image_files = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]
        if image_files:
            rel_path = os.path.relpath(root, input_path)
            path_parts = rel_path.split(os.sep)
            all_image_files.extend([(root, img_file, path_parts) for img_file in image_files])
    
    for root, img_file, path_parts in tqdm(all_image_files, desc="Copying images"):
        prefix = '_'.join(part for part in path_parts if part != '.')
        new_filename = f"{prefix}_{img_file}" if prefix else img_file
            
        src_path = os.path.join(root, img_file)
        dst_path = os.path.join(output_path, new_filename)
        
        shutil.copy2(src_path, dst_path)

if __name__ == "__main__":
    input_path = "path/to/your/input/folder"
    output_path = "path/to/your/output/folder"
    
    collect_images(input_path, output_path)

