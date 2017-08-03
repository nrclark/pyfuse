#!/usr/bin/env python3

from ctypes import *
from constantfinder import ShelvedConstantFinder

ERRNO_CONSTANTS = ShelvedConstantFinder("errno.shelf", "/usr/include/asm-generic/errno-base.h")
FCNTL_CONSTANTS = ShelvedConstantFinder("fcntl.shelf", "/usr/include/asm-generic/fcntl.h")

class FUSEFILEINFO(Structure):
	_fields_ = [("flags", c_int),
				("fh_old", c_ulong),
				("writepage", c_int),
				("direct_io", c_uint, 1),
				("keep_cache", c_uint, 1),
				("flush", c_uint, 1),
				("nonseekable", c_uint, 1),
				("flock_release", c_uint, 1),
				("padding", c_uint, 27),
				("fh", c_uint64),
				("lock_owner", c_uint64),
				]

OPENFUNC = CFUNCTYPE(c_int, c_char_p, POINTER(FUSEFILEINFO))

#----------------------------------------------------------------------#

hello_str = "Hello World!\n"
hello_path = "/hello"

def py_hello_open(path, fi):
	if path != hello_path:
		return -1 * ERRNO_CONSTANTS["ENOENT"]

	if (fi[0].flags & 3) != FCNTL_CONSTANTS["O_RDONLY"]:
		return -1 * ERRNO_CONSTANTS["EACCES"]
	
	return 0

hello_open = CFUNCTYPE(py_hello_open)

class Fuse(object):
	def __init__(self):
		self.libfuse = ctypes.cdll.LoadLibrary("libfuse.so")
		
def main():
	pass

if __name__ == "__main__":
	main()
