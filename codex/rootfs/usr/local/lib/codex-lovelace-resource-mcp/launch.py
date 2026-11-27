"""Fixed entry point for the isolated interpreter in the add-on image."""

import sys
from pathlib import Path

if not (sys.flags.isolated and sys.flags.dont_write_bytecode):
    raise SystemExit("The privileged resource server requires isolated Python.")

# This path is installed by the image, outside the editable workspaces.
sys.path.append(str(Path(__file__).parent))

from codex_lovelace_resource_mcp.server import main  # noqa: E402

main()
