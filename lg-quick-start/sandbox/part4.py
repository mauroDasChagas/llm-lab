from typing import Annotated

from dotenv import load_dotenv
from langchain_community.tools import TavilySearchResults
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import add_messages, StateGraph, START
from langgraph.prebuilt import ToolNode, tools_condition
from typing_extensions import TypedDict

load_dotenv()

memory = MemorySaver()


class State(TypedDict):
    messages: Annotated[list, add_messages]


workflow = StateGraph(State)

tool = TavilySearchResults(max_results=2)
tools = [tool]
llm = ChatOpenAI()
llm_with_tools = llm.bind_tools(tools)


def chatbot(state: State):
    return {"messages": [llm_with_tools.invoke(state["messages"])]}


workflow.add_node("chatbot", chatbot)

tool_node = ToolNode(tools=[tool])
workflow.add_node("tools", tool_node)

workflow.add_conditional_edges(
    "chatbot",
    tools_condition
)

workflow.add_edge("tools", "chatbot")
workflow.add_edge(START, "chatbot")

graph = workflow.compile(
    checkpointer=memory,
    # This is new!
    interrupt_before=["tools"]
    # Note: can also interrupt __after__ tools, if desired.
    # interrupt_after=["tools"]
)

user_input = "I'm learning LangGraph. Could you do some research on it for me?"
config = {"configurable": {"thread_id": "1"}}
# The config is the **second positional argument** to stream() or invoke()!
events = graph.stream(
    {"messages": [("user", user_input)]}, config, stream_mode="values"
)
for event in events:
    if "messages" in event:
        event["messages"][-1].pretty_print()

snapshot = graph.get_state(config)
print("Snapshot next: ", snapshot.next)

existing_message = snapshot.values["messages"][-1]
print("Existing message: ", existing_message.tool_calls)

events = graph.stream(None, config, stream_mode="values")
for event in events:
    if "messages" in event:
        event["messages"][-1].pretty_print()

# config = {"configurable": {"thread_id": "1"}}
#
#
# def stream_graph_updates(user_input: str):
#     for event in graph.stream(
#             {"messages": [("user", user_input)]},
#             config
#     ):
#         for value in event.values():
#             print("Assistant:", value["messages"][-1].content)
#
#
# while True:
#     try:
#         user_input = input("User: ")
#         if user_input.lower() in ["/q", "/quit", "/exit"]:
#             print("Goodbye!")
#             break
#
#         stream_graph_updates(user_input)
#     except:
#         # fallback if input() is not available
#         user_input = "What do you know about LangGraph?"
#         print("User: " + user_input)
#         stream_graph_updates(user_input)
#         break
