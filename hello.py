#!/usr/bin/env python3
""" Module demonstrating the basics of working with this repo's pyfuse
bridge. Contains a sample filesystem and not much else. """

import sys
import os
import compiler_tools as tools
import pyfuse


class HelloFs(pyfuse.BasicFs):
    """ Basic demonstration filesystem for Pyfuse bridge. """

    def __init__(self):
        self.hello_str = "Hello World!\n"
        self.hello_path = "/hello"
        super(HelloFs, self).__init__()

    def open(self, path, info):
        if path != self.hello_path:
            return -tools.ERRNO_CONSTANTS["ENOENT"]

        if (info.flags & 0x03) != tools.FCNTL_CONSTANTS["O_RDONLY"]:
            print("This filesystem is read-only")
            return -tools.ERRNO_CONSTANTS["EACCES"]

        return 0

    def readdir(self, path):
        return 0, [".", "..", self.hello_path[1:], "moto"]

    def getattr(self, path):
        attributes = pyfuse.FileAttributes()

        attributes.uid = os.getuid()
        attributes.gid = os.getgid()
        attributes.size = 42

        if path == "/":
            attributes.mode = tools.STAT_CONSTANTS["S_IFDIR"] | 0o755
        elif path == self.hello_path:
            attributes.mode = tools.STAT_CONSTANTS["S_IFREG"] | 0o666
        elif path == "/moto":
            attributes.mode = tools.STAT_CONSTANTS["S_IFDIR"] | 0o755
        elif path == "/moto/hello":
            attributes.mode = tools.STAT_CONSTANTS["S_IFREG"] | 0o444
        else:
            return -tools.ERRNO_CONSTANTS["ENOENT"]

        return 0, attributes

    def read(self, path, size, offset, info):
        if path != self.hello_path:
            return -tools.ERRNO_CONSTANTS["ENOENT"], ""

        length = len(self.hello_str)

        if offset >= length:
            return 0

        return size, self.hello_str[offset:offset + size]

    def write(self, path, data, size, offset, info):
        #pylint: disable=too-many-arguments
        print("Wrote [%s] to file [%s]\n" % (data, path))
        return size


def main():
    """ Main routine for launching filesystem. """

    hello = HelloFs()
    sys.exit(hello.main(sys.argv))


if __name__ == "__main__":
    main()
