#include <stdint.h>

struct file_info {
    uint64_t handle;
    uint32_t flags;
    bool direct_io;
    bool nonseekable;
}

struct file_attributes {
    uint32_t mode;
    uint32_t uid;
    uint32_t gid;
    uint64_t size;
}

/* Returns values of the form 0 (success), -ENOENT, -EACCES, etc.
 * 
 * The "file_info" struct will arrive with whatever values were
 * set inside of the fuse "fuse_file_info" struct. After the
 * callback has completed, the members of *info will be loaded
 * back into the fuse struct. */

int file_open(const char *path, int flags, struct file_info *info);

typedef int (*file_open_ptr)(const char *path, int flags,
                             struct file_info *info);

/* Returns values of the form 0 (success), -ENOENT, -EACCES, etc.
 * 
 * The 'entries' record should be pointed to a 2-D array (created
 * by Python). After the readdir callback has been processed,
 * the Python part should block until file_readdir_ack() is called
 * to acknowledge that the data has been copied out (and is safe
 * for de-allocation). */

int file_readdir(const char *path, char *entries[][]);

typedef int (*file_readdir_ptr)(const char *path, char *entries[][]);

void file_readdir_ack();

typedef int (*file_readdir_ack_ptr)(void);

/* Returns values of the form 0 (success), -ENOENT, -EACCES, etc. 
 * 
 * The 'attributes' struct will arrive pre-loaded with whatever
 * values FUSE uses as a default. After the callback the equivalent
 * FUSE struct will be re-populated. */

int file_getattr(const char *path, struct attributes *attr);

typedef int (*file_getattr_ptr)(const char *path, struct attributes *attr);

/* Returns values of the form 0 (success), -ENOENT, -EACCES, etc.
 * 
 * The "file_info" struct will arrive with whatever values were
 * set inside of the fuse "fuse_file_info" struct. After the
 * callback has completed, the members of *info will be loaded
 * back into the fuse struct. */

int file_read(const char *path, char *outbuf, uint64_t size,
              uint64_t offset, struct file_info *info);

typedef int (*file_read_ptr)(const char *path, char *outbuf,
              uint64_t size, uint64_t offset, struct file_info *info);

/* Returns values of the form 0 (success), -ENOENT, -EACCES, etc.
 * 
 * The "file_info" struct will arrive with whatever values were
 * set inside of the fuse "fuse_file_info" struct. After the
 * callback has completed, the members of *info will be loaded
 * back into the fuse struct. */

int file_write(const char *path, const char *inbuf, uint64_t size,
               uint64_t offset, struct file_info *info);

typedef int (*file_write_ptr)(const char *path, const char *inbuf,
    uint64_t size, uint64_t offset, struct file_info *info);

