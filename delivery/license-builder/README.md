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
