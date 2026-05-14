from pathlib import Path
import argparse
import json
import sys

import requests


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from mock_his.sample_loader import load_samples


URL = "http://127.0.0.1:8001/api/predict/"


def send_one(url, data):
    res = requests.post(url, json=data, timeout=30)
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
    samples = load_samples(count=args.count)
    for idx, data in enumerate(samples, start=1):
        out = send_one(args.url, data)
        print(f"sample {idx}")
        show(out)


if __name__ == "__main__":
    main()
