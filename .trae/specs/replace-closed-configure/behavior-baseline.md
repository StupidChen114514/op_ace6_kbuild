# 行为基线清单 — 闭源 `scripts/configure`（OnePlus Ace6 Kernel 构建工具）

> 本文档通过逆向 + 运行时抓取还原闭源二进制 `scripts/configure` 的实际行为，作为
> 开源等价脚本的对标基线。每一维度的结论都标注证据等级：
> - **[实测]** = 运行时抓取 / 已解密字符串原文
> - **[加密]** = 已定位 AES 密文但未解出明文（标注留存）
> - **[推断]** = 依据字符串表 + 控制流命名推断

## 0. 交付物 / 证据索引

| 文件 | 说明 |
|---|---|
| `configure` | 原始闭源二进制（UPX 4.2.4 解压前） |
| `configure.unpacked` | UPX 解压后的 Nuitka onefile 主程序（md5 `ef02085f…`） |
| `live_child.bin` | 运行时存活的自解包子进程（md5 `f8e3b575…`，含全部内嵌字符串/密文） |
| `allstrings.txt` | `live_child.bin` 提取的全部字节串（含 AES 密文） |
| `pyinstxtractor.py` | 曾尝试的 PyInstaller 解包脚本（**未使用**，与其机制无关） |
| `watcher.py` | 运行时轮询捕获完整 `configure.bin` 的脚本 |
| `config_key_and_samples.py` | AES 密钥与已解密的原文样本 |
| `restored_src/` | 基于证据重构的源码草案（`main/patcher/configs/defs/gh_hacks/utils`） |
| `sandbox/capture.log` | mock 工具抓取的网络调用记录 |
| `sandbox/kernel_workspace/` | 运行时抓取产物（gki_defconfig、config_summary.txt、下载的补丁） |

**关键技术判定**：该二进制是 **UPX(4.2.4) 压缩 → Nuitka onefile（非 PyInstaller）→ 剥离
符号**。启动时父进程解出子进程 `live_child.bin`，内嵌 Python 模块名（`main/patcher/utils/
configs/defs/gh_hacks`，及 `utils.download`），关键配置以 **AES-128-ECB + base64** 内嵌于
字节串表，密钥 `b"5YW5jaFsdWXlhbmN"`。运行时 `chdir` 到 `kernel_workspace`，最后在
`kernel_platform/common` 目录下修改内核源。

---

## 1. 参数接口（CLI）

**[实测字符串表]** 由 argparse 定义，描述见 §2 原语：

| 参数 | 类型/默认 | 说明 |
|---|---|---|
| `--ksu-variant` | choices=`{default,XXKSU,MAMBOSU,SUKISU,RESUKISU,NEXT,…}` default=`default` | 选择 KernelSU 变体 |
| `--ksu-branch` | str default=`default` | 指定 KernelSU 分支 |
| `--susfs` | `store_true` | 启用 SUSFS |
| `--with-bbg` | `store_true` | Baseband_guard 支持 |
| `--mountify` | `store_true` | Mountify 模块支持 |
| `--fengchi` | `store_true` | 启用风驰补丁 |
| `--no-ver-edit` | `store_true` | 关闭 gki_defconfig 中的版本号改写 |
| `--kpm` | `store_true` | KPM 模块支持（SukiSU only） |
| `--kpm-patch` | str(default) | 需被打 KPM 补丁的 Image 路径（SukiSU only） |
| `--multi-manager` | `store_false`(默认 True) | 关闭 Multi manager 支持（ReSukiSU only） |
| `--droidspace` | `store_true` | Droidspace-OSS 特性 |
| `--ntsync` | `store_true` | NTSync 特性 |
| `--hookless` | `store_true` | Hookless 特性（ReSukiSU only） |
| `--zram` | choices=`{DISABLE,LZ4,LZ4KD}` default=`DISABLE` | ZRAM 升级 |
| `--help` | argparse 自带 | 打印帮助 |

> 备注：`--multi-manager` 使用 `store_false` 反向语义——默认多管理器**开启**，显式传参即关闭。

**运行时开关汇总**[实测 config_summary]：闭源每次运行都输出一份 `config_summary.txt`，
逐项列出 Kernel Version / KernelSU Variant / KSU Branch / Hookless / SUSFS /
Baseband_guard / Mountify / Fengchi / KPM / Multi Manager / Droidspace-OSS /
NTSync / ZRAM Option / Version Edit 的 Enabled/Disabled。

---

## 2. 各 KSU 变体注入方式（git clone + setup.sh）

**机制模型[实测解密]**：变体 → 远端 KernelSU 仓库；configure `git clone` 该仓库后，执行
其 `kernel/setup.sh` 完成内核注入。

| 变体名 | 仓库 / 分支 | 集成方式 |
|---|---|---|
| `default`(无开关) | `backslashxx/KernelSU/master/kernel/setup.sh` | 标准 setup（[实测] capture.log 抓到该 URL） |
| XXKSU | `backslashxx/KernelSU/master/kernel/setup.sh` | 标准 setup |
| MAMBOSU | `RapliVx/KernelSU/refs/heads/master/kernel/setup.sh`（branch `master`） | 标准；SUSFS 走分支 `susfs-mambo-master` |
| SukiSU | `Sukisu-Ultra/Sukisu-Ultra/main/kernel/setup.sh` | `method=builtin`[实测解密] |
| ReSukiSU | `ReSukiSU/ReSukiSU/main/kernel/setup.sh` | 标准；SUSFS→"集成分支"路径[实测] |
| NEXT | `KernelSU-Next/KernelSU-Next/next/kernel/setup.sh`（branch `dev`） | SUSFS 走 `dev-susfs`；带 `NEXT_SPECIFIC`/`NEXT-SUSFS` 槽位 |

> `ksu_infos` 字典结构（`defs.py`）：`setup_script / branch / method(集成方式) /
> no_need_manual / manual_patches / scope / susfs_default_branch`。**method 取值 `builtin`
> 或 `manual`**，直接决定 SUSFS 是否走"集成分支"。

---

## 3. SUSFS 处理（含 RESUKISU 集成分支切换）

**SUSFS 仓库来源按内核版本分流[实测解密]**：

| 内核版本 | SUSFS 仓库 | 默认分支 |
|---|---|---|
| 6.6.89 | `https://github.com/luyanci/susfs4oki.git` | `oki-android15-6.6` |
| 6.6.118 | `https://gitlab.com/simonpunk/susfs4ksu.git` | `gki-android15-6.6` |

**三层走法判定[实测字符串表]**：
1. **集成分支**："`SUSFS support enabled and integration available for this variant.
   Using SUSFS integrated branch for setup.`" → 针对 **ReSukiSU（`susfs_intregated=manual`）
   / NEXT（`dev-susfs`）** 等提供集成分支的变体。
2. **需手动打补丁**："`SUSFS support enabled but integration requires manual patching for this
   variant. Using standard branch for setup.`" → 走 §4 手动补丁链。
3. **无集成/未启用**："`Susfs not enabled or no integration available for this variant.
   Using standard setup.`"

**获取 SUSFS**：`git clone {susfs_repo_url} -b {susfs_default_branch}`（按版本选择仓库）。

**手动集成动作**[实测]（`integrate_susfs_to_ksu` / `integrate_susfs_to_kernel`）：
- 应用 `./kernel_patches/KernelSU/10_enable_susfs_for_ksu.patch`（日志 "Integrating SUSFS into KernelSU…"，失败提示 `Failed to integrate SUSFS into KernelSU.It will cause build errors later.`）。
- 拷贝 `./kernel_patches/fs`、`./kernel_patches/include` 到内核树（"Copying SUSFS files to Kernel source tree…"）。
- 应用 `./kernel_patches/50_add_susfs_in_gki-android15-6.6.patch` → 落地为 `common/50_enable_susfs_for_kernel.patch`（"Integrating SUSFS into Kernel…"）。

**Susfs enable/disable 集**（`defs.py`，[实测解密]）：
- `SUSFS_CONFIGS` → `CONFIG_KSU_SUSFS=y`
- `NO_SUSFS_CONFIGS` → `CONFIG_KSU_SUSFS=n`
- `LEGACY_SUSFS_CONFIGS` → `CONFIG_KSU_KPROBES_HOOK=n`
- `NEXT_SPECIFIC`/`NEXT-SUSFS` → 含 `CONFIG_KSU_FULL_NAME_FORMAT=…`

**ReSukiSU+SUSFS 组合结论（本项目关注点）**：命中集成分支路径，SUSFS 通过 `susfs_intregated
= manual` 标识，在恒等分支上拉取 SUSFS 并根据内核版本选 `susfs4oki`（6.6.89）或
`susfs4ksu`（6.6.118）完成集成。

---

## 4. CVE 补丁来源

CVE / 显示修复等"总是下载"的补丁，集中来自 `luyancib-org/kernel_patches` [实测解密]：

| 补丁落盘名 | 来源 URL |
|---|---|
| `fix-CVE-2026-43499.patch` | `https://github.com/luyancib-org/kernel_patches/raw/master/other/fix-CVE-2026-43499.patch` |
| `fix_display_for_118.patch` | `https://github.com/luyancib-org/kernel_patches/raw/master/other/fix_display_for_118.patch` |

运行后这些文件名会出现在 `kernel_platform/common/` 下（[实测] sandbox 抓取到
`fix_CVE_2026_43499.patch` 与 `fix_display_for_118.patch`）；`fix_CVE_2026_43499.patch`
内容为 rtmutex/`rt_mutex_start_proxy_lock` 、`remove_waiter()` 的修复（CVE-2026-43499）。

---

## 5. defconfig 修改（config 阶段）

**写入目标**：`kernel_workspace/kernel_platform/common/arch/arm64/configs/gki_defconfig` [实测]
（追加 + `sed` 改写）。

**追加策略[实测]**：`Configs.generate_config` 依开关把 `defs.*_CONFIGS` 追加写入 defconfig：
- KSU 公共（首部）
- SUSFS：启用 → `CONFIG_KSU_SUSFS=y`；禁用 → `CONFIG_KSU_SUSFS=n`（+ LEGACY
  `CONFIG_KSU_KPROBES_HOOK=n`）
- 多管理器（ReSukiSU）、BBG、Mountify、KPM、ZRAM(LZ4KD)、Droidspace、NTSync、hookless 各自追加。

**sed 改写[实测字符串表]**：
- `sed -i 's/-4k//' <defconfig>` —— 去掉 4k page-size 内核后缀。
- `sed -i 's/CONFIG_ZRAM=m/CONFIG_ZRAM=y/' <defconfig>` —— ZRAM 由模块改为内置。

**版本号改写（`--no-ver-edit`）[实测]**：
- 默认开启版本号注入，追加形如 `CONFIG_KSU_FULL_NAME_FORMAT="%TAG_NAME%-%COMMIT_SHA%@%REPO_NAME%"`。
- `--no-ver-edit` 关闭该写入（名称 `no_ver_edit` → summary "Disabled"）。

**结束动作**：生成 `config_summary.txt`（上一工作流 `buildbot.py` 也会读取它）。

---

## 6. KPM：改写 `kernel_platform/common/arch/arm64/Makefile`

KPM 仅 SukiSU 支持 [实测字符串表 `--kpm`/`--kpm-patch` 帮助文案]：
- 通过本地 `patch_linux` 二进制对 `-kpm-patch` 传入的 **Image** 打 KPM 补丁：
  - 检查 `patch_linux` 存在且可执行（否则报 `patch_linux not found at …` /
    `patch_linux is not executable: … (run chmod +x first)`）。
  - 检查 Image 存在且文件名恰为 `Image`（`Image file name must be 'Image', got '{name}'`）。
  - 将 Image 移至当前目录后调用 `patch_linux`。
- 同时把生成的 `auto_patch_kpm.patch` 写入工作目录供后续打包；`arch/arm64/Makefile`
  由该流程改写以接入 KPM 钩子。
  > `arch/arm64/Makefile` 直接被改写的机制来自字符串表对 KPM 段的命名，
  > 完整改写内容未能逐字节还原 [推断]。

---

## 7. 其余可选功能补丁来源

[实测解密]。除 SUSFS/CVE 之外的补丁多来自 `luyancib-org/kernel_patches` 与
`cctv18/oppo_oplus_realme_sm8750`、`Goldzxcbug/Droidspaces_Kernel_patch`：

| 功能 | 来源 |
|---|---|
| ZRAM LZ4 / ZSTD / asm | `cctv18/oppo_oplus_realme_sm8750/main/zram_patch/{001-lz4,002-zstd,lz4armv8.S}` |
| ZRAM 库升级（6.6.118） | `kernel_patches/raw/master/other/lib-Update-zram-to-1.10.0-6.6.118.patch` |
| ZRAM LZ4KD | `kernel_patches/raw/master/other/lz4kd.patch` |
| 风驰 fengchi | `kernel_patches/raw/refs/heads/master/other/fengchi_oneplus_ace_6_89.patch` / `…_6_118.patch`（按内核版本选择） |
| Droidspace | `kernel_patches/raw/master/other/droidspace.patch` |
| NTSync | `Goldzxcbug/Droidspaces_Kernel_patch/.../NTsync/{ntsync_base,ntsync_compat_android15-6.6}.patch` |
| Baseband_guard | `vc-teahouse/Baseband-guard/main/setup.sh` |
| Hookless / manual hook | `kernel_patches/raw/master/manual_hook/kernel-gki.patch`、`scope-miniminzed/scope-minnimized-hooks-v1.9.patch`、`SukiSU-Ultra/SukiSU_patch/raw/main/hooks/syscall_hooks.patch` |

---

## 8. 白名单 / 黑名单（gh_hacks）

**机制[实测字符串表]**：运行时 `gh_hacks.py` 根据环境变量判定触发者是否允许执行，判定输入：
`GITHUB_REPOSITORY`（`repo_path/owner`）、`GITHUB_REPOSITORY_OWNER_ID`(缺省
`123456789`)、`GITHUB_ACTOR`、`GITHUB_ACTOR_ID`(缺省 `987654321`)；本地无这些环境时回退
`getpass.getuser()`，空则取 `"-local"`。

**白名单[实测解密]**（owner + actor 白名单）：

| 角色 | 名称 | ID |
|---|---|---|
| 仓库 owner | luyanci | 68143180 |
| 允许 actor | luyanci | 68143180 |
| 允许 actor | cycle1337 | 105600559 |
| 允许 actor | cctv18 | 85936817 |
| 允许 actor | showdo | 94498204 |

**黑名单[加密]**：字符串表存在独立的 `blacklist` 槽位（含 `actor_id`），数值为 AES 密文，
未还原；触发了即 `logger.error("Action blocked: Actor is blacklisted.")` 后 `abort`。

**触发条件（本项目核心关注）[实测]**：
- 在 **GitHub Actions** 语境（环境含 `GITHUB_REPOSITORY/GITHUB_ACTOR`）且触发者/仓主命中
  **黑名单**或**未在白名单** → 拒绝执行并退出。
- **本地**（无 `GITHUB_*` 环境，actor 回退 `-local`）→ 放行。[实测：本机可运行]
- `is_actor_whitelisted` / `is_actor_blacklisted` 两个判定函数在字符串表唯一出现，结合
  环境变量实现访问控制。

> 开源等价脚本对策：按 spec 移除一切白名单/黑名单远程控制逻辑，功能全部改为本地开关驱动。

---

## 9. 行为时序总览（含 startup 事件）

1. 父进程 UPX 解压自解出 `live_child.bin` 子进程启动 Nuitka 运行时。
2. 打印标题 "Op Ace6 Kconfigure"（pyfiglet）+ 解析 `--*` 参数。
3. `chdir(kernel_workspace)`；判定 `gh_hacks` 访问控制（见 §8）。
4. `patcher`：下载 CVE/显示补丁 → clone 变体 KernelSU → 执行 setup.sh →（若启用）
   SUSFS 集成 → KPM/KPM-patch → BBG/mountify/fengchi/droidspace/ntsync/zram。
5. `configs.generate_config`：追加 defconfig + `sed -4k` + ZRAM 改写 + 版本号注入。
6. `generate_summary`：写 `config_summary.txt`。
7. 输出 "Configuration completed."。

---

## 10. 未能还原（诚实标注）

- **黑名单 actor_id 具体明文**：AES 密文未解出 [加密]。
- `arch/arm64/Makefile` 的 KPM 精确改写内容：仅定位到 `patch_linux`+`auto_patch_kpm.patch`
  流程，补丁内文未逐字节还原 [推断]。
- 各 `*_CONFIGS` 列表完整条目：只解出部分（`CONFIG_KSU_SUSFS`、`CONFIG_KSU_KPROBES_HOOK=n`、
  `CONFIG_KSU_FULL_NAME_FORMAT`），其余保持密文 [加密]。
- **是否强直连既定 GitHub 凭据**：未在二进制中发现明文 token（未评审凭据/密钥风险仅限
  于源码），[推断]。

---

## 11. 一句话结论

闭源 `scripts/configure` 是一份 **Nuitka onefile 冻结 + AES 掩盖参数 + GitHub-actor 白/黑名单
访问控制**的 OnePlus Ace6 内核配置器；SUSFS 在 **ReSukiSU / NEXT** 上走"集成分支"路径并
**按内核版本（6.6.89→susfs4oki、6.6.118→susfs4ksu）选择仓库/分支**，CVE/可选补丁统一来自
`luyancib-org/kernel_patches` 等公开仓库。开源等价脚本应复刻参数接口、补丁顺序与来源，
而**移除远程白/黑名单控制**。