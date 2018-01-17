Pyfuse: A tool for simple FUSE Filesystems

## Introduction ##

Pyfuse is a Python 3-based library for making easy-to-write FUSE filesystems.
It uses Python's ctypes module and your system's C compiler to generate a
portable bridge library at import time, and then hooks into all of the FUSE
interfaces that you need to get a basic filesystem up and running.

The basic idea is that Pyfuse hides most of the FUSE weirdness and ctypes
weirdness, and allows you to get down to the business of implementing
your filesystem.

## Naming ##

There's a name collision with the other Pyfuse module. I know.

## Requirements ##

Pyfuse has been tested and works on Fedora, Ubuntu, and MacOS. It'll probably
work on just about anything with Python 3.4+, a FUSE installation (libfuse and
libfuse-dev on Linux, OSXFUSE on MacOS), a C compiler, and a set of system
headers (you'll need to install the XCode CLI tools on MacOS to get these).

## Current Status ##

At present, Pyfuse is working and has been functionally tested. There are no
known bugs, although I might eventually add ioctl support. There's a sample
filesystem implemented in hello.py.

Use with pride!
