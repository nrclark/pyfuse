#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <sys/types.h>

#define FUSE_USE_VERSION 26
#include <fuse/fuse.h>

#define MIN(a,b) ((a) < (b) ? (a) : (b))

static const char *hello_str = "Hello World!\n";
static const char *hello_path = "/hello";

static int hello_open(const char *path, struct fuse_file_info *fi)
{
    if (strcmp(path, hello_path) != 0) {
        return -ENOENT;
    }

    if ((fi->flags & 3) != O_RDONLY) {
        return -EACCES;
    }

    return 0;
}

static int hello_readdir(const char *path, void *buf,
                         fuse_fill_dir_t filler, off_t offset,
                         struct fuse_file_info *fi)
{
    //if (strcmp(path, "/") != 0)
    //  return -ENOENT;

    filler(buf, ".", NULL, 0);
    filler(buf, "..", NULL, 0);
    filler(buf, hello_path + 1, NULL, 0);
    filler(buf, "moto", NULL, 0);
    return 0;
}

static int hello_getattr(const char *path, struct stat *stbuf)
{
    memset(stbuf, 0, sizeof(struct stat));
    stbuf->st_uid = getuid();
    stbuf->st_gid = getgid();

    if (strcmp(path, "/") == 0) {
        stbuf->st_mode = S_IFDIR | 0755;
        stbuf->st_nlink = 2;
    } else if (strcmp(path, hello_path) == 0) {
        stbuf->st_mode = S_IFREG | 0444;
        stbuf->st_nlink = 1;
        stbuf->st_size = strlen(hello_str);
    } else if (strcmp(path, "/moto") == 0) {
        stbuf->st_nlink = 1;        
        stbuf->st_mode = S_IFDIR | 0755;
    } else if (strcmp(path, "/moto/hello") == 0) {
        stbuf->st_mode = S_IFREG | 0444;
        stbuf->st_nlink = 1;
        stbuf->st_size = strlen(hello_str);
    }


    return stbuf->st_nlink ? 0 : -ENOENT;
}

static int hello_read(const char *path, char *buf, size_t size,
                      off_t offset, struct fuse_file_info *fi)
{
    size_t len = strlen(hello_str);

    if (strcmp(path, hello_path) != 0)
        return -ENOENT;

    if (offset > len)
        return 0;

    size = MIN(size, len - offset);
    memcpy(buf, hello_str + offset, size);

    return size;
}

static struct fuse_operations hello_oper = {
    .getattr = hello_getattr,
    .readdir = hello_readdir,
    .open = hello_open,
    .read = hello_read,
};

int main(int argc, char *argv[])
{
    return fuse_main(argc, argv, &hello_oper, NULL);
}