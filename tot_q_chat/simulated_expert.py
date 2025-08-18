
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from enum import Enum
from pydantic import BaseModel
from tree_of_thought.llm import gpt,client, model_name

class Options(str, Enum):
    Option1 = "Option 1"
    Option2 = "Option 2"

class Answer(BaseModel):
    answer: Options

def llm_qa_response(question, option1, option2, domain):
    system_prompt = f"""
You are a domain expert that uses only the provided domain description to answer questions. 
If the domain description does not provide the information, you answer with the option that discards adding additional information in the model.
Please base your answer strictly on the domain description.
**Domain description:**  
{domain}
"""
    question = f"""
Please base your answer strictly on the domain description.
Question: The question is a hypothetical scenario
{question}

Options:  
{option1}  
{option2}

Which option is better for you?

**Instructions:**
Please answer with the option that aligns with the domain description.
"""
    response = client.chat.completions.create(
    model=model_name,
    messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
    temperature=0
    )

    result = response.choices[0].message.content
    print(response.choices[0].message.content)
    return result