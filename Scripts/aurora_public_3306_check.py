#!/usr/bin/env python3
"""NN-6738: count public ingress rules that reach the Aurora port.

Reads the security groups attached to the cluster instances and sends the
result to Zabbix trapper items. It never changes AWS. Any read failure sends
nothing, so the monitor's nodata trigger covers a broken collector.
"""
import argparse
import datetime
import hashlib
import hmac
import http.client
import ipaddress
import json
import socket
import struct
import sys
import urllib.parse
import xml.etree.ElementTree as ET

IMDS_HOST = "169.254.169.254"
PRIVATE_NETWORK = ipaddress.ip_network("172.31.0.0/16")
ITEM_PREFIX = "nvoip.aurora.public3306"


def read_response(connection, method, path, body=None, headers=None):
    connection.request(method, path, body=body, headers=headers or {})
    response = connection.getresponse()
    data = response.read()
    if response.status != 200:
        raise RuntimeError(f"{connection.host} respondeu {response.status}")
    return data


def imds_credentials():
    # O serviço de metadados só existe em HTTP, no endereço local da instância.
    connection = http.client.HTTPConnection(IMDS_HOST, timeout=3)
    token = read_response(
        connection, "PUT", "/latest/api/token",
        headers={"X-aws-ec2-metadata-token-ttl-seconds": "300"},
    ).decode()
    headers = {"X-aws-ec2-metadata-token": token}

    def get(path):
        return read_response(connection, "GET", "/latest/meta-data/iam/security-credentials/" + path, headers=headers).decode()

    role = get("").strip()
    return json.loads(get(role))


def _sign(key, message):
    return hmac.new(key, message.encode(), hashlib.sha256).digest()


def aws_query(service, region, params, credentials):
    host = f"{service}.{region}.amazonaws.com"
    body = urllib.parse.urlencode(sorted(params.items()))
    now = datetime.datetime.now(datetime.timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date = now.strftime("%Y%m%d")
    token = credentials["Token"]
    canonical_headers = (
        "content-type:application/x-www-form-urlencoded; charset=utf-8\n"
        f"host:{host}\nx-amz-date:{amz_date}\nx-amz-security-token:{token}\n"
    )
    signed_headers = "content-type;host;x-amz-date;x-amz-security-token"
    canonical = "\n".join(
        ["POST", "/", "", canonical_headers, signed_headers,
         hashlib.sha256(body.encode()).hexdigest()]
    )
    scope = f"{date}/{region}/{service}/aws4_request"
    to_sign = "\n".join(
        ["AWS4-HMAC-SHA256", amz_date, scope,
         hashlib.sha256(canonical.encode()).hexdigest()]
    )
    key = _sign(("AWS4" + credentials["SecretAccessKey"]).encode(), date)
    for part in (region, service, "aws4_request"):
        key = _sign(key, part)
    signature = hmac.new(key, to_sign.encode(), hashlib.sha256).hexdigest()
    data = read_response(
        http.client.HTTPSConnection(host, timeout=10), "POST", "/", body=body.encode(),
        headers={
            "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
            "X-Amz-Date": amz_date,
            "X-Amz-Security-Token": token,
            "Authorization": (
                f"AWS4-HMAC-SHA256 Credential={credentials['AccessKeyId']}/{scope}, "
                f"SignedHeaders={signed_headers}, Signature={signature}"
            ),
        },
    )
    # A resposta vem da AWS por TLS verificado. A API não usa DOCTYPE nem entidades.
    if b"<!DOCTYPE" in data or b"<!ENTITY" in data:
        raise RuntimeError("resposta da AWS com DTD recusada")
    root = ET.fromstring(data)  # nosemgrep: python.lang.security.use-defused-xml.use-defused-xml
    for element in root.iter():
        element.tag = element.tag.rsplit("}", 1)[-1]
    return root


def describe_cluster(cluster, region, credentials):
    root = aws_query(
        "rds", region,
        {"Action": "DescribeDBInstances", "Version": "2014-10-31",
         "Filters.Filter.1.Name": "db-cluster-id",
         "Filters.Filter.1.Values.Value.1": cluster},
        credentials,
    )
    instances = root.findall(".//DBInstance")
    if not instances:
        raise RuntimeError("cluster sem instâncias: " + cluster)
    groups = sorted(
        {node.text for node in root.findall(".//VpcSecurityGroupId") if node.text}
    )
    if not groups:
        raise RuntimeError("cluster sem grupos de segurança: " + cluster)
    public = any(i.findtext("PubliclyAccessible") == "true" for i in instances)
    return groups, public


def describe_groups(group_ids, region, credentials):
    params = {"Action": "DescribeSecurityGroups", "Version": "2016-11-15"}
    for index, group_id in enumerate(group_ids, 1):
        params[f"GroupId.{index}"] = group_id
    root = aws_query("ec2", region, params, credentials)
    groups = root.findall("./securityGroupInfo/item")
    if len(groups) != len(group_ids):
        raise RuntimeError("resposta incompleta de grupos de segurança")
    return groups


def covers_port(permission, port):
    if permission.findtext("ipProtocol") == "-1":
        return True
    if permission.findtext("ipProtocol") != "tcp":
        return False
    return int(permission.findtext("fromPort")) <= port <= int(permission.findtext("toPort"))


def public_rules(groups, port):
    """Return every source outside the VPC that reaches the port.

    References to other security groups stay inside AWS and are not public. An
    IPv6 range or prefix list has no address in the VPC range, so it counts.
    """
    found = []
    for group in groups:
        group_id = group.findtext("groupId")
        for permission in group.findall("./ipPermissions/item"):
            if not covers_port(permission, port):
                continue
            for node in permission.findall("./ipRanges/item/cidrIp"):
                network = ipaddress.ip_network(node.text, strict=False)
                if not network.subnet_of(PRIVATE_NETWORK):
                    found.append(f"{group_id} {node.text}")
            for node in permission.findall("./ipv6Ranges/item/cidrIpv6"):
                found.append(f"{group_id} {node.text}")
            for node in permission.findall("./prefixListIds/item/prefixListId"):
                found.append(f"{group_id} {node.text}")
    return sorted(set(found))


def zabbix_send(server, port, host, values):
    data = [
        {"host": host, "key": f"{ITEM_PREFIX}.{key}", "value": str(value)}
        for key, value in values.items()
    ]
    body = json.dumps({"request": "sender data", "data": data}).encode()
    packet = b"ZBXD\x01" + struct.pack("<Q", len(body)) + body
    with socket.create_connection((server, port), timeout=10) as connection:
        connection.sendall(packet)
        response = b""
        while True:
            chunk = connection.recv(4096)
            if not chunk:
                break
            response += chunk
    info = json.loads(response[13:]).get("info", "")
    if f"processed: {len(data)};" not in info or "failed: 0;" not in info:
        raise RuntimeError("Zabbix recusou os valores: " + info)
    return info


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cluster", default="nvoip")
    parser.add_argument("--region", default="sa-east-1")
    parser.add_argument("--db-port", type=int, default=3306)
    parser.add_argument("--zabbix-server", default="127.0.0.1")
    parser.add_argument("--zabbix-port", type=int, default=10051)
    parser.add_argument("--zabbix-host", default="AuroraDB")
    parser.add_argument(
        "--security-group", action="append", default=[],
        help="verifica este grupo em vez dos ligados ao cluster (para teste)",
    )
    parser.add_argument("--dry-run", action="store_true", help="não envia ao Zabbix")
    args = parser.parse_args()

    credentials = imds_credentials()
    public_instance = None
    group_ids = args.security_group
    if not group_ids:
        group_ids, public_instance = describe_cluster(args.cluster, args.region, credentials)
    rules = public_rules(describe_groups(group_ids, args.region, credentials), args.db_port)
    values = {"count": len(rules), "detail": "; ".join(rules)[:1000] or "nenhuma"}
    if public_instance is not None:
        values["publicly_accessible"] = int(public_instance)
    print(json.dumps({"groups": group_ids, **values}, ensure_ascii=False))
    if not args.dry_run:
        zabbix_send(args.zabbix_server, args.zabbix_port, args.zabbix_host, values)
    return 0


if __name__ == "__main__":
    sys.exit(main())
