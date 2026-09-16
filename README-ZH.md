# op_ace6_kbuild

Oneplus ACE6 内核构建脚本，可以集成KernelSU及其变体 也包括SUSFS的集成

## 仓库简介

本仓库提供一套基于 GitHub Actions 的自动化构建脚本套件，用于编译一加 ACE6 内核，内置 KernelSU 与 SUSFS 功能集成支持。

仓库包含 GitHub Actions 工作流文件及开源构建辅助脚本，不包含任何 OEM 内核源码 —— 内核源码需从 OEM 官方渠道另行获取。

开源脚本 `scripts/configure`（Python）作为构建阶段辅助程序，具备以下核心能力：

- 解析工作流传入的同一套命令行参数（`--ksu-variant`、`--ksu-branch`、`--susfs`、`--zram LZ4|LZ4KD`、`--kpm`、`--mountify`、`--ntsync`、`--fengchi`、`--droidspace`、`--with-bbg`、`--hookless`、`--multi-manager`、`--no-ver-edit`），安装所选 KernelSU 变体、按需集成 SUSFS（含 ReSukiSU/NEXT 的"集成分支"路径）、应用可选功能补丁，并向 `gki_defconfig` 追加 CONFIG。
- 脚本**不含任何白名单/黑名单远程控制逻辑**，所有功能均由本地开关驱动，完全可审计。
- KPM 采用 **KPatch-Next 后置注入**（release tag 由 `pins.env` 钉死）：工作流在编译完成后对 Image 打补丁，全部 KSU 变体可用；产物名以 `-kpm` 后缀区分。
- ZRAM LZ4 采用与上游闭源同源的 `lib-Update-zram-to-1.10.0-6.6.118.patch` 单补丁方案（6.6.118 零拒绝；6.6.89 由 `scripts/patches/89-zram-lz4-fixup.patch` 收敛树差异）。
- 通过 `scripts/pins.env` 固定上游版本（SHA，可用环境变量覆盖），每次构建输出 `build_manifest.txt`（记录实际解析到的来源与每个补丁的应用结果）。
- **关键步骤硬失败**：SUSFS / KernelSU / BBG / ZRAM LZ4 集成任一步失败时 configure 立即以非零退出——不再出现“构建绿了但功能静默缺失”。
- 两个内核世代（6.6.89 / 6.6.118）的补丁可应用性由 `verify patches` CI 工作流持续校验。

## 使用方法 

1. Fork 本仓库

2. 启用Action ，并在build custom工作流中根据需求调整相关参数

3. 坐等放宽，等待构建完成

4. 从 Actions 制品中下载编译完成的内核镜像，并刷入，大功告成

## 许可证声明

|组件|许可证|详情|
|--|--|--|
|GitHub Actions 工作流|MIT 许可证|详见根目录 LICENSE 文件|
|开源辅助脚本 (`scripts/configure`)|MIT 许可证|详见根目录 LICENSE 文件|
|OEM 内核源码|GPLv2 许可证|遵守 OEM 内核的原始许可条款 |

## 重要说明

1. `scripts/configure` 为独立的构建阶段辅助工具，仅在构建过程中开启特定功能时修改内核构建配置文件，不参与内核编译链接，也不会嵌入最终的内核镜像。

2. `scripts/configure` 的修改行为不会影响 OEM 内核源码的 GPLv2 许可属性。

3. 分发本仓库时，必须保留原始版权声明与许可证文本；分发编译后的内核包时，仅需遵守 OEM 内核的 GPLv2 条款，无需附带本仓库的许可信息。

4. `scripts/configure` 为开源构建辅助脚本，不含任何白名单/黑名单远程控制逻辑。
