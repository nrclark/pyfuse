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

from ctypes import c_char, c_void_p, c_size_t, c_char_p
from ctypes import c_uint32, c_uint64, c_bool, c_int
from ctypes import POINTER, Structure, CFUNCTYPE
from ctypes import cast, sizeof, cdll, memmove, create_string_buffer


#pylint: disable=invalid-name

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def GetConstants(includes=None, constants=None):
    """ Compiles a test C file with a user-specified list of include
    files. Test file will have one 'printf' call for each parameter
    in the constants list. The result is parsed, and the constant
    values are returned as a dict.

    This is an easy way to use the system C compiler to achieve
    platform independence from specific constant values on any given
    system.

    Args:
        includes (list): List of files to #include in the test program.
        constants (list): List of constants to printf() and retrieve.

    Returns:
        retval: A name-index dict containing the requested constants."""

    if includes is None:
        includes = []

    if constants is None:
        constants = []

    if isinstance(includes, str):
        includes = [includes]

    template = """
    #include <stdio.h>
    #include <stddef.h>
    #include <stdlib.h>
    #include <stdint.h>
    #include <sys/types.h>
    %INCLUDES%

    int main(void) {
        %CONSTANT_LINES%
        return 0;
    }
    """

    include_string = ['#include "%s"' % x for x in includes]
    include_string = '\n'.join(include_string)

    line = 'printf("%NAME% = %lld\\n", (long long int)'
    line += '(%NAME%));'
    lines = [line.replace('%NAME%', x) for x in constants]

    source = template.replace("%INCLUDES%", include_string)
    source = source.replace("%CONSTANT_LINES%", '\n'.join(lines))

    fd, filename = tempfile.mkstemp(dir='.', suffix='.c')
    binary = filename + '.bin'
    os.write(fd, source.encode())
    os.close(fd)

    try:
        sp.check_call(["cc", filename, "-o", binary])
        result = sp.check_output([binary]).decode().strip()

    except sp.CalledProcessError:
        result = ""

    for name in [binary, filename]:
        if os.path.isfile(name):
            os.remove(name)

    results = [x.split('=') for x in result.splitlines()]
    retval = {}

    for x in results:
        retval[x[0].strip()] = ast.literal_eval(x[1].strip())

    return retval


def FindConstants(header):
    """ Finds all the names of all #define constants in the target
    header. Does not retrieve their value. """

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

    regex = "^[ \t]*[#]define[ \t]+[^ (\t]+[ \t]+"

    matches = re.findall(regex, result, flags=re.M)
    result = [x.strip().split() for x in matches]
    result = [x[1].strip() for x in result]
    result = [x for x in result if x[:1] != "_"]

    return result


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
    command = cc + cflags + list(files) + ["-o", outfile]

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
        self.callbacks = Callbacks.in_dll(self.dll, 'callbacks')

        self.types = (FileInfo, FileAttributes, OpenPtrType,
                      ReadDirPtrType, GetAttrPtrType, ReadPtrType,
                      WritePtrType, MainPtrType, AllocPtrType)

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
