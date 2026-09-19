from pathlib import Path

p = Path(r"D:\CODEX\两汉侍中数据库搭建\sources\hans.py")
t = p.read_text(encoding="utf-8")
anchor = '# str.translate 需要单字码位表；多字词进 _WORD'
assert anchor in t, "anchor not found"
extra = '''# 制度页/辑本补字（严可均㠯、职官用字等）
_T2S.update({
    "㠯": "以", "璽": "玺", "蟬": "蝉", "僕": "仆", "復": "复",
    "獨": "独", "斷": "断", "給": "给", "禦": "御", "衞": "卫",
    "勳": "勋", "舊": "旧", "續": "续", "憲": "宪", "曄": "晔",
    "階": "阶", "臻": "臻", "巽": "巽", "廙": "廙", "禕": "祎",
    "祗": "祗", "輯": "辑", "沖": "冲", "禎": "祯", "曠": "旷",
    "靑": "青", "靑": "青", "眞": "真", "衆": "众", "啓": "启",
    "聶": "聂", "覬": "觊", "覬": "觊", "齣": "出", "餘": "余",
    "劒": "剑", "劍": "剑", "璫": "珰", "負": "负", "傳": "传",
    "國": "国", "學": "学", "術": "术", "産": "产", "黨": "党",
})

'''
if "制度页/辑本补字" not in t:
    t = t.replace(anchor, extra + anchor)
    p.write_text(t, encoding="utf-8")
    print("hans.py patched")
else:
    print("already patched")

import sys
sys.path.insert(0, str(p.parent))
# force reload
if "hans" in sys.modules:
    del sys.modules["hans"]
from hans import t2s

tests = [
    "㠯其儒者，特聽掌御坐唾壺",
    "行則負璽。舊高取一人爲僕射，後改爲祭酒",
    "侍中金蟬左貂",
    "王莽秉政，侍中復入，與中官共止",
    "《獨斷》曰",
    "給事黃門侍郎員各六人",
    "侍中憲，朕之元兄",
    "魏國旣建，拜侍中，與王粲並典制度",
    "衛尉",
    "舊儀，侍中親省起居",
]
for s in tests:
    print(t2s(s))
