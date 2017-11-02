#!/usr/bin/env python3

import sys
import bridge
from bridge import FuseBridge, Errno, Fcntl, Stat
from bridge import create_char_array, load_char_ptr


hello_str = "Hello World!\n"
hello_path = "/hello"


def hello_open(path, info):
    assert isinstance(info, bridge.FileInfo)
    assert isinstance(path, str)

    if path != hello_path:
        return -Errno.ENOENT

    if (info.flags & 0x03) != Flags.O_RDONLY:
        return -Errno.EACCES

    return 0


def hello_readdir(path, target, allocator):
    assert isinstance(info, bridge.FileInfo)
    assert isinstance(target, bridge.char_triple_ptr)
    assert isinstance(allocator, bridge.AllocPtrType)

    results = [".", "..", hello_path[1:], "moto"]
    target[0] = create_char_array(results, target, allocator)
    return 0


def hello_getattr(path, attributes):
    assert isinstance(path, str)
    assert isinstance(attributes, bridge.FileAttributes)

    attributes.uid = os.getuid()
    attributes.gid = os.getgid()
    attributes.size = 42

    if path == "/":
        attributes.mode = Stat.S_IFDIR | 0755
    elif path == hello_path:
        attributes.mode = Stat.S_IFREG | 0444
    elif path == "/moto":
        attributes.mode = Stat.S_IFDIR | 0755
    elif path == "/moto/hello":
        attributes.mode = Stat.S_IFREG | 0444
    else
        return -Errno.ENOENT

    return 0


def hello_read(path, target, size, offset, info):
    assert isinstance(info, bridge.FileInfo)
    assert isinstance(target, bridge.char_ptr)
    assert isinstance(allocator, bridge.AllocPtrType)

    length = len(hello_str)

    if path != hello_path:
        return -Errno.ENOENT

    if offset >= length:
        return 0

    size = min(size, length - offset)
    load_char_ptr(hello_str[offset:offset + size], target)

    return size


def hello_main(argv):
    assert isinstance(argv, (list, tuple))

    fuse = FuseBridge()
    fuse.callbacks.open = fuse.types.OpenPtrType(hello_open)
    fuse.callbacks.readdir = fuse.types.ReadDirPtrType(hello_readdir)
    fuse.callbacks.getattr = fuse.types.GetAttrPtrType(hello_getattr)
    fuse.callbacks.read = fuse.types.ReadPtrType(hello_read)
    fuse.callbacks.write = fuse.types.WritePtrType(hello_write)

    argc = len(argv)
    argv_pointer = create_char_array(argv)

    return fuse.bridge_main(argc, argv_pointer)


def main():
    hello_main(sys.argv)

if __name__ == "__main__":
    main()
