import unittest
from collect_adoption import parse, delta

D = "sha256:" + "a"*64

class StatsTests(unittest.TestCase):
    def test_exact_total_and_alias(self):
        html = f'''<div class="lh-condensed"><span>Total downloads</span><h3 title="1,234">1.2K</h3></div>
        <div><a>latest</a><a>0.5.3</a><code>{D}</code><span>42 Version downloads</span></div>
        <svg><rect data-date="2026-11-27" data-merge-count="4"/></svg>'''
        a = parse(html)
        self.assertEqual(a["total"], 1234)
        self.assertEqual(a["versions"][D], {"tags": ["0.5.3"], "downloads": 42})
        self.assertEqual(a["daily"], {"2026-11-27": 4})
    def test_missing(self):
        self.assertIsNone(parse("<h3>Login</h3>")["total"])
        self.assertEqual(parse("<p>0 Version downloads</p>")["versions"], {})
        self.assertIsNone(delta(2, 3))
        self.assertIsNone(delta(5, None))
        self.assertEqual(delta(5, 5), 0)
    def test_developer_zero(self):
        a = parse(f'<li><a>deployment</a><a>0.5.0-dev.13</a><code>{D}</code>0 Version downloads</li>')
        self.assertEqual(a["versions"][D]["downloads"], 0)

if __name__ == "__main__":
    unittest.main()
