"""Collapses the same story reported by multiple outlets into one item."""
from difflib import SequenceMatcher
import config as C


def _similar(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def dedupe(articles, threshold=None):
    threshold = threshold or C.DEDUPE_THRESHOLD
    kept = []
    for art in articles:
        dup = False
        for k in kept:
            if _similar(art["title"], k["title"]) >= threshold:
                k.setdefault("corroborated_by", [k["source"]])
                if art["source"] not in k["corroborated_by"]:
                    k["corroborated_by"].append(art["source"])
                dup = True
                break
        if not dup:
            kept.append(art)
    return kept
