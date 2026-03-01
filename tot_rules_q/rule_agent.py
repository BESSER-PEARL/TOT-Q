#import sys
import os
#sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from os.path import exists, dirname, join
from os import mkdir
import logging
import copy
import json
import base64
from besser.agent.core.agent import Agent
from besser.agent.core.session import Session
from simulated_expert import llm_qa_response
from configuration import set_question_module_for_session
from modeling_patterns import ModelingPatterns
from rule_agent_config import MAX_QUESTIONS, REFINEMENT_THRESHOLD
import subprocess
from os.path import exists, dirname, join
from convert_tot_to_rbagent import get_domain_models
from rule_agent_utils import render_model_in_editor, render_submodel_in_editor, generate_json_log, domain_model_to_json
from rule_agent_utils import configuration_steps, deferred_steps, PATTERN_PRIORITY, TYPE_PRIORITY, DIRECTION_PRIORITY
from rule_agent_utils import identify_element_from_config, get_element_identifier, sort_configurations, format_relationship_for_log, copy_file
from rule_agent_utils import get_configuration_confidence, call_configuration_function, list_all_configurations, list_all_submodel_configurations, update_selected_configuration

current_folder = dirname(__file__)
project_folder = dirname(current_folder)
domain_path = join(current_folder, 'domains/')
logs_path = join(current_folder, 'tot_q/logs/')
DEFAULT_TOT_MODEL_PREFIX = 'tot_thoughts'

max_questions = MAX_QUESTIONS

def copy_file(src, dst_folder):
    os.makedirs(dst_folder, exist_ok=True)
    dst = os.path.join(dst_folder, os.path.basename(src))
    with open(src, "rb") as fsrc:
        with open(dst, "wb") as fdst:
            fdst.write(fsrc.read())
    return dst

def is_new_file(session: Session):
    is_duplicate = False
    if session.file:
        new_file_content = base64.b64decode(session.file.base64)
        prev_file = session.get('prev_file')
        if prev_file:
            prev_file_content = base64.b64decode(prev_file.base64)
            if new_file_content == prev_file_content:
                is_duplicate = True
    return not is_duplicate

def is_json(text: str) -> bool:
    try:
        obj = json.loads(text)
        return isinstance(obj, dict) or isinstance(obj, list)
    except (ValueError, TypeError):
        return False

logger = logging.getLogger(__name__)
base_folder = dirname(dirname(__file__))
log_folder = join(base_folder, 'logs/')

if not exists(log_folder):
    mkdir(log_folder)

agent = Agent('Domain Modeling Assistant')
agent.load_properties('config.ini')
websocket_platform = agent.use_websocket_platform(use_ui=True)

# STATES
start_state = agent.new_state('start_state', initial=True)
session_id_state = agent.new_state("session_id_state")
user_profile_state = agent.new_state("user_profile_state")
initial_model_state = agent.new_state('initial_model')
process_domain_state = agent.new_state("process_domain_state")
next_question_state = agent.new_state('next_question_state')
answer_question_state = agent.new_state('answer_question_state')
llm_answer_state = agent.new_state('llm_answer_intent')
ask_which_model_state = agent.new_state('ask_which_model_state')
final_model_state = agent.new_state('final_model')

# INTENTS
answer_question_intent = agent.new_intent('answer_question_intent', [
    'option 1:\n', 'option 2:\n','Option 1:\n', 'Option 2:\n'
])
llm_answer_intent = agent.new_intent('llm_answer_intent', [
    'i am not sure', 'help to decide'
])

# STATES BODIES' DEFINITION + TRANSITIONS
def start_message(session: Session):
    session.reply("session-id: " + str(session.id))
    session.set('max_questions', max_questions)
    questions_initiated = False
    current_step_index = 0
    questions_triggered= 0
    text_questions_triggered = []
    updated_domain_model = None
    configurations = []
    session.set('configurations', configurations)
    session.set('current_step_index', current_step_index)
    session.set('questions_triggered', questions_triggered)
    session.set('text_questions_triggered', text_questions_triggered)
    session.set('questions_initiated', questions_initiated)
    session.set('updated_domain_model', updated_domain_model) 
    session.set('answers_log', [])
    session.set('model_changes_log', [])
    session.set('question_metadata', [])
    session.set('conf_confidence_map', {})
    session.set('model_snapshots', [])
    session.set('origin_log', [])
    session.set('resulting_log', [])
    session.set('llm_raw_responses', [])
    session.reply("Welcome to the UML class modeling assistant.")
    session.reply("What is your knowledge of UML class diagram modeling?")
    websocket_platform.reply_options(session, [
        "Low: I'm new to UML class diagrams",
        "Medium: I understand UML concepts"
    ])

start_state.set_body(start_message)
start_state.when_no_intent_matched_go_to(session_id_state)

def session_id(session: Session):
    msg = session.message
    logger.info(f"Session started with ID: {session.id}")
    logger.info(f"Editor started with ID: {msg}")
    if "session-id" in msg:
        session_editor = msg.split(": ")[1]
        session.set('sid_editor', session_editor)

session_id_state.set_body(session_id)
session_id_state.when_no_intent_matched_go_to(user_profile_state) 

def user_profile(session: Session):
    msg = session.message
    patterns = None
    if 'low' in msg.lower():
        session.reply("Thank you, I will guide you with questions suitable for low knowledge of UML class diagrams.")
        session.set('user_profile', 'low')
        set_question_module_for_session('low')
        patterns = ModelingPatterns(user_profile= 'low')
    elif 'medium' in msg.lower():
        session.reply("Thank you, I will guide you with questions suitable for medium knowledge of UML class diagrams.")
        session.set('user_profile', 'medium')
        set_question_module_for_session('medium')
        patterns = ModelingPatterns(user_profile= 'medium')
    else:
        session.reply("Thank you, I will guide you with questions suitable for low knowledge of UML class diagrams.")
        session.set('user_profile', 'low')
        set_question_module_for_session('low')
        patterns = ModelingPatterns(user_profile= 'low')

    session.set("modeling_patterns", patterns)
    session.reply("Thank you. Please provide a description of your domain:")

user_profile_state.set_body(user_profile)
user_profile_state.when_no_intent_matched_go_to(process_domain_state)
user_profile_state.when_file_received_go_to(process_domain_state)

def process_domain(session: Session):
    editor_sid = session.get('sid_editor')
    if editor_sid is None:
        session.reply("I did not understood the message. Please try again.")
        return

    case_confidence_threshold = REFINEMENT_THRESHOLD
    session.set("confidence_threshold", case_confidence_threshold)
    patterns = session.get('modeling_patterns')
    patterns.set_confidence_threshold(case_confidence_threshold)

    sessions = agent._sessions
    global domain_path
    global logs_path

    domain = ""
    domain_model = None
    domain_model_alt = None

    session_id = str(session.id)
    domain_folder = join(domain_path, session_id + '/')
    os.makedirs(domain_folder, exist_ok=True)
    session.set('domain_folder', domain_folder)

    if session.file and is_new_file(session):
        text = base64.b64decode(session.file.base64).decode('utf-8')
        session.set('prev_file', session.file)
    else:
        text = session.message
    domain = str(text)
    domain_file_path = 'domain_input_' + session_id + '.txt'
    session.set('domain_input', domain_file_path)
    session.set('domain', domain)

    with open(domain_folder + domain_file_path, 'w') as f:
        f.write(domain)
        f.close()
    copy_file(domain_folder + domain_file_path, domain_path)
    session.reply("The model is being created. Please wait a moment...")
    try:
        result = subprocess.run(
            ["python", "run.py", "--model", "asocclass_3lev_unc.dmtot", "--domain", domain_file_path],
            capture_output=True,
            text=True,
            check=True,
            cwd=project_folder
        )
        tree_levels = DEFAULT_TOT_MODEL_PREFIX +"_" + domain_file_path.replace('.txt', '.json')
        domain_model, domain_model_alt, _, _ = get_domain_models(tree_levels)
        session.set('domain', domain)
        session.set('domain_model', copy.deepcopy(domain_model))
        session.set('domain_model_alt', copy.deepcopy(domain_model_alt))
        session.set('initial_domain_model', copy.deepcopy(domain_model))
        session.set('updated_domain_model', copy.deepcopy(domain_model))
        tot_json_path = join(logs_path, tree_levels)
        if exists(tot_json_path):
            copy_file(tot_json_path, domain_folder)
        buml = domain_model.to_buml()
        buml_json = domain_model_to_json(buml)
        answer = json.dumps(buml_json)
        session_editor = sessions[editor_sid]
        session_editor.reply("text-domain-desc: " + domain)
        session.reply("Thank you for waiting.The processing has finished.")
        bfs_order = domain_model.bfs_traverse_classes_priority()
        visited = []
        session.set('bfs_order', bfs_order)
        session.set('visited', visited)
        session.set('bfs_index', 0)
    except subprocess.CalledProcessError as e:
        session.reply("Error during LLM generation.")

process_domain_state.set_body(process_domain)
process_domain_state.go_to(initial_model_state)

def visualize_initial_model(session: Session):
    domain_model = session.get('initial_domain_model')
    buml = domain_model.to_buml()
    render_model_in_editor(session, agent, buml)
    session.reply("The initial model has been created based on the domain description.")
    session.reply("Now, let me ask you some questions about your domain.")
    websocket_platform.reply_options(session, ['Start with the questions'])

initial_model_state.set_body(visualize_initial_model)
initial_model_state.when_no_intent_matched_go_to(next_question_state)

def reset_bot(session: Session):
    configurations = []
    session.set('domain_model', None)
    session.set('updated_domain_model', None)
    session.set('initial_domain_model', None)

    session.set('configurations', configurations)
    session.set('current_step_index', 0)
    session.set('questions_initiated', False)
    session.set('questions_triggered', 0)
    session.set('text_questions_triggered', [])

def refresh_bfs_order_classes(session: Session):
      bfs_order = session.get('bfs_order')
      updated_domain_model = session.get('updated_domain_model')
      if not bfs_order or not updated_domain_model:
          return
      updated_classes_by_name = {cls.name: cls for cls in updated_domain_model.classes}
      refreshed_bfs_order = []
      for old_class in bfs_order:
          if old_class.name in updated_classes_by_name:
              refreshed_bfs_order.append(updated_classes_by_name[old_class.name])
      session.set('bfs_order', refreshed_bfs_order)

def next_configurations(session: Session):
    configurations = session.get('configurations')
    current_step_index = session.get('current_step_index')
    updated_domain_model = session.get('updated_domain_model')
    domain_model_alt = session.get('domain_model_alt')
    questions_triggered = session.get('questions_triggered')
    text_questions_triggered = session.get('text_questions_triggered')
    use_bfs_ordering = session.get('use_bfs_ordering')

    
    if len(configurations) == 0:
        if use_bfs_ordering:
            bfs_order = session.get('bfs_order') 
            visited = session.get('visited')
            bfs_index = session.get('bfs_index')

            while bfs_index < len(bfs_order):
                current_class = bfs_order[bfs_index]

                if current_class.name not in visited:
                    visited.append(current_class.name)
                    session.set('visited', visited)
                    current_class_exists = any(cls.name == current_class.name
                             for cls in updated_domain_model.classes)
                    if not current_class_exists:
                        bfs_index += 1
                        session.set('bfs_index', bfs_index)
                        continue

                submodel = updated_domain_model.extract_submodel(visited)
                submodel_alt = domain_model_alt 
                _, all_selected_configurations = list_all_configurations(session, use_deferred=False)
                _, submodel_selected_configurations = list_all_submodel_configurations(session, submodel, submodel_alt, use_deferred=False)
                all_configs = update_selected_configuration(submodel_selected_configurations, text_questions_triggered, all_selected_configurations)
                configurations = [c[3] for c in all_configs]
                if len(configurations) > 0:
                    conf_confidence_map = session.get('conf_confidence_map')
                    for cc, _, _, sc in all_configs:
                        conf_confidence_map[id(sc)] = cc
                    session.set('conf_confidence_map', conf_confidence_map)
                    sorted_configurations = sort_configurations(configurations)
                    session.set('configurations', sorted_configurations)
                    session.set('bfs_index', bfs_index)
                    break
                else:
                    bfs_index += 1
                    session.set('bfs_index', bfs_index)
                    
            if bfs_index >= len(bfs_order):
                print(f"DEBUG: BFS complete (visited {len(visited)} classes). Executing deferred patterns...")
                _, deferred_selected_configurations = list_all_configurations(session, use_deferred=True)
                deferred_configs_filtered = update_selected_configuration(
                    deferred_selected_configurations,
                    text_questions_triggered,
                    deferred_selected_configurations 
                )
                deferred_configs = [c[3] for c in deferred_configs_filtered]

                if len(deferred_configs) > 0:
                    print(f"DEBUG: Found {len(deferred_configs)} deferred configurations")
                    conf_confidence_map = session.get('conf_confidence_map')
                    for cc, _, _, sc in deferred_configs_filtered:
                        conf_confidence_map[id(sc)] = cc
                    session.set('conf_confidence_map', conf_confidence_map)
                    sorted_configurations = sort_configurations(deferred_configs)
                    session.set('configurations', sorted_configurations)
        else:
            while current_step_index < len(configuration_steps):
                config_func = configuration_steps[current_step_index]
                current_step_index += 1
                configurations, selected_configurations = call_configuration_function(session, config_func, updated_domain_model, domain_model_alt)
                configurations = [c[3] for c in selected_configurations]

                if len(configurations) > 0:
                    conf_confidence_map = session.get('conf_confidence_map')
                    for cc, _, _, sc in selected_configurations:
                        conf_confidence_map[id(sc)] = cc
                    session.set('conf_confidence_map', conf_confidence_map)

                    sorted_configurations = sort_configurations(configurations)
                    session.set('configurations', sorted_configurations)
                    session.set('current_step_index', current_step_index)
                    break

def ask_model_to_visualize(session: Session):
    session.reply("Please select which model you would like to visualize:")
    websocket_platform.reply_options(session, ['View Initial Model', 'View Final Model'])

    
ask_which_model_state.set_body(ask_model_to_visualize)
ask_which_model_state.when_no_intent_matched_go_to(final_model_state)

def visualize_final_model(session: Session):
    initial_domain_model = session.get('initial_domain_model')
    ibuml = initial_domain_model.to_buml()
    puml_buml = initial_domain_model.generate_plantuml()
    updated_domain_model = session.get('updated_domain_model')
    ubuml = updated_domain_model.to_buml()
    puml_ubuml = updated_domain_model.generate_plantuml()
    if 'Initial Model' in session.message:
        render_model_in_editor(session, agent, ibuml)
        session.reply("Editor was updated with the initial model.")
    elif 'Final Model' in session.message:
        render_model_in_editor(session, agent, ubuml)
        session.reply("Editor was updated with the final model proposed.")

final_model_state.set_body(visualize_final_model)
final_model_state.when_no_intent_matched_go_to(ask_which_model_state)

def next_question(session: Session):
    domain = session.get('domain')
    domain_model = session.get('domain_model')
    updated_domain_model = session.get('updated_domain_model')
    initial_domain_model = session.get('initial_domain_model')
    
    configurations = session.get('configurations')
    questions_initiated = session.get('questions_initiated')
    questions_triggered = session.get('questions_triggered')
    text_questions_triggered = session.get('text_questions_triggered')
    bfs_order = session.get('bfs_order')
    bfs_index = session.get('bfs_index')
    session.set('use_bfs_ordering', True)

    if not questions_initiated:
        updated_domain_model = copy.deepcopy(domain_model)
        session.set('updated_domain_model', updated_domain_model)
        next_configurations(session)
        configurations = session.get('configurations')
        session.set('questions_initiated', True)

        logger.info(f'Initial model:\n{initial_domain_model.generate_plantuml()}')

    max_questions = session.get('max_questions')
    if (max_questions is not None) and questions_triggered >= max_questions:
        session.reply("Reached the maximum number of questions. Here is the proposed domain model.")
        logger.info(f'Max questions reached. Final model:\n{updated_domain_model.generate_plantuml()}')
        generate_json_log(session, max_questions)

        return

    if len(configurations) == 0:
        session.reply("Thank you for your time. There is no more questions.")
        session.reply("This is the proposed domain model.")
        logger.info(f'Final model:\n{updated_domain_model.generate_plantuml()}')
        updated_domain_model = session.get('updated_domain_model')
        buml = updated_domain_model.to_buml()
        render_model_in_editor(session, agent, buml)
        generate_json_log(session, max_questions)
        ask_model_to_visualize(session)
    else:        
        conf_question, opt1, opt2 = configurations[0].get_question(domain, updated_domain_model)
        question = f"Question {questions_triggered + 1 }:\n{conf_question}" 
        opt1 = opt1.replace(': ', ': \n')
        opt2 = opt2.replace(': ', ': \n')
        opt3 = "I am not sure and need help to decide."

        question_metadata = session.get('question_metadata')
        visited = session.get('visited')
        bfs_index = session.get('bfs_index')
        bfs_order = session.get('bfs_order')
        current_class = "Unknown"
        if bfs_order and bfs_index < len(bfs_order):
            current_class = bfs_order[bfs_index].name

        pattern_name = configurations[0].__class__.__name__.replace('Configuration', '')
        if hasattr(configurations[0], 'get_pattern_name'):
            pattern_name = configurations[0].get_pattern_name()
        originated_from = None
        if hasattr(configurations[0], 'originated_from') and configurations[0].originated_from:
            elem_type, elem = configurations[0].originated_from
            originated_from = {
                'type': elem_type,
                'description': elem.name if hasattr(elem, 'name') else str(elem)
            }

        metadata = {
            'q_num': questions_triggered + 1,
            'question': conf_question,
            'option_1': configurations[0].option_1,
            'option_2': configurations[0].option_2,
            'pattern': pattern_name,
            'confidence': get_configuration_confidence(session, configurations[0]),
            'visiting_class': current_class,
            'submodel_size': len(visited),
            'originated_from': originated_from
        }
        question_metadata.append(metadata)
        session.set('question_metadata', question_metadata)

        dm = updated_domain_model
        submodel = dm.extract_submodel(visited)
        render_submodel_in_editor(session, agent, submodel)

        session.reply(question)
        websocket_platform.reply_options(session,[opt1,opt2, opt3])
        questions_triggered += 1
        text_questions_triggered.append(conf_question)
        session.set('questions_triggered', questions_triggered)
        session.set('text_questions_triggered', text_questions_triggered)
        logger.info(f'({configurations[0].__class__.__name__}) Question {questions_triggered}:\n{question}')

next_question_state.set_body(next_question)
next_question_state.when_intent_matched_go_to(answer_question_intent,answer_question_state)
next_question_state.when_intent_matched_go_to(llm_answer_intent,llm_answer_state)
next_question_state.when_no_intent_matched_go_to(llm_answer_state)

def process_answer(session: Session, option: str):
    domain_model = session.get('domain_model')
    updated_domain_model = session.get('updated_domain_model')
    questions_triggered = session.get('questions_triggered')
    configurations = session.get('configurations')
    model_snapshots = session.get('model_snapshots')
    visited = session.get('visited')

    if ("option 1" in option.lower()):
        session.reply('Ok, option 1 selected.')
        toUpdate = configurations[0].update(configurations[0], updated_domain_model, "Option 1")
    elif ("option 2" in option.lower()):
        session.reply('Ok, option 2 selected.')
        toUpdate = configurations[0].update(configurations[0], updated_domain_model, "Option 2")
    else:
        session.reply("I didn't understood. Please try again.")
        #questions_logger.info(f'DEBUG - Option not recognized')
        return
    logger.info(f'Answer to Q{questions_triggered}:\n{option}')

    originated_from = getattr(configurations[0], 'originated_from', None)
    resulting_element = getattr(configurations[0], 'resulting_element', None)
    origin_log = session.get('origin_log')
    resulting_log = session.get('resulting_log')

    if originated_from:
        element_type, element_obj = originated_from

        if element_type in ['lowerbound_cardinality', 'upperbound_cardinality', 'cardinality', 'composition', 'association']:
            element_name = format_relationship_for_log(element_obj)
        elif isinstance(element_obj, list):
            element_names = [getattr(e, 'name', str(e)) for e in element_obj]
            element_name = f"[{', '.join(element_names)}]"
        else:
            element_name = getattr(element_obj, 'name', str(element_obj))

        origin_log.append({'type': element_type, 'description': element_name})
    else:
        origin_log.append(None)

    if resulting_element:
        element_type, element_obj = resulting_element

        if element_type in ['lowerbound_cardinality', 'upperbound_cardinality', 'cardinality', 'composition', 'association']:
            element_name = format_relationship_for_log(element_obj)
        elif isinstance(element_obj, list):
            element_names = [getattr(e, 'name', str(e)) for e in element_obj]
            element_name = f"[{', '.join(element_names)}]"
        else:
            element_name = getattr(element_obj, 'name', str(element_obj))

        resulting_log.append({'type': element_type, 'description': element_name})
    else:
        resulting_log.append(None)

    session.set('origin_log', origin_log)
    session.set('resulting_log', resulting_log)

    answers_log = session.get('answers_log')
    answers_log.append(option)
    session.set('answers_log', answers_log)

    if toUpdate:
        updated_domain_model = copy.deepcopy(toUpdate)
        session.set('updated_domain_model', updated_domain_model)

    dm = None
    model_snapshots_with_conf = session.get('model_snapshots_with_conf') if session.get('model_snapshots_with_conf') else []
    if toUpdate:
        dm = updated_domain_model
        buml = updated_domain_model.to_buml()
        model_snapshots.append(updated_domain_model.generate_plantuml())
        model_snapshots_with_conf.append(updated_domain_model.model_with_confidence_values())
    else:
        dm = domain_model
        buml = domain_model.to_buml()
        model_snapshots.append(None)
        model_snapshots_with_conf.append(None)

    model_changes_log = session.get('model_changes_log')
    model_changes_log.append(toUpdate is not None)
    session.set('model_changes_log', model_changes_log)
    session.set('model_snapshots', model_snapshots)
    session.set('model_snapshots_with_conf', model_snapshots_with_conf)

    current_class_names = {cls.name for cls in dm.classes}
    bfs_order = session.get('bfs_order')
    bfs_index = session.get('bfs_index')
    bfs_class_names = {cls.name for cls in bfs_order}
    new_class_names = current_class_names - bfs_class_names
    if new_class_names:
        new_classes = [cls for cls in dm.classes
                        if cls.name in new_class_names]
        bfs_order = list(bfs_order)
        for cls in new_classes:
            bfs_order.insert(bfs_index + 1, cls)
        session.set('bfs_order', bfs_order)

    if toUpdate:
        submodel = dm.extract_submodel(visited + list(new_class_names))
        render_submodel_in_editor(session, agent, submodel)

    refresh_bfs_order_classes(session)

    answer = configurations[0]
    if answer.is_complete():
        configurations = configurations[1:]
        
    session.set('configurations', configurations)
    next_configurations(session)

    if toUpdate:
        session.set('domain_model', copy.deepcopy(updated_domain_model))
        if not answer.is_complete():
            session.set('updated_domain_model', copy.deepcopy(updated_domain_model))
        else:
            session.set('configurations', [])
            next_configurations(session)

def answer_question(session: Session):
    msg = session.message
    if is_json(msg):
        session.set('prev_json', json.loads(msg))
        session.set('model_exists', True)
        return

    # Track that this answer came from the user
    llm_raw_responses = session.get('llm_raw_responses')
    llm_raw_responses.append(None)
    session.set('llm_raw_responses', llm_raw_responses)

    process_answer(session, msg)
    
answer_question_state.set_body(answer_question)
answer_question_state.go_to(next_question_state)

def llm_answer(session: Session):

    msg = session.message
    if is_json(msg):
        session.set('prev_json', json.loads(msg))
        session.set('model_exists', True)
        return

    if ("option 1" in msg.lower()) or ("option 2" in msg.lower()):
        session.set('llm_raw_response', None)

        # Track that this answer came from the user
        llm_raw_responses = session.get('llm_raw_responses')
        llm_raw_responses.append(None)
        session.set('llm_raw_responses', llm_raw_responses)

        process_answer(session, msg)
        return
    
    consecutive_calls = session.get('llm_answer_consecutive_calls')
    if not consecutive_calls:
        consecutive_calls = session.set('llm_answer_consecutive_calls', 0)
    consecutive_calls = session.get('llm_answer_consecutive_calls') + 1
    session.set('llm_answer_consecutive_calls', consecutive_calls)

    if consecutive_calls > 1:
        print(f"ERROR: llm_answer called {consecutive_calls} times consecutively - INFINITE LOOP DETECTED")
        print("Breaking loop by transitioning to next_question")
        session.reply('There was an error.')
        configurations = session.get('configurations')
        return

    session.reply("Ok, review is in progress and a suggestion will be provided soon.")
    configurations = session.get('configurations')
    domain = session.get('domain')
    question, opt1, opt2 = configurations[0].question, configurations[0].option_1, configurations[0].option_2
    option = llm_qa_response(question,opt1,opt2, domain)
    session.set('llm_raw_response', option)

    # Track that this answer came from the LLM
    llm_raw_responses = session.get('llm_raw_responses')
    llm_raw_responses.append(option)
    session.set('llm_raw_responses', llm_raw_responses)

    option = "Thank you for your patience. Based on my review, I suggest the following:\n\n" + option
    session.reply(option)

    if "option 1" in option.lower():
        msg = opt1
    elif "option 2" in option.lower():
        msg = opt2
    else:
        msg = "The answer is unclear. Let me process the question and try again."
    process_answer(session, msg)
    print('consecutive', consecutive_calls)
    session.set('llm_answer_consecutive_calls', 0)

llm_answer_state.set_body(llm_answer)
llm_answer_state.go_to(next_question_state)

def fallback_body(session: Session):
    msg = session.message
    if ("option 1" in msg.lower()) or ("option 2" in msg.lower()):
        process_answer(session, msg)
        logger.info(f"Fallback processing due to incorrect intent with message: {msg}")
        return

    print("Fallback body activated.")
    print("Message:", msg)
    if is_json(msg):
        session.set('prev_json', json.loads(msg))
        session.set('model_exists', True)
        return
    if msg in ['View Initial Model', 'View Final Model']:
        visualize_final_model(session)
    else:
        session.reply("I didn't understood. Please try again.")
    
agent.set_global_fallback_body(fallback_body)


if __name__ == '__main__':
    #agent.run()
    try:
        agent.run()
    except Exception as e:
        print(f"\nCritical error occurred: {type(e).__name__}")
        print(f"Error details: {str(e)}")
        logger.error(f"Agent crashed with error: {type(e).__name__} - {str(e)}", exc_info=True)
        print("\nThe error has been logged. You can restart the agent to continue.")
