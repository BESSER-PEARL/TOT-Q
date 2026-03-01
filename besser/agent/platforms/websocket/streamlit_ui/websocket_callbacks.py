from __future__ import annotations

import base64
import json
from datetime import datetime
from io import StringIO

import numpy as np
import pandas as pd

from besser.agent.core.message import MessageType, Message
from besser.agent.exceptions.logger import logger
from besser.agent.platforms.payload import PayloadAction, Payload
from besser.agent.platforms.websocket.streamlit_ui.session_management import get_streamlit_session
from besser.agent.platforms.websocket.streamlit_ui.vars import QUEUE

try:
    import cv2
except ImportError:
    logger.warning("cv2 dependencies in websocket_callbacks.py could not be imported. You can install them from "
                   "the requirements/requirements-extras.txt file")
try:
    import plotly
except ImportError:
    logger.warning("plotly dependencies in websocket_callbacks.py could not be imported. You can install them from "
                   "the requirements/requirements-extras.txt file")

def on_message(ws, payload_str):
    # https://github.com/streamlit/streamlit/issues/2838
    streamlit_session = get_streamlit_session()
    payload: Payload = Payload.decode(payload_str)
    content = None
    if payload.action == PayloadAction.AGENT_REPLY_STR.value:
        content = payload.message
        t = MessageType.STR
    elif payload.action == PayloadAction.AGENT_REPLY_MARKDOWN.value:
        content = payload.message
        t = MessageType.MARKDOWN
    elif payload.action == PayloadAction.AGENT_REPLY_HTML.value:
        content = payload.message
        t = MessageType.HTML
    elif payload.action == PayloadAction.AGENT_REPLY_FILE.value:
        content = payload.message
        t = MessageType.FILE
    elif payload.action == PayloadAction.AGENT_REPLY_IMAGE.value:
        decoded_data = base64.b64decode(payload.message)  # Decode base64 back to bytes
        np_data = np.frombuffer(decoded_data, np.uint8)  # Convert bytes to numpy array
        img = cv2.imdecode(np_data, cv2.IMREAD_COLOR)  # Decode numpy array back to image
        content = img
        t = MessageType.IMAGE
    elif payload.action == PayloadAction.AGENT_REPLY_DF.value:
        content = pd.read_json(StringIO(payload.message))
        t = MessageType.DATAFRAME
    elif payload.action == PayloadAction.AGENT_REPLY_PLOTLY.value:
        content = plotly.io.from_json(payload.message)
        t = MessageType.PLOTLY
    elif payload.action == PayloadAction.AGENT_REPLY_LOCATION.value:
        content = {
            'latitude': [payload.message['latitude']],
            'longitude': [payload.message['longitude']]
        }
        t = MessageType.LOCATION
    elif payload.action == PayloadAction.AGENT_REPLY_OPTIONS.value:
        t = MessageType.OPTIONS
        d = json.loads(payload.message)
        content = []
        for button in d.values():
            content.append(button)
    elif payload.action == PayloadAction.AGENT_REPLY_RAG.value:
        t = MessageType.RAG_ANSWER
        content = payload.message
    if content is not None:
        message = Message(t=t, content=content, is_user=False, timestamp=datetime.now())
        streamlit_session._session_state[QUEUE].put(message)

    streamlit_session._handle_rerun_script_request()


def on_error(ws, error):
    print(f"❌ CALLBACK: Streamlit WebSocket error: {error}", flush=True)
    logger.error(f"❌ Streamlit WebSocket error: {error}")


def on_open(ws):
    print("✅ CALLBACK: Streamlit WebSocket connection opened successfully", flush=True)
    logger.info("✅ Streamlit WebSocket connection opened successfully")


def on_close(ws, close_status_code, close_msg):
    print(f"⚠️ CALLBACK: Streamlit WebSocket connection closed: {close_status_code} - {close_msg}", flush=True)
    logger.warning(f"⚠️ Streamlit WebSocket connection closed: {close_status_code} - {close_msg}")


def on_ping(ws, data):
    pass


def on_pong(ws, data):
    pass