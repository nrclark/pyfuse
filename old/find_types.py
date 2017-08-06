#!/usr/bin/env python3

import re
import subprocess
import os

class TypeFinder(object):
    def __init__(self, header = "/usr/include/sys/types.h"):
        command = ["cpp", os.path.realpath(header)]
        result = subprocess.check_output(command).decode().strip()

        result = result.replace("\r","\n")
        result = result.replace("\t"," ")
        result = re.sub("^ +", "", result, flags=re.M)
        result = re.sub(" +$", "", result, flags=re.M)
        result = re.sub("^[#].*?$", "", result, flags=re.M)
        result = re.sub("[\n]+","\n", result, flags=re.M)
        result = re.sub(" *[[] *","[", result)
        result = re.sub(" *[]] *","]", result)
        result = result.replace("\n"," ")
        result = re.sub(" +"," ", result)
        result = "; " + result.strip() + ";"
        print(result)

brackets_regex = "[a-zA-Z
"""
print(re.sub("[\n]+","\n",q))

cpp /usr/include/sys/types.h | 
grep -v "^#" | 
sed '/^$/N;/^\n$/D' |
 tr "\n" " " | 
 sed -r 's/\t/  /g' | 
 sed -r 's/ +/ /g'

"""

def main():
    x = TypeFinder()

if __name__ == "__main__":
    main()
