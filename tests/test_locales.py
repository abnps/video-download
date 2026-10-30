"""Prevodi u JSON fajlovima po jeziku (Faza 4, 29.10.2026): isti ključevi i ista mjesta za vrijednosti svuda."""

import json
import re
import unittest

from videodl import i18n


class LocaleFilesTest(unittest.TestCase):
    def test_every_language_file_has_the_same_keys_and_placeholders(self):
        tables = {code: json.loads((i18n.LOCALES_DIR / f"{code}.json").read_text(encoding="utf-8"))
                  for code in i18n.LANGUAGES}
        keys = set(tables["en"])
        for code, table in tables.items():
            with self.subTest(language=code):
                self.assertEqual(set(table), keys)
                self.assertTrue(all(isinstance(text, str) and text for text in table.values()))
        for key in keys:
            placeholders = {code: set(re.findall(r"\{(\w+)\}", tables[code][key])) for code in tables}
            with self.subTest(key=key):
                self.assertEqual(len({frozenset(found) for found in placeholders.values()}), 1, placeholders)

    def test_texts_keep_the_old_shape(self):
        self.assertEqual(len(i18n.TEXTS["menu.file"]), len(i18n.LANGUAGES))
        language = i18n.get_language()
        self.addCleanup(i18n.set_language, language)
        i18n.set_language("de")
        self.assertEqual(i18n.tr("cookies.none"), "Nicht verwenden")


if __name__ == "__main__":
    unittest.main()
