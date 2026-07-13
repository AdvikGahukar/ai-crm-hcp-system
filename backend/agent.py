import os
import json
import re
from typing import Dict, List, Optional, TypedDict, Annotated, Sequence
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# Database imports
from database import SessionLocal
from models import HCP, Material, Sample, Interaction, FollowUpTask

load_dotenv()

# Check if LangGraph and LangChain are installed
try:
    from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
    from langchain_core.tools import tool
    from langchain_groq import ChatGroq
    from langgraph.graph import StateGraph, END
    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False

# Define State Schema
class AgentState(TypedDict):
    messages: List[dict] # Custom message list to be JSON serializable easily: [{"role": "user"/"assistant"/"tool", "content": "..."}]
    current_form_state: dict
    logs: List[str]
    session_id: str

# Database tools implementation functions (independent of langchain for flexibility)
def db_search_hcp(name_query: str) -> List[dict]:
    db = SessionLocal()
    try:
        hcps = db.query(HCP).filter(HCP.name.ilike(f"%{name_query}%")).all()
        return [{"id": h.id, "name": h.name, "specialty": h.specialty, "clinic": h.clinic, "email": h.email, "phone": h.phone} for h in hcps]
    finally:
        db.close()

def db_get_hcp_history(hcp_id: int) -> List[dict]:
    db = SessionLocal()
    try:
        interactions = db.query(Interaction).filter(Interaction.hcp_id == hcp_id).order_by(Interaction.date.desc(), Interaction.time.desc()).limit(3).all()
        result = []
        for i in interactions:
            result.append({
                "id": i.id,
                "type": i.type,
                "date": i.date,
                "time": i.time,
                "topics_discussed": i.topics_discussed,
                "sentiment": i.sentiment,
                "outcomes": i.outcomes,
                "follow_up_actions": i.follow_up_actions,
                "materials": [m.name for m in i.materials],
                "samples": [s.name for s in i.samples]
            })
        return result
    finally:
        db.close()

def db_search_materials(query: str) -> dict:
    db = SessionLocal()
    try:
        m_matches = db.query(Material).filter(Material.name.ilike(f"%{query}%")).all()
        s_matches = db.query(Sample).filter(Sample.name.ilike(f"%{query}%")).all()
        return {
            "materials": [{"id": m.id, "name": m.name, "type": m.type, "description": m.description} for m in m_matches],
            "samples": [{"id": s.id, "name": s.name, "stock_quantity": s.stock_quantity, "description": s.description} for s in s_matches]
        }
    finally:
        db.close()

def db_log_interaction(
    hcp_id: int,
    type: str,
    date: str,
    time: str,
    attendees: Optional[str] = None,
    topics_discussed: Optional[str] = None,
    sentiment: Optional[str] = "Neutral",
    outcomes: Optional[str] = None,
    follow_up_actions: Optional[str] = None,
    materials_shared: Optional[List[str]] = None, # List of material names or parts
    samples_distributed: Optional[List[str]] = None # List of sample names or parts
) -> dict:
    db = SessionLocal()
    try:
        # Check for duplicates (same HCP, date, time, and topic)
        duplicate = db.query(Interaction).filter(
            Interaction.hcp_id == hcp_id,
            Interaction.date == date,
            Interaction.time == time,
            Interaction.topics_discussed == topics_discussed
        ).first()
        if duplicate:
            return {"status": "error", "message": "This interaction has already been logged."}
            
        hcp = db.query(HCP).filter(HCP.id == hcp_id).first()
        if not hcp:
            return {"status": "error", "message": f"HCP with ID {hcp_id} not found."}
            
        interaction = Interaction(
            hcp_id=hcp_id,
            type=type,
            date=date,
            time=time,
            attendees=attendees,
            topics_discussed=topics_discussed,
            sentiment=sentiment,
            outcomes=outcomes,
            follow_up_actions=follow_up_actions
        )
        
        # Link materials
        if materials_shared:
            for mat_name in materials_shared:
                mat = db.query(Material).filter(Material.name.ilike(f"%{mat_name}%")).first()
                if mat:
                    interaction.materials.append(mat)
                    
        # Link samples and deduct stock
        if samples_distributed:
            for samp_name in samples_distributed:
                samp = db.query(Sample).filter(Sample.name.ilike(f"%{samp_name}%")).first()
                if samp:
                    interaction.samples.append(samp)
                    # Deduct 1 sample from stock
                    if samp.stock_quantity > 0:
                        samp.stock_quantity -= 1
                        
        db.add(interaction)
        db.commit()
        db.refresh(interaction)
        
        # If there's follow-up actions and date, auto-create a task
        # Let's see if we can extract a follow-up task
        if follow_up_actions:
            # Generate a due date, e.g. 7 days from now (simple default)
            # In a production app, we would parse the date, let's use date or default
            due_date = date # Default to same date as interaction or parse it
            task = FollowUpTask(
                hcp_id=hcp_id,
                interaction_id=interaction.id,
                description=follow_up_actions,
                due_date=due_date,
                status="Pending"
            )
            db.add(task)
            db.commit()
            
        return {
            "status": "success",
            "message": f"Interaction successfully logged with ID {interaction.id} for {hcp.name}.",
            "interaction_id": interaction.id,
            "hcp_name": hcp.name,
            "form_state": {
                "hcp_id": hcp.id,
                "hcp_name": hcp.name,
                "type": interaction.type,
                "date": interaction.date,
                "time": interaction.time,
                "attendees": interaction.attendees,
                "topics_discussed": interaction.topics_discussed,
                "sentiment": interaction.sentiment,
                "outcomes": interaction.outcomes,
                "follow_up_actions": interaction.follow_up_actions,
                "materials_shared": [m.id for m in interaction.materials],
                "samples_distributed": [s.id for s in interaction.samples]
            }
        }
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": f"Failed to log interaction: {str(e)}"}
    finally:
        db.close()

def db_edit_interaction(interaction_id: int, updates: dict) -> dict:
    db = SessionLocal()
    try:
        interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
        if not interaction:
            return {"status": "error", "message": f"Interaction with ID {interaction_id} not found."}
            
        # Update allowed fields
        allowed_fields = ["type", "date", "time", "attendees", "topics_discussed", "sentiment", "outcomes", "follow_up_actions"]
        for key, value in updates.items():
            if key in allowed_fields:
                setattr(interaction, key, value)
                
        # Handle materials updates if provided
        if "materials_shared" in updates:
            # Re-link materials
            interaction.materials = []
            for mat_id in updates["materials_shared"]:
                mat = db.query(Material).filter(Material.id == mat_id).first()
                if mat:
                    interaction.materials.append(mat)
                    
        # Handle samples updates if provided
        if "samples_distributed" in updates:
            interaction.samples = []
            for samp_id in updates["samples_distributed"]:
                samp = db.query(Sample).filter(Sample.id == samp_id).first()
                if samp:
                    interaction.samples.append(samp)
                    
        db.commit()
        db.refresh(interaction)
        
        return {
            "status": "success",
            "message": f"Interaction {interaction.id} successfully updated.",
            "form_state": {
                "hcp_id": interaction.hcp_id,
                "hcp_name": interaction.hcp.name if interaction.hcp else "",
                "type": interaction.type,
                "date": interaction.date,
                "time": interaction.time,
                "attendees": interaction.attendees,
                "topics_discussed": interaction.topics_discussed,
                "sentiment": interaction.sentiment,
                "outcomes": interaction.outcomes,
                "follow_up_actions": interaction.follow_up_actions,
                "materials_shared": [m.id for m in interaction.materials],
                "samples_distributed": [s.id for s in interaction.samples]
            }
        }
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": f"Failed to edit interaction: {str(e)}"}
    finally:
        db.close()

def db_schedule_followup(hcp_id: int, description: str, due_date: str) -> dict:
    db = SessionLocal()
    try:
        hcp = db.query(HCP).filter(HCP.id == hcp_id).first()
        if not hcp:
            return {"status": "error", "message": f"HCP with ID {hcp_id} not found."}
            
        task = FollowUpTask(
            hcp_id=hcp_id,
            description=description,
            due_date=due_date,
            status="Pending"
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return {
            "status": "success",
            "message": f"Scheduled task: '{description}' for {hcp.name} by {due_date}.",
            "task_id": task.id
        }
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": f"Failed to schedule follow-up: {str(e)}"}
    finally:
        db.close()


# Let's define the LangChain tools if LangChain is installed
if HAS_LANGCHAIN:
    @tool
    def search_hcp(name_query: str) -> str:
        """Search for Healthcare Professionals (HCPs) in the database by name."""
        results = db_search_hcp(name_query)
        return json.dumps(results, indent=2)

    @tool
    def get_hcp_history(hcp_id: int) -> str:
        """Get the recent interaction history of a specific HCP by their ID."""
        results = db_get_hcp_history(hcp_id)
        return json.dumps(results, indent=2)

    @tool
    def search_materials(query: str) -> str:
        """Search available clinical materials (PDFs, study papers) and drug samples by name."""
        results = db_search_materials(query)
        return json.dumps(results, indent=2)

    @tool
    def log_interaction(
        hcp_id: int,
        type: str,
        date: str,
        time: str,
        attendees: Optional[str] = None,
        topics_discussed: Optional[str] = None,
        sentiment: Optional[str] = "Neutral",
        outcomes: Optional[str] = None,
        follow_up_actions: Optional[str] = None,
        materials_shared: Optional[List[str]] = None,
        samples_distributed: Optional[List[str]] = None
    ) -> str:
        """Log a new interaction with an HCP in the database."""
        result = db_log_interaction(
            hcp_id=hcp_id,
            type=type,
            date=date,
            time=time,
            attendees=attendees,
            topics_discussed=topics_discussed,
            sentiment=sentiment,
            outcomes=outcomes,
            follow_up_actions=follow_up_actions,
            materials_shared=materials_shared,
            samples_distributed=samples_distributed
        )
        return json.dumps(result, indent=2)

    @tool
    def edit_interaction(interaction_id: int, updates: dict) -> str:
        """Edit details of an existing logged interaction by ID. Updates is a dictionary of fields to modify."""
        result = db_edit_interaction(interaction_id, updates)
        return json.dumps(result, indent=2)

    @tool
    def schedule_followup(hcp_id: int, description: str, due_date: str) -> str:
        """Schedule a follow-up task/meeting with an HCP by ID."""
        result = db_schedule_followup(hcp_id, description, due_date)
        return json.dumps(result, indent=2)

    TOOLS_LIST = [search_hcp, get_hcp_history, search_materials, log_interaction, edit_interaction, schedule_followup]
else:
    TOOLS_LIST = []


# SMART MOCK AGENT (Fallback when GROQ_API_KEY is not set or LangGraph is not ready)
class MockAgent:
    def __init__(self):
        pass
        
    def process_message(self, message: str, current_form_state: dict) -> dict:
        logs = []
        response = ""
        form_state = current_form_state.copy() if current_form_state else {
            "hcp_id": None, "hcp_name": "", "type": "Meeting", "date": "", "time": "",
            "attendees": "", "topics_discussed": "", "sentiment": "Neutral",
            "outcomes": "", "follow_up_actions": "", "materials_shared": [], "samples_distributed": []
        }
        
        message_lower = message.lower()
        
        # 1. Search HCP simulation
        # Look for "dr. sarah", "sarah patel", "dr. chen", "robert", "amanda", "jane"
        hcp_match = None
        if "sarah" in message_lower or "patel" in message_lower:
            hcp_match = db_search_hcp("Sarah")[0]
        elif "robert" in message_lower or "chen" in message_lower:
            hcp_match = db_search_hcp("Robert")[0]
        elif "amanda" in message_lower or "ross" in message_lower:
            hcp_match = db_search_hcp("Amanda")[0]
        elif "jane" in message_lower or "smith" in message_lower:
            hcp_match = db_search_hcp("Jane")[0]

        if hcp_match:
            logs.append(f"Tool Executed: search_hcp(name_query='{hcp_match['name'].split()[-1]}')")
            form_state["hcp_id"] = hcp_match["id"]
            form_state["hcp_name"] = hcp_match["name"]
            
        # 2. Extract Sentiment
        if "positive" in message_lower:
            form_state["sentiment"] = "Positive"
        elif "negative" in message_lower:
            form_state["sentiment"] = "Negative"
        elif "neutral" in message_lower:
            form_state["sentiment"] = "Neutral"
            
        # 3. Extract Type
        if "email" in message_lower:
            form_state["type"] = "Email"
        elif "call" in message_lower:
            form_state["type"] = "Call"
        elif "meeting" in message_lower or "met" in message_lower:
            form_state["type"] = "Meeting"
        elif "video" in message_lower or "zoom" in message_lower:
            form_state["type"] = "Video Conference"

        # 4. Extract materials & samples
        materials_found = []
        samples_found = []
        if "oncoboost phase iii" in message_lower or "oncoboost trial" in message_lower or "oncoboost pdf" in message_lower:
            materials_found.append("OncoBoost Phase III PDF")
        if "cardioshield brochure" in message_lower:
            materials_found.append("CardioShield Brochure")
        if "neuromax study" in message_lower or "neuromax efficacy" in message_lower:
            materials_found.append("NeuroMax Efficacy Study")
            
        if "oncoboost starter" in message_lower or "oncoboost sample" in message_lower:
            samples_found.append("OncoBoost Starter Packs")
        if "cardioshield sample" in message_lower:
            samples_found.append("CardioShield Daily Dose")
        if "neuromax sample" in message_lower:
            samples_found.append("NeuroMax 10mg Tablets")

        if materials_found or samples_found:
            logs.append(f"Tool Executed: search_materials(query='extracted materials/samples')")
            
            # Map material names to IDs
            db = SessionLocal()
            for m_name in materials_found:
                m = db.query(Material).filter(Material.name == m_name).first()
                if m and m.id not in form_state.get("materials_shared", []):
                    form_state["materials_shared"] = list(set((form_state.get("materials_shared") or []) + [m.id]))
            for s_name in samples_found:
                s = db.query(Sample).filter(Sample.name == s_name).first()
                if s and s.id not in form_state.get("samples_distributed", []):
                    form_state["samples_distributed"] = list(set((form_state.get("samples_distributed") or []) + [s.id]))
            db.close()

        # 5. Extract topics, outcomes, follow-ups
        # Try some Regex extraction or default parsing
        topics_match = re.search(r"discuss(?:ed)? (.*?)(?:\.|$|and sentiment|shared|requested)", message, re.IGNORECASE)
        if topics_match:
            form_state["topics_discussed"] = topics_match.group(1).strip()
            
        outcomes_match = re.search(r"outcome(?:s)? is (.*?)(?:\.|$|and)", message, re.IGNORECASE)
        if outcomes_match:
            form_state["outcomes"] = outcomes_match.group(1).strip()

        followup_match = re.search(r"(?:schedule|follow up|todo|next step) (.*?)(?:\.|$)", message, re.IGNORECASE)
        if followup_match:
            form_state["follow_up_actions"] = followup_match.group(1).strip()
            
        # 6. Check for date/time in message or use current
        import datetime
        now = datetime.datetime.now()
        if not form_state.get("date"):
            form_state["date"] = now.strftime("%Y-%m-%d")
        if not form_state.get("time"):
            form_state["time"] = now.strftime("%H:%M")
            
        # 7. Action trigger: "log this" or "save"
        if "log this" in message_lower or "save interaction" in message_lower or "submit" in message_lower:
            if not form_state.get("hcp_id"):
                response = "I detected you want to log an interaction, but I couldn't identify which HCP. Please specify the doctor's name."
            else:
                response = "I've filled the form. Please review and click 'Log Interaction' to save."
        
        # 8. Action trigger: "edit" or "update"
        elif "edit interaction" in message_lower or "update interaction" in message_lower or "change details" in message_lower:
            # Find the last interaction ID if not specified
            db = SessionLocal()
            last_i = None
            if form_state.get("hcp_id"):
                last_i = db.query(Interaction).filter(Interaction.hcp_id == form_state["hcp_id"]).order_by(Interaction.id.desc()).first()
            if not last_i:
                last_i = db.query(Interaction).order_by(Interaction.id.desc()).first()
            db.close()
            
            if last_i:
                logs.append(f"Tool Executed: edit_interaction(interaction_id={last_i.id}, updates=...)")
                # Perform edit
                updates = {
                    "type": form_state["type"],
                    "sentiment": form_state["sentiment"],
                    "topics_discussed": form_state["topics_discussed"],
                    "outcomes": form_state["outcomes"],
                    "follow_up_actions": form_state["follow_up_actions"],
                    "materials_shared": form_state["materials_shared"],
                    "samples_distributed": form_state["samples_distributed"]
                }
                res = db_edit_interaction(last_i.id, updates)
                if res["status"] == "success":
                    response = f"Successfully updated the last logged interaction (ID: {last_i.id}) with {res['form_state']['hcp_name']}."
                    form_state = res["form_state"]
                else:
                    response = f"Failed to update interaction: {res['message']}"
            else:
                response = "I couldn't find a logged interaction to update."
                
        # 9. Normal chat or query
        else:
            # Just search or help
            if hcp_match:
                response = f"I've found {hcp_match['name']} ({hcp_match['specialty']} at {hcp_match['clinic']}) and updated the form on the left. "
                
                # Fetch history as well
                logs.append(f"Tool Executed: get_hcp_history(hcp_id={hcp_match['id']})")
                history = db_get_hcp_history(hcp_match['id'])
                if history:
                    response += f"Based on history, the last interaction was on {history[0]['date']} regarding '{history[0]['topics_discussed'][:40]}...'. "
                    
                # response += "What topics did you discuss in today's interaction?"
            else:
                response = "Hello! I am your CRM Assistant. You can describe an interaction (e.g. 'Met Dr. Sarah Patel, discussed OncoBoost, positive sentiment') and tell me to 'log this', or search for doctors, study reports, or schedule tasks."

        # Append structured JSON state to response
        # Using the standard json block formatting we discussed
        response += f"\n\n```json\n{json.dumps(form_state, indent=2)}\n```"
        return {"response": response, "form_state": form_state, "logs": logs}


# LANGGRAPH REAL IMPLEMENTATION (when GROQ_API_KEY is present)
def _run_langgraph_agent_internal(message: str, current_form_state: dict, session_id: str = "default") -> dict:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or not HAS_LANGCHAIN:
        # Fallback to MockAgent
        mock = MockAgent()
        return mock.process_message(message, current_form_state)

    # Initialize LLM
    # Groq API model gemma2-9b-it or llama-3.3-70b-versatile
    llm = ChatGroq(
        groq_api_key=api_key,
        model_name="llama-3.3-70b-versatile",
        temperature=0.1
    )

    # Bind tools
    llm_with_tools = llm.bind_tools(TOOLS_LIST)

    # State update helper functions for tool invocations
    execution_logs = []
    
    # Custom state object to update
    form_state_tracker = current_form_state.copy() if current_form_state else {
        "hcp_id": None, "hcp_name": "", "type": "Meeting", "date": "", "time": "",
        "attendees": "", "topics_discussed": "", "sentiment": "Neutral",
        "outcomes": "", "follow_up_actions": "", "materials_shared": [], "samples_distributed": []
    }

    # Define Node 1: Call Model
    def call_model(state):
        messages = []
        
        # System Prompt
        sys_msg = SystemMessage(
            content=(
                "You are an expert AI medical CRM representative assistant for field sales agents. "
                "Your objective is to assist the user in logging, updating, and querying HCP interactions. "
                "You have access to tools: search_hcp, get_hcp_history, search_materials, log_interaction, edit_interaction, schedule_followup.\n"
                "Current Form State:\n"
                f"{json.dumps(form_state_tracker, indent=2)}\n\n"
                "Instructions:\n"
                "1. If the user mentions a doctor (HCP) by name, always call search_hcp first to get the correct ID.\n"
                "2. DO NOT call the log_interaction tool. If the user wants to log the interaction, extract all the fields, write them into the form_state JSON block, and respond with a message exactly like: 'I've filled the form. Please review and click 'Log Interaction' to save.'\n"
                "3. If the user wants to update or edit, use the edit_interaction tool.\n"
                "4. At the end of your response, you MUST append a JSON code block with the key 'form_state' representing the final state of the form fields to sync. "
                "Always write the JSON inside ```json ... ``` formatting block so it can be parsed. Ensure ALL keys: hcp_id, hcp_name, type, date, time, attendees, topics_discussed, sentiment, outcomes, follow_up_actions, materials_shared, samples_distributed are present in the JSON."
            )
        )
        
        messages.append(sys_msg)
        
        # Load previous messages (limit to last 10 for speed/context limits)
        for msg in state.get("messages", [])[-10:]:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
            elif msg["role"] == "system":
                messages.append(SystemMessage(content=msg["content"]))
                
        # Add the new message if it's not already in history
        if not messages or messages[-1].content != message:
            messages.append(HumanMessage(content=message))

        response = llm_with_tools.invoke(messages)
        return {"messages": state["messages"] + [{"role": "assistant", "content": response.content, "tool_calls": getattr(response, "tool_calls", None)}], "response_message": response}

    # Define Node 2: Execute Tools
    def execute_tools(state):
        last_message = state["messages"][-1]
        tool_calls = last_message.get("tool_calls", [])
        
        tool_messages = []
        for call in tool_calls:
            name = call["name"]
            args = call["args"]
            call_id = call["id"]
            
            execution_logs.append(f"Tool Executed: {name}(**{json.dumps(args)})")
            
            # Execute tool logic based on name
            result_str = ""
            if name == "search_hcp":
                result_str = search_hcp.invoke(args)
                # Auto update form_state_tracker with first matching HCP
                try:
                    hcps = json.loads(result_str)
                    if hcps:
                        form_state_tracker["hcp_id"] = hcps[0]["id"]
                        form_state_tracker["hcp_name"] = hcps[0]["name"]
                except:
                    pass
            elif name == "get_hcp_history":
                result_str = get_hcp_history.invoke(args)
            elif name == "search_materials":
                result_str = search_materials.invoke(args)
            elif name == "log_interaction":
                result_str = log_interaction.invoke(args)
                # Auto update state
                try:
                    res = json.loads(result_str)
                    if res["status"] == "success":
                        form_state_tracker.update(res["form_state"])
                except:
                    pass
            elif name == "edit_interaction":
                result_str = edit_interaction.invoke(args)
                try:
                    res = json.loads(result_str)
                    if res["status"] == "success":
                        form_state_tracker.update(res["form_state"])
                except:
                    pass
            elif name == "schedule_followup":
                result_str = schedule_followup.invoke(args)
                
            tool_messages.append({"role": "tool", "content": result_str, "name": name, "tool_call_id": call_id})
            
        return {"messages": state["messages"] + tool_messages}

    # Conditional edge router
    def route_tools(state):
        last_message = state["response_message"]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return END

    # Setup StateGraph
    workflow = StateGraph(dict)
    
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", execute_tools)
    
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", route_tools, {"tools": "tools", END: END})
    workflow.add_edge("tools", "agent")
    
    graph = workflow.compile()
    
    # Run the graph
    # Convert string-based history representation to graph state
    initial_state = {
        "messages": [{"role": "user", "content": message}],
        "current_form_state": current_form_state or {},
        "logs": []
    }
    
    output_state = graph.invoke(initial_state)
    
    # Extract final AIMessage
    final_reply = ""
    for msg in reversed(output_state["messages"]):
        if msg["role"] == "assistant" and msg.get("content"):
            final_reply = msg["content"]
            break
            
    # Try to parse the JSON state from response, or use the form_state_tracker
    parsed_form_state = form_state_tracker.copy()
    try:
        json_blocks = re.findall(r"```json\s*(.*?)\s*```", final_reply, re.DOTALL)
        if json_blocks:
            # Use the last json block
            block_data = json.loads(json_blocks[-1])
            if isinstance(block_data, dict):
                # Sync form fields
                for k, v in block_data.items():
                    if k in parsed_form_state:
                        parsed_form_state[k] = v
    except Exception as e:
        print(f"Error parsing LLM form state: {e}")
        
    # Append the state to reply if it doesn't already have it (ensures consistency)
    if "```json" not in final_reply:
        final_reply += f"\n\n```json\n{json.dumps(parsed_form_state, indent=2)}\n```"

    return {
        "response": final_reply,
        "form_state": parsed_form_state,
        "logs": execution_logs
    }

def run_langgraph_agent(message: str, current_form_state: dict, session_id: str = "default") -> dict:
    try:
        return _run_langgraph_agent_internal(message, current_form_state, session_id)
    except Exception as e:
        print(f"Error running live LangGraph agent: {e}. Falling back to MockAgent.")
        mock = MockAgent()
        res = mock.process_message(message, current_form_state)
        res["response"] = f"{res['response']}\n\n[Notice: Groq API Rate Limit or Error encountered (using local simulation)] "
        return res

