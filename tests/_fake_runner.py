"""Runner giả cho test agent: cùng dòng lệnh với automation.runner nhưng không mở trình duyệt.

    python -m tests._fake_runner <job> --input in.json --output out.json
Job: echo | files (trả về một file) | fail | slow (chạy ~60 giây, để test huỷ lệnh)
"""
import argparse
import json
import os
import time
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("--input")
    ap.add_argument("--output")
    args = ap.parse_args()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    print(f"lang={os.environ.get('L2M_LANG')} game={payload.get('game')}", flush=True)
    if args.job == "slow":
        for i in range(120):
            print(f"tick {i}", flush=True)
            time.sleep(0.5)
    for i in range(3):
        print(f"step {i} {payload.get('word', '')}", flush=True)
        time.sleep(0.3)
    result = {"ok": args.job != "fail", "echo": payload}
    if args.job == "files":
        f = Path(args.output).with_name(f"report-{payload['word']}.xlsx")
        f.write_bytes(b"PK fake " + payload["word"].encode())
        result["results"] = [{"file": str(f.resolve()), "shop": "SEA"}]
    if args.job == "fail":
        result["error"] = "boom"
    Path(args.output).write_text(json.dumps(result), encoding="utf-8")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
