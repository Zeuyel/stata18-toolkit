# Stata 18 License Builder

入口：`stata18-license-builder.py`

示例：

```bash
python3 stata18-license-builder.py --preset mp32
python3 stata18-license-builder.py --preset be --output ~/.config/stata18-runtime/stata.lic
```

已验证工作族默认值：
- `field1=999`
- `field2=24`
- `field3=5`
- `field4=9999`
- `field5=h`
- `field6=` 空值可作为 perpetual
- `field7=32` 作为默认 MP 核心数
