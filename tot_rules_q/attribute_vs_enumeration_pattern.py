import copy
from tree_of_thought.model_elements import UMLClass, UMLAttribute, UMLEnumeration, Visibility, UMLRelationship, UMLDomainModel
from .configuration import Configuration
from .configuration import split_camel_case, correct_article, plural, name_format, is_similar
from .configuration import high_confidence, low_confidence, get_question_function
from collections import Counter

##############Attribute vs Enumeration##############

def find_simple_string_attributes(domain_model: UMLDomainModel):
    attr_list = []
    for cls in domain_model.classes:
        for attr in cls.attributes:
            if any(t in attr.type.lower() for t in ['string', 'str', 'text']):
                attr_list.append((cls, attr))
    return attr_list


def find_enumeration_candidates(domain_model: UMLDomainModel):
    enum_list = [e.name.lower() for e in domain_model.enumerations]
    enum_candidates = []

    for cls in domain_model.classes:
        for attr in cls.attributes:
            if attr.name.lower() in enum_list or attr.type.lower() in enum_list:
                enum = next((e for e in domain_model.enumerations
                           if e.name.lower() == attr.name.lower() or
                              e.name.lower() == attr.type.lower()), None)
                if enum:
                    enum_candidates.append((cls, enum))

    return enum_candidates


class AttributeVsEnumerationConfiguration(Configuration):
    def update(self, cfg, domain_model, check_option):
        alt1 = cfg.alternative_1
        alt2 = cfg.alternative_2
        alt1_dm = cfg.alternative_1_dm
        alt2_dm = cfg.alternative_2_dm

        if (check_option == "Option 1" and cfg.option_1_dm) or \
           (check_option == "Option 2" and cfg.option_2_dm):
            if check_option == "Option 1":
                att_to_update = domain_model.get_class(alt1[0].name).get_attribute(alt1[1].name)
                if att_to_update:
                    cfg.update_confidence_model_element(att_to_update, high_confidence)
                    cfg.resulting_element = ('attribute', att_to_update)
                if alt2 and len(alt2) > 1:
                    enum_to_remove = domain_model.get_enumeration(alt2[1].name)
                    if enum_to_remove:
                        domain_model.update_model_general(
                            classes_to_remove=[],
                            attributes_to_remove=[],
                            relationships_to_remove=[],
                            enumerations_to_remove=[enum_to_remove],
                            assoc_classes_to_remove=[],
                            classes_to_add=[],
                            attributes_to_add=[],
                            relationships_to_add=[],
                            enumerations_to_add=[],
                            assoc_classes_to_add=[],
                            replacement_map={}
                        )
            else:
                enum_to_update = domain_model.get_enumeration(alt2[1].name)
                if enum_to_update:
                    cfg.update_confidence_model_element(enum_to_update, high_confidence)
                    cfg.resulting_element = ('enumeration', enum_to_update)

                parent_cls = domain_model.get_class(alt1[0].name)
                if parent_cls:
                    attr_to_update = parent_cls.get_attribute(alt1[1].name)
                    if attr_to_update:
                        attr_to_update.type = alt2[1].name
                        cfg.update_confidence_model_element(attr_to_update, high_confidence)

            return None

        elif check_option == "Option 1" and not cfg.option_1_dm:
            att_to_update = alt1[1]
            cfg.update_confidence_model_element(att_to_update, high_confidence)

            enum_to_remove = alt2[1]

            classes_using_enum = []
            for cls in domain_model.classes:
                for attr in cls.attributes:
                    if attr.type == enum_to_remove.name:
                        attr.type = 'string'
                        cfg.update_confidence_model_element(attr, high_confidence)
                        classes_using_enum.append(cls)

            if not classes_using_enum:
                target_class = domain_model.get_class(alt1[0].name)
                if target_class:
                    existing_attr = target_class.get_attribute(att_to_update.name)
                    if not existing_attr:
                        new_attr = copy.deepcopy(att_to_update)
                        target_class.add_attribute(new_attr)
                        cfg.update_confidence_model_element(new_attr, high_confidence)
                        att_to_update = new_attr

            domain_model.update_model_general(
                classes_to_remove=[],
                attributes_to_remove=[],
                relationships_to_remove=[],
                enumerations_to_remove=[enum_to_remove],
                assoc_classes_to_remove=[],
                classes_to_add=[],
                attributes_to_add=[],
                relationships_to_add=[],
                enumerations_to_add=[],
                assoc_classes_to_add=[],
                replacement_map={}
            )
            cfg.resulting_element = ('attribute', att_to_update)
            return domain_model

        elif check_option == "Option 2" and not cfg.option_2_dm:
            enum_to_add = alt2[1]
            cfg.update_confidence_model_element(enum_to_add, high_confidence)

            attr_to_update = None
            attr_to_remove = None
            parent_cls = domain_model.get_class(alt1[0].name)
            if parent_cls:
                attr_to_remove = parent_cls.get_attribute(alt1[1].name)
                if attr_to_remove:
                    attr_to_update = copy.deepcopy(attr_to_remove)
                    attr_to_update.type = enum_to_add.name
                    cfg.update_confidence_model_element(attr_to_update, high_confidence)

            domain_model.update_model_general(
                classes_to_remove=[],
                attributes_to_remove=[(parent_cls,attr_to_remove)],
                relationships_to_remove=[],
                enumerations_to_remove=[],
                assoc_classes_to_remove=[],
                classes_to_add=[],
                attributes_to_add=[],
                relationships_to_add=[],
                enumerations_to_add=[],
                assoc_classes_to_add=[],
                replacement_map={}
            )
            
            if parent_cls:
                attr_to_remove = parent_cls.get_attribute(alt1[1].name)
                if attr_to_remove:
                    domain_model.update_model_general(
                        classes_to_remove=[],
                        attributes_to_remove=[(parent_cls,attr_to_remove)],
                        relationships_to_remove=[],
                        enumerations_to_remove=[],
                        assoc_classes_to_remove=[],
                        classes_to_add=[],
                        attributes_to_add=[],
                        relationships_to_add=[],
                        enumerations_to_add=[],
                        assoc_classes_to_add=[],
                        replacement_map={}
                    )
                    
            domain_model.update_model_general(
                classes_to_remove=[],
                attributes_to_remove=[],
                relationships_to_remove=[],
                enumerations_to_remove=[],
                assoc_classes_to_remove=[],
                classes_to_add=[],
                attributes_to_add=[(parent_cls,attr_to_update)],
                relationships_to_add=[],
                enumerations_to_add=[enum_to_add],
                assoc_classes_to_add=[],
                replacement_map={}
            )
            cfg.resulting_element = ('enumeration', enum_to_add)
            return domain_model

    def set_confidence(self, configurations, alternative=True):
        """Set confidence scores for configurations based on metadata."""
        for conf in configurations:
            alternative_1_score = None
            if hasattr(conf.alternative_1[1], '_metadata') and conf.alternative_1[1].get_metadata():
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

def find_attribute_alternatives(enum_candidates, string_attrs, domain_model, template_module=None):
    alternatives = []
    no_alternatives = []

    for attr_cls, attr in string_attrs:
        alt_1_dm = UMLDomainModel()
        alt_1_dm.add_class(attr_cls)

        if template_module:
            generate_string_attribute_question = template_module.generate_string_attribute_question
        else:
            generate_string_attribute_question = get_question_function('generate_string_attribute_question')

        alt2_found = None
        for enum_cls, enum in enum_candidates:
            attr_name_normalized = attr.name.lower().replace('type', '').replace('_', '').strip()
            enum_name_normalized = enum.name.lower().replace('type', '').replace('_', '').strip()

            if (is_similar(attr_name_normalized, enum_name_normalized) or
                is_similar(attr.type.lower(), enum.name.lower()) or
                enum_cls.name == attr_cls.name):

                alt_2_dm = UMLDomainModel()
                alt_2_dm.add_class(enum_cls)
                alt_2_dm.add_enumeration(enum)

                q, o1, o2 = generate_string_attribute_question(attr_cls, attr, enum)
                config = AttributeVsEnumerationConfiguration(
                    alternative_1=(attr_cls, attr),
                    alternative_1_dm=alt_1_dm,
                    alternative_2=(enum_cls, enum),
                    alternative_2_dm=alt_2_dm,
                    question=q,
                    option_1=o1,
                    option_2=o2
                )
                config.originated_from = ('attribute', attr)
                config.option_1_dm = domain_model

                alt2_found = enum
                alternatives.append(config)
                break

        if not alt2_found:
            enum_name = name_format(attr.name.replace('_', ' ').title())
            if not enum_name.endswith('Type'):
                enum_name = enum_name + 'Type'

            new_enum = UMLEnumeration(enum_name, ['LITERAL_1', 'LITERAL_2', 'LITERAL_3'])

            alt_2_dm = UMLDomainModel()
            alt_2_dm.add_class(attr_cls)
            alt_2_dm.add_enumeration(new_enum)

            q, o1, o2 = generate_string_attribute_question(attr_cls, attr, new_enum)
            config = AttributeVsEnumerationConfiguration(
                alternative_1=(attr_cls, attr),
                alternative_1_dm=alt_1_dm,
                alternative_2=(attr_cls, new_enum),
                alternative_2_dm=alt_2_dm,
                question=q,
                option_1=o1,
                option_2=o2
            )
            config.originated_from = ('attribute', attr)
            config.option_1_dm = domain_model

            no_alternatives.append(config)

    return alternatives, no_alternatives


def find_enumeration_alternatives(enum_candidates, string_attrs, domain_model, template_module=None):
    alternatives = []
    no_alternatives = []

    for enum_cls, enum in enum_candidates:
        alt_2_dm = UMLDomainModel()
        alt_2_dm.add_class(enum_cls)
        alt_2_dm.add_enumeration(enum)

        if template_module:
            generate_enumeration_attribute_question = template_module.generate_enumeration_attribute_question
        else:
            generate_enumeration_attribute_question = get_question_function('generate_enumeration_attribute_question')

        alt1_found = None
        for attr_cls, attr in string_attrs:
            attr_name_normalized = attr.name.lower().replace('type', '').replace('_', '').strip()
            enum_name_normalized = enum.name.lower().replace('type', '').replace('_', '').strip()

            if (is_similar(attr_name_normalized, enum_name_normalized) or
                is_similar(attr.type.lower(), enum.name.lower()) or
                enum_cls.name == attr_cls.name):

                alt_1_dm = UMLDomainModel()
                alt_1_dm.add_class(attr_cls)

                q, o1, o2 = generate_enumeration_attribute_question(attr_cls, attr, enum)
                config = AttributeVsEnumerationConfiguration(
                    alternative_1=(attr_cls, attr),
                    alternative_1_dm=alt_1_dm,
                    alternative_2=(enum_cls, enum),
                    alternative_2_dm=alt_2_dm,
                    question=q,
                    option_1=o1,
                    option_2=o2
                )
                config.originated_from = ('enumeration', enum)
                config.option_2_dm = domain_model

                alt1_found = attr
                alternatives.append(config)
                break

        if not alt1_found:
            attr_name = enum.name.replace('Type', '').replace('type', '').strip()
            if not attr_name:
                attr_name = enum_cls.name.lower() + 'Type'

            new_attr = UMLAttribute(attr_name, 'string', Visibility.PRIVATE)

            alt_1_dm = UMLDomainModel()
            alt_1_cls = copy.deepcopy(enum_cls)
            alt_1_cls.attributes = [a for a in alt_1_cls.attributes if a.name.lower() != attr_name.lower()]
            alt_1_cls.add_attribute(new_attr)
            alt_1_dm.add_class(alt_1_cls)

            q, o1, o2 = generate_enumeration_attribute_question(alt_1_cls, new_attr, enum)
            config = AttributeVsEnumerationConfiguration(
                alternative_1=(alt_1_cls, new_attr),
                alternative_1_dm=alt_1_dm,
                alternative_2=(enum_cls, enum),
                alternative_2_dm=alt_2_dm,
                question=q,
                option_1=o1,
                option_2=o2
            )
            config.originated_from = ('enumeration', enum)
            config.option_2_dm = domain_model

            no_alternatives.append(config)

    return alternatives, no_alternatives


def setup_attribute_vs_enumeration_patterns(domain_model, domain_model_alternatives, template_module=None):
    # Find string attributes and enumerations in current model
    string_attrs_dm = find_simple_string_attributes(domain_model)
    enum_candidates_dm = find_enumeration_candidates(domain_model)

    # Find in alternative model
    string_attrs_alt = find_simple_string_attributes(domain_model_alternatives)
    enum_candidates_alt = find_enumeration_candidates(domain_model_alternatives)

    attr_conf_alt, attr_conf_no_alt = find_attribute_alternatives(enum_candidates_alt, string_attrs_dm, domain_model, template_module)

    enum_conf_alt, enum_conf_no_alt = find_enumeration_alternatives(enum_candidates_dm, string_attrs_alt, domain_model, template_module)

    configurations_alt = attr_conf_alt + enum_conf_alt
    configurations_no_alt = attr_conf_no_alt + enum_conf_no_alt

    return configurations_alt, configurations_no_alt
