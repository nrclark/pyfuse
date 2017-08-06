#!/usr/bin/env python3

import re
import copy
import tempfile
import subprocess
import os
import ast
import shelve    
    
class StructFinder(object):
    def __init__(self, header, struct):
        self.header = header
        self.struct = struct
        self.members = self._find_members()

    def _find_members(self):
        command = ["cpp", os.path.realpath(self.header)]
        result = subprocess.check_output(command).decode().strip()
        result = re.sub("^[#].*?$","", result, flags=re.M)
        result = result.replace("\t"," ")
        result = re.sub("^ +","", result, flags=re.M)
        result = re.sub("\n+","\n", result, flags=re.M)
        result = re.sub(" +"," ", result)
        
        regex = "struct %s[ \t\n]+[{].*?[}]" % self.struct
        result = re.findall(regex, result, flags=re.DOTALL)[0]

        result = re.sub("^.*?[{]","", result, flags=re.DOTALL)
        result = re.sub("[}].*?$","", result, flags=re.DOTALL)
        result = result.strip().splitlines()
        result = [x.strip().split() for x in result]
        result = [[' '.join(x[:-1]), x[-1][:-1]] for x in result]
        return result

def GetSize(dtype, headers = []):
    template = """
    #include <stdio.h>
    #include <stddef.h>
    #include <stdlib.h>
    #include <stdint.h>
    %INCLUDES%
    
    int main(void) {
        printf("%u\\n", sizeof(%DTYPE%));
        return 0;
    }
    """
    include_string = ['#include "%s"' % x for x in headers]
    include_string = '\n'.join(include_string)

    source = template.replace("%INCLUDES%", include_string)
    source = source.replace("%DTYPE%", dtype)

    fd, filename = tempfile.mkstemp(dir='.', suffix='.c')
    binary = filename + '.bin'
    os.write(fd, source.encode())
    os.close(fd)

    try:
        subprocess.check_call(["cc", filename, "-o", binary])
        result = subprocess.check_output([binary]).decode().strip()
        result = ast.literal_eval(result)

    except subprocess.CalledProcessError:
        result = None

    for name in [binary, filename]:
        if os.path.isfile(name):
            os.remove(name)

    return result

def GetMemberSize(struct, member, headers = []):
    template = """
    #include <stdio.h>
    #include <stddef.h>
    #include <stdlib.h>
    #include <stdint.h>
    %INCLUDES%
    
    %STRUCT% dummy;
    int main(void) {
        printf("%u\\n", sizeof(dummy.%MEMBER%));
        return 0;
    }
    """
    include_string = ['#include "%s"' % x for x in headers]
    include_string = '\n'.join(include_string)

    source = template.replace("%INCLUDES%", include_string)
    source = source.replace("%STRUCT%", struct)
    source = source.replace("%MEMBER%", member)

    fd, filename = tempfile.mkstemp(dir='.', suffix='.c')
    binary = filename + '.bin'
    os.write(fd, source.encode())
    os.close(fd)

    try:
        subprocess.check_call(["cc", filename, "-o", binary])
        result = subprocess.check_output([binary]).decode().strip()
        result = ast.literal_eval(result)

    except subprocess.CalledProcessError:
        result = None

    for name in [binary, filename]:
        if os.path.isfile(name):
            os.remove(name)

    return result


def main():
    x = StructFinder("/usr/include/sys/stat.h", "stat")
    members = x._find_members()
    members = [x[1] for x in members]

    for member in members:
        size = GetMemberSize("struct stat", member, ["/usr/include/sys/stat.h"])
        print("%s: %d bytes" % (member, size))

    dtype = "off_t"
    size = GetSize(dtype)
    print("%s: %d bytes" % (dtype, size))

if __name__ == "__main__":
    main()
