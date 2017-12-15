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
        assert isinstance(path, bytes)
        assert isinstance(info, ct.POINTER(pyfuse.FileInfo))

        path = path.decode()

        if path != self.hello_path:
            return -tools.ERRNO_CONSTANTS["ENOENT"]

        if (info.contents.flags & 0x03) != tools.FCNTL_CONSTANTS["O_RDONLY"]:
            print("This filesystem is read-only")
            return -tools.ERRNO_CONSTANTS["EACCES"]

        return 0

    def readdir(self, path, target):
        assert isinstance(path, bytes)
        assert isinstance(target, ct.POINTER(ct.POINTER(ct.c_char_p)))

        results = [".", "..", self.hello_path[1:], "moto"]
        target[0] = self.bridge.make_string_array(results)
        return 0

    def getattr(self, path, attributes):
        assert isinstance(path, bytes)
        assert isinstance(attributes, ct.POINTER(pyfuse.FileAttributes))

        path = path.decode()
        attributes.contents.uid = os.getuid()
        attributes.contents.gid = os.getgid()
        attributes.contents.size = 42
        if path == "/":
            attributes.contents.mode = tools.STAT_CONSTANTS["S_IFDIR"] | 0o755
        elif path == self.hello_path:
            attributes.contents.mode = tools.STAT_CONSTANTS["S_IFREG"] | 0o666
        elif path == "/moto":
            attributes.contents.mode = tools.STAT_CONSTANTS["S_IFDIR"] | 0o755
        elif path == "/moto/hello":
            attributes.contents.mode = tools.STAT_CONSTANTS["S_IFREG"] | 0o444
        else:
            return -tools.ERRNO_CONSTANTS["ENOENT"]
        return 0

    def read(self, path, target, size, offset, info):
        assert isinstance(path, bytes)
        assert isinstance(target, int)
        assert isinstance(size, int)
        assert isinstance(offset, int)
        assert isinstance(info, ct.POINTER(pyfuse.FileInfo))

        path = path.decode()

        if path != self.hello_path:
            return -tools.ERRNO_CONSTANTS["ENOENT"]

        length = len(self.hello_str)

        if offset >= length:
            return 0

        size = min(size, length - offset)
        self.bridge.load_string_ptr(target, self.hello_str[offset:offset + size])

        return size

    def write(self, path, data, size, offset, info):
        assert isinstance(path, bytes)
        assert isinstance(data, bytes)
        assert isinstance(size, int)
        assert isinstance(offset, int)
        assert isinstance(info, ct.POINTER(pyfuse.FileInfo))

        print("Wrote [%s] to file [%s]\n" % (data, path))
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
