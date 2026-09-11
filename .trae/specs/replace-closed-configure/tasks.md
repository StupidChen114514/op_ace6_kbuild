# Tasks

> 顺序：先"反编译抓行为基线"，再接"自写等价脚本"，最后"工作流替换 + 验证"。

- [ ] Task 1: 反编译闭源 configure，产出行为基线清单
  - [ ] 1.1 定位自定义 PyInstaller cookie，解开 PYZ 归档（必要时绕过 upx/pyinstxtractor 兼容问题）
  - [ ] 1.2 还原 `patcher.py` / `main.py` / `utils.py` / `utils.download`，提取真实行为
  - [ ] 1.3 整理输出"行为基线清单"：各参数→实际动作（KSU 变体注入、SUSFS 集成分支切换条件、CVE 补丁来源、defconfig/版本改写、各可选功能翻表点）
  - [ ] 1.4 校验：用运行时日志/最小内核树跑一次闭源 configure，核对清单与实际行为一致

- [ ] Task 2: 编写开源等价 configure 脚本（核心主干）
  - [ ] 2.1 解析与工作流一致的参数接口（`--ksu-variant/--ksu-branch/--susfs/--zram/--kpm/--kpm-patch/--mountify/--ntsync/--fengchi/--droidspace/--with-bbg/--hookless/--no-ver-edit/--multi-manager`）
  - [ ] 2.2 实现 KSU 变体注入（KSU/RKSU/NEXT/SUKISU/RESUKISU/MAMBOSU/XXKSU）与分支选择
  - [ ] 2.3 实现 SUSFS：按内核版本选择 susfs4ksu/kernel_patches 对应分支，clone 并应用补丁；对 RESUKISU 采用"集成 SUSFS"处理（对齐行为基线）
  - [ ] 2.4 实现 KPM：写入 `arch/arm64/Makefile` 并配置所需 CONFIG（SukiSU only）
  - [ ] 2.5 实现 ZRAM(LZ4/LZ4KD)：改写 gki_defconfig 相关 CONFIG
  - [ ] 2.6 实现 `--no-ver-edit` 与版本号改写（对照现有 workflow 的 setlocalversion 逻辑）
  - [ ] 2.7 实现 mountify/ntsync/fengchi/droidspace/bbg/hookless/multi-manager 开关（按公开源/自写 patch）
  - [ ] 2.8 校验：脚本 `--help` 正常、各参数可解析、可选功能配置项正确写入

- [ ] Task 3: 工作流集成与一键替换
  - [ ] 3.1 在 `.github/workflows/build-custom.yml` 中将 `./configure $ARGS` 替换为等价脚本调用
  - [ ] 3.2 移除对闭源 `scripts/configure` 的依赖（同步说明 README/许可证）
  - [ ] 3.3 校验：yaml 结构不变，其余步骤（sync/build/pack/upload）逻辑未受影响

- [ ] Task 4: 端到端验证
  - [ ] 4.1 用最小内核树 + 等价脚本跑通"纯 stock 无功能"路径
  - [ ] 4.2 分别启用 SUSFS、KPM、ZRAM(LZ4) 及组合，跑通 configure → 改配置 → make 步骤
  - [ ] 4.3 记录关键验证结果，确认产出 Image 并符合各功能开关预期

# Task Dependencies
- Task 2 依赖 Task 1（行为基线性决定等价脚本的补丁顺序/交互，尤其 SUSFS+RESUKISU）。
- Task 3 依赖 Task 2（先有可用等价脚本再替换工作流调用）。
- Task 4 依赖 Task 2、Task 3；可与 Task 1 产生的基线做交叉核对。