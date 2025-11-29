from getpass import getuser
from socket import gethostname

from . import bin_ops
from . import xps_const
from . import xps_types
import bpy


def fillPoseString(poseBytes):
    poseLenghtUnround = len(poseBytes)
    poseLenght = bin_ops.roundToMultiple(
        poseLenghtUnround, xps_const.ROUND_MULTIPLE)
    emptyFill = b'0' * (poseLenght - poseLenghtUnround)
    return poseBytes + emptyFill


def getPoseStringLength(poseString):
    return len(poseString)


def bonePoseCount(poseString):
    boneList = poseString.split('\n')
    return len(boneList) - 1