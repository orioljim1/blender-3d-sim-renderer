import bpy
import math
import os
from mathutils import Vector
import bmesh
import random
import glob

def set_origin_to_center_of_volume(obj):
    if obj is None or obj.type not in {'MESH', 'CURVE', 'SURFACE', 'META', 'FONT'}:
        print(f"Error: Invalid object or object type for origin setting.")
        return

    current_active = bpy.context.view_layer.objects.active
    current_selection = bpy.context.selected_objects.copy()

    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS', center='MEDIAN')

    bpy.context.view_layer.objects.active = current_active
    for ob in current_selection:
        ob.select_set(True)

def target_lock_object(source_obj, target_obj):
    if source_obj.type not in {'LIGHT', 'CAMERA'}:
        print(f"Error: {source_obj.name} is not a light or camera object.")
        return

    existing_constraint = next((c for c in source_obj.constraints if c.type == 'TRACK_TO'), None)
    
    if existing_constraint:
        existing_constraint.target = target_obj
    else:
        constraint = source_obj.constraints.new(type='TRACK_TO')
        constraint.target = target_obj
        constraint.track_axis = 'TRACK_NEGATIVE_Z'
        constraint.up_axis = 'UP_Y'

def remove_doubles_from_mesh(obj, threshold=0.0101):
    if obj.type != 'MESH':
        print(f"Error: Object {obj.name} is not a mesh object.")
        return

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=threshold)
    bm.to_mesh(obj.data)
    obj.data.update()
    bm.free()


def rotate_object(obj, rotations):
    """
    Rotate object according to given rotations (x, y, z) in radians
    """
    obj.rotation_mode = 'XYZ'
    obj.rotation_euler = rotations

def import_glb(file_path):
    try:
        bpy.ops.import_scene.gltf(filepath=file_path)
        imported_objects = bpy.context.selected_objects
        if not imported_objects:
            print(f"Error: No objects were imported from {file_path}")
            return None
        return imported_objects[0]
    except Exception as e:
        print(f"Error importing GLB file: {e}")
        return None

def get_second_lowest_vertex(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    
    sorted_verts = sorted(bm.verts, key=lambda v: (obj.matrix_world @ v.co).z)
    
    if len(sorted_verts) > 1:
        second_lowest = sorted_verts[1]
        second_lowest_world = obj.matrix_world @ second_lowest.co
    else:
        second_lowest_world = None
    
    bm.free()
    return second_lowest_world


def move_obj_z_to_zero(obj):
    bpy.context.scene.cursor.location =  get_second_lowest_vertex(obj)
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')
    obj.location.z = 0    
    bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS', center='MEDIAN')
    obj.location.x = 0  
    obj.location.y = 0

def setup_object(glb_path, config):
    obj = import_glb(glb_path)
    bpy.ops.object.mode_set(mode='OBJECT')
    
    move_obj_z_to_zero(obj)

    if obj is None:
        print("Error: Failed to import GLB file. Exiting.")
        return
    
    # Apply mesh optimizations if enabled
    if config['optimize_mesh']:
        print(f"Optimizing mesh with threshold {config['remove_doubles_threshold']}")
        remove_doubles_from_mesh(obj, threshold=config['remove_doubles_threshold'])
    
    obj.name = "Render_object"
    
    return obj

def render_view(output_path, angle, config):
    bpy.context.scene.render.engine = config['render_engine']
    
    if config['gpu_acceleration']:
        bpy.context.preferences.addons['cycles'].preferences.compute_device_type = config['compute_device']
        bpy.context.scene.cycles.device = 'GPU'
    
    # Set render resolution
    bpy.context.scene.render.resolution_x = config['resolution_x']
    bpy.context.scene.render.resolution_y = config['resolution_y']
    bpy.context.scene.render.resolution_percentage = config['resolution_percentage']
    
    # Set render quality for Cycles
    if config['render_engine'] == 'CYCLES':
        bpy.context.scene.cycles.samples = config['samples']
    
    bpy.context.scene.render.filepath = output_path
    bpy.context.scene.render.image_settings.file_format = config['file_format']
    bpy.context.scene.render.film_transparent = config['transparent_background']
    
    bpy.ops.render.render(write_still=True)

def render_step(output_dir, obj, config):
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Render multiple views with rotating object
    rotation_increments = config['rotation_increments']
    
    for angle in range(0, 360, rotation_increments):
        
        rotate_object(obj, (0, 0, math.radians(angle)))
        
        output_path = os.path.join(output_dir, f"render_{angle}.png")
        render_view(output_path, angle, config)

def setup_scene(obj_path, config):
    # Set render engine and GPU acceleration
    bpy.context.scene.render.engine = config['render_engine']
    if config['gpu_acceleration']:
        bpy.context.preferences.addons['cycles'].preferences.compute_device_type = config['compute_device']
        bpy.context.scene.cycles.device = 'GPU'

    # Configure compositor nodes for post-processing
    bpy.context.scene.use_nodes = True
    tree = bpy.context.scene.node_tree
    
    for node in tree.nodes:
        tree.nodes.remove(node)
    
    render_layers = tree.nodes.new('CompositorNodeRLayers')
    contrast = tree.nodes.new('CompositorNodeColorCorrection')
    output = tree.nodes.new('CompositorNodeComposite')
    
    contrast.master_contrast = config['contrast']
    contrast.master_saturation = config['saturation']
    
    tree.links.new(render_layers.outputs['Image'], contrast.inputs['Image'])
    tree.links.new(contrast.outputs['Image'], output.inputs['Image'])

    # Clear existing objects
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    # Setup camera
    camera_loc = config['camera_location']
    camera_rot = config['camera_rotation']
    bpy.ops.object.camera_add(location=camera_loc, rotation=camera_rot)
    camera = bpy.context.active_object
    bpy.context.scene.camera = camera

    # Setup light
    light_loc = config['light_location']
    bpy.ops.object.light_add(type=config['light_type'], location=light_loc)
    light = bpy.context.active_object
    light.data.type = config['light_type']
    
    if config['light_type'] == 'SUN':
        light.data.energy = config['light_energy']
    
    # Setup shadow catcher
    shadow_catcher = setup_shadow_catcher(
        location=config['shadow_catcher_location'], 
        size=config['shadow_catcher_size'], 
        shadow_opacity=config['shadow_opacity']
    )

    # Import and setup the 3D object
    obj = setup_object(obj_path, config)
    set_origin_to_center_of_volume(obj)
    
    # Apply target tracking
    if config['track_object']:
        target_lock_object(light, obj)
        target_lock_object(camera, obj)
    
    # Optionally fit camera to object
    if config['auto_frame_object']:
        fit_camera_to_object(camera, obj, target_coverage=config['frame_coverage'])

    return camera, light, shadow_catcher, obj

def set_random_color(obj):
    """
    Sets random colors for all materials of an object
    Returns list of random colors used for each material
    """
    if not obj.data.materials:
        print(f"Error: Object {obj.name} has no materials to modify")
        return None
    
    random_colors = []
    
    # Iterate through all materials
    for material in obj.data.materials:
        if not material:
            continue
            
        if not material.use_nodes:
            material.use_nodes = True
        
        nodes = material.node_tree.nodes
        links = material.node_tree.links
        
        # Clear existing mix nodes to prevent duplicates
        for node in nodes:
            if node.type == 'MIX_RGB':
                nodes.remove(node)
        
        principled = next((node for node in nodes if node.type == 'BSDF_PRINCIPLED'), None)
        if not principled:
            continue
        
        mix_node = nodes.new('ShaderNodeMixRGB')
        mix_node.blend_type = 'HUE'
        mix_node.inputs[0].default_value = 1.0
        
        random_color = (random.random(), random.random(), random.random(), 1.0)
        mix_node.inputs[2].default_value = random_color
        random_colors.append(random_color)
        
        base_color_input = principled.inputs['Base Color']
        if base_color_input.links:
            original_link = base_color_input.links[0]
            original_node = original_link.from_node
            links.new(original_node.outputs[0], mix_node.inputs[1])
        else:
            mix_node.inputs[1].default_value = (1, 1, 1, 1)
        
        links.new(mix_node.outputs[0], base_color_input)
    
    return random_colors

def move_to_zero(obj):
    
    bpy.ops.object.transform_apply(rotation=True)
    bpy.context.scene.cursor.location = get_second_lowest_vertex(obj)
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')
    obj.location.z = 0    
    bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS', center='MEDIAN')
    obj.location.x = 0  
    obj.location.y = 0   

def rotate_and_setup(obj, rot_radiants):
    
    rotate_object(obj, rot_radiants)
    bpy.ops.object.transform_apply(rotation=True)
    bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS', center='MEDIAN')
    move_to_zero(obj)   

def setup_shadow_catcher(location=(0, 0, 0), size=20, shadow_opacity=0.5):
    """
    Creates and sets up a shadow catcher plane with adjustable shadow opacity
    Args:
        location: (x,y,z) coordinates for the plane
        size: size of the plane
        shadow_opacity: opacity of shadows (0.0 to 1.0)
    """
    bpy.ops.mesh.primitive_plane_add(size=size, enter_editmode=False, location=location)
    shadow_catcher = bpy.context.active_object
    shadow_catcher.name = "ShadowCatcher"
    shadow_catcher.is_shadow_catcher = True
    shadow_catcher.hide_render = False
    shadow_catcher.hide_viewport = False
    
    material = shadow_catcher.data.materials.get("Shadow_Catcher_Material")
    if not material:
        material = bpy.data.materials.new(name="Shadow_Catcher_Material")
        shadow_catcher.data.materials.append(material)
    
    material.use_nodes = True
    nodes = material.node_tree.nodes
    
    nodes["Principled BSDF"].inputs[4].default_value = shadow_opacity
    
    return shadow_catcher

def fit_camera_to_object(camera, obj, target_coverage=0.7):
    cam_data = camera.data
    aspect_ratio = bpy.context.scene.render.resolution_x / bpy.context.scene.render.resolution_y
    
    if cam_data.sensor_fit == 'VERTICAL':
        fov = cam_data.angle
    else:
        fov = 2 * math.atan(math.tan(cam_data.angle / 2) * aspect_ratio)
    
    world_bbox_corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    
    cam_mat = camera.matrix_world
    cam_loc = cam_mat.translation
    
    cam_dir = Vector(cam_mat.col[2][:3])
    cam_dir.negate()
    cam_dir.normalize()
    
    max_distance = 0
    min_x = min_y = float('inf')
    max_x = max_y = float('-inf')
    
    for corner in world_bbox_corners:
        corner_cam_space = camera.matrix_world.inverted() @ corner
        x, y, z = corner_cam_space
        
        if z < 0:
            min_x = min(min_x, x)
            max_x = max(max_x, x)
            min_y = min(min_y, y)
            max_y = max(max_y, y)
            
            if x != 0:
                dist_x = abs((x * cam_data.clip_start) / (math.tan(fov / 2)))
            else:
                dist_x = 0
                
            if y != 0:
                dist_y = abs((y * cam_data.clip_start) / (math.tan(cam_data.angle / 2)))
            else:
                dist_y = 0
                
            required_dist = max(dist_x, dist_y)
            max_distance = max(max_distance, required_dist)
    
    object_width = max_x - min_x
    object_height = max_y - min_y
    
    view_width = 2 * math.tan(fov / 2) * max_distance
    view_height = 2 * math.tan(cam_data.angle / 2) * max_distance
    
    current_coverage = max(object_width / view_width, object_height / view_height)
    
    scale_factor = current_coverage / target_coverage
    max_distance /= scale_factor
    
    camera.location = cam_loc + (cam_dir * max_distance)
    
    bpy.context.view_layer.update()

def main(seed=None, asset="obj_path", output_dir='DATA/renders', config=None):
    # Set default configuration if not provided
    if config is None:
        config = {
            # Render settings
            'render_engine': 'CYCLES',
            'gpu_acceleration': True,
            'compute_device': 'CUDA',
            'samples': 128,
            'resolution_x': 1920,
            'resolution_y': 1080,
            'resolution_percentage': 100,
            'file_format': 'PNG',
            'transparent_background': True,
            
            # Post-processing
            'contrast': 1.05,
            'saturation': 1.3,
            
            # Camera settings
            'camera_location': (0, -2.6, 0.5),
            'camera_rotation': (math.pi/2, 0, 0),
            'track_object': True,
            'auto_frame_object': False,
            'frame_coverage': 0.7,
            
            # Light settings
            'light_type': 'SUN',
            'light_location': (-3, 0, 2),
            'light_energy': 1.0,
            
            # Shadow catcher
            'shadow_catcher_location': (0, 0, 0),
            'shadow_catcher_size': 20,
            'shadow_opacity': 0.7,
            
            # Mesh optimization
            'optimize_mesh': False,
            'remove_doubles_threshold': 0.01,
            
            # Material settings
            'random_colors': False,
            
            # Rotation settings
            'rotation_increments': 60,
            'rotations': [(0,0,0), (90,0,0), (-90,0,0), (0,90,0)]
        }
    
    if seed is not None:
        random.seed(seed)
    
    if asset is not None:
        asset_name = os.path.basename(asset)
        asset_name = os.path.splitext(asset_name)[0]
        output_dir = os.path.join(output_dir, f"{asset_name}")
    
    camera, light, shadow_catcher, obj = setup_scene(asset, config)
    
    # Apply random colors if enabled
    if config['random_colors']:
        colors = set_random_color(obj)
        if colors:
            print(f"Applied random colors to {len(colors)} materials")
    
    rotations = config['rotations']
    
    for i, rot_degrees in enumerate(rotations):
        rotation_radians = tuple(math.radians(x) for x in rot_degrees)
        rotate_and_setup(obj, rotation_radians)
        
        output_folder = os.path.join(output_dir, str(i))
        
        render_step(output_folder, obj, config)
        
        # Reset object rotation
        rotation_radians = tuple(math.radians(-x) for x in rot_degrees)
        rotate_object(obj, rotation_radians)
        bpy.ops.object.transform_apply(rotation=True)
        bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS', center='MEDIAN')
                
    print(f"Rendering complete for {asset_name}!")

if __name__ == "__main__":
    # Configuration dictionary for customizing all rendering parameters
    config = {
        # Processing mode
        'mode': 'directory',  # 'single' or 'directory'
        
        # Input/Output paths
        'single_model_path': "path/to/your/model.glb",
        'models_directory': "path/to/models/folder",
        'output_directory': "path/to/output/folder",
        
        # Render settings
        'render_engine': 'CYCLES',  # 'CYCLES' or 'EEVEE'
        'gpu_acceleration': True,
        'compute_device': 'CUDA',  # 'CUDA', 'OPTIX', or 'OPENCL'
        'samples': 128,  # Higher values = better quality but slower
        'resolution_x': 1920,
        'resolution_y': 1080,
        'resolution_percentage': 100,
        'file_format': 'PNG',  # 'PNG', 'JPEG', 'TIFF', etc.
        'transparent_background': True,
        
        # Post-processing
        'contrast': 1.05,  # Values > 1 increase contrast
        'saturation': 1.3,  # Values > 1 increase saturation
        
        # Camera settings
        'camera_location': (0, -2.6, 0.5),  # (x, y, z)
        'camera_rotation': (math.pi/2, 0, 0),  # (x, y, z) in radians
        'track_object': True,  # Whether camera should track the object
        'auto_frame_object': False,  # Enable to automatically frame the object
        'frame_coverage': 0.7,  # How much of the frame the object should fill (0.0 to 1.0)
        
        # Light settings
        'light_type': 'SUN',  # 'SUN', 'POINT', 'SPOT', 'AREA'
        'light_location': (-3, 0, 2),  # (x, y, z)
        'light_energy': 1.0,  # Light strength
        
        # Shadow catcher
        'shadow_catcher_location': (0, 0, 0),  # (x, y, z)
        'shadow_catcher_size': 20,  # Size of the shadow catcher plane
        'shadow_opacity': 0.7,  # Shadow opacity (0.0 to 1.0)
        
        # Mesh optimization
        'optimize_mesh': False,  # Enable mesh optimization by removing duplicate vertices
        'remove_doubles_threshold': 0.01,  # Distance threshold for considering vertices as duplicates
        
        # Material settings
        'random_colors': False,  # Set to True to apply random colors to materials
        
        # Rotation settings
        'rotation_increments': 60,  # Angle increments for each rotation step (in degrees)
        'rotations': [  # Base rotations for different orientations (in degrees)
            (0, 0, 0),      # Default orientation
            (90, 0, 0),     # X-axis rotation
            (-90, 0, 0),    # Negative X-axis rotation
            (0, 90, 0),     # Y-axis rotation
            # Add or remove rotations as needed
        ]
    }
    
    # Use the configuration
    if config['mode'] == 'single':
        main(
            seed=None, 
            asset=config['single_model_path'], 
            output_dir=config['output_directory'],
            config=config
        )
    
    elif config['mode'] == 'directory':    
        # Get all .glb files recursively
        glb_files = glob.glob(os.path.join(config['models_directory'], "**/*.glb"), recursive=True)
        
        total_files = len(glb_files)
        for i, obj_path in enumerate(glb_files, 1):
            print(f"Processing {i}/{total_files}: {os.path.basename(obj_path)}")
            main(
                seed=None, 
                asset=obj_path, 
                output_dir=config['output_directory'],
                config=config
            )
            print(f"Completed {i}/{total_files} files")
    
    else:
        print("Invalid mode. Please set 'mode' to either 'single' or 'directory'.")