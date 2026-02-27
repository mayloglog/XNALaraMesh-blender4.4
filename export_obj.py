import os
import bpy
import mathutils
from mathutils import Matrix, Vector


def write_arl(filepath, armatures, global_matrix=None):
    """Write XPS ARL bone file."""
    if global_matrix is None:
        global_matrix = Matrix()
    
    if not armatures:
        print("Warning: No armatures found for ARL export")
        return False
    
    # We only use the first armature found (typical for XPS models)
    armature_ob, ob_mat = armatures[0]
    
    print(f"Writing ARL file: {filepath}")
    print(f"Armature: {armature_ob.name}, Bones: {len(armature_ob.data.bones)}")
    
    with open(filepath, "w", encoding="utf8", newline="\n") as f:
        fw = f.write
        fw('# XPS NGFF ARL Blender Exporter file: %r\n' %
            (os.path.basename(bpy.data.filepath) or "None"))
        fw('# Version: %g\n' % 0.1)
        fw('%i # bone Count\n' % len(armature_ob.data.bones))
        
        # Create a copy to apply transformation without modifying original
        armature_data = armature_ob.data.copy()
        armature_data.transform(global_matrix @ ob_mat)
        
        bones = armature_data.bones
        for bone in bones:
            fw('%s\n' % bone.name)
            parent_bone_id = -1
            if bone.parent:
                parent_bone_name = bone.parent.name
                parent_bone_id = bones.find(parent_bone_name)
            fw('%i\n' % parent_bone_id)
            fw('%g %g %g\n' % bone.head_local[:])
    
    print(f"ARL file written successfully: {filepath}")
    return True


def add_bw_lines_to_obj(obj_filepath, all_weights, global_matrix=None):
    """
    Add bone weight lines (bw) to OBJ file
    all_weights: list of [(vertex_index, [(bone_id, weight), ...]), ...]
    """
    if not all_weights:
        return False
    
    print(f"Adding bw lines to {obj_filepath}")
    
    # Read original OBJ file
    with open(obj_filepath, 'r') as f:
        lines = f.readlines()
    
    # Find position after all vertices
    vertex_count = 0
    insert_pos = 0
    for i, line in enumerate(lines):
        if line.startswith('v '):
            vertex_count += 1
        elif line.startswith(('vt ', 'vn ', 'f ', 'g ', 'o ', 's ')):
            # Insert before first non-vertex line
            if insert_pos == 0:
                insert_pos = i
            break
    
    if insert_pos == 0:
        insert_pos = len(lines)
    
    print(f"Found {vertex_count} vertices, inserting at position {insert_pos}")
    
    # Generate bw lines
    bw_lines = []
    for v_idx, weights in all_weights:
        # Note: OBJ vertex indices start from 1, but our indices start from 0
        # bw line format: bw [ [bone_id,weight], ... ]
        bw_str = 'bw [%s]\n' % ', '.join('[%i,%g]' % w for w in weights)
        bw_lines.append(bw_str)
    
    # Insert bw lines
    new_lines = lines[:insert_pos] + bw_lines + lines[insert_pos:]
    
    # Write back to file
    with open(obj_filepath, 'w') as f:
        f.writelines(new_lines)
    
    print(f"Added {len(bw_lines)} bw lines to OBJ file")
    return True


def add_vertex_colors_to_obj(obj_filepath, vcolor_data):
    """
    Add vertex color lines (vc) to OBJ file
    vcolor_data: [(obj_name, colors_list)], colors_list = [(r,g,b,a), ...]
    """
    if not vcolor_data:
        return False
    
    print("Adding vertex colors to OBJ file")
    
    # Read original OBJ file
    with open(obj_filepath, 'r') as f:
        lines = f.readlines()
    
    # Find position after all vertices
    vertex_count = 0
    insert_pos = 0
    for i, line in enumerate(lines):
        if line.startswith('v '):
            vertex_count += 1
        elif line.startswith(('vt ', 'vn ', 'f ', 'g ', 'o ', 's ')):
            if insert_pos == 0:
                insert_pos = i
            break
    
    if insert_pos == 0:
        insert_pos = len(lines)
    
    # Collect unique vertex colors
    vc_lines = []
    vc_dict = {}
    vc_count = 0
    
    for obj_name, colors in vcolor_data:
        for color in colors:
            color_key = (round(color[0], 4), round(color[1], 4), round(color[2], 4), round(color[3], 4))
            if color_key not in vc_dict:
                vc_dict[color_key] = vc_count
                vc_lines.append('vc %.4f %.4f %.4f %.4f\n' % color)
                vc_count += 1
    
    if vc_lines:
        # Insert vc lines
        new_lines = lines[:insert_pos] + vc_lines + lines[insert_pos:]
        
        # Write back to file
        with open(obj_filepath, 'w') as f:
            f.writelines(new_lines)
        
        print(f"Added {len(vc_lines)} vertex color definitions")
        return True
    
    return False


def export_with_xps(context, filepath, **kwargs):
    """
    Main export function: Call official exporter + add XPS data
    """
    # Extract XPS related parameters
    use_xps_arl = kwargs.get('use_xps_arl', True)
    use_vcolors = kwargs.get('use_vcolors', False)
    use_selection = kwargs.get('use_selection', True)
    global_matrix = kwargs.get('global_matrix', None)
    
    if global_matrix is None:
        global_matrix = Matrix()
    
    print(f"Exporting with XPS: ARL={use_xps_arl}, VColors={use_vcolors}")
    
    # Get dependency graph
    depsgraph = context.evaluated_depsgraph_get()
    scene = context.scene
    
    # Collect objects to export
    if use_selection:
        objects = context.selected_objects
    else:
        objects = scene.objects
    
    print(f"Found {len(objects)} objects to export")
    
    # Collect armatures for ARL
    armatures = []
    # Collect bone weights for each mesh
    all_weights = {}  # Indexed by object name
    # Collect vertex color data (store as data copy, not mesh references)
    vcolor_data = []  # [(obj_name, vertex_colors_data)]
    
    if use_xps_arl or use_vcolors:
        for obj in objects:
            # Collect armatures
            if obj.type == 'ARMATURE' and use_xps_arl:
                armature_entry = (obj, obj.matrix_world.copy())
                if armature_entry not in armatures:
                    armatures.append(armature_entry)
                    print(f"Found armature: {obj.name}")
            
            # Collect mesh data (weights and vertex colors)
            elif obj.type == 'MESH':
                # Get evaluated mesh (with modifiers applied)
                obj_eval = obj.evaluated_get(depsgraph)
                me = obj_eval.to_mesh()
                if me is None:
                    continue
                
                # Copy mesh data to avoid reference issues
                me_copy = me.copy()
                
                # Collect vertex colors
                if use_vcolors and me_copy.vertex_colors:
                    colors = []
                    color_layer = me_copy.vertex_colors.active.data
                    loops = me_copy.loops
                    
                    # Get first loop color for each vertex
                    vc_map = {}
                    for loop in loops:
                        v_idx = loop.vertex_index
                        if v_idx not in vc_map:
                            color = color_layer[loop.index].color
                            vc_map[v_idx] = (color[0], color[1], color[2], 1.0)
                    
                    # Convert to list sorted by vertex index
                    colors = [vc_map[i] for i in range(len(me_copy.vertices)) if i in vc_map]
                    vcolor_data.append((obj.name, colors))
                    print(f"Found vertex colors on {obj.name} with {len(colors)} vertices")
                
                # Collect bone weights
                if use_xps_arl:
                    armature = obj.find_armature()
                    if armature:
                        # Ensure armature is in list
                        armature_entry = (armature, armature.matrix_world.copy())
                        if armature_entry not in armatures:
                            armatures.append(armature_entry)
                            print(f"Found armature via mesh: {armature.name}")
                        
                        # Get weight data
                        weights = []
                        for v_idx, v in enumerate(me_copy.vertices):
                            v_weights = []
                            for g in v.groups:
                                group_name = obj.vertex_groups[g.group].name
                                bone_id = armature.data.bones.find(group_name)
                                if bone_id != -1 and g.weight > 0:
                                    v_weights.append((bone_id, g.weight))
                            
                            # Sort by weight descending
                            v_weights.sort(key=lambda x: x[1], reverse=True)
                            # Pad to 4 weights (XPS format)
                            while len(v_weights) < 4:
                                v_weights.append((0, 0.0))
                            
                            weights.append((v_idx, v_weights))
                        
                        if weights:
                            all_weights[obj.name] = weights
                            print(f"Object {obj.name}: collected {len(weights)} vertex weights")
                
                # Clean up temporary mesh
                obj_eval.to_mesh_clear()
                bpy.data.meshes.remove(me_copy)
    
    print(f"Collected {len(armatures)} armatures, {len(all_weights)} weighted meshes, {len(vcolor_data)} meshes with vertex colors")
    
    # Call official OBJ exporter
    obj_export_kwargs = {
        'filepath': filepath,
        'export_selected_objects': use_selection,
        'apply_modifiers': kwargs.get('use_mesh_modifiers', True),
        'export_uv': kwargs.get('use_uvs', True),
        'export_normals': kwargs.get('use_normals', False),
        'export_materials': kwargs.get('use_materials', True),
        'export_triangulated_mesh': kwargs.get('use_triangles', False),
        'export_vertex_groups': kwargs.get('use_vertex_groups', False),
        'export_smooth_groups': kwargs.get('use_smooth_groups', False),
        'smooth_group_bitflags': kwargs.get('use_smooth_groups_bitflags', False),
    }
    
    print("Calling official OBJ exporter...")
    result = bpy.ops.wm.obj_export(**obj_export_kwargs)
    print(f"OBJ export result: {result}")
    
    if 'FINISHED' not in result:
        return result
    
    # Add XPS bone data
    if use_xps_arl and (armatures or all_weights):
        print("Adding XPS bone data...")
        
        # Add bw lines to OBJ file
        if all_weights:
            # Flatten all weights
            flat_weights = []
            for obj_name, weights in all_weights.items():
                flat_weights.extend(weights)
                print(f"Object {obj_name}: {len(weights)} weights")
            
            if flat_weights:
                add_bw_lines_to_obj(filepath, flat_weights, global_matrix)
        
        # Generate ARL file
        if armatures:
            arl_filepath = os.path.splitext(filepath)[0] + ".arl"
            print(f"Generating ARL file: {arl_filepath}")
            write_arl(arl_filepath, armatures, global_matrix)
    
    # Add vertex colors
    if use_vcolors and vcolor_data:
        print("Adding vertex colors...")
        add_vertex_colors_to_obj(filepath, vcolor_data)
        print(f"Added vertex colors from {len(vcolor_data)} meshes")
    
    print("Export completed successfully")
    return {'FINISHED'}


def save(context,
         filepath,
         *,
         use_triangles=False,
         use_edges=True,
         use_normals=False,
         use_vcolors=False,
         use_smooth_groups=False,
         use_smooth_groups_bitflags=False,
         use_uvs=True,
         use_materials=True,
         use_mesh_modifiers=True,
         use_mesh_modifiers_render=False,
         use_blen_objects=True,
         group_by_object=False,
         group_by_material=False,
         keep_vertex_order=False,
         use_vertex_groups=False,
         use_nurbs=True,
         use_selection=True,
         use_animation=False,
         global_matrix=None,
         path_mode='AUTO',
         use_xps_arl=True,
         ):
    
    print(f"Starting XPS OBJ export to: {filepath}")
    print(f"Options: ARL={use_xps_arl}, VColors={use_vcolors}, Selection={use_selection}")
    
    # Call export function
    return export_with_xps(context, filepath,
                          use_triangles=use_triangles,
                          use_edges=use_edges,
                          use_normals=use_normals,
                          use_vcolors=use_vcolors,
                          use_smooth_groups=use_smooth_groups,
                          use_smooth_groups_bitflags=use_smooth_groups_bitflags,
                          use_uvs=use_uvs,
                          use_materials=use_materials,
                          use_mesh_modifiers=use_mesh_modifiers,
                          use_mesh_modifiers_render=use_mesh_modifiers_render,
                          use_blen_objects=use_blen_objects,
                          group_by_object=group_by_object,
                          group_by_material=group_by_material,
                          keep_vertex_order=keep_vertex_order,
                          use_vertex_groups=use_vertex_groups,
                          use_nurbs=use_nurbs,
                          use_selection=use_selection,
                          use_animation=use_animation,
                          global_matrix=global_matrix,
                          path_mode=path_mode,
                          use_xps_arl=use_xps_arl)