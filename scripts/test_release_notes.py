import unittest

from release_notes import release_notes


class ReleaseNotesTests(unittest.TestCase):
    def test_extracts_only_requested_version(self):
        changelog = "# Changelog\n\n## Unreleased\n\nFuture\n\n## 1.2.3 — 2026-01-01\n\n### Added\n\n- Feature\n\n## 1.2.2\n\nOld\n"
        self.assertEqual(release_notes("v1.2.3", changelog), "### Added\n\n- Feature\n")

    def test_undated_heading(self):
        self.assertEqual(release_notes("v0.0.1", "## 0.0.1\n\n- Initial\n"), "- Initial\n")

    def test_invalid_tags(self):
        for tag in ("1.2.3", "v1.2", "v01.2.3", "v1.2.3-rc.1", "v1.2.3+build"):
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                release_notes(tag, "## 1.2.3\nNotes")

    def test_missing_empty_duplicate_and_prefix_sections(self):
        for changelog in ("## Unreleased\nNotes", "## 1.2.3\n\n",
                          "## 1.2.3\nA\n## 1.2.3\nB", "## 1.2.30\nNotes"):
            with self.subTest(changelog=changelog), self.assertRaises(ValueError):
                release_notes("v1.2.3", changelog)
