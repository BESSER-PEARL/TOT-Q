import copy
from tree_of_thought.model_elements import UMLClass, UMLAttribute, UMLEnumeration, Visibility, UMLRelationship, UMLDomainModel, UMLAssociationClass
from configuration import Configuration
from configuration import split_camel_case, correct_article, plural, name_format, is_similar
from configuration import high_confidence, low_confidence
from collections import Counter
from template_questions import generate_class_with_single_association_question, generate_attribute_question


##############Class vs Attribute ##############
###Class vs Attribute - Class identified
def find_class_with_single_association(domain_model: UMLDomainModel):
    association_count = {cls.name: 0 for cls in domain_model.classes}
    association_objects = {cls.name: [] for cls in domain_model.classes}
    for rel in domain_model.relationships:
        #if rel.type.lower() == "association":
        if domain_model.compare_relationship_type(rel.type.lower(), "association") or \
            domain_model.compare_relationship_type(rel.type.lower(), "composition"):
            association_count[rel.source.name] += 1
            association_count[rel.target.name] += 1
            association_objects[rel.source.name].append(rel)
            association_objects[rel.target.name].append(rel)
    association_count = {cl: cnt for cl, cnt in association_count.items() if cnt != 0}
    for rel in domain_model.relationships:
        if domain_model.compare_relationship_type(rel.type.lower(), "inheritance"):
            if rel.source.name in association_count:
                association_count[rel.source.name] += 1
            if rel.target.name in association_count:    
                association_count[rel.target.name] += 1
    classes_with_single_association = [(domain_model.get_class(name), association_objects[name][0]) for name, count in association_count.items() if count == 1]
    return classes_with_single_association

###Class vs Attribute - attributes identified
def find_attributes(domain_model: UMLDomainModel):
    enum_list = [e.name.lower() for e in domain_model.enumerations]
    attr_list = [(c, at) for c in domain_model.classes for at in c.attributes if \
                 not (at.name.lower() in enum_list or at.type.lower() in enum_list or 'bool' in at.type.lower())]
    return attr_list


class ClassVsAttributeConfiguration(Configuration):
    def update(self, cfg, domain_model, check_option):
        alt1 = cfg.alternative_1
        alt2 = cfg.alternative_2
        alt1_dm = cfg.alternative_1_dm
        alt2_dm = cfg.alternative_2_dm
        if (check_option == "Option 1" and cfg.option_1_dm) or \
            (check_option == "Option 2" and cfg.option_2_dm):
            if check_option == "Option 1":
                cfg.update_confidence_model_element(domain_model.get_class(alt1_dm.classes[1].name), high_confidence)
            else:
                att_to_update = domain_model.get_class(alt2[0].name).get_attribute(alt2[1].name)
                cfg.update_confidence_model_element(att_to_update, high_confidence)
            return None
        elif check_option == "Option 1" and not cfg.option_1_dm:
            #update confidences
            cfg.update_confidence_model_element(alt1_dm.classes[1], high_confidence)
            rel_conf = [(cfg.update_confidence_model_element(rel, low_confidence), 
                        cfg.update_confidence_model_element(rel.sourceCardinality, low_confidence),
                        cfg.update_confidence_model_element(rel.targetCardinality, low_confidence))
                        for rel in alt1_dm.relationships]
            domain_model.update_model_general(
                classes_to_remove=alt2_dm.classes,
                attributes_to_remove=[(alt2[0],alt2[1])],  
                relationships_to_remove=[],
                enumerations_to_remove=[],
                assoc_classes_to_remove=[],
                classes_to_add=alt1_dm.classes,
                attributes_to_add=[],
                relationships_to_add=alt1_dm.relationships,
                enumerations_to_add=[],
                assoc_classes_to_add=[],
                replacement_map={alt2_dm.classes[0]: alt1_dm.classes[0]},
            )
            return domain_model
        elif check_option == "Option 2" and not cfg.option_2_dm:
            #update confidences
            cls_rep = alt1_dm.classes[0] if alt1_dm.classes[0].name == alt2_dm.classes[0].name else alt1_dm.classes[1]
            cfg.update_confidence_model_element(alt2[1], high_confidence)
            domain_model.update_model_general(
                classes_to_remove=[alt1[0]],
                attributes_to_remove=[],  
                relationships_to_remove=alt1_dm.relationships,
                enumerations_to_remove=[],
                assoc_classes_to_remove=[],
                classes_to_add=alt2_dm.classes,
                attributes_to_add=[(alt2[0],alt2[1])],
                relationships_to_add=[],
                enumerations_to_add=[],
                assoc_classes_to_add=[],
                #replacement_map={alt1_dm.classes[0]: alt2_dm.classes[0]},
                replacement_map={cls_rep: alt2_dm.classes[0]},
            )
            return domain_model
        
    def set_confidence(self, configurations, alternative = True):
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


def find_class_alternatives(class_alternatives, attributes_alternatives, domain_model):
    alternatives = []
    no_alternatives = []
    for alt2 in attributes_alternatives:
        attr = alt2[1]
        alt2_dm = UMLDomainModel()
        alt2_dm.add_class(alt2[0])
        q, o1, o2 = generate_attribute_question(alt2[0], alt2[1])
        #config = Configuration(alternative_2= alt2, alternative_2_dm = alt2_dm, question = q, option_1 = o1, option_2 = o2)
        config = ClassVsAttributeConfiguration(alternative_2= alt2, alternative_2_dm = alt2_dm, question = q, option_1 = o1, option_2 = o2)
        config.option_2_dm = domain_model
        alt1_found = None
        for alt1 in class_alternatives:
            cls = alt1[0]
            if is_similar(attr.name, cls.name):
                alt_1_dm = UMLDomainModel()
                source = copy.deepcopy(alt1[1].source)
                target = copy.deepcopy(alt1[1].target)
                alt_1_dm.add_class(source)
                alt_1_dm.add_class(target)
                alt_1_dm.add_relationship(copy.deepcopy(alt1[1]))
                #Abstract is another question
                if source.name.lower() == alt2[0].name.lower():
                    source.is_abstract = alt2[0].is_abstract 
                if target.name.lower() == alt2[0].name.lower():
                    target.is_abstract = alt2[0].is_abstract
                config.add_alternative_1(alternative_1 = alt1, alternative_1_dm = alt_1_dm)
                alt1_found = alt1
                
                #alt1_domain_model = alternative_1_model_change(domain_model, alt1, alt2)#use llm for change
                #config.add_option_1(alt1_domain_model)
                alternatives.append(config)
                break
        #config.add_option_1(alt1_domain_model)
        #alternatives.append(config)
        if not alt1_found:
            alt_1_dm = UMLDomainModel()
            source = copy.deepcopy(alt2[0])
            source.remove_attribute(alt2[1].name)
            target = UMLClass(name_format(alt2[1].name), [])
            new_relationship = UMLRelationship(source, target, "Association", "has", sourceCardinality="1", targetCardinality="1")
            alt_1_dm.add_class(source)
            alt_1_dm.add_class(target)
            alt_1_dm.add_relationship(new_relationship)
            alt1 = (target, new_relationship)
            config.add_alternative_1(alternative_1 = alt1, alternative_1_dm = alt_1_dm)
            no_alternatives.append(config)
    return alternatives, no_alternatives

def find_attribute_alternatives(class_alternatives, attributes_alternatives, domain_model):
    attr_list = attributes_alternatives
    class_list = class_alternatives
    
    alternatives = []
    no_alternatives = []
    for alt1 in class_list:
        cls = alt1[0]
        alt_1_dm = UMLDomainModel()
        alt_1_dm.add_class(copy.deepcopy(alt1[1].source))
        alt_1_dm.add_class(copy.deepcopy(alt1[1].target))
        alt_1_dm.add_relationship(copy.deepcopy(alt1[1]))
        q, o1, o2 = generate_class_with_single_association_question(alt1[0], alt1[1])
        #config = Configuration(alternative_1= alt1, alternative_1_dm = alt_1_dm, question = q, option_1 = o1, option_2 = o2)
        config = ClassVsAttributeConfiguration(alternative_1= alt1, alternative_1_dm = alt_1_dm, question = q, option_1 = o1, option_2 = o2)
        config.option_1_dm = domain_model
        alt2_found = None
        for alt2 in attr_list:
            attr = alt2[1]
            if is_similar(attr.name, cls.name):
                alt_2_dm = UMLDomainModel()
                alt2_cls = copy.deepcopy(alt2[0])
                alt_2_dm.add_class(alt2_cls)
                #Abstract is another question
                if alt1[1].source.name.lower() == alt2_cls.name.lower():
                    alt2_cls.is_abstract = alt1[1].source.is_abstract
                if alt1[1].target.name.lower() == alt2_cls.name.lower():
                    alt2_cls.is_abstract = alt1[1].target.is_abstract
                config.add_alternative_2(alternative_2 = alt2, alternative_2_dm = alt_2_dm)
                alt2_found = alt2
                
                #alt1_domain_model = alternative_1_model_change(domain_model, alt1, alt2)
                #config.add_option_1(alt2_domain_model)
                alternatives.append(config)
                break
        if not alt2_found:
            alt_2_dm = UMLDomainModel()
            alt2_cls = None
            new_attribute = None
            if alt1[0].name.lower() == alt1[1].source.name.lower():
                alt2_cls = copy.deepcopy(alt1[1].target)
                new_attribute = UMLAttribute(alt1[1].source.name, "string", Visibility.PRIVATE)
            else:
                alt2_cls = copy.deepcopy(alt1[1].source)
                new_attribute = UMLAttribute(alt1[1].target.name, "string", Visibility.PRIVATE)
            alt2_cls.add_attribute(new_attribute)
            alt_2_dm.add_class(alt2_cls)
            alt2 = (alt2_cls, new_attribute)
            config.add_alternative_2(alternative_2 = alt2, alternative_2_dm = alt_2_dm)

            no_alternatives.append(config)
    return alternatives, no_alternatives

def setup_class_vs_attribute_patterns(domain_model, domain_model_alternatives):
    attributes_dm = find_attributes(domain_model)
    class_alternatives = find_class_with_single_association(domain_model_alternatives)
    attributes_conf_alt, attributes_conf_no_alt = find_class_alternatives(class_alternatives, attributes_dm, domain_model)
    class_dm = find_class_with_single_association(domain_model)
    attributes_alternatives = find_attributes(domain_model_alternatives)
    class_conf_alt, class_conf_no_alt = find_attribute_alternatives(class_dm, attributes_alternatives, domain_model)
    
    configurations_alt = attributes_conf_alt + class_conf_alt
    configurations_no_alt = attributes_conf_no_alt + class_conf_no_alt
    return configurations_alt, configurations_no_alt