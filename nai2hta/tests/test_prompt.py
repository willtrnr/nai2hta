from __future__ import annotations

import unittest

from nai2hta.prompt import prompt


class PromptParserTest(unittest.TestCase):
    def test_empty(self) -> None:
        self.assertEqual(prompt.parse_strict(""), [])

    def test_basic(self) -> None:
        self.assertEqual(prompt.parse_strict("foo, bar"), [(["foo", "bar"], None)])

    def test_basic_weighted(self) -> None:
        self.assertEqual(prompt.parse_strict("{foo, bar}"), [(["foo", "bar"], None)])
        self.assertEqual(prompt.parse_strict("[foo, bar]"), [(["foo", "bar"], None)])
        self.assertEqual(prompt.parse_strict("(foo, bar)"), [(["foo", "bar"], None)])

    def test_mixed(self) -> None:
        self.assertEqual(
            prompt.parse_strict("{{{foo}}} bar"), [(["foo"], None), (["bar"], None)]
        )

    def test_real(self) -> None:
        self.assertEqual(
            prompt.parse_strict(
                "(masterpiece:1.157625), (best quality:1.157625), 1girl, solo, science fiction,"
            ),
            [
                (["masterpiece"], 1.157625),
                (["best quality"], 1.157625),
                (["1girl", "solo", "science fiction"], None),
            ],
        )
        self.assertEqual(
            prompt.parse_strict("bronya zaychik (silverwing: n-ex)|masterpiece"),
            [
                (["bronya zaychik (silverwing: n-ex)"], None),
                (["masterpiece"], None),
            ],
        )
        self.assertEqual(
            prompt.parse_strict("black dress, yuuka (blue archive):0.5|masterpiece"),
            [
                (["black dress", "yuuka (blue archive)"], 0.5),
                (["masterpiece"], None),
            ],
        )


if __name__ == "__main__":
    unittest.main()
