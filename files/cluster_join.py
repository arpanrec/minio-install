#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--access_key")
parser.add_argument("--secret_key")
parser.add_argument("--inventory_hosts")
args = parser.parse_args()
print(args.access_key)
print(args.secret_key)
print(args.inventory_hosts)
