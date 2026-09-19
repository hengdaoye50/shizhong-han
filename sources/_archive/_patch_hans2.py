from pathlib import Path
p = Path(r"D:\CODEX\两汉侍中数据库搭建\sources\hans.py")
t = p.read_text(encoding="utf-8")
old = '"眞": "真", "衆": "众", "啓": "启",'
new = '"眞": "真", "衆": "众", "啓": "启", "旣": "既", "並": "并", "旣": "既",'
if "旣" not in t:
    t = t.replace(old, new)
    p.write_text(t, encoding="utf-8")
    print("added 旣/並")
else:
    print("ok already")
import sys
sys.path.insert(0, str(p.parent))
if "hans" in sys.modules:
    del sys.modules["hans"]
from hans import t2s
print(t2s("魏國旣建，拜侍中，與王粲並典制度"))
