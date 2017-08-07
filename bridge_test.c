#include <stdint.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>

typedef void * (*alloc_ptr)(size_t size);
typedef int (*readdir_ptr)(char ***entries, alloc_ptr allocator);

struct python_callbacks {
    readdir_ptr readdir;
};

struct python_callbacks callbacks = {NULL};

void *zalloc(size_t size)
{
    return calloc(1, size);
}

int dummy_function(void)
{
    int retval;
    char **entries = NULL;

    if (callbacks.readdir == NULL) {
        return -EPERM;
    }

    retval = callbacks.readdir(&entries, zalloc);

    if (entries == NULL) {
        printf("No entries.\n");
        return -ENOENT;
    }

    for(uint32_t x = 0; entries[x] != NULL; x++) {
        printf("Entry #%d: %s\n", x, entries[x]);
        free(entries[x]);
    }

    free(entries);
    return retval;
}
