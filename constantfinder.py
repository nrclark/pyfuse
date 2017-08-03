#!/usr/bin/env python3

import re
import tempfile
import subprocess
import os
import ast

class ConstantFinder(object):
	def __init__(self, header, includes = []):
		self.header = header
		self.includes = includes
		self.constants = self._detect_constants()
		
	def _find_constant_names(self):
		with open(self.header, 'r') as infile:
			data = infile.read()

		regex = "^[ \t]*[#]define[ \t]+[^ \t\n]+[ \t]+[^\t\n]+"
		defines = re.findall(regex, data, flags=re.M)
		defines = [x.split() for x in defines]
		defines = [[y.strip() for y in x] for x in defines]
		defines = [x[1] for x in defines]
		defines = [x for x in defines if '(' not in x]

		return defines

	def _get_constant(self, constant):
		template = """
		#include <stdio.h>
		#include <stddef.h>
		#include <stdlib.h>
		#include <stdint.h>
		%INCLUDES%

		int main(void) {
			printf("%lld\\n", (long long int)(%CONSTANT%));
			return 0;
		}
		"""
		includes = self.includes + [self.header]
		include_string = ['#include "%s"' % x for x in includes]
		include_string = '\n'.join(include_string)

		source = template.replace("%INCLUDES%", include_string)
		source = source.replace("%CONSTANT%", constant)

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

	def _detect_constants(self):
		constants = self._find_constant_names()
		result = {}

		for constant in constants:
			result[constant] = self._get_constant(constant)

		return result

def main():
	#x = ConstantFinder("/usr/include/linux/fuse.h", ["asm/ioctl.h"])
	x = ConstantFinder("/usr/include/asm-generic/fcntl.h")

	for constant in x.constants:
		print(constant, x.constants[constant], type(x.constants[constant]))

if __name__ == "__main__":
	main()
