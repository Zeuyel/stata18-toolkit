# Stata 18 License Builder

主入口：`stata18-license-builder.sh`

特性：
- 无参数运行时进入交互式 shell 提示流程
- 保留 `--preset` / `--output` / `--format` 等非交互参数，方便 CI 或脚本调用
- 运行时不依赖 Python

示例：

```bash
./stata18-license-builder.sh
./stata18-license-builder.sh --non-interactive --preset mp32 --output ~/.config/stata18-runtime/stata.lic
./stata18-license-builder.sh --non-interactive --preset be --format license-only
```

已验证工作族默认值：
- `field1=999`
- `field2=24`
- `field3=5`
- `field4=9999`
- `field5=h`
- `field6=` 空值可作为 perpetual
- `field7=32` 作为默认 MP 核心数

字段含义速查：
- `preset`：授权模板。`be`=基础版，`mp32`=32 核 MP，`mp64`=64 核 MP。
- `Serial number`：安装器里填写的序列号。
- `field1/field2/field3`：内部兼容字段，通常保持默认值即可。
- `field4`：席位数/用户数，`9999` 表示 `Unlimited`。
- `field5`：授权类型，`h` 表示 `student lab`。
- `field6`：到期日。Stata 18 留空表示 perpetual。
- `field7`：MP 核心数。BE 留空，MP 一般填 `32` 或 `64`。
- `line1/line2`：界面里显示的授权名称两行文本。
- `split-prefix`：内部把 `Authorization` 和 `Code` 切开的分割位，通常保持 `4`。
