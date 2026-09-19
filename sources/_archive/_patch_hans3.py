from pathlib import Path
p = Path(r"D:\CODEX\两汉侍中数据库搭建\sources\hans.py")
t = p.read_text(encoding="utf-8")
block = '''    "劒": "剑", "靑": "青", "眞": "真",
})'''
extra = '''    "劒": "剑", "靑": "青", "眞": "真",
    "僃": "备", "篤": "笃", "職": "职", "來": "来", "請": "请",
    "組": "组", "綬": "绶", "乗": "乘", "晝": "昼", "稱": "称",
    "贊": "赞", "績": "绩", "準": "准", "補": "补", "從": "从",
    "後": "后", "與": "与", "爲": "为", "無": "无", "員": "员",
    "屬": "属", "獨": "独", "斷": "断", "給": "给", "禦": "御",
    "衞": "卫", "勳": "勋", "舊": "旧", "續": "续", "憲": "宪",
    "旣": "既", "並": "并", "驛": "驿", "傳": "传", "國": "国",
    "書": "书", "漢": "汉", "門": "门", "開": "开", "長": "长",
})'''
if '"僃": "备"' not in t:
    t = t.replace(block, extra)
    p.write_text(t, encoding="utf-8")
    print("hans expanded")
else:
    print("ok")
import sys
sys.path.insert(0, str(p.parent))
if "hans" in sys.modules:
    del sys.modules["hans"]
from hans import t2s
print(t2s("行能兼僃，忠孝尤篤，當以舊典輔斯職焉"))
print(t2s("得舉非法白請及出省戶休沐往來過直事"))
