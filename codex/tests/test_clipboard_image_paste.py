"""Developer-only live screenshot paste transport source regression checks.

Does not open user files, connect to Supervisor, or access the browser clipboard.
The image transport build is separately compiled with pinned ttyd 1.7.7 CI.
"""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config.yaml"
START = ROOT / "rootfs/usr/local/bin/codex-start"
DOCKERFILE = ROOT / "Dockerfile"
SOURCE = ROOT / "ttyd-mobile-keys"
HEADER = SOURCE / "codex-image-paste.h"
PATCH = SOURCE / "apply-image-paste.py"


class ClipboardImagePasteTests(unittest.TestCase):
    def test_developer_opt_in_and_security_boundary(self):
        options = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(options["name"], "Codex Deployment")
        self.assertEqual(options["version"], "0.5.0-dev.7")
        self.assertIs(options["options"]["clipboard_image_paste"], True)
        self.assertEqual(options["schema"]["clipboard_image_paste"], "bool")
        self.assertIs(options["options"]["file_transfer_enabled"], False)
        start = START.read_text(encoding="utf-8")
        self.assertIn(".clipboard_image_paste // true", start)
        self.assertIn("CODEX_IMAGE_PASTE_ENABLED", start)
        self.assertIn("enableCodexImagePaste=", start)
        self.assertIn('chmod 700 "$image_upload_dir"', start)
        self.assertIn('chown 22000:0 "$image_upload_dir"', start)
        self.assertIn('[[ -L "$image_upload_dir" ]]', start)
        self.assertNotIn("CODEX_SQLITE_HOME=", start)

    def test_reuses_existing_terminal_socket_and_private_png_only_storage(self):
        source = PATCH.read_text(encoding="utf-8")
        header = HEADER.read_text(encoding="utf-8")
        docker = DOCKERFILE.read_text(encoding="utf-8")
        self.assertIn("CODEX_IMAGE_WS_REQUEST '4'", header)
        self.assertIn("CODEX_IMAGE_WS_REPLY '4'", header)
        self.assertIn("CODEX_IMAGE_WS_ERROR '5'", header)
        self.assertIn("CODEX_IMAGE_MAX_SIZE (10u * 1024u * 1024u)", header)
        self.assertIn('O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW', header)
        self.assertIn("O_CREAT | O_EXCL | O_WRONLY", header)
        self.assertIn("getrandom(", header)
        self.assertIn("fchown(fd, 22000, 0)", header)
        self.assertIn("fchmod(fd, 0600)", header)
        self.assertIn("memcmp(data, png_magic", header)
        self.assertIn('memcmp(data + 12, "IHDR"', header)
        self.assertIn('"/data/codex-home/users/anonymous/.codex/uploads/%s"', header)
        self.assertIn("Never buffer an unbounded screenshot", source)
        self.assertIn("CODEX_IMAGE_PASTE_ENABLED", source)
        self.assertIn("pss->process == NULL", source)
        self.assertIn("image_reply_pending", source)
        self.assertIn('CODEX_IMAGE_WS_ERROR', source)
        self.assertIn("event.clipboardData.items", source)
        self.assertIn("event.preventDefault();", source)
        self.assertIn("event.stopImmediatePropagation();", source)
        self.assertIn("source?.closest?.('.xterm')", source)
        self.assertIn("item.kind === 'file' && item.type === 'image/png'", source)
        self.assertIn("this.imagePastePending", source)
        self.assertIn("this.sendData(", source)
        self.assertIn("path +", source)
        self.assertIn("codex-image-paste.h", docker)
        self.assertIn("python3 /tmp/apply-image-paste.py", docker)
        self.assertIn("codex_image_error_code", header)
        self.assertIn("UPLOAD_PERMISSIONS", header)
        self.assertIn("UPLOAD_DIR_MISSING", header)
        self.assertIn("STORAGE_FULL", header)
        self.assertIn("String.fromCharCode(27)", source)
        self.assertIn("^[0-9a-f]{32}[.]png$", source)
        self.assertIn("onCodexClipboardKeyDown", source)
        self.assertIn("event.stopImmediatePropagation();", source)
        self.assertIn("Screenshot rejected:", source)
        self.assertNotIn("nginx", docker)
        self.assertNotIn("socat", docker)

    def test_no_type_change_for_normal_text_and_existing_mobile_events(self):
        script = PATCH.read_text(encoding="utf-8")
        self.assertIn("if (!item) return;", script)
        self.assertIn("if (!this.imagePasteEnabled", script)
        self.assertIn("if (this.imagePastePending)", script)
        self.assertIn("this.imagePastePending = false", script)
        self.assertIn("addCapturedEventListener(document, 'paste'", script)
        self.assertIn("this.onCodexImagePaste(event as ClipboardEvent)", script)
        self.assertIn("IMAGE_PASTE_RESULT", script)
        self.assertIn("IMAGE_PASTE_ERROR", script)
        for translation in ("de.yaml", "en.yaml", "es.yaml", "pt-BR.yaml"):
            obj = yaml.safe_load((ROOT / "translations" / translation).read_text())
            self.assertIn("clipboard_image_paste", obj["configuration"])

    def test_python_patch_script_syntax_and_header_compiles(self):
        result = subprocess.run(
            ["python3", "-c", "import ast,sys; ast.parse(open(sys.argv[1]).read())", str(PATCH)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        if shutil.which("cc"):
            command = ["cc", "-D_GNU_SOURCE", "-std=c11", "-Wall", "-Werror", "-Wno-unused-function",
                       "-fsyntax-only", "-x", "c", "-I", str(SOURCE), "-"]
            result = subprocess.run(
                command, input='#include "codex-image-paste.h"\nint main(void) { return 0; }\n',
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
