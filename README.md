<a name="readme-top"></a>
<!-- ABOUT THE PROJECT -->
## Towards Human-in-the-Loop LLM-enabled Domain Modeling

We propose to improve LLM-enabled domain model generation with a refinement loop. The workflow is organized in three main phases:

1. **Initial Modeling Phase**: Start with a domain description to create a draft domain model.  
2. **Iterative Improvement Phase**: Refine the domain model via a Q&A feedback loop.  
3. **Final Modeling Phase**: Presents the domain model with changes incorporated from domain expert's answer. 

![ToT-Q](experiments/ToT-Q/tot-q.png "ToT-Q")

The ToT-Q framework is supported by four components:

1. **ToT & Confidence Quantification** – Creates the domain model using [ToT4DM](https://github.com/BESSER-PEARL/dsl-tot-dm) framework and estimates confidence of the recommended elements.  
2. **Modeling Pattern Matching** – Detects modeling patterns in the domain model and prepares relevant data for question generation.  
3. **Question Generation & Selection** – Generates questions from matched patterns using a [rule-based agent](https://github.com/BESSER-PEARL/BESSER-Agentic-Framework), prioritizing the areas of uncertainty in the domain model.  
4. **Model Refinement** – Updates the domain model and confidence scores based on  domain expert’s answers, until all questions are addressed or a limit is reached.


The ToT-Q tool is developed using the [ToT4DM DSL tool](https://github.com/BESSER-PEARL/dsl-tot-dm) and [BESSER Agentic framework](https://github.com/BESSER-PEARL/BESSER-Agentic-Framework).

<!-- GETTING STARTED -->
## Setup

### Prerequisites

Request OpenAI or Azure keys to have access to the LLM API. Instructions are in the following links:

* [OpenAI](https://platform.openai.com/docs/quickstart)
* [AzureOpenAI](https://learn.microsoft.com/en-gb/azure/ai-foundry/openai/chatgpt-quickstart?tabs=keyless%2Ctypescript-keyless%2Cpython-new%2Ccommand-line&pivots=programming-language-python)

To configure the [ToT DSL](https://github.com/BESSER-PEARL/dsl-tot-dm):
 - Create the .env file as instructed in the [Tot4DM repo](https://github.com/BESSER-PEARL/dsl-tot-dm?tab=readme-ov-file#prerequisites).
 - Review the examples to configure the [ToT4DM DSL](https://github.com/BESSER-PEARL/dsl-tot-dm?tab=readme-ov-file#how-to-create-a-new-model-for-the-dsl).

To configure the BESSER Agentic framework:
 - Configure the config.ini file with the websocket options indicated in the [BESSER Agentic framework docs](https://besser-agentic-framework.readthedocs.io/latest/wiki/configuration_properties.html). 

<!-- RECOMMENDATIONS -->

### How to configure templates

To configure the templates, you can modify the question variables in the following [python file](tot_rules_q/template_questions.py).

### How to configure question triggers

Add in the [.env file](.env_example) the following variables to configure the trigger of questions:

```python
# Maximum number of questions in the Q&A loop
MAX_QUESTIONS = 10

# Confidence threshold for asking questions
CONFIDENCE_THRESHOLD = 0.8   # Suggested range: (0.5, 0.9]

# Confidence values used when updating the model based on expert answers
HIGH_CONFIDENCE = 0.9         # Suggested range: (0.5, 1.0]
LOW_CONFIDENCE = 0.4          # Suggested range: [0.1, 0.5]

# Expert simulation mode (0 = No simulation, 1 = Simulation)
SIMULATED_EXPERT = 1
```

### Run the project
1. Install Python 3.11 and create a virtual environment
2. Install the [required packages](requirements.txt):
   ```sh
   pip install -r requirements.txt
   ```
3. Configure the templates and question triggers in the [.env file](.env_example).
4. Run the rule-based agent (this agent call the LLM agents):
   ```sh
   python tot_rules_q/rule_agent.py
   ```
5. Run the chat application:
   ```sh
   python chat.py
   ```
6. A log will capture all the thoughts created by the LLM and questions triggered by the rule-based agent.
   
<!-- USAGE EXAMPLES -->
## Paper Experiments

The results of the experiments include the [reference models](experiments/ToT-Q/reference_model/) and the [output](experiments/ToT-Q/logs/) from the experiments.
To run the experiments, use the [input](experiments/ToT-Q/input/) data with the domain descriptions. Then execute the experiment:
   ```ssh   
   python tot_rules_q/rule_agent.py
   python chat.py
   ```
