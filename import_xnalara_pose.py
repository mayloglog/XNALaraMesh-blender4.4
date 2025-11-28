from math import radians
import os
import re

from . import read_ascii_xps
from .timing import timing
import bpy
from mathutils import Euler, Matrix, Vector, Quaternion

PLACE_HOLDER = r'*side*'
RIGHT_BLENDER_SUFFIX = r'.R'
LEFT_BLENDER_SUFFIX = r'.L'
RIGHT_XPS_SUFFIX = r'right'
LEFT_XPS_SUFFIX = r'left'

xpsData = None
rootDir = ''

def changeBoneNameToBlender(boneName, xpsSuffix, blenderSuffix):
    newName = re.sub(xpsSuffix, PLACE_HOLDER, boneName, flags=re.I)
    newName = re.sub(r'\s+', ' ', newName)
    newName = newName.strip()
    if boneName.lower() != newName.lower():
        newName = f"{newName}{blenderSuffix}"
    return newName.strip()

def renameBoneToBlender(oldName):
    if PLACE_HOLDER not in oldName.lower():
        if re.search(LEFT_XPS_SUFFIX, oldName, flags=re.I):
            return changeBoneNameToBlender(oldName, LEFT_XPS_SUFFIX, LEFT_BLENDER_SUFFIX)
        if re.search(RIGHT_XPS_SUFFIX, oldName, flags=re.I):
            return changeBoneNameToBlender(oldName, RIGHT_XPS_SUFFIX, RIGHT_BLENDER_SUFFIX)
    return oldName

def renameBonesToBlender(armatures_obs):
    for armature in armatures_obs:
        for bone in armature.data.bones:
            bone.name = renameBoneToBlender(bone.name)

def changeBoneNameToXps(oldName, blenderSuffix, xpsSuffix):
    newName = re.sub(f"{re.escape(blenderSuffix)}$", '', oldName, flags=re.I)
    newName = re.sub(r'\s+', ' ', newName)
    newName = re.sub(re.escape(PLACE_HOLDER), xpsSuffix, newName, flags=re.I)
    return newName.strip()

def renameBoneToXps(oldName):
    if PLACE_HOLDER in oldName.lower():
        if re.search(re.escape(LEFT_BLENDER_SUFFIX), oldName, re.I):
            return changeBoneNameToXps(oldName, LEFT_BLENDER_SUFFIX, LEFT_XPS_SUFFIX)
        if re.search(re.escape(RIGHT_BLENDER_SUFFIX), oldName, re.I):
            return changeBoneNameToXps(oldName, RIGHT_BLENDER_SUFFIX, RIGHT_XPS_SUFFIX)
    return oldName.strip()

def renameBonesToXps(armatures_obs):
    for armature in armatures_obs:
        for bone in armature.data.bones:
            bone.name = renameBoneToXps(bone.name)

def getInputPoseSequence(filename):
    filepath, file = os.path.split(filename)
    basename, ext = os.path.splitext(file)
    poseSuffix = re.sub(r'\d+$', '', basename)

    files = []
    for f in os.listdir(filepath):
        if f.lower().endswith('.pose'):
            name_part = re.sub(r'\d+$', '', os.path.splitext(f)[0])
            if name_part == poseSuffix:
                files.append(f)

    files.sort()
    current_frame = bpy.context.scene.frame_current

    for poseFile in files:
        posePath = os.path.join(filepath, poseFile)
        importPoseAsKeyframe(posePath)
        bpy.context.scene.frame_current += 1

    bpy.context.scene.frame_current = current_frame

def importPoseAsKeyframe(filename):
    getInputFilename(filename)

def getInputFilename(filename):
    blenderImportSetup()
    xpsImport(filename)
    blenderImportFinalize()

def blenderImportSetup():
    pass

def blenderImportFinalize():
    pass

def loadXpsFile(filename):
    return read_ascii_xps.readXpsPose(filename)

@timing
def xpsImport(filename):
    global rootDir, xpsData

    print("------------------------------------------------------------")
    print("----------- EXECUTING XPS POSE IMPORTER -------------------")
    print("------------------------------------------------------------")
    print("Importing pose:", filename)

    rootDir, _ = os.path.split(filename)
    print("Root directory:", rootDir)

    xpsData = loadXpsFile(filename)
    importPose()

def importPose():
    boneCount = len(xpsData)
    print(f"Importing pose with {boneCount} bones")

    armature = bpy.context.active_object
    if armature and armature.type == 'ARMATURE':
        setXpsPose(armature, xpsData)

def resetPose(armature):
    for pb in armature.pose.bones:
        pb.matrix_basis = Matrix()

def setXpsPose(armature, xpsData):
    current_mode = bpy.context.mode
    current_obj = bpy.context.active_object

    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)

    bpy.ops.object.mode_set(mode='POSE')

    for boneName, boneData in xpsData.items():
        poseBone = armature.pose.bones.get(boneName)
        if not poseBone:
            poseBone = armature.pose.bones.get(renameBoneToBlender(boneName))
        if poseBone:
            xpsPoseBone(poseBone, boneData)

    insert_keyframes_for_pose(armature)

    bpy.ops.object.mode_set(mode='OBJECT')

    if current_obj:
        bpy.context.view_layer.objects.active = current_obj
    if current_mode != 'OBJECT':
        bpy.ops.object.mode_set(mode=current_mode)

def insert_keyframes_for_pose(armature):
    scene = bpy.context.scene
    current_frame = scene.frame_current
    
    for pose_bone in armature.pose.bones:
        # Fix: Use length_squared for location comparison
        if pose_bone.location.length_squared > 0.0001:
            pose_bone.keyframe_insert(data_path="location", frame=current_frame)
        
        if pose_bone.rotation_mode == 'QUATERNION':
            default_quat = Quaternion((1, 0, 0, 0))
            diff_quat = pose_bone.rotation_quaternion.rotation_difference(default_quat)
            if diff_quat.angle > 0.0001:
                pose_bone.keyframe_insert(data_path="rotation_quaternion", frame=current_frame)
        else:
            # Fix: Use proper Euler angle comparison
            default_euler = Euler((0, 0, 0))
            current_euler = pose_bone.rotation_euler
            diff_euler = Vector((
                abs(current_euler.x - default_euler.x),
                abs(current_euler.y - default_euler.y), 
                abs(current_euler.z - default_euler.z)
            ))
            if diff_euler.length > 0.0001:
                pose_bone.keyframe_insert(data_path="rotation_euler", frame=current_frame)
        
        # Fix: Use proper scale comparison
        scale_diff = (pose_bone.scale - Vector((1, 1, 1))).length
        if scale_diff > 0.0001:
            pose_bone.keyframe_insert(data_path="scale", frame=current_frame)

def xpsPoseBone(poseBone, xpsBoneData):
    xpsBoneRotate(poseBone, xpsBoneData.rotDelta)
    xpsBoneTranslate(poseBone, xpsBoneData.coordDelta)
    xpsBoneScale(poseBone, xpsBoneData.scale)

def xpsBoneRotToEuler(rotDelta):
    return Euler((radians(rotDelta.x), radians(rotDelta.y), radians(rotDelta.z)), 'YXZ')

def vectorTransform(vec):
    return Vector((vec.x, vec.z, -vec.y))

def vectorTransformTranslate(vec):
    return Vector((vec.x, vec.z, -vec.y))

def vectorTransformScale(vec):
    return Vector((vec.x, vec.y, vec.z))

def xpsBoneRotate(poseBone, rotDelta):
    prev_mode = poseBone.rotation_mode
    poseBone.rotation_mode = 'QUATERNION'

    rot = vectorTransform(rotDelta)
    euler = xpsBoneRotToEuler(rot)
    edit_quat = poseBone.bone.matrix_local.to_quaternion()
    delta_quat = euler.to_quaternion()

    poseBone.rotation_quaternion = edit_quat.inverted() @ delta_quat @ edit_quat
    poseBone.rotation_mode = prev_mode

def xpsBoneTranslate(poseBone, coordDelta):
    trans = vectorTransformTranslate(coordDelta)
    edit_quat = poseBone.bone.matrix_local.to_quaternion()
    poseBone.location = edit_quat.inverted() @ trans

def xpsBoneScale(poseBone, scale):
    poseBone.scale = vectorTransformScale(scale)