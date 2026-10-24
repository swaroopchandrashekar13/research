# Tier 2 (E2) generation on Kaggle or Google Colab — run this file from ONE notebook cell (see the lines below).
#
# Choose ONE code revision and use it for everything: a release tag or a full 40-character commit id of
# https://github.com/swaroopchandrashekar13/research (never a branch name: a branch can move while the run is going).
#
#   import os; os.environ["RAGMV_CODE_REF"] = "<tag or full commit id>"
#   !wget -q -O /tmp/notebook_tier2.py https://raw.githubusercontent.com/swaroopchandrashekar13/research/<same ref>/experiments/E2_generation/notebook_tier2.py
#   %run /tmp/notebook_tier2.py
#
# The script checks out exactly RAGMV_CODE_REF, refuses branch names, and stops if the file you are running differs
# from that revision's copy. Optional: RAGMV_CODE_SHA256 = the expected content digest of src/ragmv
# (`python -I -c "from ragmv.integrity import source_digest; print(source_digest()['sha256'])"`).
#
# KAGGLE: Session options -> Accelerator: GPU T4 x2 (CPU also works, just slower); Internet: On.
# Results are saved to the notebook's output folder (and a zip). Pushing results to the git branch tier2-results is
# OFF unless you opt in: set RAGMV_PUSH_RESULTS=1 and add a GITHUB_TOKEN secret (fine-grained, Contents: read & write
# on this repository only). The token is passed to git through a temporary askpass helper: it never appears in a
# remote URL, in .git/config or in the log. With pushing on, a new session resumes from that branch.
#
# GPU: llama-cpp-python 0.3.36 is built with CUDA. Kaggle keeps libcuda.so in /usr/local/nvidia/lib64, outside the
# toolkit's stubs folders, so CMake's CUDA::cuda_driver target is not created unless CUDA_cuda_driver_LIBRARY is set;
# the build passes it (and links the library into the stubs folder). GPU offload is then verified with
# llama_supports_gpu_offload(); if the build or the check fails, the run falls back to CPU (same model and decoding,
# only slower). CPU and GPU rows go to differently named runs and are never mixed.
import glob
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

REPO_SLUG = "swaroopchandrashekar13/research"
CODE_REF = os.environ.get("RAGMV_CODE_REF", "")  # tag or full commit id; required (see the header)
RESULTS_BRANCH = "tier2-results"
DATASETS = ("squad2", "covidqa", "cuad", "qasper")
JOBS_PER_DATASET = 400
PUSH_EVERY = int(os.environ.get("RAGMV_PUSH_EVERY", 3600))  # seconds between pushes
MAX_HOURS = float(os.environ.get("RAGMV_MAX_HOURS", 11.5))  # stop before Kaggle's 12 h limit and push

KAGGLE = Path("/kaggle/working").exists()
COLAB = "google.colab" in sys.modules or Path("/content").exists() and not KAGGLE
PLATFORM = "kaggle" if KAGGLE else "colab" if COLAB else "local"
BASE = Path(os.environ.get("RAGMV_NOTEBOOK_BASE", "/tmp/ragmv"))  # venv, code and model: local disk, not output
OUT = Path("/kaggle/working/ragmv_tier2") if KAGGLE else BASE / "out"  # notebook output (zip, logs)
CODE, VENV, RESULTS = BASE / "code", BASE / "venv", BASE / "results"
PY = str(VENV / "bin" / "python")
# Kaggle's PYTHONPATH carries a sitecustomize that imports wrapt; keep it away from the venv and the build
CLEAN_ENV = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP")}
T0 = time.time()


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def sh(cmd, check=True, env=None, cwd=None, hide=None, capture=False):
    shown = cmd if isinstance(cmd, str) else " ".join(map(str, cmd))
    log("$ " + (shown.replace(hide, "***") if hide else shown))
    r = subprocess.run(cmd, shell=isinstance(cmd, str), env=env or CLEAN_ENV, cwd=cwd, text=True,
                       capture_output=capture)
    if check and r.returncode:
        raise RuntimeError(f"command failed ({r.returncode}): {shown.replace(hide, '***') if hide else shown}")
    return r


def push_enabled():
    return os.environ.get("RAGMV_PUSH_RESULTS") == "1"


def github_token():
    if not push_enabled():
        return None  # pushing is opt-in; without it no token is read at all
    if os.environ.get("GITHUB_TOKEN"):
        return os.environ["GITHUB_TOKEN"]
    try:
        if KAGGLE:
            from kaggle_secrets import UserSecretsClient
            return UserSecretsClient().get_secret("GITHUB_TOKEN")
        if COLAB:
            from google.colab import userdata
            return userdata.get("GITHUB_TOKEN")
    except Exception as exc:  # noqa: BLE001 - no secret configured
        log(f"no GITHUB_TOKEN secret ({type(exc).__name__}); results will only be saved to {OUT}")
    return None


def repo_url(token=None):
    """Token-free repository URL (the token, if any, reaches git only through `git_env`)."""
    if os.environ.get("RAGMV_TEST_REPO"):  # tests point this at a local bare repository
        return os.environ["RAGMV_TEST_REPO"]
    return f"https://github.com/{REPO_SLUG}.git"


def git_env(token):
    """Environment for git commands that may need the token: an askpass helper reads it from the environment of
    that one process, so it is never written to a URL, a config file or the log."""
    env = dict(CLEAN_ENV)
    if token:
        helper = BASE / "git_askpass.sh"
        BASE.mkdir(parents=True, exist_ok=True)
        helper.write_text('#!/bin/sh\ncase "$1" in Username*) echo x-access-token ;; *) echo "$RAGMV_GIT_TOKEN" ;; esac\n')
        helper.chmod(0o700)
        env.update(GIT_ASKPASS=str(helper), RAGMV_GIT_TOKEN=token, GIT_TERMINAL_PROMPT="0")
    return env


def resolve_code_ref(ref, url=None):
    """Refuse an empty ref or a branch name; accept a tag or a full commit id."""
    import re

    if not ref:
        raise SystemExit("Set RAGMV_CODE_REF to a release tag or a full 40-character commit id (see the header).")
    if re.fullmatch(r"[0-9a-f]{40}", ref):
        return ref
    url = url or repo_url()
    heads = sh(["git", "ls-remote", "--heads", url, ref], capture=True, check=False).stdout.strip()
    tags = sh(["git", "ls-remote", "--tags", url, ref], capture=True, check=False).stdout.strip()
    if heads and not tags:
        raise SystemExit(f"RAGMV_CODE_REF={ref!r} is a branch; use a tag or a full commit id so the code cannot move.")
    if not tags:
        raise SystemExit(f"RAGMV_CODE_REF={ref!r} is neither a tag nor a full commit id of {url}")
    return ref


def checkout_code(ref, dest=None):
    """Fresh checkout of exactly `ref` into `dest` (any previous checkout is replaced, never updated in place)."""
    dest = Path(dest or CODE)
    ref = resolve_code_ref(ref)
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    sh(["git", "-C", str(dest), "init", "-q"])
    sh(["git", "-C", str(dest), "fetch", "-q", "--depth", "1", repo_url(), ref])
    sh(["git", "-C", str(dest), "checkout", "-q", "FETCH_HEAD"])
    want = os.environ.get("RAGMV_CODE_SHA256")
    if want:
        got = sh([sys.executable, "-I", "-c", "import sys; sys.path.insert(0, 'src'); "
                  "from ragmv.integrity import source_digest; print(source_digest()['sha256'])"],
                 cwd=str(dest), capture=True).stdout.strip()
        if got != want:
            raise SystemExit(f"code content digest {got} != RAGMV_CODE_SHA256 {want}; refusing to run")
    return dest


def verify_same_helper(this_file, code_dir=None, rel="experiments/E2_generation/notebook_tier2.py"):
    """The script being executed must be byte-identical to the checked-out revision's copy."""
    import hashlib

    if not this_file or not Path(this_file).exists():
        return
    mine = hashlib.sha256(Path(this_file).read_bytes()).hexdigest()
    theirs = hashlib.sha256((Path(code_dir or CODE) / rel).read_bytes()).hexdigest()
    if mine != theirs:
        raise SystemExit(f"{this_file} differs from {rel} at RAGMV_CODE_REF; download the script from the same ref")


# ----------------------------------------------------------------------------- environment
def setup_code_and_venv():
    BASE.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    if not ((CODE / ".git").exists() and os.environ.get("RAGMV_CODE_READY") == "1"):
        checkout_code(CODE_REF)
    if not Path(PY).exists():
        sh([sys.executable, "-m", "pip", "install", "-q", "virtualenv"])
        sh([sys.executable, "-m", "virtualenv", "-q", str(VENV)])  # seeds its own pip (no ensurepip needed)
    reqs = [line for line in (CODE / "requirements.txt").read_text().splitlines()
            if line.strip() and not line.startswith(("#", "llama-cpp-python"))]
    (BASE / "reqs.txt").write_text("\n".join(reqs) + "\n")
    sh([PY, "-m", "pip", "install", "-q", "-r", str(BASE / "reqs.txt")])
    sh([PY, "-m", "pip", "install", "-q", "--no-deps", "-e", str(CODE)])


def gpu_present():
    return subprocess.run("nvidia-smi -L", shell=True, capture_output=True).returncode == 0


def cuda_build_env():
    """CMAKE_ARGS that let CMake create CUDA::cuda_driver on Kaggle/Colab images."""
    candidates = ["/usr/local/nvidia/lib64/libcuda.so", "/usr/lib/x86_64-linux-gnu/libcuda.so",
                  "/usr/lib64/libcuda.so", *glob.glob("/usr/local/cuda*/lib64/stubs/libcuda.so"),
                  *glob.glob("/usr/local/nvidia/lib64/libcuda.so.*")]
    libcuda = next((c for c in candidates if Path(c).exists()), None)
    cap = subprocess.run(["nvidia-smi", "--query-gpu=compute_cap", "--format=csv,noheader"], capture_output=True,
                         text=True).stdout.split()
    arch = cap[0].replace(".", "") if cap else "75"
    args = ["-DGGML_CUDA=on", f"-DCMAKE_CUDA_ARCHITECTURES={arch}"]
    env = dict(CLEAN_ENV)
    if libcuda:
        args.append(f"-DCUDA_cuda_driver_LIBRARY={libcuda}")
        libdir = str(Path(libcuda).parent)
        args.append(f"-DCMAKE_LIBRARY_PATH={libdir}")
        env["LIBRARY_PATH"] = libdir + os.pathsep + env.get("LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = libdir + os.pathsep + env.get("LD_LIBRARY_PATH", "")
        for stubs in glob.glob("/usr/local/cuda*/lib64") + glob.glob("/usr/local/cuda*/targets/x86_64-linux/lib"):
            try:  # second route for FindCUDAToolkit, which searches <toolkit>/lib64/stubs
                Path(stubs, "stubs").mkdir(exist_ok=True)
                if not Path(stubs, "stubs", "libcuda.so").exists():
                    os.symlink(libcuda, Path(stubs, "stubs", "libcuda.so"))
            except OSError:
                pass
    log(f"CUDA build: arch {arch}, libcuda {libcuda}")
    env["CMAKE_ARGS"] = " ".join(args)
    env["CMAKE_BUILD_PARALLEL_LEVEL"] = str(os.cpu_count() or 4)
    return env


def install_llama(flavour):
    """Build and install llama-cpp-python 0.3.36; returns True if GPU offload works (for flavour 'gpu')."""
    wheel_dir = BASE / "wheels" / flavour
    wheel_dir.mkdir(parents=True, exist_ok=True)
    if not glob.glob(str(wheel_dir / "llama_cpp_python-0.3.36-*.whl")):
        env = cuda_build_env() if flavour == "gpu" else dict(CLEAN_ENV, CMAKE_ARGS="-DGGML_CUDA=off")
        build_log = OUT / f"build_{flavour}.log"
        log(f"building llama-cpp-python ({flavour}); GPU builds take ~15-25 min; log: {build_log}")
        with open(build_log, "w") as f:
            r = subprocess.run([PY, "-m", "pip", "wheel", "-v", "--no-deps", "llama-cpp-python==0.3.36",
                                "-w", str(wheel_dir)], env=env, stdout=f, stderr=subprocess.STDOUT)
        if r.returncode:
            tail = build_log.read_text().splitlines()[-25:]
            log(f"{flavour} build FAILED; last lines:\n" + "\n".join(tail))
            return False
    sh([PY, "-m", "pip", "install", "-q", "--force-reinstall", "--no-deps",
        glob.glob(str(wheel_dir / "llama_cpp_python-0.3.36-*.whl"))[0]])
    sh([PY, "-m", "pip", "install", "-q", "typing-extensions", "diskcache", "jinja2"])
    check = sh([PY, "-c", "import llama_cpp; print(llama_cpp.__version__, llama_cpp.llama_supports_gpu_offload())"],
               capture=True, check=False)
    log(f"llama_cpp check: {check.stdout.strip()} {check.stderr.strip()[-300:]}")
    if flavour == "gpu":
        return check.returncode == 0 and check.stdout.strip().endswith("True")
    return check.returncode == 0


# ----------------------------------------------------------------------------- results branch
def setup_results(token, run_name):
    """Working copy of the tier2-results branch (only when pushing is enabled); earlier sessions' rows come from it."""
    if not push_enabled() or (not token and not os.environ.get("RAGMV_TEST_REPO")):
        return None, OUT / "runs" / run_name
    url = repo_url()
    env = git_env(token)
    if not (RESULTS / ".git").exists():
        has = sh(["git", "ls-remote", "--heads", url, RESULTS_BRANCH], capture=True, hide=token, env=env).stdout.strip()
        if has:
            sh(["git", "clone", "-q", "--depth", "1", "--branch", RESULTS_BRANCH, url, str(RESULTS)], hide=token, env=env)
        else:
            checkout_code(CODE_REF, RESULTS)
            sh(["git", "-C", str(RESULTS), "remote", "add", "origin", url])
            sh(["git", "-C", str(RESULTS), "checkout", "-q", "-b", RESULTS_BRANCH])
    sh(["git", "-C", str(RESULTS), "config", "user.name", f"Tier 2 runner ({PLATFORM})"])
    sh(["git", "-C", str(RESULTS), "config", "user.email", "tier2-runner@users.noreply.github.com"])
    return url, RESULTS / "experiments" / "E2_generation" / "runs" / run_name


def push(url, message, token=None):
    if url is None or not push_enabled():
        return
    rel = "experiments/E2_generation"
    sh(["git", "-C", str(RESULTS), "add", "-A", rel])
    if sh(["git", "-C", str(RESULTS), "diff", "--cached", "--quiet"], check=False).returncode == 0:
        log("push: nothing new")
        return
    sh(["git", "-C", str(RESULTS), "commit", "-q", "-m", message])
    for attempt in range(4):
        if sh(["git", "-C", str(RESULTS), "push", "-q", url, f"HEAD:{RESULTS_BRANCH}"], check=False,
              hide=token, env=git_env(token)).returncode == 0:
            log(f"pushed to branch {RESULTS_BRANCH}")
            return
        time.sleep(2 ** (attempt + 1))
    log("push failed 4 times; will retry at the next interval")


def mirror_to_output(run_dir, run_name):
    if run_dir.exists() and OUT not in run_dir.parents:
        shutil.copytree(run_dir, OUT / "runs" / run_name, dirs_exist_ok=True)


def ok_count(path):
    """Successful jobs in a dataset's log (all segments). A half-written final line from an interrupted session is
    tolerated here explicitly (progress counting only); the generator handles it with --recover-incomplete-tail."""
    n = set()
    seg_dir = Path(path).parent
    paths = ([Path(path)] if Path(path).exists() else []) + sorted(seg_dir.glob("generations.seg-[0-9][0-9][0-9].jsonl"))
    for p in paths:
        lines = p.read_text().split("\n")
        for i, line in enumerate(lines):
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                if i == len(lines) - 1:  # unterminated final line only
                    continue
                raise
            if row.get("status") == "ok":
                n.add(row["job_id"])
    return len(n)


# ----------------------------------------------------------------------------- main
def main():
    log(f"platform {PLATFORM}; GPU present: {gpu_present()}; code ref {CODE_REF or '(unset)'}; "
        f"push results: {push_enabled()}")
    setup_code_and_venv()
    verify_same_helper(globals().get("__file__"))
    flavour = "gpu" if gpu_present() and install_llama("gpu") else "cpu"
    if flavour == "cpu":
        if gpu_present():
            log("GPU build/offload not available -> CPU build (same model and decoding; slower)")
        if not install_llama("cpu"):
            raise RuntimeError("CPU build failed too; see the build log in the output folder")
    run_name = f"qwen3-4b-{PLATFORM}-{flavour}"
    token = github_token()
    url, run_dir = setup_results(token, run_name)
    sh([PY, "-I", "-m", "ragmv.fetch"], cwd=CODE)
    log(f"run {run_name}: {run_dir}")

    stop = threading.Event()

    def pusher():
        while not stop.wait(PUSH_EVERY):
            try:
                push(url, f"E2 {run_name}: progress {sum(ok_count(run_dir / d / 'generations.jsonl') for d in DATASETS)}/1600", token)
                mirror_to_output(run_dir, run_name)
            except Exception as exc:  # noqa: BLE001 - keep generating even if a push fails
                log(f"periodic push error: {exc}")

    threading.Thread(target=pusher, daemon=True).start()
    timed_out = False
    try:
        for ds in DATASETS:
            done = ok_count(run_dir / ds / "generations.jsonl")
            log(f"{ds}: {done}/{JOBS_PER_DATASET} done")
            if done >= JOBS_PER_DATASET:
                continue
            cmd = [PY, "-I", "-m", "ragmv.generate", "--backend", "llama", "--model", "qwen3-4b-q4_k_m",
                   "--model-dir", str(BASE / "models"), "--n-gpu-layers", "-1" if flavour == "gpu" else "0",
                   "--threads", str(os.cpu_count() or 4), "--dataset", ds, "--out", str(run_dir),
                   "--recover-incomplete-tail"]  # explicit: sessions can be killed mid-write; reported per session
            proc = subprocess.Popen(cmd, cwd=CODE, env=CLEAN_ENV, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True)
            for line in proc.stdout:  # stream progress lines (s/job, time left)
                print(line, end="", flush=True)
                if time.time() - T0 > MAX_HOURS * 3600:
                    timed_out = True
                    proc.terminate()
                    break
            proc.wait()
            if timed_out:
                log(f"reached {MAX_HOURS} h; stopping to push before the session limit")
                break
            if proc.returncode == 2:
                raise RuntimeError(f"{ds}: generator could not start (exit 2); see the message above")
            if proc.returncode:
                log(f"{ds}: generator exited with {proc.returncode} (3 = incomplete); continuing with the next dataset")
    finally:
        stop.set()
        counts = {ds: ok_count(run_dir / ds / "generations.jsonl") for ds in DATASETS}
        total = sum(counts.values())
        log(f"completed jobs: {counts} ({total}/1600)")
        if total >= 1600:
            analysis = run_dir.parents[1] / "analysis" / f"{run_name}-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
            sh([PY, "-I", "-m", "ragmv.analyze_generation", "--run", str(run_dir), "--out", str(analysis)], cwd=CODE,
               check=False)
            target = OUT / "analysis" / run_name
            if analysis.exists() and analysis.resolve() != target.resolve():  # without a token it is already in OUT
                shutil.copytree(analysis, target, dirs_exist_ok=True)
        push(url, f"E2 {run_name}: {total}/1600 jobs" + (" (complete, analysed)" if total >= 1600 else ""), token)
        mirror_to_output(run_dir, run_name)
        archive = shutil.make_archive(str(OUT.parent / "tier2_results"), "zip", OUT)  # outside OUT: never zips itself
        if total >= 1600:
            log(f"ALL 1600 JOBS DONE. Results are on branch {RESULTS_BRANCH} and in {archive}")
        else:
            log(f"NOT FINISHED ({total}/1600). Start the notebook again (Save & Run All): it resumes from branch "
                f"{RESULTS_BRANCH}" if url else f"NOT FINISHED ({total}/1600); without GITHUB_TOKEN it cannot resume")


if __name__ == "__main__":
    main()
