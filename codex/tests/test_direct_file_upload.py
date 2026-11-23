"""Developer 0.5.0-dev.10 responsive upload and private transport regressions."""
import shutil
import subprocess
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config.yaml"
START = ROOT / "rootfs/usr/local/bin/codex-start"
PATCH = ROOT / "ttyd-mobile-keys/apply-file-upload.py"
HEADER = ROOT / "ttyd-mobile-keys/codex-file-upload.h"
DOCKER = ROOT / "Dockerfile"


class DirectFileUploadTests(unittest.TestCase):
    def test_developer_only_gate_and_multi_language_controls(self):
        config = yaml.safe_load(CONFIG.read_text())
        self.assertEqual(config["version"], "0.5.0-dev.10")
        self.assertEqual(config["name"], "Codex Deployment")
        self.assertIs(config["options"]["direct_file_upload"], True)
        self.assertEqual(config["schema"]["direct_file_upload"], "bool")
        self.assertIs(config["options"]["file_transfer_enabled"], False)
        start = START.read_text()
        self.assertIn('CODEX_FILE_UPLOAD_ENABLED="$direct_file_upload"', start)
        self.assertIn("enableCodexFileUpload=", start)
        for name in ("de.yaml", "en.yaml", "es.yaml", "pt-BR.yaml"):
            translations = yaml.safe_load((ROOT / "translations" / name).read_text())
            self.assertIn("direct_file_upload", translations["configuration"])

    def test_existing_ingress_and_private_file_invariants(self):
        src = PATCH.read_text()
        header = HEADER.read_text()
        docker = DOCKER.read_text()
        self.assertIn("apply-image-paste.py", docker)
        self.assertIn("apply-file-upload.py", docker)
        self.assertIn("codex-file-upload.h", docker)
        self.assertIn("CODEX_FILE_MAX_SIZE (10u * 1024u * 1024u)", header)
        self.assertIn("CODEX_FILE_PATH_MAX 480u", header)
        self.assertIn("O_NOFOLLOW", header)
        self.assertIn("O_EXCL", header)
        self.assertIn("fchown(out, 22000, 0)", header)
        self.assertIn("fchmod(out, 0600)", header)
        self.assertIn("mkdirat(parent_fd, name, 0700)", header)
        self.assertIn("codex_image_open_upload_dir()", header)
        self.assertIn("AT_SYMLINK_NOFOLLOW", header)
        self.assertIn("CODEX_FILE_WS_REQUEST", src)
        self.assertIn("pss->image_reply_pending", src)
        self.assertIn("FILE_UPLOAD_RESULT", src)
        self.assertIn("FILE_UPLOAD_ERROR", src)
        self.assertIn("this.sendData(String.fromCharCode(27)", src)
        self.assertNotIn("app.post(", src)
        self.assertNotIn("http.createServer", src)

    def test_ui_and_mobile_technical_keys_non_regression(self):
        source = PATCH.read_text()
        self.assertIn("codex-upload-dock", source)
        self.assertIn("codex-upload-sheet", source)
        self.assertIn("onUploadDrop", source)
        self.assertIn("chooseFiles", source)
        self.assertIn("chooseImages", source)
        self.assertIn("chooseFolder", source)
        self.assertIn("webkitdirectory", source)
        # The new iOS control row must retain all 16 original positions;
        # only the second-row old shift-lock key becomes the Upload toggle.
        self.assertNotIn("renderMobileTechToggle", source)
        self.assertNotIn("technicalKeys", source)
        self.assertNotIn("<Fragment>", source)
        self.assertIn("uploadEnabled ? this.renderMobileUploadToggle(uploadOpen) : this.renderShiftLock(shiftLock)", source)
        self.assertIn("private renderMobileUploadToggle(active: boolean)", source)
        self.assertIn("onPointerDown={this.pressMobileUpload}", source)
        self.assertIn("onClick={this.clickMobileUpload}", source)
        self.assertIn("event.detail === 0", source)
        self.assertIn("aria-expanded={active}", source)
        self.assertIn("mobileKeys.slice(2, 7).map(this.renderMobileKey)", source)
        self.assertIn("mobileKeys.slice(0, 2).map(this.renderMobileKey)", source)
        self.assertIn("mobileKeys.slice(8, 9).map(this.renderMobileKey)", source)
        self.assertIn("this.renderModifier('Alt', alt, 'alt')", source)
        self.assertIn("this.renderModifier('Shift', shift, 'shift')", source)
        self.assertIn("this.renderKeyboardShow()", source)
        self.assertIn("this.renderKeyboardDismiss()", source)
        self.assertIn('<button type="button" onClick={this.chooseFiles}>Datei auswählen</button>', source)
        self.assertIn("border-radius: 0;", source)
        self.assertNotIn("border-radius: 14px 14px 0 0;", source)
        self.assertIn("max-height: 26vh", source)
        self.assertNotIn('onClick={this.chooseImages}>▧ Foto / Bild', source)
        self.assertNotIn('onClick={this.chooseFolder}>▱ Ordner</button>\\n                                    </div>', source)
        self.assertIn("mobileKeys.slice(7, 8)", source)
        self.assertIn("renderSelectionMode(selectionMode)", source)
        self.assertIn("renderKeyboardDismiss()", source)
        self.assertIn("uploadOpen", source)
        self.assertIn("uploadEntries", source)
        self.assertIn("this.xterm.fit()", source)
        self.assertIn("uploadFiles(files", source)
        self.assertIn("progress(i, 'done')", source)
        self.assertIn("file.webkitRelativePath || file.name", source)
        self.assertIn("files.length > 24", source)
        self.assertIn("file.size > 10 * 1024 * 1024", source)

    def test_patch_python_and_c_header_syntax(self):
        result = subprocess.run(
            ["python3", "-m", "py_compile", str(PATCH)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        if shutil.which("cc"):
            result = subprocess.run(
                ["cc", "-D_GNU_SOURCE", "-std=c11", "-Wall", "-Werror",
                 "-Wno-unused-function", "-fsyntax-only", "-x", "c",
                 "-I", str(HEADER.parent), "-"],
                input='#include "codex-file-upload.h"\nint main(void) { return 0; }\n',
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
