import io
import ntpath

from . import bin_ops
from . import read_ascii_xps
from . import xps_const
from . import xps_types


def flagName(flag):
    flagList = {
        0: xps_const.BACK_FACE_CULLING,
        1: xps_const.ALWAYS_FORCE_CULLING,
        2: xps_const.MODEL_CAST_SHADOWS,
        3: xps_const.TANGENT_SPACE_RED,
        4: xps_const.TANGENT_SPACE_GREEN,
        5: xps_const.TANGENT_SPACE_BLUE,
        6: xps_const.GLOSS,
        7: xps_const.HAS_BONE_DIRECTIONS,
    }
    return flagList.get(flag, flag)


def flagsDefault():
    flags = {
        xps_const.BACK_FACE_CULLING: False,
        xps_const.ALWAYS_FORCE_CULLING: False,
        xps_const.MODEL_CAST_SHADOWS: True,
        xps_const.TANGENT_SPACE_RED: 0,  # Straight X channel
        xps_const.TANGENT_SPACE_GREEN: 1,  # Invert Y channel
        xps_const.TANGENT_SPACE_BLUE: 0,  # Straight Z channel
        xps_const.GLOSS: 10,
        xps_const.HAS_BONE_DIRECTIONS: False,
    }
    return flags


def flagValue(flag, value):
    # Flags
    # 00: Backface culling
    # 01: Always force culling
    # 02: Model cast shadows
    # 06: Save current bump specular gloss

    if flag in (0, 1, 2, 6, 7):
        return bool(value)
    # Flags
    # 03: X space
    # 04: Y space
    # 05: Z space
    elif flag in (3, 4, 5):
        return (value % 2)
    else:
        return value


def intToCoords(flag):
    flagValue = {
        0: '+',
        1: '-',
    }
    return flagValue.get(flag, 'Uk')


def printNormalMapSwizzel(tangentSpaceRed, tangentSpaceGreen, tangentSpaceBlue):
    # Default XPS NormalMapTangentSpace == 0 1 0 == X+ Y- Z+
    print('Tangent Space Normal Map Swizzel Coordinates:')
    print('X{} Y{} Z{}'.format(intToCoords(tangentSpaceRed), intToCoords(tangentSpaceGreen), intToCoords(tangentSpaceBlue)))
    print('')


def readFilesString(file):
    try:
        lengthByte2 = 0

        lengthByte1 = bin_ops.readByte(file)
        if lengthByte1 is None:
            return ""

        if (lengthByte1 >= xps_const.LIMIT):
            lengthByte2 = bin_ops.readByte(file)
            if lengthByte2 is None:
                return ""
        length = (lengthByte1 % xps_const.LIMIT) + (lengthByte2 * xps_const.LIMIT)

        string = bin_ops.readString(file, length)
        return string or ""
    except Exception as e:
        print(f"Error reading string: {e}")
        return ""


def readVertexColor(file):
    try:
        r = bin_ops.readByte(file) or 255
        g = bin_ops.readByte(file) or 255
        b = bin_ops.readByte(file) or 255
        a = bin_ops.readByte(file) or 255
        vertexColor = [r, g, b, a]
        return vertexColor
    except Exception as e:
        print(f"Error reading vertex color: {e}")
        return [255, 255, 255, 255]


def readUvVert(file):
    try:
        x = bin_ops.readSingle(file) or 0.0  # X pos
        y = bin_ops.readSingle(file) or 0.0  # Y pos
        coords = [x, y]
        return coords
    except Exception as e:
        print(f"Error reading UV vertex: {e}")
        return [0.0, 0.0]


def readXYZ(file):
    try:
        x = bin_ops.readSingle(file) or 0.0  # X pos
        y = bin_ops.readSingle(file) or 0.0  # Y pos
        z = bin_ops.readSingle(file) or 0.0  # Z pos
        coords = [x, y, z]
        return coords
    except Exception as e:
        print(f"Error reading XYZ coordinates: {e}")
        return [0.0, 0.0, 0.0]


def read4Float(file):
    try:
        x = bin_ops.readSingle(file) or 0.0
        y = bin_ops.readSingle(file) or 0.0
        z = bin_ops.readSingle(file) or 0.0
        w = bin_ops.readSingle(file) or 0.0
        coords = [x, y, z, w]
        return coords
    except Exception as e:
        print(f"Error reading 4 floats: {e}")
        return [0.0, 0.0, 0.0, 0.0]


def read4Int16(file):
    try:
        r = bin_ops.readInt16(file) or 0
        g = bin_ops.readInt16(file) or 0
        b = bin_ops.readInt16(file) or 0
        a = bin_ops.readInt16(file) or 0
        vertexColor = [r, g, b, a]
        return vertexColor
    except Exception as e:
        print(f"Error reading 4 int16: {e}")
        return [0, 0, 0, 0]


def readTriIdxs(file):
    try:
        face1 = bin_ops.readUInt32(file) or 0
        face2 = bin_ops.readUInt32(file) or 0
        face3 = bin_ops.readUInt32(file) or 0
        faceLoop = [face1, face2, face3]
        return faceLoop
    except Exception as e:
        print(f"Error reading triangle indices: {e}")
        return [0, 0, 0]


def readHeader(file):
    xpsHeader = xps_types.XpsHeader()
    flags = flagsDefault()

    try:
        # MagicNumber
        magic_number = bin_ops.readUInt32(file)
        if magic_number != xps_const.MAGIC_NUMBER:
            print(f"Warning: Invalid magic number: {magic_number}")
            return None
            
        # XPS Version
        version_mayor = bin_ops.readUInt16(file) or 0
        version_minor = bin_ops.readUInt16(file) or 0
        # XNAaral Name
        xna_aral = readFilesString(file)
        # Settings Length
        settingsLen = bin_ops.readUInt32(file) or 0
        # MachineName
        machineName = readFilesString(file)
        # UserName
        userName = readFilesString(file)
        # File-->File
        filesString = readFilesString(file)
        xpsPoseData = None

        # print('*'*80)
        hasTangent = bin_ops.hasTangentVersion(version_mayor, version_minor)
        if (hasTangent):
            # print('OLD Format')
            settingsStream = io.BytesIO(file.read(settingsLen * 4))
        else:
            # print('NEW Format')
            valuesRead = 0
            hash = bin_ops.readUInt32(file) or 0
            valuesRead += 1 * 4
            items = bin_ops.readUInt32(file) or 0
            valuesRead += 1 * 4
            # print('hash', hash)
            # print('items', items)
            for i in range(items):
                # print('valuesRead', valuesRead)
                optType = bin_ops.readUInt32(file) or 0
                valuesRead += 1 * 4
                optcount = bin_ops.readUInt32(file) or 0
                valuesRead += 1 * 4
                optInfo = bin_ops.readUInt32(file) or 0
                valuesRead += 1 * 4

                # print('------')
                # print('count',i)
                # print('optType',optType)
                # print('optcount',optcount)
                # print('optInfo',optInfo)

                if (optType == 0):
                    # print('Read None')
                    readNone(file, optcount)
                    valuesRead += optcount * 2
                elif (optType == 1):
                    # print('Read Pose')
                    xpsPoseData = readDefaultPose(file, optcount, optInfo)
                    readCount = bin_ops.roundToMultiple(optcount, xps_const.ROUND_MULTIPLE)
                    valuesRead += readCount
                elif (optType == 2):
                    # print('Read Flags')
                    flags = readFlags(file, optcount)
                    valuesRead += optcount * 2 * 4
                else:
                    # print('Read Waste')
                    loopStart = valuesRead // 4
                    loopFinish = settingsLen
                    # print (loopStart, loopFinish)
                    for j in range(loopStart, loopFinish):
                        # print('waste',j - loopStart)
                        waste = bin_ops.readUInt32(file)

        xpsHeader.magic_number = magic_number
        xpsHeader.version_mayor = version_mayor
        xpsHeader.version_minor = version_minor
        xpsHeader.xna_aral = xna_aral
        xpsHeader.settingsLen = settingsLen
        xpsHeader.machine = machineName
        xpsHeader.user = userName
        xpsHeader.files = filesString
        xpsHeader.pose = xpsPoseData
        xpsHeader.flags = flags
        return xpsHeader
    except Exception as e:
        print(f"Error reading header: {e}")
        return None


def findHeader(file):
    header = None

    try:
        # Check for MAGIC_NUMBER
        number = bin_ops.readUInt32(file)
        file.seek(0)

        if (number == xps_const.MAGIC_NUMBER):
            print('Header Found')
            header = readHeader(file)
        else:
            print(f"Warning: Invalid magic number, expected {xps_const.MAGIC_NUMBER}, got {number}")

        # logHeader(header)
        return header
    except Exception as e:
        print(f"Error finding header: {e}")
        return None


def readNone(file, optcount):
    try:
        for i in range(optcount):
            waste = bin_ops.readUInt32(file)
    except Exception as e:
        print(f"Error reading none data: {e}")


def readFlags(file, optcount):
    flags = flagsDefault()
    try:
        for i in range(optcount):
            flag = bin_ops.readUInt32(file) or 0
            value = bin_ops.readUInt32(file) or 0
            flag_name = flagName(flag)
            if flag_name in flags:
                flags[flag_name] = flagValue(flag, value)
        printNormalMapSwizzel(flags.get(xps_const.TANGENT_SPACE_RED, 0), 
                             flags.get(xps_const.TANGENT_SPACE_GREEN, 1), 
                             flags.get(xps_const.TANGENT_SPACE_BLUE, 0))
        return flags
    except Exception as e:
        print(f"Error reading flags: {e}")
        return flagsDefault()


def logHeader(xpsHeader):
    if not xpsHeader:
        print("No header found")
        return
        
    print("MAGIX:", xpsHeader.magic_number)
    print('VER MAYOR:', xpsHeader.version_mayor)
    print('VER MINOR:', xpsHeader.version_minor)
    print('NAME:', xpsHeader.xna_aral)
    print('SETTINGS LEN:', xpsHeader.settingsLen)
    print('MACHINE:', xpsHeader.machine)
    print('USR:', xpsHeader.user)
    print('FILES:', xpsHeader.files)
    print('SETTING:', xpsHeader.settings)
    print('DEFAULT POSE:', xpsHeader.pose)


def readBones(file, header):
    bones = []
    try:
        # Bone Count
        boneCount = bin_ops.readUInt32(file) or 0

        for boneId in range(boneCount):
            boneName = readFilesString(file)
            if not boneName:
                boneName = f"Bone_{boneId}"
            parentId = bin_ops.readInt16(file) or -1
            coords = readXYZ(file)

            xpsBone = xps_types.XpsBone(boneId, boneName, coords, parentId)
            bones.append(xpsBone)
        return bones
    except Exception as e:
        print(f"Error reading bones: {e}")
        return []


def readMeshes(file, xpsHeader, hasBones):
    meshes = []
    try:
        meshCount = bin_ops.readUInt32(file) or 0

        hasHeader = bool(xpsHeader)

        verMayor = xpsHeader.version_mayor if hasHeader else 0
        verMinor = xpsHeader.version_minor if hasHeader else 0

        hasTangent = bin_ops.hasTangentVersion(verMayor, verMinor, hasHeader)
        hasVariableWeights = bin_ops.hasVariableWeights(verMayor, verMinor, hasHeader)

        for meshId in range(meshCount):
            try:
                # Name
                meshName = readFilesString(file)
                if not meshName:
                    meshName = f'Mesh_{meshId}'
                # print('Mesh Name:', meshName)
                # uv Count
                uvLayerCount = bin_ops.readUInt32(file) or 0
                # Textures
                textures = []
                textureCount = bin_ops.readUInt32(file) or 0
                for texId in range(textureCount):
                    try:
                        textureFile = ntpath.basename(readFilesString(file))
                        if not textureFile:
                            textureFile = f"texture_{texId}.dds"
                        # print('Texture file', textureFile)
                        uvLayerId = bin_ops.readUInt32(file) or 0

                        xpsTexture = xps_types.XpsTexture(texId, textureFile, uvLayerId)
                        textures.append(xpsTexture)
                    except Exception as e:
                        print(f"Error reading texture {texId}: {e}")
                        continue

                # Vertices
                vertex = []
                vertexCount = bin_ops.readUInt32(file) or 0

                for vertexId in range(vertexCount):
                    try:
                        coord = readXYZ(file)
                        normal = readXYZ(file)
                        vertexColor = readVertexColor(file)

                        uvs = []
                        for uvLayerId in range(uvLayerCount):
                            uvVert = readUvVert(file)
                            uvs.append(uvVert)
                            if hasTangent:
                                tangent = read4Float(file)

                        boneWeights = []
                        if hasBones:
                            # if cero bones dont have weights to read

                            boneIdx = []
                            boneWeight = []
                            if hasVariableWeights:
                                weightsCount = bin_ops.readInt16(file) or 0
                            else:
                                weightsCount = 4

                            for x in range(weightsCount):
                                bone_id = bin_ops.readInt16(file) or 0
                                boneIdx.append(bone_id)
                            for x in range(weightsCount):
                                weight = bin_ops.readSingle(file) or 0.0
                                boneWeight.append(weight)

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
                triCount = bin_ops.readUInt32(file) or 0
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
                print(f"Error reading mesh {meshId}: {e}")
                continue
        return meshes
    except Exception as e:
        print(f"Error reading meshes: {e}")
        return []


def readIoStream(filename):
    try:
        with open(filename, "rb") as a_file:
            ioStream = io.BytesIO(a_file.read())
        return ioStream
    except Exception as e:
        print(f"Error opening file {filename}: {e}")
        return None


def readXpsModel(filename):
    print('File:', filename)

    try:
        ioStream = readIoStream(filename)
        if not ioStream:
            return xps_types.XpsData(None, [], [])
            
        print('Reading Header')
        xpsHeader = findHeader(ioStream)
        print('Reading Bones')
        bones = readBones(ioStream, xpsHeader)
        hasBones = bool(bones)
        print('Read', len(bones), 'Bones')
        print('Reading Meshes')
        meshes = readMeshes(ioStream, xpsHeader, hasBones)
        print('Read', len(meshes), 'Meshes')

        xpsData = xps_types.XpsData(xpsHeader, bones, meshes)
        return xpsData
    except Exception as e:
        print(f"Error reading XPS model {filename}: {e}")
        return xps_types.XpsData(None, [], [])


def readDefaultPose(file, poseLenghtUnround, poseBones):
    try:
        # print('Import Pose')
        poseBytes = b''
        if poseLenghtUnround and poseBones > 0:
            for i in range(0, poseBones):
                line = file.readline()
                if line:
                    poseBytes += line

        poseLenght = bin_ops.roundToMultiple(
            poseLenghtUnround, xps_const.ROUND_MULTIPLE)
        emptyBytes = poseLenght - poseLenghtUnround
        if emptyBytes > 0:
            file.read(emptyBytes)
        poseString = bin_ops.decodeBytes(poseBytes)
        bonesPose = read_ascii_xps.poseData(poseString)
        return bonesPose
    except Exception as e:
        print(f"Error reading default pose: {e}")
        return None


if __name__ == "__main__":
    readfilename = r'G:\3DModeling\XNALara\XNALara_XPS\Young Samus\Generic_Item.mesh'

    print('----READ START----')
    xpsData = readXpsModel(readfilename)
    print('----READ END----')