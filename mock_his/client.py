from pathlib import Path
import argparse
import json
import sys

import requests


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from mock_his.sample_loader import load_records


URL = "http://127.0.0.1:8001/api/ingest/"


def payload(rec):
    return {
        **rec["payload"],
        "patient_id": int(float(rec["pid"])),
        "patient_name": str(rec["name"]),
        "source": "mock_his",
        "source_idx": int(rec["idx"]),
        "truth": rec.get("truth") or None,
    }


def send_one(url, rec):
    res = requests.post(url, json=payload(rec), timeout=30)
    try:
        body = res.json()
    except ValueError:
        body = {"text": res.text}
    return {
        "status_code": res.status_code,
        "response": body,
    }


def show(obj):
    enc = (sys.stdout.encoding or "").lower()
    ascii_only = "utf" not in enc
    print(json.dumps(obj, ensure_ascii=ascii_only, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--url", default=URL)
    args = parser.parse_args()
    samples = load_records(limit=args.count)
    for idx, rec in enumerate(samples, start=1):
        out = send_one(args.url, rec)
        print(f"sample {idx}")
        show(out)


if __name__ == "__main__":
    main()
