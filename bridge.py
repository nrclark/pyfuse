#!/usr/bin/env python3
""" Helper module for interfacing with the FUSE bridge supplied
in bridge.c (included). Knows how to compile and load the bridge
library, including relevant errnos.

Includes a helper function for the tricky business of using an external
allocator (supplied by bridge.c) to create a 2-D string array (for use
in the readdir callback. """

import subprocess as sp
import shlex
import shutil
import tempfile
import re
import sys
import os

from ctypes import c_char, c_void_p, c_size_t, c_char_p
from ctypes import c_uint32, c_uint64, c_bool, c_int
from ctypes import POINTER, Structure, CFUNCTYPE
from ctypes import cast, sizeof, addressof

#pylint: disable=invalid-name


def find_errnos(header="/usr/include/errno.h"):
    """ Finds all the errno error-codes defined for the host's system.

    This is accomplished by useing the local C compiler ('cc' or the
    CC environment variable) to preprocess the errno.h header.

    The result is returned as a dict of values. """

    if "CC" in os.environ:
        cc = shlex.split(os.environ["CC"])
    else:
        cc = ["cc"]

    if "CFLAGS" in os.environ:
        cflags = shlex.split(os.environ["CFLAGS"])
    else:
        cflags = []

    base = os.path.split(sys.argv[0])[1]
    command = cc + cflags + ["-E", "-dM", header]

    try:
        result = sp.check_output(command).decode().strip()
    except (FileNotFoundError, sp.CalledProcessError) as error:
        command = shlex.quote(' '.join(command))
        err_msg = "%s: Pre-parser couldn't execute command: %s)"
        err_msg = err_msg % (base, command)
        sys.stderr.write(err_msg + "\n")

        if isinstance(error, FileNotFoundError):
            sys.exit(127)
        else:
            sys.exit(error.returncode)

    regex = "^[ \t]*[#]define[ \t]+E[^ \t]+[ \t]+[0-9]+"

    matches = re.findall(regex, result, flags=re.M)
    errnos = {}
    for match in matches:
        match = [x.strip() for x in match.split()]
        errnos[match[1]] = int(match[2])

    return errnos


def compile_library(files=("bridge_test.c",), name="bridge"):
    """ Compiles a set of files into a dynamically-linked object
    in a new temp directory. Returns the path to the new library.

    This is accomplished by using the local C compiler ('cc' or the
    CC environment variable) and CFLAGS (if defined in the environment)
    to compile the provided file set.

    The result is returned as a string. """

    base = os.path.split(sys.argv[0])[1]
    tempdir = tempfile.mkdtemp(prefix="tmp.%s." % base)
    outfile = "lib%s.so" % name
    outfile = os.path.join(tempdir, outfile)

    if "CC" in os.environ:
        cc = shlex.split(os.environ["CC"])
    else:
        cc = ["cc"]

    if "CFLAGS" in os.environ:
        cflags = shlex.split(os.environ["CFLAGS"])
    else:
        cflags = ["-O2"]

    cflags += ["-D_FILE_OFFSET_BITS=64", "-fPIC", "-shared", "-lfuse"]
    cflags += ["-Wall", "-Wextra", "-pedantic", "-Werror"]
    command = cc + cflags + files + ["-o", outfile]

    try:
        result = sp.call(command)
    except FileNotFoundError:
        result = 127

    if result != 0:
        shutil.rmtree(tempdir, ignore_errors=True)
        command = shlex.quote(' '.join(command))
        err_msg = "%s: couldn't compile library. (command: %s)"
        err_msg = err_msg % (base, command)
        sys.stderr.write(err_msg + "\n")
        sys.exit(result)

    return outfile

#----------------------------------------------------------------------#

char_ptr = POINTER(c_char)
char_double_ptr = POINTER(char_ptr)
char_triple_ptr = POINTER(char_double_ptr)
AllocPtrType = CFUNCTYPE(c_void_p, c_size_t)


class FileInfo(Structure):
    #pylint: disable=too-few-public-methods
    """ Reduced version of the 'fuse_file_info' structure. Free of
    bitfields and unneeded parameters. """

    _fields_ = [("handle", c_uint64),
                ("flags", c_uint32),
                ("direct_io", c_bool),
                ("nonseekable", c_bool)]


class FileAttributes(Structure):
    #pylint: disable=too-few-public-methods
    """ Reduced version of the 'stat' structure. Only includes the
    bits that are relevant to our particular application. """

    _fields_ = [("size", c_uint64),
                ("mode", c_uint32),
                ("uid", c_uint32),
                ("gid", c_uint32)]


OpenPtrType = CFUNCTYPE(c_int, c_char_p, POINTER(FileInfo))

ReadDirPtrType = CFUNCTYPE(c_int, c_char_p, char_triple_ptr,
                           AllocPtrType)

GetAttrPtrType = CFUNCTYPE(c_int, c_char_p, POINTER(FileAttributes))

ReadPtrType = CFUNCTYPE(c_int, c_char_p, c_char_p, c_uint64, c_uint64,
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


def load_2d_array(data, target, allocator, terminate=True):
    """ Accepts a list of strings/bytes on the 'data' input.

    Uses the 'allocator' ctypes function to create an array of (char *),
    with each pointing to an also-allocated array of (char). The result
    is loaded with the values from 'data'.

    If 'terminate' is true, an extra NUL character will be added to the
    end of each string before copying it. """

    assert isinstance(data, list)
    assert isinstance(data[0], (bytes, str))
    assert isinstance(allocator, AllocPtrType)
    assert isinstance(terminate, bool)

    target[0] = cast(allocator(sizeof(char_ptr) * len(data)),
                     char_double_ptr)

    for k, string in enumerate(data):
        if isinstance(string, str):
            string = string.encode()

        if terminate:
            string += b'\0'

        length = len(string)

        target[0][k] = cast(allocator(length), char_ptr)
        addr = addressof(target[0][k].contents)
        string_buf = (c_char * length).from_address(addr)
        string_buf[:length] = string
