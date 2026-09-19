"""从 data/raw 抽取侍中制度史料句 + 名录核对候选。

输出:
  data/institution/raw_quotes.json     全量含「侍中」句（含制度启发式标注）
  data/institution/institution.json    制度沿革页数据（按演变阶段编排）
  data/candidates/roster_gap_audit.csv 名录对照：制度/传记句中人名 vs person 表
  data/candidates/institution_review.csv 待人工审定的制度条与拟补名录
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
OUT_INST = ROOT / "data" / "institution"
OUT_CAND = ROOT / "data" / "candidates"
CARDS = ROOT / "data" / "cards"

# 简繁与异体（姓名核对用；单字映射）
_T2S = {
    "漢": "汉", "書": "书", "後": "后", "國": "国",
    "吳": "吴", "陽": "阳", "陰": "阴", "張": "张",
    "鄧": "邓", "竃": "窦", "劉": "刘", "陳": "陈",
    "楊": "杨", "韓": "韩", "馬": "马", "許": "许",
    "鄭": "郑", "蕭": "萧", "顏": "颜", "顧": "顾",
    "華": "华", "萬": "万", "與": "与", "為": "为",
    "無": "无", "員": "员", "從": "从", "來": "来",
    "開": "开", "關": "关", "門": "门", "內": "内",
    "宮": "宫", "將": "将", "軍": "军", "騎": "骑",
    "黃": "黄", "鳳": "凤", "龐": "庞", "趙": "赵",
    "錢": "钱", "孫": "孙", "呂": "吕", "嚴": "严",
    "閻": "阎", "鐘": "钟", "謝": "谢", "蘇": "苏",
    "盧": "卢", "賈": "贾", "衛": "卫", "陸": "陆",
    "羅": "罗", "賊": "贺", "費": "费", "種": "种",
    "樂": "乐", "於": "于", "靈": "灵", "獻": "献",
    "懷": "怀", "義": "义", "興": "兴", "舉": "举",
    "薦": "荐", "徵": "征", "監": "监", "僕": "仆",
    "諄": "谒", "給": "给", "諸": "诸", "璽": "玺",
    "劒": "剑", "劍": "剑", "參": "参", "舊": "旧",
    "儀": "仪", "續": "续", "紀": "纪", "觀": "观",
    "記": "记", "錄": "录", "釋": "释", "隸": "隶",
    "辭": "辞", "說": "说", "論": "论", "議": "议",
    "詮": "诏", "傳": "传", "誌": "志", "廟": "庙",
    "禮": "礼", "車": "车", "祿": "禄", "勳": "勋",
    "屬": "属", "職": "职", "綝": "绥", "臺": "台",
    "閣": "阁", "長": "长", "執": "执", "駙": "驾",
    "驂": "骖", "衞": "卫", "當": "当", "實": "实",
    "對": "对", "點": "点", "黨": "党", "錮": "锩",
    "禍": "祸", "亂": "乱", "諤": "诛", "殺": "杀",
    "敗": "败", "戰": "战", "勝": "胜", "還": "还",
    "遷": "迁", "選": "选", "補": "补", "餘": "余",
    "歲": "岁", "時": "时", "會": "会", "眾": "众",
    "數": "数", "稱": "称", "讓": "让", "號": "号",
    "顯": "显", "榮": "荣", "獵": "宠", "權": "权",
    "勢": "势", "專": "专", "賢": "贤",
}
SIMPLE = str.maketrans(_T2S)


def to_simple(s: str) -> str:
    if not s:
        return s
    return s.translate(SIMPLE)


# 制度关键词启发式
INST_KEYS = [
    "秩", "加官", "禁中", "无员", "無員", "亡员", "亡員", "员各", "員各",
    "百官表", "百官志", "百官公卿", "汉官", "漢官", "独断", "獨斷",
    "汉旧仪", "漢舊儀", "汉官仪", "漢官儀", "周官", "丞相史",
    "貂蝉", "貂蟬", "负玺", "負璽", "参乘", "驂乘", "參乘",
    "唾壶", "唾壺", "侍中寺", "职掌", "職掌", "位次", "印绶", "印綬",
    "服制", "冠制", "出入禁", "得入禁", "更直", "宿卫", "宿衞",
    "待诏", "待詔", "顾问", "顧問", "近臣", "省官", "属官", "屬官",
    "少府", "无定员", "無定員", "本秦", "秦官", "皆加官", "所加或",
    "左右曹", "散骑", "散騎", "中常侍", "给事黄门", "給事黃門",
    "献帝", "獻帝", "定员", "定員", "六人", "佩玺", "佩璽",
    "抱剑", "抱劒", "抱劍", "称制", "稱制", "殿下", "朝会", "朝會",
    "位序", "典制度", "掌御", "掌御坐",
]

PAT_BAI = re.compile(r"拜\s*([\w·]{1,8})\s*(?:为|為)?\s*侍中")
PAT_WEI = re.compile(r"([\w·]{1,8})\s*(?:为|為)\s*侍中")
PAT_NAME_SZ = re.compile(r"侍中\s*([\w·]{1,4}?)(?=[，。、；：？！\s]|等|与|與|及|并|並|上书|上書|言|曰|议|議)")
PAT_YI = re.compile(r"([\w·]{1,8})(?:等)?(?:以|以)?(?:公车|公車)?[^。]{0,6}入为侍中|入為侍中")

STOP = {
    "侍中", "中常侍", "给事黄门", "給事黃門", "散骑", "散騎", "左右曹", "诸吏", "諸吏",
    "尚书", "尚書", "博士", "郎中", "大夫", "将军", "將軍", "列侯", "列候", "卿大夫",
    "都尉", "太医", "太醫", "太官", "令", "丞", "仆射", "僕射", "驸马都尉", "駙馬都尉",
    "光禄大夫", "光祿大夫", "奉车都尉", "奉車都尉", "骑都尉", "騎都尉", "校尉", "谒者", "謁者",
    "百官", "公卿", "朝廷", "天子", "陛下", "先帝", "今上", "上", "帝", "王", "侯", "君",
    "臣", "某", "等", "诸", "諸", "皆", "以", "为", "為", "拜", "迁", "遷", "征", "徵",
    "召", "出", "入", "兼", "领", "領", "录", "錄", "典", "掌", "知", "监", "監", "护", "護",
    "侍", "中", "官", "职", "職", "事", "曹", "寺", "省", "台", "臺", "阁", "閣", "府", "第",
    "舍", "内", "內", "外", "禁", "殿", "宫", "宮", "门", "門", "省中", "禁中", "左右",
    "前后", "前後", "父子", "兄弟", "群臣", "羣臣", "百僚", "有司", "诸曹", "諸曹",
    "尚书令", "尚書令", "尚书仆射", "尚書僕射", "黄门", "黃門", "常侍", "宦官", "外戚",
    "太后", "皇后", "太子", "诸王", "諸王", "公主", "驸马", "駙馬", "加官", "亡员", "亡員",
    "无员", "無員", "秩比", "二千石", "千石", "六百石", "比二千石",
}

PHASES = [
    {"id": "origin", "title": "渊源与名义", "range": "先秦—秦",
     "summary": "侍中名义的旧说与秦制渊源：或云周官常伯，或云本秦丞相史，往来殿中故名。",
     "themes": ["名义", "秦制", "近侍起源"]},
    {"id": "xihan_addition", "title": "西汉：加官与入禁", "range": "高祖—景帝",
     "summary": "西汉初侍中为加官，与左右曹、诸吏、散骑、中常侍并列；得入禁中，「亡员」而亲近。",
     "themes": ["加官", "禁中", "亡员"]},
    {"id": "wudi_expansion", "title": "武帝前后：职掌扩展", "range": "武帝—昭宣",
     "summary": "近臣职掌具体化：儒者掌唾壶、驸马都尉兼侍中、参与机密与讨逆；侍中成为外戚/降人/近幸重要进身。",
     "themes": ["职掌", "驸马都尉", "近臣"]},
    {"id": "chengai_mingjing", "title": "成哀：明经充侍中", "range": "成帝—哀帝",
     "summary": "取明经者充侍中，参议可正为止殿，行则负玺；文化—顾问色彩上升。",
     "themes": ["明经", "负玺", "顾问"]},
    {"id": "wangmang", "title": "新莽更始：制度波动", "range": "新—更始",
     "summary": "莽时禁中出入制度变动；更始政权短暂延续汉官名号。",
     "themes": ["新莽", "更始", "出入禁中"]},
    {"id": "donghan_bureau", "title": "东汉：少府属官化", "range": "光武—明章",
     "summary": "侍中隶少府，秩比二千石（异说千石），无员；服制貂蝉、侍中寺等制度记述增多。",
     "themes": ["少府", "秩比", "无员", "侍中寺", "服制"]},
    {"id": "donghan_mid", "title": "东汉中期：外戚近侍与录尚书", "range": "和帝—质帝",
     "summary": "外戚以侍中居禁中、掌机要，与录尚书事体制交织；侍中成为权力网络关键节点。",
     "themes": ["外戚", "录尚书", "禁中"]},
    {"id": "donghan_late", "title": "东汉后期：士人侍中与中常侍分野", "range": "桓灵—献帝",
     "summary": "宦官中常侍与士人侍中并行；献帝时定侍中、给事黄门侍郎员各六人，员额制度化。",
     "themes": ["中常侍", "士人", "定员", "献帝"]},
    {"id": "hanwei", "title": "汉魏之际：侍中典制度", "range": "建安—黄初",
     "summary": "魏国既建，拜侍中与王粲等典制度；侍中从近臣进一步走向制度—顾问中枢，并延续至蜀吴。",
     "themes": ["魏国", "典制度", "蜀吴", "汉制衔接"]},
]


def norm_name(s: str) -> str:
    s = to_simple(s or "").strip()
    s = re.sub(r"[「」『』《》\[\]（）()【】、，。；：？！\s'\"“”]", "", s)
    s = s.replace("侯", "")  # 偶发「侍中某侯」
    # 去掉官职尾巴
    for suf in [
        "侍中",
        "侍中仆射",
        "侍中驸马都尉",
        "驸马都尉",
        "光禄大夫",
        "奉车都尉",
        "骑都尉",
        "校尉",
        "尚书",
        "太守",
        "大将军",
        "将军",
        "列侯",
        "关内侯",
        "关内侯",
        "侯",
        "公",
        "君",
        "等",
        "某",
        "及",
        "与",
        "并",
        "兼",
        "为侍中",
        "拜侍中",
    ]:
        if s.endswith(suf) and len(s) > len(suf):
            s = s[: -len(suf)]
    s = s.strip("之其于於以而")
    return s


def is_valid_name(name: str) -> bool:
    if not name or len(name) < 2 or len(name) > 4:
        return False
    if name in STOP:
        return False
    if re.fullmatch(r"[0-9a-zA-Z]+", name):
        return False
    # 纯官制词
    if any(k in name for k in ["侍中", "常侍", "黄门", "黃門", "尚书", "尚書", "将军", "將軍", "都尉", "大夫", "仆射", "僕射"]):
        return False
    if re.search(r"[0-9]", name):
        return False
    # 必须基本是汉字
    if not re.fullmatch(r"[一-鿿·]+", name):
        return False
    return True


def extract_names(sentence: str) -> list[str]:
    names = []
    for pat in (PAT_BAI, PAT_WEI, PAT_NAME_SZ, PAT_YI):
        for m in pat.finditer(sentence):
            n = norm_name(m.group(1))
            if is_valid_name(n):
                names.append(n)
    # 「史丹为侍中」「李郃以公车司马入为侍中」
    m = re.search(r"([一-鿿]{2,4})(?:以[^。]{0,20})?入?[为為]侍中", sentence)
    if m:
        n = norm_name(m.group(1))
        if is_valid_name(n) and n not in names:
            names.append(n)
    # 去重保序
    out, seen = [], set()
    for n in names:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def classify(sentence: str) -> str:
    s = sentence
    inst_hit = any(k in s for k in INST_KEYS)
    # 纯员额/官制连称
    pure_inst = bool(
        re.search(r"(皆加官|无员|無員|亡员|亡員|秩[比千二]|少府属|少府屬|侍中寺|汉官|漢官|独断|獨斷|百官公卿表|百官志)", s)
        or re.search(r"侍中[、，].{0,20}(散骑|散騎|中常侍|左右曹|给事|給事)", s)
        or re.search(r"(凡|凡侍中).{0,30}皆加官", s)
    )
    has_name = bool(extract_names(s))
    if pure_inst and not has_name:
        return "制度"
    if inst_hit and has_name:
        return "制度+人物"
    if has_name:
        return "人物"
    if inst_hit:
        return "制度待核"
    return "一般含侍中"


def guess_phase(sentence: str, book: str, juan: str) -> str:
    s = sentence
    blob = f"{book} {juan} {s}"
    if any(k in s for k in ["周官", "常伯", "丞相史", "本秦", "秦官", "秦始皇"]):
        return "origin"
    if any(k in s for k in ["皆加官", "左右曹", "得入禁中", "亡员", "亡員", "所加或"]):
        return "xihan_addition"
    if any(k in s for k in ["孔安国", "孔安國", "唾壶", "唾壺", "莽何罗", "莽何羅", "金日磾", "驸马都尉", "駙馬都尉", "武帝"]):
        return "wudi_expansion"
    if any(k in s for k in ["明经", "明經", "负玺", "負璽", "成帝", "哀帝"]):
        return "chengai_mingjing"
    if any(k in s for k in ["王莽", "新莽", "更始", "莽时", "莽時"]):
        return "wangmang"
    if any(k in s for k in ["少府", "比二千石", "秩千石", "侍中寺", "貂蝉", "貂蟬", "光武", "世祖", "中兴", "中興"]):
        return "donghan_bureau"
    if any(k in s for k in ["窦宪", "竇憲", "录尚书", "錄尚書", "和帝", "梁冀", "邓骘", "鄧騭"]):
        return "donghan_mid"
    if any(k in s for k in ["中常侍", "献帝", "獻帝", "员各六人", "員各六人", "桓帝", "灵帝", "靈帝", "党锢", "黨錮"]):
        return "donghan_late"
    if any(k in s for k in ["魏国", "魏國", "典制度", "黄初", "黃初", "曹操", "汉魏", "漢魏", "蜀", "吴", "吳"]) or book in (
        "三國志",
        "三国志",
    ):
        return "hanwei"
    if book in ("史記", "史记") or "漢書" in book or "汉书" in book:
        return "xihan_addition"
    if any(x in book for x in ["後漢書", "后汉书", "後漢紀", "后汉纪", "東觀", "东观", "全後漢文", "全后汉文"]):
        return "donghan_bureau"
    return "donghan_bureau"


def iter_raw_files():
    skip_parts = {"books", "china-history", "mirror"}
    # mirror 也扫：前四史章节本与 wiki 互补，但去重时按句文本
    for p in RAW.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in {".txt", ".wikitext", ".md"}:
            continue
        if p.name.startswith("."):
            continue
        # 跳过纯目录镜像中的重复？仍扫 mirror 以便补缺
        if "vendors" in p.parts:
            continue
        yield p


def book_of(path: Path) -> tuple[str, str]:
    rel = path.relative_to(RAW)
    parts = rel.parts
    if len(parts) >= 2:
        book = parts[0]
        if book == "mirror" and len(parts) >= 3:
            book = parts[1]
            juan = parts[-1]
        else:
            juan = parts[-1]
    else:
        book = path.stem
        juan = path.name
    juan = re.sub(r"\.(txt|wikitext|md)$", "", juan, flags=re.I)
    return to_simple(book), juan


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\{\{[^}]{0,200}\}\}", " ", text)
    text = re.sub(r"<ref[^>]*>.*?</ref>", " ", text, flags=re.S)
    text = re.sub(r"<ref[^/]*/>", " ", text)
    text = re.sub(r"\[\[[^\]|]+\|([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"'''?", "", text)
    text = re.sub(r"={2,}", "\n", text)
    text = text.replace("\r", "\n")
    # 保留含侍中的窗口
    parts = re.split(r"(?<=[。！？；;])", text)
    out = []
    for s in parts:
        s = s.strip()
        if "侍中" in s or "侍中" in s:
            s2 = re.sub(r"\s+", "", s)
            if "侍中" in s2 and 8 <= len(s2) <= 400:
                out.append(s2)
    return out


def load_roster():
    con = sqlite3.connect(DB)
    rows = con.execute(
        "SELECT id, name, dynasty, dynasty_primary, n_terms, n_sources FROM person"
    ).fetchall()
    con.close()
    by_simple = {}
    for r in rows:
        n = to_simple(r[1])
        by_simple[n] = {"id": r[0], "name": r[1], "dynasty": r[2], "dynasty_primary": r[3], "n_terms": r[4], "n_sources": r[5]}
    return by_simple


def main():
    OUT_INST.mkdir(parents=True, exist_ok=True)
    OUT_CAND.mkdir(parents=True, exist_ok=True)
    roster = load_roster()

    seen_sent = set()
    quotes = []
    name_hits = defaultdict(list)  # simple_name -> list of quote idx/meta

    files = list(iter_raw_files())
    print(f"scanning {len(files)} files")
    for p in files:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if "侍中" not in text:
            continue
        book, juan = book_of(p)
        for sent in split_sentences(text):
            key = sent[:120]
            if key in seen_sent:
                continue
            seen_sent.add(key)
            kind = classify(sent)
            names = extract_names(sent)
            phase = guess_phase(sent, book, juan)
            rec = {
                "book": book,
                "juan": juan,
                "path": str(p.relative_to(ROOT)).replace("\\", "/"),
                "sentence": sent,
                "kind": kind,
                "phase": phase,
                "names": names,
            }
            quotes.append(rec)
            for n in names:
                name_hits[n].append(rec)

    print(f"unique 侍中 sentences: {len(quotes)}")
    by_kind = defaultdict(int)
    for q in quotes:
        by_kind[q["kind"]] += 1
    print("by kind", dict(by_kind))

    # 制度句（含制度+人物、制度待核）
    inst_quotes = [q for q in quotes if q["kind"].startswith("制度")]
    person_quotes = [q for q in quotes if q["kind"] in ("人物", "制度+人物")]

    # 按阶段编排制度页
    phase_map = {ph["id"]: ph for ph in PHASES}
    for ph in PHASES:
        ph["quotes"] = []
    for q in inst_quotes + [x for x in person_quotes if any(k in x["sentence"] for k in INST_KEYS)]:
        ph = phase_map.get(q["phase"], phase_map["donghan_bureau"])
        if len(ph["quotes"]) < 40:
            # 控制体量，优先制度+人物 / 短而关键
            score = 0
            if q["kind"] == "制度":
                score += 3
            if q["kind"] == "制度+人物":
                score += 2
            if any(k in q["sentence"] for k in ["秩", "加官", "禁中", "负玺", "明经", "侍中寺", "貂蝉", "貂蟬", "少府", "典制度", "员各", "員各"]):
                score += 2
            if len(q["sentence"]) < 80:
                score += 1
            q2 = dict(q)
            q2["score"] = score
            ph["quotes"].append(q2)
    for ph in PHASES:
        ph["quotes"].sort(key=lambda x: (-x.get("score", 0), len(x["sentence"])))
        # 去掉 score 字段输出时再处理
        ph["quote_count"] = len(ph["quotes"])

    institution = {
        "title": "侍中制度沿革",
        "subtitle": "两汉侍中职官制度史料编年梳理",
        "updated": "2026-09",
        "note": "语料来自项目 data/raw（前四史、两汉纪、东观、全汉文/全后汉文、金石辑本）。制度条与人物任职条分列；推断不得写成确定。",
        "phases": [
            {
                "id": ph["id"],
                "title": ph["title"],
                "range": ph["range"],
                "summary": ph["summary"],
                "themes": ph["themes"],
                "quotes": [
                    {
                        "book": q["book"],
                        "juan": q["juan"],
                        "sentence": q["sentence"],
                        "kind": q["kind"],
                        "names": q["names"],
                        "path": q["path"],
                    }
                    for q in ph["quotes"][:36]
                ],
                "quote_count": ph["quote_count"],
            }
            for ph in PHASES
        ],
        "stats": {
            "sentences_total": len(quotes),
            "institution_flavored": len(inst_quotes),
            "person_flavored": len(person_quotes),
            "by_kind": dict(by_kind),
            "by_phase": {ph["id"]: ph["quote_count"] for ph in PHASES},
            "roster_size": len(roster),
        },
        "sources_note": [
            "《汉书·百官公卿表》《后汉书》百官志 — 正史职官主干",
            "《全后汉文》卷三十四等 — 严可均辑应劭《汉官仪》及汉官类佚文",
            "《史记》《汉书》《后汉书》《三国志》列传注 — 人物任职与制度夹注",
            "《前汉纪》《后汉纪》《东观汉记》及金石辑本 — 编年与石刻旁证",
        ],
    }

    # 全量 raw_quotes
    raw_payload = {
        "count": len(quotes),
        "by_kind": dict(by_kind),
        "quotes": quotes,
    }

    (OUT_INST / "raw_quotes.json").write_text(
        json.dumps(raw_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT_INST / "institution.json").write_text(
        json.dumps(institution, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("wrote institution.json phases:", [(p["id"], p["quote_count"]) for p in institution["phases"]])

    # 名录核对
    gap_rows = []
    missing_names = []
    present_with_new_quote = []
    for n, recs in sorted(name_hits.items(), key=lambda x: (-len(x[1]), x[0])):
        in_db = n in roster
        # 也查卡片文件
        card_hit = any(to_simple(f.name).startswith(n) for f in CARDS.glob("*.md"))
        # 近似：库中是否存在包含关系
        approx = [rn for rn in roster if n in rn or rn in n] if not in_db else []
        primary = recs[0]
        # 任职明文线索
        explicit = [
            r
            for r in recs
            if re.search(r"(拜|迁|遷|征拜|徵拜|召拜|为|為|入为|入為|补|補|位至|位次).{0,6}侍中", r["sentence"])
            or re.search(r"侍中", r["sentence"])
            and re.search(rf"{re.escape(n)}", r["sentence"])
        ]
        row = {
            "name_simple": n,
            "in_db": "Y" if in_db else "N",
            "card": "Y" if card_hit else "N",
            "approx_in_db": ";".join(approx[:5]),
            "hit_count": len(recs),
            "explicit_count": len(explicit),
            "dynasty_db": roster[n]["dynasty"] if in_db else "",
            "person_id": roster[n]["id"] if in_db else "",
            "sample_book": primary["book"],
            "sample_juan": primary["juan"],
            "sample_sentence": primary["sentence"][:180],
            "phase": primary["phase"],
            "kinds": ";".join(sorted({r["kind"] for r in recs})),
        }
        gap_rows.append(row)
        if not in_db and not card_hit:
            if len(explicit) >= 1 and is_valid_name(n) and n not in STOP:
                missing_names.append(row)
        elif in_db:
            # 已有库，可核是否缺出处
            if len(recs) >= 1:
                present_with_new_quote.append(row)

    gap_rows.sort(key=lambda r: (r["in_db"], -r["explicit_count"], -r["hit_count"]))
    gap_path = OUT_CAND / "roster_gap_audit.csv"
    fields = list(gap_rows[0].keys()) if gap_rows else [
        "name_simple",
        "in_db",
        "card",
        "approx_in_db",
        "hit_count",
        "explicit_count",
        "dynasty_db",
        "person_id",
        "sample_book",
        "sample_juan",
        "sample_sentence",
        "phase",
        "kinds",
    ]
    with gap_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(gap_rows)

    # 审定表：缺名 + 制度条
    review_path = OUT_CAND / "institution_review.csv"
    review_fields = [
        "category",
        "name",
        "in_db",
        "book",
        "juan",
        "sentence",
        "phase",
        "kind",
        "action_hint",
        "path",
    ]
    review = []
    for r in missing_names:
        review.append(
            {
                "category": "拟补人物",
                "name": r["name_simple"],
                "in_db": r["in_db"],
                "book": r["sample_book"],
                "juan": r["sample_juan"],
                "sentence": r["sample_sentence"],
                "phase": r["phase"],
                "kind": r["kinds"],
                "action_hint": "核查是否史有明文任侍中；确认则建卡（勿自动定稿）",
                "path": "",
            }
        )
    # 制度核心句（score 高）
    for ph in PHASES:
        for q in ph["quotes"][:12]:
            review.append(
                {
                    "category": "制度沿革",
                    "name": ";".join(q["names"]),
                    "in_db": "",
                    "book": q["book"],
                    "juan": q["juan"],
                    "sentence": q["sentence"][:220],
                    "phase": ph["id"],
                    "kind": q["kind"],
                    "action_hint": "纳入制度沿革页；若含人名再核名录",
                    "path": q["path"],
                }
            )
    with review_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=review_fields)
        w.writeheader()
        w.writerows(review)

    print(f"gap audit rows: {len(gap_rows)} -> {gap_path}")
    print(f"missing candidate names: {len(missing_names)}")
    print(f"review rows: {len(review)} -> {review_path}")
    # 打印前 30 缺名
    for r in missing_names[:30]:
        print(f"  MISS {r['name_simple']} hits={r['hit_count']} ex={r['explicit_count']} {r['sample_book']} {r['sample_juan']} | {r['sample_sentence'][:60]}")


if __name__ == "__main__":
    main()
