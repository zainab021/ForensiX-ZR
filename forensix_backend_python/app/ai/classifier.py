from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from app.ai.training_data import REPORT_SAMPLES

_descriptions = [row[0] for row in REPORT_SAMPLES]
_categories = [row[1] for row in REPORT_SAMPLES]
_priorities = [row[2] for row in REPORT_SAMPLES]


def _build_pipeline():
    return Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), stop_words="english")),
        ("clf", LogisticRegression(max_iter=1000)),
    ])


category_model = _build_pipeline()
category_model.fit(_descriptions, _categories)

priority_model = _build_pipeline()
priority_model.fit(_descriptions, _priorities)


def classify_report(description: str) -> dict:
    category_probs = category_model.predict_proba([description])[0]
    priority_probs = priority_model.predict_proba([description])[0]

    category_idx = category_probs.argmax()
    priority_idx = priority_probs.argmax()

    category = str(category_model.classes_[category_idx])
    priority = str(priority_model.classes_[priority_idx])
    confidence = float(category_probs[category_idx])

    return {
        "category": category,
        "priority": priority,
        "confidence": round(confidence, 4),
    }
