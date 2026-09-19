"""检查 hans.t2s 对制度页关键用字的覆盖，并打印缺失项。"""
import sys
sys.path.insert(0, r"D:\CODEX\两汉侍中数据库搭建\sources")
from hans import t2s

samples = [
    "㠯其儒者", "負璽", "金蟬左貂", "唾壺", "僕射", "後改爲祭酒",
    "復入", "與中官共止", "無員", "屬少府", "秩千石", "獨斷",
    "漢官儀", "給事黃門", "員各六人", "參乘", "驂乘", "佩璽",
    "貂蟬", "執虎子", "親省起居", "典制度", "長安", "從至長安",
    "禦", "衞", "衞尉", "勳", "將大夫郎", "舉非法",
    "舊儀", "續漢志", "獻帝", "靈帝", "賈逵", "竇憲",
]
for s in samples:
    out = t2s(s)
    mark = "OK" if out == s or all(ord(c) < 0x3400 or c in out for c in s) else "?"
    # print if any traditional-looking char remains
    tradish = [c for c in out if c in "㠯璽蟬壺僕後與無屬獨給黃員參驂佩貂親長從禦衞勳將舉舊續獻靈賈竇儀斷漢書國"]
    if tradish or out != s:
        print(f"{s!r:30s} -> {out!r:30s} left={tradish}")
    else:
        print(f"{s!r:30s} -> {out!r}  [clean]")
