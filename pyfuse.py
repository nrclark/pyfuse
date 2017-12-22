#!/usr/bin/env python3

""" A library for making simlpe FUSE filesystems in Python. This library
uses the host's C compiler to compile and load a libfuse bridge, which is
then used to launch a Python-based filesystem (implemented via callbacks).

This scheme provides Python-side independence from all the platform-specific
aspects of the the underlying fuse and stat structures.

This library is under heavy development, and should be expected to change
over time. """

import time
import multiprocessing
import signal
import sys
import os

import ctypes as ct
import compiler_tools as tools

#------------------------------------------------------------------------------#


class FileInfo(ct.Structure):
    # pylint: disable=too-few-public-methods
    """ Equivalent structure to file_info from bridge.h. Used as a reduced-
    complexity version of fuse_file_info. """

    _fields_ = [("handle", ct.c_uint64),
                ("flags", ct.c_uint32),
                ("direct_io", ct.c_bool),
                ("nonseekable", ct.c_bool)]


class FileAttributes(ct.Structure):
    # pylint: disable=too-few-public-methods
    """ Equivalent structure to file_info from bridge.h. Used as a reduced-
    complexity version of the stat structure. """

    _fields_ = [("size", ct.c_uint64),
                ("mode", ct.c_uint32),
                ("uid", ct.c_uint32),
                ("gid", ct.c_uint32)]


# pylint: disable=invalid-name
OpenPtrType = ct.CFUNCTYPE(ct.c_int, ct.c_char_p, ct.POINTER(FileInfo))
AllocPtrType = ct.CFUNCTYPE(ct.c_void_p, ct.c_size_t)
ReadDirPtrType = ct.CFUNCTYPE(ct.c_int, ct.c_char_p,
                              ct.POINTER(ct.POINTER(ct.c_char_p)))

GetAttrPtrType = ct.CFUNCTYPE(ct.c_int, ct.c_char_p, ct.POINTER(FileAttributes))
AccessPtrType = ct.CFUNCTYPE(ct.c_int, ct.c_char_p, ct.c_int)

ReadPtrType = ct.CFUNCTYPE(ct.c_int, ct.c_char_p, ct.c_void_p, ct.c_uint64,
                           ct.c_uint64, ct.POINTER(FileInfo))

WritePtrType = ct.CFUNCTYPE(ct.c_int, ct.c_char_p, ct.c_void_p, ct.c_uint64,
                            ct.c_uint64, ct.POINTER(FileInfo))

TruncatePtrType = ct.CFUNCTYPE(ct.c_int, ct.c_char_p, ct.c_uint64)

MainPtrType = ct.CFUNCTYPE(ct.c_int, ct.c_int, ct.POINTER(ct.c_char_p))
# pylint: enable=invalid-name


class Callbacks(ct.Structure):
    # pylint: disable=too-few-public-methods
    """ Equivalent structure to callbacks from bridge.h. Used to provide the
    callback interface from FUSE back into Python. """

    _fields_ = [("open", OpenPtrType),
                ("readdir", ReadDirPtrType),
                ("getattr", GetAttrPtrType),
                ("access", AccessPtrType),
                ("read", ReadPtrType),
                ("write", WritePtrType),
                ("truncate", TruncatePtrType)]


def register_process_killer(process, signum):
    """ Registers a running multiprocess.Process() instance with the main
    process's signal handlers. This ensures that interrupts/terminate requests
    will also shut down the fuse event loop. """

    original_handler = signal.getsignal(signum)

    def killer(num, frame):
        """ Signal-handler wrapper. Kills the process passed to parent, and
        then launches the parent's signal handler. """

        process.terminate()
        original_handler(num, frame)

    signal.signal(signum, killer)

def profiler(target):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = target(*args, **kwargs)
        print("%s ran in: %.4f sec" % (target.__name__, time.time() - start))
        return result

    return wrapper

class FuseBridge(object):
    """ Main bridge object for creating and connecting custom FUSE designs.
    At present, this class should be used by creating an instance,
    connecting callbacks, and launching main() with any arguments that
    should be passed down to fuse_main. """

    def __init__(self):
        srcfile = os.path.join(os.path.dirname(__file__), "bridge.c")
        self.bridge_lib = tools.compile_library(srcfile)
        self.extern = ct.cdll.LoadLibrary(self.bridge_lib)
        self.callbacks = Callbacks.in_dll(self.extern, 'python_callbacks')
        self.result = None
        self.process = None

    @staticmethod
    def unload_bytes(address, length):
        """ Copies a fixed amount of bytes from a (char *) buffer to a new
        Python bytes() instance and returns the result. """

        char_buffer = (ct.c_char * length).from_address(address)
        return char_buffer.raw

    @staticmethod
    def load_string_ptr(address, data=b"", terminate=False):
        """ Copies a Python string (or bytes object) into a (char *) address
        (address should point to already-allocated memory). Optionally
        terminates the string with a NUL character. """

        if isinstance(data, str):
            data = data.encode()

        size = len(data) + int(terminate)
        string = (ct.c_char * size).from_address(address)

        if terminate:
            string.raw = data + b"\x00"
        else:
            string.raw = data

    def make_string(self, data=b"", terminate=False):
        """ Uses the bridge's allocator to create a new (char *) buffer, and
        initializes it with the contents of 'data'. Optionally allocates
        an extra byte and terminates the string with a NUL character.

        Returns an address to the allocated memory. User is responsible for
        freeing the memory when finished. """

        address = self.extern.zalloc(len(data) + int(terminate))
        self.load_string_ptr(address, data)
        return address

    def make_string_array(self, strings=(), string_term=True,
                          array_term=True):
        """ Uses the bridge's allocator to create an array of char pointers,
        each of which points to a newly-allocated string buffer. This function
        can be used for creating argv-style lists.

        Optionally adds a terminating NUL character to each string, and/or a
        terminating NULL address to the end of the list.

        Returns an address to top of the list. User is responsible for freeing
        all of the memory blocks in the list, as well as the list itself. """

        length = len(strings) + int(array_term)

        address = self.extern.zalloc(ct.sizeof(ct.c_char_p) * length)
        array = (ct.c_char_p * length).from_address(address)

        for k, string in enumerate(strings):
            array[k] = self.make_string(string, string_term)

        return array

    def _main(self, argv):
        """ Internally-launched routine for calling the FUSE event loop. This
        routine is spawned in a new Process() instance by self.main(), and
        generally shouldn't be called directly. """

        argv = list(argv)
        argv = [argv[0], "-s"] + argv[1:]
        argc = len(argv)
        argv = self.make_string_array(argv)

        self.result = self.extern.bridge_main(argc, argv)
        return self.result

    def main(self, argv):
        """ Main routine for launching FUSE bridge after the user has finished
        connecting callbacks. """

        self.process = multiprocessing.Process(target=self._main, args=(argv,))
        self.process.start()
        register_process_killer(self.process, signal.SIGINT)
        register_process_killer(self.process, signal.SIGQUIT)
        register_process_killer(self.process, signal.SIGTERM)

        while self.process.is_alive():
            time.sleep(0.5)

        return self.result


class BasicFs(object):
    """ Basic FUSE filesystem class. Provides a full set of wrappers
    around everything ctypes-specific, which simplifies the end-user's
    design significantly. """

    def __init__(self):
        self.bridge = FuseBridge()
        self.bridge.callbacks.open = OpenPtrType(self._open)
        self.bridge.callbacks.readdir = ReadDirPtrType(self._readdir)
        self.bridge.callbacks.getattr = GetAttrPtrType(self._getattr)
        self.bridge.callbacks.access = AccessPtrType(self._access)
        self.bridge.callbacks.read = ReadPtrType(self._read)
        self.bridge.callbacks.write = WritePtrType(self._write)
        self.bridge.callbacks.truncate = TruncatePtrType(self._truncate)

    def _open(self, path, info_ptr):
        """ Wraps user-provided open() """
        return self.open(path.decode(), info_ptr.contents)

    def _readdir(self, path, target):
        """ Wraps user-provided readdir() """

        result = self.readdir(path.decode())

        if isinstance(result, (tuple, list)):
            target[0] = self.bridge.make_string_array(result[1])
            return result[0]
        elif isinstance(result, int):
            return result

        target[0] = self.bridge.make_string_array(result)
        return 0

    def _getattr(self, path, attributes_ptr):
        """ Wraps user-provided getattr() """

        result = self.getattr(path.decode())

        if isinstance(result, (tuple, list)):
            retval, attributes = result
        elif isinstance(result, int):
            return result
        else:
            retval, attributes = 0, result

        #pylint: disable=protected-access
        for field in attributes._fields_:
            val = getattr(attributes, field[0])
            setattr(attributes_ptr.contents, field[0], val)

        return retval

    def _access(self, path, mask):
        """ Wraps user-provided access() """
        return self.access(path.decode(), mask)

    def _read(self, path, target, size, offset, info_ptr):
        #pylint: disable=too-many-arguments
        """ Wraps user-provided read() """

        result = self.read(path.decode(), size, offset, info_ptr.contents)

        if isinstance(result, (tuple, list)):
            self.bridge.load_string_ptr(target, result[1])
            return result[0]
        elif isinstance(result, int):
            return result

        self.bridge.load_string_ptr(target, result)
        return 0

    def _write(self, path, data, size, offset, info_ptr):
        #pylint: disable=too-many-arguments
        """ Wraps user-provided write() """

        write_data = self.bridge.unload_bytes(data, size)
        return self.write(path.decode(), write_data, offset, info_ptr.contents)

    def _truncate(self, path, size):
        """ Wraps user-provided truncate() """

        return self.truncate(path.decode(), size)


    def main(self, argv=()):
        """ Launches FUSE filesystem. Returns when the filesystem is dismounted
        or FUSE is otherwise terminated. """

        assert isinstance(argv, (list, tuple))
        return self.bridge.main(argv)

    def open(self, path, info):
        # pylint: disable=unused-argument, no-self-use
        """ Opens a file. Should return 0 on success, and something else
        otherwise. """

        sys.stderr.write("'Open' not implemented in this filesystem.\n")
        return -1

    def readdir(self, path):
        # pylint: disable=unused-argument, no-self-use
        """ Reads the contents of a directory. Should return a tuple
        of (retval, contents), where 'contents' is a list or tuple of
        entries in the directory. """

        sys.stderr.write("'Readdir' not implemented in this filesystem.\n")
        return -1, []

    def getattr(self, path):
        # pylint: disable=unused-argument, no-self-use
        """ Gets the attributes of a path. Should return a tuple of
        (retval, attributes), where 'attributes' is a FileAttributes()
        instance. """

        sys.stderr.write("'Getattr' not implemented in this filesystem.\n")
        return -1, FileAttributes()

    def access(self, path, mask):
        # pylint: disable=unused-argument, no-self-use
        """ Returns 0 if a path can be accessed with the provided mask,
        -ENOENT if the path is nonexistent, or -EACCES if the path exists
        but can't be accessed with the target mask. """

        sys.stderr.write("'Access' not implemented in this filesystem.\n")
        return -1

    def read(self, path, size, offset, info):
        # pylint: disable=unused-argument, no-self-use
        """ Reads some data from a file. Should return a tuple of
        (retval, data), where 'data' is a string/bytes instance. Retval
        should be the length of the returned string, 0 if at EOF, or -1
        in the event of an error. """

        sys.stderr.write("'Read' not implemented in this filesystem.\n")
        return -1, ""

    def write(self, path, data, offset, info):
        # pylint: disable=unused-argument, no-self-use, too-many-arguments
        """ Writes some data to a file. Should return the number of bytes
        written (generally retval should equal len(data)), or -1 in the event
        of an error. 'Offset' is the target offset into the file. """

        sys.stderr.write("'Write' not implemented in this filesystem.\n")
        return -1

    def truncate(self, path, size):
        # pylint: disable=unused-argument, no-self-use, too-many-arguments
        """ Truncates a file to a given size. Should return 0 on success
        or a negative number in the event of an error. """

        sys.stderr.write("'Truncate' not implemented in this filesystem.\n")
        return -1

def main():
    """ Launches dummy filesystem. This filesystem won't do anything
    except for complain at you. """

    dummy_filesystem = BasicFs()
    dummy_filesystem.main(sys.argv)


if __name__ == "__main__":
    main()
