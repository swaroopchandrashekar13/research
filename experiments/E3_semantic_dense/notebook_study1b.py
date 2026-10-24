# Study 1b (E3: semantic chunking + dense retrieval) on Kaggle — run from ONE notebook cell:
#
#   !wget -q -O /tmp/notebook_study1b.py https://raw.githubusercontent.com/swaroopchandrashekar13/reasearch/claude/phd-research-mentor-vtven3/experiments/E3_semantic_dense/notebook_study1b.py
#   %run /tmp/notebook_study1b.py
#
# Kaggle settings: Accelerator GPU T4 x2 (GPU is needed: ~5M words are embedded with bge-m3), Internet On, secret
# GITHUB_TOKEN attached (as for Tier 2). Then Save Version -> Save & Run All (Commit).
#
# SPLIT: "exploratory" (the pilot) by default. The confirmatory split runs only after research/preregistration_study1b.md
# is frozen (the script checks this and refuses otherwise). Results are pushed every hour to the git branch
# study1b-results and once at the end; a new session resumes (finished datasets are skipped).
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

SPLIT = os.environ.get("RAGMV_SPLIT", "exploratory")
DATASETS = ("squad2", "covidqa", "cuad", "qasper")

# Reuse the tested Tier 2 notebook helpers (venv, clean environment, git push/resume) from the same branch.
_helper = Path("/tmp/notebook_tier2.py")
subprocess.run(["wget", "-q", "-O", str(_helper), "https://raw.githubusercontent.com/swaroopchandrashekar13/reasearch/"
                "claude/phd-research-mentor-vtven3/experiments/E2_generation/notebook_tier2.py"], check=True)
sys.path.insert(0, "/tmp")
import notebook_tier2 as nb  # noqa: E402

nb.RESULTS_BRANCH = "study1b-results"
nb.RESULTS = nb.BASE / "results1b"
nb.OUT = Path("/kaggle/working/ragmv_study1b") if nb.KAGGLE else nb.BASE / "out1b"
log, sh = nb.log, nb.sh


def main():
    log(f"Study 1b, split {SPLIT}; GPU present: {nb.gpu_present()}")
    if not nb.gpu_present():
        log("WARNING: no GPU. Embedding the corpora on CPU takes many hours; enable a GPU accelerator.")
    nb.setup_code_and_venv()
    prereg = (nb.CODE / "research" / "preregistration_study1b.md").read_text()
    if SPLIT == "confirmatory" and "1.0 (frozen)" not in prereg:
        raise SystemExit("Refusing the confirmatory split: preregistration_study1b.md is not frozen yet.")
    sh([nb.PY, "-m", "pip", "install", "-q", "-r", str(nb.CODE / "requirements-study1b.txt")])
    sh([nb.PY, "-I", "-m", "ragmv.fetch"], cwd=nb.CODE)
    token = nb.github_token()
    run_name = f"{SPLIT}-{nb.PLATFORM}-{'gpu' if nb.gpu_present() else 'cpu'}"
    url, run_dir = nb.setup_results(token, run_name)
    if url:  # results live under experiments/E3_semantic_dense in the results branch
        run_dir = nb.RESULTS / "experiments" / "E3_semantic_dense" / "runs" / run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    env = dict(nb.CLEAN_ENV, HF_HOME=str(nb.BASE / "hf"))
    stop = threading.Event()

    def pusher():
        while not stop.wait(nb.PUSH_EVERY):
            try:
                push(url, token, f"E3 {run_name}: progress")
            except Exception as exc:  # noqa: BLE001
                log(f"periodic push error: {exc}")

    threading.Thread(target=pusher, daemon=True).start()
    try:
        for ds in DATASETS:
            if (run_dir / ds / "manifest.json").exists():
                log(f"{ds}: already done")
                continue
            t0 = time.time()
            sh([nb.PY, "-I", "-m", "ragmv.run1b", "--dataset", ds, "--split", SPLIT, "--out", str(run_dir),
                "--device", "cuda" if nb.gpu_present() else "cpu", "--batch-size", "32",
                "--cache-dir", str(nb.BASE / "emb_cache")], cwd=nb.CODE, env=env)
            log(f"{ds}: done in {(time.time() - t0) / 60:.1f} min")
            push(url, token, f"E3 {run_name}: {ds} done")
        label = "EXPLORATORY" if SPLIT == "exploratory" else "CONFIRMATORY"
        analysis = run_dir.parents[1] / "analysis" / run_name
        sh([nb.PY, "-I", "-m", "ragmv.analyze1b", "--run", str(run_dir), "--label", label, "--out", str(analysis)],
           cwd=nb.CODE, env=env)
        log("STUDY 1B RUN COMPLETE")
    finally:
        stop.set()
        push(url, token, f"E3 {run_name}: final")
        if url:
            import shutil
            shutil.copytree(run_dir.parents[1], nb.OUT / "E3_semantic_dense", dirs_exist_ok=True)


def push(url, token, message):
    if url is None:
        return
    rel = "experiments/E3_semantic_dense"
    sh(["git", "-C", str(nb.RESULTS), "add", "-A", rel])
    if sh(["git", "-C", str(nb.RESULTS), "diff", "--cached", "--quiet"], check=False).returncode == 0:
        return
    sh(["git", "-C", str(nb.RESULTS), "commit", "-q", "-m", message])
    for attempt in range(4):
        if sh(["git", "-C", str(nb.RESULTS), "push", "-q", url, f"HEAD:{nb.RESULTS_BRANCH}"], check=False,
              hide=token).returncode == 0:
            log(f"pushed to branch {nb.RESULTS_BRANCH}")
            return
        time.sleep(2 ** (attempt + 1))
    log("push failed 4 times; will retry later")


if __name__ == "__main__":
    main()
