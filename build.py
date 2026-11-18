"""Build a standalone installer from the checked-in public template."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    text = (ROOT / 'providers.json').read_text()
    json.loads(text)
    engine = (ROOT / 'installer.py').read_text()
    payload = 'TEMPLATE = ' + repr(text) + '\n' + engine
    script = '#!/usr/bin/env bash\nset -euo pipefail\nset +x\n'
    script += 'command -v python3 >/dev/null || { echo "需要 Python 3，请先安装 python3。" >&2; exit 1; }\n'
    script += "python3 - <<'OPENCODE_INSTALL_PY'\n" + payload + '\nOPENCODE_INSTALL_PY\n'
    (ROOT / 'install.sh').write_text(script)
    (ROOT / 'install.sh').chmod(0o755)


if __name__ == '__main__':
    main()
