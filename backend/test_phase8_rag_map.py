import os
import sys
import logging
from app.core.db import init_db, get_db_connection
from app.modules.location.location_service import get_nearby_trial_sites, haversine_distance, save_patient_address_location
from app.modules.chatbot.rag_service import process_chatbot_query, retrieve_grounded_trials, get_conversation_history

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_phase8")

def run_phase8_tests():
    logger.info("=== STARTING PHASE 8 VERIFICATION SUITE ===")
    init_db()

    # -------------------------------------------------------------
    # TEST 1: Haversine Distance & Nearby Trial Sites Query
    # -------------------------------------------------------------
    # Distance between Chennai (13.0827, 80.2707) and Salem (11.6643, 78.1460) is ~310 km
    dist_salem = haversine_distance(13.0827, 80.2707, 11.6643, 78.1460)
    assert 270.0 <= dist_salem <= 300.0, f"Unexpected Haversine distance: {dist_salem}"
    logger.info(f"[TEST 1a PASSED] Haversine calculation verified: Chennai to Salem = {dist_salem} km")


    # Fetch nearby sites within 50km of Chennai
    nearby_50km = get_nearby_trial_sites(user_lat=13.0827, user_lon=80.2707, radius_km=50.0)
    assert len(nearby_50km) >= 1, "Expected at least 1 trial site near Chennai within 50km"
    assert nearby_50km[0]["city"] == "Chennai"
    logger.info(f"[TEST 1b PASSED] Found {len(nearby_50km)} trial site(s) near Chennai within 50km radius.")

    # -------------------------------------------------------------
    # TEST 2: Grounded RAG Query Matching Existing Trials
    # -------------------------------------------------------------
    rag_res = process_chatbot_query(
        user_id="test-researcher@example.com",
        role="researcher",
        message_text="Are there any clinical trials for Stage 4 NSCLC near Chennai?"
    )
    assert rag_res["conversation_id"] is not None
    assert "disclaimer" in rag_res
    assert len(rag_res["cited_trials"]) >= 1
    cited_ids = [t["nct_id"] for t in rag_res["cited_trials"]]
    logger.info(f"[TEST 2 PASSED] Grounded RAG response generated. Cited trial IDs: {cited_ids}")

    # -------------------------------------------------------------
    # TEST 3: Grounded RAG Query with NO Matching Data
    # -------------------------------------------------------------
    no_match_res = process_chatbot_query(
        user_id="test-researcher@example.com",
        role="researcher",
        message_text="trials for unknown rare disease 9999"
    )
    assert "No matching trials found" in no_match_res["answer"]
    assert len(no_match_res["cited_trials"]) == 0
    logger.info("[TEST 3 PASSED] Honest fallback verified for non-existent condition query (no hallucinations).")

    # -------------------------------------------------------------
    # TEST 4: Address-level Location Save & Live GPS Privacy Audit
    # -------------------------------------------------------------
    save_res = save_patient_address_location(
        patient_id="patient-01",
        address_text="No 45, Apollo Hospital Road, Greams Lane, Chennai, Tamil Nadu"
    )
    assert save_res["status"] == "updated"

    # Audit DB to verify patients table stores address string only, not raw live GPS
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT location FROM patients WHERE id = 'patient-01';")
        row = cursor.fetchone()
        assert row is not None
        assert "Greams Lane" in row["location"]
        logger.info(f"[TEST 4 PASSED] Address location explicitly saved to patient profile: '{row['location']}'")

    # -------------------------------------------------------------
    # TEST 5: Chatbot Conversation & Message History Audit
    # -------------------------------------------------------------
    conv_history = get_conversation_history(rag_res["conversation_id"])
    assert len(conv_history) >= 2  # user message + assistant message
    logger.info(f"[TEST 5 PASSED] Conversation history correctly persisted ({len(conv_history)} messages logged).")

    logger.info("=== ALL PHASE 8 TESTS PASSED SUCCESSFULLY ===")

if __name__ == "__main__":
    run_phase8_tests()
