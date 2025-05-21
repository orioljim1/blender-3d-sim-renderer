# Utilities

Collection of Python utilities for image processing and management.

## Tools Overview

### 1. Image Collection Creator (`img_collection_creator.py`)
Collects images from nested folders into a single output folder.
- Copies images to a single directory
- Prefixes filenames with parent folder names


### 2. Automatic Image Cropper (`img_automatic_cropper.py`)
Crops images to remove transparent padding, keeping only the non-transparent content.
- Finds bounding box of non-transparent pixels
- Supports optional padding around content
- Processes PNG files

### 3. Compositor (`compositor.py`)
Creates grid composites of rendered images with a colored background.
- Auto-detects render directories (numbered or _run_ format)
- Single row for 1-4 images, two balanced rows for 5+ images
- Centers and resizes images with aspect ratio preservation

### 4. Crop and Collect Runner (`crop_and_collect.py`)
Combines collection and cropping in one step.

## Usage Examples

### Collecting Images
```python
from img_collection_creator import collect_images

input_path = "path/to/input/folder"
output_path = "path/to/gallery"
collect_images(input_path, output_path)
```

### Cropping Images
```python
from img_automatic_cropper import process_folder

input_folder = "path/to/gallery"
output_folder = "path/to/cropped/gallery"
process_folder(input_folder, output_folder)
```

### Creating Composites
```python
from compositor import composite_images, process_all_folders

base_path = "path/to/base/folder"
process_all_folders(base_path, base_path + "/composites")
```

## Dependencies
Required packages are listed in `requirements.txt`:
- PIL (Python Imaging Library)
- tqdm (for progress bars)
- os (standard library)
- shutil (standard library)

## Installation
1. Ensure Python 3.x is installed
2. Install required packages using the requirements file:
    ```bash
    pip install -r requirements.txt
    ``` 