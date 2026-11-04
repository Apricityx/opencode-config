"""Export only the selected public provider settings and build a standalone installer."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = Path.home() / '.config/opencode/opencode.json'
KEEP = ('openai-272k', 'openai-1m', 'guomo', 'opencode')
BASE = 'https://newapi.server.apricityx.top:55555/v1'


def main():
    source = json.loads(SOURCE.read_text())
    config = {'$schema': 'https://opencode.ai/config.json',
              'model': 'openai-272k/gpt-6.1-sol', 'providers': {},
              'policies': [{'action': 'provider.use', 'resource': '*', 'effect': 'deny'}]}
    for name in KEEP:
        if name == 'opencode':
            config['providers'][name] = {}
        else:
            provider = source['providers'][name]
            config['providers'][name] = {
                'name': provider['name'], 'package': provider['package'],
                'settings': {'baseURL': BASE, 'apiKey': '{file:./newapi.key}',
                             'setCacheKey': True, 'headerTimeout': False,
                             'chunkTimeout': 600000, 'timeout': False},
                'models': provider['models']}
        config['policies'].append({'action': 'provider.use', 'resource': name, 'effect': 'allow'})
    text = json.dumps(config, ensure_ascii=False, indent=2) + '\n'
    (ROOT / 'providers.json').write_text(text)
    engine = (ROOT / 'installer.py').read_text()
    payload = 'TEMPLATE = ' + repr(text) + '\n' + engine
    script = '#!/usr/bin/env bash\nset -euo pipefail\nset +x\n'
    script += 'command -v python3 >/dev/null || { echo "需要 Python 3，请先安装 python3。" >&2; exit 1; }\n'
    script += "python3 - <<'OPENCODE_INSTALL_PY'\n" + payload + '\nOPENCODE_INSTALL_PY\n'
    (ROOT / 'install.sh').write_text(script)
    (ROOT / 'install.sh').chmod(0o755)


if __name__ == '__main__':
    main()
