"""名录核对（第二版）：更严的人名过滤 + 与现有卡片/候选交叉。

输出:
  data/candidates/roster_gap_v2.csv     高置信拟补与已核对条
  data/candidates/roster_gap_noise.csv  噪声（供改进抽取器）
  docs/roster_gap_report.md             人读报告
"""
from __future__ import annotations

import csv
import json
import re
import sqlite3
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DB = ROOT / "data" / "db" / "shizhong.db"
CARDS = ROOT / "data" / "cards"
CAND = ROOT / "data" / "candidates"
INST = ROOT / "data" / "institution"
DOCS = ROOT / "docs"

_T2S = {
    "漢": "汉", "書": "书", "後": "后", "國": "国", "吳": "吴", "陽": "阳", "陰": "阴",
    "張": "张", "鄧": "邓", "竇": "窦", "劉": "刘", "陳": "陈", "楊": "杨", "韓": "韩",
    "馬": "马", "許": "许", "鄭": "郑", "蕭": "萧", "顏": "颜", "顧": "顾",
    "華": "华", "萬": "万", "與": "与", "為": "为", "無": "无", "員": "员", "從": "从",
    "來": "来", "開": "开", "關": "关", "門": "门", "內": "内", "宮": "宫", "將": "将",
    "軍": "军", "騎": "骑", "黃": "黄", "鳳": "凤", "龐": "庞", "趙": "赵", "錢": "钱",
    "孫": "孙", "呂": "吕", "嚴": "严", "閻": "阎", "鍾": "钟", "謝": "谢", "蘇": "苏",
    "盧": "卢", "賈": "贾", "衛": "卫", "陸": "陆", "羅": "罗", "賀": "贺", "費": "费",
    "種": "种", "樂": "乐", "於": "于", "靈": "灵", "獻": "献", "懷": "怀", "義": "义",
    "興": "兴", "舉": "举", "薦": "荐", "徵": "征", "監": "监", "僕": "仆", "謁": "谒",
    "給": "给", "諸": "诸", "璽": "玺", "參": "参", "蟬": "蝉", "舊": "旧", "儀": "仪",
    "續": "续", "紀": "纪", "觀": "观", "記": "记", "錄": "录", "釋": "释", "隸": "隶",
    "傳": "传", "誌": "志", "車": "车", "祿": "禄", "勳": "勋", "屬": "属", "職": "职",
    "長": "长", "執": "执", "駙": "驸", "當": "当", "實": "实", "對": "对", "黨": "党",
    "錮": "锢", "亂": "乱", "誅": "诛", "殺": "杀", "敗": "败", "戰": "战", "勝": "胜",
    "還": "还", "遷": "迁", "選": "选", "補": "补", "餘": "余", "歲": "岁", "時": "时",
    "會": "会", "議": "议", "眾": "众", "數": "数", "稱": "称", "讓": "让", "詔": "诏",
    "諡": "谥", "號": "号", "廟": "庙", "顯": "显", "榮": "荣", "寵": "宠", "權": "权",
    "勢": "势", "專": "专", "賢": "贤", "穎": "颖", "潁": "颖", "陽": "阳",
}
SIMPLE = str.maketrans(_T2S)

# 常见姓（用于过滤非人名）
SURNAMES = set(
    "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜戚谢邹喻柏水窦章云苏潘葛奚范彭郎鲁韦昌马苗凤花方俞任袁柳酆鲍史唐费廉岑薛雷贺倪汤滕殷罗毕郝邬安常乐于时傅皮卞齐康伍余元卜顾孟平黄和穆萧尹姚邵湛汪祁毛禹狄米贝明臧计伏成戴谈宋茅庞熊纪舒屈项祝董梁杜阮蓝闵席季麻强贾路娄危江童颜郭梅盛林刁钟徐邱骆高夏蔡田樊胡凌霍虞万支柯昝管卢莫经房裘缪干解应宗丁宣贲邓郁单杭洪包诸左石崔吉钮龚程嵇邢滑裴陆荣翁荀羊於惠甄曲家封芮羿储靳汲邴糜松井段富巫乌焦巴弓牧隗山谷车侯宓蓬全郗班仰秋仲伊宫宁仇栾暴甘钭厉戎祖武符刘景詹束龙叶幸司韶郜黎蓟薄印宿白怀蒲邰从鄂索咸籍赖卓蔺屠蒙池乔阴鬱胥能苍双闻莘党翟谭贡劳逄姬申扶堵冉宰郦雍却璩桑桂濮牛寿通边扈燕冀郏浦尚农温别庄晏柴瞿阎充慕连茹习宦艾鱼容向古易慎戈廖庾终暨居衡步都耿满弘匡国文寇广禄阙东欧殳沃利蔚越夔隆师巩厍聂晁勾敖融訾辛阚那简饶空曾毋沙乜养鞠须丰巢关蒯相查后荆红游竺权逯盖益桓公万俟司马上官欧阳夏侯诸葛闻人东方赫连皇甫尉迟公羊澹台公冶宗政濮阳淳于单于太叔申屠公孙仲孙轩辕令狐钟离宇文长孙慕容司徒司空"
)

# 明显非人名：官职/动词短语/制度词
NOISE_EXACT = {
    "卫尉", "卫尉", "祭酒", "中郎将", "中郎", "再迁", "三迁", "用事", "行服", "不通",
    "举为", "乃拜", "乃引", "允迁", "元以来", "亲省起居", "便蕃左右", "建章监",
    "步兵", "兄子璜", "子张辟强", "子張辟強", "陈祗代允", "陳祗代允", "何晏代毓",
    "代毓", "代允", "淳于恭奏", "祭酒乐松", "祭酒樂松", "常侍中", "侍中用事",
    "光禄大夫", "奉车都尉", "骑都尉", "驸马都尉", "侍中仆射", "给事黄门", "散骑常侍",
    "中常侍", "尚书令", "尚书仆射", "大将军", "车骑将军", "卫将军", "前将军",
    "左将军", "右将军", "后将军", "司空", "司徒", "太尉", "太傅", "太守", "刺史",
    "校尉", "都尉", "郎中", "议郎", "博士", "谒者", "大夫", "仆射", "丞相",
    "御史", "宗正", "大司农", "少府", "光禄勋", "执金吾", "京兆尹", "河南尹",
    "匈奴", "乌桓", "鲜卑", "羌胡", "西域", "南单于", "北单于",
    "侍中", "常侍", "黄门", "尚书", "将军", "列侯", "关内侯", "诸侯", "公主",
    "皇后", "太后", "皇帝", "天子", "陛下", "先帝", "今上", "朕", "孤", "寡人",
    "百官", "公卿", "群臣", "有司", "诸生", "诸将", "诸王", "外戚", "宦官",
    "左右", "前后", "内外", "禁中", "省中", "殿中", "宫中", "府中", "朝中",
    "上书", "上言", "奏事", "议政", "辅政", "执政", "秉政", "用事", "当权",
    "父子", "兄弟", "从父", "从子", "外孙", "女婿", "妻兄", "舅氏",
}


def to_simple(s: str) -> str:
    return (s or "").translate(SIMPLE)


def clean_name(raw: str) -> str:
    s = to_simple(raw).strip()
    s = re.sub(r"[「」『』《》\[\]（）()【】、，。；：？！\s'\"“”·・]", "", s)
    s = s.replace("侯", "")
    for suf in [
        "侍中", "侍中仆射", "侍中驸马都尉", "驸马都尉", "光禄大夫", "奉车都尉",
        "骑都尉", "校尉", "尚书", "太守", "大将军", "将军", "列侯", "关内侯",
        "公", "君", "等", "某", "及", "与", "并", "兼", "为侍中", "拜侍中",
        "侍中祭酒", "祭酒", "中郎将", "中郎", "步兵校尉", "虎贲中郎将",
    ]:
        if s.endswith(suf) and len(s) > len(suf):
            s = s[: -len(suf)]
    # 「子张辟强」→ 可能是「张辟强」
    if s.startswith("子") and len(s) >= 3 and s[1] in SURNAMES:
        s = s[1:]
    s = s.strip("之其于於以而乃则遂因")
    return s


def looks_like_person(name: str) -> bool:
    if not name or len(name) < 2 or len(name) > 3:
        return False
    if name in NOISE_EXACT:
        return False
    if name[0] not in SURNAMES:
        # 仍允许复姓后半或少见姓，但要求第二字也不是纯虚词
        if name[0] not in SURNAMES and len(name) == 2:
            return False
    if re.search(r"[0-9a-zA-Z]", name):
        return False
    if not re.fullmatch(r"[一-鿿]+", name):
        return False
    # 含官制语素则否
    bad_bits = ["侍", "尉", "郎", "将", "军", "书", "令", "守", "史", "大夫", "侯", "帝", "后", "官", "曹", "寺"]
    # 姓后的名可以含这些字（如「霍光」无；「金安上」无）——但「卫尉」整词已排除
    if name in NOISE_EXACT:
        return False
    # 双字且第一字非姓 → 倾向否
    if len(name) == 2 and name[0] not in SURNAMES:
        return False
    return True


PATTERNS = [
    re.compile(r"拜\s*([一-鿿·]{2,4})\s*(?:为|為)?\s*侍中"),
    re.compile(r"([一-鿿·]{2,4})\s*(?:为|為)\s*侍中"),
    re.compile(r"([一-鿿·]{2,4})\s*(?:迁|遷|征拜|徵拜|召拜|补|補|擢|充|选|選)\s*(?:为|為)?\s*侍中"),
    re.compile(r"侍中\s*([一-鿿·]{2,3}?)(?=[，。、；：？！]|等|与|與|及|并|並|上书|上書|言|曰|议|議|奏)"),
    re.compile(r"([一-鿿·]{2,4})(?:以[^。]{0,24})?入?[为為]侍中"),
    re.compile(r"([一-鿿·]{2,3})\s*(?:子|弟子|从子|兄子|弟子)?\s*[，、]?\s*(?:俱|皆|並|并)?\s*侍中"),
]


def extract_names(sentence: str) -> list[str]:
    out, seen = [], set()
    for pat in PATTERNS:
        for m in pat.finditer(sentence):
            n = clean_name(m.group(1))
            if looks_like_person(n) and n not in seen:
                seen.add(n)
                out.append(n)
    return out


def load_roster():
    con = sqlite3.connect(DB)
    rows = con.execute(
        "SELECT id, name, style_name, dynasty, dynasty_primary, n_terms, n_sources FROM person"
    ).fetchall()
    con.close()
    by = {}
    for r in rows:
        by[to_simple(r[1])] = {
            "id": r[0], "name": r[1], "style": r[2], "dynasty": r[3],
            "dynasty_primary": r[4], "n_terms": r[5], "n_sources": r[6],
        }
    return by


def card_names():
    names = set()
    for f in CARDS.glob("*.md"):
        # 文件名 姓名_朝代.md
        stem = f.stem
        if "_" in stem:
            names.add(to_simple(stem.split("_")[0]))
        else:
            names.add(to_simple(stem))
    return names


def scan_corpus():
    quotes = []
    seen = set()
    for p in RAW.rglob("*.txt"):
        if p.name.startswith("."):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if "侍中" not in text:
            continue
        rel = p.relative_to(ROOT)
        parts = rel.parts
        if len(parts) >= 3 and parts[1] == "raw":
            book = parts[2]
            if book == "mirror" and len(parts) >= 4:
                book = parts[3]
            juan = parts[-1][:40]
        else:
            book, juan = p.stem, p.name
        book = to_simple(book)
        # 切句
        t = re.sub(r"\{\{[^}]{0,200}\}\}", " ", text)
        t = re.sub(r"<ref[^>]*>.*?</ref>", " ", t, flags=re.S)
        t = re.sub(r"\s+", "", t)
        for sent in re.split(r"(?<=[。！？；;])", t):
            if "侍中" not in sent or not (10 <= len(sent) <= 350):
                continue
            key = sent[:100]
            if key in seen:
                continue
            seen.add(key)
            names = extract_names(sent)
            quotes.append({"book": book, "juan": juan, "sentence": sent, "names": names, "path": str(rel).replace("\\", "/")})
    return quotes


def main():
    DOCS.mkdir(exist_ok=True)
    roster = load_roster()
    cards = card_names()
    print(f"roster={len(roster)} cards={len(cards)}")

    # 也纳入 institution_review 中「拟补人物」与历史 candidates
    extra_hits = defaultdict(list)
    for path in [
        CAND / "unparsed_namequeue.csv",
        CAND / "anonymous_shizhong.csv",
        CAND / "institution_review.csv",
        CAND / "shizhong_candidates.csv",
    ]:
        if not path.exists():
            continue
        with path.open(encoding="utf-8-sig") as f:
            r = csv.DictReader(f)
            for row in r:
                sent = row.get("sentence") or row.get("句") or ""
                if "侍中" not in sent:
                    continue
                names = extract_names(sent)
                book = row.get("book") or row.get("书") or ""
                juan = row.get("juan") or ""
                for n in names:
                    extra_hits[n].append(
                        {
                            "book": to_simple(book),
                            "juan": juan,
                            "sentence": sent[:200],
                            "path": path.name,
                        }
                    )

    corpus = scan_corpus()
    print(f"corpus 侍中 sentences: {len(corpus)}")
    hits = defaultdict(list)
    for q in corpus:
        for n in q["names"]:
            hits[n].append(q)
    for n, recs in extra_hits.items():
        if n not in hits:
            hits[n] = recs
        else:
            hits[n].extend(recs)

    rows = []
    noise = []
    high = []
    for n, recs in sorted(hits.items(), key=lambda x: (-len(x[1]), x[0])):
        in_db = n in roster
        in_card = n in cards or any(n in c for c in cards)
        explicit = [
            r
            for r in recs
            if re.search(rf"{re.escape(n)}", r["sentence"])
            and re.search(r"(拜|迁|遷|征拜|徵拜|召拜|为|為|入为|入為|补|補|擢|充|俱|皆|並|并).{0,8}侍中|侍中", r["sentence"])
        ]
        # 更严：句子中「名 + 任职动词 + 侍中」或「拜/迁 名 侍中」
        strong = []
        for r in recs:
            s = r["sentence"]
            if re.search(rf"(拜|迁|遷|征拜|徵拜|召拜|补|補|擢|充|選|选|署)\s*{re.escape(n)}\s*(为|為)?\s*侍中", s):
                strong.append(r)
            elif re.search(rf"{re.escape(n)}\s*(为|為|迁|遷|征拜|徵拜|补|補)\s*(为|為)?\s*侍中", s):
                strong.append(r)
            elif re.search(rf"侍中\s*{re.escape(n)}", s) and n[0] in SURNAMES:
                strong.append(r)

        if not in_db and not in_card:
            if not looks_like_person(n) or (not strong and len(recs) < 2):
                noise.append(
                    {
                        "name": n, "hits": len(recs), "strong": len(strong),
                        "sample": recs[0]["sentence"][:100] if recs else "",
                        "book": recs[0]["book"] if recs else "",
                    }
                )
                continue
            row = {
                "name_simple": n,
                "status": "拟补_待审",
                "in_db": "N",
                "in_card": "N",
                "person_id": "",
                "dynasty_db": "",
                "hits": len(recs),
                "strong": len(strong),
                "sample_book": (strong or recs)[0]["book"],
                "sample_juan": (strong or recs)[0]["juan"],
                "sample_sentence": (strong or recs)[0]["sentence"][:200],
                "all_books": ";".join(sorted({r["book"] for r in recs})[:6]),
            }
            rows.append(row)
            if strong:
                high.append(row)
        else:
            # 已在库：检查是否可能缺出处（strong 句是否已引用无法直接比，仅列出）
            approx = roster.get(n) or {}
            rows.append(
                {
                    "name_simple": n,
                    "status": "已在库",
                    "in_db": "Y" if in_db else "N",
                    "in_card": "Y" if in_card else "N",
                    "person_id": approx.get("id", ""),
                    "dynasty_db": approx.get("dynasty", ""),
                    "hits": len(recs),
                    "strong": len(strong),
                    "sample_book": recs[0]["book"] if recs else "",
                    "sample_juan": recs[0]["juan"] if recs else "",
                    "sample_sentence": recs[0]["sentence"][:200] if recs else "",
                    "all_books": ";".join(sorted({r["book"] for r in recs})[:6]),
                }
            )

    fields = [
        "name_simple", "status", "in_db", "in_card", "person_id", "dynasty_db",
        "hits", "strong", "sample_book", "sample_juan", "sample_sentence", "all_books",
    ]
    out = CAND / "roster_gap_v2.csv"
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    with (CAND / "roster_gap_noise.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["name", "hits", "strong", "sample", "book"])
        w.writeheader()
        w.writerows(noise)

    # 人读报告
    high_sorted = sorted(high, key=lambda r: -r["strong"])
    lines = [
        "# 侍中名录核对报告（制度史料交叉）",
        "",
        f"- 库内人物：{len(roster)}",
        f"- 语料含「侍中」句（去重后扫描）：{len(corpus)}",
        f"- 抽出候选名：{len(rows)}（已在库 + 拟补）",
        f"- 高置信拟补（strong≥1 且不在库/卡）：{len(high_sorted)}",
        f"- 噪声剔除：{len(noise)}（见 roster_gap_noise.csv）",
        "",
        "## 高置信拟补（建议优先人工审定）",
        "",
        "| 姓名 | strong | hits | 样例出处 | 样例句 |",
        "|------|--------|------|----------|--------|",
    ]
    for r in high_sorted[:80]:
        sent = r["sample_sentence"].replace("|", "｜")[:80]
        lines.append(
            f"| {r['name_simple']} | {r['strong']} | {r['hits']} | {r['sample_book']} {r['sample_juan']} | {sent} |"
        )
    lines += [
        "",
        "## 说明",
        "",
        "1. 自动抽取只产出候选，**不直接建正式卡片**（与 CLAUDE.md 数据原则一致）。",
        "2. `strong` 表示句中出现「拜/迁/为…侍中」等较明确任职结构。",
        "3. 已在库人物若本表出现，可对照样例句检查是否需补 source。",
        "4. 制度条（无名）请进制度沿革页，不建人卡。",
        "",
        "## 文件",
        "",
        "- `data/candidates/roster_gap_v2.csv`",
        "- `data/candidates/roster_gap_noise.csv`",
        "- `data/institution/institution.json`",
        "",
    ]
    report = DOCS / "roster_gap_report.md"
    report.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out} rows={len(rows)} high={len(high_sorted)} noise={len(noise)}")
    print(f"report {report}")
    for r in high_sorted[:40]:
        print(f"  HIGH {r['name_simple']} s={r['strong']} h={r['hits']} {r['sample_book']} | {r['sample_sentence'][:70]}")


if __name__ == "__main__":
    main()
