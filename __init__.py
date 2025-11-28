bl_info = {
    "name": "XPS Import/Export",
    "author": "maylog, johnzero7",
    "version": (2, 2, 1),
    "blender": (5, 0, 0),
    "location": "File > Import-Export > XNALara/XPS",
    "description": "Fork of XNALara/XPS import-export tool with Blender 5.0 compatibility. Original addon by XNALara community.",
    "category": "Import-Export",
    "support": "COMMUNITY",
}

_modules = [
    'xps_panels',
    'xps_tools',
    'xps_toolshelf',
    'xps_const',
    'xps_types',
    'xps_material',
    'write_ascii_xps',
    'write_bin_xps',
    'read_ascii_xps',
    'read_bin_xps',
    'mock_xps_data',
    'export_xnalara_model',
    'export_xnalara_pose',
    'import_xnalara_model',
    'import_xnalara_pose',
    'import_obj',
    'export_obj',
    'ascii_ops',
    'bin_ops',
    'timing',
    'material_creator',
    'node_shader_utils',
]

if "bpy" in locals():
    import importlib
    for module in _modules_loaded:
        if module in globals():
            importlib.reload(globals()[module])
    _modules_loaded[:] = []

for name in _modules:
    if name in globals():
        continue
    full_name = f"{__name__}.{name}"
    try:
        mod = __import__(full_name, fromlist=[name])
        globals()[name] = mod
    except ImportError as e:
        print(f"Warning: Failed to import {name}: {e}")

_modules_loaded = [globals()[name] for name in _modules if name in globals()]

import bpy
from bpy.utils import register_class, unregister_class

classesToRegister = [
    xps_panels.XPSToolsObjectPanel,
    xps_panels.XPSToolsBonesPanel,
    xps_panels.XPSToolsAnimPanel,

    xps_toolshelf.ArmatureBonesHideByName_Op,
    xps_toolshelf.ArmatureBonesHideByVertexGroup_Op,
    xps_toolshelf.ArmatureBonesShowAll_Op,
    xps_toolshelf.ArmatureBonesRenameToBlender_Op,
    xps_toolshelf.ArmatureBonesRenameToXps_Op,
    xps_toolshelf.ArmatureBonesConnect_Op,
    xps_toolshelf.NewRestPose_Op,

    xps_tools.Import_Xps_Model_Op,
    xps_tools.Export_Xps_Model_Op,
    xps_tools.Import_Xps_Pose_Op,
    xps_tools.Export_Xps_Pose_Op,
    xps_tools.Import_Poses_To_Keyframes_Op,
    xps_tools.Export_Frames_To_Poses_Op,
    xps_tools.ArmatureBoneDictGenerate_Op,
    xps_tools.ArmatureBoneDictRename_Op,
    xps_tools.ArmatureBoneDictRestore_Op,
    xps_tools.ImportXpsNgff,
    xps_tools.ExportXpsNgff,
    xps_tools.XpsImportSubMenu,
    xps_tools.XpsExportSubMenu,
]

registerClasses, unregisterClasses = bpy.utils.register_classes_factory(classesToRegister)

def register():
    registerClasses()
    xps_tools.register()
    print(f"{bl_info['name']} v{bl_info['version']} has been enabled.")

def unregister():
    xps_tools.unregister()
    unregisterClasses()
    print(f"{bl_info['name']} has been disabled.")