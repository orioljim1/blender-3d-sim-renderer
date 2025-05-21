import os
from PIL import Image
import math

def is_valid_image_dir(dir_path):
    """
    Check if directory contains valid images for compositing
    """
    if not os.path.isdir(dir_path):
        return False
        
    image_files = [f for f in os.listdir(dir_path) 
                  if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))
                  and f.startswith('render_')]
    return len(image_files) > 0

def get_render_dirs(input_dir):
    """
    Get all valid render directories (both numbered and _run_ formats)
    """
    render_dirs = []
    
    # Check immediate subdirectories
    for item in os.listdir(input_dir):
        item_path = os.path.join(input_dir, item)
        
        # Check if it's a directory and contains renders
        if is_valid_image_dir(item_path):
            render_dirs.append(item_path)
            continue
            
        # Check if it's a directory that might contain render subdirectories
        if os.path.isdir(item_path):
            # Look for numbered dirs (0,1,2,3) or _run_ dirs
            for subdir in os.listdir(item_path):
                subdir_path = os.path.join(item_path, subdir)
                if (subdir.isdigit() or subdir.startswith('_run_')) and is_valid_image_dir(subdir_path):
                    render_dirs.append(subdir_path)
    
    return render_dirs

def calculate_grid_layout(num_images):
    """
    Calculate grid dimensions ensuring balanced rows
    Returns: (rows, cols, images_per_row)
    """
    if num_images <= 4:
        return 1, num_images, [num_images]
    
    # For more than 4 images, use 2 rows
    if num_images % 2 == 0:
        # Even number of images: split equally
        images_per_row = num_images // 2
        return 2, images_per_row, [images_per_row, images_per_row]
    else:
        # Odd number of images: more on top, centered bottom
        top_row = math.ceil(num_images / 2)
        bottom_row = num_images - top_row
        max_cols = max(top_row, bottom_row)
        return 2, max_cols, [top_row, bottom_row]

def composite_images(input_dir, output_dir, img_width=1920, img_height=1080, allow_overflow=True, bg_color='white'):
    """
    Creates composite images from folders containing rendered images arranged in a grid
    
    Args:
        input_dir (str): Input directory containing subdirectories with images
        output_dir (str): Output directory for composite images
        img_width (int): Width of each individual image in the grid
        img_height (int): Height of each individual image in the grid
        allow_overflow (bool): If True, images can overflow their grid cell
        bg_color (str): Background color for the composite image (default: 'white')
    """
    os.makedirs(output_dir, exist_ok=True)
    
    render_dirs = get_render_dirs(input_dir)
    
    for render_dir in render_dirs:
        # Get all render images sorted by angle
        image_files = [f for f in os.listdir(render_dir) 
                      if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))
                      and f.startswith('render_')]
        image_files.sort(key=lambda x: int(x.split('_')[1].split('.')[0]))  # Sort by angle number
        
        num_images = len(image_files)
        if num_images == 0:
            continue
            
        # Calculate balanced grid layout
        grid_rows, grid_cols, images_per_row = calculate_grid_layout(num_images)
        
        composite_width = img_width * grid_cols
        composite_height = img_height * grid_rows
        
        composite = Image.new('RGBA', (composite_width, composite_height), bg_color)
        
        image_index = 0
        for row in range(grid_rows):
            # Calculate centering offset for this row
            row_images = images_per_row[row]
            row_offset = (grid_cols - row_images) * img_width // 2
            
            for col in range(row_images):
                if image_index >= num_images:
                    break
                    
                img_file = image_files[image_index]
                img_path = os.path.join(render_dir, img_file)
                img = Image.open(img_path).convert('RGBA')
                
                # Calculate centered position for this image
                cell_x = col * img_width + row_offset + (img_width // 2)
                cell_y = row * img_height + (img_height // 2)
                
                if allow_overflow:
                    aspect = img.width / img.height
                    if aspect > 1:
                        new_width = img_width
                        new_height = int(img_width / aspect)
                    else:
                        new_height = img_height
                        new_width = int(img_height * aspect)
                else:
                    img_aspect = img.width / img.height
                    cell_aspect = img_width / img_height
                    
                    if img_aspect > cell_aspect:
                        new_width = img_width
                        new_height = int(img_width / img_aspect)
                    else:
                        new_height = img_height
                        new_width = int(img_height * img_aspect)
                
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                paste_x = cell_x - (img.width // 2)
                paste_y = cell_y - (img.height // 2)
                
                composite.paste(img, (paste_x, paste_y), img)
                image_index += 1
        
        # Generate output filename based on directory structure
        dir_name = os.path.basename(render_dir)
        parent_dir = os.path.basename(os.path.dirname(render_dir))
        
        if dir_name.isdigit():  # For renderer_hard.py structure
            output_name = f"{parent_dir}_rotation_{dir_name}_composite.png"
        elif dir_name.startswith('_run_'):  # For renderer_soft.py structure
            output_name = f"{parent_dir}_{dir_name}_composite.png"
        else:
            output_name = f"{dir_name}_composite.png"
            
        output_path = os.path.join(output_dir, output_name)
        composite = composite.convert('RGB')
        composite.save(output_path)
        print(f"Created composite for {output_name}")

def process_all_folders(base_path, output_dir=None, bg_color='white'):
    """
    Processes all folders in base_path, creating composites for each
    Args:
        base_path: Root directory containing folders to process
        output_dir: Optional custom output directory, if None uses base_path/composites
        bg_color: Background color for the composite images (default: 'white')
    """
    if output_dir is None:
        output_dir = os.path.join(base_path, "composites")
    
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Processing renders in {base_path}")
    try:
        composite_images(
            input_dir=base_path,
            output_dir=output_dir,
            img_width=1920,
            img_height=1080,
            bg_color=bg_color
        )
        print(f"Completed composites in {output_dir}")
    except Exception as e:
        print(f"Error processing renders: {str(e)}")

if __name__ == "__main__":
    # Example usage
    base_path = "path/to/your/input/folder"
    process_all_folders(base_path, base_path + "/composites", bg_color='white')