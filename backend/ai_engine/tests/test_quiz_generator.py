from django.test import SimpleTestCase

from ai_engine.services.quiz_generator import (
    QuizGenerationError,
    normalize_topic_tag,
    post_process_questions,
    validate_question,
)


class QuizGeneratorValidationTests(SimpleTestCase):
    def test_normalize_topic_tag(self):
        self.assertEqual(normalize_topic_tag("Python OOP"), "python_oop")

    def test_validate_mcq(self):
        q = validate_question(
            {
                "question": "What is a class in Python?",
                "type": "mcq",
                "difficulty": "easy",
                "bloom_level": "remember",
                "topic_tag": "oop",
                "options": ["A blueprint", "A loop", "A file", "A socket"],
                "correct_answer": "A blueprint",
                "explanation": "Classes define object structure and behavior.",
            }
        )
        self.assertEqual(q["type"], "mcq")

    def test_validate_true_false(self):
        q = validate_question(
            {
                "question": "Python supports inheritance?",
                "type": "true_false",
                "difficulty": "medium",
                "bloom_level": "understand",
                "topic_tag": "inheritance",
                "options": ["True", "False"],
                "correct_answer": "True",
                "explanation": "Python classes can inherit from other classes.",
            }
        )
        self.assertEqual(q["options"], ["True", "False"])

    def test_reject_opinion_in_post_process(self):
        items = [
            {
                "question": "In your opinion, is Python the best language?",
                "type": "mcq",
                "difficulty": "easy",
                "bloom_level": "remember",
                "topic_tag": "python",
                "options": ["Yes", "No", "Maybe", "Sometimes"],
                "correct_answer": "Yes",
                "explanation": "This is subjective and not valid.",
            },
            {
                "question": "What does OOP stand for?",
                "type": "mcq",
                "difficulty": "easy",
                "bloom_level": "remember",
                "topic_tag": "oop",
                "options": [
                    "Object-Oriented Programming",
                    "Open Output Protocol",
                    "Optional Operand Pointer",
                    "Ordered Operation Process",
                ],
                "correct_answer": "Object-Oriented Programming",
                "explanation": "OOP is a programming paradigm based on objects.",
            },
            {
                "question": "Encapsulation hides data?",
                "type": "true_false",
                "difficulty": "easy",
                "bloom_level": "understand",
                "topic_tag": "encapsulation",
                "options": ["True", "False"],
                "correct_answer": "True",
                "explanation": "Encapsulation bundles data with methods that operate on it.",
            },
        ]
        with self.assertRaises(QuizGenerationError):
            post_process_questions(items)
