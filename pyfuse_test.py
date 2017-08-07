#!/usr/bin/env python3

import time
import typing
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

def compile_library(files = ["bridge_test.c"], name = "bridge"):
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

AllocPtrType = CFUNCTYPE(c_void_p, c_size_t)
char_ptr = POINTER(c_char)
char_double_ptr = POINTER(char_ptr)
char_triple_ptr = POINTER(char_double_ptr)

ReadDirPtrType = CFUNCTYPE(c_int, char_triple_ptr, AllocPtrType)

class Callbacks(Structure):
    _fields_ = [("readdir", ReadDirPtrType)]

def load_2d_array(data, target, allocator, terminate = True):
    """ Accepts a list of strings/bytes on the 'data' input.
    
    Uses the 'allocator' ctypes function to create an array of (char *),
    with each pointing to an also-allocated array of (char). The result
    is loaded with the values from 'data'.
    
    If 'terminate' is true, an extra NUL character will be added to the
    end of each string before copying it. """
    
    assert isinstance(data, list)
    assert isinstance(data[0], str) or isinstance(data[0], bytes)
    assert isinstance(allocator, AllocPtrType)
    assert isinstance(terminate, bool)

    count = len(data)
    target[0] = cast(allocator(sizeof(char_ptr) * count), 
                     char_double_ptr)

    for x in range(count):
        if type(data[x]) == str:
            out_word = data[x].encode()
        else:
            out_word = data[x]
        if terminate:
            out_word += b'\0'

        length = len(out_word)

        target[0][x] = cast(allocator(length), char_ptr)
        addr = addressof(target[0][x].contents)
        string_buf = (c_char * length).from_address(addr)
        string_buf[:length] = out_word
    
def readdir(entries, allocator):
    load_2d_array(["hello","you cool dudes"], entries, allocator)
    return 0

readdir_callback = ReadDirPtrType(readdir)

def main():
    errnos = find_errnos()
    bridge = cdll.LoadLibrary(compile_library())

    callbacks = Callbacks.in_dll(bridge, 'callbacks');
    callbacks.readdir = readdir_callback;

    bridge.dummy_function()

    shutil.rmtree(os.path.dirname(bridge._name))

if __name__ == "__main__":
    main()
