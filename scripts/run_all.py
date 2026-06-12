#!/usr/bin/env python3
"""Download each configured JFreeChart version and run the QMOOD extractor on it.

Usage:
    python3 run_all.py                 # analyze every version in versions.json
    python3 run_all.py 1.0.6 1.0.9     # analyze only the listed labels
"""
import json
import os
import shutil
import subprocess
import sys
import time

import extract_metrics as em

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
WORK = os.path.join(ROOT, "work")
REPO = "jfree/jfreechart"


def source_root(tree):
    """Main source dir: excludes tests/, experimental/, swt/ automatically."""
    for cand in ("src/main/java", "source", "src"):
        p = os.path.join(tree, cand)
        if os.path.isdir(p):
            return p
    raise RuntimeError(f"no source root under {tree}")


def fetch(ref, dest):
    url = f"https://codeload.github.com/{REPO}/tar.gz/{ref}"
    os.makedirs(dest, exist_ok=True)
    tarball = os.path.join(dest, "src.tar.gz")
    subprocess.run(["curl", "-sL", "-o", tarball, url], check=True)
    subprocess.run(["tar", "xzf", tarball, "-C", dest], check=True)
    os.remove(tarball)
    dirs = [d for d in os.listdir(dest) if os.path.isdir(os.path.join(dest, d))]
    return os.path.join(dest, dirs[0])


def main():
    with open(os.path.join(ROOT, "versions.json")) as fh:
        versions = json.load(fh)
    only = set(sys.argv[1:])
    for v in versions:
        if only and v["label"] not in only:
            continue
        out = os.path.join(DATA, v["label"])
        if os.path.exists(os.path.join(out, "summary.json")):
            print(f"[skip] {v['label']} (already analyzed)")
            continue
        t0 = time.time()
        wdir = os.path.join(WORK, v["label"])
        shutil.rmtree(wdir, ignore_errors=True)
        tree = fetch(v["ref"], wdir)
        src = source_root(tree)
        s = em.analyze_tree(src, v["label"], out)
        shutil.rmtree(wdir, ignore_errors=True)
        print(f"[done] {v['label']:7s} files={s['n_files']:4d} classes={s['n_classes']:4d} "
              f"interfaces={s['n_interfaces']:3d} parse_fail={s['n_parse_failed']} "
              f"({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
