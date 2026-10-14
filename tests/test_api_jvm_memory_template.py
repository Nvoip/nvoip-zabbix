import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TEMPLATE_PATH = ROOT / "templates" / "template-nvoip-api-jvm-memory.json"
MASTER_KEY = "vfs.file.contents[/run/nvoip-api-memory/metrics.json]"


class ApiJvmMemoryTemplateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
        cls.export = cls.document["zabbix_export"]
        cls.template = cls.export["templates"][0]
        cls.items = {item["key"]: item for item in cls.template["items"]}

    def test_targets_zabbix_7_with_unique_uuids(self):
        self.assertEqual("7.0", self.export["version"])
        self.assertEqual("Template Nvoip API JVM Memory", self.template["template"])
        uuids = [group["uuid"] for group in self.export["template_groups"]]
        uuids.append(self.template["uuid"])
        uuids.extend(item["uuid"] for item in self.template["items"])
        uuids.extend(
            trigger["uuid"]
            for item in self.template["items"]
            for trigger in item.get("triggers", [])
        )
        self.assertEqual(len(uuids), len(set(uuids)))
        for uuid in uuids:
            self.assertRegex(uuid, r"^[0-9a-f]{32}$")

    def test_uses_one_active_json_master_and_dependent_items(self):
        master = self.items[MASTER_KEY]
        self.assertEqual("ZABBIX_ACTIVE", master["type"])
        self.assertEqual("TEXT", master["value_type"])
        dependents = [
            item for item in self.template["items"] if item["type"] == "DEPENDENT"
        ]
        self.assertEqual(len(self.template["items"]) - 1, len(dependents))
        for item in dependents:
            self.assertEqual(MASTER_KEY, item["master_item"]["key"])
            self.assertEqual("JSONPATH", item["preprocessing"][0]["type"])
            self.assertTrue(item["preprocessing"][0]["parameters"][0].startswith("$."))

    def test_covers_staleness_host_pressure_and_both_jvms(self):
        keys = set(self.items)
        for expected in (
            "nvoip.api.memory.sample.epoch",
            "nvoip.api.host.memory.available",
            "nvoip.api.host.swap.used",
            "nvoip.api.jvm.metaspace.used[tomcat9]",
            "nvoip.api.jvm.metaspace.used[tomcat10]",
            "nvoip.api.jvm.classes.loaded[tomcat9]",
            "nvoip.api.jvm.classes.loaded[tomcat10]",
            "nvoip.api.jvm.classes.unloaded[tomcat9]",
            "nvoip.api.jvm.classes.unloaded[tomcat10]",
        ):
            self.assertIn(expected, keys)

        trigger_names = {
            trigger["name"]
            for item in self.template["items"]
            for trigger in item.get("triggers", [])
        }
        for fragment in (
            "no fresh sample",
            "600 MiB deploy guard",
            "swap",
            "Tomcat 9 Metaspace",
            "Tomcat 10 Metaspace",
            "retained deployments",
        ):
            self.assertTrue(
                any(fragment in name for name in trigger_names),
                msg=f"missing trigger containing {fragment!r}",
            )

    def test_thresholds_warn_before_the_existing_deploy_guard(self):
        macros = {entry["macro"]: int(entry["value"]) for entry in self.template["macros"]}
        deploy_guard = 600 * 1024 * 1024
        self.assertGreater(macros["{$NVOIP.API.MEM.AVAILABLE.WARN}"], deploy_guard)
        self.assertGreater(macros["{$NVOIP.API.MEM.AVAILABLE.HIGH}"], deploy_guard)
        self.assertGreater(
            macros["{$NVOIP.API.MEM.AVAILABLE.WARN}"],
            macros["{$NVOIP.API.MEM.AVAILABLE.HIGH}"],
        )
        self.assertGreater(
            macros["{$NVOIP.API.TOMCAT9.METASPACE.HIGH}"],
            macros["{$NVOIP.API.TOMCAT9.METASPACE.WARN}"],
        )
        self.assertGreater(
            macros["{$NVOIP.API.TOMCAT10.METASPACE.HIGH}"],
            macros["{$NVOIP.API.TOMCAT10.METASPACE.WARN}"],
        )


if __name__ == "__main__":
    unittest.main()
