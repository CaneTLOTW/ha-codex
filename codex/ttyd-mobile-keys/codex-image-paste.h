/* Codex HA ttyd 1.7.7: authenticated PTY-WebSocket screenshot storage.
 * The sender cannot choose a destination. All output names are random.
 * Socket is only available through Home Assistant's authenticated ingress.
 * Run on the ttyd event loop; no separate port, file-upload HTTP endpoint,
 * shell execution or attacker-provided path.
 */
#ifndef CODEX_HA_IMAGE_PASTE_H
#define CODEX_HA_IMAGE_PASTE_H

#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/random.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#define CODEX_IMAGE_MAX_SIZE (10u * 1024u * 1024u)
#define CODEX_IMAGE_WS_REQUEST '4'
#define CODEX_IMAGE_WS_REPLY '4'
#define CODEX_IMAGE_WS_ERROR '5'

static int codex_image_open_upload_dir(void) {
  static const char *const dirs[] = {
      "codex-home", "users", "anonymous", ".codex", "uploads"};
  int fd = open("/data", O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
  if (fd < 0) return -1;

  for (size_t i = 0; i < sizeof(dirs) / sizeof(dirs[0]); i++) {
    int child = openat(fd, dirs[i], O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
    close(fd);
    if (child < 0) return -1;
    fd = child;
  }

  struct stat st;
  if (fstat(fd, &st) != 0 || !S_ISDIR(st.st_mode) ||
      st.st_uid != 22000 || (st.st_mode & 0077) != 0 ||
      (st.st_mode & 0700) != 0700) {
    close(fd);
    errno = EACCES;
    return -1;
  }
  return fd;
}

static int codex_image_save_png(const unsigned char *data, size_t len, char *result, size_t result_cap) {
  static const unsigned char png_magic[] = {137, 80, 78, 71, 13, 10, 26, 10};
  /* Minimal PNG signature and IHDR test; Codex decodes and validates the
   * complete image separately when the model attachment is processed.
   */
  if (!data || len < 33 || len > CODEX_IMAGE_MAX_SIZE ||
      memcmp(data, png_magic, sizeof(png_magic)) != 0 ||
      memcmp(data + 12, "IHDR", 4) != 0) {
    errno = EINVAL;
    return -1;
  }

  int dir_fd = codex_image_open_upload_dir();
  if (dir_fd < 0) return -1;

  unsigned char random_bytes[16];
  if (getrandom(random_bytes, sizeof(random_bytes), 0) != (ssize_t)sizeof(random_bytes)) {
    close(dir_fd);
    return -1;
  }
  char token[sizeof(random_bytes) * 2 + 1];
  for (size_t i = 0; i < sizeof(random_bytes); i++)
    snprintf(token + i * 2, 3, "%02x", random_bytes[i]);

  char name[64];
  snprintf(name, sizeof(name), "clipboard-%s.png", token);
  int fd = openat(dir_fd, name, O_CREAT | O_EXCL | O_WRONLY | O_CLOEXEC | O_NOFOLLOW, 0600);
  if (fd < 0) {
    close(dir_fd);
    return -1;
  }

  int status = -1;
  if (fchown(fd, 22000, 0) != 0 || fchmod(fd, 0600) != 0) goto done;
  size_t offset = 0;
  while (offset < len) {
    ssize_t n = write(fd, data + offset, len - offset);
    if (n < 0 && errno == EINTR) continue;
    if (n <= 0) goto done;
    offset += (size_t)n;
  }
  if (snprintf(result, result_cap,
               "/data/codex-home/users/anonymous/.codex/uploads/%s", name) >= (int)result_cap)
    goto done;
  status = 0;

done:
  close(fd);
  if (status != 0) unlinkat(dir_fd, name, 0);
  close(dir_fd);
  return status;
}

#endif
