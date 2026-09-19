from pathlib import Path
p = Path(r"D:\CODEX\两汉侍中数据库搭建\data\raw\居延汉简释文\bkkbooks_KR5a0332.txt")
t = p.read_text(encoding="utf-8", errors="ignore")
print("len", len(t), "侍中", t.count("侍中"))
i = t.find("侍中")
if i >= 0:
    print(t[max(0, i - 80): i + 120])
# also sample other bamboo terms
for k in ["简", "簡", "尉", "令长", "候"]:
    print(k, t.count(k))
print("--- head ---")
print(t[:400])
