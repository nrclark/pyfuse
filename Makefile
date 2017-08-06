LIBRARY_NAME := bridge
SO_OBJECT := lib$(LIBRARY_NAME).so
LIBSRC := bridge.c bridge.h

CC ?= gcc
OBJFLAGS ?= $(CFLAGS) -D_FILE_OFFSET_BITS=64 -fPIC -shared
OBJFLAGS += -Wall -Wextra -pedantic -Werror

OBJFLAGS := $(strip $(OBJFLAGS))

$(SO_OBJECT): $(LIBSRC)
	gcc $^ -o $@ $(OBJFLAGS)

clean:
	rm -rf $(SO_OBJECT)
