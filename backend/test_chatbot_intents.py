import os
import sys
import logging
from app.core.db import init_db
from app.modules.chatbot.rag_service import process_chatbot_query, classify_chatbot_intent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_intents")

def test_chatbot_intents():
    init_db()
    logger.info("=== TESTING CHATBOT INTENT CLASSIFIER & ROUTING ===")

    # 1. Greeting Mode Test
    greetings = ["Hello", "Hi", "Hey", "Good morning"]
    for g in greetings:
        intent = classify_chatbot_intent(g)
        assert intent == "greeting", f"Expected 'greeting' for '{g}', got '{intent}'"
        res = process_chatbot_query(user_id="user1", role="patient", message_text=g)
        assert "Clinical Trial Assistant" in res["answer"]
        assert len(res["cited_trials"]) == 0
        logger.info(f"[PASSED] Greeting '{g}' -> Answer: {res['answer'][:70]}...")

    # 2. Symptom / Medical Triage Guidance Mode Test
    symptoms = ["patient has fever", "I have a severe headache", "patient has cough and chest pain"]
    for s in symptoms:
        intent = classify_chatbot_intent(s)
        assert intent == "symptom_guidance", f"Expected 'symptom_guidance' for '{s}', got '{intent}'"
        res = process_chatbot_query(user_id="user1", role="patient", message_text=s)
        assert "doctor" in res["answer"].lower()
        assert len(res["cited_trials"]) == 0
        logger.info(f"[PASSED] Symptom '{s}' -> Answer: {res['answer'][:100]}...")

    # 3. Clinical Trial Search Mode Test
    trial_queries = ["find trials for lung cancer", "Are there any clinical trials for Stage 4 NSCLC near Chennai?"]
    for tq in trial_queries:
        intent = classify_chatbot_intent(tq)
        assert intent == "trial_search", f"Expected 'trial_search' for '{tq}', got '{intent}'"
        res = process_chatbot_query(user_id="user1", role="patient", message_text=tq)
        assert "clinical trial protocol" in res["answer"].lower()
        assert len(res["cited_trials"]) > 0
        logger.info(f"[PASSED] Trial search '{tq}' -> Found {len(res['cited_trials'])} cited trial(s).")

    logger.info("=== ALL CHATBOT INTENT TESTS PASSED SUCCESSFULLY ===")

if __name__ == "__main__":
    test_chatbot_intents()
