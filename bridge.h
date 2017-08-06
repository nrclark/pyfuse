#ifndef _BRIDGE_H_
#define _BRIDGE_H_

#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>

/*--------------------------------------------------------------------*/

struct file_info {
    uint64_t handle;
    uint32_t flags;
    bool direct_io;
    bool nonseekable;
};

struct file_attributes {
    uint64_t size;
    uint32_t mode;
    uint32_t uid;
    uint32_t gid;
};

/*--------------------------------------------------------------------*/

/* Returns values of the form 0 (success), -ENOENT, -EACCES, etc.
 * 
 * The "file_info" struct will arrive with whatever values were
 * set inside of the fuse "fuse_file_info" struct. After the
 * callback has completed, the members of *info will be loaded
 * back into the fuse struct. */

typedef int (*python_open_ptr)(const char *path,
                               struct file_info *info);

/* Returns values of the form 0 (success), -ENOENT, -EACCES, etc.
 * 
 * The 'entries' record should be pointed to a 2-D array (created
 * by Python). The Python function that supplies this should use
 * the provided allocator to allocate all memory. The memory will
 * be freed at the end of the C routine. */

typedef void * (*alloc_ptr)(size_t size);

typedef int (*python_readdir_ptr)(const char *path, char ***entries,
                                  alloc_ptr allocator);

/* Returns values of the form 0 (success), -ENOENT, -EACCES, etc. 
 * 
 * The 'attributes' struct will arrive pre-loaded with whatever
 * values FUSE uses as a default. After the callback the equivalent
 * FUSE struct will be re-populated. */

typedef int (*python_getattr_ptr)(const char *path,
                                  struct file_attributes *attr);

/* Returns values of the form 0 (success), -ENOENT, -EACCES, etc.
 * 
 * The "file_info" struct will arrive with whatever values were
 * set inside of the fuse "fuse_file_info" struct. After the
 * callback has completed, the members of *info will be loaded
 * back into the fuse struct. */

typedef int (*python_read_ptr)(const char *path, char *outbuf,
                               uint64_t size, uint64_t offset,
                               struct file_info *info);

/* Returns values of the form 0 (success), -ENOENT, -EACCES, etc.
 * 
 * The "file_info" struct will arrive with whatever values were
 * set inside of the fuse "fuse_file_info" struct. After the
 * callback has completed, the members of *info will be loaded
 * back into the fuse struct. */

typedef int (*python_write_ptr)(const char *path, const char *inbuf,
                                uint64_t size, uint64_t offset,
                                struct file_info *info);

/*--------------------------------------------------------------------*/

struct callbacks {
    python_open_ptr open;
    python_readdir_ptr readdir;
    python_getattr_ptr getattr;
    python_read_ptr read;
    python_write_ptr write;
};

/*--------------------------------------------------------------------*/

extern struct callbacks python_callbacks;
int bridge_main(int argc, char *argv[]);

#endif
