# 用开源等价脚本替代闭源 configure Spec

## Why

本仓库的 `scripts/configure` 是一个逻辑完全隐藏的闭源二进制（UPX 压缩 → 剥离符号 → 内部 Python
字节码再压缩），构建期间会联网下载补丁并 git clone 第三方仓库，且 README 声明内置白名单/黑名单远程控制。
用户选择 build-custom 工作流并启用 SUSFS 时必然失败（SUSFS + RESUKISU 会走"集成分支"路径）。目标是
用可审计、可控、可维护的开源等价脚本替代该闭源二进制，完整复刻其全部可选功能，并不依赖任何远程访问控制。

## What Changes

- 反编译闭源 `scripts/configure`（已确认：UPX 4.22 打包、废弃了 section、运行时解到 `/tmp/onefile_*`，
  含 `main.py` / `patcher.py` / `utils.py` / `utils.download`），提取其真实的补丁应用顺序与行为清单，
  作为"行为基线"。
- 基于公开源（KernelSU/ReSukiSU/SukiSU/Risu、simonpunk/susfs4ksu、kernel_patches、内核自带 CONFIG）
  自写一份等价 `configure` 脚本，参数接口与现有工作流保持一致（`--ksu-variant`、`--ksu-branch`、
  `--susfs`、`--zram LZ4/LZ4KD`、`--kpm`/`--kpm-patch`、`--mountify`、`--ntsync`、`--fengchi`、
  `--droidspace`、`--with-bbg`、`--hookless`、`--no-ver-edit`、`--multi-manager`）。
- 保留现有 `.github/workflows/build-custom.yml` 的整体结构，仅把 `./configure $ARGS` 替换为等价脚本调用。
- **BREAKING**：移除闭源 `scripts/configure` 及其依赖；自写脚本不再包含任何白名单/黑名单远程控制逻辑。
- 验证：用同一套 `make ... gki_defconfig all` 命令，能在启用 SUSFS + RESUKISU + ZRAM(LZ4) 等组合下
  正常产出 `Image`。

## Impact

- Affected specs：新增能力"本地开源自动构建"。
- Affected code：
  - 移除：`scripts/configure`（闭源二进制，不提交）
  - 新增/修改：本地等价 `configure` 脚本（bash 或 Python）
  - 修改：`.github/workflows/build-custom.yml` 中 Run configure 步骤的调用
  - 参考用于对齐行为：闭源二进制运行时 `/tmp/onefile_*` 中还原出的 `patcher.py` 行为清单
- 对外部依赖的影响：SUSFS/KSU 变体来源仍是公开 GitHub 仓库；新增对 `simonpunk/susfs4ksu`、
  `luyancib-org/kernel_patches`（或等价公开补丁集）的依赖，均需用户已知情。

## ADDED Requirements

### Requirement: 行为基线反编译清单

系统 SHALL 通过反编译闭源 `scripts/configure` 生成一份"实际补丁应用顺序与功能行为清单"。

#### Scenario: 成功产出行为清单
- **WHEN** 运行规格中的反编译步骤（定位自定义 PyInstaller cookie → 解开 PYZ → 还原 `patcher.py`/`main.py`）
- **THEN** 得到包含 KSU 变体注入方式、SUSFS 集成分支切换条件、CVE 补丁来源、defconfig/版本改写动作的清单

### Requirement: 开源等价 configure 脚本

系统 SHALL 提供一份不依赖闭源二进制的 `configure` 脚本，接口与现有工作流参数一致。

#### Scenario: 参数接口对齐
- **WHEN** 以 `--ksu-variant RESUKISU --ksu-branch default --susfs --zram LZ4` 等组合调用等价脚本
- **THEN** 等价脚本逐一应用对应补丁/配置，且不依赖任何白名单或黑名单远程控制

### Requirement: 各可选功能逐一复刻

系统 SHALL 支持以下可选功能并可通过开关启用：SUSFS、KPM、ZRAM(LZ4/LZ4KD)、Mountify、NTSync、
风驰(fengchi)、Droidspace-OSS、BBG、Hookless、multi-manager、不编辑内核版本(--no-ver-edit)。

#### Scenario: 组合启用 SUSFS + KPM + ZRAM
- **WHEN** 用户启用 SUSFS、KPM 与 ZRAM(LZ4)
- **THEN** 等价脚本正确应用三者，且后续 `make gki_defconfig all` 成功产出 Image

### Requirement: 工作流集成

系统 SHALL 在 `.github/workflows/build-custom.yml` 中改用等价脚本，保持其余步骤（sync、build、打包、上传）不变。

#### Scenario: 替换调用后全流程可跑
- **WHEN** 触发 build-custom 工作流
- **THEN** 全流程通过，且不依赖闭源 `scripts/configure`

## MODIFIED Requirements

（无既有 spec 被修改。）

## REMOVED Requirements

### Requirement: 闭源 configure 及其远程访问控制
**Reason**：它是黑盒，含隐藏逻辑与白名单/黑名单远程控制，导致 SUSFS 等受限功能不可预测地失败，且不可审计。
**Migration**：以其开源等价脚本替换；如需 SUSFS 等补丁行为，从公开 susfs4ksu / kernel_patches 获取，不再经由远程控制的闭源二进制。