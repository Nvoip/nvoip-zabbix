import importlib.util
import json
import pathlib
import unittest
import xml.etree.ElementTree as ET


ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "aurora_public_3306_check", ROOT / "Scripts" / "aurora_public_3306_check.py"
)
check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check)
TEMPLATE = json.loads(
    (ROOT / "templates" / "template-nvoip-aurora-public-access.json").read_text(encoding="utf-8")
)["zabbix_export"]["templates"][0]


def group(permission_xml, group_id="sg-1"):
    return ET.fromstring(
        f"<item><groupId>{group_id}</groupId><ipPermissions>{permission_xml}</ipPermissions></item>"
    )


def permission(sources, protocol="tcp", start=3306, end=3306):
    ports = "" if protocol == "-1" else f"<fromPort>{start}</fromPort><toPort>{end}</toPort>"
    return f"<item><ipProtocol>{protocol}</ipProtocol>{ports}{sources}</item>"


def cidr(value):
    return f"<ipRanges><item><cidrIp>{value}</cidrIp></item></ipRanges>"


class PublicRulesTest(unittest.TestCase):
    def rules(self, permission_xml):
        return check.public_rules([group(permission_xml)], 3306)

    def test_public_cidr_is_reported(self):
        self.assertEqual(["sg-1 203.0.113.10/32"], self.rules(permission(cidr("203.0.113.10/32"))))

    def test_open_to_the_world_is_reported(self):
        self.assertEqual(["sg-1 0.0.0.0/0"], self.rules(permission(cidr("0.0.0.0/0"))))

    def test_all_traffic_rule_is_reported(self):
        self.assertEqual(1, len(self.rules(permission(cidr("203.0.113.10/32"), protocol="-1"))))

    def test_port_range_covering_the_database_is_reported(self):
        self.assertEqual(
            1, len(self.rules(permission(cidr("203.0.113.10/32"), start=3000, end=4000)))
        )

    def test_ipv6_and_prefix_list_are_reported(self):
        sources = (
            "<ipv6Ranges><item><cidrIpv6>2001:db8::/32</cidrIpv6></item></ipv6Ranges>"
            "<prefixListIds><item><prefixListId>pl-1</prefixListId></item></prefixListIds>"
        )
        self.assertEqual(2, len(self.rules(permission(sources))))

    def test_range_wider_than_the_vpc_is_reported(self):
        self.assertEqual(["sg-1 172.16.0.0/12"], self.rules(permission(cidr("172.16.0.0/12"))))

    def test_private_rule_is_not_reported(self):
        self.assertEqual([], self.rules(permission(cidr("172.31.35.211/32"))))

    def test_group_reference_is_not_reported(self):
        sources = "<groups><item><groupId>sg-2</groupId></item></groups>"
        self.assertEqual([], self.rules(permission(sources)))

    def test_public_rule_on_other_port_is_not_reported(self):
        self.assertEqual([], self.rules(permission(cidr("0.0.0.0/0"), start=443, end=443)))

    def test_udp_rule_is_not_reported(self):
        self.assertEqual([], self.rules(permission(cidr("0.0.0.0/0"), protocol="udp")))


class TemplateTest(unittest.TestCase):
    def test_trigger_expressions_use_this_template(self):
        items = {item["key"]: item for item in TEMPLATE["items"]}
        triggers = items["nvoip.aurora.public3306.count"]["triggers"]
        expressions = [trigger["expression"] for trigger in triggers]
        self.assertIn(
            "last(/Template Nvoip Aurora Public Access/nvoip.aurora.public3306.count)>0",
            expressions,
        )
        self.assertTrue(any(expression.startswith("nodata(") for expression in expressions))

    def test_trappers_only_accept_the_local_collector(self):
        for item in TEMPLATE["items"]:
            self.assertEqual("TRAP", item["type"])
            self.assertEqual("127.0.0.1", item["allowed_hosts"])


if __name__ == "__main__":
    unittest.main()
