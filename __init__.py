bl_info = {
    "name": "XPS Import/Export",
    "author": "maylog, johnzero7",
    "version": (2, 2, 2),
    "blender": (5, 0, 0),
    "location": "File > Import-Export",
    "description": "Community-maintained fork of the original XNALara/XPS Tools. Fully Blender 5.0+ compatible.",
    "category": "Import-Export",
    "support": "COMMUNITY",
    "credits": "2025 johnzero7 (original author), 2025 Clothoid, 2025 XNALara/XPS community, 2025 maylog (Blender 5.0+ update & Extensions submission)",
}


from . import (
    xps_panels,
    xps_tools,
    xps_toolshelf,
    xps_const,
    xps_types,
    xps_material,
    write_ascii_xps,
    write_bin_xps,
    read_ascii_xps,
    read_bin_xps,
    mock_xps_data,
    export_xnalara_model,
    export_xnalara_pose,
    import_xnalara_model,
    import_xnalara_pose,
    import_obj,
    export_obj,
    ascii_ops,
    bin_ops,
    timing,
    material_creator,
    node_shader_utils,
)


modules = (
    xps_const,
    xps_types,
    xps_material,
    read_ascii_xps,
    read_bin_xps,
    write_ascii_xps,
    write_bin_xps,
    mock_xps_data,
    material_creator,
    node_shader_utils,
    timing,
    ascii_ops,
    bin_ops,
    import_obj,
    export_obj,
    import_xnalara_model,
    export_xnalara_model,
    import_xnalara_pose,
    export_xnalara_pose,
    xps_tools,
    xps_toolshelf,
    xps_panels,
)

def register():
    for mod in modules:
        if hasattr(mod, "register"):
            mod.register()

def unregister():
    for mod in reversed(modules):
        if hasattr(mod, "unregister"):
            mod.unregister()