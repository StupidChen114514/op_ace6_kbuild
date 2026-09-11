# Tasks

> 顺序：先"反编译抓行为基线"，再接"自写等价脚本"，最后"工作流替换 + 验证"。

- [x] Task 1: 反编译闭源 configure，产出行为基线清单
  - [x] 1.1 定位二进制结构（判定为 UPX→Nuitka onefile，非 PyInstaller），抽出运行时子进程与字符串表
  - [x] 1.2 还原 `main`/`patcher`/`configs`/`defs`/`gh_hacks`/`utils` 行为要点
  - [x] 1.3 产出"行为基线清单"（`behavior-baseline.md`：参数接口、KSU 变体来源、SUSFS 分版本/集成分支、CVE 来源、defconfig/版本改写、各功能翻表点、白名单/黑名单机制）
  - [x] 1.4 校验：运行时用 mock git/curl 抓取真实补丁 URL 与落盘动作，与清单一致

- [x] Task 2: 编写开源等价 configure 脚本（核心主干）
  - [x] 2.1 解析与工作流一致的参数接口（`--ksu-variant/--ksu-branch/--susfs/--zram/--kpm/--kpm-patch/--mountify/--ntsync/--fengchi/--droidspace/--with-bbg/--hookless/--no-ver-edit/--multi-manager`）
  - [x] 2.2 实现 KSU 变体注入（KSU/RKSU/NEXT/SUKISU/RESUKISU/MAMBOSU/XXKSU）与分支选择
  - [x] 2.3 实现 SUSFS：按内核版本选择 susfs4oki/susfs4ksu，RESUKISU/NEXT 走"集成分支"路径
  - [x] 2.4 实现 KPM：写入 `arch/arm64/Makefile` 并配置 CONFIG（SukiSU only）
  - [x] 2.5 实现 ZRAM(LZ4/LZ4KD)：改写 gki_defconfig 相关 CONFIG
  - [x] 2.6 实现 `--no-ver-edit` 与版本号改写（CONFIG_KSU_FULL_NAME_FORMAT）
  - [x] 2.7 实现 mountify/ntsync/fengchi/droidspace/bbg/hookless/multi-manager 开关（按公开源/自写 patch）
  - [x] 2.8 校验：脚本 `--help` 正常、各参数可解析、可选功能配置项正确写入

- [x] Task 3: 工作流集成与一键替换
  - [x] 3.1 用等价脚本替换 `scripts/configure`（调用接口与文件名不变，`./configure $ARGS` 直接命中新脚本）
  - [x] 3.2 移除对闭源 `scripts/configure` 的依赖（同步更新 README.md/README-ZH.md 说明与许可证表；脚本改 MIT）
  - [x] 3.3 校验：build-custom.yml 结构不变，其余步骤（sync/build/pack/upload）逻辑未受影响

- [x] Task 4: 端到端验证
  - [x] 4.1 最小内核树 + 等价脚本跑通"纯 stock 无功能"路径（`--help` + 默认）
  - [x] 4.2 分别启用 SUSFS、KPM、ZRAM(LZ4)、--no-ver-edit、--multi-manager 组合，跑通 configure → 改 defconfig
  - [x] 4.3 记录关键验证结果：各开关正确写入 gki_defconfig 并生成 config_summary.txt

# Task Dependencies
- Task 2 依赖 Task 1（行为基线性决定等价脚本的补丁顺序/交互，尤其 SUSFS+RESUKISU）。
- Task 3 依赖 Task 2（先有可用等价脚本再替换工作流调用）。
- Task 4 依赖 Task 2、Task 3；可与 Task 1 产生的基线做交叉核对。