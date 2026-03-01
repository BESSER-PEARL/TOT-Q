import queue
import sys
import threading
from pathlib import Path

# Add project root to path (works both locally and in Docker)
try:
    current_file = Path(__file__).resolve()
    project_root = current_file.parents[4]  # Go up 4 levels from initialization.py
    if str(project_root) not in sys.path:
        sys.path.append(str(project_root))
    print(f"✅ Added to sys.path: {project_root}", flush=True)
except Exception as path_error:
    print(f"❌ Error setting up sys.path: {path_error}", flush=True)

import streamlit as st
import websocket
from streamlit.runtime.scriptrunner_utils.script_run_context import add_script_run_ctx

try:
    from besser.agent.exceptions.logger import logger
    from besser.agent.platforms.websocket.streamlit_ui.session_management import session_monitoring
    from besser.agent.platforms.websocket.streamlit_ui.vars import SESSION_MONITORING_INTERVAL, SUBMIT_TEXT, HISTORY, QUEUE, \
        WEBSOCKET, SESSION_MONITORING, SUBMIT_AUDIO, SUBMIT_FILE
    from besser.agent.platforms.websocket.streamlit_ui.websocket_callbacks import on_open, on_error, on_message, on_close, on_ping, on_pong
    print("✅ All BESSER imports successful", flush=True)
except ImportError as import_err:
    print(f"❌ IMPORT ERROR in initialization.py: {import_err}", flush=True)
    import traceback
    traceback.print_exc()
    raise


def initialize():
    # Try multiple output methods
    import sys
    sys.stderr.write("🚀 STDERR: initialize() called!\n")
    sys.stderr.flush()
    print("🚀 STDOUT: initialize() called!", flush=True)
    logger.info("🚀 initialize() function called!")

    if SUBMIT_TEXT not in st.session_state:
        st.session_state[SUBMIT_TEXT] = False

    if SUBMIT_AUDIO not in st.session_state:
        st.session_state[SUBMIT_AUDIO] = False

    if SUBMIT_FILE not in st.session_state:
        st.session_state[SUBMIT_FILE] = False

    if HISTORY not in st.session_state:
        st.session_state[HISTORY] = []

    if QUEUE not in st.session_state:
        st.session_state[QUEUE] = queue.Queue()

    websocket_exists = WEBSOCKET in st.session_state
    print(f"DEBUG: Checking if WEBSOCKET in session_state: {websocket_exists}", flush=True)
    sys.stderr.write(f"DEBUG STDERR: WEBSOCKET in session_state = {websocket_exists}\n")
    sys.stderr.flush()
    if WEBSOCKET not in st.session_state:
        print("DEBUG: WebSocket NOT in session_state, creating new connection", flush=True)
        import os
        # Try environment variables first (for Docker), then sys.argv, then defaults
        try:
            host = os.getenv('WEBSOCKET_BACKEND_HOST') or sys.argv[2]
            port = os.getenv('WEBSOCKET_BACKEND_PORT') or sys.argv[3]
        except Exception as e:
            # If not provided, use default values
            host = os.getenv('WEBSOCKET_BACKEND_HOST', 'localhost')
            port = os.getenv('WEBSOCKET_BACKEND_PORT', '8765')
            logger.warning(f"⚠️ Could not get WebSocket config from argv, using defaults: {e}")

        # Use wss:// for port 443 (Azure production), ws:// otherwise
        protocol = "wss" if str(port) == "443" else "ws"
        websocket_url = f"{protocol}://{host}:{port}/"
        print(f"DEBUG: WebSocket URL: {websocket_url}", flush=True)
        logger.info(f"🔌 Streamlit backend attempting to connect to WebSocket: {websocket_url}")

        try:
            print("DEBUG: Creating WebSocketApp instance", flush=True)
            ws = websocket.WebSocketApp(websocket_url,
                                        on_open=on_open,
                                        on_message=on_message,
                                        on_error=on_error,
                                        on_close=on_close,
                                        on_ping=on_ping,
                                        on_pong=on_pong)
            print("DEBUG: WebSocketApp instance created", flush=True)

            # For WSS connections, configure SSL settings
            import ssl
            sslopt = None
            if protocol == "wss":
                # Azure uses valid SSL certificates, but we might need to specify settings
                sslopt = {"cert_reqs": ssl.CERT_NONE}  # Disable certificate verification for testing
                print("DEBUG: Using WSS with SSL cert validation disabled", flush=True)
                logger.info("🔒 Using WSS with SSL (cert validation disabled for Azure)")

            print("DEBUG: Creating WebSocket thread", flush=True)
            websocket_thread = threading.Thread(target=lambda: ws.run_forever(sslopt=sslopt))
            add_script_run_ctx(websocket_thread)
            print("DEBUG: Starting WebSocket thread", flush=True)
            websocket_thread.start()
            print("DEBUG: WebSocket thread started, storing in session_state", flush=True)
            st.session_state[WEBSOCKET] = ws
            print("✅ WebSocket thread started successfully and stored in session_state", flush=True)
            logger.info(f"✅ WebSocket thread started successfully")
        except Exception as ws_error:
            print(f"❌ EXCEPTION creating WebSocket: {ws_error}", flush=True)
            logger.error(f"❌ Failed to create WebSocket connection: {ws_error}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}", flush=True)
            logger.error(traceback.format_exc())
    else:
        print("DEBUG: WebSocket ALREADY in session_state, reusing existing connection", flush=True)

    if SESSION_MONITORING not in st.session_state:
        session_monitoring_thread = threading.Thread(target=session_monitoring,
                                                     kwargs={'interval': SESSION_MONITORING_INTERVAL})
        add_script_run_ctx(session_monitoring_thread)
        session_monitoring_thread.start()
        st.session_state[SESSION_MONITORING] = session_monitoring_thread
