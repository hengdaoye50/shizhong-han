from pathlib import Path
import re

# pull real 王莽/更始/侍中 institutional sentences from corpus
RAW = Path(r"D:\CODEX\两汉侍中数据库搭建\data\raw")
keys = ["侍中"]
need = ["莽", "更始", "亡員", "亡员", "禁中", "少府", "秩千石", "比二千石", "皆加官", "明經", "明经", "員各", "典制度", "侍中寺", "唾壺", "唾壶"]
count = 0
for p in RAW.rglob("*.txt"):
    if p.name.startswith("."):
        continue
    try:
        t = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    if "侍中" not in t:
        continue
    t2 = re.sub(r"\{\{[^}]{0,200}\}\}", " ", t)
    t2 = re.sub(r"<ref[^>]*>.*?</ref>", " ", t2, flags=re.S)
    t2 = re.sub(r"\s+", "", t2)
    for sent in re.split(r"(?<=[。！？；;])", t2):
        if "侍中" not in sent or not (12 <= len(sent) <= 280):
            continue
        if any(k in sent for k in ["王莽", "更始", "莽時", "莽时", "新莽"]):
            print(p.relative_to(RAW), "|", sent[:160])
            count += 1
            if count > 40:
                raise SystemExit
