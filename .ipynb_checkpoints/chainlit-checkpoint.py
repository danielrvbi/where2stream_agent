from app.agent import build_app
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)


agent = build_app()

print(agent.invoke({"messages":HumanMessage("Where do I stream Shrek 2?")}))