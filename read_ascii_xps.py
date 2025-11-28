import io
import ntpath

from . import ascii_ops
from . import xps_const
from . import xps_types

from mathutils import Vector


def readUvVert(file):
    line = ascii_ops.readline(file)
    if not line:
        return [0.0, 0.0]
    values = ascii_ops.splitValues(line)
    if len(values) < 2:
        return [0.0, 0.0]
    x = (ascii_ops.getFloat(values[0]))  # X pos
    y = (ascii_ops.getFloat(values[1]))  # Y pos
    coords = [x, y]
    return coords


def readXYZ(file):
    line = ascii_ops.readline(file)
    if not line:
        return [0.0, 0.0, 0.0]
    values = ascii_ops.splitValues(line)
    if len(values) < 3:
        return [0.0, 0.0, 0.0]
    x = (ascii_ops.getFloat(values[0]))  # X pos
    y = (ascii_ops.getFloat(values[1]))  # Y pos
    z = (ascii_ops.getFloat(values[2]))  # Z pos
    coords = [x, y, z]
    return coords


def fillArray(array, minLen, value):
    # Complete the array with selected value
    filled = array + [value] * (minLen - len(array))
    return filled


def read4Float(file):
    line = ascii_ops.readline(file)
    if not line:
        return [0.0, 0.0, 0.0, 0.0]
    values = ascii_ops.splitValues(line)
    values = fillArray(values, 4, 0)
    x = (ascii_ops.getFloat(values[0]))
    y = (ascii_ops.getFloat(values[1]))
    z = (ascii_ops.getFloat(values[2]))
    w = (ascii_ops.getFloat(values[3]))
    coords = [x, y, z, w]
    return coords


def readBoneWeight(file):
    line = ascii_ops.readline(file)
    if not line:
        return [0.0, 0.0, 0.0, 0.0]
    values = ascii_ops.splitValues(line)
    values = fillArray(values, 4, 0)
    weights = [ascii_ops.getFloat(val) for val in values]
    return weights


def readBoneId(file):
    line = ascii_ops.readline(file)
    if not line:
        return [0, 0, 0, 0]
    values = ascii_ops.splitValues(line)
    values = fillArray(values, 4, 0)
    ids = [ascii_ops.getInt(val) for val in values]
    return ids


def read4Int(file):
    line = ascii_ops.readline(file)
    if not line:
        return [255, 255, 255, 255]
    values = ascii_ops.splitValues(line)
    values = fillArray(values, 4, 0)
    r = ascii_ops.getInt(values[0])
    g = ascii_ops.getInt(values[1])
    b = ascii_ops.getInt(values[2])
    a = ascii_ops.getInt(values[3])
    vertexColor = [r, g, b, a]
    return vertexColor


def readTriIdxs(file):
    line = ascii_ops.readline(file)
    if not line:
        return [0, 0, 0]
    values = ascii_ops.splitValues(line)
    if len(values) < 3:
        return [0, 0, 0]
    face1 = ascii_ops.getInt(values[0])
    face2 = ascii_ops.getInt(values[1])
    face3 = ascii_ops.getInt(values[2])
    faceLoop = [face1, face2, face3]
    return faceLoop


def readBones(file):
    bones = []
    try:
        # Bone Count
        boneCount = ascii_ops.readInt(file)
        if boneCount is None or boneCount < 0:
            return bones
            
        for boneId in range(boneCount):
            boneName = ascii_ops.readString(file)
            if boneName is None:
                boneName = f"Bone_{boneId}"
            parentId = ascii_ops.readInt(file)
            if parentId is None:
                parentId = -1
            coords = readXYZ(file)

            xpsBone = xps_types.XpsBone(boneId, boneName, coords, parentId)
            bones.append(xpsBone)
    except Exception as e:
        print(f"Error reading bones: {e}")
    return bones


def readMeshes(file, hasBones):
    meshes = []
    try:
        meshCount = ascii_ops.readInt(file)
        if meshCount is None or meshCount < 0:
            return meshes

        for meshId in range(meshCount):
            # Name
            meshName = ascii_ops.readString(file)
            if not meshName:
                meshName = f'Mesh_{meshId}'
            # print('Mesh Name:', meshName)
            
            # uv Count
            uvLayerCount = ascii_ops.readInt(file)
            if uvLayerCount is None or uvLayerCount < 0:
                uvLayerCount = 0

            # Textures
            textures = []
            textureCount = ascii_ops.readInt(file)
            if textureCount is None or textureCount < 0:
                textureCount = 0
                
            for texId in range(textureCount):
                try:
                    textureFile = ntpath.basename(ascii_ops.readString(file))
                    if not textureFile:
                        textureFile = f"texture_{texId}.dds"
                    # print('Texture file', textureFile)
                    uvLayerId = ascii_ops.readInt(file)
                    if uvLayerId is None:
                        uvLayerId = 0

                    xpsTexture = xps_types.XpsTexture(texId, textureFile, uvLayerId)
                    textures.append(xpsTexture)
                except Exception as e:
                    print(f"Error reading texture {texId}: {e}")
                    continue

            # Vertices
            vertex = []
            vertexCount = ascii_ops.readInt(file)
            if vertexCount is None or vertexCount < 0:
                vertexCount = 0
                
            for vertexId in range(vertexCount):
                try:
                    coord = readXYZ(file)
                    normal = readXYZ(file)
                    vertexColor = read4Int(file)

                    uvs = []
                    for uvLayerId in range(uvLayerCount):
                        uvVert = readUvVert(file)
                        uvs.append(uvVert)
                        # if ????
                        # tangent????
                        # tangent = read4float(file)

                    boneWeights = []
                    if hasBones:
                        # if cero bones dont have weights to read
                        boneIdx = readBoneId(file)
                        boneWeight = readBoneWeight(file)

                        for idx in range(len(boneIdx)):
                            boneWeights.append(
                                xps_types.BoneWeight(boneIdx[idx], boneWeight[idx]))
                    xpsVertex = xps_types.XpsVertex(
                        vertexId, coord, normal, vertexColor, uvs, boneWeights)
                    vertex.append(xpsVertex)
                except Exception as e:
                    print(f"Error reading vertex {vertexId}: {e}")
                    continue

            # Faces
            faces = []
            triCount = ascii_ops.readInt(file)
            if triCount is None or triCount < 0:
                triCount = 0
                
            for i in range(triCount):
                try:
                    triIdxs = readTriIdxs(file)
                    faces.append(triIdxs)
                except Exception as e:
                    print(f"Error reading face {i}: {e}")
                    continue
                    
            xpsMesh = xps_types.XpsMesh(
                meshName, textures, vertex, faces, uvLayerCount)
            meshes.append(xpsMesh)
    except Exception as e:
        print(f"Error reading meshes: {e}")
    return meshes


def readPoseFile(file):
    try:
        return file.read()
    except Exception as e:
        print(f"Error reading pose file: {e}")
        return ""


def poseData(string):
    poseData = {}
    try:
        poseList = string.split('\n')
        for bonePose in poseList:
            if bonePose and ':' in bonePose:
                pose = bonePose.split(':')
                if len(pose) < 2:
                    continue

                boneName = pose[0].strip()
                if not boneName:
                    continue
                    
                dataList = fillArray(pose[1].split(), 9, 1)
                try:
                    rotDelta = Vector((
                        ascii_ops.getFloat(dataList[0]),
                        ascii_ops.getFloat(dataList[1]),
                        ascii_ops.getFloat(dataList[2])))
                    coordDelta = Vector((
                        ascii_ops.getFloat(dataList[3]),
                        ascii_ops.getFloat(dataList[4]),
                        ascii_ops.getFloat(dataList[5])))
                    scale = Vector((
                        ascii_ops.getFloat(dataList[6]),
                        ascii_ops.getFloat(dataList[7]),
                        ascii_ops.getFloat(dataList[8])))

                    bonePose = xps_types.XpsBonePose(
                        boneName, coordDelta, rotDelta, scale)
                    poseData[boneName] = bonePose
                except Exception as e:
                    print(f"Error parsing pose data for bone {boneName}: {e}")
                    continue
    except Exception as e:
        print(f"Error processing pose data: {e}")
    return poseData


def boneDictData(string):
    boneDictRename = {}
    boneDictRestore = {}
    try:
        poseList = string.split('\n')
        for bonePose in poseList:
            if bonePose and ';' in bonePose:
                pose = bonePose.split(';')
                if len(pose) == 2:
                    oldName, newName = pose
                    oldName = oldName.strip()
                    newName = newName.strip()
                    if oldName and newName:
                        boneDictRename[oldName] = newName
                        boneDictRestore[newName] = oldName
    except Exception as e:
        print(f"Error processing bone dictionary: {e}")
    return boneDictRename, boneDictRestore


def readIoStream(filename):
    try:
        with open(filename, "r", encoding=xps_const.ENCODING_READ) as a_file:
            content = a_file.read()
        return io.StringIO(content)
    except UnicodeDecodeError:
        # Try with different encoding if default fails
        try:
            with open(filename, "r", encoding='utf-8') as a_file:
                content = a_file.read()
            return io.StringIO(content)
        except Exception as e:
            print(f"Error reading file {filename}: {e}")
            return io.StringIO("")
    except Exception as e:
        print(f"Error opening file {filename}: {e}")
        return io.StringIO("")


def readXpsModel(filename):
    try:
        ioStream = readIoStream(filename)
        if not ioStream:
            return xps_types.XpsData(bones=[], meshes=[])
            
        # print('Reading Header')
        # xpsHeader = readHeader(ioStream)
        print('Reading Bones')
        bones = readBones(ioStream)
        hasBones = bool(bones)
        print('Reading Meshes')
        meshes = readMeshes(ioStream, hasBones)
        xpsModelData = xps_types.XpsData(bones=bones, meshes=meshes)
        return xpsModelData
    except Exception as e:
        print(f"Error reading XPS model {filename}: {e}")
        return xps_types.XpsData(bones=[], meshes=[])


def readXpsPose(filename):
    try:
        ioStream = readIoStream(filename)
        if not ioStream:
            return {}
        # print('Import Pose')
        poseString = readPoseFile(ioStream)
        bonesPose = poseData(poseString)
        return bonesPose
    except Exception as e:
        print(f"Error reading XPS pose {filename}: {e}")
        return {}


def readBoneDict(filename):
    try:
        ioStream = readIoStream(filename)
        if not ioStream:
            return {}, {}
        boneDictString = readPoseFile(ioStream)
        boneDictRename, boneDictRestore = boneDictData(boneDictString)
        return boneDictRename, boneDictRestore
    except Exception as e:
        print(f"Error reading bone dictionary {filename}: {e}")
        return {}, {}
