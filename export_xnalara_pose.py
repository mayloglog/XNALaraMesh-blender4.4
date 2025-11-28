from math import degrees
import os
import re

from . import write_ascii_xps
from . import xps_types
from .timing import timing

import bpy
from mathutils import Vector


def getOutputPoseSequence(filename):
    filepath, file = os.path.split(filename)
    basename, ext = os.path.splitext(file)
    poseSuffix = re.sub(r'\d+$', '', basename)

    startFrame = bpy.context.scene.frame_start
    endFrame = bpy.context.scene.frame_end
    initialFrame = bpy.context.scene.frame_current

    for currFrame in range(startFrame, endFrame + 1):
        bpy.context.scene.frame_set(currFrame)
        numSuffix = f'{currFrame:03d}'
        name = poseSuffix + numSuffix + ext
        newPoseFilename = os.path.join(filepath, name)
        getOutputFilename(newPoseFilename)

    bpy.context.scene.frame_current = initialFrame


def getOutputFilename(filename):
    blenderExportSetup()
    xpsExport(filename)
    blenderExportFinalize()


def blenderExportSetup():
    pass


def blenderExportFinalize():
    pass


def saveXpsFile(filename, xpsPoseData):
    write_ascii_xps.writeXpsPose(filename, xpsPoseData)


@timing
def xpsExport(filename):
    print("------------------------------------------------------------")
    print("------------- EXECUTING XPS POSE EXPORTER ------------------")
    print("------------------------------------------------------------")
    print("Exporting Pose:", filename)

    root_dir, _ = os.path.split(filename)
    print(f'Root directory: {root_dir}')

    xpsPoseData = exportPose()
    saveXpsFile(filename, xpsPoseData)


def exportPose():
    armature = next(
        (obj for obj in bpy.context.selected_objects if obj.type == 'ARMATURE'),
        None
    )
    if not armature:
        armature = next(
            (obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE'),
            None
        )
    
    if not armature:
        raise ValueError("No armature found. Please select or create an armature to export the pose.")

    boneCount = len(armature.data.bones)
    print(f'Exporting pose for {boneCount} bones')

    return xpsPoseData(armature)


def xpsPoseData(armatureObj):
    original_active = bpy.context.view_layer.objects.active
    original_selected = bpy.context.selected_objects.copy()
    
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    
    armatureObj.select_set(True)
    bpy.context.view_layer.objects.active = armatureObj
    
    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    
    poseData = {}
    for bone in armatureObj.pose.bones:
        coord = xpsBoneTranslate(bone, armatureObj.matrix_world)
        rot = xpsBoneRotate(bone)
        scale = xpsBoneScale(bone)
        
        xpsBone = xps_types.XpsBonePose(bone.name, coord, rot, scale)
        poseData[bone.name] = xpsBone
    
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    
    for obj in original_selected:
        obj.select_set(True)
    
    bpy.context.view_layer.objects.active = original_active
    
    return poseData


def xpsPoseBone(pose_bone, object_matrix):
    name = pose_bone.name
    coord = xpsBoneTranslate(pose_bone, object_matrix)
    rot = xpsBoneRotate(pose_bone)
    scale = xpsBoneScale(pose_bone)

    return xps_types.XpsBonePose(name, coord, rot, scale)


def eulerToXpsBoneRot(euler):
    return Vector((degrees(euler.x), degrees(euler.y), degrees(euler.z)))


def vectorTransform(vec):
    return Vector((vec.x, -vec.y, vec.z))


def vectorTransformTranslate(vec):
    return Vector((vec.x, -vec.y, vec.z))


def vectorTransformScale(vec):
    return Vector((vec.x, vec.y, vec.z))


def xpsBoneRotate(pose_bone):
    if pose_bone.rotation_mode == 'QUATERNION':
        pose_quat = pose_bone.rotation_quaternion.copy()
    else:
        pose_quat = pose_bone.rotation_euler.to_quaternion()
    
    edit_quat = pose_bone.bone.matrix_local.to_quaternion()

    delta_quat = edit_quat @ pose_quat @ edit_quat.inverted()
    euler = delta_quat.to_euler('YXZ')
    xps_rot = eulerToXpsBoneRot(euler)
    return vectorTransform(xps_rot)


def xpsBoneTranslate(pose_bone, object_matrix):
    translate = pose_bone.location.copy()
    edit_quat = pose_bone.bone.matrix_local.to_quaternion()
    local_vec = edit_quat @ translate
    
    world_rot = object_matrix.to_3x3()
    world_vec = world_rot @ local_vec
    
    return vectorTransformTranslate(world_vec)


def xpsBoneScale(pose_bone):
    return vectorTransformScale(pose_bone.scale)