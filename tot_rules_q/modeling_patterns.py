import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from typing import Callable, List, Tuple
import copy
from tree_of_thought.model_elements import UMLClass, UMLAttribute, UMLEnumeration, Visibility, UMLRelationship, UMLDomainModel, UMLAssociationClass
import logging
from os.path import exists, dirname, join
#from configuration import Configuration
#from configuration import split_camel_case, correct_article, plural, name_format, is_similar
from configuration import high_confidence, low_confidence, confidence_threshold
from class_vs_attribute_pattern import setup_class_vs_attribute_patterns
from enumeration_vs_inheritance_pattern import setup_enumeration_vs_inheritance_patterns
from attribute_vs_inheritance_pattern import setup_attribute_vs_inheritance_patterns
from concrete_vs_abstract_class_pattern import setup_concrete_vs_abstract_class_patterns
from composition_vs_assocation_pattern import setup_composition_vs_association_patterns
from lowerbound_card_zero_one_pattern import setup_lowerbound_cardinality_zero_vs_one_patterns
from upperbound_card_one_many_pattern import setup_upperbound_cardinality_one_vs_many_patterns
from association_class_vs_class_pattern import setup_association_class_vs_class_patterns

logger = logging.getLogger(__name__)
base_folder = dirname(dirname(__file__))
log_folder = join(base_folder, 'logs/')
configurations = []

def confidence_configuration_class_vs_attribute(configurations, alternative = True):
    for conf in configurations:
        alternative_1_score = None
        if hasattr(conf.alternative_1[0], '_metadata') and conf.alternative_1[0].get_metadata():
            if alternative or conf.option_1_dm:
                alternative_1_score = conf.alternative_1[0].get_metadata().score
        alternative_2_score = None
        if hasattr(conf.alternative_2[1], '_metadata') and conf.alternative_2[1].get_metadata():
            #Attribute score exists
            if alternative or conf.option_2_dm:
                alternative_2_score = conf.alternative_2[1].get_metadata().score
        elif hasattr(conf.alternative_2[0], '_metadata') and conf.alternative_2[0].get_metadata():
            #Attribute score do not exists
            if alternative or conf.option_2_dm:
                alternative_2_score = conf.alternative_2[0].get_metadata().score
        if conf.option_1_dm:
            conf.set_metadata('alternative_1', alternative_1_score, alternative_2_score)
        elif conf.option_2_dm:
            conf.set_metadata('alternative_2', alternative_1_score, alternative_2_score)
    return configurations

def confidence_configuration_enumeration_vs_inheritance(configurations, alternative = True):
    for conf in configurations:
        alternative_1_score = None
        #subclasses is a list
        if hasattr(conf.alternative_1[1][0], '_metadata') and conf.alternative_1[1][0].get_metadata():
            if alternative or conf.option_1_dm:
                subclass_scores = [c.get_metadata().score for c in conf.alternative_1[1]]
                alternative_1_score = min(subclass_scores)
        alternative_2_score = None
        if hasattr(conf.alternative_2[1], '_metadata') and conf.alternative_2[1].get_metadata():
            if alternative or conf.option_2_dm:
                alternative_2_score = conf.alternative_2[1].get_metadata().score
        if conf.option_1_dm:
            conf.set_metadata('alternative_1', alternative_1_score, alternative_2_score)
        elif conf.option_2_dm:
            conf.set_metadata('alternative_2', alternative_1_score, alternative_2_score)
    return configurations

def confidence_configuration_attribute_vs_inheritance(configurations, alternative = True):
    for conf in configurations:
        alternative_1_score = None
        #subclasses is a list
        if hasattr(conf.alternative_1[1][0], '_metadata') and conf.alternative_1[1][0].get_metadata():
            if alternative or conf.option_1_dm:
                subclass_scores = [c.get_metadata().score for c in conf.alternative_1[1]]
                alternative_1_score = min(subclass_scores)
        alternative_2_score = None
        if hasattr(conf.alternative_2[1], '_metadata') and conf.alternative_2[1].get_metadata():
            #Attribute score exists
            if alternative or conf.option_2_dm:
                alternative_2_score = conf.alternative_2[1].get_metadata().score
        elif hasattr(conf.alternative_2[0], '_metadata') and conf.alternative_2[0].get_metadata():
            #Attribute score do not exists
            if alternative or conf.option_2_dm:
                alternative_2_score = conf.alternative_2[0].get_metadata().score
        if conf.option_1_dm:
            conf.set_metadata('alternative_1', alternative_1_score, alternative_2_score)
        elif conf.option_2_dm:
            conf.set_metadata('alternative_2', alternative_1_score, alternative_2_score)
    return configurations

def filter_configurations(configurations):
    sorted_configurations = sorted(configurations, key=lambda conf: conf.get_metadata().order_score)
    check_sorted_configurations = [(c.get_metadata().get_order_score(), c.get_metadata().get_alternative_1_score(), c.get_metadata().get_alternative_2_score(), c) for c in sorted_configurations]
    #review scores that are not in correct scale
    below_threshold_configurations = [c for c in check_sorted_configurations if c[0] <= confidence_threshold]
    above_threshold_configurations = [c for c in check_sorted_configurations if c[0] > confidence_threshold]
    high_confidence_configurations = [c for c in above_threshold_configurations if (c[1] and c[1] >= confidence_threshold) and (c[2] and c[2] >= confidence_threshold)]

    selected_configurations = below_threshold_configurations + high_confidence_configurations
    return selected_configurations

def get_configuration_class_enum(domain_model, domain_model2):
    configurations = []
    configurations_alt = []
    configurations_no_alt = []
    conf_alt, conf_no_alt = setup_class_vs_attribute_patterns(domain_model, domain_model2)
    conf_alt = confidence_configuration_class_vs_attribute(conf_alt)
    conf_no_alt = confidence_configuration_class_vs_attribute(conf_no_alt, alternative = False)
    configurations_alt += conf_alt
    configurations_no_alt += conf_no_alt

    conf_alt, conf_no_alt = setup_enumeration_vs_inheritance_patterns(domain_model, domain_model2)
    conf_alt = confidence_configuration_enumeration_vs_inheritance(conf_alt)
    conf_no_alt = confidence_configuration_enumeration_vs_inheritance(conf_no_alt, alternative = False)
    configurations_alt += conf_alt
    configurations_no_alt += conf_no_alt
    
    conf_alt, conf_no_alt = setup_attribute_vs_inheritance_patterns(domain_model, domain_model2)
    conf_alt = confidence_configuration_attribute_vs_inheritance(conf_alt)
    conf_no_alt = confidence_configuration_attribute_vs_inheritance(conf_no_alt, alternative = False)
    configurations_alt += conf_alt
    configurations_no_alt += conf_no_alt
    
    configurations = configurations_alt + configurations_no_alt
    selected_configurations = filter_configurations(configurations)

    return configurations, selected_configurations

#Cardinality question before association class.
def confidence_configuration_abstract_class(configurations, alternative = True):
    for conf in configurations:
        alternative_1_score = None
        if hasattr(conf.alternative_1[0], '_metadata') and conf.alternative_1[0].get_metadata():
            if alternative or conf.option_1_dm:
                alternative_1_score = conf.alternative_1[0].get_metadata().score
        alternative_2_score = None
        if hasattr(conf.alternative_2[0], '_metadata') and conf.alternative_2[0].get_metadata():
            if alternative or conf.option_2_dm:
                alternative_2_score = conf.alternative_2[0].get_metadata().score
        if conf.option_1_dm:
            conf.set_metadata('alternative_1', alternative_1_score, alternative_2_score)
        elif conf.option_2_dm:
            conf.set_metadata('alternative_2', alternative_1_score, alternative_2_score)
    return configurations

def get_configuration_abstract_class(domain_model, domain_model2):
    configurations = []
    configurations_alt = []
    configurations_no_alt = []
    conf_alt, conf_no_alt = setup_concrete_vs_abstract_class_patterns(domain_model, domain_model2)
    conf_alt = confidence_configuration_abstract_class(conf_alt)
    conf_no_alt = confidence_configuration_abstract_class(conf_no_alt, alternative = False)
    configurations_alt += conf_alt
    configurations_no_alt += conf_no_alt
    
    configurations = configurations_alt + configurations_no_alt
    selected_configurations = filter_configurations(configurations)
    return configurations, selected_configurations

def confidence_configuration_relationships(configurations, alternative = True):
    for conf in configurations:
        alternative_1_score = None
        if hasattr(conf.alternative_1, '_metadata') and conf.alternative_1.get_metadata():
            if alternative or conf.option_1_dm:
                alternative_1_score = conf.alternative_1.get_metadata().score
        alternative_2_score = None
        if hasattr(conf.alternative_2, '_metadata') and conf.alternative_2.get_metadata():
            if alternative or conf.option_2_dm:
                alternative_2_score = conf.alternative_2.get_metadata().score
        if conf.option_1_dm:
            conf.set_metadata('alternative_1', alternative_1_score, alternative_2_score)
        elif conf.option_2_dm:
            conf.set_metadata('alternative_2', alternative_1_score, alternative_2_score)
    return configurations

def get_configuration_relationships(domain_model, domain_model2):
    configurations = []
    configurations_alt = []
    configurations_no_alt = []
    conf_alt, conf_no_alt = setup_composition_vs_association_patterns(domain_model, domain_model2)
    conf_alt = confidence_configuration_relationships(conf_alt)
    conf_no_alt = confidence_configuration_relationships(conf_no_alt, alternative = False)
    configurations_alt += conf_alt
    configurations_no_alt += conf_no_alt
    
    configurations = configurations_alt + configurations_no_alt
    selected_configurations = filter_configurations(configurations)
    return configurations, selected_configurations

def confidence_configuration_association_class(configurations, alternative = True):
    for conf in configurations:
        alternative_1_score = None
        if hasattr(conf.alternative_1, '_metadata') and conf.alternative_1.get_metadata():
            #alternative 1 do not exits in all configurations
            if alternative or conf.option_1_dm:
                alternative_1_score = conf.alternative_1[1].get_metadata().score
        alternative_2_score = None
        if hasattr(conf.alternative_2[1], '_metadata') and conf.alternative_2[1].get_metadata():
            if alternative or conf.option_2_dm:
                alternative_2_score = conf.alternative_2[1].get_metadata().score
        if conf.option_1_dm:
            conf.set_metadata('alternative_1', alternative_1_score, alternative_2_score)
        elif conf.option_2_dm:
            conf.set_metadata('alternative_2', alternative_1_score, alternative_2_score)
    return configurations

def get_configuration_association_class(domain_model, domain_model2):
    configurations = []
    configurations_alt = []
    configurations_no_alt = []
    conf_alt, conf_no_alt = setup_association_class_vs_class_patterns(domain_model, domain_model2)
    conf_alt = confidence_configuration_association_class(conf_alt)
    conf_no_alt = confidence_configuration_association_class(conf_no_alt, alternative = False)
    configurations_alt += conf_alt
    configurations_no_alt += conf_no_alt
    
    configurations = configurations_alt + configurations_no_alt
    #selected_configurations = filter_configurations(configurations)
    selected_configurations = configurations
    return configurations, selected_configurations

def confidence_configuration_cardinalities(configurations, alternative = True):
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

def get_configuration_lowerbound_cardinalities(domain_model, domain_model2):
    configurations = []
    configurations_alt = []
    configurations_no_alt = []
    conf_alt, conf_no_alt = setup_lowerbound_cardinality_zero_vs_one_patterns(domain_model, domain_model2)
    conf_alt = confidence_configuration_cardinalities(conf_alt)
    conf_no_alt = confidence_configuration_cardinalities(conf_no_alt, alternative = False)
    configurations_alt += conf_alt
    configurations_no_alt += conf_no_alt
    
    configurations = configurations_alt + configurations_no_alt
    selected_configurations = filter_configurations(configurations)
    return configurations, selected_configurations

def get_configuration_upperbound_cardinalities(domain_model, domain_model2):
    configurations = []
    configurations_alt = []
    configurations_no_alt = []
    conf_alt, conf_no_alt = setup_upperbound_cardinality_one_vs_many_patterns(domain_model, domain_model2)
    conf_alt = confidence_configuration_cardinalities(conf_alt)
    conf_no_alt = confidence_configuration_cardinalities(conf_no_alt, alternative = False)
    configurations_alt += conf_alt
    configurations_no_alt += conf_no_alt
    
    configurations = configurations_alt + configurations_no_alt
    selected_configurations = filter_configurations(configurations)
    return configurations, selected_configurations