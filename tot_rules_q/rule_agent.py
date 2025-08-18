#import sys
import os
#sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import besser
from besser.agent.core.agent import Agent
from besser.agent.core.session import Session
from modeling_patterns import  get_configuration_class_enum, get_configuration_abstract_class, get_configuration_relationships, get_configuration_association_class, get_configuration_lowerbound_cardinalities, get_configuration_upperbound_cardinalities
import logging
import copy
from os.path import exists, dirname, join
from os import mkdir
from dotenv import load_dotenv

load_dotenv()

max_questions = float(os.getenv('MAX_QUESTIONS', None))
domain = ""
domain_model = None
domain_model_alt = None
initial_domain_model = None
configurations = []
updated_domain_model = None
questions_initiated = False
current_step_index = 0
questions_triggered= 0
configuration_steps = [
    get_configuration_class_enum,
    get_configuration_abstract_class,
    get_configuration_relationships,
    get_configuration_lowerbound_cardinalities,
    get_configuration_upperbound_cardinalities,
    get_configuration_association_class,
]


logger = logging.getLogger(__name__)
base_folder = dirname(dirname(__file__))
log_folder = join(base_folder, 'logs/')

log_name = 'questions.txt'
if not exists(log_folder):
    mkdir(log_folder)
log_file = join(log_folder, log_name)
logging.basicConfig(filename = log_file, filemode="a", level=logging.INFO)

agent = Agent('Domain Modeling Assistant')
agent.load_properties('config.ini')
websocket_platform = agent.use_websocket_platform(use_ui=False)

# STATES
initial_state = agent.new_state('initial_state', initial=True)
process_domain_state = agent.new_state("process_domain_state")
next_question_state = agent.new_state('next_question_state')
formulate_question_state = agent.new_state('formulate_question_state')

# INTENTS
next_question_intent = agent.new_intent('next_question_intent', [
    'next',
    'question',
])
formulate_question_intent = agent.new_intent('formulate_question_intent', [
    'ask',
])

# STATES BODIES' DEFINITION + TRANSITIONS
default_intent = agent.new_intent('default_intent', [])

def initial_message(session: Session):
    session.reply("Please provide a description of your domain.")

initial_state.set_body(initial_message)
initial_state.when_no_intent_matched().go_to(process_domain_state)

import subprocess
from os.path import exists, dirname, join
from convert_tot_to_rbagent import get_domain_models

current_folder = dirname(__file__)
project_folder = dirname(current_folder)
domain_folder = join(project_folder, 'domains/')
tot_model_file = 'asocclass_3lev_unc.dmtot'

def process_domain(session: Session):
    global domain
    global domain_folder
    global domain_model
    global domain_model_alt
    global initial_domain_model
    event = session.event
    domain = event.message.strip()
    domain_file_path = 'domain_input.txt'
    
    with open(domain_folder + domain_file_path, 'w') as f:
        f.write(domain)
        f.close()
        
    session.reply("✅ Domain model received. Now starting to process it...")

    try:
        result = subprocess.run(
            ["python", "run.py", "--model", tot_model_file, "--domain", domain_file_path],
            capture_output=True,
            text=True,
            check=True
        )
        tree_levels = tot_model_file.replace('.dmtot', '_') + domain_file_path.replace('.txt', '.json')
        domain_model, domain_model_alt = get_domain_models(tree_levels)
        initial_domain_model = copy.deepcopy(domain_model)
        
        session.reply("Thank you for waiting.The processing has finished.")
        session.reply("Now, let me ask you some questions about your domain.")
    except subprocess.CalledProcessError as e:
        session.reply("❌ Error during reasoning process.")
        session.reply(str(e.stderr or e.stdout))

process_domain_state.set_body(process_domain)
process_domain_state.go_to(next_question_state)

next_question_state.when_intent_matched(next_question_intent).go_to(next_question_state)

def reset_bot():
    global configurations
    global initial_domain_model
    global updated_domain_model
    global questions_initiated
    global current_step_index
    global questions_triggered
    configurations = []
    initial_domain_model = copy.deepcopy(domain_model)
    updated_domain_model = None
    questions_initiated = False
    current_step_index = 0
    questions_triggered= 0

def next_configurations():
    global current_step_index
    global configurations
    if len(configurations) == 0:
        while current_step_index < len(configuration_steps):
            config_func = configuration_steps[current_step_index]
            current_step_index += 1
            configurations, selected_configurations= config_func(updated_domain_model, domain_model_alt)            
            configurations = [c[3] for c in selected_configurations]

            if len(configurations) > 0:
                break

def next_question(session: Session):
    global configurations
    global updated_domain_model
    global current_step_index
    global questions_initiated
    global questions_triggered
    if not questions_initiated:
        updated_domain_model = copy.deepcopy(domain_model)
        next_configurations()
        questions_initiated = True
        logger.info(f'Initial model:\n{initial_domain_model.generate_plantuml()}')
        
    if (max_questions is not None) and questions_triggered >= max_questions:
        session.reply("Reached the maximum number of questions. Here is the proposed domain model.")
        logger.info(f'Max questions reached. Final model:\n{updated_domain_model.generate_plantuml()}')
        return

    if len(configurations) == 0:
        session.reply("This is the proposed domain model.")
        logger.info(f'Final model:\n{updated_domain_model.generate_plantuml()}')
    else:
        puml1 = configurations[0].alternative_1_dm.generate_plantuml()
        puml2 = configurations[0].alternative_2_dm.generate_plantuml()
        puml3 = initial_domain_model.generate_plantuml()
        if updated_domain_model:
            puml4 = updated_domain_model.generate_plantuml()
        else:
            puml4 = domain_model.generate_plantuml()
        puml_combined = puml1 + \
            "@@@NEXT_UML@@@" + \
            puml2 + \
            "@@@NEXT_UML@@@" + \
            puml3 + \
            "@@@NEXT_UML@@@" + \
            puml4
        
        question, opt1, opt2 = configurations[0].question, configurations[0].option_1, configurations[0].option_2
        session.reply(puml_combined)
        session.reply(question)
        websocket_platform.reply_options(session,[opt1,opt2])
        questions_triggered += 1
        logger.info(f'({configurations[0].__class__.__name__}) Question {questions_triggered}:\n{question}')

next_question_state.set_body(next_question)

def formulate_question(session: Session):
    global configurations
    global updated_domain_model
    global questions_triggered
    event = session.event
    prediction = event.predicted_intent
    intent = prediction.intent
    msg = event.message

    if ("Option 1" in msg):
        session.reply('Ok, option 1')
        toUpdate = configurations[0].update(configurations[0], updated_domain_model, "Option 1")
    elif ("Option 2" in msg):
        session.reply('Ok, option 2')
        toUpdate = configurations[0].update(configurations[0], updated_domain_model, "Option 2")
    else:
        session.reply('I did not understood your response. Please check the options again.')

    logger.info(f'Answer to Q{questions_triggered}:\n{msg}')
    
    if toUpdate:
        updated_domain_model = toUpdate
    websocket_platform.reply_options(session,['Next question'])

    puml1 = configurations[0].alternative_1_dm.generate_plantuml()
    puml2 = configurations[0].alternative_2_dm.generate_plantuml()
    puml3 = initial_domain_model.generate_plantuml()
    if updated_domain_model:
        puml4 = updated_domain_model.generate_plantuml()
        if toUpdate:
            logger.info(f'Model update required:\n{puml4}')
        else:
            logger.info(f'Model update not required.')
    else:
        puml4 = domain_model.generate_plantuml()
    puml_combined = puml1 + \
        "@@@NEXT_UML@@@" + \
        puml2 + \
        "@@@NEXT_UML@@@" + \
        puml3 + \
        "@@@NEXT_UML@@@" + \
        puml4
    session.reply(puml_combined)
    answer = configurations[0]
    configurations = configurations[1:]
    next_configurations()

formulate_question_state.set_body(formulate_question)
formulate_question_state.go_to(next_question_state)

def fallback_body(session: Session):
    global configurations
    global updated_domain_model
    global questions_triggered
    event = session.event
    prediction = event.predicted_intent
    intent = prediction.intent
    msg = event.message

    if ("Option 1" in msg):
        session.reply('Ok, option 1')
        toUpdate = configurations[0].update(configurations[0], updated_domain_model, "Option 1")
    elif ("Option 2" in msg):
        session.reply('Ok, option 2')
        toUpdate = configurations[0].update(configurations[0], updated_domain_model, "Option 2")
    else:
        session.reply('I will check')

    
    logger.info(f'Answer to Q{questions_triggered}:\n{msg}')
    
    if toUpdate:
        updated_domain_model = toUpdate
    websocket_platform.reply_options(session,['Next question'])

    puml1 = configurations[0].alternative_1_dm.generate_plantuml()
    puml2 = configurations[0].alternative_2_dm.generate_plantuml()
    puml3 = initial_domain_model.generate_plantuml()
    if updated_domain_model:
        puml4 = updated_domain_model.generate_plantuml()
        if toUpdate:
            logger.info(f'Model update required:\n{puml4}')
        else:
            logger.info(f'Model update not required.')
    else:
        puml4 = domain_model.generate_plantuml()
    puml_combined = puml1 + \
        "@@@NEXT_UML@@@" + \
        puml2 + \
        "@@@NEXT_UML@@@" + \
        puml3 + \
        "@@@NEXT_UML@@@" + \
        puml4
    session.reply(puml_combined)
    answer = configurations[0]
    configurations = configurations[1:]
    next_configurations()

agent.set_global_fallback_body(fallback_body)

if __name__ == '__main__':
    agent.run()