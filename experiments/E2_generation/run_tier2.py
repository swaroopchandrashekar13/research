"""Tier 2 (E2) runner for any computer: Windows, Linux or Mac, started from PyCharm or a terminal.

PyCharm: open the repository folder -> set a Python 3.12+ interpreter (virtualenv) -> install requirements/core.txt
and requirements/generation.txt -> right-click this file -> Run 'run_tier2'. Terminal:
python experiments/E2_generation/run_tier2.py

Resumable: stop it any time and run it again; finished jobs are skipped. When it prints ALL 1600 JOBS DONE it has
run the planned analysis and written tier2_results_<run>.zip in the repository folder (upload that file).
Options: --gpu (offload to an NVIDIA or Apple GPU), --run NAME (default: qwen3-4b-local; letters, digits, ".", "_"
and "-" only).
"""
import argparse
import platform
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
DATASETS = ("squad2", "covidqa", "cuad", "qasper")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gpu", action="store_true", help="offload all layers to the GPU (CUDA or Metal build needed)")
    ap.add_argument("--run", default="qwen3-4b-local", help="run name (a new directory under runs/)")
    ap.add_argument("--threads", type=int, default=None, help="CPU threads (default: all cores)")
    args = ap.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.run):
        ap.error("--run may contain only letters, digits, '.', '_' and '-' (it names a directory under runs/)")

    if sys.version_info < (3, 12):
        sys.exit(f"Python 3.12 or newer is needed (this is {platform.python_version()}).")
    missing = [m for m in ("numpy", "bm25s", "yaml", "llama_cpp", "huggingface_hub") if not _importable(m)]
    if missing:
        sys.exit(f"Missing packages {missing}. In the project's interpreter: pip install -r requirements/core.txt "
                 "-r requirements/generation.txt")

    import os
    from ragmv import analyze_generation, fetch, generate

    os.chdir(ROOT)  # data/raw and relative paths are resolved from the repository root
    fetch.fetch(Path("data/MANIFEST.yaml"), None)  # datasets and extracted members, SHA-256 checked
    run_dir = ROOT / "experiments" / "E2_generation" / "runs" / args.run
    threads = args.threads or os.cpu_count() or 4
    print(f"run: {run_dir}\nthreads: {threads}, gpu: {args.gpu}\n"
          "First time: downloads the model (~2.5 GB). Time estimates appear after the first few jobs.", flush=True)
    for ds in DATASETS:
        rc = generate.main(["--backend", "llama", "--model", "qwen3-4b-q4_k_m", "--n-gpu-layers", "-1" if args.gpu else "0",
                            "--threads", str(threads), "--dataset", ds, "--out", str(run_dir), "--recover-incomplete-tail"])
        if rc == generate.EXIT_CANNOT_START:
            print(f"{ds}: the generator could not start (see the message above)")
            return 2

    counts = {ds: len(generate.done_ids(run_dir / ds)) for ds in DATASETS}
    print("completed jobs:", counts, flush=True)
    if sum(counts.values()) < 1600:
        print("NOT FINISHED -> run this file again; finished jobs are skipped")
        return 1
    analysis = ROOT / "experiments" / "E2_generation" / "analysis" / args.run
    if analyze_generation.main(["--run", str(run_dir), "--out", str(analysis)]) != 0:
        return 2
    staging = ROOT / f"tier2_results_{args.run}"
    shutil.rmtree(staging, ignore_errors=True)
    shutil.copytree(run_dir, staging / "runs" / args.run)
    shutil.copytree(analysis, staging / "analysis" / args.run)
    archive = shutil.make_archive(str(staging), "zip", staging)
    shutil.rmtree(staging)
    print(f"ALL 1600 JOBS DONE -> upload {archive}")
    return 0


def _importable(name: str) -> bool:
    try:
        __import__(name)
        return True
    except ImportError:
        return False


if __name__ == "__main__":
    sys.exit(main())
