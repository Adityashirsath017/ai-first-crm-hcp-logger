from typing import Dict, Any, List
from langgraph.graph import MessagesState

class AgentState(MessagesState):
    """
    State for the LangGraph agent.
    Inherits 'messages' from MessagesState (a list of BaseMessage).
    Also tracks the 'form_state' which mirrors the frontend fields.
    """
    form_state: Dict[str, Any]
