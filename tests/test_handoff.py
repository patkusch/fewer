import json
import re
import unittest

from fewer.handoff import build_handoff, parse_feedback

XSS = '<script>alert(1)</script>'


class BuildTests(unittest.TestCase):
    def page(self, **kw):
        args = dict(title="T", decisions=["Use A"], questions=["Why B?"],
                    examples=["print(1)"], diff_text="+new\n-old\n ctx")
        args.update(kw)
        return build_handoff(args["title"], args["decisions"], args["questions"],
                             args["examples"], args["diff_text"])

    def test_sections_and_controls(self):
        h = self.page()
        for name in ("Key decisions", "Open questions", "Examples", "Git diff"):
            self.assertIn(name, h)
        self.assertIn("agree", h)
        self.assertIn("Copy feedback", h)
        self.assertIn("IntersectionObserver", h)
        self.assertIn("prefers-color-scheme:dark", h)
        self.assertIn("viewport", h)

    def test_no_external_requests(self):
        h = self.page()
        self.assertNotRegex(h, r'(src|href)\s*=\s*["\']?https?:')
        self.assertNotIn("@import", h)
        self.assertNotIn("fetch(", h)

    def test_diff_colouring(self):
        h = self.page()
        self.assertIn('class="l add">+new', h)
        self.assertIn('class="l del">-old', h)
        self.assertIn('class="l ctx"> ctx', h)

    def test_escapes_everything(self):
        h = self.page(title=XSS, decisions=[XSS, {"title": XSS, "text": XSS}],
                      questions=[XSS], examples=[XSS, {"title": XSS, "text": XSS}],
                      diff_text=XSS + '\n+' + XSS)
        # only our own single script tag remains
        self.assertEqual(h.count("<script"), 1)
        self.assertNotIn(XSS, h)
        self.assertIn("&lt;script&gt;", h)

    def test_attribute_injection(self):
        h = self.page(title='"><img src=x onerror=alert(1)>')
        self.assertNotIn("<img", h)

    def test_empty_inputs(self):
        h = self.page(decisions=[], questions=[], examples=[], diff_text="")
        self.assertIn("Nothing here.", h)
        self.assertIn("No changes.", h)


class ParseTests(unittest.TestCase):
    def test_summary(self):
        fb = json.dumps({
            "viewed": [{"section": "Key decisions", "seconds": 5},
                       {"section": "Git diff", "seconds": 40}],
            "highlights": ["retry loop"],
            "answers": [{"id": "decision-2", "choice": "disagree", "note": "too slow"},
                        {"id": "decision-1", "choice": "agree", "note": ""},
                        {"id": "question-1", "choice": "", "note": "use sqlite"}],
        })
        md = parse_feedback(fb)
        self.assertIn("Spent longest on Git diff (40 seconds)", md)
        self.assertIn("Disagreed with decision 2: too slow", md)
        self.assertIn("Agreed with decision 1", md)
        self.assertIn("Note on question 1: use sqlite", md)
        self.assertIn('"retry loop"', md)
        self.assertLess(md.index("Disagreed"), md.index("Agreed"))

    def test_bad_input(self):
        self.assertIn("not valid JSON", parse_feedback("{nope"))
        self.assertIn("expected a JSON object", parse_feedback("[1]"))

    def test_empty(self):
        md = parse_feedback("{}")
        self.assertIn("No reading time", md)
        self.assertIn("No answers given", md)

    def test_messy_values(self):
        md = parse_feedback(json.dumps({"viewed": [{"section": "A"}, "x"],
                                        "answers": [{"id": "decision-1", "choice": "weird"}, 3]}))
        self.assertIn("Spent longest on A", md)


if __name__ == "__main__":
    unittest.main()
