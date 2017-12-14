#!/usr/bin/env python3

import subprocess as sp
import shlex
import shutil
import tempfile
import re
import sys
import os

import ctypes as ct
import compiler_tools as tools

#----------------------------------------------------------------------#

class FileInfo(ct.Structure):
    _fields_ = [("handle", ct.c_uint64),
                ("flags", ct.c_uint32),
                ("direct_io", ct.c_bool),
                ("nonseekable", ct.c_bool)]

class FileAttributes(ct.Structure):
    _fields_ = [("size", ct.c_uint64),
                ("mode", ct.c_uint32),
                ("uid", ct.c_uint32),
                ("gid", ct.c_uint32)]

OpenPtrType = ct.CFUNCTYPE(ct.c_int, ct.c_char_p, ct.POINTER(FileInfo))
AllocPtrType = ct.CFUNCTYPE(ct.c_void_p, ct.c_size_t)
ReadDirPtrType = ct.CFUNCTYPE(ct.c_int, ct.c_char_p,
                              ct.POINTER(ct.POINTER(ct.c_char_p)),
                              AllocPtrType)

GetAttrPtrType = ct.CFUNCTYPE(ct.c_int, ct.c_char_p, ct.POINTER(FileAttributes))

ReadPtrType = ct.CFUNCTYPE(ct.c_int, ct.c_char_p, ct.c_char_p, ct.c_uint64,
                           ct.c_uint64, ct.POINTER(FileInfo))

WritePtrType = ct.CFUNCTYPE(ct.c_int, ct.c_char_p, ct.c_char_p, ct.c_uint64,
                            ct.c_uint64, ct.POINTER(FileInfo))

MainPtrType = ct.CFUNCTYPE(ct.c_int, ct.c_int, ct.POINTER(ct.c_char_p))
DebugType = ct.CFUNCTYPE(ct.c_int, ct.c_char_p)

class Callbacks(ct.Structure):
    _fields_ = [("open", OpenPtrType)]
    _fields_ = [("readdir", ReadDirPtrType)]
    _fields_ = [("getattr", GetAttrPtrType)]
    _fields_ = [("read", ReadPtrType)]
    _fields_ = [("write", WritePtrType)]

class FuseBridge(object):
    def __init__(self):
        self.bridge_lib = tools.compile_library('bridge.c')
        self.bridge = ct.cdll.LoadLibrary(self.bridge_lib)
        self.callbacks = Callbacks.in_dll(self.bridge, 'python_callbacks')
        self.bridge.debug_write(b"bumpers")

def load_string_ptr(address, data=b"", terminate=False):
    # Copies a Python string (or bytes object) into a (char *) address.
    # Optionally terminates the string with a NUL character.

    if isinstance(data, str):
        data = data.encode()

    size = len(data) + int(terminate)
    string = (ct.c_char * size).from_address(address)

    if terminate:
        string.raw = data + b"\x00"
    else:
        string.raw = data

def main():
    fuse = FuseBridge()

    string_ptr = fuse.bridge.zalloc(64)
    load_string_ptr(string_ptr, "hello, my dudes")
    fuse.bridge.bridge_main(3, string_ptr)

if __name__ == "__main__":
    main()
