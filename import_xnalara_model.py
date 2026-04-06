import bpy
import copy
import operator
import os
import re
from mathutils import Vector
from . import import_xnalara_pose
from . import read_ascii_xps
from . import read_bin_xps
from . import xps_types
from . import material_creator

rootDir = ''
blenderBoneNames = []
MIN_BONE_LENGTH = 0.005

xpsSettings = None
xpsData = None


def newBoneName():
    """Initialize the bone name list"""
    global blenderBoneNames
    blenderBoneNames = []


def addBoneName(newName):
    """Add bone name to the global list"""
    global blenderBoneNames
    blenderBoneNames.append(newName)


def getBoneName(originalIndex):
    """Get bone name by index"""
    return blenderBoneNames[originalIndex] if originalIndex < len(blenderBoneNames) else None


def coordTransform(coords):
    """Convert coordinate system: XPS Y-up to Blender Z-up"""
    x, y, z = coords
    return (x, -z, y)


def faceTransform(face):
    """Adjust the vertex order of the face to fit Blender"""
    return (face[0], face[2], face[1])


def faceTransformList(faces):
    """Generator: Batch Convert Face Vertex Order"""
    for face in faces:
        yield faceTransform(face)


def uvTransform(uv):
    """Convert UV coordinates"""
    u = uv[0] + xpsSettings.uvDisplX
    v = 1 + xpsSettings.uvDisplY - uv[1]
    return (u, v)


def rangeFloatToByte(floatVal):
    """Convert floating-point numbers to byte values"""
    return int(floatVal * 255) % 256


def rangeByteToFloat(byteVal):
    """Convert byte value to floating-point number"""
    return byteVal / 255


def uvTransformLayers(uvLayers):
    """Convert UV layer coordinates"""
    return [uvTransform(uv) for uv in uvLayers]


def getInputFilename(xpsSettingsAux):
    """Main entry function, executes XPS file import"""
    global xpsSettings
    xpsSettings = xpsSettingsAux

    blenderImportSetup()
    status = xpsImport()
    blenderImportFinalize()
    return status


def blenderImportSetup():
    """Preparation before import: switch to Object Mode and deselect"""
    objectMode()
    bpy.ops.object.select_all(action='DESELECT')


def blenderImportFinalize():
    """Clean up after import: Restore object mode"""
    objectMode()


def objectMode():
    """Switch to Object Mode"""
    if bpy.context.view_layer.objects.active and bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)


def loadXpsFile(filename):
    """Load XPS files, supports multiple formats"""
    try:
        dirpath, file = os.path.split(filename)
        basename, ext = os.path.splitext(file)
        extLower = ext.lower()
        if extLower in ('.mesh', '.xps'):
            return read_bin_xps.readXpsModel(filename)
        elif extLower == '.ascii':
            return read_ascii_xps.readXpsModel(filename)
        else:
            raise ValueError(f"Unsupported file format: {ext}")
    except Exception as e:
        print(f"Failed to load XPS file: {e}")
        return None


def makeMesh(meshFullName):
    """Create a new mesh object"""
    meshData = bpy.data.meshes.new(meshFullName)
    meshObj = bpy.data.objects.new(meshData.name, meshData)
    print(f'Create mesh: {meshFullName}')
    print(f'New mesh = {meshData.name}')
    return meshObj


def linkToCollection(collection, obj):
    """Link the object to the specified collection"""
    collection.objects.link(obj)


def xpsImport():
    """Execute the complete import process for XPS files"""
    global rootDir, xpsData

    print("------------------------------------------------------------")
    print("-----------Execute the XPS Python Importer------------")
    print("------------------------------------------------------------")
    print(f"Import File: {xpsSettings.filename}")

    rootDir, file = os.path.split(xpsSettings.filename)
    print(f'Root Directory: {rootDir}')

    xpsData = loadXpsFile(xpsSettings.filename)
    if not xpsData:
        return '{NONE}'
    if not xpsData.meshes:
        print("Warning: No mesh data found in the XPS file.")
        return '{NONE}'

    fname, _ = os.path.splitext(file)
    newCollection = bpy.data.collections.new(fname)
    viewLayer = bpy.context.view_layer
    activeCollection = viewLayer.active_layer_collection.collection
    activeCollection.children.link(newCollection)

    armatureObj = createArmature()
    if armatureObj:
        linkToCollection(newCollection, armatureObj)
        importBones(armatureObj)
        markSelected(armatureObj)

    meshesObjs = importMeshesList(armatureObj)
    for obj in meshesObjs:
        linkToCollection(newCollection, obj)
        markSelected(obj)

    if armatureObj:
        armatureObj.pose.use_auto_ik = xpsSettings.autoIk
        hideUnusedBones([armatureObj])
        boneTailMiddleObject(armatureObj, xpsSettings.connectBones)

    if xpsSettings.importDefaultPose and armatureObj and xpsData.header and xpsData.header.pose:
        import_xnalara_pose.setXpsPose(armatureObj, xpsData.header.pose)

    return '{FINISHED}'


def setMinimumLength(bone):
    """Set Minimum Bone Length"""
    defaultLength = MIN_BONE_LENGTH
    if bone.length == 0:
        bone.tail = bone.head - Vector((0, .001, 0))
    if bone.length < defaultLength:
        bone.length = defaultLength


def boneTailMiddleObject(armatureObj, connectBones):
    """Adjust the position of the bone's tail and connect it."""
    bpy.context.view_layer.objects.active = armatureObj
    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
    visibility_cache = {b.name: visibleBone(b) for b in armatureObj.data.bones}
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)
    editBones = armatureObj.data.edit_bones
    boneTailMiddle(editBones, connectBones, visibility_cache) 
    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)


def setBoneConnect(connectBones):
    """Set Bone Connection Status"""
    currMode = bpy.context.mode
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)
    editBones = bpy.context.view_layer.objects.active.data.edit_bones
    connectEditBones(editBones, connectBones)
    bpy.ops.object.mode_set(mode=currMode, toggle=False)


def connectEditBones(editBones, connectBones):
    """Connect Bones in Edit Mode"""
    for bone in editBones:
        if bone.parent and bone.head == bone.parent.tail:
            bone.use_connect = connectBones


def hideBonesByName(armatureObjs):
    """Hide bones with names starting with 'unused'."""
    for armature in armatureObjs:
        for bone in armature.data.bones:
            if bone.name.lower().startswith('unused'):
                hideBone(bone)


def hideBonesByVertexGroup(armatureObjs):
    """Hide bones without affecting the mesh."""
    for armature in armatureObjs:
        objs = [obj for obj in armature.children
                if obj.type == 'MESH' and obj.modifiers and any(
                    modif for modif in obj.modifiers if modif and modif.type == 'ARMATURE' and modif.object == armature)]
        vertexGroups = set(vg.name for obj in objs if obj.type == 'MESH' for vg in obj.vertex_groups)
        bones = armature.data.bones
        rootBones = [bone for bone in bones if not bone.parent]

        for bone in rootBones:
            recurBones(bone, vertexGroups, '')


def recurBones(bone, vertexGroups, name):
    """Recursively hide unused bone chains."""
    visibleChild = any(recurBones(childBone, vertexGroups, f'{name} ') for childBone in bone.children)
    visibleChain = bone.name in vertexGroups or visibleChild
    if not visibleChain:
        hideBone(bone)
    return visibleChain


if bpy.app.version < (4, 0):
    def hideBone(bone):
        bone.layers[1] = True
        bone.layers[0] = False

    def showBone(bone):
        bone.layers[0] = True
        bone.layers[1] = False

    def visibleBone(bone):
        return bone.layers[0]
else:
    def _ensureVisibilityBonesCollection(armature):
        col = armature.collections.get("Visible Bones")
        if col is None:
            return armature.collections.new("Visible Bones")
        return col

    def hideBone(bone):
        col = _ensureVisibilityBonesCollection(bone.id_data)
        col.unassign(bone)

    def showBone(bone):
        col = _ensureVisibilityBonesCollection(bone.id_data)
        col.assign(bone)

    def visibleBone(bone):
        col = _ensureVisibilityBonesCollection(bone.id_data)
        return bone.name in col.bones


def showAllBones(armatureObjs):
    """Show All Bones"""
    for armature in armatureObjs:
        for bone in armature.data.bones:
            showBone(bone)


def hideBoneChain(bone):
    """Hide Bones and Their Parent Chains"""
    hideBone(bone)
    if bone.parent:
        hideBoneChain(bone.parent)


def showBoneChain(bone):
    """Display the skeleton and its parent chain."""
    showBone(bone)
    if bone.parent:
        showBoneChain(bone.parent)


def hideUnusedBones(armatureObjs):
    """Hide Unused Bones"""
    hideBonesByVertexGroup(armatureObjs)
    hideBonesByName(armatureObjs)


def boneDictRename(filepath, armatureObj):
    """Rename Bones Using a Dictionary"""
    boneDictRenameData, _ = read_ascii_xps.readBoneDict(filepath)
    renameBonesUsingDict(armatureObj, boneDictRenameData)


def boneDictRestore(filepath, armatureObj):
    """Restore Bone Names"""
    _, boneDictRestoreData = read_ascii_xps.readBoneDict(filepath)
    renameBonesUsingDict(armatureObj, boneDictRestoreData)


def renameBonesUsingDict(armatureObj, boneDict):
    """Rename Bones Based on Dictionary"""
    getBone = armatureObj.data.bones.get
    for key, value in boneDict.items():
        boneRenamed = getBone(import_xnalara_pose.renameBoneToBlender(key))
        if boneRenamed:
            boneRenamed.name = value
        else:
            boneOriginal = getBone(key)
            if boneOriginal:
                boneOriginal.name = value


def createArmature():
    """Create Skeleton Object"""
    bones = xpsData.bones
    if not bones:
        return None
    boneCount = len(bones)
    print(f'Import Skeleton {boneCount} Root Bone')

    armatureData = bpy.data.armatures.new("Armature")
    armatureData.display_type = 'STICK'
    armatureObj = bpy.data.objects.new("Armature", armatureData)
    armatureObj.show_in_front = True
    return armatureObj

def importBones(armatureObj):
    """Import Skeleton Data"""
    bones = xpsData.bones
    bpy.context.view_layer.objects.active = armatureObj

    bpy.ops.object.mode_set(mode='EDIT')
    newBoneName()
    for bone in bones:
        editBone = armatureObj.data.edit_bones.new(bone.name)
        addBoneName(editBone.name)
        editBone.head = Vector(coordTransform(bone.co))
        editBone.tail = editBone.head + Vector((0, 0, -.1))
        setMinimumLength(editBone)

    for bone in bones:
        if bone.parentId >= 0:
            armatureObj.data.edit_bones[bone.id].parent = armatureObj.data.edit_bones[bone.parentId]

    bpy.ops.object.mode_set(mode='OBJECT')

    if bpy.app.version >= (4, 0):
        bonesColl = armatureObj.data.collections.get("Bones") or armatureObj.data.collections.new("Bones")
        visBonesColl = armatureObj.data.collections.get("Visible Bones") or armatureObj.data.collections.new("Visible Bones")

        for b in armatureObj.data.bones:
            bonesColl.assign(b)
            visBonesColl.assign(b)

    markSelected(armatureObj)
    return armatureObj


def boneTailMiddle(editBones, connectBones, visibility_cache=None):
    """
    Optimized bone tail positioning.
    Uses pre-compiled regex and minimizes EditBone property lookups.
    """

    re_twist = re.compile(r'\b(hip)?(twist|ctr|root|adj)\d*\b', re.IGNORECASE)
    
    if visibility_cache is not None:
        bone_visibility = visibility_cache
    else:
        bone_visibility = {b.name: visibleBone(b) for b in editBones}
        
    for bone in editBones:
        b_name_lower = bone.name.lower()
        if b_name_lower == "root ground" or not bone.parent:
            bone.tail = bone.head + Vector((0, -0.5, 0))
            continue

        is_visible = bone_visibility.get(bone.name, True)
        
        if is_visible:
            child_bones = [c for c in bone.children if bone_visibility.get(c.name, True) and not re_twist.search(c.name)]
        else:
            child_bones = [c for c in bone.children if not re_twist.search(c.name)]

        if child_bones:
            sum_vec = Vector((0.0, 0.0, 0.0))
            for cb in child_bones:
                sum_vec += cb.head
            bone.tail = sum_vec / len(child_bones)
        elif bone.parent:
            p_tail = bone.parent.tail
            p_head = bone.parent.head
            delta = (bone.head - p_tail) if bone.head != p_tail else (p_tail - p_head)
            bone.tail = bone.head + delta

    for bone in editBones:
        if bone.length < MIN_BONE_LENGTH:
            if bone.length == 0:
                bone.tail = bone.head - Vector((0, 0.001, 0))
            bone.length = MIN_BONE_LENGTH

    connectEditBones(editBones, connectBones)


def markSelected(obj):
    """Mark the object as selected."""
    obj.select_set(state=True)


def makeUvs(meshData, faces, uvData, vertexColors):
    """
    High-performance UV and Vertex Color assignment using foreach_set.
    Bypasses slow Python loops by writing directly to memory.
    """
    loop_indices = [idx for face in faces for idx in face]
    
    for i in range(len(uvData[0])):
        uv_layer = meshData.uv_layers.new(name=f"UV{i + 1}")
        flat_uvs = [val for idx in loop_indices for val in uvData[idx][i]]
        uv_layer.data.foreach_set("uv", flat_uvs)

    if xpsSettings.vColors and vertexColors:
        v_col = meshData.vertex_colors.new()
        flat_colors = [val for idx in loop_indices for val in vertexColors[idx]]
        v_col.data.foreach_set("color", flat_colors)


def createJoinedMeshes():
    """Merge Mesh Sections"""
    meshPartRegex = re.compile(r'(!.*)*([\d]+nPart)*!')
    sortedMeshesList = sorted(xpsData.meshes, key=operator.attrgetter('name'))
    joinedMeshNames = sorted({meshPartRegex.sub('', mesh.name, 0) for mesh in sortedMeshesList})
    newMeshes = []
    for joinedMeshName in joinedMeshNames:
        meshesToJoin = [mesh for mesh in sortedMeshesList if meshPartRegex.sub('', mesh.name, 0) == joinedMeshName]
        totalVertexCount = 0
        meshName = meshPartRegex.sub('', meshesToJoin[0].name, 0)
        textures = meshesToJoin[0].textures
        uvCount = meshesToJoin[0].uvCount
        vertices = []
        faces = []

        for mesh in meshesToJoin:
            vertexCount = 0
            if len(meshesToJoin) > 1 or meshesToJoin[0] not in sortedMeshesList:
                for vert in mesh.vertices:
                    vertexCount += 1
                    newVertex = xps_types.XpsVertex(
                        vert.id + totalVertexCount, vert.co, vert.norm, vert.vColor, vert.uv, vert.boneWeights)
                    vertices.append(newVertex)
                for face in mesh.faces:
                    newFace = [face[0] + totalVertexCount, face[1] + totalVertexCount, face[2] + totalVertexCount]
                    faces.append(newFace)
            else:
                vertices = mesh.vertices
                faces = mesh.faces
            totalVertexCount += vertexCount

        xpsMesh = xps_types.XpsMesh(meshName, textures, vertices, faces, uvCount)
        newMeshes.append(xpsMesh)
    return newMeshes


def importMeshesList(armatureObj):
    """
    Optimized mesh list import.
    Disables global undo and minimizes UI/Depsgraph updates.
    """
    original_undo = bpy.context.preferences.edit.use_global_undo
    bpy.context.preferences.edit.use_global_undo = False

    meshes = createJoinedMeshes() if xpsSettings.joinMeshParts else xpsData.meshes
    importedMeshes = []
    totalMeshes = len(meshes)

    wm = bpy.context.window_manager
    wm.progress_begin(0, totalMeshes)

    for i, meshInfo in enumerate(meshes): 
        if i % 5 == 0 or i == totalMeshes - 1:
            wm.progress_update(i)
            status_msg = f"XPS Import: {i}/{totalMeshes} meshes..."
            bpy.context.workspace.status_text_set(status_msg)
        
        mesh = importMesh(armatureObj, meshInfo)
        if mesh:
            importedMeshes.append(mesh)

    wm.progress_end()
    bpy.context.view_layer.update()
    bpy.context.preferences.edit.use_global_undo = original_undo
    bpy.context.workspace.status_text_set(None)
    
    return importedMeshes

def generateVertexKey(vertex):
    """Generate Unique Vertex Keys"""
    if xpsSettings.joinMeshRips:
        return (tuple(vertex.co), tuple(vertex.norm))
    return (vertex.id, tuple(vertex.co), tuple(vertex.norm))


def getVertexId(vertex, mapVertexKeys, mergedVertexList):
    """Get the unique ID of a vertex."""
    vertexKey = generateVertexKey(vertex)
    vertexId = mapVertexKeys.get(vertexKey)
    if vertexId is None:
        vertexId = len(mergedVertexList)
        mapVertexKeys[vertexKey] = vertexId
        newVertex = xps_types.XpsVertex(vertexId, vertex.co, vertex.norm, vertex.vColor, vertex.uv, vertex.boneWeights)
        mergedVertexList.append(newVertex)
    else:
        mergedVertexList[vertexId].merged = True
    return vertexId


def makeVertexDict(vertexDict, mergedVertexList, uvLayers, vertexColors, vertices):
    """Create a vertex dictionary and related data."""
    mapVertexKeys = {}
    for vertex in vertices:
        vColor = vertex.vColor
        uvLayers.append(uvTransformLayers(vertex.uv))
        vertexColors.append([rangeByteToFloat(c) for c in vColor])
        vertexId = getVertexId(vertex, mapVertexKeys, mergedVertexList)
        vertexDict.append(vertexId)


def processVertices(meshInfo):
    """Processing Vertex Data"""
    vertexDict = []
    mergedVertexList = []
    uvLayers = []
    vertexColors = []
    makeVertexDict(vertexDict, mergedVertexList, uvLayers, vertexColors, meshInfo.vertices)
    return vertexDict, mergedVertexList, uvLayers, vertexColors


def createFaces(meshData, vertexDict, mergedVertexList, meshInfo, useSeams):
    """Create Mesh Faces"""
    facesData = []
    seamEdgesDict = {}
    mergedVertices = {}
    for face in meshInfo.faces:
        originalIndices = (face[0], face[1], face[2])
        newIndices = (vertexDict[face[0]], vertexDict[face[1]], vertexDict[face[2]])
        facesData.append(newIndices)
        if useSeams and any(mergedVertexList[i].merged for i in newIndices):
            findMergedEdges(seamEdgesDict, vertexDict, mergedVertexList, mergedVertices, originalIndices)

    mergeByNormal = True
    vertices = mergedVertexList if mergeByNormal else meshInfo.vertices
    coords = [coordTransform(vertex.co) for vertex in vertices]
    normals = [coordTransform(Vector(vertex.norm).normalized()) for vertex in vertices]
    faces = list(faceTransformList(facesData if mergeByNormal else meshInfo.faces))

    meshData.from_pydata(coords, [], faces)
    meshData.polygons.foreach_set("use_smooth", [True] * len(meshData.polygons))

    if xpsSettings.markSeams:
        markSeams(meshData, seamEdgesDict)

    del coords, normals
    return faces


def assignUvs(meshData, faces, uvLayers, vertexColors):
    """Assign UVs and Vertex Colors"""
    makeUvs(meshData, faces, uvLayers, vertexColors)


def setupMaterialAndRigging(meshObj, meshInfo, armatureObj):
    """Setting Up Materials and Rigging"""
    flags = xpsData.header.flags if xpsData.header else read_bin_xps.flagsDefault()
    material_creator.makeMaterial(xpsSettings, rootDir, meshObj.data, meshInfo, flags)

    if armatureObj:
        setArmatureModifier(armatureObj, meshObj)
        setParent(armatureObj, meshObj)
        if armatureObj.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        makeVertexGroups(meshObj, meshInfo.vertices)
        makeBoneGroups(armatureObj, meshObj)


def importMesh(armatureObj, meshInfo):
    """
    Optimized importMesh: Silent mode.
    Removed UI status updates to prevent thread locking.
    """
    useSeams = xpsSettings.markSeams
    meshFullName = meshInfo.name
    vertexCount = len(meshInfo.vertices)
    
    if vertexCount < 3:
        print(f"Warning: {meshFullName} has insufficient vertices, skipping mesh creation.")
        return None

    meshObj = makeMesh(meshFullName)
    meshData = meshObj.data

    vertexDict, mergedVertexList, uvLayers, vertexColors = processVertices(meshInfo)
    originalFaces = list(faceTransformList(meshInfo.faces))
    faces = createFaces(meshData, vertexDict, mergedVertexList, meshInfo, useSeams)
    assignUvs(meshData, originalFaces, uvLayers, vertexColors)
    setupMaterialAndRigging(meshObj, meshInfo, armatureObj)


    if xpsSettings.importNormals and not hasattr(xpsSettings, 'skipNormals'):
        normals = [coordTransform(Vector(v.norm).normalized()) for v in mergedVertexList]
        meshData.normals_split_custom_set_from_vertices(normals)
    
    meshData.validate(clean_customdata=False)

    return meshObj


def markSeams(meshData, seamEdgesDict):
    """Mark Stitching Edges"""
    edgeKeys = {val: index for index, val in enumerate(meshData.edge_keys)}
    for vert1, vertList in seamEdgesDict.items():
        for vert2 in vertList:
            edgeIdx = edgeKeys.get((vert1, vert2)) if vert1 < vert2 else edgeKeys.get((vert2, vert1))
            if edgeIdx is not None:
                meshData.edges[edgeIdx].use_seam = True


def findMergedEdges(seamEdgesDict, vertexDict, mergedVertexList, mergedVertices, originalFace):
    """Find the vertices of merged edges."""
    for vertexIndex in originalFace:
        findMergedVert(seamEdgesDict, vertexDict, mergedVertexList, mergedVertices, originalFace, vertexIndex)


def findMergedVert(seamEdgesDict, vertexDict, mergedVertexList, mergedVertices, originalFace, mergedVertexIndex):
    """Handling Merged Vertices"""
    v1, v2, v3 = originalFace
    vertX = vertexDict[mergedVertexIndex]
    if mergedVertexList[vertX].merged:
        if vertX not in mergedVertices:
            mergedVertices[vertX] = []
        for faceList in mergedVertices[vertX]:
            for i, faceVertex in enumerate(faceList):
                if vertX == vertexDict[faceVertex] and mergedVertexIndex != faceVertex:
                    if mergedVertexIndex != v1:
                        checkEdgePairForSeam(i, seamEdgesDict, vertexDict, vertX, v1, faceList)
                    if mergedVertexIndex != v2:
                        checkEdgePairForSeam(i, seamEdgesDict, vertexDict, vertX, v2, faceList)
                    if mergedVertexIndex != v3:
                        checkEdgePairForSeam(i, seamEdgesDict, vertexDict, vertX, v3, faceList)
        mergedVertices[vertX].append((v1, v2, v3))


def checkEdgePairForSeam(i, seamEdgesDict, vertexDict, mergedVertex, vertexIndex, faceList):
    """Check whether the edge pair requires stitching."""
    for j in range(3):
        if i != j:
            makeSeamEdgeDict(j, seamEdgesDict, vertexDict, mergedVertex, vertexIndex, faceList)


def makeSeamEdgeDict(i, seamEdgesDict, vertexDict, mergedVertex, vertexIndex, faceList):
    """Generate Stitch Edge Dictionary"""
    if vertexDict[vertexIndex] == vertexDict[faceList[i]]:
        seamEdgesDict.setdefault(mergedVertex, []).append(vertexDict[vertexIndex])


def setArmatureModifier(armatureObj, meshObj):
    """Set Up Bone Modifiers"""
    mod = meshObj.modifiers.new(type="ARMATURE", name="Armature")
    mod.use_vertex_groups = True
    mod.object = armatureObj


def setParent(armatureObj, meshObj):
    """Set Parent Object"""
    meshObj.parent = armatureObj


def makeVertexGroups(meshObj, vertices):
    """
    Final Optimized Vertex Group assignment.
    Groups indices by bone name AND weight to maximize batch efficiency.
    Eliminates the per-vertex Python loop bottleneck.
    """
    armature = meshObj.find_armature()
    if not armature:
        return

    bone_map = {}
    
    for vert in vertices:
        for bw in vert.boneWeights:
            if bw.weight > 0.0001:  
                b_name = getBoneName(bw.id)
                if b_name:
                    if b_name not in bone_map:
                        bone_map[b_name] = {}

                    w_key = round(bw.weight, 4)
                    if w_key not in bone_map[b_name]:
                        bone_map[b_name][w_key] = []
                    
                    bone_map[b_name][w_key].append(vert.id)

    for b_name, weights_dict in bone_map.items():
        vg = meshObj.vertex_groups.get(b_name) or meshObj.vertex_groups.new(name=b_name)
        
        for w_val, indices in weights_dict.items():
            vg.add(indices, w_val, 'REPLACE')


def assignVertexGroup(vertex, armature, meshObj):
    """
    Deprecated: Logic moved to batch processing in makeVertexGroups
    to prevent performance bottlenecks in high-poly models.
    """
    pass


def makeBoneGroups(armatureObj, meshObj):
    """Create a bone group and set the color."""
    if armatureObj.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    surfaceColor = material_creator.randomColor()
    selectColor = material_creator.randomColor()
    activeColor = material_creator.randomColor()

    if bpy.app.version < (4, 0):
        boneGroup = armatureObj.pose.bone_groups.new(name=meshObj.name)
        boneGroup.color_set = 'CUSTOM'
        boneGroup.colors.normal = surfaceColor
        boneGroup.colors.select = selectColor
        boneGroup.colors.active = activeColor
        
        for boneName in meshObj.vertex_groups.keys():
            if boneName in armatureObj.pose.bones:
                armatureObj.pose.bones[boneName].bone_group = boneGroup
    else:
        bColl = armatureObj.data.collections.get(meshObj.name) or armatureObj.data.collections.new(name=meshObj.name)
        
        for boneName in meshObj.vertex_groups.keys():
            if boneName in armatureObj.pose.bones:
                pBone = armatureObj.pose.bones[boneName]
                bColl.assign(pBone) 
                pBone.color.palette = 'CUSTOM'
                pBone.color.custom.normal = surfaceColor
                pBone.color.custom.select = selectColor
                pBone.color.custom.active = activeColor