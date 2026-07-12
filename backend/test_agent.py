import json
import random
from database import init_db, SessionLocal
from agent import run_langgraph_agent, db_search_hcp, db_log_interaction
from models import Interaction, HCP, Material, Sample

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

    # 3. Test Logging Interaction capability (Form Fill Only)
    print("\n3. Testing Agent Logging Interaction capability (Form Fill Only)...")
    form_state = result_search["form_state"]
    
    # Generate a unique topic for this test run
    test_id = random.randint(10000, 99999)
    unique_topic = f"OncoBoost Phase III trial results discussion {test_id}"
    
    # Provide topics, sentiment, and instruct agent to log
    log_message = (
        f"We met Dr. Sarah Patel today and discussed {unique_topic}. "
        "She had a positive sentiment. I shared the OncoBoost Starter Packs sample. Please log this."
      )
    result_log = run_langgraph_agent(
        message=f"{log_message} and save interaction.",
        current_form_state=form_state
    )
    print("Agent Response:\n", result_log["response"])
    print("Logs:\n", result_log["logs"])
    print("Updated Form State:\n", json.dumps(result_log["form_state"], indent=2))

    # Verify that the response prompts the user to review and click 'Log Interaction'
    if "please review and click 'log interaction' to save" in result_log["response"].lower():
        print("PASS: Agent responded with correct instructions to click save manually.")
    else:
        print("FAIL: Agent did not prompt user to save manually.")

    # Verify interaction was NOT saved in the database automatically
    db = SessionLocal()
    interaction_exists = db.query(Interaction).filter(
        Interaction.topics_discussed == unique_topic
    ).first()
    db.close()
    
    if not interaction_exists:
        print("PASS: No automatic database insert occurred.")
    else:
        print("FAIL: Database insert occurred automatically from the chat endpoint.")
        
    # 4. Simulate clicking the "Log Interaction" button manually
    print("\n4. Simulating manual Log Interaction button click...")
    db = SessionLocal()
    mat_ids = result_log["form_state"].get("materials_shared", [])
    samp_ids = result_log["form_state"].get("samples_distributed", [])
    mat_names = [db.query(Material).filter(Material.id == mid).first().name for mid in mat_ids if db.query(Material).filter(Material.id == mid).first()]
    samp_names = [db.query(Sample).filter(Sample.id == sid).first().name for sid in samp_ids if db.query(Sample).filter(Sample.id == sid).first()]
    db.close()
    
    db_res = db_log_interaction(
        hcp_id=result_log["form_state"]["hcp_id"],
        type=result_log["form_state"]["type"],
        date=result_log["form_state"]["date"],
        time=result_log["form_state"]["time"],
        attendees="Dr. Sarah Patel, Sales Rep Alex",
        topics_discussed=result_log["form_state"]["topics_discussed"],
        sentiment=result_log["form_state"]["sentiment"],
        outcomes=result_log["form_state"]["outcomes"],
        follow_up_actions=result_log["form_state"]["follow_up_actions"],
        materials_shared=mat_names,
        samples_distributed=samp_names
    )
    
    if db_res["status"] == "success":
        print(f"PASS: Manual log call succeeded. Created Interaction ID: {db_res['interaction_id']}")
    else:
        print(f"FAIL: Manual log call failed: {db_res['message']}")
        
    # Check duplicate prevention
    print("\n5. Testing Duplicate Interaction Prevention...")
    dup_res = db_log_interaction(
        hcp_id=result_log["form_state"]["hcp_id"],
        type=result_log["form_state"]["type"],
        date=result_log["form_state"]["date"],
        time=result_log["form_state"]["time"],
        attendees="Dr. Sarah Patel, Sales Rep Alex",
        topics_discussed=result_log["form_state"]["topics_discussed"],
        sentiment=result_log["form_state"]["sentiment"],
        outcomes=result_log["form_state"]["outcomes"],
        follow_up_actions=result_log["form_state"]["follow_up_actions"],
        materials_shared=mat_names,
        samples_distributed=samp_names
    )
    
    if dup_res["status"] == "error" and "already been logged" in dup_res["message"]:
        print("PASS: Duplicate interaction logging was successfully blocked.")
    else:
        print(f"FAIL: Duplicate interaction check failed: {dup_res}")
        
    print("\n=== INTEGRATION TESTS COMPLETED ===")

if __name__ == "__main__":
    run_tests()
