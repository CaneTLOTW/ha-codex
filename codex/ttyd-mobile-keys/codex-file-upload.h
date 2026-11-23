/* Codex HA Developer: bounded file/folder uploads over the existing authenticated
 * ttyd ingress WebSocket. No new endpoint or browser-selected filesystem path.
 * File requests: '6' + 32 lowercase hex batch ID + uint16 big-endian relative
 * path length + UTF-8 relative path + file bytes (max 10 MiB per file).
 * Reply: '6' + absolute private path, or '7' + safe failure category.
 */
#ifndef CODEX_HA_FILE_UPLOAD_H
#define CODEX_HA_FILE_UPLOAD_H

#include "codex-image-paste.h"

#define CODEX_FILE_WS_REQUEST '6'
#define CODEX_FILE_WS_REPLY '6'
#define CODEX_FILE_WS_ERROR '7'
#define CODEX_FILE_MAX_SIZE (10u * 1024u * 1024u)
#define CODEX_FILE_PATH_MAX 480u
#define CODEX_FILE_FRAME_MAX (CODEX_FILE_MAX_SIZE + 35u + CODEX_FILE_PATH_MAX)

static const char *codex_file_error_code(int error) {
  if (error == EINVAL) return "INVALID_FILE";
  if (error == ENAMETOOLONG) return "PATH_TOO_LONG";
  if (error == EEXIST) return "ALREADY_EXISTS";
  if (error == EFBIG) return "TOO_LARGE";
  return codex_image_error_code(error);
}

/* Never follow symlinks, including all intermediate folders. Upload folder
 * identity comes from a random client-side batch ID; the recipient stays
 * pinned to the private home directory regardless of any client path. */
static int codex_file_open_child_dir(int parent_fd, const char *name) {
  if (mkdirat(parent_fd, name, 0700) == 0) {
    if (fchownat(parent_fd, name, 22000, 0, AT_SYMLINK_NOFOLLOW) != 0) return -1;
  } else if (errno != EEXIST) {
    return -1;
  }

  int child = openat(parent_fd, name, O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
  if (child < 0) return -1;
  struct stat st;
  if (fstat(child, &st) != 0 || !S_ISDIR(st.st_mode) ||
      st.st_uid != 22000 || (st.st_mode & 0077) != 0 ||
      (st.st_mode & 0700) != 0700) {
    close(child);
    errno = EACCES;
    return -1;
  }
  return child;
}

static int codex_file_valid_path(const unsigned char *path, size_t len) {
  if (!path || len == 0 || len > CODEX_FILE_PATH_MAX || path[0] == '/' ||
      path[len - 1] == '/') return 0;
  size_t part_start = 0;
  int depth = 0;
  for (size_t i = 0; i <= len; i++) {
    if (i < len && path[i] != '/') {
      unsigned char c = path[i];
      if (c < 32 || c == 127 || c == '\\') return 0;
      continue;
    }
    size_t n = i - part_start;
    if (n == 0 || n > 120 || (n == 1 && path[part_start] == '.') ||
        (n == 2 && path[part_start] == '.' && path[part_start + 1] == '.'))
      return 0;
    if (++depth > 8) return 0;
    part_start = i + 1;
  }
  return 1;
}

static int codex_file_save(const unsigned char *payload, size_t len,
                           char *result, size_t result_cap) {
  /* Validate complete frame before touching disk. */
  if (!payload || len < 36 || len > CODEX_FILE_FRAME_MAX) {
    errno = EINVAL;
    return -1;
  }
  char batch[40];
  memcpy(batch, payload, 32);
  batch[32] = '\0';
  for (size_t i = 0; i < 32; i++) {
    if (!((batch[i] >= '0' && batch[i] <= '9') ||
          (batch[i] >= 'a' && batch[i] <= 'f'))) {
      errno = EINVAL;
      return -1;
    }
  }
  size_t path_len = ((size_t)payload[32] << 8) | (size_t)payload[33];
  if (path_len == 0 || path_len > CODEX_FILE_PATH_MAX ||
      len < 34 + path_len || len - 34 - path_len > CODEX_FILE_MAX_SIZE ||
      !codex_file_valid_path(payload + 34, path_len)) {
    errno = EINVAL;
    return -1;
  }

  char relative[CODEX_FILE_PATH_MAX + 1];
  memcpy(relative, payload + 34, path_len);
  relative[path_len] = '\0';
  int fd = codex_image_open_upload_dir();
  if (fd < 0) return -1;

  char folder[48];
  snprintf(folder, sizeof(folder), "upload-%s", batch);
  int child = codex_file_open_child_dir(fd, folder);
  int err = errno;
  close(fd);
  if (child < 0) {
    errno = err;
    return -1;
  }
  fd = child;
  char *part = relative;
  for (char *p = relative; *p; p++) {
    if (*p != '/') continue;
    *p = '\0';
    child = codex_file_open_child_dir(fd, part);
    err = errno;
    close(fd);
    if (child < 0) {
      errno = err;
      return -1;
    }
    fd = child;
    *p = '/';
    part = p + 1;
  }

  int out = openat(fd, part, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600);
  if (out < 0) {
    err = errno;
    close(fd);
    errno = err;
    return -1;
  }
  const unsigned char *body = payload + 34 + path_len;
  const size_t file_len = len - 34 - path_len;
  int status = -1;
  if (fchown(out, 22000, 0) != 0 || fchmod(out, 0600) != 0) goto finish;
  for (size_t offset = 0; offset < file_len;) {
    ssize_t count = write(out, body + offset, file_len - offset);
    if (count < 0 && errno == EINTR) continue;
    if (count <= 0) goto finish;
    offset += (size_t)count;
  }
  if (snprintf(result, result_cap,
      "/data/codex-home/users/anonymous/.codex/uploads/%s/%s", folder, relative)
      >= (int)result_cap) {
    errno = ENAMETOOLONG;
    goto finish;
  }
  status = 0;

finish:
  err = errno;
  close(out);
  if (status != 0) unlinkat(fd, part, 0);
  close(fd);
  if (status != 0) errno = err;
  return status;
}

#endif
