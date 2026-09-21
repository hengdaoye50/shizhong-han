"""Inspect nature vs quotes for timeline backfill candidates."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGETS = {
    "辛毗","张辟疆","孔安国","卓茂","卫觊","孙资","丁冲","金建","李祯","梁安国",
    "刘劭","刘平","刘恭","刘珍","刘瑰","刘茂","台崇","史恃","向栩","周举",
    "孔昱","寇荣","尹敏","张兴","张湛","张玄","来历","杨奇","桓郁","江革",
    "淳于恭","王莽","王接","王方","荀勖","陈矫","陈泰","金涉","金赏","霍山",
    "霍禹","黄权","赵典","郑均","阎畅","马康","邓蕃","邓建","和逌","李尤",
    "刘能卿","王舜","王音","班伯","种辑","许允","谢弼","赵孝","尹忠","卫伉",
    "孔霸","孔永","杨伦","蔡玄","耿箕","邓干","闾丘弘","阴统","陈光","马何罗",
    "郭昌","杨统","王况","王去疾","王参","王奇","王望","王歙","王能","王辅",
    "王邑","王闳","徐宣","是仪","李充","李棽","杜辅","公孙敬声","关统","何休","任芝",
}

for p in sorted((ROOT / "data" / "cards").glob("*.md")):
    t = p.read_text(encoding="utf-8", errors="ignore")
    name = p.stem.split("_")[0]
    if name not in TARGETS:
        continue
    m = re.search(r"^---\n(.*?)\n---\n", t, re.S)
    if not m:
        continue
    fm = m.group(1)
    nat = re.search(r"nature:\s*(.*)", fm)
    birth = re.search(r"^birth:\s*(.*)", fm, re.M)
    death = re.search(r"^death:\s*(.*)", fm, re.M)
    dyn = re.search(r"^dynasty:\s*(.*)", fm, re.M)
    quotes = re.findall(r"quote:\s*(.+)", fm)
    n = (nat.group(1).strip() if nat else "")
    good = bool(
        re.search(
            r"年|帝|初|中|末|间|更始|魏国|曹爽|光武|武帝|昭帝|宣帝|元帝|成帝|哀帝|安帝|顺帝|桓帝|灵帝|献帝|明帝|章帝|和帝|惠帝|吕后|建安|延光|永平|元寿|阳嘉|建武|元兴|初平|兴平|正始|景初|嘉平",
            n,
        )
    )
    print("===" , name, "dyn=", dyn.group(1).strip() if dyn else "", end=" ")
    print("birth=", birth.group(1).strip() if birth else "", end=" ")
    print("death=", death.group(1).strip() if death else "")
    print("  nature", "OK" if good else "WEAK", ":", n[:120])
    for q in quotes[:4]:
        print("  Q:", q[:100])
