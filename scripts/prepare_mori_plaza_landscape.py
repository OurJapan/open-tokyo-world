# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Prepare a local, fixed-source landscape plan; never publish its geometry."""
import argparse
import json
from pathlib import Path

from mori_plaza_landscape_v1 import digest, prepare_plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='New JSON file under a local output folder')
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Use a new plan output')
    plan = prepare_plan(args.inputs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(plan, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'sha256': digest(args.output), 'audit': plan['audit']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
