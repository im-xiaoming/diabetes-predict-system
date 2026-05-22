from .models import Alert, WatchlistItem


TARGET_NAMES = {
    "NEP": "biến chứng thận",
    "NEU": "biến chứng thần kinh",
    "RET": "biến chứng võng mạc",
    "CV": "biến chứng tim mạch",
    "PER VAS": "biến chứng mạch máu ngoại biên",
}


def message_for(score):
    name = TARGET_NAMES.get(score.target, score.target)
    if score.risk_level == "high":
        return f"Cảnh báo nguy cơ cao {name}. Bác sĩ cần ưu tiên đánh giá hồ sơ."
    return f"Nguy cơ trung bình {name}. Đưa vào danh sách theo dõi thêm."


def create_alerts(pred):
    rows = []
    for score in pred.scores.all():
        if int(score.risk_label) != 1:
            continue
        if score.risk_level != "high":
            continue
        alert, made = Alert.objects.get_or_create(
            score=score,
            defaults={
                "patient": pred.patient,
                "prediction": pred,
                "target": score.target,
                "level": score.risk_level,
                "message": message_for(score),
            },
        )
        if made:
            rows.append(alert)
    return rows


def create_watchlist_items(pred):
    rows = []
    for score in pred.scores.all():
        if int(score.risk_label) != 1:
            continue
        if score.risk_level != "medium":
            continue
        item, made = WatchlistItem.objects.get_or_create(
            score=score,
            defaults={
                "patient": pred.patient,
                "prediction": pred,
                "target": score.target,
                "message": message_for(score),
            },
        )
        if made:
            rows.append(item)
    return rows


def create_workflow_items(pred):
    return {
        "alerts": create_alerts(pred),
        "watchlist": create_watchlist_items(pred),
    }
