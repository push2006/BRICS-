"""Simple keyword classifier — swap in an LLM/API call later if you want
smarter tagging; this keeps the template dependency-free by default."""
import config as C

KEYWORDS = {
    "GEOPOLITICS": ["summit", "diplomat", "bilateral", "foreign minister", "president", "prime minister"],
    "TRADE": ["trade", "export", "import", "tariff", "supply chain", "currency"],
    "SANCTIONS": ["sanction", "embargo", "blacklist", "restricted"],
    "RISK": ["attack", "explosion", "unrest", "coup", "conflict", "ceasefire"],
    "CONFERENCE": ["conference", "meeting", "forum", "declaration", "summit"],
}


def classify(article):
    text = (article.get("title", "") + " " + article.get("summary", "")).lower()
    for cat, words in KEYWORDS.items():
        if any(w in text for w in words):
            return cat
    return "GENERAL"


def classify_all(articles):
    out = []
    for a in articles:
        a["category"] = classify(a)
        if a["category"] in C.ACTIVE_CATEGORIES:
            out.append(a)
    return out


def is_critical(article):
    text = (article.get("title", "") + " " + article.get("summary", "")).lower()
    return any(kw.strip().lower() in text for kw in C.CRITICAL_KEYWORDS)


# Being published by a BRICS-country outlet does NOT make a story
# BRICS-relevant (e.g. local sports, domestic policy, a leader's
# unrelated activity). A single leader-name mention alone is too loose
# — "Modi pays tribute to 9/11 victims" would false-positive on "modi".
# Require either a strong standalone signal, or a leader name combined
# with an actual diplomatic/summit term.
STRONG_SIGNALS = [
    "brics", "new delhi declaration", "bharat mandapam", "18th brics",
    "brics summit", "brics nations", "brics countries", "brics leaders",
]
LEADER_NAMES = [
    "modi", "putin", "xi jinping", "ramaphosa", "lula", "abiy ahmed",
    "prabowo", "pezeshkian", "el-sisi", "al nahyan", "faisal al saud",
]
DIPLOMATIC_TERMS = [
    "summit", "bilateral meeting", "bilateral talks", "joint statement",
    "multilateral", "state visit", "delegation", "foreign minister meeting",
    "trade agreement", "trade deal", "de-dollarization", "currency pact",
    "diplomatic", "sanctions", "new delhi", "declaration",
]


def is_brics_relevant(article):
    text = (article.get("title", "") + " " + article.get("summary", "")).lower()
    if any(kw in text for kw in STRONG_SIGNALS):
        return True
    has_leader = any(kw in text for kw in LEADER_NAMES)
    has_diplomatic_term = any(kw in text for kw in DIPLOMATIC_TERMS)
    return has_leader and has_diplomatic_term


def filter_brics(articles):
    return [a for a in articles if is_brics_relevant(a)]
