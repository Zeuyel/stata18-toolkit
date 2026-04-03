# Stata 18 Reverse-Engineering Notes

## `stinit` summary

Primary target: `artifacts/binfocus/stinit`

Key code locations:
- `0x400ce0`: main
- `0x400a0e`: read one line and trim leading/trailing spaces
- `0x400a80`: prompt for a labeled field such as `Serial number`, `Code`, `Authorization`
- `0x400b0d`: validate freeform line input for the two `Licensed to` lines
- `0x400bc6`: parse yes/no prompts
- `0x4013d0`: extract a delimited segment from a decoded string
- `0x401440`: validate and decode `authorization + code`

## High-confidence behavior

### Installer flow

`main` only proceeds if either `./stata` or `./xstata` exists.

If `./stata.lic` already exists, `stinit` offers to back it up to `./stata.lic.bak` using `link()` and `unlink()` before continuing.

After license-agreement confirmation, `stinit` asks for:
- serial number
- code
- authorization

### `authorization + code` validation

`0x401440` takes three arguments:
- `rdi`: code string
- `rsi`: authorization string
- `rdx`: output buffer

Observed behavior:
1. Concatenate `authorization || code` into the output buffer.
2. Normalize the concatenated string:
- remove spaces
- accept digits `0-9`
- accept letters `a-z` or `A-Z`
- accept delimiter `$`
- reject anything else
3. Convert characters into base-37 symbols:
- `0-9` -> `0..9`
- `a-z` / `A-Z` -> `10..35`
- `$` -> `36`
4. Transform the symbol stream into cyclic adjacent differences modulo 37.
5. Treat the last 3 transformed symbols as checksums and verify them against the prefix:
- checksum 1: sum of all prefix symbols mod 37
- checksum 2: sum of prefix symbols at odd indexes mod 37
- checksum 3: sum of prefix symbols at even indexes mod 37
6. If verification succeeds, drop the trailing 3 checksum symbols and convert the remaining base-37 symbols back to characters.

Return convention:
- success: `0`
- failure: nonzero

### Segment extraction and main checks

`0x4013d0` extracts the Nth segment from a string using a chosen delimiter.

`main` uses the decoded payload from `0x401440` as follows:
- segment `0` split on `$` must equal the user-entered serial number
- segment `3` split on `$` must parse as an integer
- accepted integer values are `1`, `2`, `4`, or `5`

This means the decoded payload format is at least:

`<serial>$...$...$<edition>`

where `<edition>` is one of `1`, `2`, `4`, `5`.

### `stata.lic` file format

On success, `stinit` writes `./stata.lic` using `fprintf()` with `"%s!"` for five strings and `"%d!"` for one decimal checksum.

The resulting layout is:

`serial!code!authorization!first_line!second_line!sum!`

where `sum` is the decimal sum of all byte values from `first_line` and `second_line`.

It then calls `chmod("./stata.lic", 0644)`.

### Validation of the two `Licensed to` lines

`0x400b0d` enforces:
- not blank
- minimum length 5
- maximum length 240
- must not contain `!`

## Interpretation

So far `stinit` looks like a stock local license-initialization helper, not a packed loader and not a networked challenge wrapper.

If challenge-specific behavior exists, the next likely targets are:
- `artifacts/binfocus/stata`
- `artifacts/binfocus/libstata.so`
- `artifacts/binfocus/libstata-se.so`
- `artifacts/binfocus/libstata-mp.so`

## Runtime binary scan

A first-pass string scan of `stata` and `libstata*.so` found expected local license-consumption messages such as:
- `Cannot find license file`
- `License is invalid`
- `Your license has expired`
- `Stata license:`
- `Serial number:`
- `Licensed to:`

It did not find obvious strings referencing:
- `CTF`
- `192.168.2.1`
- `127.0.0.1`
- `RoxyBrowser`
- `lumibrowser`
- `discord`

This does not prove the runtime binaries are stock, but it lowers the probability of a trivial string-level challenge implant in those files.

## Local installation check

An isolated install was performed into `ctf/stata18-toolkit/runtime/stata-local` by invoking the original `install` script from the extracted media. The install completed successfully and produced the expected outputs, including:
- `installed.180`
- `stinit`
- `stata` / `xstata` / `stata-se` / `stata-mp`
- `libstata.so` / `libstata-se.so` / `libstata-mp.so`

This confirms the earlier reverse engineering of `install` and `inst2`: the installer path behaves as expected.

Runtime checks then showed environment-level missing dependencies:
- `stata` is blocked by missing `libncurses.so.5` and `libtinfo.so.5`
- `xstata` is additionally blocked by missing GTK2 libraries such as `libgtk-x11-2.0.so.0` and `libgdk-x11-2.0.so.0`

At this stage, installer analysis appears correct; the next execution blocker is the host library set, not the package logic itself.

## Runtime checker differential

A local copy of `ncurses5-compat-libs` was extracted into `runtime/localdeps/ncurses5`, and the broken absolute `libtinfo.so.5 -> /usr/lib/libncurses.so.5` symlink was rewritten locally so the console runtime could be launched with:

`LD_LIBRARY_PATH=runtime/localdeps/ncurses5/usr/lib ./stata`

This removed the missing-library blocker and shifted the failure to the actual license checker.

### Working generator and runtime mismatch

`tools/license_probe.py` now:
- encodes a chosen decoded payload into a `stinit`-compatible `authorization + code`
- writes `stata.lic`
- can execute either the original runtime or a patched probe binary

For payloads such as:

`12345678$999$24$5$0$h$`

the script generates a code / authorization pair that `stinit` accepts.

`tools/call_license_fn.c` directly calls internal functions in `libstata.so` and showed:
- `decode_rc=0` from the runtime decode helper at `libstata.so:0x5eb151`
- decoded payload exactly matches the injected payload
- runtime field extractors return the expected values:
  - `field1=999`
  - `field2=24`
  - `field3=5`
  - `field4=0`
  - `field5=h`
  - `field6=` (empty)
- despite that, the internal checker at `libstata.so:0x9a5e88` still returns `rc=3`

This proves the remaining discrepancy is runtime-only and lives after the basic decode / parse stages already reversed from `stinit`.

### Local bypass probe

To keep analyzing the display path without mutating the original binary, a copied executable was created:

- original: `runtime/stata-local/stata`
- probe copy: `runtime/stata-local/stata.patched`

The copy changes the invalid-return immediate at file offset `0x7b6608` from:

- `bb 03 00 00 00`

to:

- `bb 00 00 00 00`

With the patched copy and staged ncurses libs, the runtime reaches the normal Stata banner and dot prompt and displays the injected serial number and `Licensed to` lines:

- `Serial number: 12345678`
- `Licensed to: LocalLab`

So the current hard boundary is no longer “can the app run”, but “what exact additional condition inside the unmodified checker turns a correctly decoded payload into rc=3”.

## Runtime-correct `stata.lic` split

The remaining mismatch was not in the base-37 payload transform. It was in how the unmodified runtime parses the `!`-delimited `stata.lic` fields.

`libstata.so:0x9a5957` extracts one license field and then copies it with the helper at `libstata.so:0x9e3737`.

That helper copies at most `len-1` bytes and then writes a trailing `NUL`.

This matters because the checker loads the third `!`-delimited segment with `len=5`. In practice the runtime preserves only 4 payload characters from that segment.

So for the original runtime, the encoded stream must be split as:

- third segment: first 4 encoded characters
- second segment: remaining encoded characters

and not as the earlier 5-character split used for `stinit` probing.

### Working perpetual license on the unmodified runtime

For payload:

`12345678$999$24$5$9999$h$`

`tools/license_probe.py` now writes a runtime-valid license by default:

`12345678!$l09ac5q1epw36a5s5ag5wcu!jif9!LocalLab!LocalLab!1524!`

Running the original unmodified console binary with staged ncurses libs:

`LD_LIBRARY_PATH=runtime/localdeps/ncurses5/usr/lib ./runtime/stata-local/stata`

produces a normal startup banner and prompt:

- `Stata license: Unlimited-student lab perpetual`
- `Serial number: 12345678`
- `Licensed to: LocalLab`

This establishes a real locally generated license path for the stock BE/SE console runtimes.

## Date field behavior

Observed behavior for decoded `field6`:

- empty: accepted as perpetual; runtime reaches the dot prompt
- past date such as `01012020`: license class is recognized and displayed, then runtime prints `Your license has expired`
- future date such as `12312099`: runtime prints `License is invalid`

So `field6` is not required for a valid local startup. In practice, leaving it empty is the working perpetual path.

## Display mapping

Using the original unmodified runtime with an expired date to force a clean one-line license display, the mapped display controls are:

- `field4`
  - `0` or `1` -> `Single`
  - `2`, `5`, `10`, ... -> `<n>-user`
  - `9999` -> `Unlimited`
- `field5`
  - `a`, `b` -> plain user
  - `c`, `d` -> `network`
  - `e`, `f` -> `compute server`
  - `g`, `h` -> `student lab`

Examples:

- `field4=0`, `field5=c` -> `Single-user network`
- `field4=5`, `field5=e` -> `5-user compute server`
- `field4=9999`, `field5=h` -> `Unlimited-student lab`

No non-stock or obviously challenge-specific text appeared in this mapped BE/SE matrix.

## Edition observations

- The recovered perpetual license works in:
  - `runtime/stata-local/stata`
  - `runtime/stata-local/stata-se`
- A searched space for `runtime/stata-local/stata-mp` with:
  - `field2=0..40`
  - `field3=0..10`
  - fixed `field1=999`
  - fixed `field4=9999`
  - fixed `field5=h`
  - empty `field6`
  produced no accepted MP startup.

So current evidence supports a stock BE/SE local license path, while MP either uses different applicability rules or requires a different parameter family not yet mapped.

## MP payload family

That missing MP family has now been mapped.

The MP checker accepts one additional decoded field beyond the BE/SE payload:

`serial$field1$field2$field3$field4$field5$field6$field7`

where:

- `field1` still must be greater than `179`
- `field2` still must be `24`
- `field3` is MP-specific in the tested family and must be `5`
- `field4` is the seat-count / Unlimited field
- `field5` selects the displayed channel suffix
- `field6` is the optional date field
- `field7` is the licensed core count

### Working MP example

This payload starts the original unmodified `runtime/stata-local/stata-mp`:

`12345678$999$24$5$9999$h$$8`

It displays:

- `Stata license: Unlimited-student 8-core lab perpetual`

and reaches the normal prompt.

### Core-count behavior

Observed behavior for MP `field7`:

- `0` or `1` -> `License not applicable to this Stata`
- `2..64` -> accepted
- `>64` -> accepted but clamped to `64`

With payload `12345678$999$24$5$9999$h$$32`, batch-mode `creturn list` in `stata-mp` reports:

- `c(MP) = 1`
- `c(processors) = 32`
- `c(processors_lic) = 32`
- `c(processors_max) = 32`

So the extra MP field is not cosmetic. It directly controls the active licensed processor count exposed by the application.

### MP display mapping

Using the unmodified runtime with an expired date and `field7=8`, the mapped MP display controls are:

- `field4`
  - `0` -> `Single`
  - `2` -> `2-user`
  - `9999` -> `Unlimited`
- `field5`
  - `a`, `b` -> plain user
  - `c`, `d` -> `network`
  - `e`, `f` -> `compute server`
  - `g`, `h` -> `lab`

Examples:

- `field4=0`, `field5=c` -> `Single-user 8-core network`
- `field4=2`, `field5=e` -> `2-user 8-core compute server`
- `field4=9999`, `field5=h` -> `Unlimited-student 8-core lab`

No challenge-specific or flag-like text appeared in the mapped MP display strings either.

## Local GTK2 staging for GUI startup

Because `gtk2` is no longer available from the live Arch repositories, the GUI dependency was staged locally from the official Arch archive package:

- archive package: `gtk2-2.24.33-5-x86_64.pkg.tar.zst`
- local extraction target: `runtime/localdeps/gtk2`

This avoided any system package installation or writes to `/usr`.

After extraction, the previously missing GUI libraries are resolved by:

- `runtime/localdeps/gtk2/usr/lib/libgtk-x11-2.0.so.0`
- `runtime/localdeps/gtk2/usr/lib/libgdk-x11-2.0.so.0`

A local launcher was created at:

- `~/.local/bin/xstata-mp-local`

It:

- writes a runtime-valid MP license with the chosen `STATA_MP_CORES` value
- prepends the staged GTK2 and ncurses compatibility libraries via `LD_LIBRARY_PATH`
- executes `runtime/stata-local/xstata-mp`

With this wrapper, the runtime is past the missing-library stage. The current failure mode is:

- `Gtk-WARNING: cannot open display: :0`

which indicates that GTK2 itself is now resolved and the remaining blocker is the graphical display environment, not the license or the shared-library set.

## Local UX layer

Because the stock GTK2 interface is visually dated, a fully local wrapper layer was added without modifying the Stata binaries:

- GUI wrapper: `~/.local/bin/xstata-mp-local`
- console wrapper: `~/.local/bin/stata-mp-local`
- TUI control surface: `~/.local/bin/stata-deck`
- local config: `~/.config/stata-local/config.env`
- local GTK2 theme: `~/.config/stata-local/gtkrc-2.0`

### GUI wrapper behavior

`xstata-mp-local` now:

- reads the default core count from `~/.config/stata-local/config.env`
- applies the local GTK2 theme via `GTK2_RC_FILES`
- unsets `GTK_MODULES` so the non-fatal `canberra-gtk-module` warning no longer appears
- prepends the local GTK2 + ncurses libraries

The theme is intentionally simple and non-invasive: warm paper background, darker ink text, and a muted teal selection/accent color. It improves readability without attempting to patch the binary UI itself.

### TUI launcher behavior

`stata-deck` provides a terminal control room for the local MP runtime:

- launch GUI
- launch console
- set licensed MP core count using `fzf`
- show the active runtime/profile
- run a batch do-file

It persists the chosen core count by updating:

- `~/.config/stata-local/config.env`

So the console and GUI wrappers stay in sync.

## Normalized user-local install

The operator-facing setup was then consolidated into a cleaner user-local install root:

- install root: `~/.local/opt/stata-mp`
- active commands:
  - `~/.local/bin/stata-mp`
  - `~/.local/bin/xstata-mp`
- active config:
  - `~/.config/stata-mp/config.env`
  - `~/.config/stata-mp/themes/mojave.gtkrc`

This keeps the runtime tree, staged libraries, launcher scripts, and icons separate from the reverse-engineering workspace while still avoiding any system package installation.

Legacy entry points were preserved as compatibility symlinks:

- `~/.local/bin/stata-mp-local`
- `~/.local/bin/xstata-mp-local`
- `~/.config/stata-local` -> `~/.config/stata-mp`

## Static license workbench

A static local operator page was added for faster payload and license iteration:

- single-file page:
  - `tools/license_lab.html`

The page runs entirely in the browser with no backend and reimplements the recovered base-37 encoder/decoder locally. It is intentionally operator-facing rather than reverse-engineering-facing. It can:

- accept the license parameters directly
- explain what each parameter means in the mapped local family
- output `Serial number`, `Code`, and `Authorization` for installer dialogs on platforms that ask for those values
- emit a full `stata.lic`
- explain where the generated file should be placed for the normalized local install

The intermediate `encoded`, `authorization`, and `code` values are no longer shown in the UI. They are still computed internally, but the page now keeps the surface focused on the operator task: fill parameters, copy the generated `stata.lic`, and drop it into the runtime.

After operator feedback, the page was adjusted again so the user-facing output includes the three installer inputs:

- `Serial number`
- `Code`
- `Authorization`

while still hiding the broader internal transform state.

Validation against `tools/license_probe.py` with the known-good MP payload:

- payload: `12345678$999$24$5$9999$h$$32`
- encoded: `985$qbr$02wgs4fmux0wiw06wmd1ox5`
- authorization: `985$`
- code: `qbr$02wgs4fmux0wiw06wmd1ox5`
- `stata.lic`: `12345678!qbr$02wgs4fmux0wiw06wmd1ox5!985$!LocalLab!LocalLab!1524!`

This gives a low-friction way to explore license variations visually before dropping the generated file into:

- `~/.local/opt/stata-mp/runtime/stata.lic`
