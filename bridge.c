#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/types.h>

#define FUSE_USE_VERSION 26
#include <fuse/fuse.h>

#include "bridge.h"

struct callbacks python_callbacks = {NULL};

/*----------------------------------------------------------------------------*/

void *zalloc(size_t size)
{
    return calloc(1, size);
}

void zfree(void *ptr)
{
    free(ptr);
}

/*----------------------------------------------------------------------------*/

static void load_file_info(const struct fuse_file_info *in,
                           struct file_info *out)
{
    out->handle = in->fh;
    out->flags = in->flags;
    out->direct_io = in->direct_io;
    out->nonseekable = in->nonseekable;
}

static void unload_file_info(const struct file_info *in,
                             struct fuse_file_info *out)
{
    out->fh = in->handle;
    out->flags = in->flags;
    out->direct_io = in->direct_io;
    out->nonseekable = in->nonseekable;
}

static void load_attributes(const struct stat *in,
                            struct file_attributes *out)
{
    out->mode = in->st_mode;
    out->uid = in->st_uid;
    out->gid = in->st_gid;
    out->size = in->st_size;
}

static void unload_attributes(const struct file_attributes *in,
                              struct stat *out)
{
    out->st_mode = in->mode;
    out->st_uid = in->uid;
    out->st_gid = in->gid;
    out->st_size = in->size;
}

/*----------------------------------------------------------------------------*/

static int bridge_open(const char *path, struct fuse_file_info *fi)
{
    int retval;
    struct file_info info = {0};

    if (python_callbacks.open == NULL) {
        return -EPERM;
    }

    load_file_info(fi, &info);
    retval = python_callbacks.open(path, &info);
    unload_file_info(&info, fi);

    return retval;
}

#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-parameter"
static int bridge_readdir(const char *path, void *buf,
                          fuse_fill_dir_t filler, off_t offset,
                          struct fuse_file_info *fi)
{
    int retval;
    char **entries = NULL;

    if (python_callbacks.readdir == NULL) {
        return -EPERM;
    }

    retval = python_callbacks.readdir(path, &entries);

    if (entries == NULL) {
        return -ENOENT;
    }

    for (uint32_t x = 0; entries[x] != NULL; x++) {
        if (filler(buf, entries[x], NULL, 0) != 0) {
            retval = -EIO;
            break;
        }
        free(entries[x]);
    }

    free(entries);
    return retval;
}
#pragma GCC diagnostic pop

static int bridge_getattr(const char *path, struct stat *stbuf)
{
    int retval;
    struct file_attributes attributes = {0};

    if (python_callbacks.getattr == NULL) {
        return -EPERM;
    }

    load_attributes(stbuf, &attributes);
    retval = python_callbacks.getattr(path, &attributes);

    if (retval != -ENOENT) {
        stbuf->st_nlink = 1;
        unload_attributes(&attributes, stbuf);
    }

    return retval;
}

static int bridge_read(const char *path, char *buf, size_t size,
                       off_t offset, struct fuse_file_info *fi)
{
    int retval;
    struct file_info info = {0};

    if (python_callbacks.read == NULL) {
        return -EPERM;
    }

    load_file_info(fi, &info);
    retval = python_callbacks.read(path, buf, size, offset, &info);
    unload_file_info(&info, fi);

    return retval;
}

static int bridge_write(const char *path, const char *buf, size_t size,
                        off_t offset, struct fuse_file_info *fi)
{
    int retval;
    struct file_info info = {0};

    if (python_callbacks.write == NULL) {
        return -EPERM;
    }

    load_file_info(fi, &info);
    retval = python_callbacks.write(path, buf, size, offset, &info);
    unload_file_info(&info, fi);

    return retval;
}

static struct fuse_operations bridge_oper = {
    .getattr = bridge_getattr,
    .readdir = bridge_readdir,
    .open = bridge_open,
    .read = bridge_read,
    .write = bridge_write
};

int bridge_main(int argc, char *argv[])
{
    int result = fuse_main(argc, argv, &bridge_oper, NULL);
    for (int x = 0; x < argc; x++) {
        zfree(argv[x]);
    }

    zfree(argv);
    return result;
}

/*--------------------------------------------------------------------*/

int debug_write(char *string)
{
    int result = strnlen(string, 1024);
    printf("debug: [%s]\n", string);
    return result;
}

