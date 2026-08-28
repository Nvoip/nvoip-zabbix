import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MarketplacePackageTest(unittest.TestCase):
    def test_public_package_has_required_files_and_links(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        listing = (ROOT / "docs" / "zabbix-marketplace-listing.md").read_text(
            encoding="utf-8"
        )

        for relative_path in (
            "assets/nvoip-logo.svg",
            "templates/media_nvoip.yaml",
            "docs/zabbix-nvoip-alerts.en.md",
            "docs/zabbix-nvoip-alerts.md",
            "docs/zabbix-marketplace-listing.md",
        ):
            self.assertTrue((ROOT / relative_path).is_file(), relative_path)
            self.assertIn(relative_path, readme + listing)

        self.assertIn("https://github.com/Nvoip/nvoip-zabbix", listing)
        self.assertIn("Zabbix 7.0 and 7.4", listing)
        self.assertIn("7.0.30 and 7.4.14", listing)
        self.assertIn("Nvoip API v3", listing)

    def test_marketplace_logo_is_svg_below_form_limit(self):
        logo = ROOT / "assets" / "nvoip-logo.svg"
        self.assertLessEqual(logo.stat().st_size, 50 * 1024)
        self.assertIn("<svg", logo.read_text(encoding="utf-8"))

    def test_public_docs_do_not_expose_internal_profile_ids(self):
        public_files = (
            ROOT / "README.md",
            ROOT / "docs" / "zabbix-nvoip-alerts.en.md",
            ROOT / "docs" / "zabbix-nvoip-alerts.md",
            ROOT / "docs" / "zabbix-marketplace-listing.md",
        )
        combined = "\n".join(path.read_text(encoding="utf-8") for path in public_files)
        self.assertNotIn("id_profile", combined.lower())
        self.assertNotIn("internal profile", combined.lower())


if __name__ == "__main__":
    unittest.main()
