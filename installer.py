"""Installer engine; build.py embeds this and the public template in install.sh."""
import copy
import datetime
import getpass
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path


def parse_jsonc(text):
    # Tokenize strings first, so URLs, escaped quotes and comment markers survive.
    tokens = re.compile(r'("(?:\\.|[^"\\])*")|(/\*[\s\S]*?\*/|//[^\n]*)')
    text = tokens.sub(lambda m: m[1] if m[1] else ' ', text)
    text = re.sub(r'("(?:\\.|[^"\\])*")|(,\s*(?=[}\]]))',
                  lambda m: m[1] if m[1] else '', text)
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError('配置根节点必须是对象')
    return data


def merge(a, b):
    result = copy.deepcopy(a)
    for key, value in b.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def assemble(existing, template):
    result = copy.deepcopy(existing)
    result.pop('provider', None)
    result.pop('enabled_providers', None)
    result.pop('disabled_providers', None)
    for key in ('$schema', 'model', 'providers'):
        result[key] = copy.deepcopy(template[key])
    rules = result.get('policies', [])
    result['policies'] = [r for r in rules if r.get('action') != 'provider.use'] + template['policies']
    experimental = result.get('experimental', {})
    if isinstance(experimental, dict) and 'policies' in experimental:
        experimental['policies'] = [r for r in experimental['policies'] if r.get('action') != 'provider.use']
    # Remove the known local Claude provider plugin, not unrelated plugins.
    for key in ('plugins', 'plugin'):
        if isinstance(result.get(key), list):
            result[key] = [p for p in result[key] if 'opencode-claude' not in
                           (p if isinstance(p, str) else str(p.get('package', '')))]
    return result


def atomic_write(path, content):
    fd, temp = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def install(directory, template, key):
    directory = Path(directory)
    paths = [directory / 'opencode.json', directory / 'opencode.jsonc']
    keypath = directory / 'newapi.key'
    for path in paths + [keypath]:
        if path.is_symlink():
            raise ValueError('为避免覆盖符号链接，请先手动处理：' + str(path))
    existing = {}
    # Read and validate everything before writing anything. JSONC takes precedence.
    for path in paths:
        if path.exists():
            existing = merge(existing, parse_jsonc(path.read_text()))
    result = assemble(existing, template)
    for provider in result['providers'].values():
        if provider.get('settings', {}).get('apiKey'):
            provider['settings']['apiKey'] = '{file:' + str(keypath.resolve()) + '}'
    directory.mkdir(parents=True, exist_ok=True)
    os.chmod(directory, directory.stat().st_mode & 0o777)
    backup = directory / 'backups' / ('newapi-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    backup.mkdir(parents=True, mode=0o700)
    for path in paths + [keypath]:
        if path.exists():
            shutil.copy2(path, backup / path.name)
            os.chmod(backup / path.name, 0o600)
    atomic_write(keypath, key + '\n')
    atomic_write(paths[0], json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    # Consolidate both global configs; keep all unrelated parsed settings.
    if paths[1].exists():
        atomic_write(paths[1], '{"$schema": "https://opencode.ai/config.json"}\n')
    return backup


def main():
    if not sys.platform.startswith('linux'):
        raise ValueError('此脚本仅支持 Linux')
    directory = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'opencode'
    print('OpenCode V2 网关配置安装器（不安装 OpenCode 本体）')
    print('目标：', directory)
    print('仅保留 openai-272k、openai-1m、guomo、opencode。')
    print('将备份并合并全局 JSON/JSONC；保留 MCP、权限等无关设置，JSONC 注释不会保留。')
    with open('/dev/tty', 'w') as tty, open('/dev/tty', 'r') as tty_input:
        tty.write('继续安装？[y/N] ')
        tty.flush()
        if tty_input.readline().strip().lower() not in ('y', 'yes'):
            print('已取消，未修改任何文件。')
            return
        key = getpass.getpass('请输入 New API API Key（不回显）：', stream=tty).strip()
    if not key or any(c.isspace() for c in key):
        raise ValueError('API Key 不能为空或包含空白字符')
    backup = install(directory, json.loads(TEMPLATE), key)
    print('安装完成。备份：', backup)
    print('密钥仅保存于本机 newapi.key（权限 600），不会上传。')
    print('默认模型：openai-272k/gpt-6.1-sol；网关：https://newapi.server.apricityx.top:55555/v1')
    print('配置会自动重载；可运行 /reload，然后在 /models 中检查。')
    print('未测试 API Key、额度和模型可用性；opencode 内置服务仍使用自己的认证。')


if __name__ == '__main__':
    try:
        main()
    except (Exception, KeyboardInterrupt) as exc:
        print('安装失败：' + str(exc), file=sys.stderr)
        sys.exit(1)
