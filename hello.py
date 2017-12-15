#!/usr/bin/env python3

import sys
import os
import ctypes as ct
import compiler_tools as tools
import pyfuse

class HelloFs(object):
    def __init__(self):
        self.hello_str = "Hello World!\n"
        self.hello_path = "/hello"
        self.bridge = pyfuse.FuseBridge()

    def open(self, path, info):
        assert isinstance(path, str)
        assert isinstance(info, pyfuse.FileInfo)

        if path != hello_path:
            return -Errno.ENOENT

        if (info.flags & 0x03) != Flags.O_RDONLY:
            return -Errno.EACCES

        return 0

    def readdir(self, path, target):
        assert isinstance(path, str)
        assert isinstance(target, ct.POINTER(ct.POINTER(ct.c_char_p)))

        results = [".", "..", self.hello_path[1:], "moto"]
        target[0] = self.bridge.make_string_array(results)
        return 0

    def getattr(self, path, attributes):
        assert isinstance(path, bytes)
        assert isinstance(attributes, ct.POINTER(pyfuse.FileAttributes))
        path = path.decode()
        attributes.uid = os.getuid()
        attributes.gid = os.getgid()
        attributes.size = 42

        if path == "/":
            attributes.mode = tools.STAT_CONSTANTS["S_IFDIR"] | 755
        elif path == self.hello_path:
            attributes.mode = tools.STAT_CONSTANTS["S_IFREG"] | 444
        elif path == "/moto":
            attributes.mode = tools.STAT_CONSTANTS["S_IFDIR"] | 755
        elif path == "/moto/hello":
            attributes.mode = tools.STAT_CONSTANTS["S_IFREG"] | 444
        else:
            return -tools.ERRNO_CONSTANTS["ENOENT"]
        return 0

    def read(self, path, target, size, offset, info):
        assert isinstance(path, str)
        assert isinstance(target, ct.POINTER(ct.c_char))
        assert isinstance(size, int)
        assert isinstance(offset, int)
        assert isinstance(info, bridge.FileInfo)

        length = len(self.hello_str)

        if path != self.hello_path:
            return -tools.ERRNO_CONSTANTS["ENOENT"]

        if offset >= length:
            return 0

        size = min(size, length - offset)
        self.bridge.load_string_ptr(self.hello_str[offset:offset + size], target)

        return size

    def write(self, path, data, size, offset, info):
        assert isinstance(path, str)
        assert isinstance(data, str)
        assert isinstance(size, int)
        assert isinstance(offset, int)
        assert isinstance(info, bridge.FileInfo)

        print("Wrote [%s] to file [%s]\n", data, path)
        return size

    def main(self, argv=()):
        assert isinstance(argv, (list, tuple))

        self.bridge.callbacks.open = pyfuse.OpenPtrType(self.open)
        self.bridge.callbacks.readdir = pyfuse.ReadDirPtrType(self.readdir)
        self.bridge.callbacks.getattr = pyfuse.GetAttrPtrType(self.getattr)
        self.bridge.callbacks.read = pyfuse.ReadPtrType(self.read)
        self.bridge.callbacks.write = pyfuse.WritePtrType(self.write)

        return self.bridge.main(argv)

def main():
    fs = HelloFs()
    sys.exit(fs.main(sys.argv))

if __name__ == "__main__":
    main()
