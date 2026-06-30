import logging
import random
import re
from collections import Counter
from functools import lru_cache

from celery import shared_task
from django.db import transaction

logger = logging.getLogger(__name__)

KEY_SENTENCE_COUNT = 5
CHOICE_COUNT = 4
DISTRACTOR_COUNT = 3

# Tags added by ingest pipeline — exclude from quiz targeting so lessons stay topic-focused.
_QUIZ_PIPELINE_META_TERMS = frozenset({"ingested", "webpage", "youtube", "pdf"})


@lru_cache(maxsize=1)
def _get_nlp():
    import spacy

    return spacy.load("en_core_web_sm")


def _normalize_np(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip()).lower()


def _collect_noun_phrases(doc):
    """Noun chunks with 1–3 words; returns list of original surface strings."""
    out = []
    for chunk in doc.noun_chunks:
        words = chunk.text.split()
        if 1 <= len(words) <= 3:
            out.append(chunk.text.strip())
    return out


def _all_noun_chunk_surfaces(doc):
    """All noun chunk surfaces (any length) for distractor pool."""
    return [chunk.text.strip() for chunk in doc.noun_chunks if chunk.text.strip()]


def _phrase_to_topic_tag(phrase: str) -> str:
    s = phrase.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s-]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return (s or "topic")[:100]


def _high_freq_noun_phrases(np_list: list[str], top_n: int = 20) -> set[str]:
    if not np_list:
        return set()
    counts = Counter(_normalize_np(p) for p in np_list)
    # Prefer phrases that appear more than once; else top by frequency.
    repeated = {p for p, c in counts.items() if c >= 2}
    if len(repeated) >= 3:
        return repeated
    return {p for p, _ in counts.most_common(max(top_n, 5))}


def _lesson_tag_terms(tags) -> frozenset[str]:
    """Normalize lesson tags into searchable phrases and tokens for quiz targeting."""
    if not isinstance(tags, list):
        return frozenset()
    out: set[str] = set()
    for raw in tags:
        text = str(raw).strip().lower()
        if not text:
            continue
        text = text.replace("_", " ")
        norm = _normalize_np(text)
        if norm:
            out.add(norm)
        for word in re.findall(r"[a-z][a-z0-9]*", text):
            if len(word) >= 3:
                out.add(word)
    return frozenset(t for t in out if t not in _QUIZ_PIPELINE_META_TERMS)


def _normalized_text_matches_tag(sl_norm: str, term: str) -> bool:
    """Match tag phrases/tokens to normalized lesson text (handles simple plural ↔ singular)."""
    if len(term) < 2:
        return False
    if term in sl_norm:
        return True
    if len(term) >= 5 and term.endswith("s"):
        stem = term[:-1]
        if len(stem) >= 3 and stem in sl_norm:
            return True
    if len(term) >= 4 and not term.endswith("s") and f"{term}s" in sl_norm:
        return True
    return False


def _tag_sentence_bonus(sentence: str, tag_terms: frozenset[str]) -> int:
    """Extra weight for sentences that explicitly reflect declared lesson tags (e.g. loops)."""
    if not tag_terms:
        return 0
    sl = _normalize_np(sentence)
    bonus = 0
    matched = set()
    for term in tag_terms:
        if len(term) < 2 or term in matched:
            continue
        if _normalized_text_matches_tag(sl, term):
            matched.add(term)
            bonus += 5
    return bonus


def _score_sentence(sentence: str, high_freq: set[str], tag_terms: frozenset[str] | None = None) -> int:
    sl = sentence.lower()
    score = 0
    for phrase in high_freq:
        if phrase and phrase in sl:
            score += 1
    if tag_terms:
        score += _tag_sentence_bonus(sentence, tag_terms)
    return score


def _key_sentences(
    doc,
    lesson_text: str,
    high_freq: set[str],
    tag_terms: frozenset[str] | None = None,
) -> list[str]:
    sents = [s.text.strip() for s in doc.sents if s.text.strip()]
    if not sents:
        parts = re.split(r"(?<=[.!?])\s+", lesson_text.strip())
        sents = [p.strip() for p in parts if p.strip()]
    scored = [(s, _score_sentence(s, high_freq, tag_terms)) for s in sents]
    scored.sort(key=lambda x: (-x[1], -len(x[0])))
    seen = set()
    ordered = []
    for s, _ in scored:
        key = s.lower()
        if key not in seen:
            seen.add(key)
            ordered.append(s)
        if len(ordered) >= KEY_SENTENCE_COUNT:
            break
    return ordered[:KEY_SENTENCE_COUNT]


def _np_freq_map(np_list: list[str]) -> Counter:
    return Counter(_normalize_np(p) for p in np_list)


def _chunk_tag_bonus(surface_norm: str, tag_terms: frozenset[str] | None) -> int:
    if not tag_terms or not surface_norm:
        return 0
    bonus = 0
    for t in tag_terms:
        if len(t) >= 3 and _normalized_text_matches_tag(surface_norm, t):
            bonus += 6
        elif len(surface_norm) >= 3 and _normalized_text_matches_tag(t, surface_norm):
            bonus += 4
    return bonus


def _best_chunk_for_question(
    sent_doc,
    global_freq: Counter,
    tag_terms: frozenset[str] | None = None,
):
    candidates = []
    for chunk in sent_doc.noun_chunks:
        words = chunk.text.split()
        if not (1 <= len(words) <= 3):
            continue
        surface = chunk.text.strip()
        key = _normalize_np(surface)
        freq_score = global_freq.get(key, 0) + _chunk_tag_bonus(key, tag_terms)
        candidates.append((freq_score, len(surface), surface, chunk))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (-x[0], -x[1], x[2]))
    return candidates[0][3]


def _mask_sentence(sentence: str, chunk) -> str | None:
    start, end = chunk.start_char, chunk.end_char
    if start < 0 or end > len(sentence) or start >= end:
        return None
    return sentence[:start] + "[?]" + sentence[end:]


def _pick_distractors(
    correct: str,
    pool: list[str],
    k: int = DISTRACTOR_COUNT,
) -> list[str]:
    correct_n = _normalize_np(correct)
    seen = {correct_n}
    out = []
    random.shuffle(pool)
    for p in pool:
        pn = _normalize_np(p)
        if pn in seen or not pn:
            continue
        seen.add(pn)
        out.append(p.strip())
        if len(out) >= k:
            break
    # Remaining slots: other noun phrases as single-token keywords from pool
    if len(out) < k:
        tokens = []
        for p in pool:
            tokens.extend(re.findall(r"[A-Za-z]{3,}", p))
        random.shuffle(tokens)
        for t in tokens:
            tl = t.lower()
            if tl == correct_n or tl in seen:
                continue
            seen.add(tl)
            out.append(t)
            if len(out) >= k:
                break
    return out[:k]


def _build_mcq(
    sentence: str,
    distractor_pool: list[str],
    global_freq: Counter,
    tag_terms: frozenset[str] | None = None,
):
    nlp = _get_nlp()
    sent_doc = nlp(sentence)
    chunk = _best_chunk_for_question(sent_doc, global_freq, tag_terms)
    if chunk is None:
        return None
    correct = chunk.text.strip()
    stem = _mask_sentence(sentence, chunk)
    if stem is None or "[?]" not in stem:
        return None
    distractors = _pick_distractors(correct, [p for p in distractor_pool if p])
    if len(distractors) < DISTRACTOR_COUNT:
        return None

    deck = [correct] + distractors[:DISTRACTOR_COUNT]
    if len(set(_normalize_np(x) for x in deck)) < CHOICE_COUNT:
        return None
    random.shuffle(deck)
    try:
        correct_index = next(
            i for i, c in enumerate(deck) if _normalize_np(c) == _normalize_np(correct)
        )
    except StopIteration:
        return None
    topic_tag = _phrase_to_topic_tag(correct)
    return {
        "stem": stem.strip(),
        "choices": deck,
        "correct_index": correct_index,
        "topic_tag": topic_tag,
    }


@shared_task
def generate_quiz_for_lesson(lesson_id: int) -> int | None:
    from courses.models import Lesson
    from quizzes.models import Question, Quiz

    try:
        lesson = Lesson.objects.get(pk=lesson_id)
    except Lesson.DoesNotExist:
        logger.error("generate_quiz_for_lesson: Lesson id=%s not found", lesson_id)
        return None

    content = (lesson.content or "").strip()
    nlp = _get_nlp()
    doc = nlp(content)
    np_surfaces = _collect_noun_phrases(doc)
    counts = Counter(_normalize_np(p) for p in np_surfaces)
    if counts:
        top_norm, _ = counts.most_common(1)[0]
        for p in np_surfaces:
            if _normalize_np(p) == top_norm:
                lesson.topic_tag = p[:100]
                break
    else:
        lesson.topic_tag = ""

    tag_terms = _lesson_tag_terms(lesson.tags or [])
    high_freq = _high_freq_noun_phrases(np_surfaces) | set(tag_terms)
    key_sents = _key_sentences(doc, content, high_freq, tag_terms)
    global_freq = _np_freq_map(np_surfaces)

    distractor_pool = _all_noun_chunk_surfaces(doc)
    mcqs = []
    for sent in key_sents:
        row = _build_mcq(sent, distractor_pool, global_freq, tag_terms)
        if row:
            mcqs.append(row)
        if len(mcqs) >= KEY_SENTENCE_COUNT:
            break

    with transaction.atomic():
        lesson.save(update_fields=["topic_tag"])
        Quiz.objects.filter(lesson_id=lesson.pk).delete()
        quiz = Quiz.objects.create(
            lesson=lesson,
            passing_score=60,
            generation_status=Quiz.GenerationStatus.DONE,
        )
        for i, row in enumerate(mcqs):
            Question.objects.create(
                quiz=quiz,
                order=i,
                stem=row["stem"],
                choices=row["choices"],
                correct_index=row["correct_index"],
                topic_tag=row["topic_tag"],
                question_type=Question.QuestionType.MCQ,
                is_published=True,
            )

        course_id = lesson.course_id

        def _enqueue_ready_check():
            from courses.tasks import check_course_ready

            check_course_ready.delay(course_id)

        transaction.on_commit(_enqueue_ready_check)
    return lesson_id
