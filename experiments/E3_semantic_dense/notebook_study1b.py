# Study 1b (E3: semantic chunking + dense retrieval) on Kaggle — run from ONE notebook cell:
#
#   import os
#   os.environ["RAGMV_REPO_URL"] = "<clone URL of the repository that holds this code>"
#   os.environ["RAGMV_CODE_REF"] = "<release tag or full commit id>"   # never a branch name
#   # save this file, at the same revision, as /tmp/notebook_study1b.py (the hosting service's raw-file link), then
#   %run /tmp/notebook_study1b.py
#
# Kaggle settings: Accelerator GPU T4 x2 (GPU is needed: ~5M words are embedded with bge-m3), Internet On.
# Pushing results to the branch study1b-results is opt-in (RAGMV_PUSH_RESULTS=1 plus a GITHUB_TOKEN secret, as for
# Tier 2); otherwise results stay in the notebook's output folder.
#
# SPLIT: "exploratory" (the pilot) by default. The confirmatory split runs only if research/preregistration_study1b.md
# says version 1.0 (frozen). The helpers are imported from the SAME checkout (RAGMV_CODE_REF), never fetched from a
# branch, and this script must be byte-identical to that revision's copy.
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

SPLIT = os.environ.get("RAGMV_SPLIT", "exploratory")
DATASETS = ("squad2", "covidqa", "cuad", "qasper")
_BASE = Path(os.environ.get("RAGMV_NOTEBOOK_BASE", "/tmp/ragmv"))
_CODE = _BASE / "code"


def _bootstrap_checkout():
    """Check out RAGMV_CODE_REF once, then import notebook_tier2 from that checkout (same revision)."""
    import re

    ref = os.environ.get("RAGMV_CODE_REF", "")
    url = os.environ.get("RAGMV_TEST_REPO") or os.environ.get("RAGMV_REPO_URL", "")
    if not url:
        raise SystemExit("Set RAGMV_REPO_URL to the clone URL of the repository that holds this code.")
    if not ref:
        raise SystemExit("Set RAGMV_CODE_REF to a release tag or a full 40-character commit id.")
    if not re.fullmatch(r"[0-9a-f]{40}", ref):
        heads = subprocess.run(["git", "ls-remote", "--heads", url, ref], capture_output=True, text=True).stdout.strip()
        tags = subprocess.run(["git", "ls-remote", "--tags", url, ref], capture_output=True, text=True).stdout.strip()
        if heads and not tags:
            raise SystemExit(f"RAGMV_CODE_REF={ref!r} is a branch; use a tag or a full commit id.")
        if not tags:
            raise SystemExit(f"RAGMV_CODE_REF={ref!r} is neither a tag nor a full commit id of {url}")
    if _CODE.exists():
        import shutil
        shutil.rmtree(_CODE)
    _CODE.mkdir(parents=True)
    for cmd in (["git", "-C", str(_CODE), "init", "-q"], ["git", "-C", str(_CODE), "fetch", "-q", "--depth", "1", url, ref],
                ["git", "-C", str(_CODE), "checkout", "-q", "FETCH_HEAD"]):
        subprocess.run(cmd, check=True)
    os.environ["RAGMV_CODE_READY"] = "1"  # notebook_tier2.setup_code_and_venv keeps this checkout
    sys.path.insert(0, str(_CODE / "experiments" / "E2_generation"))
    import notebook_tier2 as helpers

    helpers.verify_same_helper(globals().get("__file__"), _CODE, "experiments/E3_semantic_dense/notebook_study1b.py")
    return helpers


nb = _bootstrap_checkout() if __name__ == "__main__" else None

def _configure(helpers):
    helpers.RESULTS_BRANCH = "study1b-results"
    helpers.RESULTS = helpers.BASE / "results1b"
    helpers.OUT = Path("/kaggle/working/ragmv_study1b") if helpers.KAGGLE else helpers.BASE / "out1b"


def log(msg):
    nb.log(msg)


def sh(*a, **kw):
    return nb.sh(*a, **kw)


def main():
    _configure(nb)
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
        analysis = run_dir.parents[1] / "analysis" / f"{run_name}-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
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
    if url is None or not nb.push_enabled():
        return
    rel = "experiments/E3_semantic_dense"
    sh(["git", "-C", str(nb.RESULTS), "add", "-A", rel])
    if sh(["git", "-C", str(nb.RESULTS), "diff", "--cached", "--quiet"], check=False).returncode == 0:
        return
    sh(["git", "-C", str(nb.RESULTS), "commit", "-q", "-m", message])
    for attempt in range(4):
        if sh(["git", "-C", str(nb.RESULTS), "push", "-q", url, f"HEAD:{nb.RESULTS_BRANCH}"], check=False,
              hide=token, env=nb.git_env(token)).returncode == 0:
            log(f"pushed to branch {nb.RESULTS_BRANCH}")
            return
        time.sleep(2 ** (attempt + 1))
    log("push failed 4 times; will retry later")


if __name__ == "__main__":
    main()
