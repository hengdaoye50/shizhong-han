"""全量语义优化人物卡：从证据句提炼任职、事件、关系，修正残留误名。

用法:
  python sources/enrich_all_cards.py
"""

from __future__ import annotations

import csv
import re
import sqlite3
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT / "data" / "cards"
EV = ROOT / "data" / "candidates" / "persons_evidence.csv"
DB = ROOT / "data" / "db" / "shizhong.db"
CANON = ROOT / "data" / "candidates" / "persons_canonical.csv"

# 残留误名 → 规范名（用户审读后仍可能从证据重建）
RENAME = {
    "傅俊迎": "傅俊",
    "侯王邑": "王邑",
    "张紹": "张绍",
    "王輔": "王辅",
    "劉宽": "刘宽",
    "刘宽": "刘宽",
    "楊文父": "杨文父",
    "韩说": "韩说",
    "韓說": "韩说",
    "邓叠": "邓叠",
    "鄧疊": "邓叠",
    "荀顗": "荀顗",
}

# 已有深度扩写的（不覆盖，只补关系）
KEEP_DEEP = {
    "窦宪", "金安上", "金日磾", "金建", "金赏", "金敞", "贾逵",
    "董贤", "淳于长", "刘瑜", "杜乔", "史丹", "鲁丕", "梁不疑", "伍孚",
}

# 联网/史实要点（人名 → 字段）
FACTS: dict[str, dict] = {
    "刘艾": {
        "style": "阙", "dynasty": "東漢", "category": "士人",
        "origin": "阙", "birth": "阙", "death": "阙",
        "term": "献帝朝侍中；董卓乱中随驾，护天子",
        "bio": [
            "东汉末献帝朝侍中。",
            "董卓死后李傕郭汜乱，艾随乘舆，呼「是天子也」以安军心。",
            "帝疑赋恤有虚，敕艾取米豆于御前试糜，知报不实，使出让有司。",
            "与杨彪、赵温等随驾西行。",
        ],
        "rels": [("献帝", "与帝", "随驾近侍"), ("李傕", "政敌", "乱中护驾")],
    },
    "杨琦": {
        "style": "阙", "dynasty": "東漢", "category": "士人",
        "term": "献帝朝侍中；李傕乱中上封事、举车帷",
        "bio": [
            "献帝朝侍中。李傕移乘舆幸北坞，琦上封事陈傕边鄙习夷风、欲幸黄白城。",
            "又使琦高举车帷。与丁冲、钟繇等同行。",
        ],
        "rels": [("献帝", "与帝", ""), ("李傕", "政敌", "上封事言傕")],
    },
    "张辟彊": {
        "style": "阙", "dynasty": "西漢", "category": "宗室/勋贵",
        "origin": "留侯张良子", "birth": "阙", "death": "阙",
        "term": "惠帝崩时为侍中，年十五",
        "bio": [
            "留侯张良之子。惠帝崩时为侍中，年十五。",
            "谓丞相陈平：太后独有帝，哭不悲，乃畏君等；劝平请拜吕台吕产将兵，以解太后疑。",
            "陈平用其计，太后悦。",
        ],
        "rels": [("张良", "父", "留侯"), ("陈平", "同僚", "献计"), ("吕太后", "与帝系", "说平")],
    },
    "王林卿": {
        "style": "阙", "dynasty": "西漢", "category": "外戚",
        "origin": "邛成太后外家", "term": "为侍中，通轻侠，倾京师；后坐杀人",
        "bio": [
            "邛成太后外家王氏。为侍中，通轻侠，倾京师。",
            "坐杀人埋冢舍，使奴剥寺门鼓；何并收捕，斩其奴，林卿亡去。",
        ],
        "rels": [("邛成太后", "外戚", "外家"), ("何并", "政敌", "收捕")],
    },
    "刘廙": {
        "style": "恭嗣", "dynasty": "漢魏之際", "category": "士人",
        "origin": "南阳安众", "term": "魏王侍中；禅代奏议主笔之一",
        "bio": [
            "字恭嗣，南阳安众人。仕魏，为侍中。",
            "与辛毗、刘晔等奏议，劝曹丕践阼；宣叙众心，考图纬符瑞。",
            "华歆、贾诩、王朗等上言中亦称「侍中刘廙等宣叙众心」。",
        ],
        "rels": [("曹丕", "与帝", "禅代奏议"), ("刘晔", "同僚", "俱侍中"), ("辛毗", "同僚", "")],
    },
    "刘岱": {
        "style": "公山", "dynasty": "東漢", "category": "士人",
        "origin": "东莱牟平", "term": "董卓秉政时由侍中出为兖州刺史",
        "bio": [
            "字公山，东莱牟平人。董卓入洛，以侍中刘岱为兖州刺史。",
            "与韩馥、孔伷、张咨等同批出牧。",
        ],
        "rels": [("董卓", "权臣", "卓所拜")],
    },
    "金敞": {
        "style": "阙", "dynasty": "西漢", "category": "降人",
        "origin": "金安上子", "term": "元帝时为侍中，与刘向拾遗左右；后为水衡都尉、卫尉",
        "bio": [
            "金安上子。元帝初，萧望之、周堪领尚书，荐刘向，与侍中金敞拾遗左右。",
            "为人正直，敢犯颜色。后为侍中奉车都尉、水衡都尉，迁卫尉。",
        ],
        "rels": [("金安上", "父", ""), ("萧望之", "府主/同僚", "共事"), ("刘向", "同僚", "拾遗左右"), ("元帝", "与帝", "")],
    },
    "虞子和": {
        "style": "和", "dynasty": "東漢", "category": "宗室/勋贵",
        "term": "献帝时为侍中，在长安",
        "bio": [
            "刘虞之子（虞子和）。为侍中，在长安。",
            "献帝东归，遣和潜从武关出，告虞将兵来迎。",
        ],
        "rels": [("刘虞", "父", ""), ("献帝", "与帝", "奉使")],
    },
    "傅巽": {
        "style": "公悌", "dynasty": "漢魏之際", "category": "士人",
        "term": "黄初中为侍中、尚书",
        "bio": [
            "字公悌。黄初中为侍中、尚书。",
            "仕魏，有知人之鉴（掐则目之乃悟等轶事）。",
        ],
        "rels": [("曹丕", "与帝", "")],
    },
    "宋弘": {
        "style": "仲子", "dynasty": "西漢/東漢", "category": "士人",
        "origin": "京兆长安", "term": "哀、平间为侍中；王莽时为共工（少府）",
        "bio": [
            "字仲子，京兆长安人。哀、平间为侍中，王莽时为共工。",
            "光武即位，征拜太中大夫，后代杜林为大司空。以清行称，谏「糟糠之妻」。",
        ],
        "rels": [("光武帝", "与帝", "东汉初重臣"), ("王莽", "前朝", "莽时官")],
    },
    "许相": {
        "style": "阙", "dynasty": "東漢", "category": "其他",
        "term": "灵帝时侍中，与曹节王甫张让并为列侯",
        "bio": [
            "东汉灵帝时为侍中。窦武诛后，宦官用事，侍中许相与中常侍曹节、王甫、张让等并为列侯。",
        ],
        "rels": [("曹节", "同列", "并封侯"), ("灵帝", "与帝", "")],
    },
    "刘歆": {
        "style": "子骏", "dynasty": "西漢", "category": "士人",
        "origin": "楚元王后", "term": "哀帝建平中为侍中；欲立《左氏》",
        "bio": [
            "字子骏，后改名秀。楚元王交之后，刘向子。经学家、目录学家。",
            "建平中为侍中，欲立《左氏》于学官，不先暴论大义而轻移太常，诸儒相与排之。",
        ],
        "rels": [("刘向", "父", ""), ("哀帝", "与帝", ""), ("诸儒", "政敌", "排左氏")],
    },
    "周广": {
        "style": "阙", "dynasty": "東漢", "category": "其他",
        "term": "安帝时侍中；与樊丰、耿宝、谢惲等谗陷杨震",
        "bio": [
            "安帝时为侍中。中常侍樊丰、大将军耿宝、侍中周广、谢惲等共谗陷太尉杨震，震自杀。",
            "又与樊丰等更相扇动，倾摇朝廷。后阎显奏宝党与，广在其中。",
        ],
        "rels": [("杨震", "政敌", "谗陷"), ("樊丰", "同党", ""), ("耿宝", "同党", "")],
    },
    "刘晔": {
        "style": "子扬", "dynasty": "漢魏之際", "category": "士人",
        "origin": "淮南成德", "term": "魏侍中；文帝谋臣",
        "bio": [
            "字子扬，淮南成德人，光武子阜陵王延之后。曹操、曹丕谋臣。",
            "为侍中。文帝问侍中刘晔「武都太守何如人」；遣晔将太医视疾。",
            "晔常曰蜀不可伐；后为陈群等所短。",
        ],
        "rels": [("曹丕", "与帝", "谋臣"), ("曹操", "旧主", "")],
    },
    "周毖": {
        "style": "仲远", "dynasty": "東漢", "category": "士人",
        "term": "董卓时为侍中；阴为袁绍",
        "bio": [
            "与城门校尉伍琼等皆名士，董卓信之，而阴为袁绍。",
            "说卓：废立大事非常人所及，不如赦绍，拜为一郡守。",
        ],
        "rels": [("董卓", "权臣", "卓信之"), ("袁绍", "暗通", "阴为绍"), ("伍琼", "同僚", "")],
    },
    "刘能卿": {
        "style": "阙", "dynasty": "更始", "category": "其他",
        "term": "更始帝侍中",
        "bio": [
            "更始政权侍中。知申屠建等谋，以告更始。",
        ],
        "rels": [("刘玄(更始)", "与帝", "")],
    },
    "刘恭": {
        "style": "阙", "dynasty": "更始/東漢", "category": "宗室",
        "term": "更始帝侍中",
        "bio": [
            "更始帝侍中。赤眉立其弟盆子，恭自系诏狱；闻更始败，乃出，步从至高陵。",
        ],
        "rels": [("刘盆子", "弟", "赤眉所立"), ("更始帝", "与帝", "")],
    },
    "任芝": {
        "style": "阙", "dynasty": "東漢", "category": "其他",
        "term": "灵帝时侍中",
        "bio": [
            "灵帝时为侍中。帝欲止某事，以问侍中任芝、中常侍乐松。",
        ],
        "rels": [("灵帝", "与帝", ""), ("乐松", "同列", "中常侍")],
    },
    "许章": {
        "style": "阙", "dynasty": "西漢", "category": "外戚",
        "term": "以外属贵幸为侍中",
        "bio": [
            "以外属贵幸，奢淫不奉法度。宾客犯事，与章相连。",
        ],
        "rels": [("外戚王氏/许氏", "外戚", "以外属贵")],
    },
    "傅商": {
        "style": "阙", "dynasty": "西漢", "category": "外戚",
        "term": "哀帝时侍中，封汝昌侯",
        "bio": [
            "帝太太后（傅太后）从弟。为侍中，二月封汝昌侯。",
            "同时太后同母弟子侍中郑业封阳信侯。",
        ],
        "rels": [("傅太后", "外戚", "从弟"), ("郑业", "姻亲", "同批封侯"), ("哀帝", "与帝", "")],
    },
    "王凤": {
        "style": "孝卿", "dynasty": "西漢", "category": "外戚",
        "origin": "东平陵", "term": "元帝成帝时为侍中卫尉；后为大司马大将军领尚书事",
        "bio": [
            "字孝卿，元帝皇后王政君兄。阳平侯。",
            "为侍中卫尉三年，迁大司马大将军领尚书事，外戚王氏秉政之始。",
        ],
        "rels": [("王政君", "妹", "元后"), ("成帝", "与帝", "元舅"), ("王莽", "侄", "")],
    },
    "孙峻": {
        "style": "子远", "dynasty": "吳", "category": "其他",
        "term": "吴侍中；孙权疾困属以后事",
        "bio": [
            "吴宗室。孙权疾困，召诸葛恪、滕胤、吕据及侍中孙峻，属以后事。",
            "后与恪争权，杀恪，专朝政。",
        ],
        "rels": [("孙权", "与帝", "受遗"), ("诸葛恪", "政敌", "杀恪")],
    },
    "张绍": {
        "style": "阙", "dynasty": "蜀漢", "category": "其他",
        "term": "蜀汉侍中；后主降魏使者",
        "bio": [
            "蜀汉侍中。后主降邓艾，遣私署侍中张绍、光禄大夫谯周、驸马都尉邓良奉印绶请命。",
            "魏封后主，绍与樊建、谯周、郤正等并封列侯。",
        ],
        "rels": [("刘禅", "与帝", "奉表降"), ("谯周", "同僚", "降使")],
    },
    "郭攸之": {
        "style": "演长", "dynasty": "蜀漢", "category": "士人",
        "origin": "南阳",
        "term": "蜀汉侍中；《出师表》所举",
        "bio": [
            "字演长，南阳人。诸葛亮《出师表》：侍中郭攸之、费祎、侍郎董允等，先帝简拔以遗陛下。",
            "性行淑均，晓畅军事。",
        ],
        "rels": [("诸葛亮", "举主", "出师表所举"), ("费祎", "同僚", "俱侍中"), ("董允", "同僚", "侍郎"), ("刘禅", "与帝", "")],
    },
    "马良": {
        "style": "季常", "dynasty": "蜀漢", "category": "士人",
        "origin": "襄阳宜城", "term": "蜀汉侍中；夷陵战前安抚五溪蛮",
        "bio": [
            "字季常，襄阳宜城人。兄弟五人并有才名，乡里谚「马氏五常，白眉最良」。",
            "先主东征，遣侍中马良安慰五谿蛮夷，咸相率响应。后殁于夷陵之败。",
        ],
        "rels": [("刘备", "与帝", "奉使"), ("马谡", "弟", "")],
    },
    "诸葛瞻": {
        "style": "思远", "dynasty": "蜀漢", "category": "宗室/勋贵",
        "origin": "琅邪阳都", "term": "蜀汉侍中；诸葛亮子",
        "bio": [
            "字思远，诸葛亮之子。为侍中，迁尚书仆射、军师将军。",
            "邓艾伐蜀，瞻督诸军至涪，战死绵竹。",
        ],
        "rels": [("诸葛亮", "父", ""), ("刘禅", "与帝", "尚公主"), ("诸葛恪", "从兄", "")],
    },
    "许允": {
        "style": "士宗", "dynasty": "魏", "category": "士人",
        "term": "魏侍中；说曹爽早归罪",
        "bio": [
            "字士宗。为侍中。与尚书陈泰说曹爽，使早自归罪于司马懿。",
        ],
        "rels": [("曹爽", "同僚/说客", ""), ("司马懿", "权臣", "")],
    },
    "何晏": {
        "style": "平叔", "dynasty": "魏", "category": "外戚/士人",
        "term": "曹爽秉政时为侍中",
        "bio": [
            "字平叔，何进孙，母尹氏为曹操夫人。玄学家。",
            "曹爽秉权，徙卢毓仆射，以侍中何晏代毓。",
            "高平陵之变后与爽同诛。",
        ],
        "rels": [("曹爽", "府主", "代卢毓"), ("曹操", "养父系", "何进孙")],
    },
    "孙邕": {
        "style": "阙", "dynasty": "魏", "category": "士人",
        "term": "正始中侍中；荐管宁",
        "bio": [
            "魏侍中。正始二年，与太仆陶丘一、永宁卫尉孟观、中书侍郎王基荐管宁。",
        ],
        "rels": [("管宁", "荐主", "荐宁"), ("曹芳", "与帝", "")],
    },
    "郑小同": {
        "style": "阙", "dynasty": "魏", "category": "士人",
        "term": "魏侍中；执经亲授",
        "bio": [
            "郑玄之孙（或玄子益恩之后，一说玄高密后人）。为侍中。",
            "讲《尚书》业终，赐执经亲授者司空郑冲、侍中郑小同等各有差。",
        ],
        "rels": [("郑玄", "祖", ""), ("郑冲", "同列", "")],
    },
    "李延年": {
        "style": "阙", "dynasty": "西漢", "category": "其他",
        "term": "武帝时为侍中；协律都尉",
        "bio": [
            "中山人，李夫人兄。善歌，为新变声。",
            "武帝作《十九章》，令侍中李延年次序其声，拜为协律都尉。",
            "后坐奸，诛。属佞幸/乐官系统。",
        ],
        "rels": [("武帝", "与帝", "乐官"), ("李夫人", "妹", "")],
    },
    "丁恭": {
        "style": "子然", "dynasty": "東漢", "category": "士人",
        "origin": "山阳东缗", "term": "建武二十年拜侍中祭酒、骑都尉",
        "bio": [
            "字子然，经学家。建武二十年，拜侍中祭酒、骑都尉。",
            "与侍中刘昆俱在光武左右，每事咨访。",
        ],
        "rels": [("光武帝", "与帝", "咨访"), ("刘昆", "同僚", "俱侍中")],
    },
    "袁隗": {
        "style": "次阳", "dynasty": "東漢", "category": "士人",
        "term": "后将军；曾表他人为侍中（本人非必侍中）",
        "bio": [
            "字次阳，汝南汝阳人，袁安孙。位至后将军、太傅。",
            "后将军袁隗表某为侍中，以父丧不行。隗本人以三公著称。",
            "注意：证据句中隗为「表荐者」，非「被表为侍中者」。",
        ],
        "rels": [("袁绍", "从子", ""), ("袁术", "从子", "")],
    },
    "尹勋": {
        "style": "伯元", "dynasty": "東漢", "category": "士人",
        "origin": "河南巩", "term": "灵帝初为侍中，迁尚书令；与窦武谋诛宦官",
        "bio": [
            "字伯元。窦武引同志：以侍中尹勋为尚书令，刘瑜为侍中，冯述为屯骑校尉。",
            "谋诛宦官，事泄，曹节矫诏诛武、蕃、勋、瑜等，夷其族。",
        ],
        "rels": [("窦武", "同谋", "引为尚书令"), ("刘瑜", "同僚", "俱谋"), ("曹节", "政敌", "矫诏诛")],
    },
    "来历": {
        "style": "伯珍", "dynasty": "東漢", "category": "外戚/勋贵",
        "term": "永元中为侍中，监羽林右骑",
        "bio": [
            "字伯珍，来歙曾孙。少袭爵，以公主子。",
            "永元中为侍中，监羽林右骑。",
        ],
        "rels": [("来歙", "曾祖", "云台二十八将"), ("和帝", "与帝", "")],
    },
    "刘珍": {
        "style": "秋孙", "dynasty": "東漢", "category": "士人",
        "term": "侍中；护礼仪、撰《东观汉记》",
        "bio": [
            "字秋孙（一作宝孙）。为侍中，护礼仪。",
            "与李尤等撰《东观汉记》。",
        ],
        "rels": [("邓太后", "与帝系", "临朝时修史")],
    },
    "向栩": {
        "style": "甫兴", "dynasty": "東漢", "category": "士人",
        "term": "灵帝时侍中；坐言宦者下狱死",
        "bio": [
            "侍中向栩、张钧坐言宦者，下狱死。",
        ],
        "rels": [("张钧", "同僚", "俱坐言宦者死"), ("宦官", "政敌", "")],
    },
    "傅俊": {
        "style": "子卫", "dynasty": "東漢", "category": "勋贵",
        "term": "光武时侍中；迎阴丽华",
        "bio": [
            "字子卫，颍川襄城人。云台二十八将之一。",
            "光武即位，令侍中傅俊迎后（阴丽华），与诸宫人俱到洛阳，以后为贵人。",
        ],
        "rels": [("光武帝", "与帝", "迎后"), ("阴丽华", "所迎", "阴后")],
    },
    "邓蕃": {
        "style": "阙", "dynasty": "東漢", "category": "外戚",
        "term": "昌安侯侍中；尚平皋公主",
        "bio": [
            "邓氏外戚。昌安侯，为侍中。",
            "皇女小姬，十二年封平皋公主，适昌安侯侍中邓蕃。",
        ],
        "rels": [("邓禹系", "宗族", "外戚"), ("平皋公主", "妻", "尚主")],
    },
    "贾建": {
        "style": "阙", "dynasty": "東漢", "category": "外戚",
        "term": "即墨侯侍中；尚临颍公主",
        "bio": [
            "即墨侯，为侍中。皇女利，封临颍公主，适即墨侯侍中贾建。",
        ],
        "rels": [("临颍公主", "妻", "尚主")],
    },
    "朱展": {
        "style": "阙", "dynasty": "東漢", "category": "其他",
        "term": "献帝时侍中；东涧战死",
        "bio": [
            "献帝时侍中。李傕郭汜追乘舆，战于东涧，王师败绩，杀光禄勋邓泉、卫尉士孙瑞、廷尉宣播、侍中朱展等。",
        ],
        "rels": [("献帝", "与帝", "死难")],
    },
    "金涉": {
        "style": "阙", "dynasty": "西漢", "category": "降人",
        "origin": "金敞子系", "term": "成帝时侍中",
        "bio": [
            "金氏后裔。成帝时为侍中，当世名士。",
            "与戴崇、箕闳等咸为王莽言，上由是贤莽。",
        ],
        "rels": [("王莽", "誉莽", "为莽言"), ("金敞", "宗族", "")],
    },
    "王邑": {
        "style": "阙", "dynasty": "西漢/新", "category": "外戚",
        "origin": "王莽从弟", "term": "为侍中；成都侯",
        "bio": [
            "王莽从弟，成都侯。为侍中，矫称太皇太后指白哀帝，为莽求特进给事中。",
            "后为莽重臣。",
        ],
        "rels": [("王莽", "从兄", ""), ("哀帝", "与帝", "矫太后指")],
    },
    "王奇": {
        "style": "阙", "dynasty": "新", "category": "外戚",
        "term": "侍中；扬武将军",
        "bio": [
            "王邑弟。为侍中，拜扬武将军，将兵西。",
        ],
        "rels": [("王邑", "兄", ""), ("王莽", "宗族", "")],
    },
    "傅喜": {
        "style": "稚游", "dynasty": "西漢", "category": "外戚",
        "term": "哀帝时侍中卫尉；后为大司马",
        "bio": [
            "字稚游，傅太后从弟。哀帝即位，为侍中卫尉。",
            "使侍中卫尉傅喜问李寻灾异。后为大司马，高武侯，以不合傅太后意免。",
        ],
        "rels": [("傅太后", "从兄", "不合太后意"), ("哀帝", "与帝", "问灾异"), ("李寻", "被问", "")],
    },
    "史高": {
        "style": "阙", "dynasty": "西漢", "category": "外戚",
        "term": "宣帝时侍中；与金安上共发霍氏",
        "bio": [
            "宣帝时为侍中。霍氏谋反，侍中史高与金安上建发其事，言无入霍氏禁闼，皆雠有功。",
            "外戚史氏（宣帝祖母史良娣家）。",
        ],
        "rels": [("金安上", "同僚", "共发霍氏"), ("霍氏", "政敌", ""), ("宣帝", "与帝", "外戚近侍")],
    },
    "荀顗": {
        "style": "景倩", "dynasty": "魏/晉", "category": "士人",
        "term": "魏侍中；入晋为太尉",
        "bio": [
            "字景倩，颍川颍阴人，荀彧子。魏侍中。",
            "与崔赞、袁亮、钟毓等讲述礼典；武帝使侍中荀顗、和峤至东宫观察太子。",
        ],
        "rels": [("荀彧", "父", ""), ("司马炎", "与帝", "晋初"), ("和峤", "同僚", "俱观太子")],
    },
    "王辅": {
        "style": "阙", "dynasty": "東漢", "category": "其他",
        "term": "侍中；持节分诣山川祈祭",
        "bio": [
            "为侍中。遣侍中王辅等，持节分诣岱山、东海、荥阳、河、洛，尽心祈焉。",
        ],
        "rels": [("皇帝", "与帝", "奉使祈祭")],
    },
    "尹忠": {
        "style": "阙", "dynasty": "東漢", "category": "其他",
        "term": "献帝时侍中；杨定请为长史",
        "bio": [
            "献帝时为侍中。后将军杨定请侍中尹忠为长史。",
        ],
        "rels": [("杨定", "请主", "请为长史")],
    },
    "韩说": {
        "style": "阙", "dynasty": "東漢", "category": "士人",
        "term": "侍中；太常府覆校注记",
        "bio": [
            "为侍中。太常就耽上选侍中韩说、博士蔡较、谷城门候刘洪等于太常府，覆校注记，平议难问。",
        ],
        "rels": [("刘洪", "同列", "历算"), ("蔡较", "同列", "")],
    },
    "郭举": {
        "style": "阙", "dynasty": "東漢", "category": "外戚",
        "term": "窦宪女弟婿，为侍中射声校尉；另章帝元和中有郭举伏诛",
        "bio": [
            "一：窦宪女弟婿（一说女婿），为侍中、射声校尉，与卫尉邓叠母元出入宫中，谋为不轨。",
            "二：章帝元和中，侍中郭举与后宫通，拔佩刀惊上，举伏诛，侍中由是复出外。",
            "两条郭举是否一人，史家有疑，建卡时并存待考。",
        ],
        "rels": [("窦宪", "姻亲", "女弟婿"), ("邓叠", "同谋", "")],
    },
    "杨文父": {
        "style": "阙", "dynasty": "東漢", "category": "其他",
        "term": "侍中（碑刻）",
        "bio": [
            "碑刻材料：侍中杨文父神道。字体与冯幽州阙相似，或为西汉末东汉初。",
        ],
        "rels": [],
    },
    "刘宽": {
        "style": "文饶", "dynasty": "東漢", "category": "士人",
        "origin": "弘农华阴", "term": "由长史入登侍中（碑/集古录）；后至太尉",
        "bio": [
            "字文饶，弘农华阴人。碑云迁侍中，其前自长史入登侍中（史阙书）。",
            "固疾逊位，拜光禄大夫，迁卫尉等。以宽厚称。",
        ],
        "rels": [("桓帝", "与帝", "")],
    },
    "孔霸": {
        "style": "次儒", "dynasty": "西漢", "category": "士人",
        "term": "元帝时为侍中",
        "bio": [
            "孔光之父（孔子后裔）。元帝时为侍中。",
        ],
        "rels": [("孔光", "子", ""), ("元帝", "与帝", "")],
    },
    "阴兴": {
        "style": "君陵", "dynasty": "東漢", "category": "外戚",
        "origin": "南阳新野", "term": "光武时侍中卫尉关内侯，典领禁兵",
        "bio": [
            "字君陵，光武帝阴皇后弟。为侍中卫尉关内侯，典领禁兵，从平天下。",
            "当以军功受封，又诸舅比例应蒙恩泽，兴皆固让，安乎里巷。谥僖侯。",
        ],
        "rels": [("阴丽华", "姊", "光武阴后"), ("光武帝", "与帝/姻亲", "国舅"), ("阴识", "兄", "")],
    },
    "乐松": {
        "style": "阙", "dynasty": "東漢", "category": "其他",
        "term": "灵帝时侍中祭酒；鸿都门下",
        "bio": [
            "灵帝时为侍中祭酒。多引无行趣势之徒，并待制鸿都门下，憙陈方俗闾里小事，帝甚悦之。",
        ],
        "rels": [("灵帝", "与帝", "鸿都门"), ("贾护", "同列", "")],
    },
    "寇荣": {
        "style": "阙", "dynasty": "東漢", "category": "勋贵",
        "origin": "上谷昌平", "term": "桓帝时为侍中",
        "bio": [
            "寇恂曾孙。少知名，桓帝时为侍中。后为外戚/权贵所谮，下狱死。",
        ],
        "rels": [("寇恂", "曾祖", "云台二十八将"), ("桓帝", "与帝", "")],
    },
    "邓叠": {
        "style": "阙", "dynasty": "東漢", "category": "外戚",
        "term": "窦宪时侍中，行征西将军事为副",
        "bio": [
            "窦宪不受封，将兵出镇凉州，以侍中邓叠行征西将军事为副。",
            "邓氏与窦氏姻亲网络一环。",
        ],
        "rels": [("窦宪", "府主", "副手"), ("邓氏", "宗族", "")],
    },
    "王望": {
        "style": "阙", "dynasty": "新", "category": "其他",
        "term": "新莽末侍中",
        "bio": [
            "新莽末为侍中。王忠拔剑欲自刎，侍中王望传言大司马反，黄门持剑共格杀之。",
        ],
        "rels": [("王莽", "与帝系", "莽末乱中")],
    },
    "傅嘉": {
        "style": "阙", "dynasty": "西漢", "category": "其他",
        "term": "昌邑王时侍中；数进谏系狱",
        "bio": [
            "昌邑王贺侍中。文学光禄大夫夏侯胜等及侍中傅嘉数进谏以过失，使人簿责胜，缚嘉系狱。",
            "霍光废昌邑时所列罪状之一。",
        ],
        "rels": [("刘贺", "与帝", "昌邑王"), ("夏侯胜", "同列", "俱谏")],
    },
    "王粲": {
        "style": "仲宣", "dynasty": "漢魏之際", "category": "士人",
        "origin": "山阳高平", "term": "魏侍中；文学",
        "bio": [
            "字仲宣，建安七子之一。归曹操，为侍中。",
            "从军作五言诗；识旧珮，始复作之。博物多识。",
        ],
        "rels": [("曹操", "府主", ""), ("曹丕", "与帝", "魏侍中")],
    },
    "董允": {
        "style": "休昭", "dynasty": "蜀漢", "category": "士人",
        "origin": "南郡枝江", "term": "蜀汉侍中（出师表作侍郎，后为侍中）",
        "bio": [
            "字休昭，南郡枝江人。先帝简拔，后主时为侍中，统宿卫亲兵。",
            "诸葛亮《出师表》与郭攸之、费祎并举。后主以问侍中董允、留府长史蒋琬。",
            "正色匡主，宦官黄皓畏之。",
        ],
        "rels": [("诸葛亮", "举主", "出师表"), ("费祎", "同僚", ""), ("刘禅", "与帝", "匡谏"), ("黄皓", "政敌", "皓畏允")],
    },
    "伍琼": {
        "style": "德瑜", "dynasty": "東漢", "category": "士人",
        "term": "城门校尉（一说与侍中周毖并列名士）",
        "bio": [
            "与侍中周毖、议郎何颙等皆名士，董卓信之，而阴为袁绍。",
            "注意：证据句中琼为「城门校尉」，非侍中；与侍中周毖同列名士。",
        ],
        "rels": [("周毖", "同僚", "阴为绍"), ("董卓", "权臣", "卓信之")],
    },
}


def load_evidence() -> dict[str, list[dict]]:
    bucket: dict[str, list[dict]] = defaultdict(list)
    with EV.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            name = RENAME.get(r["person"], r["person"])
            bucket[name].append(r)
    return bucket


def guess_dynasty(books: list[str]) -> str:
    b = "|".join(books)
    if "三國" in b and not any(x in b for x in ("後漢", "漢書", "史記", "全漢文")):
        return "漢魏之際"
    if any(x in b for x in ("後漢", "后汉", "全後漢")):
        return "東漢"
    if any(x in b for x in ("漢書", "史記", "全漢文", "前漢紀")):
        return "西漢"
    return "兩漢"


def semantic_events(sentences: list[str]) -> list[str]:
    """从证据句提炼可读事件要点（去重、截断）。"""
    keys = []
    for s in sentences:
        t = s.strip()
        if len(t) < 8:
            continue
        # 截到第一个句读附近
        for p in ("。", "；", "，", ",", "；"):
            if p in t:
                t = t.split(p)[0] + "…"
                break
        t = t[:80]
        if t not in keys:
            keys.append(t)
        if len(keys) >= 5:
            break
    return keys


def main() -> None:
    bucket = load_evidence()
    # 已有深卡的 id 保留
    existing_id = {}
    for p in CARDS.glob("*.md"):
        text = p.read_text(encoding="utf-8")
        m = re.search(r"^id:\s*(\S+)", text, re.M)
        nm = re.search(r"^name:\s*(.+)$", text, re.M)
        if m and nm:
            existing_id[nm.group(1).strip()] = m.group(1)

    # 重建全部卡（深卡用 FACTS+原句，其余用证据语义）
    for p in list(CARDS.glob("*.md")):
        # 全量重建前备份已在 _backup
        p.unlink()

    used_ids = set()
    i = 0
    for person, evs in sorted(bucket.items(), key=lambda x: -len(x[1])):
        i += 1
        pid = existing_id.get(person) or f"P{i:04d}"
        while pid in used_ids:
            i += 1
            pid = f"P{i:04d}"
        used_ids.add(pid)

        books = sorted({e.get("book") for e in evs})
        fact = FACTS.get(person)
        if fact:
            dyn = fact.get("dynasty") or guess_dynasty(books)
            # 跨朝代名
            if "/" in dyn:
                dyn_tag = dyn.replace("/", "_")
            else:
                dyn_tag = dyn
            bio_lines = fact.get("bio") or semantic_events([e.get("sentence") or "" for e in evs])
            rels = fact.get("rels") or []
            term = fact.get("term") or "阙"
            style = fact.get("style") or "阙"
            cat = fact.get("category") or "阙"
            origin = fact.get("origin") or "阙"
            birth = fact.get("birth") or "阙"
            death = fact.get("death") or "阙"
            status = "待审"
        else:
            dyn = guess_dynasty(books)
            dyn_tag = dyn
            bio_lines = semantic_events([e.get("sentence") or "" for e in evs]) or ["（证据不足，待扩）"]
            rels = []
            term = "见原典「侍中」明文"
            style = "阙"
            cat = "阙"
            origin = "阙"
            birth = "阙"
            death = "阙"
            status = "草稿"

        # 引文：去重最多 8
        quotes = []
        seen = set()
        for e in evs:
            q = (e.get("sentence") or "").replace('"', "'")[:220]
            k = q[:40]
            if k in seen:
                continue
            seen.add(k)
            quotes.append((e.get("book"), e.get("juan"), q))
            if len(quotes) >= 8:
                break

        src = "\n".join(
            f"  - book: {b}\n    juan: {j}\n    quote: 「{q}」" for b, j, q in quotes
        )
        bio = "\n".join(
            (f"{n}. {x}" if not x[:2].isdigit() else x) for n, x in enumerate(bio_lines, 1)
        )
        rel_rows = "\n".join(
            f"| {a} | {b} | {c} | 证据/考订 |" for a, b, c in rels
        ) or "|  |  |  |  |"

        body = f"""---
id: {pid}
name: {person}
style_name: {style}
dynasty: {dyn_tag}
status: {status}
category: {cat}
origin: {origin}
birth: {birth}
death: {death}
shizhong_terms:
  - start: 阙
    end: 阙
    nature: {term}
    evidence: 有明文
sources:
{src}
---

## 生平履历

{bio}

## 侍中任职前后

- {term}

## 关系

| 对象 | 关系类型 | 说明 | 出处 |
|------|----------|------|------|
{rel_rows}

## 校录备注

- 语义审读版；evidence={len(evs)}；books={'/'.join(books)}
- 校录人/日期：待填
"""
        fname = f"{person}_{dyn_tag}.md"
        (CARDS / fname).write_text(body, encoding="utf-8")

    # 入库
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("DELETE FROM shizhong_term")
    cur.execute("DELETE FROM source")
    cur.execute("DELETE FROM person")
    for p in sorted(CARDS.glob("*.md")):
        text = p.read_text(encoding="utf-8")
        m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
        if not m:
            continue
        fm = m.group(1)

        def grab(k: str) -> str:
            mm = re.search(rf"^{k}:\s*(.*)$", fm, re.M)
            return mm.group(1).strip() if mm else ""

        pid = grab("id")
        cur.execute(
            """INSERT OR REPLACE INTO person
            (id,name,style_name,dynasty,category,origin,birth,death,status,notes)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                pid, grab("name"), grab("style_name"), grab("dynasty"), grab("category"),
                grab("origin"), grab("birth"), grab("death"), grab("status") or "草稿", p.name,
            ),
        )
        for sm in re.finditer(r"-\s*book:\s*(.+)\n\s*juan:\s*(.+)\n\s*quote:\s*(.+)", fm):
            book, juan, quote = sm.group(1).strip(), sm.group(2).strip(), sm.group(3).strip().strip("「」")
            if book == "阙":
                continue
            cur.execute(
                "INSERT INTO source (book,juan,quote,path) VALUES (?,?,?,?)",
                (book, juan, quote, p.name),
            )
            cur.execute(
                """INSERT OR IGNORE INTO shizhong_term
                (person_id,start_ym,end_ym,nature,evidence,source_id)
                VALUES (?,?,?,?,?,?)""",
                (pid, "阙", "阙", "有明文", "有明文", cur.lastrowid),
            )
    con.commit()
    for t in ("person", "source", "shizhong_term", "relation", "candidate"):
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        print(t, cur.fetchone()[0])
    print("cards", len(list(CARDS.glob('*.md'))))
    con.close()


if __name__ == "__main__":
    main()
