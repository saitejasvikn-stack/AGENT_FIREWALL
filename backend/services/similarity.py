import re
from sqlalchemy.orm import Session
from models import Contribution

SEEDED_KNOWN_CORPUS = [
    "deep learning based fundus image classification for diabetic retinopathy screening on mobile edge devices using compressed convolutional networks",
    "benchmarking small language models for low resource kannada text classification using fine tuned transformer representations"
]

def get_5grams(text: str) -> set[tuple[str, ...]]:
    words = re.findall(r'\w+', text.lower())
    if len(words) < 5:
        return {tuple(words)} if words else set()
    return {tuple(words[i:i+5]) for i in range(len(words) - 4)}

def jaccard_similarity(set1: set, set2: set) -> float:
    if not set1 or not set2:
        return 0.0
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    return intersection / union if union > 0 else 0.0

class SimilarityService:
    @staticmethod
    def check_similarity(db: Session, content_text: str) -> float:
        input_5grams = get_5grams(content_text)
        if not input_5grams:
            return 0.0

        max_score = 0.0

        # Check against seeded known corpus
        for doc in SEEDED_KNOWN_CORPUS:
            doc_5grams = get_5grams(doc)
            score = jaccard_similarity(input_5grams, doc_5grams)
            if score > max_score:
                max_score = score

        # Check against previous contributions
        contributions = db.query(Contribution).all()
        for c in contributions:
            c_5grams = get_5grams(c.content_text)
            score = jaccard_similarity(input_5grams, c_5grams)
            if score > max_score:
                max_score = score

        return round(max_score, 4)

similarity_service = SimilarityService()
