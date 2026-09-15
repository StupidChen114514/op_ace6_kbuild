<div align="center">
  
# op_ace6_kbuild

English|[简体中文](./README-ZH.md)

Oneplus ACE6 kernel builder, can integrate KernelSU or its various and SUSFS.

</div>

## Overview

This repository provides a GitHub Actions-based automated build script suite for compiling the OnePlus ACE6 kernel, with built-in support for integrating KernelSU or ots various and SUSFS features.

It includes GitHub Actions workflow files and an open-source build helper, without any OEM kernel source code — the kernel source code must be obtained separately from official OEM channels.

The open-source tool `scripts/configure` (Python) acts as a build-time helper:

- It parses the same CLI arguments the workflow passes (`--ksu-variant`, `--ksu-branch`, `--susfs`, `--zram LZ4|LZ4KD`, `--kpm`, `--mountify`, `--ntsync`, `--fengchi`, `--droidspace`, `--with-bbg`, `--hookless`, `--multi-manager`, `--no-ver-edit`), installing the selected KernelSU variant, integrating SUSFS when enabled (including the ReSukiSU/NEXT "integrated branch" path), applying optional feature patches, and appending CONFIG lines to `gki_defconfig`.
- It contains **no whitelist/blacklist remote-control logic**. All features are driven purely by local CLI switches, and the script is fully auditable.
- Version pinning via `scripts/pins.env` (upstream SHAs, env-overridable) and a per-build `build_manifest.txt` recording every resolved source and patch result.
- **Strict failure semantics**: if a critical integration step (SUSFS / KernelSU / BBG) fails, the configure step exits non-zero immediately instead of failing minutes later inside the kernel build.
- Patch applicability for both kernel generations (6.6.89 / 6.6.118) is continuously checked by the `verify patches` CI workflow.

## Usage

1. Fork this repository

2. Enable the action

3. Trigger the GitHub Actions workflow named Build custom,and select what you want

4. Drink something, wait for building done.

5. Download the Anykernel3 package ,then flash it. Reboot to enjoy.

## License

|Component|License|Detail|
|-|-|-|
|GitHub Actions Workflows|MIT License| See the LICENSE file for details |
|Open-Source Helper (`scripts/configure`) |MIT License|See the LICENSE file for details |
OEM Kernel Source Code |GPLv2 License| Comply with the original terms of the OEM kernel |

## Important Notes

1. `scripts/configure` is an independent build-time auxiliary tool. It only modifies the kernel build configuration files when specific features are enabled during the build phase, does not participate in kernel compilation or linking, and is not embedded into the final kernel image.

2. The modification behavior of `scripts/configure` does not affect the GPLv2 licensing of the OEM kernel source code.

3. When redistributing this repository, the original copyright notice and license text must be retained. When redistributing the compiled kernel package, users only need to comply with the GPLv2 terms of the OEM kernel and do not need to include the license information of this repository.

4. `scripts/configure` is an open-source build helper with no remote access-control (whitelist/blacklist) logic.

 
