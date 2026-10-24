"""Record the execution environment so every experiment can cite the hardware and software it ran on.

Usage: python tools/env_probe.py --out <new file> [--no-network] [--overwrite]

`env/environment.json` is the historical record of the environment the Study 1 runs used; the probe refuses to
overwrite an existing file unless --overwrite is given, so write new probes to a new path.

Network reachability is probed with short HTTPS requests; a host counts as reachable
only if it answers with any HTTP status (proxy denials surface as connection errors).
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PROBE_HOSTS = {
    "pypi": "https://pypi.org/simple/numpy/",
    "github_raw": "https://raw.githubusercontent.com/github/gitignore/main/Python.gitignore",
    "huggingface": "https://huggingface.co/api/models?limit=1",
    "arxiv_api": "https://export.arxiv.org/api/query?search_query=ti:ReAct&max_results=1",
    "semantic_scholar": "https://api.semanticscholar.org/graph/v1/paper/search?query=rag&limit=1",
    "crossref": "https://api.crossref.org/works?rows=1",
    "openreview": "https://api2.openreview.net/notes?limit=1",
}


def _run(cmd: list[str]) -> str | None:
    if shutil.which(cmd[0]) is None:
        return None
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=20).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return None


def _mem_total_gib() -> float | None:
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                return round(int(line.split()[1]) / 1024**2, 1)
    except OSError:
        return None
    return None


def _cpu_model() -> str | None:
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        return None
    return platform.processor() or None


def _reachable(url: str, timeout: float = 10.0) -> dict:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return {"reachable": True, "status": resp.status}
    except urllib.error.HTTPError as exc:  # host answered, just not 2xx
        return {"reachable": True, "status": exc.code}
    except (urllib.error.URLError, OSError) as exc:
        return {"reachable": False, "error": type(exc).__name__ + ": " + str(exc)[:120]}


def probe(check_network: bool = True) -> dict:
    gpu = _run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"])
    return {
        "probed_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "cpu_model": _cpu_model(),
        "cpu_count": os.cpu_count(),
        "mem_total_gib": _mem_total_gib(),
        "gpu": gpu or None,
        "latex": {tool: shutil.which(tool) is not None for tool in ("pdflatex", "latexmk", "bibtex")},
        "network": {name: _reachable(url) for name, url in PROBE_HOSTS.items()} if check_network else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", required=True, help="new output file (existing files are not overwritten)")
    parser.add_argument("--no-network", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    out = Path(args.out)
    if out.exists() and not args.overwrite:
        parser.error(f"{out} exists (it may be a historical record); choose a new --out or pass --overwrite")
    info = probe(check_network=not args.no_network)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(info, indent=2) + "\n")
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
