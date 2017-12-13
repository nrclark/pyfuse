#!/usr/bin/env python3
""" Helper module for interfacing with the FUSE bridge supplied
in bridge.c (included). Knows how to compile and load the bridge
library, including relevant errnos.

Includes a helper function for the tricky business of using an external
allocator (supplied by bridge.c) to create a 2-D string array (for use
in the readdir callback. """

import ast
import subprocess as sp
import shlex
import shutil
import tempfile
import re
import sys
import os

import ctypes as ct
import compiler_tools as compiler

#pylint: disable=invalid-name
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

#------------------------------------------------------------------------------#

class FileInfo(ct.Structure):
    #pylint: disable=too-few-public-methods
    """ Reduced version of the 'fuse_file_info' structure. Free of bitfields
    and unneeded parameters. """

    _fields_ = [("handle", ct.c_uint64),
                ("flags", ct.c_uint32),
                ("direct_io", ct.c_bool),
                ("nonseekable", ct.c_bool)]

class FileAttributes(ct.Structure):
    #pylint: disable=too-few-public-methods
    """ Reduced version of the 'stat' structure. Only includes the bits that
    are relevant to our particular application. """

    _fields_ = [("size", ct.c_uint64),
                ("mode", ct.c_uint32),
                ("uid", ct.c_uint32),
                ("gid", ct.c_uint32)]

OpenPtrType = ct.CFUNCTYPE(ct.c_int, ct.c_char_p, ct.POINTER(FileInfo))

AllocPtrType = ct.CFUNCTYPE(ct.c_void_p, ct.c_size_t)

ReadDirPtrType = CFUNCTYPE(c_int, c_char_p, char_triple_ptr,
                           AllocPtrType)

GetAttrPtrType = CFUNCTYPE(c_int, c_char_p, POINTER(FileAttributes))

ReadPtrType = CFUNCTYPE(c_int, c_char_p, char_ptr, c_uint64, c_uint64,
                        POINTER(FileInfo))

WritePtrType = CFUNCTYPE(c_int, c_char_p, c_char_p, c_uint64, c_uint64,
                         POINTER(FileInfo))

MainPtrType = CFUNCTYPE(c_int, c_int, POINTER(c_char_p))


class Callbacks(Structure):
    #pylint: disable=too-few-public-methods
    """ Container for all of the python-supplied callbacks that
    bridge.c knows how to use. Reduced version of the 'fuse_operations'
    struct."""

    _fields_ = [("open", OpenPtrType)]
    _fields_ = [("readdir", ReadDirPtrType)]
    _fields_ = [("getattr", GetAttrPtrType)]
    _fields_ = [("read", ReadPtrType)]
    _fields_ = [("write", WritePtrType)]


def load_char_ptr(data, target, terminate=False):
    """ Copies a string or bytearray into a C-type char* pointer.
    Adds an optional termination character at the end.

    Args:
        data (str, bytes): Input data to copy
        target (char_ptr): Pointer to target memory
        terminate (bool): Append a NULL character if true.

    Returns:
        None """

    assert isinstance(data, (bytes, str))
    assert isinstance(target, char_ptr)

    if isinstance(data, str):
        data = data.encode()

    if terminate:
        data += b'\x00'

    memmove(target, data, len(data))


def create_char_array(data, allocator=None,
                      terminate_array=True,
                      terminate_strings=True):
    """ Creates a 2-D char array, and populates it with the list of
    strings held in data. Can use an external allocator and/or
    add terminations.

    Args:
        data (list, tuple): List of input strings to copy.

        allocator (AllocPtrType): Optional external malloc()-style
            allocator function to use. If not given, data will be
            allocated internally.

        terminate_array (bool): Append a NULL pointer to the end
            of the generated array.

        terminate_strings (bool): Append a NULL character to the end
            of each string.

    Returns:
        result (char_double_ptr): Pointer of type char** to new
           array. """

    assert isinstance(data, (list, tuple))
    assert isinstance(terminate_strings, bool)
    assert isinstance(terminate_array, bool)

    if allocator is not None:
        assert isinstance(allocator, AllocPtrType)

    count = len(data)

    if allocator is None:
        result = (char_ptr * (count + int(terminate_array)))()
    else:
        size = sizeof(char_ptr) * (count + int(terminate_array))
        result = cast(allocator(size), char_double_ptr)

    for x, entry in enumerate(data):
        length = len(entry) + int(terminate_strings)

        if allocator is None:
            result[x] = create_string_buffer(length)
        else:
            result[x] = cast(allocator(length), char_ptr)

        load_char_ptr(entry, result[x], terminate_strings)

    if terminate_array:
        result[count] = None


#----------------------------------------------------------------------#

class Container(object):
    """ Dummy container object. Functionally equivalent to a dict,
    but with cleaner syntax for external users. """

    #pylint: disable=too-few-public-methods

    def __init__(self, item_dict=None):
        """ Returns a Container object with an optional pre-iinitialized
        set of members from an input dict.

        Args:
            item_dict (dict): Dict of values to pre-initialize.

        Returns:
            self: A Container object initialized with any provided
            member variables. """

        if item_dict is None:
            item_dict = {}

        for key in item_dict.keys():
            self.__dict__[key] = item_dict[key]


class ConstantContainer(Container):
    """ Container object which parses an include file, finds all
    #define constants that match an optional regex, and loads them as
    integer member variables in the returned class instance. """

    #pylint: disable=too-few-public-methods

    def __init__(self, include_file, regex=None):
        """ Returns a ConstantContainer object initialized with
        the all constants detected within a C include file that
        match a given regex. Host must have a working C compiler.

        Args:
            include_file (str): C header file to check for constants
            regex (str): Optional regular expression to use for
                filtering constants.

        Returns:
            self: A ConstantContainer object initialized with the
               detected constants as instance members. """

        if regex is None:
            regex = ".*"

        regex = re.compile(regex)
        constants = FindConstants(include_file)
        constants = [x for x in constants if re.search(regex, x)]
        constant_dict = GetConstants(include_file, constants)
        super(ConstantContainer, self).__init__(constant_dict)

Errno = ConstantContainer("/usr/include/errno.h")
Fcntl = ConstantContainer("/usr/include/fcntl.h", "^[A-Z]")
Stat = ConstantContainer("/usr/include/sys/stat.h", "^[A-Z]")

#----------------------------------------------------------------------#


class FuseBridge(object):
    """ Utility class for holding everything of interest that this
    module can generate. """

    #pylint: disable=too-few-public-methods

    def __init__(self, source_file="bridge.c"):
        self.library_file = None
        source_file = os.path.join(SCRIPT_DIR, source_file)

        self.library_file = compile_library()
        self.dll = cdll.LoadLibrary(self.library_file)
        self.callbacks = Callbacks.in_dll(self.dll, 'python_callbacks')

        self.types = Container({"FileInfo": FileInfo,
                                "FileAttributes": FileAttributes,
                                "OpenPtrType": OpenPtrType,
                                "ReadDirPtrType": ReadDirPtrType,
                                "GetAttrPtrType": GetAttrPtrType,
                                "ReadPtrType": ReadPtrType,
                                "WritePtrType": WritePtrType,
                                "MainPtrType": MainPtrType,
                                "AllocPtrType": AllocPtrType})

    def __del__(self):
        if self.library_file is not None:
            shutil.rmtree(os.path.dirname(self.library_file))


def main():
    """ Main routine when executed directly. Serves no purpose. """
    FuseBridge()

    print(dir(Errno))
    print(dir(Fcntl))
    print(dir(Stat))


if __name__ == "__main__":
    main()
