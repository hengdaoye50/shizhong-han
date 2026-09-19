import json
from pathlib import Path

d = json.loads(
    Path(r"D:\CODEX\两汉侍中数据库搭建\shizhongdata\data\institution.json").read_text(
        encoding="utf-8"
    )
)
print("display_script:", d.get("display_script"))
print("note:", d.get("note", "")[:80])
print("sources_note:")
for s in d.get("sources_note") or []:
    print(" -", s)
print("quality:", d.get("quality"))
print("stats:", d.get("stats"))
print("gaps:", len((d.get("roster_check") or {}).get("gaps") or []))
print()
trad = set("漢書後國為無員與從來門開萬號孫權獻靈㠯璽蟬僕獨斷給禦衞勳舊續憲旣並僃篤職請組乗晝稱贊績準補節竝矦藝")
bad = 0
for ph in d["phases"]:
    print(f"{ph['id']:16s} n={ph['quote_count']}")
    for q in ph["quotes"][:3]:
        s = q["sentence"]
        left = [c for c in s if c in trad]
        mark = "BAD" if left or "}}" in s or "===" in s else "ok"
        if mark == "BAD":
            bad += 1
        print(f"  {mark} [{q['book']}] {s[:72]}")
print("bad_total_in_sample", bad)
