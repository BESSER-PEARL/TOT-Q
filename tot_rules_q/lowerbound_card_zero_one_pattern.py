import copy
from tree_of_thought.model_elements import UMLClass, UMLAttribute, UMLEnumeration, Visibility, UMLRelationship, UMLDomainModel, UMLAssociationClass
from configuration import Configuration
from configuration import split_camel_case, correct_article, plural, name_format, is_similar
from configuration import high_confidence, low_confidence
from collections import Counter
from template_questions import generate_target_lowerbound_cardinality_zero_question, generate_source_lowerbound_cardinality_zero_question, generate_target_lowerbound_cardinality_one_question, generate_source_lowerbound_cardinality_one_question

##############Lowerbound Cardinality: 0 vs 1##############
###Lowerbound Cardinality: 0 vs 1 - Lowerbound 0 identified
def find_target_lowerbound_cardinality_zero(domain_model):
    associations = []
    for rel in domain_model.relationships:
        if domain_model.compare_relationship_type(rel.type.lower(), "association"):
            if rel.targetCardinality == "*" or "0.." in rel.targetCardinality:
                associations.append(rel)
    return associations


def find_source_lowerbound_cardinality_zero(domain_model):
    associations = []
    for rel in domain_model.relationships:
        if domain_model.compare_relationship_type(rel.type.lower(), "association") or \
            domain_model.compare_relationship_type(rel.type.lower(), "composition"):
            if rel.sourceCardinality == "*" or "0.." in rel.sourceCardinality:
                associations.append(rel)
    return associations

def find_target_lowerbound_cardinality_one(domain_model):
    associations = []
    for rel in domain_model.relationships:
        if domain_model.compare_relationship_type(rel.type.lower(), "association"):
            if rel.targetCardinality == "1" or "1.." in rel.targetCardinality:
                associations.append(rel)
    return associations

def find_source_lowerbound_cardinality_one(domain_model):
    associations = []
    for rel in domain_model.relationships:
        if domain_model.compare_relationship_type(rel.type.lower(), "association") or \
            domain_model.compare_relationship_type(rel.type.lower(), "composition"):
            if rel.sourceCardinality == "1" or "1.." in rel.sourceCardinality:
                associations.append(rel)
    return associations

class LowerboundCardinalityOneVsManyConfiguration(Configuration):
    def __init__(self, alternative_1=None, alternative_2=None, alternative_1_dm=None, alternative_2_dm=None,
                 question='', option_1='', option_2='', direction = ''):
        super().__init__(alternative_1, alternative_2, alternative_1_dm, alternative_2_dm, question, option_1, option_2)
        self.type = "lowerbound"
        self.direction = direction

    def update(self, cfg, domain_model, check_option):
        alt1 = cfg.alternative_1
        alt2 = cfg.alternative_2
        alt1_dm = cfg.alternative_1_dm
        alt2_dm = cfg.alternative_2_dm
        if (check_option == "Option 1" and cfg.option_1_dm) or \
            (check_option == "Option 2" and cfg.option_2_dm):
            ##do not update confidence to trigger upperbound templates.
            return None
        elif check_option == "Option 1" and not cfg.option_1_dm:
            print()
            #do not update confidence to trigger upperbound templates.
            #confidence for source or target?
            #if cfg.direction == 'source':
            #    rel_conf = [cfg.update_confidence_model_element(rel.sourceCardinality, high_confidence)
            #                for rel in alt1_dm.relationships]
            #elif cfg.direction == 'target':
            #    rel_conf = [cfg.update_confidence_model_element(rel.targetCardinality, high_confidence)
            #                for rel in alt1_dm.relationships]
            #else:
            #    rel_conf = [(cfg.update_confidence_model_element(rel.sourceCardinality, high_confidence),
            #                cfg.update_confidence_model_element(rel.targetCardinality, high_confidence))
            #                for rel in alt1_dm.relationships]
            domain_model.update_model_general(
                classes_to_remove=[],
                attributes_to_remove=[],  
                relationships_to_remove=alt2_dm.relationships,
                enumerations_to_remove=[],
                assoc_classes_to_remove=[],
                classes_to_add=[],
                attributes_to_add=[],
                relationships_to_add=alt1_dm.relationships,
                enumerations_to_add=[],
                assoc_classes_to_add=[],
                replacement_map={alt2_dm.relationships[0]:alt1_dm.relationships[0]},
            )
            return domain_model
        elif check_option == "Option 2" and not cfg.option_2_dm:
            print()
            #do not update confidence to trigger upperbound templates.
            #confidence for source or target?
            #if cfg.direction == 'source':
            #    rel_conf = [cfg.update_confidence_model_element(rel.sourceCardinality, high_confidence)
            #                for rel in alt2_dm.relationships]
            #elif cfg.direction == 'target':
            #    rel_conf = [cfg.update_confidence_model_element(rel.targetCardinality, high_confidence)
            #                for rel in alt2_dm.relationships]
            #else:
            #    rel_conf = [(cfg.update_confidence_model_element(rel.sourceCardinality, high_confidence),
            #                cfg.update_confidence_model_element(rel.targetCardinality, high_confidence))
            #                for rel in alt2_dm.relationships]
            domain_model.update_model_general(
                classes_to_remove=[],
                attributes_to_remove=[],  
                relationships_to_remove=alt1_dm.relationships,
                enumerations_to_remove=[],
                assoc_classes_to_remove=[],
                classes_to_add=[],
                attributes_to_add=[],
                relationships_to_add=alt2_dm.relationships,
                enumerations_to_add=[],
                assoc_classes_to_add=[],
                replacement_map={alt1_dm.relationships[0]: alt2_dm.relationships[0]},
            )
            return domain_model

    def set_confidence(self, configurations, alternative = True):
    #def confidence_configuration_cardinalities(configurations, alternative = True):
        for conf in configurations:
            alternative_1_score = None
            if hasattr(conf.alternative_1, '_metadata') and conf.alternative_1.get_metadata():
                #relationship confidence. Change for cardinality confidence. 
                # TODO add first cardinality confidence. Then relationship if not found
                if alternative or conf.option_1_dm:
                    alternative_1_score = conf.alternative_1.get_metadata().score
            alternative_2_score = None
            if hasattr(conf.alternative_2, '_metadata') and conf.alternative_2.get_metadata():
                #relationship confidence. Change for cardinality confidence.
                if alternative or conf.option_2_dm:
                    alternative_2_score = conf.alternative_2.get_metadata().score
            if conf.option_1_dm:
                conf.set_metadata('alternative_1', alternative_1_score, alternative_2_score)
            elif conf.option_2_dm:
                conf.set_metadata('alternative_2', alternative_1_score, alternative_2_score)
        return configurations

def find_lowerbound_zero_alternatives(lowerbound_zero_alternatives, lowerbound_one_alternatives,domain_model, question_generator_fn):
    alternatives = []
    no_alternatives = []
    direction = 'target' if 'target' in str(question_generator_fn) else 'source'
    for alt2 in lowerbound_one_alternatives:
        alt2_source = alt2.source
        alt2_target = alt2.target
        alt2_dm = UMLDomainModel()
        alt2_dm.add_class(alt2_source)
        alt2_dm.add_class(alt2_target)
        alt2_dm.add_relationship(alt2)
        #q, o1, o2 = generate_target_upperbound_cardinality_many_question(alt2)
        q, o1, o2 = question_generator_fn(alt2)
        #config = Configuration(alternative_2= alt2, alternative_2_dm = alt2_dm, question = q, option_1 = o1, option_2 = o2)
        config = LowerboundCardinalityOneVsManyConfiguration(alternative_2= alt2, alternative_2_dm = alt2_dm, question = q, option_1 = o1, option_2 = o2, direction = direction)
        config.option_2_dm = domain_model
        alt1_found = None
        for alt1 in lowerbound_zero_alternatives:
            alt1_source = alt1.source
            alt1_target = alt1.target
            is_alternative = is_similar(alt1_source.name, alt2_source.name) and \
                                is_similar(alt1_target.name, alt2_target.name) 
            if not is_alternative:
                is_alternative = is_similar(alt1_source.name, alt2_target.name) and \
                                    is_similar(alt1_target.name, alt2_source.name) 
            if is_alternative:
                alt_1_dm = UMLDomainModel()
                #Relationship type is another question
                alt1_relationship = copy.deepcopy(alt1)
                alt1_relationship.type = alt2.type
                #lowerbound cardinality is another question
                #t = alt1.targetCardinality
                if is_similar(alt2_source.name, alt1_relationship.source.name):
                    if direction == 'source':
                        alt1_relationship.sourceCardinality = f'{alt1_relationship.sourceCardinality}..{alt2.sourceCardinality[-1]}'
                    elif direction == 'target':
                        alt1_relationship.targetCardinality = f'{alt1_relationship.targetCardinality}..{alt2.targetCardinality[-1]}'
                elif is_similar(alt2_target.name, alt1_relationship.source.name):
                    if direction == 'source':
                        alt1_relationship.sourceCardinality = f'{alt1_relationship.sourceCardinality}..{alt2.targetCardinality[-1]}'
                    elif direction == 'target':
                        alt1_relationship.targetCardinality = f'{alt1_relationship.targetCardinality}..{alt2.sourceCardinality[-1]}'
                alt1_relationship.sourceCardinality = "0..1" if alt1_relationship.sourceCardinality == "*..1" else alt1_relationship.sourceCardinality 
                alt1_relationship.targetCardinality = "0..1" if alt1_relationship.targetCardinality == "*..1" else alt1_relationship.targetCardinality 
                alt1_relationship.sourceCardinality = "*" if alt1_relationship.sourceCardinality == "*..*" else alt1_relationship.sourceCardinality 
                alt1_relationship.targetCardinality = "*" if alt1_relationship.targetCardinality == "*..*" else alt1_relationship.targetCardinality 
                #r = alt1_relationship.targetCardinality
                alt_1_dm.add_class(alt1_source)
                alt_1_dm.add_class(alt1_target)
                alt_1_dm.add_relationship(alt1_relationship)
                config.add_alternative_1(alternative_1 = alt1, alternative_1_dm = alt_1_dm)
                alt1_found = alt1
                
                alternatives.append(config)
                break
        if not alt1_found:
            alt_1_dm = UMLDomainModel()
            alt1_relationship = copy.deepcopy(alt2)
            if direction == 'source':
                alt1_relationship.sourceCardinality = '0'
            else:
                alt1_relationship.targetCardinality = '0'
            alt1_source = alt1_relationship.source
            alt1_target = alt1_relationship.target
            #lowerbound cardinality is another question
            #t = alt1.targetCardinality
            if is_similar(alt2_source.name, alt1_relationship.source.name):
                if direction == 'source':
                    alt1_relationship.sourceCardinality = f'{alt1_relationship.sourceCardinality}..{alt2.sourceCardinality[-1]}'
                elif direction == 'target':
                    alt1_relationship.targetCardinality = f'{alt1_relationship.targetCardinality}..{alt2.targetCardinality[-1]}'
            elif is_similar(alt2_target.name, alt1_relationship.source.name):
                if direction == 'source':
                    alt1_relationship.sourceCardinality = f'{alt1_relationship.sourceCardinality}..{alt2.targetCardinality[-1]}'
                elif direction == 'target':
                    alt1_relationship.targetCardinality = f'{alt1_relationship.targetCardinality}..{alt2.sourceCardinality[-1]}'
            alt1_relationship.sourceCardinality = "0..1" if alt1_relationship.sourceCardinality == "*..1" else alt1_relationship.sourceCardinality 
            alt1_relationship.targetCardinality = "0..1" if alt1_relationship.targetCardinality == "*..1" else alt1_relationship.targetCardinality 
            alt1_relationship.sourceCardinality = "*" if alt1_relationship.sourceCardinality == "*..*" else alt1_relationship.sourceCardinality 
            alt1_relationship.targetCardinality = "*" if alt1_relationship.targetCardinality == "*..*" else alt1_relationship.targetCardinality 
            #r = alt1_relationship.targetCardinality
            alt_1_dm.add_class(alt1_source)
            alt_1_dm.add_class(alt1_target)
            alt_1_dm.add_relationship(alt1_relationship)
            alt1 = alt1_relationship
            config.add_alternative_1(alternative_1 = alt1, alternative_1_dm = alt_1_dm)
            no_alternatives.append(config)
    return alternatives, no_alternatives

def find_lowerbound_one_alternatives(lowerbound_zero_alternatives, lowerbound_one_alternatives, domain_model, question_generator_fn):
    alternatives = []
    no_alternatives = []
    direction = 'target' if 'target' in str(question_generator_fn) else 'source'
    for alt1 in lowerbound_zero_alternatives:
        alt1_source = alt1.source
        alt1_target = alt1.target
        alt_1_dm = UMLDomainModel()
        alt_1_dm.add_class(alt1_source)
        alt_1_dm.add_class(alt1_target)
        alt_1_dm.add_relationship(alt1)
        #q, o1, o2 = generate_target_lowerbound_cardinality_many_question(alt1)
        q, o1, o2 = question_generator_fn(alt1)
        #config = Configuration(alternative_1= alt1, alternative_1_dm = alt_1_dm, question = q, option_1 = o1, option_2 = o2)
        config = LowerboundCardinalityOneVsManyConfiguration(alternative_1= alt1, alternative_1_dm = alt_1_dm, question = q, option_1 = o1, option_2 = o2, direction = direction)
        config.option_1_dm = domain_model
        alt2_found = None
        for alt2 in lowerbound_one_alternatives:
            alt2_source = alt2.source
            alt2_target = alt2.target
            is_alternative = is_similar(alt1_source.name, alt2_source.name) and \
                                is_similar(alt1_target.name, alt2_target.name) 
            if not is_alternative:
                is_alternative = is_similar(alt1_source.name, alt2_target.name) and \
                                    is_similar(alt1_target.name, alt2_source.name) 
            if is_alternative:
                alt2_dm = UMLDomainModel()
                #Relationship type is another question
                alt2_relationship = copy.deepcopy(alt2)
                alt2_relationship.type = alt1.type
                #lowerbound cardinality is another question
                #t = alt1.sourceCardinality
                if is_similar(alt1_source.name, alt2_relationship.source.name):
                    if direction == 'source':
                        alt2_relationship.sourceCardinality = f'{alt2_relationship.sourceCardinality}..{alt1.sourceCardinality[-1]}'
                    elif direction == 'target':
                        alt2_relationship.targetCardinality = f'{alt2_relationship.targetCardinality}..{alt1.targetCardinality[-1]}'
                elif is_similar(alt1_target.name, alt2_relationship.source.name):
                    if direction == 'source':
                        alt2_relationship.sourceCardinality = f'{alt2_relationship.sourceCardinality}..{alt1.targetCardinality[-1]}'
                    elif direction == 'target':
                        alt2_relationship.targetCardinality = f'{alt2_relationship.targetCardinality}..{alt1.sourceCardinality[-1]}'
                alt2_relationship.sourceCardinality = "1" if alt2_relationship.sourceCardinality == "1..1" else alt2_relationship.sourceCardinality 
                alt2_relationship.targetCardinality = "1" if alt2_relationship.targetCardinality == "1..1" else alt2_relationship.targetCardinality 
                alt2_relationship.sourceCardinality = "*" if alt2_relationship.sourceCardinality == "*..*" else alt2_relationship.sourceCardinality 
                alt2_relationship.targetCardinality = "*" if alt2_relationship.targetCardinality == "*..*" else alt2_relationship.targetCardinality 
                #r = alt2_relationship.sourceCardinality
                alt2_dm.add_class(alt2_source)
                alt2_dm.add_class(alt2_target)
                alt2_dm.add_relationship(alt2_relationship)
                config.add_alternative_2(alternative_2 = alt2, alternative_2_dm = alt2_dm)
                alt2_found = alt2

                alternatives.append(config)
                break
        if not alt2_found:
            alt2_dm = UMLDomainModel()
            alt2_relationship = copy.deepcopy(alt1)
            if direction == 'source':
                alt2_relationship.sourceCardinality = '1'
            else:
                alt2_relationship.targetCardinality = '1'
            alt2_source = alt2_relationship.source
            alt2_target = alt2_relationship.target
            #lowerbound cardinality is another question
            #t = alt1.sourceCardinality
            if is_similar(alt1_source.name, alt2_relationship.source.name):
                if direction == 'source':
                    alt2_relationship.sourceCardinality = f'{alt2_relationship.sourceCardinality}..{alt1.sourceCardinality[-1]}'
                elif direction == 'target':
                    alt2_relationship.targetCardinality = f'{alt2_relationship.targetCardinality}..{alt1.targetCardinality[-1]}'
            elif is_similar(alt1_target.name, alt2_relationship.source.name):
                if direction == 'source':
                    alt2_relationship.sourceCardinality = f'{alt2_relationship.sourceCardinality}..{alt1.targetCardinality[-1]}'
                elif direction == 'target':
                    alt2_relationship.targetCardinality = f'{alt2_relationship.targetCardinality}..{alt1.sourceCardinality[-1]}'
            alt2_relationship.sourceCardinality = "1" if alt2_relationship.sourceCardinality == "1..1" else alt2_relationship.sourceCardinality 
            alt2_relationship.targetCardinality = "1" if alt2_relationship.targetCardinality == "1..1" else alt2_relationship.targetCardinality 
            alt2_relationship.sourceCardinality = "*" if alt2_relationship.sourceCardinality == "*..*" else alt2_relationship.sourceCardinality 
            alt2_relationship.targetCardinality = "*" if alt2_relationship.targetCardinality == "*..*" else alt2_relationship.targetCardinality 
            #r = alt2_relationship.sourceCardinality
            alt2_dm.add_class(alt2_source)
            alt2_dm.add_class(alt2_target)
            alt2_dm.add_relationship(alt2_relationship)
            alt2 = alt2_relationship
            config.add_alternative_2(alternative_2 = alt2, alternative_2_dm = alt2_dm)
            no_alternatives.append(config)            
    return alternatives, no_alternatives

def setup_lowerbound_cardinality_zero_vs_one_patterns(domain_model, domain_model_alternatives):
    configurations = []

    target_lowerbound_cardinality_one_dm = find_target_lowerbound_cardinality_one(domain_model)
    target_lowerbound_cardinality_zero_dm = find_target_lowerbound_cardinality_zero(domain_model)

    target_lowerbound_cardinality_one_alternatives = find_target_lowerbound_cardinality_one(domain_model_alternatives)
    target_lowerbound_cardinality_zero_alternatives = find_target_lowerbound_cardinality_zero(domain_model_alternatives)

    target_zero_conf_alt, target_zero_conf_no_alt = find_lowerbound_zero_alternatives(target_lowerbound_cardinality_zero_alternatives, target_lowerbound_cardinality_one_dm, domain_model, question_generator_fn=generate_target_lowerbound_cardinality_zero_question)
    target_one_conf_alt, target_one_conf_no_alt = find_lowerbound_one_alternatives(target_lowerbound_cardinality_zero_dm, target_lowerbound_cardinality_one_alternatives, domain_model, question_generator_fn=generate_target_lowerbound_cardinality_one_question)

    #configurations, selected_configurations += target_one_alternatives + target_many_alternatives

    source_lowerbound_cardinality_one_dm = find_source_lowerbound_cardinality_one(domain_model)
    source_lowerbound_cardinality_zero_dm = find_source_lowerbound_cardinality_zero(domain_model)

    source_lowerbound_cardinality_one_alternatives = find_source_lowerbound_cardinality_one(domain_model_alternatives)
    source_lowerbound_cardinality_zero_alternatives = find_source_lowerbound_cardinality_zero(domain_model_alternatives)

    source_zero_conf_alt, source_zero_conf_no_alt = find_lowerbound_zero_alternatives(source_lowerbound_cardinality_zero_alternatives, source_lowerbound_cardinality_one_dm, domain_model, question_generator_fn=generate_source_lowerbound_cardinality_zero_question)
    source_one_conf_alt, source_one_conf_no_alt = find_lowerbound_one_alternatives(source_lowerbound_cardinality_zero_dm, source_lowerbound_cardinality_one_alternatives, domain_model, question_generator_fn=generate_source_lowerbound_cardinality_one_question)

    configurations_alt = []
    configurations_no_alt = []

    configurations_alt += target_zero_conf_alt + target_one_conf_alt
    configurations_alt += source_zero_conf_alt + source_one_conf_alt
    configurations_no_alt += target_zero_conf_no_alt + target_one_conf_no_alt
    configurations_no_alt += source_zero_conf_no_alt + source_one_conf_no_alt

    return configurations_alt, configurations_no_alt