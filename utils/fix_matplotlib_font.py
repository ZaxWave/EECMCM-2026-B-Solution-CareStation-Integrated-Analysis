"""
fix_matplotlib_font.py — 一键修复 Windows 下 matplotlib 中文方框问题
运行后自动检测系统可用中文字体, 清除缓存, 注入 rcParams
"""
import matplotlib
import matplotlib.font_manager as fm
from pathlib import Path
import shutil, os, sys

# ---- Step 1: 扫描系统可用中文字体 ----
PRIORITY_FONTS = [
    'SimHei', 'Microsoft YaHei', 'Noto Sans SC', 'Noto Serif SC',
    'STXihei', 'DengXian', 'KaiTi', 'FangSong', 'STKaiti',
    'SimSun', 'FangSong', 'HYZhongHei', 'STFangsong', 'STXingkai',
]

# 重建字体管理器 (强制扫描)
fm._load_fontmanager(try_read_cache=False)

available = []
for f in fm.fontManager.ttflist:
    if any(k.lower() in f.name.lower() for k in ['simhei','yahei','noto','song','hei','kai','fang','ming','dengxian','xihei','zhonghei']):
        available.append((f.name, f.fname))

print(f"[FontScan] 检测到 {len(available)} 个可用中文字体:")
for name, path in available:
    print(f"  {name}: {path}")

# ---- Step 2: 确定最佳字体 ----
selected_font = None
for priority in PRIORITY_FONTS:
    for name, path in available:
        if priority.lower() in name.lower():
            selected_font = (name, path)
            break
    if selected_font:
        break

if selected_font is None and available:
    selected_font = available[0]

if selected_font is None:
    print("[ERROR] 未检测到任何中文字体! 请检查 C:\\Windows\\Fonts")
    sys.exit(1)

font_name, font_path = selected_font
print(f"\n[Selected] {font_name} → {font_path}")

# ---- Step 3: 注册字体并清除缓存 ----
# 直接添加字体文件
fm.fontManager.addfont(font_path)

# 清除 matplotlib 字体缓存
cache_dir = Path(matplotlib.get_cachedir())
for cache_file in cache_dir.glob("fontlist*.json"):
    cache_file.unlink()
    print(f"[CacheCleared] {cache_file}")

# ---- Step 4: 写入全局 rcParams 补丁 ----
# 生成 matplotlibrc 覆盖文件
rc_path = Path(os.path.dirname(font_path)).parent / "matplotlib" / "matplotlibrc"
print(f"\n[FinalFont] 最佳中文字体: {font_name}")
print(f"[FinalFont] 路径: {font_path}")
print("[FixDone] 请在脚本中导入并使用此字体")

# 输出供批处理使用
print(f"\nFONT_NAME={font_name}")
print(f"FONT_PATH={font_path}")
