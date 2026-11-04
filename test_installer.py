import json
import stat
import tempfile
import unittest
from pathlib import Path

import installer


class InstallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = json.loads(Path('providers.json').read_text())

    def test_jsonc_strings_and_comments(self):
        value = installer.parse_jsonc('''{
          // comment
          "url": "https://example.com/v1", /* comment */
          "literal": ",}", "escaped": "a\\\"//b", "list": [1,],
        }''')
        self.assertEqual(value['url'], 'https://example.com/v1')
        self.assertEqual(value['literal'], ',}')
        self.assertEqual(value['escaped'], 'a"//b')

    def test_install_preserves_unrelated_and_backs_up(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            original = {'providers': {'deepseek': {}}, 'mcp': {'servers': {'test': {}}},
                        'permissions': [], 'plugins': ['other', '/local/opencode-claude.js'],
                        'policies': [{'action': 'tool.use', 'resource': 'shell:*', 'effect': 'deny'}]}
            (directory / 'opencode.json').write_text(json.dumps(original))
            (directory / 'opencode.jsonc').write_text('{/* hi */ "username": "test",}')
            backup = installer.install(directory, self.template, 'dummy-test-key')
            config = json.loads((directory / 'opencode.json').read_text())
            self.assertEqual(set(config['providers']), {'openai-272k', 'openai-1m', 'guomo', 'opencode'})
            self.assertEqual(config['mcp'], original['mcp'])
            self.assertEqual(config['username'], 'test')
            self.assertEqual(config['plugins'], ['other'])
            self.assertEqual(config['policies'][0]['action'], 'tool.use')
            self.assertTrue((backup / 'opencode.jsonc').exists())
            self.assertEqual(json.loads((backup / 'opencode.json').read_text()), original)
            self.assertEqual(stat.S_IMODE((directory / 'newapi.key').stat().st_mode), 0o600)
            self.assertNotIn('dummy-test-key', (directory / 'opencode.json').read_text())
            second = installer.install(directory, self.template, 'another-dummy')
            self.assertNotEqual(backup, second)
            self.assertEqual(config, json.loads((directory / 'opencode.json').read_text()))

    def test_invalid_config_no_writes(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            (directory / 'opencode.jsonc').write_text('{bad')
            with self.assertRaises(ValueError):
                installer.install(directory, self.template, 'dummy')
            self.assertFalse((directory / 'newapi.key').exists())
            self.assertFalse((directory / 'backups').exists())

    def test_symlink_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            (directory / 'newapi.key').symlink_to('/nonexistent')
            with self.assertRaises(ValueError):
                installer.install(directory, self.template, 'dummy')

    def test_export_has_only_public_configuration(self):
        self.assertEqual(set(self.template), {'$schema', 'model', 'providers', 'policies'})
        self.assertEqual(sum(len(v.get('models', {})) for v in self.template['providers'].values()), 21)
        text = Path('install.sh').read_text()
        self.assertNotIn('192.168.', text)
        self.assertNotIn('/home/apricityx', text)
        for provider in self.template['providers'].values():
            if provider.get('models'):
                self.assertEqual(provider['settings']['baseURL'], 'https://newapi.server.apricityx.top:55555/v1')


if __name__ == '__main__':
    unittest.main()
