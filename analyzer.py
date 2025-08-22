import time
import re
from typing import Dict, Any, List, Tuple
from difflib import SequenceMatcher
from config import DUPLICATE_SIMILARITY_THRESHOLD, HIGH_PRIORITY_SLACK_USER, UNANSWERED_SECONDS
from storage import read_all


def _normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def _similar(a: str, b: str) -> float:
    return SequenceMatcher(a=_normalize_text(a), b=_normalize_text(b)).ratio()


def _classify_item(text: str) -> str:
    t = _normalize_text(text)
    if any(x in t for x in ["crash", "ошибка", "баг", "не работает", "urgent", "срочно"]):
        return "🔴 Action"
    if any(x in t for x in ["ждём", "wait", "ожидание", "ожидаю", "pending"]):
        return "🟡 Waiting for"
    if any(x in t for x in ["инфо", "справка", "reference", "note", "заметка"]):
        return "🟢 Reference"
    return "⚪ Archive"


def _priority_score(item: Dict[str, Any]) -> int:
    score = 0
    text = (item.get("text") or item.get("name") or "")
    t = _normalize_text(text)
    if item.get("source") == "slack" and item.get("user") == HIGH_PRIORITY_SLACK_USER:
        score += 50
    if "deadline_ts" in item and item["deadline_ts"]:
        # Closer deadlines => higher score
        try:
            remain = item["deadline_ts"] - time.time()
            if remain < 0:
                score += 40
            elif remain < 6 * 3600:
                score += 30
            elif remain < 24 * 3600:
                score += 15
        except Exception:
            pass
    if any(k in t for k in ["crash", "critical", "падение", "критично"]):
        score += 30
    if item.get("no_response_secs") and item["no_response_secs"] > UNANSWERED_SECONDS:
        score += 20
    return score


def analyze() -> Dict[str, Any]:
    data = read_all()
    slack = data.get("slack_messages", [])
    tasks = data.get("clickup_tasks", [])

    # Build simple link candidates by similarity
    links: List[Tuple[int, int, float]] = []  # (slack_idx, task_idx, sim)
    for i, sm in enumerate(slack):
        stext = sm.get("text") or ""
        if not stext:
            continue
        for j, t in enumerate(tasks):
            ttext = t.get("name") or t.get("description") or ""
            if not ttext:
                continue
            sim = _similar(stext, ttext)
            if sim >= DUPLICATE_SIMILARITY_THRESHOLD:
                links.append((i, j, sim))

    # Classification and priority
    enriched_items: List[Dict[str, Any]] = []
    now = time.time()

    for i, sm in enumerate(slack):
        text = sm.get("text") or ""
        cls = _classify_item(text)
        last_reply_ts = sm.get("last_reply_ts") or sm.get("ts")
        no_resp_secs = None
        try:
            if last_reply_ts:
                no_resp_secs = max(0, now - float(last_reply_ts))
        except Exception:
            no_resp_secs = None
        enriched = {
            "source": "slack",
            "text": text,
            "channel": sm.get("channel"),
            "user": sm.get("user"),
            "class": cls,
            "no_response_secs": no_resp_secs,
        }
        enriched["priority"] = _priority_score(enriched)
        enriched_items.append(enriched)

    for t in tasks:
        text = t.get("name") or t.get("description") or ""
        cls = _classify_item(text)
        enriched = {
            "source": "clickup",
            "name": t.get("name"),
            "text": text,
            "status": (t.get("status") or {}).get("status"),
            "deadline_ts": t.get("due_date_ts"),
        }
        enriched["priority"] = _priority_score(enriched)
        enriched_items.append(enriched)

    # Actions suggestions
    suggestions: List[str] = []
    if links:
        suggestions.append(f"Найдено пересечений Slack↔ClickUp: {len(links)} — стоит связать обсуждения с задачами")

    # Detect potential duplicates in tasks
    duplicates: List[Tuple[int, int, float]] = []
    for i in range(len(tasks)):
        for j in range(i + 1, len(tasks)):
            a = tasks[i].get("name") or ""
            b = tasks[j].get("name") or ""
            if a and b:
                sim = _similar(a, b)
                if sim >= DUPLICATE_SIMILARITY_THRESHOLD:
                    duplicates.append((i, j, sim))
    if duplicates:
        suggestions.append(f"Найдены возможные дубли задач: {len(duplicates)} — стоит объединить")

    result = {
        "links": links,
        "duplicates": duplicates,
        "items": sorted(enriched_items, key=lambda x: x.get("priority", 0), reverse=True),
        "suggestions": suggestions,
    }
    return result