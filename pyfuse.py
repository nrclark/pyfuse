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

ReadPtrType = ct.CFUNCTYPE(ct.c_int, ct.c_char_p, ct.c_void_p, ct.c_uint64,
                           ct.c_uint64, ct.POINTER(FileInfo))

WritePtrType = ct.CFUNCTYPE(ct.c_int, ct.c_char_p, ct.c_char_p, ct.c_uint64,
                            ct.c_uint64, ct.POINTER(FileInfo))

MainPtrType = ct.CFUNCTYPE(ct.c_int, ct.c_int, ct.POINTER(ct.c_char_p))
# pylint: enable=invalid-name


class Callbacks(ct.Structure):
    # pylint: disable=too-few-public-methods
    """ Equivalent structure to callbacks from bridge.h. Used to provide the
    callback interface from FUSE back into Python. """

    _fields_ = [("open", OpenPtrType),
                ("readdir", ReadDirPtrType),
                ("getattr", GetAttrPtrType),
                ("read", ReadPtrType),
                ("write", WritePtrType)]


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


class FuseBridge(object):
    """ Main bridge object for creating and connecting custom FUSE designs.
    At present, this class should be used by creating an instance,
    connecting callbacks, and launching main() with any arguments that
    should be passed down to fuse_main. """

    def __init__(self):
        self.bridge_lib = tools.compile_library('bridge.c')
        self.extern = ct.cdll.LoadLibrary(self.bridge_lib)
        self.callbacks = Callbacks.in_dll(self.extern, 'python_callbacks')
        self.result = None
        self.process = None

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


def main():
    """ Test routine. Shouldn't do anything interesting, broken at the
    current time. """
    fuse = FuseBridge()

    args = ["hello", "my dudes", "it is thursday!"]
    fuse.main(args)


if __name__ == "__main__":
    main()
