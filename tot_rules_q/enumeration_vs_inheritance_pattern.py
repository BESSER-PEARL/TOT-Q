import copy
from tree_of_thought.model_elements import UMLClass, UMLAttribute, UMLEnumeration, Visibility, UMLRelationship, UMLDomainModel, UMLAssociationClass
from .configuration import Configuration
from .configuration import split_camel_case, correct_article, plural, name_format, is_similar
from .configuration import high_confidence, low_confidence, get_question_function
from collections import Counter

##############Enumeration vs Inheritance##############

def find_subclass_with_no_attributes(domain_model: UMLDomainModel):
    inheritance = [(rel.source, rel.target) for rel in domain_model.relationships if domain_model.compare_relationship_type(rel.type.lower(), "inheritance")]
    subclasses = [(sup, sub) for sup, sub in inheritance
            if domain_model.get_class(sub.name) and len(domain_model.get_class(sub.name).attributes) == 0]
    if len(subclasses)>0:
        num_relationships = {}
        for supcls, subcls in subclasses:
            relationship_count=0
            for rel in domain_model.relationships:
                if rel.source.name.lower() == subcls.name.lower():
                    relationship_count += 1
                elif rel.target.name.lower() == subcls.name.lower():    
                    relationship_count += 1
            num_relationships[subcls.name]=relationship_count
        subclasses = [(sup, sub) for sup, sub in subclasses 
                    if num_relationships[sub.name]==1]
    count_inheritance = Counter([sup.name for sup, _ in inheritance])
    multiple_class_inheritance = {sup: count for sup, count  in count_inheritance.items() if count > 1}
    count_subclasses = Counter([sup.name for sup, _ in subclasses])
    subclasses_with_no_attributes = [(sup, sub)  for sup, sub in subclasses 
                                     if sup.name in multiple_class_inheritance and
                                     multiple_class_inheritance[sup.name] == count_subclasses[sup.name]]
    superclasses = list({cls.name: cls for cls, _ in subclasses_with_no_attributes}.values())
    superclass_subclasses_with_no_attributes = [(cls, [sub for sup, sub in subclasses_with_no_attributes if sup.name == cls.name]) for cls in superclasses]
    return superclass_subclasses_with_no_attributes

def find_enumerations(domain_model):
    enum_list = [e.name.lower() for e in domain_model.enumerations]
    attr_list = [(c.name, a.name, a.type) for c in domain_model.classes for a in c.attributes]
    enum_associations = [(a[2], a[0]) for a in attr_list if a[2].lower() in enum_list]
    existing_enums = [k.lower() for k, v in enum_associations]
    enum_associations2 = [(a[1], a[0]) for a in attr_list if a[1].lower() in enum_list and a[1].lower() not in existing_enums]
    enum_associations = enum_associations + enum_associations2
    counting_enums = {}
    for k, v in enum_associations:
        key = k.lower()
        counting_enums[key] = counting_enums.get(key, 0) + 1
    single_enums = [(k, v) for k, v in enum_associations]
    class_with_enum = [(domain_model.get_class(cls), domain_model.get_enumeration(enum)) for enum, cls in single_enums]
    return class_with_enum



class EnumerationVsInheritanceConfiguration(Configuration):
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
                cfg.resulting_element = ('subclass', alt1[1])  
            else:
                enum_to_update = domain_model.get_enumeration(alt2[1].name)
                cfg.update_confidence_model_element(enum_to_update, high_confidence)
                for cls in domain_model.classes:
                    for attr in cls.attributes:
                        if attr.type.lower() == enum_to_update.name.lower():
                            cfg.update_confidence_model_element(attr, high_confidence)

                cfg.resulting_element = ('enumeration', enum_to_update)
                inheritance = [(rel.source, rel.target, rel) for rel in domain_model.relationships if domain_model.compare_relationship_type(rel.type.lower(), "inheritance")]
                subclasses = [(sup, sub, rel) for sup, sub, rel in inheritance
                        if domain_model.get_class(sub.name)] 
                supcls_to_remove = []
                cls_to_remove = []
                rel_to_remove = []
                for l in enum_to_update.literals:
                    for supc, subc, rel in subclasses:
                        if l.lower() in subc.name.lower():
                            cls_to_remove.append(subc)
                            rel_to_remove.append(rel)
                            if supc not in supcls_to_remove:
                                supcls_to_remove.append(supc)
                if len(cls_to_remove) > 0:
                    domain_model.update_model_general(
                        classes_to_remove=cls_to_remove,
                        attributes_to_remove=[],  
                        relationships_to_remove=rel_to_remove,
                        enumerations_to_remove=[],
                        assoc_classes_to_remove=[],
                        classes_to_add=[],
                        attributes_to_add=[],
                        relationships_to_add=[],
                        enumerations_to_add=[],
                        assoc_classes_to_add=[],
                        replacement_map={supcls_to_remove[0]:alt2_dm.classes[0]},
                    )
            return None
        elif check_option == "Option 1" and not cfg.option_1_dm:
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
            cfg.resulting_element = ('subclass', alt1[1])
            return domain_model
        elif check_option == "Option 2" and not cfg.option_2_dm:
            cfg.update_confidence_model_element(alt2[1], high_confidence)
            enum_to_update = alt2[1]
            for attr in alt2[0].attributes:
                if attr.type.lower() == enum_to_update.name.lower():
                    cfg.update_confidence_model_element(attr, high_confidence)
            domain_model.update_model_general(
                classes_to_remove=alt1_dm.classes,
                attributes_to_remove=[],
                relationships_to_remove=alt1_dm.relationships,
                enumerations_to_remove=[],
                assoc_classes_to_remove=[],
                classes_to_add=[alt2[0]],
                attributes_to_add=[],
                relationships_to_add=[],
                enumerations_to_add=[alt2[1]],
                assoc_classes_to_add=[],
                replacement_map={alt1_dm.classes[0]: alt2[0]},
            )
            cfg.resulting_element = ('enumeration', alt2[1])
            for cls in domain_model.classes:
                for attr in cls.attributes:
                    if attr.type.lower() == enum_to_update.name.lower():
                        cfg.update_confidence_model_element(attr, high_confidence)
            return domain_model
        
    def set_confidence(self, configurations, alternative = True):
        for conf in configurations:
            alternative_1_score = None
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
        
def find_enumeration_alternatives(enumeration_alternatives, inheritance_alternatives, domain_model, template_module=None):
    alternatives = []
    no_alternatives = []
    for alt1 in inheritance_alternatives:
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
        if template_module:
            generate_subclass_with_no_attributes_question = template_module.generate_subclass_with_no_attributes_question
        else:
            generate_subclass_with_no_attributes_question = get_question_function('generate_subclass_with_no_attributes_question')
        q, o1, o2 = generate_subclass_with_no_attributes_question(alt1[0], alt1[1])
        config = EnumerationVsInheritanceConfiguration(alternative_1= alt1, alternative_1_dm= inheritance_dm, question=q, option_1=o1, option_2=o2)
        config.originated_from = ('subclass', alt1[1])
        config.option_1_dm = domain_model
        alt2_found = None
        for alt2 in enumeration_alternatives:
            alt2_name = alt2[1].name
            literals_name = [split_camel_case(l).lower() for l in alt2[1].literals]
            match_literal_subclass = [l for l in literals_name if l in subclasses_names]
            is_alternative = len(literals_name) == len(match_literal_subclass)
            if is_alternative:
                alt_2_dm = UMLDomainModel()
                alt2[0].is_abstract = False
                alt_2_dm.add_class(alt2[0])
                alt_2_dm.add_enumeration(alt2[1])
                config.add_alternative_2(alternative_2 = alt2, alternative_2_dm = alt_2_dm)
                alt2_found = alt2
                alternatives.append(config)
                break
        if not alt2_found:
            alt_2_dm = UMLDomainModel()
            alt2_cls = copy.deepcopy(alt1[0])
            alt2_cls.is_abstract = False
            new_attribute = UMLAttribute(alt1[0].name + 'Type', alt1[0].name + 'Type', Visibility.PRIVATE)
            alt2_cls.add_attribute(new_attribute)
            new_literals = [l.upper() for l in subclasses_names if l.lower() != alt2_cls.name.lower()]
            alt2_enum =  UMLEnumeration(name_format(alt1[0].name + 'Type'), new_literals)
            alt_2_dm.add_class(alt2_cls)
            alt_2_dm.add_enumeration(alt2_enum)
            alt2 = (alt2_cls, alt2_enum)
            config.add_alternative_2(alternative_2 = alt2, alternative_2_dm = alt_2_dm)
            no_alternatives.append(config)
    return alternatives, no_alternatives

def find_inheritance_alternatives(enumeration_alternatives, inheritance_alternatives, domain_model, template_module=None):
    alternatives = []
    no_alternatives = []
    for alt2 in enumeration_alternatives:
        alt2_name = alt2[1].name
        literals_name = [split_camel_case(l).lower() for l in alt2[1].literals]
        alt_2_dm = UMLDomainModel()
        cls_alt_2 = copy.deepcopy(alt2[0])
        cls_alt_2.is_abstract = False
        alt_2_dm.add_class(cls_alt_2)
        alt_2_dm.add_enumeration(alt2[1])
        if template_module:
            generate_enumeration_question = template_module.generate_enumeration_question
        else:
            generate_enumeration_question = get_question_function('generate_enumeration_question')
        q, o1, o2 = generate_enumeration_question(alt2[0], alt2[1])
        config = EnumerationVsInheritanceConfiguration(alternative_2= alt2, alternative_2_dm= alt_2_dm, question=q, option_1=o1, option_2=o2)
        config.originated_from = ('enumeration', alt2[1])
        config.option_2_dm = domain_model
        alt1_found = None
        for alt1 in inheritance_alternatives:
            alt1_name = alt1[0].name
            subclasses_names = [split_camel_case(sc.name).lower() for sc in alt1[1]]
            subclasses_names = [item.split(' ') for item in subclasses_names]
            subclasses_names = [s for sc in subclasses_names for s in sc]
            match_literal_subclass = [l for l in literals_name if l in subclasses_names]
            is_alternative = len(literals_name) == len(match_literal_subclass)
            if is_alternative:
                inheritance_dm = UMLDomainModel()
                parent_cls = copy.deepcopy(alt1[0])
                if alt2[0].name.lower() == parent_cls.name.lower():
                    parent_cls.is_abstract = alt2[0].is_abstract
                inheritance_dm.add_class(parent_cls)
                subclasses = [inheritance_dm.add_class(sc) for sc in alt1[1]]
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
            new_attributes = [copy.deepcopy(att) for att in parent_cls.attributes 
                              if att.name.lower() != alt2[1].name.lower() and att.type.lower() != alt2[1].name.lower()]
            parent_cls.attributes = new_attributes
            alt_1_dm.add_class(parent_cls)

            subclasses = [UMLClass(name_format(sc.lower()),[]) for sc in alt2[1].literals]
            add_subclasses = [alt_1_dm.add_class(sc) for sc in subclasses]
            relationships =[alt_1_dm.add_relationship(
                        UMLRelationship(parent_cls, sc, "Inheritance", "inherits", sourceCardinality="1", targetCardinality="1"))
                        for sc in subclasses]
            alt1 = (parent_cls, subclasses)
            config.add_alternative_1(alternative_1 = alt1, alternative_1_dm = alt_1_dm)
            no_alternatives.append(config)
    return alternatives, no_alternatives

def setup_enumeration_vs_inheritance_patterns(domain_model, domain_model_alternatives, template_module=None):
    enumerations_dm = find_enumerations(domain_model)
    subclasses_dm = find_subclass_with_no_attributes(domain_model)
    enumeration_alternatives = find_enumerations(domain_model_alternatives)
    inheritance_alternatives = find_subclass_with_no_attributes(domain_model_alternatives)
    enumeration_conf_alt, enumeration_conf_no_alt = find_enumeration_alternatives(enumeration_alternatives, subclasses_dm, domain_model, template_module)
    inheritance_conf_alt, inheritance_conf_no_alt = find_inheritance_alternatives(enumerations_dm, inheritance_alternatives, domain_model, template_module)

    configurations_alt = enumeration_conf_alt + inheritance_conf_alt
    configurations_no_alt = enumeration_conf_no_alt + inheritance_conf_no_alt
    return configurations_alt, configurations_no_alt

