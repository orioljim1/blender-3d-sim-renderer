from img_collection_creator import collect_images
from img_automatic_cropper import process_folder

if __name__ == "__main__":


    input_folder = "path/to/your/input/folder"
    out_gallery = input_folder + "path/to/your/output/folder"
    out_gallery_cropped = input_folder + "path/to/your/output/folder/cropped"
    
    collect_images(input_folder, out_gallery)
    process_folder(out_gallery, out_gallery_cropped)