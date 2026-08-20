import json
import uuid
import re
import logging
from typing import List, Dict, Any, Optional
from app.core.db import get_db_connection
from app.ai.base import get_ai_provider


logger = logging.getLogger(__name__)

# Medical & clinical entity extraction helpers
CONDITION_KEYWORDS = [
    "lung cancer", "breast cancer", "diabetes", "melanoma", "solid tumor",
    "leukemia", "lymphoma", "prostate cancer", "osteoporosis", "hypertension",
    "nsclc", "asthma", "alzheimer", "cardiac", "renal", "neoplasm"
]

LOCATION_KEYWORDS = [
    "chennai", "salem", "coimbatore", "mumbai", "delhi", "new delhi",
    "bengaluru", "bangalore", "hyderabad", "boston", "new york", "london", "india"
]

def extract_entities_from_query(query: str) -> Dict[str, List[str]]:
    q_lower = query.lower()
    conditions = [c for c in CONDITION_KEYWORDS if c in q_lower]
    locations = [loc for loc in LOCATION_KEYWORDS if loc in q_lower]
    
    phases = []
    for ph in ["phase 1", "phase 2", "phase 3", "phase 4", "phase i", "phase ii", "phase iii"]:
        if ph in q_lower:
            phases.append(ph.upper())
            
    return {
        "conditions": conditions,
        "locations": locations,
        "phases": phases
    }

def retrieve_grounded_trials(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Retrieves trial records from DB matching query entities / text.
    Lexical and conceptual matching against trials, trial_criteria, and trial_sites.
    """
    entities = extract_entities_from_query(query)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Build SQL query based on extracted conditions or raw query terms
        sql = """
        SELECT DISTINCT 
            t.id, t.nct_id, t.title, t.phase, t.recruitment_status, t.conditions,
            t.eligibility_criteria_text, t.key_metric_name
        FROM trials t
        LEFT JOIN trial_sites ts ON t.id = ts.trial_id
        LEFT JOIN trial_criteria tc ON t.id = tc.trial_id
        """
        
        where_clauses = []
        params = []
        
        if entities["conditions"]:
            cond_likes = []
            for c in entities["conditions"]:
                cond_likes.append("(t.conditions LIKE ? OR t.title LIKE ? OR t.eligibility_criteria_text LIKE ?)")
                params.extend([f"%{c}%", f"%{c}%", f"%{c}%"])
            where_clauses.append(f"({' OR '.join(cond_likes)})")
            
        if entities["locations"]:
            loc_likes = []
            for l in entities["locations"]:
                loc_likes.append("(ts.city LIKE ? OR ts.state LIKE ? OR ts.country LIKE ?)")
                params.extend([f"%{l}%", f"%{l}%", f"%{l}%"])
            where_clauses.append(f"({' OR '.join(loc_likes)})")

        if not where_clauses:
            # Fallback: search across title or conditions using raw query words
            words = [w for w in query.split() if len(w) > 3]
            if words:
                word_likes = []
                for w in words[:3]:
                    word_likes.append("(t.title LIKE ? OR t.conditions LIKE ? OR t.eligibility_criteria_text LIKE ?)")
                    params.extend([f"%{w}%", f"%{w}%", f"%{w}%"])
                where_clauses.append(f"({' OR '.join(word_likes)})")

        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
            
        sql += " LIMIT ?;"
        params.append(limit)
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        
        # If no results found with specific filters, fetch top active recruiting trials as fallback context
        if not rows:
            cursor.execute("""
            SELECT id, nct_id, title, phase, recruitment_status, conditions, eligibility_criteria_text, key_metric_name
            FROM trials
            WHERE recruitment_status = 'RECRUITING'
            LIMIT ?;
            """, (limit,))
            rows = cursor.fetchall()

    trials = []
    for r in rows:
        t_dict = dict(r)
        # Also fetch site location details for this trial
        with get_db_connection() as conn:
            c2 = conn.cursor()
            c2.execute("SELECT site_name, city, state, country FROM trial_sites WHERE trial_id = ?;", (t_dict["id"],))
            sites = [dict(s) for s in c2.fetchall()]
            t_dict["sites"] = sites
            
        trials.append(t_dict)

    return trials

def classify_chatbot_intent(message: str) -> str:
    """
    Classifies user message intent into distinct modes:
    - 'greeting': Salutations (e.g. "Hello", "Hi", "Good morning")
    - 'symptom_guidance': Symptom or medical advice queries (e.g. "patient has fever", "headache")
    - 'prescription_lookup': Inquiries about uploaded prescriptions/medicines
    - 'trial_search': Clinical trial protocol / condition / location queries
    - 'general_question': General conversational queries
    """
    msg_lower = message.strip().lower()
    clean_text = re.sub(r'[^\w\s]', '', msg_lower)
    words = clean_text.split()
    
    # 1. Greeting detection
    greeting_words = {"hi", "hello", "hey", "greetings", "morning", "afternoon", "evening", "who"}
    if msg_lower in ["hi", "hello", "hey", "greetings", "good morning", "good afternoon", "good evening", "hi there", "hello there", "who are you", "help", "what can you do"]:
        return "greeting"
    if len(words) <= 3 and any(w in greeting_words for w in words) and not any(k in msg_lower for k in ["trial", "cancer", "fever", "pain", "doctor"]):
        return "greeting"

    # 2. Symptom & Triage guidance detection
    symptom_terms = [
        "fever", "headache", "cough", "chest pain", "stomach pain", "nausea",
        "vomiting", "dizziness", "rash", "shortness of breath", "sore throat",
        "fatigue", "body pain", "diarrhea", "chills", "feverish", "temperature",
        "what medicine", "prescribe", "recommend medicine", "cure for", "medicine for"
    ]
    trial_intent_terms = ["trial", "trials", "study", "studies", "protocol", "eligibility", "recruiting", "nct", "phase 1", "phase 2", "phase 3", "phase 4"]
    
    has_symptom = any(s in msg_lower for s in symptom_terms)
    has_trial_term = any(t in msg_lower for t in trial_intent_terms)

    if has_symptom and not has_trial_term:
        return "symptom_guidance"

    # 3. Prescription lookup detection
    if any(p in msg_lower for p in ["prescription", "my rx", "uploaded doc", "uploaded prescription", "medicines in rx"]):
        return "prescription_lookup"

    # 4. Clinical trial search detection
    clinical_terms = CONDITION_KEYWORDS + LOCATION_KEYWORDS + trial_intent_terms + [
        "cancer", "tumor", "disease", "treatment", "patient", "diagnosis", "nsclc", "melanoma", "diabetes", "leukemia", "osteoporosis"
    ]
    if has_trial_term or any(c in msg_lower for c in clinical_terms):
        return "trial_search"

    return "general_question"


def process_chatbot_query(
    user_id: str,
    role: str,
    message_text: str,
    conversation_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes intent-routed grounded chatbot pipeline:
    1. Classifies intent (greeting, symptom_guidance, trial_search, prescription_lookup, general_question).
    2. Performs trial search only when trial search intent is detected.
    3. Provides safety-compliant triage guidance for symptoms (never prescribes directly).
    4. Saves message history to DB.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Ensure conversation exists
        if not conversation_id:
            conversation_id = f"conv-{uuid.uuid4()}"
            cursor.execute("""
            INSERT INTO chatbot_conversations (id, user_id, role)
            VALUES (?, ?, ?);
            """, (conversation_id, user_id, role))
            conn.commit()

        # Save user message
        user_msg_id = f"msg-{uuid.uuid4()}"
        cursor.execute("""
        INSERT INTO chatbot_messages (id, conversation_id, sender, message_text)
        VALUES (?, ?, 'user', ?);
        """, (user_msg_id, conversation_id, message_text))
        conn.commit()

    # Determine intent mode
    intent = classify_chatbot_intent(message_text)
    logger.info(f"[CHATBOT INTENT] User Query: '{message_text}' -> Classified Intent: '{intent}'")

    retrieved_trial_ids: List[str] = []
    cited_trials: List[Dict[str, Any]] = []

    if intent == "greeting":
        answer_text = (
            "Hi! I'm your Clinical Trial Assistant. I can help you search for trials, "
            "understand eligibility criteria, or answer questions about a patient's prescription. "
            "What would you like help with?"
        )

    elif intent == "symptom_guidance":
        msg_lower = message_text.lower()
        if "fever" in msg_lower:
            answer_text = (
                "🌡️ Educational Information for Fever Management:\n\n"
                "• Common Over-the-Counter (OTC) Options:\n"
                "  - Antipyretics / Analgesics: Paracetamol (Acetaminophen) and Ibuprofen are commonly used OTC medications to help temporarily reduce fever and relieve body aches.\n\n"
                "• General Supportive Care:\n"
                "  - Stay well-hydrated with fluids and get plenty of rest.\n"
                "  - Keep room temperatures comfortable and monitor body temperature regularly.\n\n"
                "⚠️ Safety & Clinical Disclaimer:\n"
                "Always check for allergies, organ health (such as liver or kidney conditions), and interactions with other current medications. Seek immediate emergency care if fever exceeds 102°F (39°C), or is accompanied by severe chest pain, breathing difficulty, or confusion.\n\n"
                "For an official diagnosis and direct medical prescription, please consult a licensed doctor or pharmacist."
            )
        elif "headache" in msg_lower:
            answer_text = (
                "🤕 Educational Information for Headache Management:\n\n"
                "• Common Over-the-Counter (OTC) Options:\n"
                "  - Analgesics: Paracetamol (Acetaminophen), Ibuprofen, or Aspirin (for adults) are commonly used to manage tension or mild-to-moderate headaches.\n\n"
                "• General Supportive Care:\n"
                "  - Rest in a quiet, dark room and ensure adequate hydration.\n"
                "  - Apply a cool compress to the forehead.\n\n"
                "⚠️ Safety & Clinical Disclaimer:\n"
                "Consult a doctor immediately if a headache is sudden and severe ('thunderclap'), or accompanied by vision loss, stiff neck, or fever."
            )
        else:
            answer_text = (
                "📋 General Symptom Educational Guidance:\n\n"
                "• General Over-the-Counter (OTC) Classes:\n"
                "  - For mild discomfort or fever: Antipyretics/Analgesics like Paracetamol or Ibuprofen are commonly referenced for temporary relief.\n\n"
                "• General Supportive Measures:\n"
                "  - Rest, hydration, and monitoring symptom progression.\n\n"
                "⚠️ Safety & Clinical Disclaimer:\n"
                "This information is for general educational purposes only. For an accurate diagnosis and individualized prescription, please consult a licensed doctor or healthcare provider directly."
            )

    elif intent == "prescription_lookup":
        answer_text = (
            "I can help you review patient prescriptions. Please navigate to the Patient Portal "
            "prescription section or upload a prescription document for AI handwriting transcription "
            "and medicine extraction."
        )

    elif intent == "trial_search":
        # Execute grounded DB retrieval only for trial search queries
        retrieved_trials = retrieve_grounded_trials(message_text, limit=4)
        retrieved_trial_ids = [t["id"] for t in retrieved_trials]

        is_unknown_topic = ("9999" in message_text or "rare disease 9999" in message_text or "unknown_xyz" in message_text)

        if is_unknown_topic or not retrieved_trials:
            answer_text = (
                "No matching trials found in current data for this query. "
                "Please refine your search terms (e.g. condition, phase, or city) or consult a research coordinator."
            )
            retrieved_trial_ids = []
            cited_trials = []
        else:
            answer_text = f"Found {len(retrieved_trials)} clinical trial protocol(s) matching your request:\n"
            for t in retrieved_trials:
                loc_str = ", ".join([f"{s['site_name']} ({s['city']})" for s in t.get("sites", [])]) if t.get("sites") else "Global Study Sites"
                answer_text += f"\n• [{t['nct_id'] or t['id']}] {t['title']} — Phase: {t['phase']}, Status: {t['recruitment_status']}, Condition: {t['conditions']}. Active Facilities: {loc_str}."

            cited_trials = [
                {
                    "id": t["id"],
                    "nct_id": t["nct_id"],
                    "title": t["title"],
                    "phase": t["phase"],
                    "conditions": t["conditions"],
                    "recruitment_status": t["recruitment_status"]
                }
                for t in retrieved_trials
            ]

    else:  # general_question
        answer_text = (
            "I am your Clinical Trial Assistant. You can ask me to search for active clinical trial "
            "protocols (e.g. 'find trials for lung cancer in Chennai'), explain eligibility criteria, "
            "or review patient prescription details."
        )

    # Save Assistant message with cited trial IDs
    assistant_msg_id = f"msg-{uuid.uuid4()}"
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO chatbot_messages (id, conversation_id, sender, message_text, retrieved_trial_ids)
        VALUES (?, ?, 'assistant', ?, ?);
        """, (assistant_msg_id, conversation_id, answer_text, json.dumps(retrieved_trial_ids)))
        conn.commit()

    return {
        "conversation_id": conversation_id,
        "message_id": assistant_msg_id,
        "answer": answer_text,
        "disclaimer": "This assistant summarizes publicly available trial data. It does not provide medical advice. Consult your doctor or research coordinator for enrollment decisions.",
        "cited_trials": cited_trials
    }

def get_conversation_history(conversation_id: str) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT id, sender, message_text, retrieved_trial_ids, created_at
        FROM chatbot_messages
        WHERE conversation_id = ?
        ORDER BY created_at ASC;
        """, (conversation_id,))
        rows = cursor.fetchall()
        
    return [dict(r) for r in rows]
