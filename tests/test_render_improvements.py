"""Regression coverage for the PR #1 features adapted to per-site layouts."""
import contextlib
import copy
import io
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
REAL_RUN = subprocess.run


def render(site, inventory=None, lang=None, mode=None, unredacted=False):
    with tempfile.TemporaryDirectory() as tmp:
        args = [str(ROOT / 'sites' / site / 'layout.py')]
        if inventory is not None:
            cfg = Path(tmp) / 'site.yaml'
            cfg.write_text(yaml.safe_dump(inventory))
            args += ['--inventory', str(cfg)]
        if lang:
            args += ['--lang', lang]

        if mode is not None:
            args += ['--mode', mode]
        if unredacted:
            args += ['--unredacted']

        def run(command, *a, **kw):
            if command[0] == 'rsvg-convert':
                return subprocess.CompletedProcess(command, 0)
            return REAL_RUN(command, *a, **kw)

        with patch.object(sys, 'argv', args), patch.object(subprocess, 'run', run), contextlib.redirect_stdout(io.StringIO()):
            return runpy.run_path(args[0])


class RenderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.origin = render('origin')

    def test_optional_inventory_fields(self):
        inv = copy.deepcopy(self.origin['INV'])
        inv['fritzbox']['stub'] = True
        inv['switch']['ports'][0].update(short='UPLINK', untagged=None, tagged=[])
        inv['ssids'][0].pop('vlan', None)
        inv['ssids'][0]['vlans'] = ['10', '20']
        # Discover the guest list without coupling the test to group names.
        def visit(value):
            if isinstance(value, dict):
                if 'id' in value and 'name' in value:
                    value.update(kind='VM', node='pve2', vlan='10')
                for v in value.values():
                    visit(v)
            elif isinstance(value, list):
                for v in value:
                    visit(v)
        visit(inv)
        result = render('origin', inv)
        svg = result['S'].render()
        for expected in ('UPLINK', 'PPSK', 'pve2', 'VM '):
            self.assertIn(expected, svg)
        self.assertNotIn('>Cable<', svg)

    def test_pool_warning_and_overflow(self):
        g = self.origin
        pool = dict(name='test', layout='mirror', used='90%', pct=90, groups=[])
        g['pool_box'](pool, 0, 0, 300, 170)
        self.assertIn('#f0883e', g['S'].p[-1])
        pool['groups'] = [dict(kind='hdd', count=2, label='Disk group', sub='two disks')] * 2
        with self.assertRaisesRegex(AssertionError, 'pool test'):
            g['pool_box'](pool, 0, 0, 150, 170)
        g['pool_box'](pool, 0, 0, 150, 280)

    def test_bilingual_layouts_follow_growing_content(self):
        for site in ('cbny', 'hkzn'):
            inv = yaml.safe_load((ROOT / 'sites' / site / 'site.zh.yaml').read_text())
            inv['notes'] *= 8
            result = render(site, inv, 'zh')
            self.assertGreater(result['H'], 1240)
            self.assertIn('PingFang SC', result['SANS'])

    def test_inventory_cli_rejects_missing_value_and_multiple_sites(self):
        for args in (['origin', '--inventory'], ['--all', '--inventory', 'other.yaml']):
            proc = REAL_RUN([sys.executable, str(ROOT / 'build.py'), *args], capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn('--inventory', proc.stderr)


if __name__ == '__main__':
    unittest.main()
