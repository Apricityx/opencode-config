import ast
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
        text = Path('install.sh').read_text()
        self.assertNotIn('192.168.', text)
        self.assertNotIn('/home/apricityx', text)
        for name, host in [('openai-272k', 'direct'), ('openai-1m', 'server'), ('guomo', 'server')]:
            settings = self.template['providers'][name]['settings']
            self.assertEqual(settings['baseURL'], f'https://newapi.{host}.apricityx.top:55555/v1')
            self.assertEqual(settings['apiKey'], '{file:./newapi.key}')

    def test_installer_embeds_current_template(self):
        line = next(line for line in Path('install.sh').read_text().splitlines()
                    if line.startswith('TEMPLATE = '))
        self.assertEqual(json.loads(ast.literal_eval(line.split(' = ', 1)[1])), self.template)

    def test_gpt_62_capabilities_and_route_budgets(self):
        efforts = ['low', 'medium', 'high', 'xhigh', 'max']
        for route, context, input_limit in [('openai-272k', 400000, 272000),
                                            ('openai-1m', 1050000, 922000)]:
            for model_id in ['gpt-6.2-sol', 'gpt-6.2-astra']:
                with self.subTest(route=route, model=model_id):
                    model = self.template['providers'][route]['models'][model_id]
                    self.assertEqual(model['modelID'], model_id)
                    self.assertEqual(model['limit'], {
                        'context': context, 'input': input_limit, 'output': 128000,
                    })
                    self.assertEqual(model['capabilities'], {
                        'tools': True, 'input': ['text', 'image', 'pdf'], 'output': ['text'],
                        'temperature': False, 'reasoning': {'supported': True, 'effort': efforts},
                    })
                    self.assertEqual(model['settings']['reasoningEffort'], 'medium')
                    self.assertEqual(model['variants'], [
                        {'id': effort, 'settings': {'reasoningEffort': effort}} for effort in efforts
                    ])


if __name__ == '__main__':
    unittest.main()
