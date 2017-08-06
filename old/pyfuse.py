#!/usr/bin/env python3

from ctypes import *
from constantfinder import ShelvedConstantFinder
from structfinder import StructFinder

ERRNO_CONSTANTS = ShelvedConstantFinder(
    "errno.shelf",
    "/usr/include/asm-generic/errno-base.h"
)

FCNTL_CONSTANTS = ShelvedConstantFinder(
    "fcntl.shelf",
    "/usr/include/asm-generic/fcntl.h"
)

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
                ("lock_owner", c_uint64)]

OPENFUNC = CFUNCTYPE(c_int, c_char_p, POINTER(FUSEFILEINFO))

#----------------------------------------------------------------------#

fields = StructFinder("/usr/include/sys/types.h", "timespec").members
stat_field_list = []


#----------------------------------------------------------------------#

stat_fields = StructFinder("/usr/include/sys/stat.h", "stat").members
stat_field_list = []
for field in stat_fields:
    entry = {}
    dtype = field[0]
    dtype = dtype.replace("static ","").replace("const ","")
    dtype = dtype.replace("volatile ","")
    is_struct = dtype[0:len("struct ")] == "struct "
    matches = re.findall("\[[0-9]*\]"

    if len(matches) == 0:
        length = 1
    elif len(matches) == 1:
        length = int(re.sub("[\[\] ]", "", matches[0]))
    else:
        raise ValueError("Multidimensional arrays are not supported.")

    name = field[0]
    
    entry['type'] = field[0]
    entry['struct'] = field[0][0:len("struct ")] == "struct "
    

for entry in stat_fields:
    print(entry)


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
