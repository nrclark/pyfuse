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


def compile_library(files=(), libname="temp"):
    """ Compiles a set of files into a shared library in a new temp directory.
    Returns the path to the new library.

    This is accomplished by using the local C compiler ('cc' or the CC
    environment variable) and CFLAGS (if defined in the environment) to compile
    the provided file set.

    Args:
        files (tuple): List of files to #include in the library.
        libname (string): Name of generated library file.

    Returns:
        string: The path to generated library file. """

    base = os.path.split(sys.argv[0])[1]
    tempdir = tempfile.mkdtemp(prefix="tmp.%s." % base)
    outfile = "lib%s.so" % libname
    outfile = os.path.join(tempdir, outfile)

    if "CC" in os.environ:
        cc_cmd = shlex.split(os.environ["CC"])
    else:
        cc_cmd = ["cc"]

    if "CFLAGS" in os.environ:
        cflags = shlex.split(os.environ["CFLAGS"])
    else:
        cflags = ["-O2"]

    cflags += ["-D_FILE_OFFSET_BITS=64", "-fPIC", "-shared", "-lfuse"]
    cflags += ["-Wall", "-Wextra", "-pedantic"]

    command = cc_cmd + cflags + list(files) + ["-o", outfile]

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


def find_constant_names(header_filename, regex=".*"):
    """ Finds all the names of all #define constants in the target header.
    Does not retrieve their value.

    Args:
        header_filename (string): Header file to scan for constants.
        regex (string): Regex to match against detected constants. Defaults
                        to all constants.

    Returns:
        tuple: Tuple of detected constant names (as strings) """

    if "CC" in os.environ:
        cc_cmd = shlex.split(os.environ["CC"])
    else:
        cc_cmd = ["cc"]

    if "CFLAGS" in os.environ:
        cflags = shlex.split(os.environ["CFLAGS"])
    else:
        cflags = []

    base = os.path.split(sys.argv[0])[1]
    command = cc_cmd + cflags + ["-E", "-dM", header_filename]

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

    define_regex = "^[ \t]*[#]define[ \t]+[^ (\t]+[ \t]+"

    matches = re.findall(define_regex, result, flags=re.M)
    result = [x.strip().split() for x in matches]
    result = [x[1].strip() for x in result]
    result = [x for x in result if x[:1] != "_"]

    return tuple([x for x in result if re.search(regex, x)])


def get_constant_values(includes=(), constants=()):
    """ Compiles a test C file with a user-specified list of include files.
    Test file will have one 'printf' call for each parameter in the constants
    list. The result is parsed, and the constant values are returned as a dict.

    This is an easy way to use the system C compiler to achieve platform
    independence from specific constant values on any given system.

    Args:
        includes (tuple/list): List of files to #include in the test program.
        constants (tuple/list): List of constants to printf() and retrieve.

    Returns:
        dict: A name-index dict containing the requested constants. """

    if isinstance(includes, str):
        includes = (includes,)

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

    descriptor, filename = tempfile.mkstemp(dir='.', suffix='.c')
    binary = filename + '.bin'
    os.write(descriptor, source.encode())
    os.close(descriptor)

    try:
        sp.check_call(["cc", filename, "-o", binary])
        result = sp.check_output([binary]).decode().strip()

    except sp.CalledProcessError:
        result = ""

    for name in [binary, filename]:
        if os.path.isfile(name):
            os.remove(name)

    results = [pair.split('=') for pair in result.splitlines()]
    output = {}

    for pair in results:
        output[pair[0].strip()] = ast.literal_eval(pair[1].strip())

    return output


def find_and_get_constants(header, regex=".*"):
    """ Finds all constants that match a regex inside of a given header
    file.

    The result is returned as a dict of values.

    Args:
        header (string): Header file to scan for constants.
        regex (string): Regex to use for picking constant names.

    Returns:
        dict: A dict of detected constants. """

    constants = find_constant_names(header, regex)
    value_dict = get_constant_values(header, constants)
    return value_dict


def find_errnos(header="/usr/include/errno.h"):
    """ Finds all the errno error-codes defined for the host's system.

    This is accomplished by useing the local C compiler ('cc' or the
    CC environment variable) to preprocess the errno.h header.

    The result is returned as a dict of values.

    Args:
        header (string): Errno header file. The default value will work on
                         most systems.

    Returns:
        dict: A dict of detected errno constants. """

    return find_and_get_constants(header, "^E")

ERRNO_CONSTANTS = find_and_get_constants("/usr/include/errno.h", "^E")
FCNTL_CONSTANTS = find_and_get_constants("/usr/include/fcntl.h", "^[A-Z]")
STAT_CONSTANTS = find_and_get_constants("/usr/include/sys/stat.h", "^[A-Z]")

#------------------------------------------------------------------------------#

def _main():
    """ Main routine when executed directly. Serves no purpose. """

    print("Contents of fcntl.h:\n", FCNTL_CONSTANTS)
    print("Contents of sys/stat.h:\n", STAT_CONSTANTS)
    print("Contents of errno.h:\n", ERRNO_CONSTANTS)

if __name__ == "__main__":
    _main()
