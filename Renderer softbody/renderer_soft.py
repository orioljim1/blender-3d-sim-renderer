import bpy
import math
import os
from mathutils import Vector
import bmesh
import random
import glob

def set_origin_to_center_of_volume(obj):
    """
    Set the origin of the given object to its center of volume.
    
    :param obj: The Blender object to modify
    """
    if obj is None or obj.type not in {'MESH', 'CURVE', 'SURFACE', 'META', 'FONT'}:
        print(f"Error: Invalid object or object type for origin setting.", type='ERROR')
        return

    current_active = bpy.context.view_layer.objects.active
    current_selection = bpy.context.selected_objects.copy()

    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS', center='MEDIAN')

    print(f"Origin of {obj.name} set to center of volume")

    bpy.context.view_layer.objects.active = current_active
    for ob in current_selection:
        ob.select_set(True)


def target_lock_object(source_obj, target_obj):
    """
    Set up a target-lock constraint for a light or camera to point at a specified object.
    
    :param source_obj: The Blender light or camera object that will track the target
    :param target_obj: The Blender object to be tracked
    """
    if source_obj.type not in {'LIGHT', 'CAMERA'}:
        print(f"Error: {source_obj.name} is not a light or camera object.", type='ERROR')
        return

    existing_constraint = next((c for c in source_obj.constraints if c.type == 'TRACK_TO'), None)
    
    if existing_constraint:
        existing_constraint.target = target_obj
    else:
        constraint = source_obj.constraints.new(type='TRACK_TO')
        constraint.target = target_obj
        constraint.track_axis = 'TRACK_NEGATIVE_Z'
        constraint.up_axis = 'UP_Y'

    print(f"{source_obj.type.lower().capitalize()} {source_obj.name} is now target-locked to {target_obj.name}")
    
 
def remove_doubles_from_mesh(obj, threshold=0.0001):
    """
    Remove double vertices from the mesh of the specified object.
    
    :param obj: The Blender object whose mesh should have doubles removed
    :param threshold: The distance threshold for removing doubles
    """
    if obj.type != 'MESH':
        print(f"Error: Object {obj.name} is not a mesh object.", type='ERROR')
        return
    
    original_mode = obj.mode
    current_mode = obj.mode
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.object.mode_set(mode=current_mode)

    bm = bmesh.new()

    bm.from_mesh(obj.data)

    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=threshold)

    bm.to_mesh(obj.data)
    obj.data.update()

    bm.free()

    if original_mode != 'EDIT':
        bpy.ops.object.mode_set(mode=original_mode)

    print(f"Removed double vertices from object: {obj.name} with threshold {threshold}")

def select_boundary_vertices(obj=None):
    """
    Select all boundary vertices of the active object or specified object.
    
    :param obj: Optional - The Blender object to process. If None, uses active object.
    :return: Number of selected boundary vertices
    """
    if obj is None:
        obj = bpy.context.active_object
        
    if obj is None or obj.type != 'MESH':
        print(f"Error: Invalid object or not a mesh", type='ERROR')
        return 0

    bpy.ops.object.mode_set(mode='EDIT')
    
    bpy.ops.mesh.select_mode(type='VERT')
    
    bpy.ops.mesh.select_all(action='DESELECT')
    
    bm = bmesh.from_edit_mesh(obj.data)
    
    for v in bm.verts:
        if any(e.is_boundary for e in v.link_edges):
            v.select = True
    
    bmesh.update_edit_mesh(obj.data)
    
    selected_count = len([v for v in bm.verts if v.select])
    
    print(f"Selected {selected_count} boundary vertices on {obj.name}")
    
    return selected_count
    
def select_vertices_by_distance(obj, distance_threshold=0.1):
    """
    Select all vertices within a specified distance from currently selected vertices.
    
    :param obj: The Blender object to process
    :param distance_threshold: Maximum distance for vertex selection
    :return: Number of newly selected vertices
    """
    if obj is None or obj.type != 'MESH':
        print(f"Error: Invalid object or not a mesh", type='ERROR')
        return 0

    bpy.ops.object.mode_set(mode='EDIT')
    
    bm = bmesh.from_edit_mesh(obj.data)
    
    initially_selected = [v for v in bm.verts if v.select]
    
    if not initially_selected:
        print("No vertices currently selected")
        return 0
    
    newly_selected = set()
    for source_vert in initially_selected:
        for target_vert in bm.verts:
            if not target_vert.select:  # Skip already selected vertices
                distance = (source_vert.co - target_vert.co).length
                if distance <= distance_threshold:
                    target_vert.select = True
                    newly_selected.add(target_vert)
    
    bmesh.update_edit_mesh(obj.data)
    
    print(f"Selected {len(newly_selected)} additional vertices within {distance_threshold} distance")
    return len(newly_selected)


def merge_boundary_vertices_closeness(obj, threshold=0.003, runs = 3):

    original_mode = obj.mode
    select_boundary_vertices(obj)
    
    
    for i in range(runs):
        bpy.ops.mesh.select_more()
        select_vertices_by_distance(obj, threshold)
    
    bpy.ops.mesh.remove_doubles(threshold=threshold)

    if original_mode != 'EDIT':
        bpy.ops.object.mode_set(mode=original_mode)

def decimate_to_target_faces(obj, target_faces=20000):
    """
    Decimate object geometry to reach approximately the target number of faces
    
    :param obj: The Blender object to decimate
    :param target_faces: Target number of faces (default 20,000)
    :return: The actual number of faces after decimation
    """
    if obj.type != 'MESH':
        print(f"Error: Object {obj.name} is not a mesh object.")
        return None

    initial_faces = len(obj.data.polygons)
    
    if initial_faces <= target_faces:
        print(f"Object {obj.name} already has fewer faces ({initial_faces}) than target ({target_faces})")
        return initial_faces

    ratio = target_faces / initial_faces

    decimate = obj.modifiers.new(name="Decimate", type='DECIMATE')
    decimate.ratio = ratio
    decimate.use_collapse_triangulate = True

    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier="Decimate")

    final_faces = len(obj.data.polygons)
    
    print(f"Decimated {obj.name} from {initial_faces} to {final_faces} faces (target was {target_faces})")
    return final_faces

def rotate_object(obj, angle):
    """
    Rotate the object around its Z-axis.
    
    :param obj: The object to rotate
    :param angle: The angle of rotation in degrees
    """
    
    obj.rotation_mode = 'XYZ'
    obj.rotation_euler[2] = angle


def set_random_rotation_on_axis(obj, axes='Z'):
    """
    Set random rotations for an object on the specified axes.
    
    :param obj: The Blender object to rotate
    :param axes: String containing the axes to rotate around (e.g., 'X', 'XY', 'XYZ')
    """
    
    valid_axes = set('XYZ')
    axes = axes.upper()
    if not all(axis in valid_axes for axis in axes):
        print(f"Error: Invalid axes '{axes}'. Must only contain 'X', 'Y', and/or 'Z'")
        return
    
    bpy.ops.object.mode_set(mode='OBJECT')
    
    obj.rotation_mode = 'XYZ'
    
    axis_index = {'X': 0, 'Y': 1, 'Z': 2}
    
    for axis in axes:
        random_angle = random.uniform(0, 2 * math.pi)
        obj.rotation_euler[axis_index[axis]] = random_angle
        print(f"Set random rotation of {math.degrees(random_angle):.2f}° on {axis} axis for {obj.name}")
    

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


def setup_object(glb_path, decimate_target = 1000):
    
    obj = import_glb(glb_path)
    
    bpy.ops.object.mode_set(mode='OBJECT')
    
    bm = bmesh.new()
    bm.from_mesh(obj.data)

    z_min_vertex = min(bm.verts, key=lambda v: v.co.z)
    z_min_local = z_min_vertex.co

    z_min_world = obj.matrix_world @ z_min_local

    obj.location.z = obj.location.z - z_min_world.z

    bm.free()


    if obj is None:
        print("Error: Failed to import GLB file. Exiting.")
        return
    
    obj.name = "Render_object"
    
    #Fix the obj
    remove_doubles_from_mesh(obj, 0.001)
    #merge_boundary_vertices_closeness(obj, 0.002)
    #remove_shape_keys(obj)
    decimate_to_target_faces(obj, decimate_target)
    
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
    
    # Set up the render settings
    bpy.context.scene.render.filepath = output_path
    bpy.context.scene.render.image_settings.file_format = config['file_format']
    bpy.context.scene.render.film_transparent = config['transparent_background']
    
    print(f"Rendered view at {output_path} with angle {angle}")
    bpy.ops.render.render(write_still=True)

def render_step(output_dir, obj, config):
    os.makedirs(output_dir, exist_ok=True)

    rotation_increments = config['rotation_increments']
    for angle in range(0, 360, rotation_increments):
        rotate_object(obj, angle)
        
        output_path = os.path.join(output_dir, f"render_{angle}.png")
        render_view(output_path, angle, config)

def remove_shape_keys(obj):
    """
    Remove shape keys from the object
    
    :param obj: The Blender object to remove shape keys from
    """
    if obj.data.shape_keys:
        bpy.context.view_layer.objects.active = obj
        while obj.data.shape_keys:
            bpy.context.object.active_shape_key_index = 0
            bpy.ops.object.shape_key_remove(all=True)
        print(f"Removed shape keys from {obj.name}")


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

def setup_scene(obj_path, config):
    # Set render engine and GPU acceleration
    bpy.context.scene.render.engine = config['render_engine']
    if config['gpu_acceleration']:
        bpy.context.preferences.addons['cycles'].preferences.compute_device_type = config['compute_device']
        bpy.context.scene.cycles.device = 'GPU'

    # Configure compositor nodes for post-processing if enabled
    if config['use_compositor']:
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

    # Create camera
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
    
    # Import and setup 3D object
    obj = setup_object(obj_path, config['decimate_target'])
    
    # Move the obj lowest point to z = 0
    move_to_zero(obj)
    
    # Apply mesh optimizations if enabled
    if config['optimize_mesh']:
        print(f"Optimizing mesh with threshold {config['remove_doubles_threshold']}")
        remove_doubles_from_mesh(obj, threshold=config['remove_doubles_threshold'])
    
    # Set the center of the obj to its volumetric center and make the light track its position
    set_origin_to_center_of_volume(obj)
    
    # Apply target tracking
    if config['track_object']:
        target_lock_object(light, obj)
        target_lock_object(camera, obj)

    return camera, light, shadow_catcher, obj


def setup_simulation_env(plane, obj, simulation_type = 'Softbody'):
    """
    Set up simulation environment with randomized parameters
    
    :param plane: The collision plane
    :param obj: The object to simulate
    """    
    plane.modifiers.new(name="Collision", type='COLLISION')
  
    obj.modifiers.new(name= simulation_type, type='SOFT_BODY')
    settings = obj.modifiers["Softbody"].settings
    
    settings.use_goal = True
    settings.goal_default = random.uniform(0.2, 0.4)
    settings.mass = random.uniform(0.2, 0.7)

    settings.use_stiff_quads = True
    
    settings.pull = random.uniform(0.2, 0.4)      
    settings.push = 0 
    settings.bend = random.uniform(0.3, 7.5)      
    
    settings.mass = random.uniform(0.5, 2.0)
    settings.friction = random.uniform(0.2, 0.8)
    settings.damping = random.uniform(0.1, 0.5)
    
    print(f"Simulation parameters: pull={settings.pull:.3f}, "
          f"push={settings.push:.3f}, bend={settings.bend:.3f}")
    
def get_second_lowest_vertex(obj):
    """
    Get the second lowest vertex of the object
    We get the second lowest to avoid cases where a single loose vertex is in the mesh (bad obj modeling)
    
    :param obj: The Blender object to get the second lowest vertex from
    """
    
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

def move_to_zero(obj):

    bpy.ops.object.transform_apply( rotation=True)
    bpy.context.scene.cursor.location =  get_second_lowest_vertex(obj)
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')
    obj.location.z = 0    
    bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS', center='MEDIAN')
    obj.location.x = 0  
    obj.location.y = 0

def shade_smooth(obj):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.shade_smooth()

def smooth_and_convert_to_quads(obj):
    shade_smooth(obj)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.tris_convert_to_quads()
    bpy.ops.object.mode_set(mode='OBJECT')
    
def setup_simulation_env_cloth(plane, obj, output_dir, simulation_type='Cloth', config=None):
    """
    Set up simulation environment with randomized parameters
    
    :param plane: The collision plane
    :param obj: The object to simulate
    :param output_dir: The directory to save the simulation parameters
    :param simulation_type: Type of simulation to apply ('Cloth' or 'SOFT_BODY')
    :param config: Configuration dictionary with simulation parameters
    """    
    if config is None:
        config = {
            'simulation_material': 'leather',
            'save_parameters': True
        }
        
    plane.modifiers.new(name=simulation_type, type='COLLISION')
  
    obj.modifiers.new(name="Cloth", type='CLOTH')
    settings = obj.modifiers["Cloth"].settings
    
    material = config['simulation_material']
    
    if material == "plastic":
        settings.mass = random.uniform(0.05, 0.3)
        settings.air_damping = random.uniform(1, 2)
        settings.bending_stiffness = random.uniform(0.5, 1)
        settings.tension_stiffness = random.uniform(0, 15)
        
        settings.use_pressure = True
        settings.use_pressure_volume = True
        settings.target_volume = random.uniform(0, 1)
        if random.random() < 0.6:
            settings.use_internal_springs = True
            settings.internal_tension_stiffness = random.uniform(0, 1)
            settings.internal_compression_stiffness = random.uniform(0, 1)
            settings.internal_tension_stiffness_max = 0
            settings.internal_compression_stiffness_max = 0
            
        # Self collision
        collision_settings = obj.modifiers["Cloth"].collision_settings
        collision_settings.use_collision = True
        collision_settings.use_self_collision = True
        collision_settings.friction = random.uniform(0.2, 0.8)
        collision_settings.self_distance_min = 0.001
        collision_settings.collision_quality = 4
        collision_settings.self_friction = 20
        collision_settings.distance_min = 0.001
        
    elif material == "leather":
        settings.mass = random.uniform(33, 44)
        
        settings.tension_stiffness = random.uniform(64.0, 96.0)  
        settings.compression_stiffness = random.uniform(64.0, 96.0)   
        settings.shear_stiffness = random.uniform(64.0, 96.0)  
        settings.bending_stiffness = random.uniform(120.0, 180.0)  
        
        settings.tension_damping = random.uniform(20.0, 30.0)  
        settings.compression_damping = random.uniform(20.0, 30.0)  
        settings.shear_damping = random.uniform(20.0, 30.0)  
        settings.bending_damping = random.uniform(0.4, 0.6)  
        
        settings.use_internal_springs = True
        settings.internal_tension_stiffness = random.uniform(12.0, 18.0)  
        settings.internal_compression_stiffness = random.uniform(12.0, 18.0)  
        settings.internal_tension_stiffness_max = random.uniform(12.0, 18.0) 
        settings.internal_compression_stiffness_max = random.uniform(12.0, 18.0) 
 
        collision_settings = obj.modifiers["Cloth"].collision_settings
        collision_settings.use_collision = True
        collision_settings.use_self_collision = True
        collision_settings.distance_min = 0.001  
        collision_settings.self_distance_min = 0.001  
        collision_settings.collision_quality = random.randint(13, 17)

    params_dict = {
        "mass": settings.mass,
        "air_damping": settings.air_damping,
        "bending_stiffness": settings.bending_stiffness,
        "tension_stiffness": settings.tension_stiffness,
        "pressure": settings.uniform_pressure_force,
        "volume": settings.target_volume,
        "friction": collision_settings.friction,
        "self_friction": collision_settings.self_friction,
        "min_distance": collision_settings.distance_min,
        "self_min_distance": collision_settings.self_distance_min,
        "collision_quality": collision_settings.collision_quality
    }
    
    if config['save_parameters']:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        filepath = os.path.join(output_dir, f"sim_params.txt")
        
        # Write parameters to file
        with open(filepath, "w") as f:
            for param, value in params_dict.items():
                f.write(f"{param}: {value}\n")

    print(f"Simulation parameters: mass={settings.mass:.3f}, "
          f"air_damping={settings.air_damping:.3f}, "
          f"bending_stiffness={settings.bending_stiffness:.3f}, "
          f"tension_stiffness={settings.tension_stiffness:.3f}")

def run_physics_simulation(duration=10.0, frame_rate=24):
    scene = bpy.context.scene
    scene.frame_end = int(duration * frame_rate)

    for frame in range(scene.frame_start, scene.frame_end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()

    scene.frame_set(scene.frame_end)
    return scene.frame_end

def simulate_step(plane, obj, output_dir, config):
    simulation_type = config['simulation_type']
    
    if simulation_type == 'Cloth':
        setup_simulation_env_cloth(plane, obj, output_dir, simulation_type, config)
    else:
        setup_simulation_env(plane, obj, simulation_type)
    
    sim_duration = random.uniform(
        config['simulation_min_duration'], 
        config['simulation_max_duration']
    )
    
    frame_end = run_physics_simulation(sim_duration)    
    
    return frame_end


def apply_simulation_as_default(obj, simulation_type= 'Cloth'):
    """
    Applies the soft body simulation result as the default state of the object.
    
    :param obj: The object with the soft body simulation
    """    
    
    bpy.context.scene.frame_set(bpy.context.scene.frame_end)
    
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    
    bpy.ops.object.modifier_apply(modifier=simulation_type)
    
    set_origin_to_center_of_volume(obj)
    
    bpy.context.scene.frame_set(0)


def set_random_color(obj):
    """
    Multiply the existing material color/texture with a random color,
    preserving the texture details while tinting it.
    
    :param obj: The Blender object to color
    """
    
    if not obj.data.materials:
        print(f"Error: Object {obj.name} has no materials to modify")
        return None
    
    material = obj.data.materials[0]
    
    if not material.use_nodes:
        material.use_nodes = True
    
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    
    principled = next(
        (node for node in nodes if node.type == 'BSDF_PRINCIPLED'),
        None
    )
    
    if not principled:
        print(f"Error: No Principled BSDF node found in material {material.name}")
        return None
    
    random_color = (
        random.random(),  # R
        random.random(),  # G
        random.random(),  # B
        1.0              # A
    )
    
    mix_node = nodes.new('ShaderNodeMixRGB')
    mix_node.blend_type = 'SOFT_LIGHT'
    mix_node.inputs[0].default_value = 1.0
    mix_node.inputs[2].default_value = random_color
    
    base_color_input = principled.inputs['Base Color']
    if base_color_input.links:
        original_link = base_color_input.links[0]
        original_node = original_link.from_node
        
        links.new(original_node.outputs[0], mix_node.inputs[1])
    else:
        mix_node.inputs[1].default_value = (1, 1, 1, 1)
    
    links.new(mix_node.outputs[0], base_color_input)
    
    print(f"Added color multiplication {random_color[:3]} to material {material.name}")
    return random_color


def main(seed=None, run_number=None, asset=None, output_dir=None, config=None):
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
            'use_compositor': True,
            'contrast': 1.05,
            'saturation': 1.3,
            
            # Camera settings
            'camera_location': (0, -2, 0.5),
            'camera_rotation': (math.pi/2, 0, 0),
            'track_object': True,
            
            # Light settings
            'light_type': 'SUN',
            'light_location': (-3, 0, 2),
            'light_energy': 1.0,
            
            # Shadow catcher
            'shadow_catcher_location': (0, 0, 0),
            'shadow_catcher_size': 20,
            'shadow_opacity': 0.6,
            
            # Mesh optimization
            'optimize_mesh': False,
            'remove_doubles_threshold': 0.001,
            'decimate_target': 10000,
            
            # Material settings
            'random_colors': True,
            
            # Rotation settings
            'rotation_increments': 60,
            
            # Simulation settings
            'simulation_type': 'Cloth',  # 'Cloth' or 'Softbody'
            'simulation_material': 'leather',  # 'leather' or 'plastic'
            'simulation_min_duration': 0.5,
            'simulation_max_duration': 8.0,
            'save_parameters': True,
            'object_elevation': 0.2,  # Initial Z height for the object
            'object_final_elevation': 0.02  # Final Z height after simulation
        }

    # Set global random seed
    if seed is not None:
        random.seed(seed)
        
    if asset is not None:
        # Extract model name without extension
        asset_name = os.path.splitext(os.path.basename(asset))[0]
        # Create base directory for this model
        model_dir = os.path.join(output_dir, asset_name)
        # Create run-specific subdirectory
        save_dir = os.path.join(model_dir, f"_run_{run_number}")
        os.makedirs(save_dir, exist_ok=True)

    # Set the scene frame to 1
    bpy.context.scene.frame_set(1)

    # Load & setup all the assets
    camera, light, shadow_catcher, obj = setup_scene(asset, config)

    # Only set object mode if we have objects in the scene
    if bpy.context.selected_objects:
        bpy.ops.object.mode_set(mode='OBJECT')

    # Set random rotation on all axes and set position above the plane
    set_random_rotation_on_axis(obj, 'XYZ')
    obj.location.z = config['object_elevation']

    # Set obj material to a random color if enabled
    if config['random_colors']:
        set_random_color(obj)

    #Simulate obj state with randomized parameters
    frame_end = simulate_step(shadow_catcher, obj, save_dir, config)   
    
    # Apply the simulation as the default state of the object
    apply_simulation_as_default(obj, config['simulation_type'])
    shade_smooth(obj)

    # Move the object to the origin in case the obj moved due to simulation
    obj.location[0] = 0
    obj.location[1] = 0
    obj.location[2] = config['object_final_elevation']

    # Render the object from all angles
    render_step(save_dir, obj, config)    
    
    print("Rendering complete!")

if __name__ == "__main__":
    # Configuration dictionary for customizing all rendering parameters
    config = {
        # Processing mode
        'mode': 'directory',  # 'single' or 'directory'
        
        # Input/Output paths
        'single_model_path': "path/to/your/model.glb",
        'models_directory': "path/to/models/folder",
        'output_directory': "path/to/output/folder",
        
        # Number of variations per model
        'runs_per_object': 5,
        
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
        'use_compositor': True,
        'contrast': 1.05,
        'saturation': 1.3,
        
        # Camera settings
        'camera_location': (0, -2, 0.5),
        'camera_rotation': (math.pi/2, 0, 0),
        'track_object': True,
        
        # Light settings
        'light_type': 'SUN',
        'light_location': (-3, 0, 2),
        'light_energy': 1.0,
        
        # Shadow catcher
        'shadow_catcher_location': (0, 0, 0),
        'shadow_catcher_size': 20,
        'shadow_opacity': 0.6,
        
        # Mesh optimization
        'optimize_mesh': False,
        'remove_doubles_threshold': 0.001,
        'decimate_target': 10000,
        
        # Material settings
        'random_colors': False,
        
        # Rotation settings
        'rotation_increments': 60,
        
        # Simulation settings
        'simulation_type': 'Cloth',  # 'Cloth' or 'Softbody'
        'simulation_material': 'leather',  # 'leather' or 'plastic'
        'simulation_min_duration': 0.5,
        'simulation_max_duration': 8.0,
        'save_parameters': True,
        'object_elevation': 0.2,  # Initial Z height for the object
        'object_final_elevation': 0.02  # Final Z height after simulation
    }

    if config['mode'] == 'single':
        # Process a single model
        main(
            asset=config['single_model_path'], 
            output_dir=config['output_directory'], 
            run_number=0,
            config=config
        )
    
    elif config['mode'] == 'directory':    
        # Get all .glb files recursively
        glb_files = glob.glob(os.path.join(config['models_directory'], "**/*.glb"), recursive=True)
        total_files = len(glb_files)

        for i, obj_path in enumerate(glb_files, 1):
            print(f"Processing {i}/{total_files}: {os.path.basename(obj_path)}")
            for run in range(config['runs_per_object']):
                main(
                    asset=obj_path, 
                    output_dir=config['output_directory'], 
                    run_number=run, 
                    seed=None,
                    config=config
                )
            print(f"Completed {i}/{total_files} files") 
    
    else:
        print("Invalid mode. Please set 'mode' to either 'single' or 'directory'.") 