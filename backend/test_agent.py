import json
from database import init_db, SessionLocal
from agent import run_langgraph_agent, db_search_hcp
from models import Interaction, HCP

def run_tests():
    print("=== STARTING INTEGRATION TESTS ===")
    
    # 1. Initialize and Seed DB
    print("\n1. Initializing and Seeding Database...")
    init_db()
    
    db = SessionLocal()
    hcp_count = db.query(HCP).count()
    interaction_count = db.query(Interaction).count()
    print(f"Database contains {hcp_count} HCPs and {interaction_count} Interactions.")
    db.close()
    
    if hcp_count == 0:
        print("FAIL: Seeding did not create any HCPs.")
        return
    else:
        print("PASS: Database seeded successfully.")

    # 2. Test HCP Search Tool via Agent
    print("\n2. Testing Agent HCP search capability...")
    result_search = run_langgraph_agent(
        message="I want to search for Dr. Sarah Patel and get her profile.",
        current_form_state=None
    )
    print("Agent Response:\n", result_search["response"])
    print("Logs:\n", result_search["logs"])
    print("Updated Form State:\n", json.dumps(result_search["form_state"], indent=2))
    
    if result_search["form_state"].get("hcp_name") == "Dr. Sarah Patel":
        print("PASS: Agent correctly searched and resolved HCP 'Dr. Sarah Patel'.")
    else:
        print("FAIL: Agent failed to resolve HCP 'Dr. Sarah Patel'.")

    # 3. Test Logging Interaction Tool via Agent
    print("\n3. Testing Agent Logging Interaction capability...")
    form_state = result_search["form_state"]
    # Provide topics, sentiment, and instruct agent to log
    log_message = (
        "We met Dr. Sarah Patel today and discussed the OncoBoost Phase III trial results. "
        "She had a positive sentiment. I shared the OncoBoost Starter Packs sample. Please log this."
      )
    result_log = run_langgraph_agent(
        message=f"{log_message} and save interaction.",
        current_form_state=form_state
    )
    print("Agent Response:\n", result_log["response"])
    print("Logs:\n", result_log["logs"])
    print("Updated Form State:\n", json.dumps(result_log["form_state"], indent=2))

    # Verify interaction is actually in DB
    db = SessionLocal()
    latest_interaction = db.query(Interaction).order_by(Interaction.id.desc()).first()
    
    if latest_interaction and latest_interaction.hcp.name == "Dr. Sarah Patel":
        print(f"PASS: Found newly created interaction ID {latest_interaction.id} in DB.")
        print(f"Topics: {latest_interaction.topics_discussed}")
        print(f"Sentiment: {latest_interaction.sentiment}")
        print(f"Samples count: {len(latest_interaction.samples)}")
    else:
        print("FAIL: New interaction was not logged to DB.")
        
    db.close()
    
    print("\n=== INTEGRATION TESTS COMPLETED ===")

if __name__ == "__main__":
    run_tests()
