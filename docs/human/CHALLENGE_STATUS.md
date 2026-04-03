# Stata 18 Challenge Status

Current stage: runtime-valid BE/SE/MP licenses recovered; MP core-count field mapped.

Confirmed facts:
- The actual package is `artifacts/original/Stata18Linux64.tar.gz`.
- The installer wrappers are plain shell and not the challenge core.
- `artifacts/binfocus/stinit` is the first meaningful authorization target.
- `stinit` is a small stripped ELF64 executable with no obvious packer and no networking imports.
- `stinit` locally validates `authorization + code` using a base-37 transform and three trailing checksum symbols.
- The decoded payload is `$`-delimited.
- `main` checks:
  - decoded segment `0` equals the entered serial number
  - decoded segment `3` is an allowed edition value (`1`, `2`, `4`, `5`)
- `stata` and `libstata*.so` contain normal local license-consumption messages (`Cannot find license file`, `License is invalid`, `Licensed to:`), but the first string scan found no obvious `CTF`/redirect/local-host markers.
- On success, `stinit` writes `./stata.lic` in this format:
  - `serial!code!authorization!first_line!second_line!sum!`
- `sum` is the decimal byte-sum of the two `Licensed to` lines.
- A local staging of `ncurses5-compat-libs` under `runtime/localdeps/ncurses5` is enough to launch the console runtime without installing packages system-wide.
- `tools/license_probe.py` now generates stinit-compatible `code` / `authorization` pairs for chosen decoded payloads and writes test `stata.lic` files.
- `stinit` accepts the generated pair and writes the expected license file.
- The runtime helper inside `libstata.so` also decodes the generated pair and extracts the intended payload fields correctly.
- The runtime `!`-field extractor at `libstata.so:0x9a5957` uses a bounded copy helper at `libstata.so:0x9e3737` that copies at most `len-1` bytes, so the third license segment effectively preserves only 4 characters even though the caller passes `5`.
- For the unmodified runtime, the encoded stream must therefore be split as:
  - third segment = first 4 encoded characters
  - second segment = remaining encoded characters
- A runtime-valid perpetual license for the original console binary can now be generated with:
  - payload `12345678$999$24$5$9999$h$`
  - `stata.lic` `12345678!$l09ac5q1epw36a5s5ag5wcu!jif9!LocalLab!LocalLab!1524!`
- With an empty `field6`, the original unmodified `stata` starts successfully and displays:
  - `Stata license: Unlimited-student lab perpetual`
- With a past `field6` date, the original runtime recognizes the license class and reports `Your license has expired`.
- With a future `field6` date, the original runtime reports `License is invalid`.
- `field4` controls the displayed seat count (`Single`, `2-user`, `5-user`, `Unlimited`, etc.).
- `field5` controls the displayed channel/type:
  - `a/b` = plain user
  - `c/d` = network
  - `e/f` = compute server
  - `g/h` = student lab
- The recovered perpetual license works in `stata` and `stata-se`.
- The MP runtime uses an extra decoded field beyond the BE/SE layout:
  - payload layout for MP is `serial$field1$field2$field3$field4$field5$field6$field7`
  - `field7` is the licensed core count
- A working unmodified MP payload is:
  - `12345678$999$24$5$9999$h$$8`
  - displayed as `Unlimited-student 8-core lab perpetual`
- For MP:
  - `field3=5` is required in the tested family
  - `field7=0` or `1` is rejected as `License not applicable to this Stata`
  - `field7=2..64` is accepted
  - `field7>64` is clamped to `64`
- `stata-mp` reports the decoded core count internally via `c(processors)`, `c(processors_lic)`, and `c(processors_max)`.
- A searched parameter range for `stata-mp` (`field2=0..40`, `field3=0..10`, fixed `field1=999`, `field4=9999`, `field5=h`, empty `field6`) produced no accepted license.
- `runtime/stata-local/stata.patched` is still available as a probe binary, but it is no longer required to reach the prompt for BE/SE perpetual licenses.
- A local GTK2 runtime has been staged under `runtime/localdeps/gtk2` by extracting `gtk2-2.24.33-5-x86_64.pkg.tar.zst` from the Arch archive package, with no system installation.
- A local GUI launcher `~/.local/bin/xstata-mp-local` now starts `xstata-mp` with the staged GTK2 + ncurses libraries and auto-writes a matching MP license.
- `xstata-mp-local` now resolves the previously missing `libgtk-x11-2.0.so.0` / `libgdk-x11-2.0.so.0` libraries successfully.
- The remaining GUI-side blocker on this workstation is no longer missing GTK2; it is the lack of a usable X display in the current session (`cannot open display: :0`).
- A local GTK2 theme file now lives at `~/.config/stata-local/gtkrc-2.0` and is applied by `xstata-mp-local`.
- A local TUI control script now lives at `~/.local/bin/stata-deck` and provides:
  - GUI launch
  - console launch
  - MP core selection via `fzf`
  - profile/status view
  - batch do-file launch
- `xstata-mp-local` now suppresses the non-fatal `canberra-gtk-module` warning by unsetting `GTK_MODULES`.
- `stata-mp-local` and `xstata-mp-local` both read default core settings from `~/.config/stata-local/config.env`.
- A normalized user-local install now lives at `~/.local/opt/stata-mp` with this layout:
  - `bin/` launchers
  - `runtime/` binaries and writable `stata.lic`
  - `lib/` staged GTK2 + ncurses dependencies
  - `tools/` helper scripts
  - `share/` icons and visual assets
- The active user-facing commands are now:
  - `~/.local/bin/stata-mp`
  - `~/.local/bin/xstata-mp`
- Legacy compatibility links remain available:
  - `~/.local/bin/stata-mp-local`
  - `~/.local/bin/xstata-mp-local`
  - `~/.config/stata-local` -> `~/.config/stata-mp`
- The active wrapper config now lives at `~/.config/stata-mp/config.env`, with theme files under `~/.config/stata-mp/themes/`.
- A static visual license workbench now exists at:
  - single-file page: `tools/license_lab.html`
- The static workbench locally reproduces the recovered base-37 transform and can:
  - accept the operator-facing license parameters directly
  - explain what each parameter controls
  - output `Serial number`, `Code`, and `Authorization` for installer-style input flows
  - generate complete `stata.lic` text
  - explain where to place `stata.lic` and how to use it
- The workbench intentionally hides internal encoder details such as the intermediate encoded stream, authorization segment, and code segment.
- The workbench is no longer installed as a user command or desktop launcher; it is opened directly as an HTML file.
- The current operator flow now supports both:
  - installer-style entry of `Serial number` / `Code` / `Authorization`
  - direct replacement of `stata.lic`
- The workbench was validated against `tools/license_probe.py` with the known-good MP payload:
  - `12345678$999$24$5$9999$h$$32`
  - generated encoded stream `985$qbr$02wgs4fmux0wiw06wmd1ox5`
  - generated license `12345678!qbr$02wgs4fmux0wiw06wmd1ox5!985$!LocalLab!LocalLab!1524!`

Interpretation:
- `stinit` currently looks like a stock local validator/writer rather than a wrapped network challenge.
- An isolated install into `ctf/stata18-toolkit/runtime/stata-local` completed successfully, which confirms our installer-path analysis.
- The earlier `rc=3` confusion in the unmodified runtime came from writing the encoded stream with a 5-character third segment. The real runtime truncates that segment to 4 bytes during `stata.lic` parsing.
- The challenge is no longer blocked on “can the original app accept a locally generated license”; the answer is yes for BE/SE when `field6` is empty and the encoded stream is split at 4 characters.
- `stata` is no longer blocked by ncurses on this workstation because the required compatibility libs are staged locally.
- `xstata`/`xstata-mp` are no longer blocked on missing GTK2 packaging; the remaining challenge work is in GUI behavior and flag discovery, not dependency staging.
- The normalized local install and static HTML generator reduce operator friction, so future field-matrix exploration can be done without hand-editing `stata.lic`.
- The remaining challenge work is to determine whether the local CTF flag is hidden behind a non-stock license text, GUI-only behavior, or a parameter set outside the stock BE/SE/MP matrices already mapped.

Primary reference:
- `ctf/stata18-toolkit/docs/human/CHALLENGE_REPORT.md`

## 2026-04-03 Delivery Snapshot

- 最终交付物已经落在 `delivery/`，而不是 `~/.local/opt/stata-mp` 这类本地验证目录。
- 交付结构固定为：
  - `delivery/license-builder/stata18-license-builder.sh`
  - `delivery/archpkg/stata18-runtime/PKGBUILD`
  - `delivery/archpkg/stata18-runtime/stata18-runtime-18.0.0-1-x86_64.pkg.tar.zst`
- 本地安装只用于验证运行路径、依赖内置和 wrapper 行为，不作为最终交付产物。
- `delivery/archpkg/stata18-runtime/` 内已包含 launcher、desktop entry、sample config、GTK2 主题和打包所需 runtime 模板。

## 2026-04-03 GitHub Release CI

- 已新增 GitHub Actions 发布流：`.github/workflows/release.yml`。
- 发布流会从 Duke 下载 `Stata18Linux64.tar.gz`，校验 SHA-256，然后在 Arch Linux 容器内构建 `stata18-runtime`。
- Release 资产现在规划为：构建出的 `.pkg.tar.zst`、版本化 builder 脚本、`SHA256SUMS.txt`、`BUILD-INFO.txt`。
- 仓库本身不应再提交上游 tarball、运行时工作目录或最终 `.pkg.tar.zst`。

## 2026-04-03 GitHub Publication

- 源码仓库已发布到：`https://github.com/Zeuyel/stata18-toolkit`
- 首次推送只保留源码、文档和 CI/CD 配置；本地生成物与上游二进制未进入 git。
- 仓库内不再依赖本地 `git config user.name/user.email`；提交使用一次性环境变量完成。
- 下一步应直接在 GitHub 上执行一次 `workflow_dispatch`，确认 Release 资产能完整产出。

## 2026-04-03 Release Validation

- `workflow_dispatch` 已验证通过，run id: `23944903443`
- Draft Release 已生成：`stata18-runtime-v18.0.0-1`
- Release 页面：`https://github.com/Zeuyel/stata18-toolkit/releases/tag/untagged-2e2186c5a7e3c02c3858`
- 当前已确认资产包含 builder、`SHA256SUMS.txt`、`BUILD-INFO.txt`、主 `.pkg.tar.zst`；同时还产出了一个 `-debug` 包。

## 2026-04-03 Shell Builder Refresh

- `delivery/license-builder/stata18-license-builder.sh` 现在是主入口；无参数时进入交互式 shell 提示流程。
- `delivery/archpkg/stata18-runtime/stata18-license-builder.sh` 已从 Python wrapper 改成纯 shell 实现，运行时不再因为 builder 需要 `python` 依赖。
- `.github/workflows/release.yml` 和 `scripts/ci/build-release.sh` 现在发布 `.sh` builder 资产，并移除了仅为 builder 引入的 Python 安装步骤。

## 2026-04-03 Shell Release Publication

- 重新触发的 `workflow_dispatch` 已成功完成，run id: `23947872803`
- 新 release tag：`stata18-runtime-v18.0.0-2`
- Release 页面：`https://github.com/Zeuyel/stata18-toolkit/releases/tag/stata18-runtime-v18.0.0-2`
- 已确认资产包含：`stata18-license-builder.sh`、`stata18-runtime-18.0.0-2-x86_64.pkg.tar.zst`、对应 `-debug` 包、`SHA256SUMS.txt`、`BUILD-INFO.txt`
