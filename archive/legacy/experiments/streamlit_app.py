import traceback

import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.agent import get_agent, run_agent_stream


st.set_page_config(page_title="Where can I stream this?", page_icon="🎬", layout="centered")
st.title("Where can I stream this?")

with st.sidebar:
    st.header("Options")
    show_debug = st.checkbox("Show debug", value=False)
    show_thinking = st.checkbox("Show thinking process", value=True)
    if st.button("Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


@st.cache_resource
def _warm_agent():
    return get_agent()


_warm_agent()

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "assistant":
            st.markdown(message["content"], unsafe_allow_html=False)
        else:
            st.write(message["content"])

if prompt := st.chat_input("Ask for a movie you want to stream"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        try:
            # Create containers for real-time updates
            thinking_container = None
            if show_thinking:
                thinking_container = st.container()
                with thinking_container:
                    st.markdown("**🧠 Thinking process**")
                    step_placeholder = st.empty()
            
            final_response_placeholder = st.empty()
            
            # Stream the execution and show steps in real-time
            all_thinking_msgs = []
            response = ""
            debug_state = None
            
            for event in run_agent_stream(prompt):
                if event["type"] == "step" and show_thinking:
                    all_thinking_msgs.extend(event["messages"])
                    # Update the thinking UI in real-time
                    with step_placeholder.container():
                        for msg in all_thinking_msgs:
                            st.markdown(msg.content)
                            st.markdown("---")
                
                elif event["type"] == "final":
                    response = event["response"]
                    debug_state = event["state"]
            
            # Display final response
            final_response_placeholder.markdown(response, unsafe_allow_html=False)

            if show_debug and debug_state is not None:
                with st.expander("Debug state"):
                    st.json(debug_state)
                    
        except Exception as exc:
            response = "I ran into an error while searching streaming providers."
            st.error(response)
            with st.expander("Exception details"):
                st.code(f"{exc}\n\n{traceback.format_exc()}")

    st.session_state.messages.append({"role": "assistant", "content": response})
