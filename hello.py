#!/usr/bin/env python3

import bridge
from bridge import FuseBridge, load_string_array, Errno, Fcntl, Stat

hello_str = "Hello World!\n";
hello_path = "/hello";


def hello_open(path, info)
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
    load_string_array(results, target, allocator)
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


def main():
    bridge = FuseBridge()

if __name__ == "__main__":
    main()s

