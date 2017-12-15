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
                              ct.POINTER(ct.POINTER(ct.c_char_p)))

GetAttrPtrType = ct.CFUNCTYPE(ct.c_int, ct.c_char_p, ct.POINTER(FileAttributes))

ReadPtrType = ct.CFUNCTYPE(ct.c_int, ct.c_char_p, ct.c_char_p, ct.c_uint64,
                           ct.c_uint64, ct.POINTER(FileInfo))

WritePtrType = ct.CFUNCTYPE(ct.c_int, ct.c_char_p, ct.c_char_p, ct.c_uint64,
                            ct.c_uint64, ct.POINTER(FileInfo))

MainPtrType = ct.CFUNCTYPE(ct.c_int, ct.c_int, ct.POINTER(ct.c_char_p))
DebugType = ct.CFUNCTYPE(ct.c_int, ct.c_char_p)

class Callbacks(ct.Structure):
    _fields_ = [("open", OpenPtrType),
                ("readdir", ReadDirPtrType),
                ("getattr", GetAttrPtrType),
                ("read", ReadPtrType),
                ("write", WritePtrType)]

class FuseBridge(object):
    def __init__(self):
        self.bridge_lib = tools.compile_library('bridge.c')
        self.extern = ct.cdll.LoadLibrary(self.bridge_lib)
        self.callbacks = Callbacks.in_dll(self.extern, 'python_callbacks')

    @staticmethod
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

    def make_string(self, data=b"", terminate=False):
        # Uses the bridge's allocator to create a new (char *) buffer.
        # Loads the string with a fixed input.

        address = self.extern.zalloc(len(data) + int(terminate))
        self.load_string_ptr(address, data)
        return address

    def make_string_array(self, strings=(), string_term=True,
                          array_term=True):
        # Uses the bridge's allocator to create an array of C strings.
        # Initializes the strings from a set of inputs.

        length = len(strings) + int(array_term)

        address = self.extern.zalloc(ct.sizeof(ct.c_char_p) * length)
        array = (ct.c_char_p * length).from_address(address)

        for k,string in enumerate(strings):
            array[k] = self.make_string(string, string_term)

        return array

    def main(self, argv):
        argc = len(argv)
        argv = self.make_string_array(argv)
        #XXX: Free argv afterwards
        return self.extern.bridge_main(argc, argv)

def main():
    fuse = FuseBridge()

    args = ["hello", "my dudes", "it is thursday!"]
    fuse.main(args)

if __name__ == "__main__":
    main()
