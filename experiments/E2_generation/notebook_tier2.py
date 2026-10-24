# Tier 2 (E2) generation on Kaggle or Google Colab — run this file from ONE notebook cell (see the two lines below).
#
#   !wget -q -O /tmp/notebook_tier2.py https://raw.githubusercontent.com/swaroopchandrashekar13/reasearch/claude/phd-research-mentor-vtven3/experiments/E2_generation/notebook_tier2.py
#   %run /tmp/notebook_tier2.py
#
# KAGGLE: Session options -> Accelerator: GPU T4 x2 (CPU also works, just slower); Internet: On.
#   Add-ons -> Secrets -> add GITHUB_TOKEN (a GitHub fine-grained token with Contents: read & write on this repo) and
#   tick it for the notebook. Then "Save Version" -> "Save & Run All (Commit)" runs it unattended (up to 12 h).
# COLAB: the same, with the token in the key icon (Secrets) as GITHUB_TOKEN.
#
# Persistence: every PUSH_EVERY seconds the finished rows are committed and pushed to the git branch tier2-results;
# a new session resumes from that branch, so a run longer than one session simply continues in the next one. The
# script stops itself shortly before the platform's time limit and pushes once more. Without a token it still runs and
# saves to the notebook's output folder, but cannot resume across sessions.
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

REPO_SLUG = "swaroopchandrashekar13/reasearch"
CODE_BRANCH = "claude/phd-research-mentor-vtven3"
RESULTS_BRANCH = "tier2-results"
DATASETS = ("squad2", "covidqa", "cuad", "qasper")
JOBS_PER_DATASET = 400
PUSH_EVERY = int(os.environ.get("RAGMV_PUSH_EVERY", 3600))  # seconds between pushes
MAX_HOURS = float(os.environ.get("RAGMV_MAX_HOURS", 11.5))  # stop before Kaggle's 12 h limit and push

KAGGLE = Path("/kaggle/working").exists()
COLAB = "google.colab" in sys.modules or Path("/content").exists() and not KAGGLE
PLATFORM = "kaggle" if KAGGLE else "colab" if COLAB else "local"
BASE = Path("/tmp/ragmv")  # venv, code and model: fast local disk, not part of any output
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


def github_token():
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


def repo_url(token):
    if os.environ.get("RAGMV_TEST_REPO"):  # tests point this at a local bare repository
        return os.environ["RAGMV_TEST_REPO"]
    return f"https://x-access-token:{token}@github.com/{REPO_SLUG}.git" if token else f"https://github.com/{REPO_SLUG}.git"


# ----------------------------------------------------------------------------- environment
def setup_code_and_venv():
    BASE.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    if (CODE / ".git").exists():
        sh(f"git -C {CODE} fetch --depth 1 origin {CODE_BRANCH} && git -C {CODE} reset --hard FETCH_HEAD")
    else:
        sh(["git", "clone", "--depth", "1", "--branch", CODE_BRANCH, repo_url(None), str(CODE)])
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
    """Working copy of the tier2-results branch; earlier sessions' rows are restored from it."""
    if not token and not os.environ.get("RAGMV_TEST_REPO"):
        return None, OUT / "runs" / run_name
    url = repo_url(token)
    if not (RESULTS / ".git").exists():
        has = sh(["git", "ls-remote", "--heads", url, RESULTS_BRANCH], capture=True, hide=token).stdout.strip()
        branch = RESULTS_BRANCH if has else CODE_BRANCH
        sh(["git", "clone", "--depth", "1", "--branch", branch, url, str(RESULTS)], hide=token)
        if not has:
            sh(["git", "-C", str(RESULTS), "checkout", "-b", RESULTS_BRANCH])
    sh(["git", "-C", str(RESULTS), "config", "user.name", f"Tier 2 runner ({PLATFORM})"])
    sh(["git", "-C", str(RESULTS), "config", "user.email", "tier2-runner@users.noreply.github.com"])
    return url, RESULTS / "experiments" / "E2_generation" / "runs" / run_name


def push(url, message, token=None):
    if url is None:
        return
    rel = "experiments/E2_generation"
    sh(["git", "-C", str(RESULTS), "add", "-A", rel])
    if sh(["git", "-C", str(RESULTS), "diff", "--cached", "--quiet"], check=False).returncode == 0:
        log("push: nothing new")
        return
    sh(["git", "-C", str(RESULTS), "commit", "-q", "-m", message])
    for attempt in range(4):
        if sh(["git", "-C", str(RESULTS), "push", "-q", url, f"HEAD:{RESULTS_BRANCH}"], check=False,
              hide=token).returncode == 0:
            log(f"pushed to branch {RESULTS_BRANCH}")
            return
        time.sleep(2 ** (attempt + 1))
    log("push failed 4 times; will retry at the next interval")


def mirror_to_output(run_dir, run_name):
    if run_dir.exists() and OUT not in run_dir.parents:
        shutil.copytree(run_dir, OUT / "runs" / run_name, dirs_exist_ok=True)


def ok_count(path):
    n = set()
    for line in (open(path) if path.exists() else []):
        try:
            row = json.loads(line)
        except json.JSONDecodeError:  # half-written line from an interruption
            continue
        if row.get("status") == "ok":
            n.add(row["job_id"])
    return len(n)


# ----------------------------------------------------------------------------- main
def main():
    log(f"platform {PLATFORM}; GPU present: {gpu_present()}")
    setup_code_and_venv()
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
                   "--threads", str(os.cpu_count() or 4), "--dataset", ds, "--out", str(run_dir)]
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
            if proc.returncode:
                log(f"{ds}: generator exited with {proc.returncode}; continuing with the next dataset")
    finally:
        stop.set()
        counts = {ds: ok_count(run_dir / ds / "generations.jsonl") for ds in DATASETS}
        total = sum(counts.values())
        log(f"completed jobs: {counts} ({total}/1600)")
        if total >= 1600:
            analysis = run_dir.parents[1] / "analysis" / run_name
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
