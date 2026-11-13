"""The translated panorama keeps the same network facts and redaction rules."""
import unittest
import xml.etree.ElementTree as ET
import yaml

from test_render_improvements import render, ROOT


class OriginLanguageTests(unittest.TestCase):
    def test_translation_preserves_network_identifiers(self):
        en, zh = [yaml.safe_load((ROOT / 'sites/origin' / f'site.{lang}.yaml').read_text())
                  for lang in ('en', 'zh')]
        identifiers = {'id', 'ip', 'host', 'internal', 'vlan', 'tagged', 'untagged', 'port',
                       'proto', 'to', 'icons', 'icon', 'pct', 'count', 'kind', 'exposure'}
        def facts(obj, path=()):
            result = {}
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key in identifiers:
                        result[path + (key,)] = value
                    result.update(facts(value, path + (key,)))
            elif isinstance(obj, list):
                for i, value in enumerate(obj):
                    result.update(facts(value, path + (i,)))
            return result
        self.assertEqual(facts(en), facts(zh))
        self.assertEqual([g['name'] for g in en['terra']['dmz_groups']],
                         [g['key'] for g in zh['terra']['dmz_groups']])

    def test_chinese_content_and_default_redaction(self):
        g = render('origin', lang='zh')
        svg = g['S'].render()
        ET.fromstring(svg)
        for label in ('我的家庭实验室', '公网开放服务', '媒体处理流程', '入口与安全'):
            self.assertIn(label, svg)
        self.assertNotIn(g['DOMAIN'], svg)
        self.assertIn(g['RED']['domain_placeholder'], svg)
        self.assertIn('PingFang SC', g['SANS'])
        self.assertEqual(g['name'], 'origin-zh-dark')

    def test_unredacted_chinese_uses_original_values(self):
        g = render('origin', lang='zh', unredacted=True)
        svg = g['S'].render()
        self.assertIn(g['DOMAIN'], svg)
        self.assertNotIn(g['RED']['domain_placeholder'], svg)
        self.assertEqual(g['name'], 'origin-zh-dark-unredacted')
