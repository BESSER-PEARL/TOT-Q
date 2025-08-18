import copy
from tree_of_thought.model_elements import UMLClass, UMLAttribute, UMLEnumeration, Visibility, UMLRelationship, UMLDomainModel, UMLAssociationClass
from configuration import Configuration
from configuration import split_camel_case, correct_article, plural, name_format, is_similar
from configuration import high_confidence, low_confidence
from collections import Counter
from template_questions import generate_association_question


##############Composition vs Association##############
###Composition vs Association - Association identified
def find_associations_with_has_or_part(domain_model):
    associations = []
    for rel in domain_model.relationships:
        if "has" in rel.name.lower() or "part" in rel.name.lower():
            associations.append(rel)
        #if "association" in rel.type.lower():
        #    associations.append(rel)
    return associations


def find_compositions(domain_model):
    compositions = []
    for rel in domain_model.relationships:
        if domain_model.compare_relationship_type(rel.type, 'composition'):
            compositions.append(rel)
    return compositions

class CompositionVsAssociationConfiguration(Configuration):
    def update(self, cfg, domain_model, check_option):
        alt1 = cfg.alternative_1
        alt2 = cfg.alternative_2
        alt1_dm = cfg.alternative_1_dm
        alt2_dm = cfg.alternative_2_dm
        if (check_option == "Option 1" and cfg.option_1_dm) or \
            (check_option == "Option 2" and cfg.option_2_dm):
            if check_option == "Option 1":
                rel_to_update = [domain_model.get_relationship(r.source.name, r.target.name, r.type, r.name )for r in alt1_dm.relationships]
                rel_conf = [(cfg.update_confidence_model_element(rel, high_confidence),
                            cfg.update_confidence_model_element(rel.sourceCardinality, high_confidence))
                                for rel in rel_to_update]
            else:
                rel_to_update = [domain_model.get_relationship(r.source.name, r.target.name, r.type, r.name )for r in alt2_dm.relationships]
                rel_conf = [cfg.update_confidence_model_element(rel, high_confidence)
                            for rel in rel_to_update]
                #remove duplicated relationship
                rel_to_remove = [domain_model.get_relationship_ignore_name(r.source.name, r.target.name, r.type )for r in alt2_dm.relationships]
                domain_model.update_model_general(
                    classes_to_remove=[],
                    attributes_to_remove=[],  
                    relationships_to_remove=rel_to_remove,
                    enumerations_to_remove=[],
                    assoc_classes_to_remove=[],
                    classes_to_add=[],
                    attributes_to_add=[],
                    relationships_to_add=[],
                    enumerations_to_add=[],
                    assoc_classes_to_add=[],
                    replacement_map={},
                )
            return None
        elif check_option == "Option 1" and not cfg.option_1_dm:
            #remove duplicated relationship
            rel_to_remove = [domain_model.get_relationship_ignore_name(r.source.name, r.target.name, r.type )for r in alt1_dm.relationships]
            domain_model.update_model_general(
                classes_to_remove=[],
                attributes_to_remove=[],  
                relationships_to_remove=rel_to_remove,
                enumerations_to_remove=[],
                assoc_classes_to_remove=[],
                classes_to_add=[],
                attributes_to_add=[],
                relationships_to_add=[],
                enumerations_to_add=[],
                assoc_classes_to_add=[],
                replacement_map={},
            )
            #update confidence
            rel_conf = [(cfg.update_confidence_model_element(rel, high_confidence), 
                        cfg.update_confidence_model_element(rel.sourceCardinality, high_confidence),
                        cfg.update_confidence_model_element(rel.targetCardinality, low_confidence))
                        for rel in alt1_dm.relationships]
            #update association to composition
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
            #update conf
            #cls_conf = [cfg.update_confidence_model_element(cls, high_confidence) for cls in alt2[1:]]
            #rel_conf = [(cfg.update_confidence_model_element(rel, high_confidence), 
            #            cfg.update_confidence_model_element(rel.sourceCardinality, low_confidence),
            #            cfg.update_confidence_model_element(rel.targetCardinality, low_confidence))
            #            for rel in alt2_dm.relationships]
            print('Not required')
            return domain_model

    def set_confidence(self, configurations, alternative = True):
    #def confidence_configuration_relationships(configurations, alternative = True):
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


def find_compositions_alternatives(compositions_alternatives, associations_alternatives, domain_model):   
    alternatives = []
    no_alternatives = []
    for alt2 in associations_alternatives:
        alt2_source = alt2.source
        alt2_target = alt2.target
        alt2_dm = UMLDomainModel()
        alt2_dm.add_class(alt2_source)
        alt2_dm.add_class(alt2_target)
        alt2_dm.add_relationship(alt2)
        q, o1, o2 = generate_association_question(alt2)
        #config = Configuration(alternative_2= alt2, alternative_2_dm = alt2_dm, question = q, option_1 = o1, option_2 = o2)
        config = CompositionVsAssociationConfiguration(alternative_2= alt2, alternative_2_dm = alt2_dm, question = q, option_1 = o1, option_2 = o2)
        config.option_2_dm = domain_model
        alt1_found = None
        for alt1 in compositions_alternatives:
            alt1_source = alt1.source
            alt1_target = alt1.target
            is_alternative = is_similar(alt1_source.name, alt2_source.name) and \
                                is_similar(alt1_target.name, alt2_target.name) 
            if not is_alternative:
                is_alternative = is_similar(alt1_source.name, alt2_target.name) and \
                                    is_similar(alt1_target.name, alt2_source.name) 
            if is_alternative:
                alt_1_dm = UMLDomainModel()
                alt_1_dm.add_class(alt1_source)
                alt_1_dm.add_class(alt1_target)
                #Cardinality is another question
                alt1_relationship = copy.deepcopy(alt1)
                alt1_relationship.sourceCardinality = "1"
                if is_similar(alt1_source.name, alt2_source.name):
                    alt1_relationship.targetCardinality = alt2.targetCardinality
                else: 
                    alt1_relationship.targetCardinality = alt2.sourceCardinality                
                alt_1_dm.add_relationship(alt1_relationship)
                config.add_alternative_1(alternative_1 = alt1, alternative_1_dm = alt_1_dm)
                alt1_found = alt1
                alternatives.append(config)
                break
        if not alt1_found:
            alt_1_dm = UMLDomainModel()
            alt2_source = copy.deepcopy(alt2.source)
            alt2_target = copy.deepcopy(alt2.target)
            new_relationship = UMLRelationship(alt2_source, alt2_target, 'Composition', alt2.name, '1', alt2.targetCardinality)
            alt_1_dm.add_class(alt2_source)
            alt_1_dm.add_class(alt2_target)
            alt_1_dm.add_relationship(new_relationship)
            alt1 = new_relationship
            config.add_alternative_1(alternative_1 = alt1, alternative_1_dm = alt_1_dm)
            no_alternatives.append(config)
        
    return alternatives, no_alternatives

def setup_composition_vs_association_patterns(domain_model, domain_model_alternatives):
    #compositions_dm = find_compositions(domain_model)
    associations_dm = find_associations_with_has_or_part(domain_model)
    
    compositions_alternatives = find_compositions(domain_model_alternatives)    
    #associations_alternatives = find_associations_with_has_or_part(domain_model_alternatives)   
    
    compositions_conf_alt, compositions_conf_no_alt = find_compositions_alternatives(compositions_alternatives, associations_dm, domain_model)
    #associations_conf_alt, associations_conf_no_alt = find_associations_alternatives(compositions_dm, associations_alternatives, domain_model)
    
    #alternatives in same model
    compositions_conf_alt, compositions_conf_no_alt = find_compositions_alternatives(compositions_alternatives, associations_dm, domain_model)

    configurations_alt = compositions_conf_alt #+ associations_conf_alt
    configurations_no_alt = compositions_conf_no_alt #+ associations_conf_no_alt
    return configurations_alt, configurations_no_alt
