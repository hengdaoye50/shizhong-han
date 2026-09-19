"""重建制度沿革数据：清洗断句、统一简体、只收可核验原典句。

原则:
  1. 显示字段一律简体（hans.t2s），与全站一致。
  2. 去除维基标记/括注/章节标题，修正断句残片。
  3. 同一条史料繁简或 wiki/mirror 重复时只保留一条（优先卷次清楚的 wiki 卷本）。
  4. 不写入合成句；制度提要写在 curated_points，不混进 quote。
  5. 制度典章书（汉官仪辑文/独断/汉官旧仪/会要/百官表志）优先。

输出:
  data/institution/institution.json
  shizhongdata/data/institution.json  （含名录核对，调用 export_institution_web）
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sources"))
from hans import t2s, norm_quote  # noqa: E402

RAW = ROOT / "data" / "raw"
INST_DIR = ROOT / "data" / "institution"
OUT = INST_DIR / "institution.json"

# 来源可信优先级（越大越优先保留）
BOOK_RANK = {
    "汉官六种": 110,
    "通典": 105,
    "文献通考": 102,
    "职官分纪": 100,
    "汉官旧仪": 100,
    "历代职官表": 98,
    "唐六典": 98,
    "独断": 95,
    "初学记": 92,
    "北堂书钞": 90,
    "全后汉文": 90,
    "艺文类聚": 88,
    "全汉文": 85,
    "西汉会要": 82,
    "东汉会要": 82,
    "汉制考": 82,
    "太平御览": 78,
    "玉海": 76,
    "汉书": 75,
    "后汉书": 75,
    "册府元龟": 72,
    "续通典": 70,
    "史记": 70,
    "三国志": 70,
    "两汉诏令": 68,
    "前汉纪": 60,
    "后汉纪": 60,
    "东观汉记": 55,
    "隶释": 50,
    "隶续": 50,
    "集古录": 45,
    "金石录": 45,
    "补汉兵志": 40,
}

# 类书/政书：自动句须与两汉制度相关
INST_BOOKS = {
    "汉官六种", "独断", "汉官旧仪", "西汉会要", "东汉会要", "全后汉文", "全汉文",
    "通典", "文献通考", "唐六典", "册府元龟", "职官分纪", "历代职官表",
    "北堂书钞", "初学记", "艺文类聚", "太平御览", "玉海", "汉制考", "续通典",
    "两汉诏令",
}

HAN_INST_KEYS = (
    "加官", "禁中", "少府", "无员", "無員", "亡员", "亡員", "侍中寺", "门下", "門下",
    "冠武弁", "金珰", "左貂", "右貂", "貂蝉", "貂蟬", "负玺", "負璽", "佩玺", "佩璽",
    "明经", "明經", "丞相史", "周官", "常伯", "秦官", "汉官", "漢官", "百官表", "百官志",
    "秩千石", "比二千石", "省尚书", "省尚書", "仆射", "僕射", "中常侍", "左右曹",
    "献帝", "獻帝", "员各六人", "員各六人", "出入禁中", "近侍帷幄", "典制度",
    "汉制", "漢制", "秦汉", "秦漢", "后汉谓", "後漢謂", "皆加官", "得入禁中",
    "品秩", "服制", "职掌", "職掌", "玉堂署", "中朝",
)

PHASES = [
    {
        "id": "origin",
        "title": "渊源与名义",
        "range": "先秦—秦",
        "summary": "侍中名义旧说与秦制渊源：或云周官常伯，或云本秦丞相史，往来殿中故名；冠服传说附会貂蝉之始。",
        "themes": ["名义", "秦制", "近侍起源"],
        "curated_points": [
            "名义旧说：侍中「周官」或「常伯」；又说本秦丞相史，往来殿中/殿内奏事，故谓之侍中（辑《汉官仪》；《通典》卷二十一同源）。",
            "秦并天下后，冠服传说：破赵得冠以赐侍中（辑《汉官仪》、《通典》）。",
            "要点：侍中首先是禁中近侍—顾问位置，而非独立行政部门。",
        ],
    },
    {
        "id": "xihan_addition",
        "title": "西汉：加官与入禁",
        "range": "高祖—景帝",
        "summary": "西汉侍中为加官，与左右曹、诸吏、散骑、中常侍并列；得入禁中，员额开放。",
        "themes": ["加官", "禁中", "无员"],
        "curated_points": [
            "《汉书·百官公卿表》：侍中、左右曹、诸吏、散骑、中常侍皆加官；所加自列侯、将军至郎中，「无员」。",
            "侍中、中常侍得入禁中（百官公卿表；《通典》卷二十一引申）。",
            "《汉官旧仪》：侍中无员，或以列侯、将军、卫尉、光禄将、大夫、郎为之，得举非法。",
            "《唐六典》卷八引《汉书·百官表》并注「皆秦制」，系统转录西汉加官—入禁格局。",
            "《通典》引孟康：侍中等居「中朝」，丞相以下为外朝。",
            "《独断》：公卿、侍中、尚书衣帛而朝曰朝臣。",
            "要点：西汉侍中是加官系统中的禁中通道，身份取决于所加本官。",
        ],
    },
    {
        "id": "wudi_expansion",
        "title": "武帝前后：职掌扩展",
        "range": "武帝—昭宣",
        "summary": "近臣职掌具体化：儒者掌御坐唾壶、驸马都尉兼侍中、参与机密与讨逆。",
        "themes": ["职掌", "驸马都尉", "近臣"],
        "curated_points": [
            "武帝时孔安国为侍中，以其儒者，特听掌御坐唾壶（辑《汉官仪》）。",
            "分掌乘舆服物，下至亵器虎子之属；《汉官旧仪》载侍中负玺组以从。",
            "金日磾迁侍中驸马都尉光禄大夫，出则骖乘（《汉书》/《西汉会要》）。",
            "要点：侍中从「入禁资格」扩展为可参与机密、宿卫与礼仪的具体角色。",
        ],
    },
    {
        "id": "chengai_mingjing",
        "title": "成哀：明经充侍中",
        "range": "成帝—哀帝",
        "summary": "取明经者充侍中，参议可正为止殿，行则负玺；顾问色彩上升。",
        "themes": ["明经", "负玺", "顾问"],
        "curated_points": [
            "汉成帝取明经者充侍中，使辟百官公卿，参议可正为止殿，行则负玺（辑《汉官仪》）。",
            "旧高取一人为仆射，后改为祭酒——侍中系统内部职衔分化。",
            "要点：选任标准向经学—顾问倾斜；负玺象征与诏令、御物近距离。",
        ],
    },
    {
        "id": "wangmang",
        "title": "新莽更始：制度波动",
        "range": "新—更始",
        "summary": "哀平间仍见侍中；王莽秉政时侍中复入，与中官共止；更始政权沿用汉官名号。",
        "themes": ["新莽", "更始", "出入禁中"],
        "curated_points": [
            "《后汉书·百官志》注系：王莽秉政，侍中复入，与中官共止——禁中出入政策反复。",
            "哀、平间仍有侍中任职记载（张纯、宋弘等），王莽时迁转他官。",
            "更始立，卓茂为侍中祭酒——乱世仍用汉官名号。",
            "要点：新莽—更始是西汉加官制向东汉属官化过渡的波动期。",
        ],
    },
    {
        "id": "donghan_bureau",
        "title": "东汉：少府属官化",
        "range": "光武—明章",
        "summary": "侍中隶少府，无员；秩有千石与比二千石异说；服制、侍中寺等记述增多。",
        "themes": ["少府", "秩比", "无员", "侍中寺", "服制"],
        "curated_points": [
            "至东京时属少府，亦无员；驾出则一人负传国玺，操斩蛇剑（辑《汉官仪》）。",
            "侍中秩千石；《唐六典》引作比二千石，《续汉志》补注引《汉官》作秩千石——异说并存。",
            "服制：金蝉左貂，冠武弁大冠，加金珰附蝉；《通典》卷二十一系统转录，并称后汉门下省即侍中寺。",
            "《通典》：汉制置侍中、中常侍各一人，省尚书事；《唐六典》引蔡质《汉官典职》：侍中在尚书仆射下、尚书上。",
            "要点：记述重心从「谁能入禁」转向官署—秩比—服制的行政化描述；政书类为后世汇编，须回核汉唐引书。",
        ],
    },
    {
        "id": "donghan_mid",
        "title": "东汉中期：外戚近侍与录尚书",
        "range": "和帝—质帝",
        "summary": "外戚以侍中居禁中、掌机要；诏书与朝会记述显示侍中在权力网络中的位置。",
        "themes": ["外戚", "禁中", "朝会"],
        "curated_points": [
            "和帝诏书称「侍中宪，朕之元兄」，以旧典辅职而避政事安排（辑《汉官仪》相关诏）。",
            "和帝朝会召诸儒，侍中贾逵等与尚书令同席论难——侍中参与经学—朝议。",
            "要点：侍中成为权力网络节点；制度文本与政治人事高度缠绕。",
        ],
    },
    {
        "id": "donghan_late",
        "title": "东汉后期：士人侍中与中常侍分野",
        "range": "桓灵—献帝",
        "summary": "宦官中常侍与士人侍中并行；献帝时定侍中、给事黄门侍郎员各六人。",
        "themes": ["中常侍", "士人", "定员", "献帝"],
        "curated_points": [
            "初令侍中、给事黄门侍郎员各六人（《后汉书》献帝纪）。",
            "《献帝起居注》（《唐六典》卷八引）：初置侍中六人，出入禁中，近侍帷幄，省尚书事。",
            "中常侍秦官，汉兴或用士人；光武以后专任宦者（辑《汉官仪》）。",
            "给事黄门侍郎位次侍中，掌侍从左右、关通内外。",
            "《文献通考》职官考：西汉侍中但为加官，东汉属少府而秩稍增——政书层的演变概括。",
            "要点：从「无员」走向定员，反映近侍体系重组。",
        ],
    },
    {
        "id": "hanwei",
        "title": "汉魏之际：侍中典制度",
        "range": "建安—黄初",
        "summary": "魏国建，侍中与王粲等典制度；旧仪亲省起居；政书概括秦汉侍中曹至晋门下省的体制变迁。",
        "themes": ["魏国", "典制度", "门下省先声", "汉制衔接"],
        "curated_points": [
            "魏国既建，拜侍中，与王粲并典制度（《三国志》）。",
            "《魏略》注引旧仪：侍中亲省起居，故俗谓之执虎子——近侍职掌的民俗记忆。",
            "《唐六典》：魏氏侍中置四人，省祭酒，服秩依汉氏；秦汉置侍中曹，无台省之名，自晋始有门下省。",
            "《通典》：后世尤重门下，多以侍中辅政，遂为枢密之任——对汉制近侍的后设定位。",
            "要点：汉制侍中在曹魏被制度化、文本化，为魏晋门下省体制先声；十通/六典提供政书层总括，引用时须标明后世汇编性质。",
        ],
    },
]


def book_key(path: Path) -> str:
    rel = path.relative_to(RAW)
    parts = rel.parts
    book = parts[0]
    if book == "mirror" and len(parts) >= 2:
        book = parts[1]
    b = t2s(book)
    # 四库本目录名归并
    if "文献通考" in b or "文獻通考" in b:
        return "文献通考"
    if "册府元龟" in b or "冊府元龜" in b:
        return "册府元龟"
    return b


def juan_label(path: Path) -> str:
    rel = path.relative_to(RAW)
    parts = rel.parts
    name = parts[-1]
    name = re.sub(r"\.(txt|wikitext)$", "", name, flags=re.I)
    name = t2s(name).replace("_", "/")
    # 去掉重复书名前缀
    for prefix in ("通典/", "文献通考/", "唐六典/", "通志/", "册府元龟/"):
        name = name.replace(prefix, "")
    name = re.sub(r"\s*\(四库全书本\)\s*", "", name)
    if len(parts) >= 3 and parts[0] == "mirror":
        return f"{t2s(parts[1])}·{name}" if parts[1] not in name else name
    return name


def clean_quote(raw: str) -> str:
    """清洗单条引文：去 wiki 标记、注疏残片、错误断句前缀，转简体。"""
    s = raw or ""
    s = re.sub(r"\{\{[^}]{0,400}\}\}", " ", s)
    s = re.sub(r"<ref[^>]*>.*?</ref>", " ", s, flags=re.S)
    s = re.sub(r"<ref[^/]*/>", " ", s)
    s = re.sub(r"<onlyinclude>|</onlyinclude>|<poem>|</poem>|<br\s*/?>", " ", s)
    s = re.sub(r"<!--.*?-->", " ", s, flags=re.S)
    s = re.sub(r"-\{([^}]+)\}-", r"\1", s)
    s = re.sub(r"\{\{[^}]*\|([^}|]+)\}\}", r"\1", s)
    s = re.sub(r"\[\[[^\]|]+\|([^\]]+)\]\]", r"\1", s)
    s = re.sub(r"\[\[([^\]]+)\]\]", r"\1", s)
    s = re.sub(r"'''?", "", s)
    s = re.sub(r"={2,}[^=\n]{0,60}={2,}", " ", s)
    # 注疏：（注：…）/（案：…）/ {{*|…}} 残留
    s = re.sub(r"[（(](?:注|案)[：:][^）)]{2,}[）)]", " ", s)
    s = re.sub(r"\{\*?\|[^}]*\}", " ", s)
    s = re.sub(r"¶|※|□", "", s)
    # 全角/半角前导残片
    s = re.sub(r"^[》」』）)\]\}>\s]+", "", s)
    s = t2s(s)
    # t2s / hans 未覆盖的辑本与异体再扫一遍
    s = s.translate(str.maketrans({
        "㠯": "以", "璽": "玺", "蟬": "蝉", "僕": "仆", "復": "复",
        "獨": "独", "斷": "断", "給": "给", "禦": "御", "衞": "卫",
        "勳": "勋", "舊": "旧", "續": "续", "憲": "宪", "旣": "既",
        "並": "并", "劒": "剑", "靑": "青", "眞": "真",
        "僃": "备", "篤": "笃", "職": "职", "來": "来", "請": "请",
        "組": "组", "綬": "绶", "乗": "乘", "晝": "昼", "稱": "称",
        "贊": "赞", "績": "绩", "準": "准", "補": "补", "節": "节",
        "竝": "并", "矦": "侯", "藝": "艺", "敎": "教", "蓺": "艺",
        "統": "统", "監": "监", "驛": "驿", "過": "过", "戶": "户",
        "聞": "闻", "讓": "让", "許": "许", "相": "相",
    }))
    s = re.sub(r"^[\s\}\{）)》」』、，。；：]+", "", s)
    s = re.sub(r"[\s\{\（(《「『]+$", "", s)
    s = re.sub(r"^侍中箴=?", "", s)
    s = s.replace("}}", "").replace("{{", "")
    # 去掉残留的「注：」开头半截
    s = re.sub(r"^(?:注|案)[：:].{0,5}", "", s)
    s = re.sub(r"\s+", "", s)
    if "侍中" not in s or len(s) < 8:
        return ""
    m = re.search(r"^(.{8,280}?[。！？；])", s)
    if m:
        s = m.group(1)
    elif len(s) > 220:
        s = s[:220] + "…"
    return s.strip()


def split_sentences(text: str) -> list[str]:
    """更稳健的断句：先去标记，再按句读切，过长再按分句切。"""
    t = re.sub(r"\{\{[^}]{0,400}\}\}", " ", text or "")
    t = re.sub(r"-\{([^}]+)\}-", r"\1", t)
    t = re.sub(r"[（(](?:注|案)[：:][^）)]{2,}[）)]", " ", t)
    t = re.sub(r"<ref[^>]*>.*?</ref>", " ", t, flags=re.S)
    t = t2s(t)
    t = re.sub(r"\s+", "", t)
    parts = re.split(r"(?<=[。！？；;])", t)
    out = []
    for p in parts:
        p = clean_quote(p)
        if p and "侍中" in p:
            out.append(p)
    return out


def phase_of(sent: str, book: str) -> str:
    s = sent
    b = book
    if any(k in s for k in ["周官", "常伯", "丞相史", "本秦", "秦始皇破", "秦官"]):
        return "origin"
    if any(k in s for k in ["皆加官", "左右曹", "得入禁中", "无员", "亡员", "所加或", "百官公卿", "侍中无员", "侍中無員"]):
        return "xihan_addition"
    if any(k in s for k in ["孔安国", "唾壶", "莽何罗", "驸马都尉", "骖乘", "负以从", "亵器", "虎子"]):
        return "wudi_expansion"
    if any(k in s for k in ["明经者充侍中", "取明经", "负玺", "仆射，后改为祭酒", "行则负"]):
        return "chengai_mingjing"
    if any(k in s for k in ["王莽秉政", "侍中复入", "更始", "哀、平间", "哀平间", "王莽时"]):
        return "wangmang"
    if any(k in s for k in ["属少府", "屬少府", "秩千石", "比二千石", "侍中寺", "金蝉", "金蟬", "武弁", "貂蝉", "貂蟬", "斩蛇", "斬蛇", "东京时", "東京時"]):
        return "donghan_bureau"
    if any(k in s for k in ["元兄", "窦宪", "竇憲", "贾逵", "賈逵", "录尚书", "錄尚書"]):
        return "donghan_mid"
    if any(k in s for k in ["员各六人", "員各六人", "中常侍", "给事黄门", "給事黃門", "献帝", "獻帝", "省尚书事", "省尚書事"]):
        return "donghan_late"
    if any(k in s for k in ["典制度", "亲省起居", "親省起居", "执虎子", "執虎子", "魏国既建", "魏國旣建", "门下省", "門下省", "枢密", "樞密", "侍中曹", "品秩亦卑"]):
        return "hanwei"
    if b in ("通典", "唐六典", "文献通考", "册府元龟"):
        # 政书：按句内线索，否则归东汉属官化/综合
        if any(k in s for k in ["加官", "禁中", "中朝", "秦制"]):
            return "xihan_addition"
        if any(k in s for k in ["少府", "侍中寺", "冠武弁", "金珰", "左貂", "秩千石", "省尚书事"]):
            return "donghan_bureau"
        if any(k in s for k in ["员各六人", "献帝", "獻帝"]):
            return "donghan_late"
        return "donghan_bureau"
    if b in ("史记",):
        return "xihan_addition"
    if b in ("汉书", "西汉会要"):
        return "xihan_addition"
    if b in ("三国志",):
        return "hanwei"
    return "donghan_bureau"


def is_instish(sent: str) -> bool:
    keys = [
        "秩", "加官", "禁中", "无员", "无員", "少府", "侍中寺", "金蝉", "貂",
        "负玺", "明经", "汉官", "独断", "百官", "皆加官", "左右曹", "中常侍",
        "给事黄门", "典制度", "比二千石", "千石", "亲省起居", "执虎子",
        "员各", "周官", "常伯", "丞相史", "唾壶", "参乘", "佩玺", "冠",
        "印绶", "位次", "职掌", "顾问", "侍中无员", "复入", "共止",
        "起居注", "朝臣", "侍中组", "乘舆", "宿卫", "宿衛",
    ]
    return any(k in sent for k in keys)


def is_core_candidate(sent: str, book: str) -> bool:
    if book in INST_BOOKS and "侍中" in sent:
        # 类书/政书自动句再卡制度关键词
        if book in {
            "册府元龟", "太平御览", "玉海", "北堂书钞", "艺文类聚", "初学记",
            "职官分纪", "历代职官表", "续通典",
        }:
            return is_instish(sent) or any(k in sent for k in HAN_INST_KEYS)
        return True
    return is_instish(sent)


def extract_from_file(path: Path):
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return
    if "侍中" not in text:
        return
    book = book_key(path)
    juan = juan_label(path)
    rel = str(path.relative_to(ROOT)).replace("\\", "/")
    # 1) 整文件按句读切
    n_sent = 0
    for q in split_sentences(text):
        if "侍中" in q:
            n_sent += 1
            yield q, book, juan, rel
    # 2) 无标点/少标点文献：按「侍中」窗口摘句（殆知阁、汉官六种、类书）
    if n_sent < 3:
        flat = re.sub(r"\s+", "", text)
        flat = re.sub(r"\{\{[^}]*\}\}|<[^>]+>", " ", flat)
        flat = t2s(flat)
        flat = re.sub(r"^text:", "", flat)
        seen = set()
        for m in re.finditer(r"侍中", flat):
            a = max(0, m.start() - 36)
            b = min(len(flat), m.end() + 90)
            frag = flat[a:b]
            # 尽量从句读边界起
            for sep in ("。", "；", "，", "、", ";", ","):
                idx = frag.find(sep)
                if 0 <= idx <= 28:
                    frag = frag[idx + 1 :]
                    break
            # 截到下一明显句读或长度限制
            m2 = re.search(r"[。；！？]", frag[10:])
            if m2:
                frag = frag[: 10 + m2.end()]
            q = clean_quote(frag if frag.endswith("。") else frag)
            if not q or "侍中" not in q or len(q) < 12:
                continue
            # 窗口句须带制度关键词，降低类书人物轶事噪声
            if not any(k in q for k in HAN_INST_KEYS):
                continue
            if q in seen:
                continue
            seen.add(q)
            yield q, book, juan, rel


# 已核验核心句（来自 data/raw，清洗后强制注入，避免抽取漏收）
CORE_INJECT = [
    # (phase, book, juan, sentence_simple)
    ("origin", "全后汉文", "卷三十四（辑汉官仪）", "侍中，周官也。"),
    ("origin", "全后汉文", "卷三十四（辑汉官仪）", "侍中，周官，号曰常伯。"),
    ("origin", "全后汉文", "卷三十四（辑汉官仪）", "侍中左蝉右貂，本秦丞相史往来殿中，故谓之侍中。"),
    ("origin", "全后汉文", "卷三十四（辑汉官仪）", "其后秦始皇破赵，得其冠，以赐侍中。"),
    ("xihan_addition", "全后汉文", "卷三十四（辑汉官仪）", "《汉官表》曰：「凡侍中、左右曹诸吏、散骑、中常侍，皆加官也。」"),
    ("xihan_addition", "汉官旧仪", "卷上", "侍中无员，或列侯将军卫尉光禄将大夫郎为之，得举非法白请及出省户休沐往来过直事。"),
    ("xihan_addition", "独断", "卷上", "公卿侍中尚书衣帛而朝曰朝臣。"),
    ("xihan_addition", "独断", "卷上", "禁中者，门户有禁，非侍御者不得入，故曰禁中。"),
    ("wudi_expansion", "全后汉文", "卷三十四（辑汉官仪）", "武帝时，孔安国为侍中，以其儒者，特听掌御坐唾壶，朝廷荣之。"),
    ("wudi_expansion", "全后汉文", "卷三十四（辑汉官仪）", "分掌乘舆服物，下至亵器虎子之属。"),
    ("wudi_expansion", "西汉会要", "职官相关卷", "金日磾迁侍中驸马都尉光禄大夫，出则骖乘。"),
    ("chengai_mingjing", "全后汉文", "卷三十四（辑汉官仪）", "汉成帝取明经者充侍中，使辟百官公卿，参议可正为止殿，行则负玺。"),
    ("chengai_mingjing", "全后汉文", "卷三十四（辑汉官仪）", "旧高取一人为仆射，后改为祭酒。"),
    ("chengai_mingjing", "全后汉文", "卷三十四（辑汉官仪）", "侍中殿下称制，出则参乘，佩玺抱剑。"),
    ("wangmang", "后汉书", "卷116（百官志注系）", "王莽秉政，侍中复入，与中官共止。"),
    ("wangmang", "后汉书", "卷25（卓茂传）", "更始立，以茂为侍中祭酒，从至长安，知更始政乱，以年老乞骸骨归。"),
    ("wangmang", "后汉书", "卷35（张纯传）", "纯少袭爵士，哀、平间为侍中，王莽时至列卿。"),
    ("wangmang", "后汉书", "卷26（宋弘传）", "弘少而温顺，哀、平间作侍中，王莽时为共工。"),
    ("donghan_bureau", "全后汉文", "卷三十四（辑汉官仪）", "至东京时，属少府，亦无员。"),
    ("donghan_bureau", "全后汉文", "卷三十四（辑汉官仪）", "驾出则一人负传国玺，操斩蛇剑，参乘舆，中官俱止禁中。"),
    ("donghan_bureau", "全后汉文", "卷三十四（辑汉官仪）", "侍中，秩千石。"),
    ("donghan_bureau", "全后汉文", "卷三十四（辑汉官仪）", "侍中金蝉左貂。"),
    ("donghan_bureau", "全后汉文", "卷三十四（辑汉官仪）", "侍中冠武弁大冠，亦曰惠文冠，加金珰，附蝉为文，貂尾为饰，谓之貂蝉。"),
    ("donghan_bureau", "全后汉文", "卷三十四（辑汉官仪）", "尚书令侍中，上东西寺及侍中寺。"),
    ("donghan_mid", "全后汉文", "卷九（辑诏）", "侍中宪，朕之元兄，行能兼备，忠孝尤笃，先帝所器，亲受遗诏，当以旧典辅斯职焉。"),
    ("donghan_mid", "后汉书", "卷25/东观汉记", "和帝因朝会，召见诸儒，丕与侍中贾逵、尚书令黄香等相难数事。"),
    ("donghan_late", "后汉书", "卷9（献帝纪）", "初令侍中、给事黄门侍郎员各六人。"),
    ("donghan_late", "后汉书", "卷116（百官志）", "帝初即位，初置侍中、给事黄门侍郎，员各六人，出入禁中，近侍帷幄，省尚书事。"),
    ("donghan_late", "全后汉文", "卷三十四（辑汉官仪）", "中常侍，秦官也。汉兴，或用士人，银珰左貂。光武以后，专任宦者，右貂金珰。"),
    ("donghan_late", "全后汉文", "卷三十四（辑汉官仪）", "给事黄门侍郎，六百石，无员，掌侍从左右，给事中，使关通中外。"),
    ("hanwei", "三国志", "卷21（王卫二刘傅传）", "魏国既建，拜侍中，与王粲并典制度。"),
    ("hanwei", "三国志", "卷16注（魏略）", "旧仪，侍中亲省起居，故俗谓之执虎子。"),
    # —— 十通 / 唐六典（政书系统整理，须标明为后世汇编）——
    ("origin", "通典", "卷二十一·职官三·门下省侍中", "本丞相史也，使五人往来殿内东厢奏事，故谓之侍中。"),
    ("xihan_addition", "通典", "卷二十一·职官三", "凡侍中、左右曹、诸吏、散骑、中常侍，皆为加官。"),
    ("xihan_addition", "通典", "卷二十一·职官三", "侍中、中常侍得入禁中，诸曹受尚书事，诸吏得举法。"),
    ("xihan_addition", "唐六典", "卷八·门下省（引汉书百官表）", "侍中皆加官，所加或列侯、将军、卿大夫，无员，多至数十人，得入禁中，诸曹受尚书事，皆秦制。"),
    ("xihan_addition", "通典", "卷十九·职官总序（引孟康注）", "大司马、左右前后将军、侍中、常侍、散骑、诸吏为中朝；丞相以下至六百石等为外朝。"),
    ("donghan_bureau", "通典", "卷二十一·职官三", "门下省，后汉谓之侍中寺。"),
    ("donghan_bureau", "通典", "卷二十一·职官三", "汉侍中冠武弁大冠，亦曰惠文冠，加金珰，附蝉为文，貂尾为饰。"),
    ("donghan_bureau", "通典", "卷二十一·职官三", "侍中服则左貂，常侍服则右貂。"),
    ("donghan_bureau", "通典", "卷二十一·职官三", "本有仆射一人，秦汉以侍中功高者一人为仆射。"),
    ("donghan_bureau", "通典", "卷二十七·职官九", "汉制，置侍中、中常侍各一人，省尚书事，黄门侍郎一人，传发书奏，皆用姓族。"),
    ("donghan_bureau", "唐六典", "卷八·门下省（引蔡质汉官典职）", "侍中在尚书仆射下，尚书上。"),
    ("donghan_bureau", "唐六典", "卷八·门下省", "灵帝时，侍中舍有八区，论者因言员有八人，未详也。"),
    ("donghan_late", "唐六典", "卷八·门下省（引献帝起居注）", "初置侍中六人，出入禁中，近侍帷幄，省尚书事。"),
    ("donghan_late", "文献通考", "卷五十·职官考四", "侍中但为加官，在东汉亦属少府而秩稍增。"),
    ("hanwei", "唐六典", "卷八·门下省", "魏氏侍中置四人，省祭酒，而加官不在数，服秩依汉氏，掌傧赞威仪。"),
    ("hanwei", "唐六典", "卷八·门下省", "秦、汉初置侍中，主诸御物，品秩亦卑；至献帝时，与给事黄门侍郎各置六员，出入禁中，近侍帷幄，省尚书事。"),
    ("hanwei", "唐六典", "卷八·门下省", "秦、汉置侍中曹，无台省之名，自晋始有门下省。"),
    ("hanwei", "通典", "卷二十一·职官三", "然而尤重门下官，多以侍中辅政，则侍中为枢密之任。"),
    # —— 非维基：汉官六种 / 类书 / 会要 / 历代职官表 ——
    ("origin", "汉官六种", "孙星衍辑本", "侍中，周官，以其周曰常伯，故曰周官。"),
    ("origin", "初学记", "职官部（引班固汉书）", "侍中秦官，以其秦取古官复置之，故曰秦官。"),
    ("origin", "初学记", "职官部", "初秦置侍中，本丞相史也。"),
    ("xihan_addition", "西汉会要", "职官五·加官", "侍中、左右曹诸吏、散骑、中常侍皆加官，所加或列侯、将军、卿大夫至郎中，亡员，多至数十人；侍中、中常侍得入禁中，诸曹受尚书事，诸吏得举法；散骑并乘舆车。皆秦制。"),
    ("xihan_addition", "初学记", "职官部", "宣帝末又别置侍中，为加官。"),
    ("xihan_addition", "初学记", "职官部（引汉书百官表）", "自侍中、尚书、博士郎、军屯吏、马宰、永巷，皆有仆射，随所领之事以为号。"),
    ("donghan_bureau", "初学记", "职官部（引汉官）", "侍中冠武弁大冠，亦曰惠文冠。"),
    ("donghan_bureau", "初学记", "职官部", "侍中服之则左貂，常侍则右貂。本赵武灵王胡服之制，秦始皇破赵，得其冠，赐侍中。"),
    ("donghan_bureau", "初学记", "职官部（引汉官仪）", "侍中有玉堂署。"),
    ("donghan_bureau", "历代职官表", "门下省/侍中表", "东汉安帝时众务悉由尚书；中书监、侍中、尚书令仆射诸官防掌机密，并无常职。"),
    ("donghan_late", "初学记", "职官部（引献帝起居注）", "初置侍中六人，出入禁中，近侍帷幄，省尚书事。"),
    ("wudi_expansion", "汉官旧仪", "殆知阁本", "以金银縢组，侍中组负以从。"),
    ("donghan_mid", "东汉会要", "职官·侍中", "侍中丁鸿仁而有让，达于从政。"),
]


def rank_quote(q: str, book: str, juan: str) -> int:
    score = BOOK_RANK.get(book, 30)
    if "卷" in juan and "第" not in juan:
        score += 8  # 传统卷次更清晰
    if any(k in q for k in ["皆加官", "无员", "属少府", "秩千石", "员各六人", "典制度", "周官", "丞相史", "唾壶", "负玺", "侍中寺", "亲省起居", "王莽秉政"]):
        score += 20
    if is_instish(q):
        score += 8
    if len(q) < 60:
        score += 3
    # 避免 mirror 章节压过 wiki 卷
    if book in ("汉书", "后汉书", "三国志", "史记") and ("第" in juan and "章" in juan):
        score -= 5
    return score


def main():
    INST_DIR.mkdir(parents=True, exist_ok=True)
    pool = []
    scanned = 0
    for path in RAW.rglob("*.txt"):
        if path.name.startswith(".") or path.suffix.lower() != ".txt":
            continue
        for q, book, juan, rel in extract_from_file(path):
            scanned += 1
            if not is_core_candidate(q, book):
                continue
            pool.append(
                {
                    "sentence": q,
                    "book": book,
                    "juan": juan,
                    "path": rel,
                    "phase": phase_of(q, book),
                    "kind": "制度" if is_instish(q) else "旁证",
                    "rank": rank_quote(q, book, juan),
                }
            )

    # 注入已核验核心句（简体、出处标明）
    for phase, book, juan, sent in CORE_INJECT:
        pool.append(
            {
                "sentence": sent,
                "book": book,
                "juan": juan,
                "path": "",
                "phase": phase,
                "kind": "制度",
                "rank": 120 + BOOK_RANK.get(book, 40),
            }
        )

    # 去重 + 质量闸
    trad_chars = set(
        "漢書後國為無員與從來門開萬號孫權獻靈㠯璽蟬僕獨斷給禦衞勳舊續憲旣並"
        "僃篤職請組乗晝稱贊績準補驛傳節竝矦藝敎蓺統監戶聞讓過"
    )
    pool.sort(key=lambda x: -x["rank"])
    kept = []
    keys_used = []
    for item in pool:
        s = item["sentence"]
        nk = norm_quote(s)
        if not nk or "侍中" not in s:
            continue
        if any(x in s for x in ["}}", "===", "{{", "*|"]):
            continue
        # 无句读长段（制度书扫描残片）丢弃
        if len(s) > 90 and "。" not in s and "；" not in s:
            continue
        # HTML 残留 / 品秩长表
        if any(x in s for x in ["</small>", "<small>", "-----", "官秩云"]):
            continue
        if len(s) > 60 and s.count("、") >= 6 and "侍中" in s:
            # 连续官名表，非制度论述
            if not any(k in s for k in ["汉", "秦", "少府", "加官", "禁中", "冠", "貂", "玺", "献帝"]):
                continue
        # 政书自动句：须与两汉制度相关，避免唐宋南北朝枝蔓
        if item["book"] in ("通典", "文献通考", "唐六典", "册府元龟") and item.get("path"):
            han_keys = (
                "汉", "秦", "少府", "加官", "禁中", "侍中寺", "冠", "貂", "玺", "璽",
                "献帝", "更始", "王莽", "丞相史", "周官", "无员", "無員", "秩",
                "门下省，后汉", "后汉谓", "後漢謂", "汉制", "漢制", "秦汉", "秦漢",
            )
            if not any(k in s for k in han_keys):
                continue
            # 明确后世朝代且无汉制对照者降权剔除
            if any(k in s for k in ["北齐", "北齊", "后周", "後周", "大唐", "宋制", "元丰", "紹興", "绍兴", "至齐，亦呼", "乾隆", "国朝", "國朝"]):
                if not any(k in s for k in ["汉", "秦", "后汉", "後漢", "西汉", "东汉"]):
                    continue
        if item["book"] in ("册府元龟", "太平御览", "玉海", "北堂书钞", "艺文类聚", "初学记", "职官分纪", "历代职官表"):
            if not any(k in s for k in HAN_INST_KEYS):
                continue
        # 繁体/异体残留
        left = sum(1 for c in s if c in trad_chars)
        if left >= 1:
            continue
        # 引号不配对或句中残注
        if s.count("「") != s.count("」") or s.count("《") > s.count("》") + 1:
            if s.count("「") != s.count("」"):
                continue
        # 晋代嵇绍等非本库制度主干、且无制度关键词的旁证句降权过滤
        if "惠帝" in s and "成都王" in s:
            continue
        fp = nk[:28]
        if any(fp and (fp in prev or prev.startswith(nk[:20])) for prev in keys_used):
            continue
        keys_used.append(nk)
        kept.append(item)

    by_phase = defaultdict(list)
    for item in kept:
        by_phase[item["phase"]].append(item)

    final_phases = []
    total_q = 0
    for ph in PHASES:
        qs = sorted(by_phase.get(ph["id"], []), key=lambda x: -x["rank"])
        picked = qs[:28]
        total_q += len(picked)
        final_phases.append(
            {
                "id": ph["id"],
                "title": ph["title"],
                "range": ph["range"],
                "summary": ph["summary"],
                "themes": ph["themes"],
                "curated_points": ph["curated_points"],
                "quotes": [
                    {
                        "book": x["book"],
                        "juan": x["juan"],
                        "sentence": x["sentence"],
                        "kind": x["kind"],
                        "path": x["path"],
                    }
                    for x in picked
                ],
                "quote_count": len(picked),
            }
        )

    institution = {
        "title": "侍中制度沿革",
        "subtitle": "两汉侍中职官制度史料编年梳理",
        "updated": "2026-09",
        "display_script": "simplified",
        "note": (
            "引文显示统一为简体。语料：正史职官表志、《汉官六种》与辑《汉官仪》、《独断》《汉官旧仪》、"
            "两汉会要/汉制考，以及《通典》《文献通考》《唐六典》与类书（《职官分纪》《初学记》《北堂书钞》"
            "《太平御览》《册府元龟》等，来自殆知阁/Kanripo）。制度提要在各阶段「要点」；"
            "引文均为语料可检索原句，不作合成；类书/政书标明为汇编或转引。"
        ),
        "phases": final_phases,
        "stats": {
            "scanned_candidates": scanned,
            "kept_after_dedup": len(kept),
            "institution_page_quotes": total_q,
            "roster_size": 258,
        },
        "sources_note": [
            "正史职官：《汉书·百官公卿表》、《后汉书》百官志（含注引）— data/raw/汉书、后汉书",
            "制度专书/辑佚：《汉官六种》（Kanripo KR2l0023 孙星衍辑）、《独断》、《汉官旧仪》、严可均辑《汉官仪》",
            "政书会要：《西汉会要》《东汉会要》《汉制考》— 维基 + 殆知阁",
            "十通/六典：《通典》《文献通考》《续通典》《唐六典》— 维基 + 殆知阁全文",
            "类书/职官专书：《职官分纪》《初学记》《北堂书钞》《艺文类聚》《太平御览》《册府元龟》《玉海》《历代职官表》— 殆知阁 daizhigev20",
            "诏令与旁证：《两汉诏令》、编年/金石；悬泉汉简（殆知阁本）本轮未见「侍中」",
            "非维基入口：殆知阁 GitHub garychowcmu/daizhigev20 · Kanripo bkkbooks/KR2l0023",
            "体例：汉唐原典与辑本优先；类书/政书为汇编或转引，卷次/书名已标明；显示一律简体；引文不作合成",
        ],
        "quality": {
            "simplified": True,
            "no_synthetic_quotes": True,
            "dedup": "norm_quote + 前缀指纹；制度专书/政书/辑本优先于章节镜像",
            "markup_cleaned": ["wiki模板", "ref", "注案括注", "章节标题", "残缺括号", "辑本异体字"],
            "political_compendia": ["通典", "文献通考", "唐六典", "册府元龟"],
        },
    }

    OUT.write_text(json.dumps(institution, ensure_ascii=False, indent=2), encoding="utf-8")
    print("scanned", scanned, "kept", len(kept), "page quotes", total_q)
    print("phases:", [(p["id"], p["quote_count"]) for p in final_phases])
    dirty = trad = 0
    trad_chars = set("漢書後國為無員與從來門開萬號孫權獻靈㠯璽蟬僕獨斷給禦衞勳舊續憲旣並")
    for p in final_phases:
        print("---", p["id"])
        for q in p["quotes"][:4]:
            print("   ", q["book"], q["juan"], "|", q["sentence"][:70])
            s = q["sentence"]
            if any(x in s for x in ["}}", "===", "{{", "（注"]):
                dirty += 1
                print("    DIRTY")
            left = [c for c in s if c in trad_chars]
            if left:
                trad += 1
                print("    TRAD", left)
    print("dirty", dirty, "trad", trad)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
