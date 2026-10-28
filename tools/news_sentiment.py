"""
헤드라인의 방향(호재/악재)을 키워드로 판정합니다.

뉴스 '건수'만 세면 리콜·소송·실적 미스로 뉴스가 폭증한 종목이 '주목받는
종목'으로 올라옵니다. 거래대금까지 같이 터지므로 선정 상위를 차지하게 되는데,
주간 브리핑을 받는 사람은 그것을 추천으로 읽습니다.

LLM 을 쓰지 않는 이유:
- discovery 단계는 재현 가능해야 하고(같은 입력 → 같은 점수) 설명 가능해야 한다
- 이미 받아둔 응답을 재사용하므로 추가 API 호출이 0 이다
키워드 방식은 뉘앙스를 놓치지만, 방향이 명확한 사건(소송·리콜·급락·상향)에서는
충분히 작동하고 어떤 단어로 그렇게 판정했는지 로그로 남는다는 장점이 있습니다.
"""
import re

# 방향이 명확한 표현만 담는다. 'drop', 'rise' 처럼 맥락에 따라 뒤집히는
# 단어는 오판이 많아 일부러 제외했다.
# 실제 헤드라인은 두 단어 사이에 금액·분기·종목명이 끼어든다
# ("Misses Q3 Estimates", "Cuts XYZ Price Target to $40").
# 그래서 핵심 단어 사이에 최대 25자까지 허용한다.
_GAP = r".{0,25}?"

_NEGATIVE = (
    r"lawsuit|sued|sues|litigation|class action",
    r"investigation|investigating|probe|subpoena|antitrust",
    r"fraud|misconduct|accounting (?:irregular|scandal)",
    r"recall(?:s|ed)?",
    r"downgrade[sd]?",
    rf"cuts?{_GAP}(?:price target|target|rating|guidance|outlook|forecast)",
    rf"lowers?{_GAP}(?:guidance|outlook|forecast|target)",
    rf"miss(?:es|ed)?{_GAP}(?:estimates|expectations|views)|disappoint",
    r"plunge|plummet|slump|tumble|crash|sinks?|sell-?off",
    r"layoffs?|job cuts|restructuring",
    r"delist|halt(?:ed)? trading|bankrupt|default|insolven",
    r"short seller|short report",
    r"profit warning|warns? (?:of|on|about)",
    r"resign|steps? down|ousted",
    r"data breach|hacked|ransomware",
    r"weak(?:er)? (?:demand|sales|guidance|outlook)|loss(?:es)? widen",
)

_POSITIVE = (
    rf"beat(?:s|ing)?{_GAP}(?:estimates|expectations|views)|tops{_GAP}estimates",
    r"surge|soar|rally|skyrocket|spike[sd]?|jumps?",
    r"upgrade[sd]?",
    rf"raises?{_GAP}(?:price target|target|guidance|outlook|forecast)",
    rf"hikes?{_GAP}target|lifts?{_GAP}(?:guidance|outlook|target)",
    rf"record{_GAP}(?:revenue|sales|high|quarter|profit|backlog)",
    rf"wins?{_GAP}(?:contract|deal|approval|order|bid)|awarded",
    r"fda (?:approval|clearance)|approved",
    r"partnership|collaborat|joint venture",
    rf"buyback|repurchase|dividend{_GAP}(?:increase|hike|boost|raise)",
    r"expands?|unveils?|launch(?:es|ed)?",
    r"outperform|bullish",
)

_NEG_RE = [re.compile(p, re.IGNORECASE) for p in _NEGATIVE]
_POS_RE = [re.compile(p, re.IGNORECASE) for p in _POSITIVE]


def _classify(headline: str) -> int:
    """헤드라인 하나를 -1(악재) / 0(중립) / +1(호재) 로 분류합니다."""
    neg = sum(1 for r in _NEG_RE if r.search(headline))
    pos = sum(1 for r in _POS_RE if r.search(headline))
    if neg == pos:
        return 0          # 둘 다 걸리거나 둘 다 없으면 판단 보류
    return -1 if neg > pos else 1


def negative_share(news: list[dict]) -> tuple[float, int, int]:
    """
    (악재 비중, 악재 건수, 호재 건수) 를 반환합니다.

    악재 비중은 '방향이 판정된 뉴스' 중 악재의 비율입니다. 중립 뉴스를
    분모에 넣으면 대부분의 종목이 0 에 수렴해 신호가 죽습니다.
    방향을 하나도 못 읽으면 0.0(= 감쇠 없음) 입니다.
    """
    labels = [_classify(n.get("headline", "")) for n in news]
    neg = labels.count(-1)
    pos = labels.count(1)
    directional = neg + pos
    if directional == 0:
        return 0.0, 0, 0
    return neg / directional, neg, pos
