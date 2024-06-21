#!/usr/bin/env python3
import json
import os
from pathlib import Path
from typing import Dict, List
import sys
import subprocess
import hvac  # type: ignore


def run_command(command: List) -> str:  # pylint: disable=missing-function-docstring
    out = subprocess.run(
        command, env=ENV_VARS, text=True, timeout=10, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
    )
    if out.returncode != 0:
        print(f"Return code: {out.returncode}")
        print(out.stderr)
        print(out.stdout)
        sys.exit(1)
    return out.stdout


MINIO_CLUSTER_NAME = os.environ.get("MINIO_CLUSTER_NAME")
ENV_VARS = os.environ.copy()
ENV_VARS["MC_CONFIG_DIR"] = "/tmp/.mc"
client = hvac.Client()
if not client.is_authenticated():
    print("Vault is not authenticated")
    sys.exit(1)

list_response = client.secrets.kv.v2.list_secrets(
    path=f"minio/clusters/{MINIO_CLUSTER_NAME}/servers", mount_point="secret"
)

servers_map: Dict[str, Dict] = {}

for server in list_response["data"]["keys"]:
    server_response = client.secrets.kv.v2.read_secret_version(
        path=f"minio/clusters/{MINIO_CLUSTER_NAME}/servers/{server}config",
        mount_point="secret",
        raise_on_deleted_version=False
    )
    servers_map[server[:-1]] = server_response["data"]["data"]
    path = Path(f"{ENV_VARS['MC_CONFIG_DIR']}/CAs")
    path.mkdir(parents=True, exist_ok=True)
    with open(f"{ENV_VARS['MC_CONFIG_DIR']}/certs/CAs/{server[:-1]}.pem", "w", encoding="utf-8") as f:
        f.write(server_response["data"]["data"]["ca_cert"])
    run_command(
        [
            "mc",
            "alias",
            "set",
            server[:-1],
            f"https://{server_response['data']['data']['preferred_mc_host']}:"
            f"{server_response['data']['data']['server_port']}",
            server_response["data"]["data"]["root_user"],
            server_response["data"]["data"]["root_password"],
        ]
    )

for server, server_config in servers_map.items():
    rep_info = run_command(
        [
            "mc",
            "admin",
            "replicate",
            "info",
            server,
            "--json",
        ]
    )
    print(json.loads(rep_info))
    replication_servers: Dict[str, Dict] = servers_map.copy()
    del replication_servers[server]
    add_replicate_info_out = run_command(
        [
            "mc",
            "admin",
            "replicate",
            "info",
            server,
            "--json",
        ]
    )
    add_replicate_info_out = json.loads(add_replicate_info_out)
    print(add_replicate_info_out)
    for replication_server, replication_server_config in replication_servers.items():
        add_replicate_out = run_command(
            [
                "mc",
                "admin",
                "replicate",
                "add",
                server,
                replication_server,
                "--json",
            ]
        )
        add_replicate_out = json.loads(add_replicate_out)
        print(add_replicate_out)
        exit(0)
