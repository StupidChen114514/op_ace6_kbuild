#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CI 门禁：校验 SUSFS / ZRAM-LZ4 补丁对目标内核树的可应用性 + 关键补丁 URL 可用性。

背景（2026-09-15 实测矩阵，见仓库 notes/ 诊断报告）：
  - 6.6.118（OnePlusOSS android_kernel_common_oneplus_sm8750 @ oneplus/sm8750_b_16.0.0_ace_6）
      simonpunk/susfs4ksu 的 50_ 补丁可 100% 干净应用（-F0，0 拒绝）。
  - 6.6.89 （同仓库 @ 36e8d60d...，固定 SHA）
      50_ 补丁在 -F2 下应用：唯一拒绝 = fs/proc/base.c；
      随后 scripts/patches/89-susfs-fixup.patch（-F0）完成覆盖（-F2 下 fs/exec.c 的
      include hunk 会带模糊应用，属预期）。

若上游漂移导致断言失败 → 本门禁红灯（意味着需要更新 pins.env 或重新制作 fixup）。
用法：python3 scripts/tools/verify_susfs_patches.py
"""

import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root
PINS_FILE = os.path.join(ROOT, "scripts", "pins.env")
PATCHES_DIR = os.path.join(ROOT, "scripts", "patches")
UA = {"User-Agent": "verify-susfs-patches/1.0"}

ONE_PLUS_REPO = "OnePlusOSS/android_kernel_common_oneplus_sm8750"

TARGETS = [
    {
        "name": "6.6.118",
        "ref": "oneplus/sm8750_b_16.0.0_ace_6",
        "fuzz": 0,
        "expected_rejects": set(),
        "fixup": None,
    },
    {
        "name": "6.6.89",
        "ref": "36e8d60d4d1c97c08117cb0e733186515357cff3",
        "fuzz": 2,
        "expected_rejects": {"fs/proc/base.c"},
        "fixup": "89-susfs-fixup.patch",
    },
]

ZRAM_TARGETS = [
    {
        "name": "zram-6.6.118",
        "ref": "oneplus/sm8750_b_16.0.0_ace_6",
        "expected_rejects": set(),
        "fixup": None,
    },
    {
        "name": "zram-6.6.89",
        "ref": "36e8d60d4d1c97c08117cb0e733186515357cff3",
        "expected_rejects": {"fs/f2fs/compress.c", "lib/lz4/lz4hc_compress.c"},
        "fixup": "89-zram-lz4-fixup.patch",
    },
]

DEFAULT_PINS = {
    "KSU_REPO": "ReSukiSU/ReSukiSU",
    "KSU_REF": "",
    "SUSFS_HOST": "gitlab.com",
    "SUSFS_REPO": "simonpunk/susfs4ksu",
    "SUSFS_BRANCH": "gki-android15-6.6",
    "SUSFS_SHA": "",
    "KERNEL_PATCHES_REPO": "luyancib-org/kernel_patches",
    "KERNEL_PATCHES_SHA": "",
    "KPATCH_REPO": "KernelSU-Next/KPatch-Next",
    "KPATCH_TAG": "0.13.5-2",
    "NTSC_REPO": "Goldzxcbug/Droidspaces_Kernel_patch",
    "NTSC_SHA": "",
    "SUKI_HOOKS_REPO": "SukiSU-Ultra/SukiSU_patch",
}


def log(msg):
    print(msg, flush=True)


def load_pins():
    pins = dict(DEFAULT_PINS)
    if os.path.isfile(PINS_FILE):
        for line in open(PINS_FILE, encoding="utf-8"):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            pins[k.strip()] = v.strip()
    for k in list(pins):
        if os.environ.get(k):
            pins[k] = os.environ[k]
    return pins


def raw_url(host, repo, ref, path):
    if host == "gitlab.com":
        return f"https://gitlab.com/{repo}/-/raw/{ref}/{path}"
    return f"https://raw.githubusercontent.com/{repo}/{ref}/{path}"


def http_get(url, timeout=60, method="GET"):
    """单次网络抖动（SSL EOF / 超时）不应红门禁：失败后重试一次。"""
    last = None
    for attempt in (1, 2):
        try:
            req = urllib.request.Request(url, headers=UA, method=method)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read()
        except Exception as e:  # noqa: BLE001
            last = e
            if attempt == 1:
                time.sleep(3)
    raise last


def fetch_to(url, dest):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    status, data = http_get(url, timeout=120)
    with open(dest, "wb") as f:
        f.write(data)
    return status


def check_urls(pins):
    """关键补丁 URL 可用性（防 404/改名）。返回失败列表。"""
    kp_ref = pins["KERNEL_PATCHES_SHA"] or "master"
    kp_repo = pins["KERNEL_PATCHES_REPO"]
    nt_ref = pins["NTSC_SHA"] or "main"
    checks = [
        raw_url("github.com", kp_repo, kp_ref, "other/fix-CVE-2026-43499.patch"),
        raw_url("github.com", kp_repo, kp_ref, "other/fix_display_for_118.patch"),
        raw_url("github.com", kp_repo, kp_ref, "other/fengchi_oneplus_ace_6_89.patch"),
        raw_url("github.com", kp_repo, kp_ref, "other/fengchi_oneplus_ace_6_118.patch"),
        raw_url("github.com", kp_repo, kp_ref, "other/droidspace.patch"),
        raw_url("github.com", kp_repo, kp_ref, "other/lz4kd.patch"),
        raw_url("github.com", kp_repo, kp_ref, "other/lib-Update-zram-to-1.10.0-6.6.118.patch"),
        raw_url("github.com", kp_repo, kp_ref, "manual_hook/kernel-gki.patch"),
        raw_url("github.com", kp_repo, kp_ref, "scope-miniminzed/scope-minnimized-hooks-v1.9.patch"),
        raw_url("github.com", pins["NTSC_REPO"], nt_ref, "NTsync/ntsync_base.patch"),
        raw_url("github.com", pins["NTSC_REPO"], nt_ref, "NTsync/ntsync_compat_android15-6.6.patch"),
        f"https://github.com/{pins['KPATCH_REPO']}/releases/download/{pins['KPATCH_TAG']}/kptools-linux",
        f"https://github.com/{pins['KPATCH_REPO']}/releases/download/{pins['KPATCH_TAG']}/kpimg-linux",
        raw_url("github.com", pins["SUKI_HOOKS_REPO"], "main", "hooks/syscall_hooks.patch"),
    ]
    fails = []
    for u in checks:
        try:
            status, _ = http_get(u, timeout=45)
            log(f"  [URL] {status} {u}")
        except Exception as e:  # noqa: BLE001
            log(f"  [URL] FAIL {u} :: {e}")
            fails.append(u)
    return fails


def fetch_susfs(pins, workdir):
    host, repo = pins["SUSFS_HOST"], pins["SUSFS_REPO"]
    ref = pins["SUSFS_SHA"] or pins["SUSFS_BRANCH"]
    dest = os.path.join(workdir, "SUSFS")
    if host == "gitlab.com":
        url = f"https://gitlab.com/{repo}/-/archive/{ref}/source.tar.gz"
    else:
        url = f"https://codeload.github.com/{repo}/tar.gz/{ref}"
    tmp = dest + ".tgz"
    fetch_to(url, tmp)
    with tarfile.open(tmp, "r:gz") as t:
        members = t.getmembers()
        top = members[0].name.split("/")[0] if members else None
        for m in members:
            name = m.name.replace("\\", "/")
            if name.startswith("/") or ".." in name.split("/"):
                raise RuntimeError(f"unsafe tar member: {m.name}")
            if name == top:
                continue
            if name.startswith(top + "/"):
                m.name = name[len(top) + 1:]
                t.extract(m, dest)
    return dest


def patch_file_list(patch_path):
    files = []
    for line in open(patch_path, encoding="utf-8", errors="replace"):
        m = re.match(r"^diff --git a/(\S+) b/(\S+)", line)
        if m:
            files.append(m.group(2))
    return files


def patch_file_list_ex(patch_path):
    """[(b-side path, is_new_file)]：new 文件由补丁创建，不应从目标树抓取。"""
    txt = open(patch_path, encoding="utf-8", errors="replace").read()
    out = []
    for blk in re.split(r"(?m)^(?=diff --git )", txt):
        m = re.match(r"diff --git a/(\S+) b/(\S+)", blk)
        if not m:
            continue
        is_new = ("new file mode" in blk) or ("\n--- /dev/null" in blk)
        out.append((m.group(2), is_new))
    return out


def run(cmd, cwd=None):
    p = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return p.returncode, p.stdout


def find_rejects(tree):
    out = []
    for root, _d, files in os.walk(tree):
        for f in files:
            if f.endswith(".rej"):
                out.append(os.path.relpath(os.path.join(root, f), tree).replace("\\", "/"))
    return sorted(out)


def check_ksu_side_susfs(pins):
    """阶段 D：KSU 侧内置 SUSFS 证据固化（防"跳过 10_ 补丁"的依据过时）。

    RESUKISU/RKSU/SUKISU 走"内置 SUSFS"路径（不应用 KernelSU 侧 10_ 补丁）。
    本检查直接验证钉死版本（KSU_REPO@KSU_REF）的 kernel/Kconfig 含 `config KSU_SUSFS`；
    若上游未来移除该特性（或升级 KSU_REF 后消失）→ 门禁红灯（需要改走 manual 路径或回退版本）。
    """
    repo = pins["KSU_REPO"]
    ref = pins["KSU_REF"] or "main"
    url = raw_url("github.com", repo, ref, "kernel/Kconfig")
    fails = []
    try:
        status, data = http_get(url, timeout=60)
        if status != 200:
            fails.append(f"KSU 侧检查: {url} -> HTTP {status}")
        elif b"config KSU_SUSFS" not in data:
            fails.append(f"KSU 侧检查: {repo}@{ref} 的 kernel/Kconfig 无 'config KSU_SUSFS'"
                         f"（内置 SUSFS 支持缺失，跳过 10_ 补丁的依据已失效）")
        else:
            log(f"  [KSU] {repo}@{ref}: kernel/Kconfig 含 config KSU_SUSFS ✓")
    except Exception as e:  # noqa: BLE001
        fails.append(f"KSU 侧检查失败: {e}")
    return fails


def verify_zram_lz4(t, pins, workdir):
    log(f"\n==== zram-lz4 target {t['name']} ({t['ref']}) ====")
    kp_ref = pins["KERNEL_PATCHES_SHA"] or "master"
    url = raw_url("github.com", pins["KERNEL_PATCHES_REPO"], kp_ref,
                  "other/lib-Update-zram-to-1.10.0-6.6.118.patch")
    patch_path = os.path.join(workdir, "lib-update-zram.patch")
    fetch_to(url, patch_path)

    tree = os.path.join(workdir, "tree")
    missing = []
    for f, is_new in patch_file_list_ex(patch_path):
        if is_new:
            continue
        try:
            fetch_to(raw_url("github.com", ONE_PLUS_REPO, t["ref"], f), os.path.join(tree, f))
        except Exception:  # noqa: BLE001
            missing.append(f)
    if missing:
        return [f"{t['name']}: kernel tree files missing: {missing}"]

    fails = []
    rc, out = run(["patch", "-p1", "--batch", "--fuzz=0", "--forward", "-i", patch_path], cwd=tree)
    rejects = sorted(r[: -len(".rej")] for r in find_rejects(tree))
    if set(rejects) != t["expected_rejects"]:
        fails.append(f"{t['name']}: lib-update rejects={rejects} 期望={sorted(t['expected_rejects'])}")
        log("  patch tail:\n    " + "\n    ".join(out.strip().splitlines()[-8:]))
    else:
        log(f"  lib-update apply OK (rc={rc}, rejects={rejects or 'none'})")

    if rejects:
        stash = os.path.join(workdir, "rejects")
        os.makedirs(stash, exist_ok=True)
        for r in find_rejects(tree):
            shutil.move(os.path.join(tree, r), os.path.join(stash, r.replace("/", "__")))

    if t["fixup"]:
        fx = os.path.join(PATCHES_DIR, t["fixup"])
        if not os.path.isfile(fx):
            fails.append(f"{t['name']}: fixup missing: {fx}")
        else:
            rc2, out2 = run(["patch", "-p1", "--batch", "--fuzz=0", "--forward", "-i", fx], cwd=tree)
            new_rejects = find_rejects(tree)
            if rc2 != 0 or new_rejects:
                fails.append(f"{t['name']}: fixup 应用失败 rc={rc2} rejects={new_rejects}")
                log("  fixup tail:\n    " + "\n    ".join(out2.strip().splitlines()[-8:]))
            else:
                log("  fixup apply OK (rc=0)")

    # 89 差异：旧 lz4hc_compress.c 由新 lz4hc.c 取代（删除块内容不符 → 显式移除）
    hc = os.path.join(tree, "lib/lz4/lz4hc_compress.c")
    if os.path.isfile(hc):
        os.remove(hc)

    for rel, want in (
        ("lib/lz4/lz4.c", True), ("lib/lz4/lz4.h", True), ("lib/lz4/lz4hc.c", True),
        ("lib/lz4/lz4hc.h", True), ("lib/lz4/lz4armv8/lz4accel.c", True),
        ("lib/lz4/lz4armv8/lz4accel.h", True), ("lib/lz4/lz4armv8/lz4armv8.S", True),
        ("lib/lz4/lz4_compress.c", False), ("lib/lz4/lz4_decompress.c", False),
        ("lib/lz4/lz4defs.h", False), ("lib/lz4/lz4hc_compress.c", False),
    ):
        if os.path.exists(os.path.join(tree, rel)) != want:
            fails.append(f"{t['name']}: 断言失败 {rel} exists != {want}")
    ccp = os.path.join(tree, "fs/f2fs/compress.c")
    if "LZ4_arm64_decompress_safe" not in open(ccp, encoding="utf-8", errors="replace").read():
        fails.append(f"{t['name']}: fs/f2fs/compress.c 缺少 LZ4_arm64_decompress_safe")
    if not fails:
        log(f"  PASS: {t['name']}")
    return fails


def verify_target(t, pins, workdir):
    log(f"\n==== target {t['name']} ({t['ref']}) ====")
    susfs = fetch_susfs(pins, workdir)
    kp = os.path.join(susfs, "kernel_patches")
    cands = sorted(f for f in os.listdir(kp) if f.startswith("50_") and f.endswith(".patch"))
    if not cands:
        return [f"{t['name']}: 50_*.patch not found"]
    patch50 = os.path.join(kp, cands[0])

    tree = os.path.join(workdir, "tree")
    missing = []
    for f, is_new in patch_file_list_ex(patch50):
        if is_new:
            continue
        url = raw_url("github.com", ONE_PLUS_REPO, t["ref"], f)
        try:
            fetch_to(url, os.path.join(tree, f))
        except Exception:  # noqa: BLE001
            missing.append(f)
    if missing:
        return [f"{t['name']}: kernel tree files missing: {missing}"]

    fails = []
    rc, out = run(["patch", "-p1", "--batch", f"--fuzz={t['fuzz']}", "--forward", "-i", patch50], cwd=tree)
    rejects = find_rejects(tree)
    rejects_stripped = sorted(r[: -len(".rej")] for r in rejects)
    if set(rejects_stripped) != t["expected_rejects"]:
        fails.append(f"{t['name']}: 50_ rejects={rejects_stripped} 期望={sorted(t['expected_rejects'])}")
        log("  patch tail:\n    " + "\n    ".join(out.strip().splitlines()[-8:]))
    else:
        log(f"  50_ apply OK (rc={rc}, rejects={rejects_stripped or 'none'})")

    # 移走 .rej 供后续检查
    if rejects:
        stash = os.path.join(workdir, "rejects")
        os.makedirs(stash, exist_ok=True)
        for r in rejects:
            shutil.move(os.path.join(tree, r), os.path.join(stash, r.replace("/", "__")))

    if t["fixup"]:
        fx = os.path.join(PATCHES_DIR, t["fixup"])
        if not os.path.isfile(fx):
            fails.append(f"{t['name']}: fixup missing: {fx}")
        else:
            rc2, out2 = run(["patch", "-p1", "--batch", "--fuzz=0", "--forward", "-i", fx], cwd=tree)
            new_rejects = find_rejects(tree)
            if rc2 != 0 or new_rejects:
                fails.append(f"{t['name']}: fixup 应用失败 rc={rc2} rejects={new_rejects}")
                log("  fixup tail:\n    " + "\n    ".join(out2.strip().splitlines()[-8:]))
            else:
                log("  fixup apply OK (rc=0)")

    # 终态断言
    for rel, needle in (
        ("fs/exec.c", "#include <linux/susfs_def.h>"),
        ("fs/proc/base.c", "#include <linux/susfs_def.h>"),
        ("fs/exec.c", "ksu_handle_execveat"),
        ("kernel/sys.c", "ksu_handle_setresuid"),
        ("fs/Makefile", "susfs"),
    ):
        p = os.path.join(tree, rel)
        if needle not in open(p, encoding="utf-8", errors="replace").read():
            fails.append(f"{t['name']}: 断言失败 {rel} 缺少 {needle}")
    if not fails:
        log(f"  PASS: {t['name']}")
    return fails


def main():
    pins = load_pins()
    log("== 阶段 A：关键补丁 URL 可用性 ==")
    url_fails = check_urls(pins)

    log("\n== 阶段 B：SUSFS 补丁 × 内核树 矩阵 ==")
    fails = list(url_fails)
    with tempfile.TemporaryDirectory(prefix="verify_susfs_") as td:
        for t in TARGETS:
            wd = os.path.join(td, t["name"].replace(".", "_"))
            os.makedirs(wd, exist_ok=True)
            try:
                fails += verify_target(t, pins, wd)
            except Exception as e:  # noqa: BLE001
                fails.append(f"{t['name']}: 校验异常: {e}")

    log("\n== 阶段 C：ZRAM-LZ4 补丁 × 内核树 矩阵 ==")
    with tempfile.TemporaryDirectory(prefix="verify_zram_") as td:
        for t in ZRAM_TARGETS:
            wd = os.path.join(td, t["name"].replace(".", "_"))
            os.makedirs(wd, exist_ok=True)
            try:
                fails += verify_zram_lz4(t, pins, wd)
            except Exception as e:  # noqa: BLE001
                fails.append(f"{t['name']}: 校验异常: {e}")

    log("\n== 阶段 D：KSU 侧内置 SUSFS（钉死版本证据固化）==")
    fails += check_ksu_side_susfs(pins)

    log("\n================ 结果 ================")
    if fails:
        log(f"FAIL: {len(fails)} 项问题：")
        for f in fails:
            log(f"  - {f}")
        sys.exit(1)
    log("ALL PATCH CHECKS PASSED")


if __name__ == "__main__":
    main()
