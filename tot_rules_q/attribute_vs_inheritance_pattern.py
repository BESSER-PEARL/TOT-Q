import copy
from tree_of_thought.model_elements import UMLClass, UMLAttribute, UMLEnumeration, Visibility, UMLRelationship, UMLDomainModel, UMLAssociationClass
from configuration import Configuration
from configuration import split_camel_case, correct_article, plural, name_format, is_similar
from configuration import high_confidence, low_confidence
from collections import Counter
from template_questions import generate_single_empty_subclass_question, generate_boolean_attributes_question


##############Attribute vs Inheritance##############
###Attribute vs Inheritance - Inheritance identified
#TODO run with multiple patterns in same model
def find_single_empty_subclass(domain_model):
    inheritance = [(rel.source, rel.target) for rel in domain_model.relationships if domain_model.compare_relationship_type(rel.type.lower(), "inheritance")]
    subclasses = [(sup, sub) for sup, sub in inheritance
            if domain_model.get_class(sub.name) and len(domain_model.get_class(sub.name).attributes) == 0]
    count_inheritance = Counter([sup.name for sup, _ in inheritance])
    one_class_inheritance = {sup: count for sup, count  in count_inheritance.items() if count == 1}
    count_subclasses = Counter([sup.name for sup, _ in subclasses])
    subclass_with_no_attributes = [(sup, sub)  for sup, sub in subclasses 
                                     if sup.name in one_class_inheritance and 
                                     one_class_inheritance[sup.name] == count_subclasses[sup.name]]
    #number of relationships subclass:
    if len(subclass_with_no_attributes)>0:
        num_relationships = {}
        for subcls in [subclass_with_no_attributes[0][1]]:
            relationship_count=0
            for rel in domain_model.relationships:
                if rel.source.name.lower() == subcls.name.lower():
                    relationship_count += 1
                elif rel.target.name.lower() == subcls.name.lower():    
                    relationship_count += 1
            num_relationships[subcls.name]=relationship_count
            #num_relationships[subcls.name]=1
        subclass_with_no_attributes = [(sup, sub) for sup, sub in subclass_with_no_attributes 
                                        if num_relationships[sub.name]==1]
    superclasses = set(k for k, _ in subclass_with_no_attributes)
    superclass_subclass_with_no_attributes = [(cls, [sub for sup, sub in subclass_with_no_attributes if sup.name == cls.name]) for cls in superclasses]
    return superclass_subclass_with_no_attributes

def find_boolean_attributes(domain_model: UMLDomainModel):
    attr_list = [(c, at) for c in domain_model.classes for at in c.attributes if "bool" in at.type.lower()]
    return attr_list

class AttributeVsInheritanceConfiguration(Configuration):
    def update(self, cfg, domain_model, check_option):
        alt1 = cfg.alternative_1
        alt2 = cfg.alternative_2
        alt1_dm = cfg.alternative_1_dm
        alt2_dm = cfg.alternative_2_dm
        if (check_option == "Option 1" and cfg.option_1_dm) or \
            (check_option == "Option 2" and cfg.option_2_dm):
            if check_option == "Option 1":
                cls_conf = [cfg.update_confidence_model_element(domain_model.get_class(cls.name), high_confidence) for cls in alt1_dm.classes[1:]]
                rel_to_update = [domain_model.get_relationship_ignore_name(r.source.name, r.target.name, r.type) for r in alt1_dm.relationships]
                rel_conf = [(cfg.update_confidence_model_element(rel, high_confidence), 
                            cfg.update_confidence_model_element(rel.sourceCardinality, high_confidence),
                            cfg.update_confidence_model_element(rel.targetCardinality, high_confidence))
                            for rel in rel_to_update]
            else:
                att_to_update = domain_model.get_class(alt2[0].name).get_attribute(alt2[1].name)
                cfg.update_confidence_model_element(att_to_update, high_confidence)
            return None
        elif check_option == "Option 1" and not cfg.option_1_dm:
            print()
            #update confidence
            cls_conf = [cfg.update_confidence_model_element(cls, high_confidence) for cls in alt1_dm.classes[1:]]
            rel_conf = [(cfg.update_confidence_model_element(rel, high_confidence), 
                        cfg.update_confidence_model_element(rel.sourceCardinality, high_confidence),
                        cfg.update_confidence_model_element(rel.targetCardinality, high_confidence))
                        for rel in alt1_dm.relationships]
            domain_model.update_model_general(
                classes_to_remove=[alt2[0]],
                attributes_to_remove=[],  
                relationships_to_remove=[],
                enumerations_to_remove=[alt2[1]],
                assoc_classes_to_remove=[],
                classes_to_add=alt1_dm.classes,
                attributes_to_add=[],
                relationships_to_add=alt1_dm.relationships,
                enumerations_to_add=[],
                assoc_classes_to_add=[],
                replacement_map={alt2[0]: alt1_dm.classes[0]},
            )
            return domain_model
        elif check_option == "Option 2" and not cfg.option_2_dm:
            #update confidence
            cfg.update_confidence_model_element(alt2[1], high_confidence) 
            #TODO check if attribute is already in domain_model class
            domain_model.update_model_general(
                classes_to_remove=alt1_dm.classes,
                attributes_to_remove=[],  
                relationships_to_remove=alt1_dm.relationships,
                enumerations_to_remove=[],
                assoc_classes_to_remove=[],
                classes_to_add=[alt2[0]],
                attributes_to_add=[(alt2[0],alt2[1])],
                relationships_to_add=[],
                enumerations_to_add=[],
                assoc_classes_to_add=[],
                replacement_map={alt1_dm.classes[0]: alt2[0]},
            )
            return domain_model
    
    def set_confidence(self, configurations, alternative = True):
    #def confidence_configuration_attribute_vs_inheritance(configurations, alternative = True):
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

def find_attribute_boolean_alternatives(attribute_alternatives, inheritance_alternatives, domain_model):
    alternatives = []
    no_alternatives = []
    for alt1 in inheritance_alternatives:
        print(alt1)
        alt1_name = alt1[0].name
        inheritance_dm = UMLDomainModel()
        inheritance_dm.add_class(alt1[0])
        subclasses = [inheritance_dm.add_class(sc) for sc in alt1[1]]
        subclasses_names = [split_camel_case(sc.name).lower() for sc in alt1[1]]
        subclasses_names = [item.split(' ') for item in subclasses_names]
        subclasses_names = [s for sc in subclasses_names for s in sc]
        relationships =[inheritance_dm.add_relationship(
                        UMLRelationship(alt1[0], sc, "Inheritance", "inherits", sourceCardinality="1", targetCardinality="1"))
                        for sc in alt1[1]]
        q, o1, o2 = generate_single_empty_subclass_question(alt1[0], alt1[1][0])
        #config = Configuration(alternative_1= alt1, alternative_1_dm= inheritance_dm, question=q, option_1=o1, option_2=o2)
        config = AttributeVsInheritanceConfiguration(alternative_1= alt1, alternative_1_dm= inheritance_dm, question=q, option_1=o1, option_2=o2)
        config.option_1_dm = domain_model
        alt2_found = None
        for alt2 in attribute_alternatives:
            alt2_name = alt2[1].name
            attribute_name = split_camel_case(alt2[1].name)
            attribute_name = attribute_name.split(' ')
            attribute_name = [att.lower() for att in attribute_name]
            match_attribute = [l for l in attribute_name if l in subclasses_names]
            is_alternative = len(attribute_name) == len(match_attribute)
            if is_alternative:
                alt_2_dm = UMLDomainModel()
                alt2[0].is_abstract = False
                alt_2_dm.add_class(alt2[0])
                #alt_2_dm.add_enumeration(alt2[1])
                config.add_alternative_2(alternative_2 = alt2, alternative_2_dm = alt_2_dm)
                alt2_found = alt2
                alternatives.append(config)
                break
        if not alt2_found:
            alt_2_dm = UMLDomainModel()
            alt2_cls = copy.deepcopy(alt1[0])
            alt2_cls.is_abstract = False
            new_attribute = UMLAttribute('is' + alt1[1][0].name, 'boolean', Visibility.PRIVATE)
            alt2_cls.add_attribute(new_attribute)
            alt_2_dm.add_class(alt2_cls)
            alt2 = (alt2_cls, new_attribute)
            config.add_alternative_2(alternative_2 = alt2, alternative_2_dm = alt_2_dm)
            no_alternatives.append(config)
    return alternatives, no_alternatives

def find_inheritance_single_subclass_alternatives(attribute_alternatives, inheritance_alternatives, domain_model):
    alternatives = []
    no_alternatives = []
    for alt2 in attribute_alternatives:
        alt2_name = alt2[1].name
        attribute_name = split_camel_case(alt2[1].name)
        attribute_name = attribute_name.split(' ')
        attribute_name = [att.lower() for att in attribute_name]
        alt_2_dm = UMLDomainModel()
        alt_2_dm.add_class(alt2[0])
        q, o1, o2 = generate_boolean_attributes_question(alt2[0], alt2[1])
        #config = Configuration(alternative_2= alt2, alternative_2_dm= alt_2_dm, question=q, option_1=o1, option_2=o2)
        config = AttributeVsInheritanceConfiguration(alternative_2= alt2, alternative_2_dm= alt_2_dm, question=q, option_1=o1, option_2=o2)
        config.option_2_dm = domain_model
        alt1_found = None
        for alt1 in inheritance_alternatives:
            alt1_name = alt1[0].name
            subclasses_names = [split_camel_case(sc.name).lower() for sc in alt1[1]]
            subclasses_names = [item.split(' ') for item in subclasses_names]
            subclasses_names = [s for sc in subclasses_names for s in sc]
            match_attribute = [l for l in attribute_name if l in subclasses_names]
            is_alternative = len(attribute_name) == len(match_attribute)
            if is_alternative:
                inheritance_dm = UMLDomainModel()
                parent_cls = copy.deepcopy(alt1[0])
                #Abstract is another question
                if alt2[0].name.lower() == parent_cls.name.lower():
                    parent_cls.is_abstract = alt2[0].is_abstract
                inheritance_dm.add_class(parent_cls)
                subclasses = [inheritance_dm.add_class(sc) for sc in alt1[1]]
                subclasses_names = [split_camel_case(sc.name).lower() for sc in alt1[1]]
                subclasses_names = [item.split(' ') for item in subclasses_names]
                subclasses_names = [s for sc in subclasses_names for s in sc]
                relationships =[inheritance_dm.add_relationship(
                                UMLRelationship(alt1[0], sc, "Inheritance", "inherits", sourceCardinality="1", targetCardinality="1"))
                                for sc in alt1[1]]
                config.add_alternative_1(alternative_1 = alt1, alternative_1_dm = inheritance_dm)
                alt1_found = alt1
                alternatives.append(config)
                break
        if not alt1_found:
            alt_1_dm = UMLDomainModel()
            parent_cls = copy.deepcopy(alt2[0])
            #delete attribute pend
            new_attributes = [copy.deepcopy(att) for att in parent_cls.attributes 
                              if att.name.lower() != alt2[1].name.lower()]
            parent_cls.attributes = new_attributes
            alt_1_dm.add_class(parent_cls)
            name_new_class = name_format(split_camel_case(alt2[1].name).replace(' ',''))
            new_subclass = UMLClass(name_new_class,[])
            alt_1_dm.add_class(new_subclass)
            new_relationship =UMLRelationship(parent_cls, new_subclass, "Inheritance", "inherits", sourceCardinality="1", targetCardinality="1")
            alt_1_dm.add_relationship(new_relationship)
            alt1 = (parent_cls, [new_subclass])
            config.add_alternative_1(alternative_1 = alt1, alternative_1_dm = alt_1_dm)
            no_alternatives.append(config)
    return alternatives, no_alternatives

def setup_attribute_vs_inheritance_patterns(domain_model, domain_model_alternatives):
    attributes_dm = find_boolean_attributes(domain_model)
    subclass_dm = find_single_empty_subclass(domain_model)

    attributes_alternatives = find_boolean_attributes(domain_model_alternatives)
    subclass_alternatives = find_single_empty_subclass(domain_model_alternatives)
    
    # Attribute and inheritance is the same model. How to solve this?
    # Find alternatives for enumerations and inheritance
    attributes_conf_alt, attributes_conf_no_alt = find_attribute_boolean_alternatives(attributes_alternatives, subclass_dm, domain_model)
    subclass_conf_alt, subclass_conf_no_alt  = find_inheritance_single_subclass_alternatives(attributes_dm, subclass_alternatives, domain_model)
    
    configurations_alt = attributes_conf_alt + subclass_conf_alt
    configurations_no_alt = attributes_conf_no_alt + subclass_conf_no_alt
    return configurations_alt, configurations_no_alt