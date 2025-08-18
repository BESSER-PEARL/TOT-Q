import os
import json
import time
import sys
import streamlit as st
from streamlit.web import cli as stcli
import queue
import websocket
import threading
from streamlit.runtime import Runtime
from streamlit.runtime.app_session import AppSession
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
from besser.agent.platforms.payload import Payload, PayloadAction, PayloadEncoder
from tot_q_chat.simulated_expert import llm_qa_response
from tot_q_chat.puml_to_graphviz import transform_plantuml_to_graphviz
from dotenv import load_dotenv

load_dotenv()

simulate_expert = bool(int(os.getenv("SIMULATED_EXPERT", "0")))


st.set_page_config(layout="wide")
st.markdown("""
    <style>
        [data-testid="stSidebar"] > div:first-child {
            position: relative;
            top: -75;
        }
    </style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## Domain Model Assistant") 

col1, col2 = st.columns(2)

with col1:
    tab1 = st.expander("Alternative 1", expanded = True) 
with col2:
    tab2 = st.expander("Alternative 2", expanded = True) 
tab3 = st.sidebar.expander("Initial Domain Model", expanded = True) 
tab4 = st.sidebar.expander("Updated Domain Model ", expanded = True) 

import graphviz
from graphviz import Source
path = 'tot_q_chat/uml.graphviz'
s = Source.from_file(path)
uml = graphviz.Digraph()

chart1 = tab1.empty()
with chart1.container():
    st.graphviz_chart("")

chart2 = tab2.empty()
with chart2.container():
    st.graphviz_chart("")

chart3 = tab3.empty()
with chart3.container():
    st.graphviz_chart("")

chart4 = tab4.empty()
with chart4.container():
    st.graphviz_chart("")

def tab1_change(message: str = ""):
    global tab1
    global chart1
    if '@startuml' in message:
        puml_text = message.split('@@@NEXT_UML@@@')[0]
        print('tab_change\t',puml_text)
        print(transform_plantuml_to_graphviz(puml_text))
        with chart1.container():
            st.graphviz_chart(transform_plantuml_to_graphviz(puml_text))
        return True
    else:
        return False

def tab2_change(message: str = ""):
    global chart2
    if '@startuml' in message:
        puml_text = message.split('@@@NEXT_UML@@@')[1]
        print('tab_change\t',puml_text)
        print(transform_plantuml_to_graphviz(puml_text))
        with chart2.container():
            st.graphviz_chart(transform_plantuml_to_graphviz(puml_text))
        return True
    else:
        return False

def tab3_change(message: str = ""):
    global chart3
    if '@startuml' in message:
        puml_text = message.split('@@@NEXT_UML@@@')[2]
        print('tab_change\t',puml_text)
        print(transform_plantuml_to_graphviz(puml_text))
        with chart3.container():
            st.graphviz_chart(transform_plantuml_to_graphviz(puml_text))
        return True
    else:
        return False
    
def tab4_change(message: str = ""):
    global chart4
    if '@startuml' in message:
        puml_text = message.split('@@@NEXT_UML@@@')[3]
        print('tab_change\t',puml_text)
        print(transform_plantuml_to_graphviz(puml_text))
        with chart4.container():
            st.graphviz_chart(transform_plantuml_to_graphviz(puml_text))
        return True
    else:
        return False

st.markdown(
    """
    <style>
    [data-testid="stSidebar"][aria-expanded="true"]{
        min-width: 45%;
        max-width: 45%;
    }
    """,
    unsafe_allow_html=True,
) 
SESSION_MONITORING_INTERVAL = 10

def get_streamlit_session() -> AppSession or None:
    session_id = get_script_run_ctx().session_id
    runtime: Runtime = Runtime.instance()
    return next((
        s.session
        for s in runtime._session_mgr.list_sessions()
        if s.session.id == session_id
    ), None)

def session_monitoring(interval: int):
    runtime: Runtime = Runtime.instance()
    session = get_streamlit_session()
    while True:
        time.sleep(interval)
        if not runtime.is_active_session(session.id):
            runtime.close_session(session.id)
            session.session_state['websocket'].close()
            break

import pandas as pd

def main():

    def on_message(ws, payload_str):
        streamlit_session = get_streamlit_session()
        payload: Payload = Payload.decode(payload_str)        
        if payload.action == PayloadAction.AGENT_REPLY_STR.value:
            message = payload.message
        elif payload.action == PayloadAction.AGENT_REPLY_DF.value:
            message = pd.read_json(payload.message)
        elif payload.action == PayloadAction.AGENT_REPLY_OPTIONS.value:
            d = json.loads(payload.message)
            message = []
            for button in d.values():
                message.append(button)
        streamlit_session._session_state['queue'].put(message)
        streamlit_session.session_state['graphviz'] = uml
        if not st.session_state['processing'] and not st.session_state['queue'].empty():
            streamlit_session._handle_rerun_script_request()
            st.session_state['rerun'] = True


    def on_error(ws, error):
        pass

    def on_open(ws):
        pass

    def on_close(ws, close_status_code, close_msg):
        pass

    def on_ping(ws, data):
        pass

    def on_pong(ws, data):
        pass

    user_type = {
        0: 'assistant',
        1: 'user'
    }

    if 'history' not in st.session_state:
        st.session_state['history'] = []

    if 'queue' not in st.session_state:
        st.session_state['queue'] = queue.Queue()
    
    if 'new_message_ready' not in st.session_state:
        st.session_state['new_message_ready'] = False

    if 'websocket' not in st.session_state:
        ws = websocket.WebSocketApp("ws://localhost:8765/",
                                    on_open=on_open,
                                    on_message=on_message,
                                    on_error=on_error,
                                    on_close=on_close,
                                    on_ping=on_ping,
                                    on_pong=on_pong)
        websocket_thread = threading.Thread(target=ws.run_forever)
        add_script_run_ctx(websocket_thread)
        websocket_thread.start()
        st.session_state['websocket'] = ws

    if 'session_monitoring' not in st.session_state:
        session_monitoring_thread = threading.Thread(target=session_monitoring,
                                                     kwargs={'interval': SESSION_MONITORING_INTERVAL})
        add_script_run_ctx(session_monitoring_thread)
        session_monitoring_thread.start()
        st.session_state['session_monitoring'] = session_monitoring_thread

    ws = st.session_state['websocket']


    # Add a flag for processing the queue
    if 'processing' not in st.session_state:
        st.session_state['processing'] = False

    # Add a flag to indicate when user message is being processed
    if 'domain' not in st.session_state:
        st.session_state['domain'] = None
    
    if 'rerun' not in st.session_state:
        st.session_state['rerun'] = False
    
    if 'lastmsg' not in st.session_state:
        st.session_state['lastmsg'] = ''

    if "question" not in st.session_state:
        st.session_state.question = None
    
    #LLM answer configuration
    if 'llm_answer' not in st.session_state:
        st.session_state.llm_answer = simulate_expert

    with st.sidebar:
        reset_button = st.button(label="Reset bot")
        if reset_button:
            st.session_state['history'] = []
            st.session_state['queue'] = queue.Queue()
            payload = Payload(action=PayloadAction.RESET)
            ws.send(json.dumps(payload, cls=PayloadEncoder))

    for message in st.session_state['history']:
        with st.chat_message(user_type[message[1]]):
            st.write(message[0])

    if not st.session_state['processing'] and not st.session_state['queue'].empty():
        st.session_state['processing'] = True
        first_message = True
        while not st.session_state['queue'].empty():
            message = st.session_state['queue'].get()
            t = len(message) / 1000 * 3
            if t > 3:
                t = 3
            elif t < 1 and first_message:
                t = 1
            first_message = False
            if isinstance(message, list):
                st.session_state['buttons'] = message
            else:
                isDiagram = tab1_change(message)
                tab2_change(message)
                tab3_change(message)
                tab4_change(message)
                if not isDiagram:
                    #question store
                    st.session_state.question = message
                    st.session_state['history'].append((message, 0))
                    with st.chat_message("assistant"):
                        with st.spinner(''):
                            time.sleep(t)
                            st.write(message)
        
        # After processing, reset the flag
        st.session_state['processing'] = False
        

    if 'buttons' in st.session_state:
        buttons = st.session_state['buttons']
        cols = st.columns(1)
        q = st.session_state.question
        options = []
        for i, option in enumerate(buttons):
            options.append(option)
            if cols[0].button(option) and \
                option != st.session_state['lastmsg']:
                with st.chat_message("user"):
                    st.write(option)
                st.session_state.history.append((option, 1))
                payload = Payload(action=PayloadAction.USER_MESSAGE,
                                  message=option)
                st.session_state['lastmsg'] = option
                ws.send(json.dumps(payload, cls=PayloadEncoder))
                st.session_state['rerun'] == False
                del st.session_state['buttons']
                if option == 'Next question':
                    del st.session_state.history
                break
        if len(options) == 2 and st.session_state.llm_answer:
            option = llm_qa_response(q,options[0],options[1], st.session_state['domain'])
            with st.chat_message("user"):
                st.write(option)
            st.session_state.history.append((option, 1))
            payload = Payload(action=PayloadAction.USER_MESSAGE,
                                message=option)
            st.session_state['lastmsg'] = option
            ws.send(json.dumps(payload, cls=PayloadEncoder))
            st.session_state['rerun'] == False
            del st.session_state['buttons']
            if option == 'Next question':
                del st.session_state.history

    if user_input := st.chat_input("How can I help?"):
        if user_input not in [msg for msg, sender in st.session_state['history']]:
            st.session_state['rerun'] = False
        if st.session_state['rerun'] == False:
            
            if 'buttons' in st.session_state:
                del st.session_state['buttons']
            with st.chat_message("user"):
                st.write(user_input)
            st.session_state.history.append((user_input, 1))
            payload = Payload(action=PayloadAction.USER_MESSAGE,
                            message=user_input)
            try:
                ws.send(json.dumps(payload, cls=PayloadEncoder))
                st.session_state['lastmsg'] = user_input
                st.session_state['rerun'] == False
                if st.session_state['domain'] is None:
                    domain = user_input
                    st.session_state['domain'] = domain.strip()
            except Exception as e:
                st.error('Your message could not be sent. The connection is already closed')

    st.stop()


if __name__ == "__main__":
    if st.runtime.exists():
        main()
    else:
        sys.argv = ["streamlit", "run", sys.argv[0]]
        sys.exit(stcli.main())

import subprocess

subprocess.run(["streamlit", "run", "chat.py",
                "--server.address", "localhost",
                "--server.port", "5000"])
