import os
import json
import copy
import pprint
import base64
from besser.agent.core.session import Session
from besser.utilities.web_modeling_editor.backend.services import domain_model_to_json
from modeling_patterns import (
    get_configuration_class_enum,
    get_configuration_attributes,
    get_configuration_abstract_class,
    get_configuration_relationships,
    get_configuration_association_class,
    get_configuration_lowerbound_cardinalities,
    get_configuration_upperbound_cardinalities,
    get_configuration_element_relevance_classes,
    get_configuration_element_relevance_attributes,
    get_configuration_concept_decision,
    get_configuration_class_generalization
)
configuration_steps = [
    get_configuration_element_relevance_classes,
    get_configuration_element_relevance_attributes,
    get_configuration_attributes,
    get_configuration_concept_decision,
    get_configuration_class_enum,
    get_configuration_relationships,
    get_configuration_lowerbound_cardinalities,
    get_configuration_upperbound_cardinalities,
]

deferred_steps = [
    get_configuration_class_generalization,
    get_configuration_abstract_class,
    get_configuration_association_class,
]

PATTERN_PRIORITY = {
    "ElementRelevanceConfiguration": 1,
    "AttributeVsInheritanceConfiguration": 2,
    "ConceptDecisionConfiguration": 3,
    "ClassVsAttributeConfiguration": 3,
    "AttributeVsEnumerationConfiguration": 4,
    "EnumerationVsInheritanceConfiguration": 5,
    "CompositionVsAssociationConfiguration": 6,
    "LowerboundCardinalityOneVsManyConfiguration": 7,
    "UpperboundCardinalityOneVsManyConfiguration": 8,
    "ClassGeneralizationConfiguration": 9,
    "ConcreteVsAbstractClassConfiguration": 10,
    "AssociationClassVsClassConfiguration": 11,
}

TYPE_PRIORITY = {
    "class": 1,
    "subclass": 1,
    "attribute": 2,
    "enumeration": 3,
    "composition": 4,
    "association": 5,
    "cardinality": 6,
    "parentclass": 7,
    "superclass": 8,
    "associationclass": 9
}

DIRECTION_PRIORITY = {
    "source": 1,
    "target": 2,
}

__all__ = [
    'domain_model_to_json',
    'render_model_in_editor',
    'render_submodel_in_editor',
    'generate_json_log',
    'configuration_steps',
    'deferred_steps',
    'PATTERN_PRIORITY',
    'TYPE_PRIORITY',
    'DIRECTION_PRIORITY',
    'identify_element_from_config',
    'get_element_identifier',
    'sort_configurations',
    'format_relationship_for_log',
    'format_element_for_log',
    'copy_file',
    'is_new_file',
    'is_json',
    'get_configuration_confidence',
    'call_configuration_function',
    'list_all_configurations',
    'list_all_submodel_configurations',
    'update_selected_configuration'
]

def copy_file(src, dst_folder):
    import os
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

# Configuration Management Functions
def get_configuration_confidence(session: Session, configuration):
    conf_confidence_map = session.get('conf_confidence_map')
    return conf_confidence_map.get(id(configuration), 0.0)

def call_configuration_function(session: Session, config_func, domain_model, domain_model_alt):
    patterns = session.get('modeling_patterns')
    if patterns is not None:
        func_name = config_func.__name__
        if hasattr(patterns, func_name):
            method = getattr(patterns, func_name)
            return method(domain_model, domain_model_alt)
    return config_func(domain_model, domain_model_alt)

def list_all_configurations(session: Session, use_deferred=False):
    all_configurations = []
    all_selected_configurations = []
    current_step_index = 0

    updated_domain_model = session.get('updated_domain_model')
    domain_model_alt = session.get('domain_model_alt')

    steps_to_use = deferred_steps if use_deferred else configuration_steps

    while current_step_index < len(steps_to_use):
        config_func = steps_to_use[current_step_index]
        current_step_index += 1
        configurations, selected_configurations = call_configuration_function(session, config_func, updated_domain_model, domain_model_alt)
        all_configurations += configurations
        all_selected_configurations += selected_configurations
        configurations = [c[3] for c in selected_configurations]
    return all_configurations, all_selected_configurations

def list_all_submodel_configurations(session: Session, submodel, submodel_alt, use_deferred=False):
    all_configurations = []
    all_selected_configurations = []
    current_step_index = 0

    steps_to_use = deferred_steps if use_deferred else configuration_steps

    while current_step_index < len(steps_to_use):
        config_func = steps_to_use[current_step_index]
        current_step_index += 1
        configurations, selected_configurations = call_configuration_function(session, config_func, submodel, submodel_alt)
        all_configurations += configurations
        all_selected_configurations += selected_configurations
        configurations = [c[3] for c in selected_configurations]
    return all_configurations, all_selected_configurations

def update_selected_configuration(submodel_selected_configurations, triggered_questions, all_selected_configurations):
    triggered_hashes = {hash(q.strip()) for q in triggered_questions}
    full_model_hashes = {hash(sc.question.strip()) for _, _, _, sc in all_selected_configurations}
    updated_submodel_selected_configurations = [
        (cc, a, b, sc)
        for cc, a, b, sc in submodel_selected_configurations
        if hash(sc.question.strip()) in full_model_hashes and hash(sc.question.strip()) not in triggered_hashes
    ]
    return updated_submodel_selected_configurations

def identify_element_from_config(config):
    if hasattr(config, 'originated_from') and config.originated_from:
        return config.originated_from
    return ("unknown", None)

def get_element_identifier(element_type, element_obj):
    if element_type in ["composition", "association", "cardinality"]:
        if element_obj and hasattr(element_obj, 'source') and hasattr(element_obj, 'target') and hasattr(element_obj, 'type'):
            source_name = getattr(element_obj.source, "name", "unknown")
            target_name = getattr(element_obj.target, "name", "unknown")
            rel_type = getattr(element_obj, "type", "unknown")
            return f"{source_name}-{rel_type}-{target_name}"
    return getattr(element_obj, "name", "unknown") if element_obj else "unknown"

def sort_configurations(configurations):
    name_order = {}
    counter = 0

    for cfg in configurations:
        try:
            elem = identify_element_from_config(cfg)
        except Exception:
            elem = None
        element_type = elem[0] if elem and len(elem) > 0 and elem[0] is not None else "unknown"
        identifier = get_element_identifier(element_type, elem[1] if elem and len(elem) > 1 else None)
        key = (element_type, identifier)
        if key not in name_order:
            name_order[key] = counter
            counter += 1

    def key_func(cfg):
        try:
            elem = identify_element_from_config(cfg)
        except Exception:
            elem = None

        element_type = elem[0] if elem and len(elem) > 0 and elem[0] is not None else "unknown"
        identifier = get_element_identifier(element_type, elem[1] if elem and len(elem) > 1 else None)

        element_type_priority = TYPE_PRIORITY.get(element_type, 999)
        name_priority = name_order.get((element_type, identifier), 999)

        direction = getattr(cfg, 'direction', None)
        direction_priority = DIRECTION_PRIORITY.get(direction, 999) if direction else 999

        pattern = getattr(cfg.__class__, "__name__", "unknown")
        pattern_priority = PATTERN_PRIORITY.get(pattern, 999)

        return (element_type_priority, name_priority, direction_priority, pattern_priority)

    return sorted(configurations, key=key_func)

def format_relationship_for_log(rel):
    if not hasattr(rel, 'source') or not hasattr(rel, 'target'):
        return str(rel)
    source_name = getattr(rel.source, 'name', str(rel.source))
    target_name = getattr(rel.target, 'name', str(rel.target))

    formatted = {
        'source': source_name,
        'target': target_name,
        'type': getattr(rel, 'type', '?'),
        'name': getattr(rel, 'name', ''),
        'source_cardinality': str(getattr(rel, 'sourceCardinality', '?')),
        'target_cardinality': str(getattr(rel, 'targetCardinality', '?'))
    }

    return formatted

def format_element_for_log(element_tuple):
    if not element_tuple:
        return None
    element_type, element_obj = element_tuple
    if element_type in ['lowerbound_cardinality', 'upperbound_cardinality', 'cardinality', 'composition', 'association']:
        element_name = format_relationship_for_log(element_obj)
    elif isinstance(element_obj, list):
        element_names = [getattr(e, 'name', str(e)) for e in element_obj]
        element_name = f"[{', '.join(element_names)}]"
    else:
        element_name = getattr(element_obj, 'name', str(element_obj))

    return {'type': element_type, 'description': element_name}

def find_named_elements_by_type(json_obj, allowed_types):
    matches = []
    if isinstance(json_obj, dict):
        if json_obj.get("type") in allowed_types and "name" in json_obj:
            matches.append(json_obj)

        for value in json_obj.values():
            matches.extend(find_named_elements_by_type(value, allowed_types))

    elif isinstance(json_obj, list):
        for item in json_obj:
            matches.extend(find_named_elements_by_type(item, allowed_types))

    return matches


def build_elements_maps(json_doc):
    by_id = {}
    by_name_type = {}
    if not isinstance(json_doc, dict):
        return by_id, by_name_type
    elems = json_doc.get("elements", {})
    if isinstance(elems, dict):
        for el_id, el in elems.items():
            if not isinstance(el, dict):
                continue
            if "id" not in el:
                el["id"] = el_id
            by_id[el.get("id")] = el
            if "name" in el and "type" in el:
                by_name_type[(el["name"], el["type"])] = el
    elif isinstance(elems, list):
        for el in elems:
            if not isinstance(el, dict):
                continue
            if "id" in el:
                by_id[el["id"]] = el
            if "name" in el and "type" in el:
                by_name_type[(el["name"], el["type"])] = el

    return by_id, by_name_type

def extract_relationships_top(json_doc):
    if not isinstance(json_doc, dict):
        return []
    r = json_doc.get("relationships", {})
    if isinstance(r, dict):
        return list(r.values())
    elif isinstance(r, list):
        return r[:]
    return []

def name_of_element(by_id_map, elem_id):
    if not elem_id:
        return None
    el = by_id_map.get(elem_id)
    return el.get("name") if isinstance(el, dict) else None

def normalize_name(n):
    if n is None:
        return None
    if not isinstance(n, str):
        return None
    s = n.strip()
    return s if s != "" else None

def rel_type_loose_match(a, b):
    if a == b:
        return True
    if not a or not b:
        return False
    a_low = a.lower()
    b_low = b.lower()
    keywords = ["association", "bidirectional", "inheritance", "composition", "aggregation"]
    for kw in keywords:
        if kw in a_low and kw in b_low:
            return True
    if a_low.endswith(b_low) or b_low.endswith(a_low):
        return True
    return False


def copy_relationships_by_source_target_name(old_json, new_json, verbose=True):
    old_by_id, _ = build_elements_maps(old_json)
    new_by_id, _ = build_elements_maps(new_json)
    old_rels = extract_relationships_top(old_json)
    new_rels = extract_relationships_top(new_json)
    summary = {"old_rels": len(old_rels), "new_rels": len(new_rels), "copied": [], "not_copied": []}
    if verbose:
        print(f"old elements: {len(old_by_id)}, new elements: {len(new_by_id)}")
        print(f"old relationships: {len(old_rels)}, new relationships: {len(new_rels)}\n")
    def endpoint_names_from_rel(rel, by_id_map):
        src_id = rel.get("source", {}).get("element")
        tgt_id = rel.get("target", {}).get("element")
        src_name = normalize_name(name_of_element(by_id_map, src_id) or rel.get("source", {}).get("name"))
        tgt_name = normalize_name(name_of_element(by_id_map, tgt_id) or rel.get("target", {}).get("name"))
        return src_name, tgt_name
    prepared_new = []
    for nr in new_rels:
        ns, nt = endpoint_names_from_rel(nr, new_by_id)
        new_rel_name = normalize_name(nr.get("name"))
        new_type = nr.get("type")
        prepared_new.append((nr, ns, nt, new_rel_name, new_type))

    for old_rel in old_rels:
        if not isinstance(old_rel, dict):
            summary["not_copied"].append((None, "old_rel_not_dict"))
            continue

        old_rel_id = old_rel.get("id")
        old_rel_name = normalize_name(old_rel.get("name"))
        old_type = old_rel.get("type")

        old_src_name, old_tgt_name = endpoint_names_from_rel(old_rel, old_by_id)
        if not old_src_name or not old_tgt_name:
            summary["not_copied"].append((old_rel_id, "could_not_resolve_old_endpoints"))
            if verbose:
                print(f"SKIP {old_rel_id}: can't resolve old endpoints (src:{old_src_name}, tgt:{old_tgt_name})")
            continue

        if verbose:
            print(f"Matching old_rel {old_rel_id!r} name={old_rel_name!r} type={old_type!r} endpoints=({old_src_name!r},{old_tgt_name!r})")

        matched = False
        if old_rel_name is not None:
            for nr, ns, nt, new_rel_name, new_type in prepared_new:
                if new_type != old_type:
                    continue
                if ((ns == old_src_name and nt == old_tgt_name) or (ns == old_tgt_name and nt == old_src_name)):
                    # copy fields
                    copied_fields = []
                    if "path" in old_rel:
                        nr["path"] = copy.deepcopy(old_rel["path"])
                        copied_fields.append("path")
                    if "bounds" in old_rel:
                        nr["bounds"] = copy.deepcopy(old_rel["bounds"])
                        copied_fields.append("bounds")
                    # copy direction if present
                    if "source" in old_rel and "direction" in old_rel.get("source", {}):
                        nr.setdefault("source", {})["direction"] = copy.deepcopy(old_rel["source"]["direction"])
                        copied_fields.append("source.direction")
                    if "target" in old_rel and "direction" in old_rel.get("target", {}):
                        nr.setdefault("target", {})["direction"] = copy.deepcopy(old_rel["target"]["direction"])
                        copied_fields.append("target.direction")
                    if "isManuallyLayouted" in old_rel:
                        nr["isManuallyLayouted"] = copy.deepcopy(old_rel["isManuallyLayouted"])
                        copied_fields.append("isManuallyLayouted")

                    summary["copied"].append((old_rel_id, nr.get("id"), copied_fields))
                    if verbose:
                        print(f"  -> strict match: copied {copied_fields} to new_rel {nr.get('id')}")
                    matched = True
                    break
        if matched:
            continue

        for nr, ns, nt, new_rel_name, new_type in prepared_new:
            if not ((ns == old_src_name and nt == old_tgt_name) or (ns == old_tgt_name and nt == old_src_name)):
                continue
            if rel_type_loose_match(old_type, new_type):
                copied_fields = []
                if "path" in old_rel:
                    nr["path"] = copy.deepcopy(old_rel["path"])
                    copied_fields.append("path")
                if "bounds" in old_rel:
                    nr["bounds"] = copy.deepcopy(old_rel["bounds"])
                    copied_fields.append("bounds")
                if "source" in old_rel and "direction" in old_rel.get("source", {}):
                    nr.setdefault("source", {})["direction"] = copy.deepcopy(old_rel["source"]["direction"])
                    copied_fields.append("source.direction")
                if "target" in old_rel and "direction" in old_rel.get("target", {}):
                    nr.setdefault("target", {})["direction"] = copy.deepcopy(old_rel["target"]["direction"])
                    copied_fields.append("target.direction")
                if "isManuallyLayouted" in old_rel:
                    nr["isManuallyLayouted"] = copy.deepcopy(old_rel["isManuallyLayouted"])
                    copied_fields.append("isManuallyLayouted")
                summary["copied"].append((old_rel_id, nr.get("id"), copied_fields))
                if verbose:
                    print(f"  -> fallback match by endpoints+type: copied {copied_fields} to new_rel {nr.get('id')} (new_type={new_type})")
                matched = True
                break
        if not matched:
            summary["not_copied"].append((old_rel_id, "no_matching_new_rel_found"))
            if verbose:
                print(f"  -> NO MATCH for old_rel {old_rel_id}. (checked {len(prepared_new)} new rels)\n")

    if verbose:
        print("\nSUMMARY:")
        print(" copied:", len(summary["copied"]))
        print(" not_copied:", len(summary["not_copied"]))
        if summary["copied"]:
            print(" Details copied:")
            pprint.pprint(summary["copied"], width=140)
    return summary

def copy_bounds_for_all_classes(old_json, new_json):
    allowed_types = {"Class", "AbstractClass", "Enumeration"}
    old_nodes = find_named_elements_by_type(old_json, allowed_types)
    new_nodes = find_named_elements_by_type(new_json, allowed_types)
    old_by_name = {node["name"]: node for node in old_nodes}
    for new_node in new_nodes:
        name = new_node["name"]
        if name in old_by_name and "bounds" in old_by_name[name]:
            new_node["bounds"] = old_by_name[name]["bounds"].copy()

def json_bounds(session: Session, new_json):
    """Preserve visual layout (bounds, paths) from previous JSON state."""
    updated_json = new_json.copy()
    old_json = session.get('prev_json')
    copy_bounds_for_all_classes(old_json, updated_json)
    copy_relationships_by_source_target_name(old_json, updated_json)
    return updated_json

# Editor Conversion Functions
def render_model_in_editor(session: Session, agent, buml):
    sessions = agent._sessions
    buml_json = domain_model_to_json(buml)

    answer = json.dumps(buml_json)
    session.set('model_exists', True)
    session.set('prev_json', buml_json)
    editor_sid = session.get('sid_editor')
    session_editor = sessions[editor_sid]
    session_editor.reply(answer)

def render_submodel_in_editor(session: Session, agent, submodel):
    sessions = agent._sessions
    buml = submodel.to_buml()
    buml_json = domain_model_to_json(buml)

    answer = json.dumps(buml_json)
    session.set('model_exists', True)
    session.set('prev_json', buml_json)
    editor_sid = session.get('sid_editor')
    session_editor = sessions[editor_sid]
    session_editor.reply(answer)

# Logging Functions
def generate_json_log(session: Session, max_questions):
    """Generate JSON log from session data at end of interaction."""
    domain_folder = session.get('domain_folder')
    domain = session.get('domain')
    initial_model = session.get('initial_domain_model')
    final_model = session.get('updated_domain_model')
    bfs_order = session.get('bfs_order')

    text_questions = session.get('text_questions_triggered')
    answers = session.get('answers_log')
    model_changes = session.get('model_changes_log')
    question_metadata = session.get('question_metadata')
    model_snapshots = session.get('model_snapshots')
    origin_log = session.get('origin_log')
    resulting_log = session.get('resulting_log')
    llm_raw_responses = session.get('llm_raw_responses')

    # Get session-level metadata
    session_id = str(session.id)
    user_profile = session.get('user_profile')

    log_data = {
        "session_id": session_id,
        "domain": domain if domain else "",
        "user_profile": user_profile if user_profile else "low",
        "initial_model": {
            "plantuml": initial_model.generate_plantuml() if initial_model else ""
        },
        "bfs_traversal": [
            {
                "pos": i + 1,
                "class": cls.name,
                "confidence": round(cls.get_metadata().get_score(), 2) if cls.get_metadata() else 0.0
            }
            for i, cls in enumerate(bfs_order)
        ],
        "questions": [],
        "final_model": {
            "plantuml": final_model.generate_plantuml() if final_model else ""
        },
        "summary": {}
    }

    for i, metadata in enumerate(question_metadata):
        # Determine answer source from llm_raw_responses
        answer_source = "user"
        if llm_raw_responses and i < len(llm_raw_responses):
            if llm_raw_responses[i] is not None:
                answer_source = "llm"

        question_entry = {
            "q_num": metadata['q_num'],
            "question": metadata['question'],
            "option_1": metadata['option_1'],
            "option_2": metadata['option_2'],
            "pattern": metadata['pattern'],
            "confidence": round(metadata['confidence'], 2),
            "visiting_class": metadata['visiting_class'],
            "submodel_size": metadata['submodel_size']
        }

        if i < len(origin_log) and origin_log[i]:
            question_entry['originated_from'] = origin_log[i]

        question_entry['selected'] = answers[i] if i < len(answers) else "Unknown"
        question_entry['model_changed'] = model_changes[i] if i < len(model_changes) else False
        question_entry['answer_source'] = answer_source

        if i < len(resulting_log) and resulting_log[i]:
            question_entry['resulting_element'] = resulting_log[i]

        if question_entry['model_changed'] and i < len(model_snapshots) and model_snapshots[i]:
          question_entry['updated_model'] = model_snapshots[i]

        log_data['questions'].append(question_entry)
    total_questions = len(question_metadata)
    total_changes = sum(model_changes) if model_changes else 0
    changes_by_pattern = {}
    for i, metadata in enumerate(question_metadata):
        pattern = metadata['pattern']
        if pattern not in changes_by_pattern:
            changes_by_pattern[pattern] = 0
        if i < len(model_changes) and model_changes[i]:
            changes_by_pattern[pattern] += 1

    log_data['summary'] = {
        "total_questions": total_questions,
        "model_changes": total_changes,
        "changes_by_pattern": changes_by_pattern
    }
    json_filename = "interaction_log.json"
    json_path = os.path.join(domain_folder, json_filename)
    try:
        with open(json_path, 'w') as f:
            json.dump(log_data, f, indent=2)
        print(f"JSON log saved to: {json_path}")
    except Exception as e:
        print(f"Error saving JSON log: {e}")
