#!/usr/bin/env python3

import subprocess as sp
import shlex
import shutil
import tempfile
import re
import sys
import os
from ctypes import *

def find_errnos(header = "/usr/include/errno.h"):
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
    except (FileNotFoundError, sp.CalledProcessError) as e:
        command = shlex.quote(' '.join(command))
        err_msg = "%s: Pre-parser couldn't execute command: %s)"
        err_msg = err_msg % (base, command)
        sys.stderr.write(err_msg + "\n")

        if isinstance(e, FileNotFoundError):
            sys.exit(127)
        else:
            sys.exit(e.returncode)

    regex = "^[ \t]*[#]define[ \t]+E[^ \t]+[ \t]+[0-9]+"

    matches = re.findall(regex, result, flags=re.M)
    errnos = {}
    for match in matches:
        match = [x.strip() for x in match.split()]
        errnos[match[1]] = int(match[2])

    return errnos

def compile_library(files = ["bridge.h", "bridge.c"], name = "bridge"):
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
        shutil.rmtree(tempdir, ignore_errors = True)
        command = shlex.quote(' '.join(command))
        err_msg = "%s: couldn't compile library. (command: %s)"
        err_msg = err_msg % (base, command)
        sys.stderr.write(err_msg + "\n")
        sys.exit(result)

    return outfile

#----------------------------------------------------------------------#

class FileInfo(Structure):
    _fields_ = [("handle", c_uint64),
                ("flags", c_uint32),
                ("direct_io", c_bool),
                ("nonseekable", c_bool)]

class FileAttributes(Structure):
    _fields_ = [("size", c_uint64),
                ("mode", c_uint32),
                ("uid", c_uint32),
                ("gid", c_uint32)]

OpenPtrType = CFUNCTYPE(c_int, c_char_p, POINTER(FileInfo))
AllocPtrType = CFUNCTYPE(c_void_p, c_size_t)
ReadDirPtrType = CFUNCTYPE(c_int, c_char_p, POINTER(POINTER(c_char_p)),
                           AllocPtrType)

GetattrPtrType = CFUNCTYPE(c_int, c_char_p, POINTER(FileAttributes))

ReadPtrType = CFUNCTYPE(c_int, c_char_p, c_char_p, c_uint64, c_uint64,
                        POINTER(FileInfo))

WritePtrType = CFUNCTYPE(c_int, c_char_p, c_char_p, c_uint64, c_uint64,
                         POINTER(FileInfo))

MainPtrType = CFUNCTYPE(c_int, c_int, POINTER(c_char_p))

def main():
    errnos = find_errnos()
    bridge = cdll.LoadLibrary(compile_library())
    shutil.rmtree(os.path.dirname(bridge._name))

if __name__ == "__main__":
    main()
