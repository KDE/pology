import os
import subprocess
import sys

import pytest


srcdir = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)


def run_posieve(*args):
    env = dict(os.environ)
    pythonpath = [srcdir]
    if env.get("PYTHONPATH"):
        pythonpath.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(pythonpath)
    return subprocess.run(
        [sys.executable] + list(args),
        cwd=srcdir,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )


@pytest.fixture(
    scope="module",
    params=[
        [os.path.join(srcdir, "scripts", "posieve.py")],
        ["-m", "pology.scripts.posieve"],
    ],
    ids=["wrapper", "module"],
)
def posieve(request):
    return request.param


def test_list_sieve_names(posieve):
    proc = run_posieve(*(posieve + ["--list-sieve-names"]))
    assert proc.returncode == 0, proc.stderr
    assert "check-rules" in proc.stdout.split()


def test_help(posieve):
    proc = run_posieve(*(posieve + ["--help"]))
    assert proc.returncode == 0, proc.stderr
    assert "Usage:" in proc.stdout
