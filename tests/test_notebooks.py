"""Notebook bootstrap uses one explicitly selected revision, pushing is opt-in, tokens never persist.

Runs against a local bare repository (RAGMV_TEST_REPO); no network, no upload, no push to any remote."""
import importlib.util
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "experiments" / "E2_generation" / "notebook_tier2.py"
GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@example.invalid"}


def _git(*args, cwd=None):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True,
                          env={**os.environ, **GIT_ENV}).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    _git("init", "-q", "-b", "main", cwd=work)
    (work / "experiments" / "E2_generation").mkdir(parents=True)
    (work / "experiments" / "E2_generation" / "notebook_tier2.py").write_bytes(NB.read_bytes())
    (work / "marker.txt").write_text("v1\n")
    _git("add", "-A", cwd=work)
    _git("commit", "-q", "-m", "one", cwd=work)
    sha = _git("rev-parse", "HEAD", cwd=work)
    _git("tag", "v-test", cwd=work)
    _git("branch", "feature", cwd=work)
    bare = tmp_path / "bare.git"
    _git("clone", "-q", "--bare", str(work), str(bare))
    return {"bare": bare, "sha": sha, "work": work}


def _load(monkeypatch, tmp_path, repo, ref="v-test", push=None):
    monkeypatch.setenv("RAGMV_NOTEBOOK_BASE", str(tmp_path / "base"))
    monkeypatch.setenv("RAGMV_TEST_REPO", str(repo["bare"]))
    monkeypatch.setenv("RAGMV_CODE_REF", ref)
    if push:
        monkeypatch.setenv("RAGMV_PUSH_RESULTS", "1")
    else:
        monkeypatch.delenv("RAGMV_PUSH_RESULTS", raising=False)
    for k, v in GIT_ENV.items():
        monkeypatch.setenv(k, v)
    spec = importlib.util.spec_from_file_location("notebook_tier2_under_test", NB)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.CLEAN_ENV.update(GIT_ENV)
    return mod


def test_code_ref_is_required_and_branches_are_refused(monkeypatch, tmp_path, repo):
    nb = _load(monkeypatch, tmp_path, repo)
    with pytest.raises(SystemExit, match="RAGMV_CODE_REF"):
        nb.resolve_code_ref("")
    with pytest.raises(SystemExit, match="is a branch"):
        nb.resolve_code_ref("feature")
    with pytest.raises(SystemExit, match="neither a tag"):
        nb.resolve_code_ref("no-such-ref")
    assert nb.resolve_code_ref("v-test") == "v-test"
    assert nb.resolve_code_ref(repo["sha"]) == repo["sha"]


def test_checkout_is_exactly_the_selected_revision(monkeypatch, tmp_path, repo):
    nb = _load(monkeypatch, tmp_path, repo, ref=repo["sha"])
    dest = nb.checkout_code(repo["sha"], tmp_path / "code")
    assert (dest / "marker.txt").read_text() == "v1\n"
    assert _git("rev-parse", "HEAD", cwd=dest) == repo["sha"]
    nb.verify_same_helper(str(NB), dest)  # the running script equals the checkout's copy
    other = tmp_path / "other.py"
    other.write_text("# a different helper\n")
    with pytest.raises(SystemExit, match="differs"):
        nb.verify_same_helper(str(other), dest)


def test_content_digest_mismatch_stops_the_checkout(monkeypatch, tmp_path, repo):
    nb = _load(monkeypatch, tmp_path, repo)
    monkeypatch.setenv("RAGMV_CODE_SHA256", "0" * 64)
    (repo["work"] / "src" / "ragmv").mkdir(parents=True)
    (repo["work"] / "src" / "ragmv" / "__init__.py").write_text("")
    (repo["work"] / "src" / "ragmv" / "integrity.py").write_bytes((ROOT / "src/ragmv/integrity.py").read_bytes())
    _git("add", "-A", cwd=repo["work"])
    _git("commit", "-q", "-m", "two", cwd=repo["work"])
    sha = _git("rev-parse", "HEAD", cwd=repo["work"])
    _git("push", "-q", str(repo["bare"]), "HEAD:main", cwd=repo["work"])
    with pytest.raises(SystemExit, match="content digest"):
        nb.checkout_code(sha, tmp_path / "code2")


def test_pushing_is_opt_in(monkeypatch, tmp_path, repo):
    nb = _load(monkeypatch, tmp_path, repo)
    calls = []
    monkeypatch.setattr(nb, "sh", lambda *a, **k: calls.append(a))
    assert nb.github_token() is None  # the secret is not even read without opt-in
    url, run_dir = nb.setup_results("tok", "run")
    nb.push("some-url", "msg", "tok")
    assert url is None and calls == [] and run_dir == nb.OUT / "runs" / "run"


def test_token_never_reaches_urls_config_or_logs(monkeypatch, tmp_path, repo, capsys):
    nb = _load(monkeypatch, tmp_path, repo, push=True)
    secret = "SECRET-token-123"
    env = nb.git_env(secret)
    helper = Path(env["GIT_ASKPASS"]).read_text()
    assert secret not in helper and env["RAGMV_GIT_TOKEN"] == secret
    assert secret not in nb.repo_url(secret)
    url, run_dir = nb.setup_results(secret, "run")
    cfg = (nb.RESULTS / ".git" / "config").read_text()
    assert url == str(repo["bare"]) and secret not in cfg
    assert secret not in capsys.readouterr().out


def test_study1b_notebook_imports_helpers_from_the_checkout_not_a_url():
    src = (ROOT / "experiments" / "E3_semantic_dense" / "notebook_study1b.py").read_text()
    code = "\n".join(line for line in src.splitlines() if not line.lstrip().startswith("#"))
    assert "wget" not in code and "raw.githubusercontent.com" not in code
    assert "verify_same_helper" in code and "RAGMV_CODE_REF" in code
