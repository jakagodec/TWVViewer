"""
Created on 14. mar. 2016

@author: Pinceta
"""
from ctypes import *
import numpy as np

'''
// Received from Dusan , 8.4.2014

interface

uses Windows;

const
// video ID and version constants
  VIDEO_ID                = $1A57;         // Aresis Tweez video ID (derived from Aresis USB VID)
  VIDEO_VERSION           = 20;            // version 2.0 (proprietary format)

// video authorization constants
  VIDEO_LICENCE_NOT_VALID = 0;
  VIDEO_LICENCE_VALID     = 1;

// video frame data constants
  FRAME_DATA_NOT_INCLUDED = 0;             // no image data - only headers
  FRAME_DATA_INCLUDED     = 1;             // complete video stream


type

(*** Tweez 250si video structures ***)
*
'''

TW250_DSP_LOG_TRAPS = 4


class TArFrameROI(Structure):
    _pack_ = 1
    _fields_ = [('Left', c_uint16),
                ('Top', c_uint16),
                ('Width', c_uint16),
                ('Height', c_uint16)
                ]


class TArFrameData(Structure):
    _pack_ = 1
    _fields_ = [('HeaderSize', c_uint16),
                ('FrameDataIncl', c_uint16),
                ('ROI', TArFrameROI),
                ('BytesPerPixel', c_uint16),
                ('FrameRate', c_double),
                ('Exposure', c_double),
                ('Gain', c_double),
                ('RecTrapDataNo', c_uint16),
                ]


class TArCalibrationData(Structure):
    _pack_ = 1
    _fields_ = [('ImageToSampleScale', c_float)
                ]


class TArVideoHeader(Structure):
    _pack_ = 1
    _fields_ = [('VideoID', c_uint16),
                ('VideoVersion', c_uint16),
                ('VideoLicence', c_uint16),
                ('VideoHeaderSize', c_uint32),
                ('RecordedFrames', c_uint32),
                ('FrameData', TArFrameData),
                ('CalibrationData', TArCalibrationData)
                ]


class TArTrapData(Structure):
    _fields_ = [('PositionX', c_float),
                ('PositionY', c_float),
                ('Intensity', c_float)
                ]


class TArFrameHeader(Structure):
    _pack_ = 1
    _fields_ = [('FrameNumber', c_uint32),
                ('FrameTime', c_float),
                ('LaserPower', c_float),
                ('CalibrationData1', TArTrapData),
                ('CalibrationData2', TArTrapData),
                ('CalibrationData3', TArTrapData),
                ('CalibrationData4', TArTrapData)
                ]


def display_attr(obj):
    for field_name, field_type in obj._fields_:
        print(field_name, getattr(obj, field_name))


class TwvVideo(object):
    def __init__(self, fname=''):
        # open file
        self.f = open(fname, 'rb')

        # create ctype structures
        self.videoHeader = TArVideoHeader()
        self.frameHeader = TArFrameHeader()
        self.frameData = TArFrameData()
        self.frameROI = TArFrameROI()

        # read headers
        self.f.readinto(self.videoHeader)
        self.videoHeaderSize = getattr(self.videoHeader, 'VideoHeaderSize')
        self.recordedFrames = getattr(self.videoHeader, 'RecordedFrames')
        self.frameData = getattr(self.videoHeader, 'FrameData')
        self.frameROI = getattr(self.frameData, 'ROI')

        # save important data from headers
        self.frameHeaderSize = getattr(self.frameData, 'HeaderSize')
        self.imageW = getattr(self.frameROI, 'Width')
        self.imageH = getattr(self.frameROI, 'Height')
        self.imageSize = self.imageW * self.imageH

    def _framePosition(self, num=0):
        """ Calculate the beginning of desired frame in file

        :param num: frame number
        :return: int: pointer position
        """
        if isinstance(num, int):
            if num < 0 or num >= self.recordedFrames:
                raise IndexError('list index out of range')
            else:
                return self.videoHeaderSize + num * (self.frameHeaderSize + self.imageSize)
        else:
            raise ValueError('not an integer')

    def frame(self, num=0):
        """ Seek desired frame

        :param num: int: frame number
        :return: time, NDarray image
        """
        self.f.seek(self._framePosition(num))
        self.f.readinto(self.frameHeader)
        image = np.fromfile(self.f, np.uint8, self.imageSize).reshape(self.imageH, self.imageW)
        time = getattr(self.frameHeader, 'FrameTime')

        return TwvImage(timestamp=time, image=image, frame_header=self.frameHeader)

    def close(self):
        if not self.f.closed:
            self.f.close()

#    def __del__(self):
#        self.f.close()


class TwvImage(object):
    """ Class for TWV images

    Saves timestamp and image data.
    """
    def __init__(self, timestamp, image, frame_header=None):
        self.time = timestamp
        self.image = image
        self.laser_power = getattr(frame_header, 'LaserPower', None) if frame_header is not None else None
