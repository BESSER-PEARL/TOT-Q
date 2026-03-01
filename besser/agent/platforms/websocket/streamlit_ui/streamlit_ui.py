import sys
import os
import json
import streamlit as st
from streamlit.runtime import Runtime
from streamlit.web import cli as stcli

from besser.agent.platforms.websocket.streamlit_ui.chat import load_chat
from besser.agent.platforms.websocket.streamlit_ui.initialization import initialize
from besser.agent.platforms.websocket.streamlit_ui.message_input import message_input
from besser.agent.platforms.websocket.streamlit_ui.sidebar import sidebar
from besser.agent.platforms.websocket.streamlit_ui.vars import HISTORY, QUEUE

import streamlit.components.v1 as components

def main():
    print("DEBUG: main() function entered", flush=True)
    try:
        agent_name = sys.argv[1]
    except Exception as e:
        agent_name = 'Agent Demo'

    st.set_page_config(
        page_title="BESSER WME",
        page_icon="https://avatars.githubusercontent.com/u/138102430",
        layout="wide"
    )
    if 'description' not in st.session_state:
        st.session_state['description'] = "Not available."

    try:
        initialize()
    except Exception as init_error:
        import traceback

    # Display debug info on the page
    if 'debug_info' in st.session_state and st.session_state['debug_info']:
        with st.expander("Debug Info", expanded=False):
            for msg in st.session_state['debug_info']:
                st.text(msg)

    st.session_state.url_ed = os.getenv('EDITOR_URL', 'http://localhost:8080/')
    
    # Add cache busting to chat widget URL - Version 2.1 (must match index.html version)
    base_cw_url = os.getenv('CHAT_WIDGET_URL', 'http://localhost:8000/besser/agent/platforms/websocket/chat_widget/')
    st.session_state.url_cw = f"{base_cw_url}?v=2.2"

    # Lista de orígenes permitidos para postMessage (para validación de seguridad)
    allowed_origins_str = os.getenv('ALLOWED_ORIGINS', 'http://localhost:8080,http://localhost:8000')
    st.session_state.allowed_origins = [origin.strip() for origin in allowed_origins_str.split(',')]
    
    if 'diagram_json' not in st.session_state:
        st.session_state['diagram_json'] = None  # Initialize diagram JSON state
    
    if 'hidden_sid_input' not in st.session_state:
        st.session_state['hidden_sid_input'] = None  # Initialize diagram JSON state

    st.session_state.plantuml = ''
    while not st.session_state[QUEUE].empty():
        message = st.session_state[QUEUE].get()
        st.session_state[HISTORY].append(message)
        if 'session-id' in message.content:
            sid = message.content.split(": ")[1]
            st.session_state['hidden_sid_input'] = sid
        if 'text-domain-desc' in message.content:
            desc = message.content.split(": ")[1]
            st.session_state['description'] = desc
        st.session_state.plantuml = message.content

    # --- Domain Text Area (Above Editor) ---
    with st.expander("Domain Description", expanded=False):
        domain_text = st.text_area(
            label="Domain Description",
            value=f"""{st.session_state['description']}""",
            key="domain_text_area",
            label_visibility="collapsed",
            help="View the domain description here"
        )

    st.markdown("""
        <style>
            /* Make the expander float - FIXED SIZE, textarea is resizable */
            div[data-testid="stExpander"] {
                position: fixed !important;
                top: 00px !important;
                left: 70% !important;
                transform: translateX(-50%) !important;
                width: 60% !important;
                max-width: 800px !important;
                z-index: 1000 !important;

                /* Single clean border */
                background-color: #ffffff !important;
                border: 1px solid #d1d5db !important;
                box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1) !important;
                border-radius: 8px !important;
                padding: 0.5rem !important;
                

                /* NO resize on expander */
                resize: none !important;
                overflow: visible !important;
            }
                
            /* Dark mode support for expander */
            @media (prefers-color-scheme: dark) {
                div[data-testid="stExpander"] {
                    background-color: #1e1e1e !important;
                    border: 1px solid #404040 !important;
                    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4) !important;
                }
            }

            /* Remove container border */
            div[data-testid="stExpander"] div[data-baseweb="base-input"] {
                border: none !important;
                background-color: transparent !important;
                box-shadow: none !important;
            }

            /* AGGRESSIVE overrides for textarea resize - Target all relevant selectors */
            div[data-testid="stExpander"] textarea,
            div[data-testid="stExpander"] .stTextArea textarea,
            div[data-testid="stExpander"] [data-baseweb="textarea"] textarea {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
                font-size: 14px !important;
                line-height: 1.6 !important;
                color: #1f2937 !important;
                background-color: transparent !important;
                border: 1px solid #e5e7eb !important;
                border-radius: 6px !important;
                padding: 12px !important;
                outline: none !important;

                /* Force vertical resize with maximum specificity */
                resize: vertical !important;
                min-height: 150px !important;
                max-height: 600px !important;
                overflow: auto !important;

                /* Override any Streamlit defaults that prevent resizing */
                -webkit-appearance: textfield !important;
                -moz-appearance: textfield !important;
            }
            
            /* Dark mode support for textarea */
            @media (prefers-color-scheme: dark) {
                div[data-testid="stExpander"] textarea,
                div[data-testid="stExpander"] .stTextArea textarea,
                div[data-testid="stExpander"] [data-baseweb="textarea"] textarea {
                    color: #e5e7eb !important;
                    background-color: #2a2a2a !important;
                    border: 1px solid #404040 !important;
                }
            }

            /* Better focus state */
            div[data-testid="stExpander"] textarea:focus {
                border-color: #3b82f6 !important;
                box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
            }

            /* Dark mode focus state */
            @media (prefers-color-scheme: dark) {
                div[data-testid="stExpander"] textarea:focus {
                    border-color: #60a5fa !important;
                    box-shadow: 0 0 0 3px rgba(96, 165, 250, 0.2) !important;
                }
            }
                
            /* Ensure content doesn't shift when expander is shown */
            div[data-testid="stExpander"] + div {
                margin-top: 0rem !important;
            }
        </style>
    """, unsafe_allow_html=True)

    pg_height = 750
    cw_width = 440
    cw_height = 659
    cw_hidden = 100
    components.html(
        f"""
        <style>
            html, body, iframe {{
                height: 100%;
                width: 100%;
                margin: 0;
                padding: 0;
                border: none;
            }}
            #editorIframe {{
                zoom: 0.8; 
            }}
        </style>
        <iframe id="editorIframe"
            src="{st.session_state.url_ed}"
            width="100%" height="{pg_height}"
            style="border:none; position: relative; z-index: 1;"
            sandbox="allow-scripts allow-same-origin allow-modals">
        </iframe>

        <script>
            const iframe = document.getElementById('editorIframe');
            let lastSentMessage = null;

            // Function to send/resend message to editor
            function sendToEditor(message) {{
                if (iframe && iframe.contentWindow) {{
                    iframe.contentWindow.postMessage(message, "*");
                    lastSentMessage = message;
                }}
            }}

            iframe.onload = function() {{
                const initialMessage = `{st.session_state.plantuml}`;

                // Detect browser refresh by checking if initialMessage contains chat history (array) instead of diagram JSON
                let isParentRefresh = false;
                let isValidDiagramJson = false;

                if (!initialMessage || initialMessage.trim() === '') {{
                    isParentRefresh = true;
                }} else {{
                    // Check if it's valid diagram JSON (starts with {{ and has "type" field)
                    const trimmed = initialMessage.trim();
                    if (trimmed.startsWith('{{') && trimmed.includes('"type"')) {{
                        try {{
                            const parsed = JSON.parse(trimmed);
                            if (parsed.type && parsed.version) {{
                                isValidDiagramJson = true;
                            }}
                        }} catch (e) {{
                            // Not valid JSON
                        }}
                    }}

                    // If not valid diagram JSON (e.g., chat history array), it's a browser refresh
                    if (!isValidDiagramJson) {{
                        isParentRefresh = true;
                    }}
                }}

                // If parent was refreshed, send empty diagram
                if (isParentRefresh) {{
                    const emptyDiagram = JSON.stringify({{
                        "version": "3.0.0",
                        "type": "ClassDiagram",
                        "size": {{
                            "width": 1200,
                            "height": 800
                        }},
                        "interactive": {{
                            "elements": {{}},
                            "relationships": {{}}
                        }},
                        "elements": {{}},
                        "relationships": {{}},
                        "assessments": {{}}
                    }});
                    sendToEditor(emptyDiagram);
                }} else if (isValidDiagramJson) {{
                    // Valid diagram in queue, send it
                    sendToEditor(initialMessage);
                }}
            }};

            // Listen for recovery requests from editor
            window.addEventListener('message', function (event) {{
                // Handle editor recovery request
                if (event.data && typeof event.data === 'object' && event.data.type === 'editor-recovered') {{
                    console.log('Editor recovered, resending last message');
                    if (lastSentMessage) {{
                        setTimeout(() => sendToEditor(lastSentMessage), 500);
                    }}
                    return;
                }}

                // Optional: restrict to known origin
                // if (event.origin !== 'https://your-parent-origin.example') return;

                let diagramString = null;

                // Case A: child sends a primitive JSON string
                if (typeof event.data === 'string') {{
                    diagramString = event.data;
                }} else if (event.data && typeof event.data === 'object') {{
                    // Case B: child sends an envelope {{ type: 'diagram-json', payload: ... }}
                    if (event.data.type === 'diagram-json') {{
                    const p = event.data.payload;
                    diagramString = typeof p === 'string' ? p : JSON.stringify(p);
                    }} else if (event.data.payload && typeof event.data.payload === 'string') {{
                    // fallback: object with a string payload
                    diagramString = event.data.payload;
                    }}
                }}

                if (!diagramString) return;

                if (typeof diagramString !== 'string') {{
                    diagramString = JSON.stringify(diagramString);
                }} else if (diagramString.startsWith('"') && diagramString.endsWith('"')) {{
                    try {{ diagramString = JSON.parse(diagramString); }} catch (_) {{}}
                }}
                diagramJson = JSON.stringify(diagramString);
                const hiddenInput = window.parent.document.querySelector('input[aria-label="hidden_json_input"]');
                if (hiddenInput) {{
                    hiddenInput.value = diagramJson;
                    hiddenInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                }}
            }});

            // ====================
            // DEBUG/TESTING TOOLS
            // ====================

            // Manual recovery function (can be called from console if needed)
            window.resetEditor = function() {{
                iframe.src = iframe.src; // Force reload
            }};

            // Get iframe window for direct access to apollonDebug
            window.getEditorIframe = function() {{
                return iframe.contentWindow;
            }};

            // Test the full error recovery flow
            window.testErrorRecovery = async function(sendTestDiagram = true) {{

                const editorWindow = iframe.contentWindow;
                if (!editorWindow || !editorWindow.apollonDebug) {{
                    console.error('Cannot access apollonDebug - iframe may not be loaded');
                    return false;
                }}

                // Check initial state
                const initialState = editorWindow.apollonDebug.getEditorState();

                // Force destroy
                editorWindow.apollonDebug.forceDestroy();

                // Wait a bit
                await new Promise(resolve => setTimeout(resolve, 500));

                // Check destroyed state
                const destroyedState = editorWindow.apollonDebug.getEditorState();

                if (sendTestDiagram) {{
                    // Try to send a diagram (this should trigger recovery)
                    const testDiagram = JSON.stringify({{
                        type: 'ClassDiagram',
                        version: '3.0.0',
                        elements: {{}},
                        relationships: {{}}
                    }});

                    sendToEditor(testDiagram);

                    // Wait for recovery
                    await new Promise(resolve => setTimeout(resolve, 2000));

                    // Check recovered state
                    const recoveredState = editorWindow.apollonDebug.getEditorState();

                    if (recoveredState.status === 'HEALTHY') {{
                        return true;
                    }} else {{
                        console.error('Recovery test FAILED - editor did not recover');
                        return false;
                    }}
                }} else {{
                    return null;
                }}
            }};

            // Check editor health from parent
            window.checkEditorHealth = function() {{
                const editorWindow = iframe.contentWindow;
                if (!editorWindow || !editorWindow.apollonDebug) {{
                    console.error('Cannot access editor iframe');
                    return {{ accessible: false }};
                }}

                const state = editorWindow.apollonDebug.getEditorState();
                return state;
            }};

        </script>
        """,
        height=pg_height
    )
    components.html(
        f"""
        <div 
            width="{cw_width}" 
            height: auto; 
            style="position: fixed; bottom: 20px; left: 20px; z-index: 2147483647;"
            overflow: auto;
        resize: both;
        >
            <iframe id="chatIframe"
                src="{st.session_state.url_cw}"
                width="{cw_width}" height="{cw_height + 55}"
                style="
                    border-radius: 12px;
                    border:none;
                    pointer-events: auto;
                    background: transparent;
                "
                sandbox="allow-scripts allow-same-origin allow-modals allow-downloads">
            </iframe>
        </div>

        <script>
            const chatIframe = document.getElementById("chatIframe");

            function sendSessionId(delay=500) {{
                if (!chatIframe) return;
                const interval = setInterval(() => {{
                    const sessionInput = window.parent.document.querySelector('input[aria-label="hidden_sid_input"]');
                    if (!sessionInput) return;
                    const sessionId = sessionInput.value;
                    if (!sessionId || !chatIframe.contentWindow) return;

                    try {{
                        chatIframe.contentWindow.postMessage({{ type: 'session-id', payload: sessionId }}, "*");
                        clearInterval(interval);
                    }} catch(err) {{
                        console.warn("Retrying sendSessionId...", err);
                    }}
                }}, delay);
            }}

            chatIframe.addEventListener("load", () => {{
                sendSessionId();
            }});

            sendSessionId();

            // Forward diagram JSON periodically
            setInterval(() => {{
                const hiddenInput = window.parent.document.querySelector('input[aria-label="hidden_json_input"]');
                if (!hiddenInput) return;
                const jsonString = hiddenInput.value;
                if (chatIframe && chatIframe.contentWindow) {{
                    chatIframe.contentWindow.postMessage({{ type:'diagram-json', payload: jsonString }}, "*");
                }}
            }}, 2000);

            const targetIframe = window.parent.document.querySelector('iframe[width="490"]');
            targetIframe.style.height = {cw_hidden} + "px";
            targetIframe.style.width = {cw_hidden} + "px";
            
            window.addEventListener("message", (event) => {{
                const msg = event.data || {{}};
                if (msg.type === 'chat-height' && targetIframe) {{
                    if (msg.height) {{
                        targetIframe.style.height = ({cw_height} + 50) + "px";
                        targetIframe.style.width = ({cw_width} + 50)  + "px";
                    }} else {{
                        targetIframe.style.height = {cw_hidden} + "px";
                        targetIframe.style.width = {cw_hidden} + "px";
                    }}
                }}
            }});
        </script>
        """,
        width = cw_width + 50,
        height = cw_height + 50
    )

    def trigger_flag():
        st.session_state["json_flag"] = True

    def trigger_sid_flag():
        st.session_state["sid_flag"] = True

    hidden_json = st.text_input(
        label="hidden_json_input",
        value="",
        key="hidden_json_input",
        label_visibility="collapsed",
        on_change=trigger_flag,
    )
    
    hidden_sid = st.text_input(
        label="hidden_sid_input",
        key="hidden_sid_input",
        label_visibility="collapsed",
        on_change=trigger_sid_flag,
    )

    st.markdown("""
        <style>
            div[data-testid="stTextInput"] {
                display: none;
            }
        </style>
    """, unsafe_allow_html=True)

    if st.session_state.get("json_flag"):
        try:
            parsed_json = json.loads(st.session_state.hidden_json_input)
            st.session_state['diagram_json'] = parsed_json
            st.session_state["json_flag"] = False
            print("✅ Updated diagram JSON in session state:", st.session_state['diagram_json'])
        except json.JSONDecodeError:
            st.warning("⚠️ Invalid JSON received from editor iframe")

    st.markdown("""
        <style>
            .block-container {
                max-width: 1200px;
                margin: auto;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("""
        <style>
            /* Hide Streamlit top bar (hamburger menu, deploy button, etc.) */
            header[data-testid="stHeader"] {
                display: none;
            }

            /* Hide main menu button */
            #MainMenu {
                display: none;
            }

            /* Hide footer */
            footer {
                display: none;
            }

            /* Remove padding at the top and sides */
            .block-container {
                padding-top: 0rem;
                padding-left: 0rem;
                padding-right: 0rem;
                max-width: 100%;
            }

            /* Remove header spacing completely */
            h1, h2, h3 {
                margin-top: -1.5rem;
                margin-bottom: 0.5rem;
                padding: 0rem;
            }

            /* Make the app take full viewport height */
            .main .block-container {
                padding-top: 0rem;
                padding-bottom: 0rem;
            }

            /* Adjust app container to start from top */
            .appview-container {
                top: 0;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <style>
        iframe[width="{cw_width+50}"]  {{
            position: fixed !important;
            bottom: -25px !important;
            left: 5px !important;
            z-index: 9999 !important;
            background-color: transparent !important;
        }}
    </style>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    if st.runtime.exists():
        main()
    else:
        sys.argv = ["streamlit", "run", sys.argv[0]]
        sys.exit(stcli.main())
