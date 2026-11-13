"""Theme behavior, contrast and output naming for hkzn."""
import base64
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET

from test_render_improvements import render, ROOT

NS = {'s': 'http://www.w3.org/2000/svg'}


def luminance(color):
    values = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return sum((v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4) * w
               for v, w in zip(values, (.2126, .7152, .0722)))


class ThemeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.renders = {(lang, mode): render('hkzn', lang=lang, mode=mode)
                       for lang in ('en', 'zh') for mode in ('dark', 'light')}

    def test_language_and_geometry_are_independent_of_mode(self):
        for lang in ('en', 'zh'):
            dark, light = (self.renders[lang, mode] for mode in ('dark', 'light'))
            self.assertEqual((dark['W'], dark['H']), (light['W'], light['H']))
            self.assertEqual(dark['SANS'], light['SANS'])
            self.assertEqual(dark['INV'], light['INV'])
            roots = [ET.fromstring(g['S'].render()) for g in (dark, light)]
            text = [[(t.text, t.get('x'), t.get('y'), t.get('font-size'))
                     for t in root.findall('s:text', NS)] for root in roots]
            self.assertEqual(text[0], text[1])
            self.assertEqual(dark['name'], f'hkzn-{lang}-dark')
            self.assertEqual(light['name'], f'hkzn-{lang}-light')

    def test_default_is_explicitly_named_dark(self):
        default = render('hkzn')
        self.assertEqual(default['name'], 'hkzn-en-dark')
        self.assertEqual(default['S'].render(), self.renders['en', 'dark']['S'].render())
        private = render('hkzn', lang='zh', mode='light', unredacted=True)
        self.assertEqual(private['name'], 'hkzn-zh-light-unredacted')

    def test_light_text_and_inventory_accents_have_contrast(self):
        g = self.renders['en', 'light']
        colors = [g[k] for k in ('TEXT', 'MUTED', 'FAINT', 'HWC')]
        colors += list(g['C'].values()) + [v['color'] for v in g['KIND'].values()]
        colors += [g['accent']('#ffffff'), g['accent']('#aaffcc')]
        for background in ('bg', 'panel', 'chip', 'hardware_bg', 'cloud', 'lan_bg'):
            for color in colors:
                ratio = (luminance(g['THEME'][background]) + .05) / (luminance(color) + .05)
                self.assertGreaterEqual(ratio, 4.5, (background, color, ratio))

    def test_glyphs_adapt_without_changing_brand_artwork_or_source_files(self):
        for mode in ('dark', 'light'):
            g = self.renders['en', mode]
            cache = g['S']._icon_cache
            glyph = base64.b64decode(cache['glyph-nic'])
            original = (ROOT / 'icons/glyph-nic.svg').read_bytes()
            if mode == 'dark':
                self.assertEqual(glyph, original)
            else:
                self.assertNotIn(b'#c9d1d9', glyph)
                self.assertIn(g['THEME']['glyph'].encode(), glyph)
            self.assertEqual(base64.b64decode(cache['apple']), (ROOT / 'icons/apple.svg').read_bytes())

    def test_invalid_or_unsupported_modes_fail_clearly(self):
        cases = [(['build.py', 'hkzn', '--mode'], '--mode'),
                 (['build.py', 'hkzn', '--mode=sepia'], '--mode'),
                 (['build.py', 'hkzn', '--mode='], '--mode'),
                 (['build.py', 'cbny', '--mode', 'light'], 'only for hkzn'),
                 (['build.py', '--all', '--mode=light'], 'only for hkzn'),
                 (['sites/hkzn/layout.py', '--mode'], '--mode'),
                 (['sites/hkzn/layout.py', '--mode', 'sepia'], '--mode')]
        for args, message in cases:
            with self.subTest(args=args):
                proc = subprocess.run([sys.executable, str(ROOT / args[0]), *args[1:]],
                                      capture_output=True, text=True)
                self.assertNotEqual(proc.returncode, 0)
                self.assertIn(message, proc.stderr)
