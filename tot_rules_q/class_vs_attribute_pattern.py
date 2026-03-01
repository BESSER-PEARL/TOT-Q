import copy
from tree_of_thought.model_elements import UMLClass, UMLAttribute, UMLEnumeration, Visibility, UMLRelationship, UMLDomainModel, UMLAssociationClass
from .configuration import Configuration
from .configuration import split_camel_case, correct_article, plural, name_format, is_similar
from .configuration import high_confidence, low_confidence, get_question_function
from collections import Counter


##############Class vs Attribute ##############
def find_class_with_single_association(domain_model: UMLDomainModel):
    association_count = {cls.name: 0 for cls in domain_model.classes}
    association_objects = {cls.name: [] for cls in domain_model.classes}
    for rel in domain_model.relationships:
        if domain_model.compare_relationship_type(rel.type.lower(), "association") or \
            domain_model.compare_relationship_type(rel.type.lower(), "composition"):
            if rel.source.name not in association_count or rel.target.name not in association_count:
                print(f"WARNING: Skipping relationship {rel.name} - references non-existent class")
                print(f"  Source: {rel.source.name} (exists: {rel.source.name in association_count})")
                print(f"  Target: {rel.target.name} (exists: {rel.target.name in association_count})")
                continue
            association_count[rel.source.name] += 1
            association_count[rel.target.name] = association_count.get(rel.target.name, 0) + 1
            association_objects[rel.source.name].append(rel)
            try:
                if association_objects[rel.target.name] is None:
                    print("ERROR DEBUG:", rel)
            except KeyError as e:
                print("KEY ERROR:", e, rel)
            association_objects[rel.target.name].append(rel)
    association_count = {cl: cnt for cl, cnt in association_count.items() if cnt != 0}
    for rel in domain_model.relationships:
        if domain_model.compare_relationship_type(rel.type.lower(), "inheritance"):
            if rel.source.name in association_count:
                association_count[rel.source.name] += 1
            if rel.target.name in association_count:    
                association_count[rel.target.name] = association_count.get(rel.target.name, 0) + 1
    classes_with_single_association = [(domain_model.get_class(name), association_objects[name][0]) for name, count in association_count.items() if count == 1]
    return classes_with_single_association

def find_attributes(domain_model: UMLDomainModel):
    enum_list = [e.name.lower() for e in domain_model.enumerations]
    attr_list = [(c, at) for c in domain_model.classes for at in c.attributes if \
                'str' in at.type.lower() and \
                not (at.name.lower() in enum_list or at.type.lower() in enum_list)]
    return attr_list


def find_enumerations_as_types(domain_model: UMLDomainModel):
    enum_usage = []
    for enum in domain_model.enumerations:
        for cls in domain_model.classes:
            for attr in cls.attributes:
                if attr.type == enum.name:
                    enum_usage.append((cls, enum))
                    break
    return enum_usage


class ClassVsAttributeConfiguration(Configuration):
    def update(self, cfg, domain_model, check_option):
        alt1 = cfg.alternative_1
        alt2 = cfg.alternative_2
        alt1_dm = cfg.alternative_1_dm
        alt2_dm = cfg.alternative_2_dm

        is_enum_alternative = isinstance(alt2[1], UMLEnumeration) if alt2 else False

        if (check_option == "Option 1" and cfg.option_1_dm) or \
            (check_option == "Option 2" and cfg.option_2_dm):
            if check_option == "Option 1":
                resulting_class = domain_model.get_class(alt1_dm.classes[1].name)
                cfg.update_confidence_model_element(resulting_class, high_confidence)
                cfg.resulting_element = ('class', resulting_class)
            else:
                if is_enum_alternative:
                    enum_to_update = domain_model.get_enumeration(alt2[1].name)
                    cfg.update_confidence_model_element(enum_to_update, high_confidence)
                    cfg.resulting_element = ('enumeration', enum_to_update)
                else:
                    att_to_update = domain_model.get_class(alt2[0].name).get_attribute(alt2[1].name)
                    cfg.update_confidence_model_element(att_to_update, high_confidence)
                    cfg.resulting_element = ('attribute', att_to_update)
            return None

        elif check_option == "Option 1" and not cfg.option_1_dm:
            try:
                cfg.update_confidence_model_element(alt1_dm.classes[1], high_confidence)
            except Exception as e:
                print("ERROR updating confidence for class:", e, alt1_dm.classes)

            rel_conf = [(cfg.update_confidence_model_element(rel, low_confidence),
                        cfg.update_confidence_model_element(rel.sourceCardinality, low_confidence),
                        cfg.update_confidence_model_element(rel.targetCardinality, low_confidence))
                        for rel in alt1_dm.relationships]

            if is_enum_alternative:
                enum_to_remove = alt2[1]
                new_class = alt1_dm.classes[1] 
                attributes_to_remove = []
                relationships_to_add = []

                for cls in domain_model.classes:
                    for attr in cls.attributes:
                        if attr.type == enum_to_remove.name:
                            attributes_to_remove.append((cls, attr))

                            new_rel = UMLRelationship(
                                cls, new_class, "Association", "has",
                                sourceCardinality="1", targetCardinality="1"
                            )
                            cfg.update_confidence_model_element(new_rel, low_confidence)
                            cfg.update_confidence_model_element(new_rel.sourceCardinality, low_confidence)
                            cfg.update_confidence_model_element(new_rel.targetCardinality, low_confidence)
                            relationships_to_add.append(new_rel)

                domain_model.update_model_general(
                    classes_to_remove=[],
                    attributes_to_remove=attributes_to_remove, 
                    relationships_to_remove=[],
                    enumerations_to_remove=[enum_to_remove],
                    assoc_classes_to_remove=[],
                    classes_to_add=[alt1_dm.classes[1]],
                    attributes_to_add=[],
                    relationships_to_add=relationships_to_add, 
                    enumerations_to_add=[],
                    assoc_classes_to_add=[],
                    replacement_map={}
                )
            else:
                rel_types = ["Association", "Containment"]
                rel_exists = None
                for rel_type in rel_types:
                    rel_exists = domain_model.get_relationship_ignore_name(source_name = alt1[1].source.name, target_name = alt1[1].target.name, 
                                              type= rel_type)
                    if not rel_exists:
                        rel_exists = domain_model.get_relationship_ignore_name(source_name = alt1[1].target.name, target_name = alt1[1].source.name, 
                                                type= rel_type)
                    if rel_exists:
                        break
                                                          
                if rel_exists:
                    rel_to_add = []
                else:
                    rel_to_add = alt1_dm.relationships
                domain_model.update_model_general(
                    classes_to_remove=[],
                    attributes_to_remove=[(alt2[0],alt2[1])],
                    relationships_to_remove=[],
                    enumerations_to_remove=[],
                    assoc_classes_to_remove=[],
                    classes_to_add=alt1_dm.classes,
                    attributes_to_add=[],
                    relationships_to_add=rel_to_add,
                    enumerations_to_add=[],
                    assoc_classes_to_add=[],
                    replacement_map={alt2_dm.classes[0]: alt1_dm.classes[0]},
                )

            cfg.resulting_element = ('class', alt1_dm.classes[1])
            return domain_model

        elif check_option == "Option 2" and not cfg.option_2_dm:
            cls_rep = alt1_dm.classes[0] if alt1_dm.classes[0].name == alt2_dm.classes[0].name else alt1_dm.classes[1]
            cfg.update_confidence_model_element(alt2[1], high_confidence)

            class_to_remove = alt1[0]
            relationships_to_remove = [
                rel for rel in domain_model.relationships
                if rel.source.name == class_to_remove.name or rel.target.name == class_to_remove.name
            ]

            domain_model.update_model_general(
                classes_to_remove=[alt1[0]],
                attributes_to_remove=[],
                relationships_to_remove=relationships_to_remove,
                enumerations_to_remove=[],
                assoc_classes_to_remove=[],
                classes_to_add=alt2_dm.classes,
                attributes_to_add=[(alt2[0],alt2[1])],
                relationships_to_add=[],
                enumerations_to_add=[],
                assoc_classes_to_add=[],
                replacement_map={cls_rep: alt2_dm.classes[0]},
            )
            cfg.resulting_element = ('attribute', alt2[1])
            return domain_model
        
    def set_confidence(self, configurations, alternative = True):
        for conf in configurations:
            alternative_1_score = None
            if hasattr(conf.alternative_1[0], '_metadata') and conf.alternative_1[0].get_metadata():
                if alternative or conf.option_1_dm:
                    alternative_1_score = conf.alternative_1[0].get_metadata().score
            alternative_2_score = None
            if hasattr(conf.alternative_2[1], '_metadata') and conf.alternative_2[1].get_metadata():
                if alternative or conf.option_2_dm:
                    alternative_2_score = conf.alternative_2[1].get_metadata().score
            elif hasattr(conf.alternative_2[0], '_metadata') and conf.alternative_2[0].get_metadata():
                if alternative or conf.option_2_dm:
                    alternative_2_score = conf.alternative_2[0].get_metadata().score
            if conf.option_1_dm:
                conf.set_metadata('alternative_1', alternative_1_score, alternative_2_score)
            elif conf.option_2_dm:
                conf.set_metadata('alternative_2', alternative_1_score, alternative_2_score)
        return configurations

def find_class_alternatives(class_alternatives, attributes_alternatives, domain_model, template_module=None):
    alternatives = []
    no_alternatives = []
    for alt2 in attributes_alternatives:
        attr = alt2[1]
        alt2_dm = UMLDomainModel()
        alt2_dm.add_class(alt2[0])
        if template_module:
            generate_attribute_question = template_module.generate_attribute_question
        else:
            generate_attribute_question = get_question_function('generate_attribute_question')
        q, o1, o2 = generate_attribute_question(alt2[0], alt2[1])
        config = ClassVsAttributeConfiguration(alternative_2= alt2, alternative_2_dm = alt2_dm, question = q, option_1 = o1, option_2 = o2)
        config.originated_from = ('attribute', alt2[1])
        config.option_2_dm = domain_model
        alt1_found = None
        for alt1 in class_alternatives:
            cls = alt1[0]
            if is_similar(attr.name, cls.name) and is_similar(alt1[0].name, alt2[0].name):
                alt_1_dm = UMLDomainModel()
                source = copy.deepcopy(alt1[1].source)
                target = copy.deepcopy(alt1[1].target)
                alt_1_dm.add_class(source)
                alt_1_dm.add_class(target)
                alt_1_dm.add_relationship(copy.deepcopy(alt1[1]))
                if source.name.lower() == alt2[0].name.lower():
                    source.is_abstract = alt2[0].is_abstract 
                if target.name.lower() == alt2[0].name.lower():
                    target.is_abstract = alt2[0].is_abstract
                config.add_alternative_1(alternative_1 = alt1, alternative_1_dm = alt_1_dm)
                alt1_found = alt1
                alternatives.append(config)
                break
        if not alt1_found:
            alt_1_dm = UMLDomainModel()
            source = copy.deepcopy(alt2[0])
            source.remove_attribute(alt2[1].name)
            target_attribute = UMLAttribute("name", "string", Visibility.PRIVATE)
            target_attribute.set_metadata(high_confidence)
            target = UMLClass(name_format(alt2[1].name), [target_attribute])
            new_relationship = UMLRelationship(source, target, "Association", "has", sourceCardinality="1", targetCardinality="1")
            alt_1_dm.add_class(source)
            alt_1_dm.add_class(target)
            alt_1_dm.add_relationship(new_relationship)
            alt1 = (target, new_relationship)
            config.add_alternative_1(alternative_1 = alt1, alternative_1_dm = alt_1_dm)
            no_alternatives.append(config)
    return alternatives, no_alternatives

def find_attribute_alternatives(class_alternatives, attributes_alternatives, domain_model, template_module=None):
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
        if template_module:
            generate_class_with_single_association_question = template_module.generate_class_with_single_association_question
        else:
            generate_class_with_single_association_question = get_question_function('generate_class_with_single_association_question')
        q, o1, o2 = generate_class_with_single_association_question(alt1[0], alt1[1])
        config = ClassVsAttributeConfiguration(alternative_1= alt1, alternative_1_dm = alt_1_dm, question = q, option_1 = o1, option_2 = o2)
        config.originated_from = ('class', alt1[0])
        config.option_1_dm = domain_model
        alt2_found = None
        for alt2 in attr_list:
            attr = alt2[1]
            if is_similar(attr.name, cls.name) and is_similar(alt1[0].name, alt2[0].name):
                alt_2_dm = UMLDomainModel()
                alt2_cls = copy.deepcopy(alt2[0])
                alt_2_dm.add_class(alt2_cls)
                if alt1[1].source.name.lower() == alt2_cls.name.lower():
                    alt2_cls.is_abstract = alt1[1].source.is_abstract
                if alt1[1].target.name.lower() == alt2_cls.name.lower():
                    alt2_cls.is_abstract = alt1[1].target.is_abstract
                config.add_alternative_2(alternative_2 = alt2, alternative_2_dm = alt_2_dm)
                alt2_found = alt2
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

def find_enumeration_alternatives(class_alternatives, enum_candidates, domain_model, template_module=None):
    alternatives = []
    no_alternatives = []

    for parent_class, enum in enum_candidates:
        alt_2_dm = UMLDomainModel()
        alt_2_dm.add_class(parent_class)
        alt_2_dm.add_enumeration(enum)

        synthetic_attr = UMLAttribute(enum.name.lower(), enum.name, Visibility.PRIVATE)
        if template_module:
            generate_attribute_question = template_module.generate_attribute_question
        else:
            generate_attribute_question = get_question_function('generate_attribute_question')
        q, o1, o2 = generate_attribute_question(parent_class, synthetic_attr)

        config = ClassVsAttributeConfiguration(
            alternative_2=(parent_class, enum),
            alternative_2_dm=alt_2_dm,
            question=q,
            option_1=o1,
            option_2=o2
        )
        config.originated_from = ('enumeration', enum)
        config.option_2_dm = domain_model  

        alt1_found = None
        for cls, rel in class_alternatives:
            if is_similar(cls.name, enum.name):
                alt_1_dm = UMLDomainModel()
                source = copy.deepcopy(rel.source)
                target = copy.deepcopy(rel.target)
                alt_1_dm.add_class(source)
                alt_1_dm.add_class(target)
                alt_1_dm.add_relationship(copy.deepcopy(rel))

                config.add_alternative_1(alternative_1=(cls, rel), alternative_1_dm=alt_1_dm)
                alt1_found = (cls, rel)
                alternatives.append(config)
                break

        if not alt1_found:
            new_class = UMLClass(enum.name, [])
            source_class = parent_class
            new_relationship = UMLRelationship(
                source_class, new_class, "Association", "has",
                sourceCardinality="1", targetCardinality="1"
            )

            alt_1_dm = UMLDomainModel()
            alt_1_dm.add_class(copy.deepcopy(source_class))
            alt_1_dm.add_class(new_class)
            alt_1_dm.add_relationship(new_relationship)

            config.add_alternative_1(
                alternative_1=(new_class, new_relationship),
                alternative_1_dm=alt_1_dm
            )
            no_alternatives.append(config)

    return alternatives, no_alternatives


def setup_class_vs_attribute_patterns(domain_model, domain_model_alternatives, template_module=None):
    attributes_dm = find_attributes(domain_model)
    class_alternatives = find_class_with_single_association(domain_model_alternatives)
    attributes_conf_alt, attributes_conf_no_alt = find_class_alternatives(class_alternatives, attributes_dm, domain_model, template_module)

    class_dm = find_class_with_single_association(domain_model)
    attributes_alternatives = find_attributes(domain_model_alternatives)
    class_conf_alt, class_conf_no_alt = find_attribute_alternatives(class_dm, attributes_alternatives, domain_model, template_module)

    enums_dm = find_enumerations_as_types(domain_model)
    enum_conf_alt, enum_conf_no_alt = find_enumeration_alternatives(class_alternatives, enums_dm, domain_model, template_module)

    configurations_alt = attributes_conf_alt + class_conf_alt + enum_conf_alt
    configurations_no_alt = attributes_conf_no_alt + class_conf_no_alt + enum_conf_no_alt

    return configurations_alt, configurations_no_alt