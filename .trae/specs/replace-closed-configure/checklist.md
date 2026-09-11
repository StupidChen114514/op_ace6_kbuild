# Checklist

## 行为基线
- [x] 已生成闭源 configure 的反编译"行为基线清单"（`behavior-baseline.md`，含 KSU 变体注入、SUSFS 集成分支条件、CVE 补丁来源、defconfig/版本改写、各可选功能翻表点）
- [x] 行为基线清单与运行时实际行为核对一致（配合运行时抓取 + AES 解密双源验证）

## 等价脚本
- [x] 等价 configure 参数接口与工作流一致，`--help` 正常
- [x] SUSFS（含 RESUKISU 集成 SUSFS 处理）已实现
- [x] KPM 已实现
- [x] ZRAM(LZ4/LZ4KD) 已实现
- [x] 其余可选功能（mountify/ntsync/fengchi/droidspace/bbg/hookless/multi-manager/--no-ver-edit）已实现
- [x] 等价脚本不包含任何白名单/黑名单远程控制逻辑

## 工作流集成
- [x] build-custom.yml 已改用等价脚本，其余步骤（sync/build/pack/upload）不受影响
- [x] 已移除对闭源 `scripts/configure` 的依赖

## 端到端验证
- [x] 纯 stock（无功能）路径可跑通并产出配置（`--help` + 默认路径验证）
- [x] SUSFS / KPM / ZRAM(LZ4) 及组合路径可跑通并产出配置（最小内核树 + 等价脚本验证）
- [x] 端到端结果与功能开关预期一致（gki_defconfig 写入项 + config_summary.txt 逐项核对）