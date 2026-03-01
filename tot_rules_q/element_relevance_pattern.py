import copy
from tree_of_thought.model_elements import UMLClass, UMLAttribute, UMLEnumeration, Visibility, UMLRelationship, UMLDomainModel
from .configuration import Configuration
from .configuration import split_camel_case, correct_article, plural, name_format, is_similar
from .configuration import high_confidence, low_confidence, get_question_function
from tot_rules_q.rule_agent_config import VERY_LOW_CONFIDENCE_THRESHOLD


class ElementRelevanceConfiguration(Configuration):

    def __init__(self, element, element_type, parent_class=None, template_module=None, **kwargs):
        self.element = element
        self.element_type = element_type
        self.parent_class = parent_class
        self.template_module = template_module
        question, option_1, option_2 = self._generate_relevance_question(element, element_type, parent_class)
        alt1_dm, alt2_dm = self._create_alternatives(element, element_type, parent_class)

        super().__init__(
            alternative_1=(element, "keep"),
            alternative_1_dm=alt1_dm,
            alternative_2=(element, "remove"),
            alternative_2_dm=alt2_dm,
            question=question,
            option_1=option_1,
            option_2=option_2,
            **kwargs
        )
        self.option_1_dm = None
        self.option_2_dm = None

    def _generate_relevance_question(self, element, element_type, parent_class):
        if element_type == "class":
            if self.template_module:
                generate_class_relevance_question = self.template_module.generate_class_relevance_question
            else:
                generate_class_relevance_question = get_question_function('generate_class_relevance_question')
            question, option_1, option_2 = generate_class_relevance_question(element)
        else: 
            if self.template_module:
                generate_attribute_relevance_question = self.template_module.generate_attribute_relevance_question
            else:
                generate_attribute_relevance_question = get_question_function('generate_attribute_relevance_question')
            question, option_1, option_2 = generate_attribute_relevance_question(parent_class, element)

        return question, option_1, option_2

    def _create_alternatives(self, element, element_type, parent_class):
        """Create alternative domain models for keeping vs removing element."""
        alt1_dm = UMLDomainModel()
        alt2_dm = UMLDomainModel()

        return alt1_dm, alt2_dm

    def update(self, cfg, domain_model, check_option):
        if check_option == "Option 1":
            cfg.update_confidence_model_element(self.element, high_confidence)
            cfg.resulting_element = (self.element_type, self.element)
            return None

        elif check_option == "Option 2":
            if self.element_type == "class":
                class_to_remove = domain_model.get_class(self.element.name)

                if class_to_remove:
                    rels_to_remove = [
                        rel for rel in domain_model.relationships
                        if rel.source.name == self.element.name
                        or rel.target.name == self.element.name
                    ]
                    domain_model.update_model_general(
                        classes_to_remove=[class_to_remove],
                        relationships_to_remove=rels_to_remove,
                        attributes_to_remove=[],
                        enumerations_to_remove=[],
                        assoc_classes_to_remove=[],
                        classes_to_add=[],
                        attributes_to_add=[],
                        relationships_to_add=[],
                        enumerations_to_add=[],
                        assoc_classes_to_add=[],
                        replacement_map={}
                    )
                    cfg.resulting_element = ('removed_class', class_to_remove)
                    return domain_model

            else:
                parent = domain_model.get_class(self.parent_class.name)

                if parent:
                    domain_model.update_model_general(
                        classes_to_remove=[],
                        relationships_to_remove=[],
                        attributes_to_remove=[(parent, self.element)],
                        enumerations_to_remove=[],
                        assoc_classes_to_remove=[],
                        classes_to_add=[],
                        attributes_to_add=[],
                        relationships_to_add=[],
                        enumerations_to_add=[],
                        assoc_classes_to_add=[],
                        replacement_map={}
                    )
                    cfg.resulting_element = ('removed_attribute', self.element)
                    return domain_model

        return None


def find_low_confidence_classes(domain_model: UMLDomainModel, threshold=VERY_LOW_CONFIDENCE_THRESHOLD):
    low_conf_classes = []

    for cls in domain_model.classes:
        if hasattr(cls, '_metadata') and cls.get_metadata():
            score = cls.get_metadata().score
            if score < threshold:
                low_conf_classes.append(cls)

    low_conf_classes_filtered = []
    for cls in low_conf_classes:
        num_rels = sum(1 for rel in domain_model.relationships if rel.source.name == cls.name or rel.target.name == cls.name)
        if num_rels < 2:
            low_conf_classes_filtered.append(cls)

    return low_conf_classes_filtered


def find_low_confidence_attributes(domain_model: UMLDomainModel, threshold=VERY_LOW_CONFIDENCE_THRESHOLD):
    low_conf_attrs = []
    enum_names = {enum.name for enum in domain_model.enumerations}

    for cls in domain_model.classes:
        for attr in cls.attributes:
            if attr.type in enum_names:
                continue

            if hasattr(attr, '_metadata') and attr.get_metadata():
                score = attr.get_metadata().score
                if score < threshold:
                    low_conf_attrs.append((cls, attr))

    return low_conf_attrs

def setup_element_relevance_patterns(domain_model, domain_model2, threshold=VERY_LOW_CONFIDENCE_THRESHOLD, element_types=None, template_module=None):
    global VERY_LOW_CONFIDENCE_THRESHOLD
    threshold = VERY_LOW_CONFIDENCE_THRESHOLD
    if element_types is None:
        element_types = ["class", "attribute"]

    configurations_alt = []
    configurations_no_alt = []
    if "class" in element_types:
        low_conf_classes = find_low_confidence_classes(domain_model, threshold)
        for cls in low_conf_classes:
            config = ElementRelevanceConfiguration(
                element=cls,
                element_type="class",
                template_module=template_module
            )
            cls_score = cls.get_metadata().score if cls.get_metadata() else 0.0
            config.set_metadata('alternative_1', cls_score, cls_score)
            config.originated_from = ('class', cls)
            configurations_alt.append(config)
    if "attribute" in element_types:
        low_conf_attrs = find_low_confidence_attributes(domain_model, threshold)
        for parent_cls, attr in low_conf_attrs:
            config = ElementRelevanceConfiguration(
                element=attr,
                element_type="attribute",
                parent_class=parent_cls,
                template_module=template_module
            )
            attr_score = attr.get_metadata().score if attr.get_metadata() else 0.0
            config.set_metadata('alternative_1', attr_score, attr_score)
            config.originated_from = ('attribute', attr)


            configurations_alt.append(config)

    return configurations_alt, configurations_no_alt