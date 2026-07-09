import os
import json
import re
import datetime
from typing import List, Dict, Any

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from app.config import settings
from app.agent.state import AgentState
from app.agent.tools import sales_tools, search_hcps, suggest_clinical_content, log_interaction, edit_interaction, get_hcp_history

# Define the system prompt
SYSTEM_PROMPT = """You are an AI-first CRM assistant for life sciences field representatives.
Your task is to help the rep log and edit interactions with Healthcare Professionals (HCPs).

You have access to the following sales tools:
1. `search_hcps(query)` - Search for HCPs in the database by name or specialty.
2. `get_hcp_history(hcp_name)` - Retrieve the latest 3 interactions with a specific HCP.
3. `suggest_clinical_content(topic)` - Recommend materials (PDFs, brochures) or drug samples based on discussed topics.
4. `log_interaction(...)` - Save a new HCP interaction to the database.
5. `edit_interaction(interaction_id, ...)` - Modify an existing logged interaction.

Flow guidelines:
1. When the user describes an interaction (e.g. "I met Dr. Sharma today..."):
   - Call `search_hcps` with the name (e.g. "Sharma") to resolve the proper HCP name and ID.
   - Call `suggest_clinical_content` if they mention topics or products (like "OncoBoost" or "efficacy").
   - Synthesize the details (HCP ID, name, date, discussed items) and construct the form state.
2. When returning your final response to the user, you MUST append the current/updated form state in a markdown block labeled `json_form_state`.
   The frontend will parse this block to populate the structured UI form.
   Example:
   ```json_form_state
   {
     "hcp_id": 1,
     "hcp_name": "Dr. Ramesh Sharma",
     "interaction_type": "Meeting",
     "date": "2025-04-19",
     "time": "19:36",
     "attendees": ["Dr. Ramesh Sharma", "Jane Doe"],
     "topics_discussed": "Discussed OncoBoost Phase III trial results.",
     "materials_shared": ["OncoBoost Phase III PDF"],
     "samples_distributed": ["OncoBoost 10mg Starter Pack"],
     "sentiment": "Positive",
     "outcomes": "HCP was highly receptive. Requested study details.",
     "follow_up_actions": "Schedule follow-up meeting in 2 weeks."
   }
   ```
3. If the user explicitly asks to "log", "save", "submit" the interaction, call the `log_interaction` tool. Use values from the current form state for any parameters not specified by the user.
4. When the `log_interaction` tool returns a success status, you must return a final response confirming the logging and output an empty/cleared form state in the `json_form_state` block (with fields reset to default values, setting date and time to the current date/time) so that the form resets.
5. If they ask to "edit" or "modify" or "update" an interaction with an ID (e.g., "Change the date of interaction 4 to tomorrow"), call the `edit_interaction` tool.
6. When calling `edit_interaction`, use values from the current form state for any parameters not specified by the user.

Always remain helpful, concise, and professional.
"""

# Initialize the model or create the mock model
def get_model():
    if not settings.GROQ_API_KEY:
        print("WARNING: GROQ_API_KEY is not set. Using Mock LLM Agent.")
        return MockLLMAgent()
    
    # Standard ChatGroq
    try:
        model = ChatGroq(
            model=settings.GROQ_MODEL,
            groq_api_key=settings.GROQ_API_KEY,
            temperature=0.1
        )
        return model.bind_tools(sales_tools)
    except Exception as e:
        print(f"Error initializing ChatGroq ({settings.GROQ_MODEL}): {e}. Falling back to Mock LLM Agent.")
        return MockLLMAgent()


class MockLLMAgent:
    """
    Mock LLM agent that simulates tool calling and response formulation for CRM sales logging.
    Used when GROQ_API_KEY is not provided.
    """
    def __init__(self):
        pass
    
    def bind_tools(self, tools):
        return self
        
    def _get_form_state(self, messages: List[Any]) -> Dict[str, Any]:
        for msg in messages:
            if isinstance(msg, SystemMessage):
                match = re.search(r'Current Form State \(Draft\):\n(\{.*?\})', msg.content, re.DOTALL)
                if match:
                    try:
                        return json.loads(match.group(1))
                    except Exception:
                        pass
        return {}

    def _get_current_date(self, messages: List[Any]) -> str:
        for msg in messages:
            if isinstance(msg, SystemMessage):
                match = re.search(r'Current Date: ([\d-]+)', msg.content)
                if match:
                    return match.group(1)
        return datetime.datetime.now().strftime("%Y-%m-%d")

    def invoke(self, messages: List[Any]) -> AIMessage:
        # Get last message content
        last_message = messages[-1]
        user_text = last_message.content.lower() if hasattr(last_message, 'content') else ""
        
        # Check if the last message was a ToolResponse (meaning we just ran a tool)
        # In ReAct, if a tool was run, the agent should now summarize the result.
        last_is_tool = False
        tool_results = []
        for msg in reversed(messages):
            if isinstance(msg, ToolMessage):
                last_is_tool = True
                tool_results.append(msg)
            elif isinstance(msg, AIMessage) and msg.tool_calls:
                break
                
        form_state = self._get_form_state(messages)
        current_date = self._get_current_date(messages)
        
        if last_is_tool:
            hcp_info = None
            catalog_info = None
            log_result = None
            edit_result = None
            history_info = None
            
            for tr in tool_results:
                try:
                    data = json.loads(tr.content)
                    if isinstance(data, list) and len(data) > 0:
                        if "hospital" in data[0]:
                            hcp_info = data[0]
                        elif "topics" in data[0] or "interaction_id" in data[0]:
                            history_info = data
                    elif isinstance(data, dict):
                        if "materials_suggested" in data:
                            catalog_info = data
                        elif "status" in data:
                            if "logged" in data.get("message", ""):
                                log_result = data
                            elif "updated" in data.get("message", ""):
                                edit_result = data
                except Exception:
                    if "No HCPs found" in tr.content:
                        hcp_info = "not_found"
                    elif "catalog" in tr.content or "No materials" in tr.content:
                        catalog_info = "not_found"
                    elif "logged" in tr.content:
                        log_result = {"status": "success", "message": tr.content}
                    elif "updated" in tr.content:
                        edit_result = {"status": "success", "message": tr.content}
            
            updated_form = form_state.copy()
            reply_parts = []
            
            if log_result and log_result.get("status") == "success":
                reply_parts.append(f"Successfully logged the interaction! {log_result['message']}")
                # Clear form state upon logging
                updated_form = {
                    "hcp_id": None,
                    "hcp_name": "",
                    "interaction_type": "Meeting",
                    "date": current_date,
                    "time": datetime.datetime.now().strftime("%H:%M"),
                    "attendees": [],
                    "topics_discussed": "",
                    "materials_shared": [],
                    "samples_distributed": [],
                    "sentiment": "Neutral",
                    "outcomes": "",
                    "follow_up_actions": ""
                }
            elif edit_result and edit_result.get("status") == "success":
                reply_parts.append(f"Saved updates! {edit_result['message']}")
                # Clear form state upon edit completion
                updated_form = {
                    "hcp_id": None,
                    "hcp_name": "",
                    "interaction_type": "Meeting",
                    "date": current_date,
                    "time": datetime.datetime.now().strftime("%H:%M"),
                    "attendees": [],
                    "topics_discussed": "",
                    "materials_shared": [],
                    "samples_distributed": [],
                    "sentiment": "Neutral",
                    "outcomes": "",
                    "follow_up_actions": ""
                }
            else:
                if hcp_info and hcp_info != "not_found":
                    updated_form["hcp_id"] = hcp_info["id"]
                    updated_form["hcp_name"] = hcp_info["name"]
                    if hcp_info["name"] not in updated_form.get("attendees", []):
                        attendees = updated_form.get("attendees", []).copy()
                        attendees.append(hcp_info["name"])
                        updated_form["attendees"] = attendees
                    reply_parts.append(f"Found HCP: **{hcp_info['name']}** ({hcp_info['specialty']} at {hcp_info['hospital']}).")
                
                if catalog_info and catalog_info != "not_found":
                    mats = [m["name"] for m in catalog_info.get("materials_suggested", [])]
                    sams = [s["name"] for s in catalog_info.get("samples_suggested", [])]
                    if mats:
                        updated_form["materials_shared"] = list(set(updated_form.get("materials_shared", []) + mats))
                        reply_parts.append(f"Suggested Materials: {', '.join([f'`{m}`' for m in mats])}")
                    if sams:
                        updated_form["samples_distributed"] = list(set(updated_form.get("samples_distributed", []) + sams))
                        reply_parts.append(f"Suggested Samples: {', '.join([f'`{s}`' for s in sams])}")
                        
                if history_info:
                    reply_parts.append(f"Retrieved recent history for **{updated_form.get('hcp_name', 'HCP')}**:")
                    for idx, item in enumerate(history_info):
                        reply_parts.append(f"{idx+1}. **{item['date']}** ({item['type']}): \"_{item['topics']}_\" | Outcomes: _{item['outcomes']}_")
                
                if not hcp_info and not catalog_info and not history_info:
                    reply_parts.append("I processed your query but no matching database entries were found.")
                else:
                    # Detect details from human message
                    orig_user_msg = ""
                    for msg in reversed(messages):
                        if msg.type == "human" and msg.content:
                            orig_user_msg = msg.content.lower()
                            break
                    
                    if orig_user_msg:
                        if any(x in orig_user_msg for x in ["positive", "good", "happy", "receptive", "great"]):
                            updated_form["sentiment"] = "Positive"
                        elif any(x in orig_user_msg for x in ["negative", "bad", "unhappy", "refused", "poor"]):
                            updated_form["sentiment"] = "Negative"
                        else:
                            updated_form["sentiment"] = "Neutral"
                            
                        # Set default topics based on keywords
                        topics_list = []
                        if "oncoboost" in orig_user_msg:
                            topics_list.append("Discussed OncoBoost clinical trial details, safety profiles and efficacy rates.")
                        if "cardiolife" in orig_user_msg:
                            topics_list.append("Discussed CardioLife safety trial results and dosing profiles.")
                        if "glucoshield" in orig_user_msg:
                            topics_list.append("Discussed GlucoShield diabetes management and patient outcomes.")
                        
                        if topics_list:
                            updated_form["topics_discussed"] = " ".join(topics_list)
                            
                        # Outlining outcomes & followups
                        if "ask" in orig_user_msg or "request" in orig_user_msg:
                            updated_form["outcomes"] = "HCP requested study details and samples."
                        else:
                            updated_form["outcomes"] = "Successfully reviewed drug efficacy and safety data."
                            
                        if "week" in orig_user_msg or "follow up" in orig_user_msg:
                            updated_form["follow_up_actions"] = "Schedule follow-up meeting in 2 weeks"
                    
                    reply_parts.append(f"I've updated the draft interaction details for **{updated_form.get('hcp_name', 'HCP')}** based on the database details.")
            
            reply = "\n\n".join(reply_parts)
            form_str = json.dumps(updated_form, indent=2)
            content = f"{reply}\n\n```json_form_state\n{form_str}\n```"
            return AIMessage(content=content)
            
        # Determine if we should call a tool based on input text (First Turn)
        if any(x in user_text for x in ["log", "save", "submit"]):
            hcp_name = form_state.get("hcp_name")
            if not hcp_name:
                return AIMessage(content="I cannot log this interaction yet because no HCP has been selected. Please search for an HCP or mention their name (e.g., 'Met Dr. Sharma today').")
            
            tool_call = {
                "name": "log_interaction",
                "args": {
                    "hcp_name": hcp_name,
                    "date": form_state.get("date") or current_date,
                    "time": form_state.get("time") or datetime.datetime.now().strftime("%H:%M"),
                    "interaction_type": form_state.get("interaction_type", "Meeting"),
                    "attendees": form_state.get("attendees", []),
                    "topics_discussed": form_state.get("topics_discussed", ""),
                    "materials_shared": form_state.get("materials_shared", []),
                    "samples_distributed": form_state.get("samples_distributed", []),
                    "sentiment": form_state.get("sentiment", "Neutral"),
                    "outcomes": form_state.get("outcomes", ""),
                    "follow_up_actions": form_state.get("follow_up_actions", "")
                },
                "id": f"call_log_{int(datetime.datetime.now().timestamp())}"
            }
            return AIMessage(content="", tool_calls=[tool_call])
            
        elif any(x in user_text for x in ["edit", "update", "modify"]):
            match = re.search(r'(?:interaction\s+|id\s+|log\s+)?(\d+)', user_text)
            inter_id = int(match.group(1)) if match else 1
            
            args = {"interaction_id": inter_id}
            if "date" in user_text:
                if "tomorrow" in user_text:
                    args["date"] = (datetime.datetime.strptime(current_date, "%Y-%m-%d") + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                else:
                    date_match = re.search(r'\b\d{4}-\d{2}-\d{2}\b', user_text)
                    if date_match:
                        args["date"] = date_match.group(0)
            if "time" in user_text:
                time_match = re.search(r'\b\d{2}:\d{2}\b', user_text)
                if time_match:
                    args["time"] = time_match.group(0)
            if "sentiment" in user_text:
                if "positive" in user_text: args["sentiment"] = "Positive"
                elif "negative" in user_text: args["sentiment"] = "Negative"
                elif "neutral" in user_text: args["sentiment"] = "Neutral"
            if "type" in user_text or "interaction_type" in user_text:
                if "call" in user_text: args["interaction_type"] = "Call"
                elif "email" in user_text: args["interaction_type"] = "Email"
                elif "meeting" in user_text: args["interaction_type"] = "Meeting"
                
            tool_call = {
                "name": "edit_interaction",
                "args": args,
                "id": f"call_edit_{int(datetime.datetime.now().timestamp())}"
            }
            return AIMessage(content="", tool_calls=[tool_call])
            
        elif any(x in user_text for x in ["history", "past", "previous"]):
            hcp_query = ""
            for name in ["sharma", "connor", "patel", "smith", "nair", "miller"]:
                if name in user_text:
                    hcp_query = name
                    break
            if not hcp_query and form_state.get("hcp_name"):
                hcp_query = form_state.get("hcp_name")
                
            if hcp_query:
                tool_call = {
                    "name": "get_hcp_history",
                    "args": {"hcp_name": hcp_query},
                    "id": f"call_history_{int(datetime.datetime.now().timestamp())}"
                }
                return AIMessage(content="", tool_calls=[tool_call])
                
        else:
            # Check if updating draft state fields directly
            is_draft_update = False
            updated_draft = form_state.copy()
            
            if "sentiment" in user_text:
                if "positive" in user_text:
                    updated_draft["sentiment"] = "Positive"
                    is_draft_update = True
                elif "negative" in user_text:
                    updated_draft["sentiment"] = "Negative"
                    is_draft_update = True
                elif "neutral" in user_text:
                    updated_draft["sentiment"] = "Neutral"
                    is_draft_update = True
                    
            if "date" in user_text:
                if "tomorrow" in user_text:
                    updated_draft["date"] = (datetime.datetime.strptime(current_date, "%Y-%m-%d") + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                    is_draft_update = True
                elif "yesterday" in user_text:
                    updated_draft["date"] = (datetime.datetime.strptime(current_date, "%Y-%m-%d") - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                    is_draft_update = True
                else:
                    date_match = re.search(r'\b\d{4}-\d{2}-\d{2}\b', user_text)
                    if date_match:
                        updated_draft["date"] = date_match.group(0)
                        is_draft_update = True
                        
            if "time" in user_text:
                time_match = re.search(r'\b\d{2}:\d{2}\b', user_text)
                if time_match:
                    updated_draft["time"] = time_match.group(0)
                    is_draft_update = True
                    
            if "type" in user_text or "interaction_type" in user_text:
                if "call" in user_text:
                    updated_draft["interaction_type"] = "Call"
                    is_draft_update = True
                elif "email" in user_text:
                    updated_draft["interaction_type"] = "Email"
                    is_draft_update = True
                elif "meeting" in user_text:
                    updated_draft["interaction_type"] = "Meeting"
                    is_draft_update = True
                    
            if is_draft_update:
                form_str = json.dumps(updated_draft, indent=2)
                return AIMessage(content=f"I have updated the draft form fields as requested.\n\n```json_form_state\n{form_str}\n```")
                
            # Default fallback: Search doctor and suggest products
            hcp_query = ""
            for name in ["sharma", "connor", "patel", "smith", "nair", "miller"]:
                if name in user_text:
                    hcp_query = name
                    break
                    
            product_query = ""
            for prod in ["oncoboost", "cardiolife", "glucoshield"]:
                if prod in user_text:
                    product_query = prod
                    break
            
            tool_calls = []
            if hcp_query:
                tool_calls.append({
                    "name": "search_hcps",
                    "args": {"query": hcp_query},
                    "id": f"call_search_{int(datetime.datetime.now().timestamp())}"
                })
            if product_query:
                tool_calls.append({
                    "name": "suggest_clinical_content",
                    "args": {"topic": product_query},
                    "id": f"call_suggest_{int(datetime.datetime.now().timestamp())}"
                })
                
            if tool_calls:
                return AIMessage(content="", tool_calls=tool_calls)
                
            form_str = json.dumps(form_state, indent=2)
            return AIMessage(
                content=(
                    f"Hi! Tell me about your interaction. For example, 'Met Dr. Sarah Connor to discuss CardioLife.' "
                    f"Or ask to save it once ready: 'please log this interaction.'\n\n```json_form_state\n{form_str}\n```"
                )
            )


# Graph node implementations
def call_model(state: AgentState) -> Dict[str, Any]:
    messages = state["messages"]
    form_state = state.get("form_state", {})
    
    # Get current system date/time
    now = datetime.datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")
    
    # Create the dynamic context string to inject into the system prompt
    context_desc = (
        f"\n\n--- DYNAMIC CONTEXT ---\n"
        f"Current Date: {current_date}\n"
        f"Current Time: {current_time}\n"
        f"Current Form State (Draft):\n{json.dumps(form_state, indent=2)}\n"
        f"-----------------------\n"
    )
    
    # Combine system prompt with dynamic context
    dynamic_system_prompt = SYSTEM_PROMPT + context_desc
    
    # Clean up any existing SystemMessages in the messages list to avoid stale states
    cleaned_messages = [msg for msg in messages if not isinstance(msg, SystemMessage)]
    
    # Prepend the fresh, dynamically generated SystemMessage
    final_messages = [SystemMessage(content=dynamic_system_prompt)] + cleaned_messages
    
    model = get_model()
    response = model.invoke(final_messages)
    
    # Return response message
    return {"messages": [response]}


# Build the state graph
workflow = StateGraph(AgentState)

# Define nodes
workflow.add_node("agent", call_model)
workflow.add_node("tools", ToolNode(sales_tools))

# Define edges
workflow.add_edge(START, "agent")

def should_continue(state: AgentState) -> str:
    last_message = state["messages"][-1]
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    return END

workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "tools": "tools",
        END: END
    }
)
workflow.add_edge("tools", "agent")

# Compile the graph
agent_graph = workflow.compile()


# Helper to run the agent
def run_agent_chat(messages_list: List[Dict[str, str]], current_form_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parses input chat messages, executes the LangGraph agent,
    extracts the `json_form_state` block, and returns the response.
    """
    # Convert input messages list to LangChain message objects
    lc_messages = []
    for msg in messages_list:
        role = msg.get("role")
        content = msg.get("content")
        if role == "user":
            lc_messages.append(HumanMessage(content=content))
        elif role == "assistant":
            lc_messages.append(AIMessage(content=content))
            
    # Initial state
    inputs = {
        "messages": lc_messages,
        "form_state": current_form_state
    }
    
    # Run the graph
    result = agent_graph.invoke(inputs)
    
    # Find final assistant message
    final_message = ""
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage) and msg.content:
            final_message = msg.content
            break
            
    # Parse json_form_state block
    updated_form = current_form_state.copy()
    suggestions = []
    
    # Look for ```json_form_state ... ``` block
    match = re.search(r'```json_form_state\s*(\{.*?\})\s*```', final_message, re.DOTALL)
    if match:
        try:
            form_json = json.loads(match.group(1))
            # Merge with updated form state
            for k, v in form_json.items():
                if v is not None:
                    updated_form[k] = v
            # Remove the code block from the user display message for a cleaner UI
            final_message = re.sub(r'```json_form_state\s*\{.*?\s*\}\s*```', '', final_message, flags=re.DOTALL).strip()
        except Exception as e:
            print("Error parsing json_form_state block from agent response:", e)
            
    # Auto-generate dynamic AI suggested actions if not filled or based on topics
    # These will be sent to the UI as action items
    topics = updated_form.get("topics_discussed", "").lower()
    hcp_name = updated_form.get("hcp_name", "")
    
    if "oncoboost" in topics:
        suggestions = [
            "Schedule follow-up meeting in 2 weeks",
            "Send OncoBoost Phase III PDF",
            f"Add {hcp_name} to advisory board invite list" if hcp_name else "Add HCP to advisory board invite list"
        ]
    elif "cardiolife" in topics:
        suggestions = [
            "Send CardioLife Product Monograph",
            "Schedule follow-up call in 3 days",
            "Request medical science liaison (MSL) support"
        ]
    else:
        suggestions = [
            "Schedule follow-up meeting in 2 weeks",
            "Send clinical study PDF",
            f"Verify {hcp_name or 'HCP'} consent for email communications"
        ]
        
    return {
        "reply": final_message,
        "updated_form": updated_form,
        "suggestions": suggestions
    }
