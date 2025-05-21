from PIL import Image
import os
from tqdm import tqdm

def resize_image(image, canvas_width, canvas_height):
    original_width, original_height = image.size
    ratio = min(canvas_width/original_width, canvas_height/original_height)
    new_width = int(original_width * ratio)
    new_height = int(original_height * ratio)
    return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

def crop_image(image_path, output_path, padding=0):
    """
    This function crops an image to include only the non-transparent pixels, with an additional padding.
    It opens the image, converts it to RGBA format, iterates over the pixels to find the bounding box
    of non-transparent pixels, applies the specified padding, and then crops and saves the image.
    """
    with Image.open(image_path) as img:
        
        width, height = img.size
        img = resize_image(img, width, height)
        pixels = img.load()

        left, upper, right, lower = width, height, 0, 0

        for y in range(height-1):
            for x in range(width-1):
                R, G, B, alpha = pixels[x, y]

                if ((R, G, B) != (0, 0, 0) and (R, G, B) != (1, 1, 1) and alpha > 3) or alpha > 30:
                    
                    left = min(left, x)
                    upper = min(upper, y)
                    right = max(right, x)
                    lower = max(lower, y)

        #print(left, upper, right, lower)
        if left < right and upper < lower:
            left = max(left - padding, 0)
            upper = max(upper - padding, 0)
            right = min(right + padding, width)
            lower = min(lower + padding, height)
            cropped_img = img.crop((left, upper, right, lower))
            cropped_img.save(output_path)

def process_folder(input_folder, output_folder):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    png_files = [f for f in os.listdir(input_folder) if f.endswith(".png")]
    
    for filename in tqdm(png_files, desc="Processing images", unit="image"):
        input_path = os.path.join(input_folder, filename)
        output_path = os.path.join(output_folder, filename)
        crop_image(input_path, output_path)

if __name__ == "__main__":

    input_gallery = "path/to/your/input/gallery"
    out_gallery_cropped = input_gallery + "/../gallery_cropped"
    
    process_folder(out_gallery_cropped, out_gallery_cropped)

