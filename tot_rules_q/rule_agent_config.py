# app/config.py
import os
from dotenv import load_dotenv
load_dotenv()  

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MAX_QUESTIONS = float(os.getenv('MAX_QUESTIONS', None))
REFINEMENT_THRESHOLD = float(os.getenv('REFINEMENT_THRESHOLD', 0.8))
RELEVANCE_THRESHOLD = float(os.getenv("RELEVANCE_THRESHOLD", 0.4))
HIGH_CONFIDENCE = float(os.getenv('HIGH_CONFIDENCE', 0.8))
LOW_CONFIDENCE = float(os.getenv('LOW_CONFIDENCE', 0.8))
