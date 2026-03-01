import copy
from tree_of_thought.model_elements import UMLClass, UMLAttribute, UMLEnumeration, Visibility, UMLRelationship, UMLDomainModel
from .configuration import Configuration
from .configuration import split_camel_case, correct_article, plural, name_format, is_similar
from .configuration import high_confidence, low_confidence, get_question_function
from .class_vs_attribute_pattern import ClassVsAttributeConfiguration, setup_class_vs_attribute_patterns
from .attribute_vs_enumeration_pattern import AttributeVsEnumerationConfiguration


class ConceptDecisionConfiguration(Configuration):
    def __init__(self, initial_class, parent_class, potential_attr, domain_model,
                 step1_pattern=None, step2_pattern=None, template_module=None, **kwargs):
        super().__init__(**kwargs)

        self.step = 1
        self.step2_needed = False  
        self.domain_model = domain_model
        self.initial_class = initial_class
        self.parent_class = parent_class
        self.potential_attr = potential_attr
        self.template_module = template_module

        self.step1_config = step1_pattern
        self.step2_config = step2_pattern

        if self.step1_config is None:
            self._create_step1_config(initial_class, parent_class, potential_attr, domain_model)

        if self.step1_config:
            self.question = self.step1_config.question
            self.option_1 = self.step1_config.option_1
            self.option_2 = self.step1_config.option_2
            if not hasattr(self, 'originated_from') or self.originated_from is None:
                self.originated_from = self.step1_config.originated_from

    def _create_step1_config(self, initial_class, parent_class, potential_attr, domain_model):
        if self.template_module:
            generate_class_with_single_association_question = self.template_module.generate_class_with_single_association_question
        else:
            generate_class_with_single_association_question = get_question_function('generate_class_with_single_association_question')

        rel = next(
            (rel for rel in domain_model.relationships
             if rel.source.name == initial_class.name or rel.target.name == initial_class.name),
            None
        )

        if rel:
            q, o1, o2 = generate_class_with_single_association_question(initial_class, rel)
            alt1_dm = UMLDomainModel()
            alt1_dm.add_class(copy.deepcopy(rel.source))
            alt1_dm.add_class(copy.deepcopy(rel.target))
            alt1_dm.add_relationship(copy.deepcopy(rel))

            alt2_dm = UMLDomainModel()
            alt2_cls = copy.deepcopy(parent_class)
            if not any(a.name == potential_attr.name for a in alt2_cls.attributes):
                alt2_cls.add_attribute(potential_attr)
            alt2_dm.add_class(alt2_cls)

            self.step1_config = ClassVsAttributeConfiguration(
                alternative_1=(initial_class, rel),
                alternative_1_dm=alt1_dm,
                alternative_2=(parent_class, potential_attr),
                alternative_2_dm=alt2_dm,
                question=q,
                option_1=o1,
                option_2=o2
            )

            self.step1_config.originated_from = ('class', initial_class)
            self.step1_config.option_1_dm = domain_model

    def _create_step2_config(self, domain_model):
        """Create Step 2 configuration by delegating to AttributeVsEnumerationConfiguration."""

        parent_class = self.parent_class
        attribute = self.potential_attr

        enum_name = name_format(attribute.name.replace('_', ' ').title())
        if not enum_name.endswith('Type'):
            enum_name = enum_name + 'Type'

        literals = ['LITERAL_1', 'LITERAL_2', 'LITERAL_3']
        new_enum = UMLEnumeration(enum_name, literals)

        if self.template_module:
            generate_string_attribute_question = self.template_module.generate_string_attribute_question
        else:
            generate_string_attribute_question = get_question_function('generate_string_attribute_question')
        q, o1, o2 = generate_string_attribute_question(parent_class, attribute, new_enum)

        alt1_dm = UMLDomainModel()
        alt1_dm.add_class(parent_class)

        alt2_dm = UMLDomainModel()
        alt2_dm.add_class(parent_class)
        alt2_dm.add_enumeration(new_enum)

        self.step2_config = AttributeVsEnumerationConfiguration(
            alternative_1=(parent_class, attribute),
            alternative_1_dm=alt1_dm,
            alternative_2=(parent_class, new_enum),
            alternative_2_dm=alt2_dm,
            question=q,
            option_1=o1,
            option_2=o2
        )

        self.step2_config.originated_from = ('attribute', attribute)
        self.step2_config.option_1_dm = domain_model  # Attribute exists (was just created)

    def get_pattern_name(self):
        if self.step == 2 and self.step2_config:
            delegated_pattern = self.step2_config.__class__.__name__.replace('Configuration', '')
            return f"ConceptDecision({delegated_pattern})"
        elif self.step1_config:
            delegated_pattern = self.step1_config.__class__.__name__.replace('Configuration', '')
            return f"ConceptDecision({delegated_pattern})"
        else:
            # Fallback
            return "ConceptDecision"

    def is_complete(self):
        return not self.step2_needed

    def update(self, cfg, domain_model, check_option):
        if self.step == 1:
            return self._process_step1(cfg, domain_model, check_option)
        elif self.step == 2:
            return self._process_step2(cfg, domain_model, check_option)
        else:
            return domain_model

    def _process_step1(self, cfg, domain_model, check_option):
        is_enum_entry = (hasattr(cfg, 'originated_from') and cfg.originated_from and cfg.originated_from[0] == 'enumeration')
        if check_option == "Option 1":
            if is_enum_entry:
                alternative_1 = self.step1_config.alternative_1
                alternative_1_dm = self.step1_config.alternative_1_dm
                alternative_2 = self.step2_config.alternative_2
                alternative_2_dm = self.step2_config.alternative_2_dm
                cfg.alternative_1 = alternative_1
                cfg.alternative_1_dm = alternative_1_dm
                cfg.alternative_2 = alternative_2
                cfg.alternative_2_dm = alternative_2_dm
                dm2_test = self.step1_config.update(cfg, domain_model, check_option)

                return dm2_test
            else:
                result = self.step1_config.update(self.step1_config, domain_model, check_option)
                self.resulting_element = self.step1_config.resulting_element
                self.step2_needed = False
                return result

        elif check_option == "Option 2":
            if is_enum_entry:
                self.step = 2
                self.step2_needed = True
                if self.step2_config is None:
                    self._create_step2_config(domain_model)
                self.question = self.step2_config.question
                self.option_1 = self.step2_config.option_1
                self.option_2 = self.step2_config.option_2

                return None
            else:
                result = self.step1_config.update(self.step1_config, domain_model, check_option)
                self.resulting_element = self.step1_config.resulting_element
                self.step = 2
                self.step2_needed = True
                if self.step2_config is None:
                    self._create_step2_config(domain_model)
                self.question = self.step2_config.question
                self.option_1 = self.step2_config.option_1
                self.option_2 = self.step2_config.option_2
                return result

    def _process_step2(self, cfg, domain_model, check_option):
        """Process Step 2 by delegating to AttributeVsEnumerationConfiguration."""
        result = self.step2_config.update(self.step2_config, domain_model, check_option)
        self.resulting_element = self.step2_config.resulting_element
        self.step2_needed = False
        if hasattr(cfg, 'originated_from') and cfg.originated_from and self.resulting_element:
            origin_type = cfg.originated_from[0]
            final_type = self.resulting_element[0]
            if origin_type != final_type:
                return domain_model
        udpated_result = result
        return udpated_result


    def get_question(self, domain, domain_model):
        self.step1_config.llm_template_filler = None
        if self.step == 2 and "enum" not in self.step2_config.originated_from[0].lower():
            return self.step2_config.get_question(domain, domain_model)
        elif self.step == 1 and \
            "attr" in self.originated_from[0].lower() and \
            "class" not in self.step1_config.originated_from[0].lower():
            self.step1_config.llm_template_filler = 'attribute'
            return self.step1_config.get_question(domain, domain_model)
        elif self.step == 1 and \
            "enum" in self.originated_from[0].lower() and \
            "class" not in self.step1_config.originated_from[0].lower():
            self.step1_config.llm_template_filler = 'enumeration'
            return self.step1_config.get_question(domain, domain_model)
        else:
            return (self.question, self.option_1, self.option_2)

def find_concept_decision_candidates(domain_model):
    candidates = []
    for cls in domain_model.classes:
        rel_count = sum(
            1 for rel in domain_model.relationships
            if rel.source.name == cls.name or rel.target.name == cls.name
        )

        if 1 <= rel_count <= 2 and len(cls.attributes) <= 3:
            parent_rel = next(
                (rel for rel in domain_model.relationships
                 if rel.target.name == cls.name and
                    domain_model.compare_relationship_type(rel.type, 'association')),
                None
            )
            if parent_rel:
                parent_class = parent_rel.source
                attr_name = cls.name.lower()
                potential_attr = UMLAttribute(attr_name, 'string', Visibility.PRIVATE)
                candidates.append((cls, parent_class, potential_attr))
    return candidates

from .attribute_vs_enumeration_pattern import setup_attribute_vs_enumeration_patterns
from .modeling_patterns import confidence_configuration_class_vs_attribute
from .modeling_patterns import confidence_configuration_attribute_vs_enumeration

def setup_concept_decision_patterns(domain_model, domain_model_alternatives, template_module=None):
    configurations_alt = []
    configurations_no_alt = []
    class_vs_attr_alt, class_vs_attr_no_alt = setup_class_vs_attribute_patterns(
        domain_model, domain_model_alternatives, template_module
    )
    class_vs_attr_alt = confidence_configuration_class_vs_attribute(class_vs_attr_alt, alternative=True)
    class_vs_attr_no_alt = confidence_configuration_class_vs_attribute(class_vs_attr_no_alt, alternative=False)
    all_class_vs_attr = class_vs_attr_alt + class_vs_attr_no_alt
    attr_vs_enum_alt, attr_vs_enum_no_alt = setup_attribute_vs_enumeration_patterns(
        domain_model, domain_model_alternatives, template_module
    )
    attr_vs_enum_alt = confidence_configuration_attribute_vs_enumeration(attr_vs_enum_alt, alternative=True)
    attr_vs_enum_no_alt = confidence_configuration_attribute_vs_enumeration(attr_vs_enum_no_alt, alternative=False)
    all_attr_vs_enum = attr_vs_enum_alt + attr_vs_enum_no_alt
    class_vs_attr_by_element = {}

    for config in all_class_vs_attr:
        is_alt = config in class_vs_attr_alt
        if config.originated_from:
            elem_type, elem = config.originated_from
            if elem_type == 'class':
                class_vs_attr_by_element[elem.name] = (config, is_alt)
            elif elem_type == 'attribute':
                parent_name = config.alternative_2[0].name  # parent class
                attr_name = elem.name
                class_vs_attr_by_element[f"{parent_name}.{attr_name}"] = (config, is_alt)
    attr_vs_enum_by_element = {}

    for config in all_attr_vs_enum:
        is_alt = config in attr_vs_enum_alt
        if config.originated_from:
            elem_type, elem = config.originated_from
            if elem_type == 'attribute':
                parent_name = config.alternative_1[0].name
                attr_name = elem.name
                attr_vs_enum_by_element[f"{parent_name}.{attr_name}"] = (config, is_alt)
            elif elem_type == 'enumeration':
                attr_vs_enum_by_element[elem.name] = (config, is_alt)

    used_class_vs_attr = set()
    used_attr_vs_enum = set()
    for key, (class_config, is_alt) in class_vs_attr_by_element.items():
        if '.' in key:
            continue 
        if class_config.alternative_2:
            potential_attr = class_config.alternative_2[1]
            parent_class = class_config.alternative_2[0]
            attr_key = f"{parent_class.name}.{potential_attr.name}"
            used_class_vs_attr.add(id(class_config))
            if attr_key in attr_vs_enum_by_element:
                enum_config, enum_is_alt = attr_vs_enum_by_element[attr_key]
                used_attr_vs_enum.add(id(enum_config))

                concept_config = ConceptDecisionConfiguration(
                    initial_class=class_config.alternative_1[0],
                    parent_class=parent_class,
                    potential_attr=potential_attr,
                    domain_model=domain_model,
                    step1_pattern=class_config,
                    step2_pattern=enum_config,
                    template_module=template_module
                )

                concept_config.option_1_dm = class_config.option_1_dm
                concept_config.option_2_dm = class_config.option_2_dm

                if is_alt:
                    configurations_alt.append(concept_config)
                else:
                    configurations_no_alt.append(concept_config)
            else:
                concept_config = ConceptDecisionConfiguration(
                    initial_class=class_config.alternative_1[0],
                    parent_class=parent_class,
                    potential_attr=potential_attr,
                    domain_model=domain_model,
                    step1_pattern=class_config,
                    step2_pattern=None,
                    template_module=template_module
                )
                concept_config.option_1_dm = class_config.option_1_dm
                concept_config.option_2_dm = class_config.option_2_dm

                if is_alt:
                    configurations_alt.append(concept_config)
                else:
                    configurations_no_alt.append(concept_config)
    for key, (attr_config, is_alt) in class_vs_attr_by_element.items():
        if '.' not in key:
            continue
        if id(attr_config) in used_class_vs_attr:
            continue
        parent_class = attr_config.alternative_2[0]
        attribute = attr_config.alternative_2[1]
        used_class_vs_attr.add(id(attr_config))
        if key in attr_vs_enum_by_element:
            enum_config, enum_is_alt = attr_vs_enum_by_element[key]
            used_attr_vs_enum.add(id(enum_config))
            concept_config = ConceptDecisionConfiguration(
                initial_class=None,
                parent_class=parent_class,
                potential_attr=attribute,
                domain_model=domain_model,
                step1_pattern=attr_config,
                step2_pattern=enum_config,
                template_module=template_module
            )

            concept_config.originated_from = ('attribute', attribute)
            concept_config.option_1_dm = attr_config.option_1_dm
            concept_config.option_2_dm = attr_config.option_2_dm

            if is_alt:
                configurations_alt.append(concept_config)
            else:
                configurations_no_alt.append(concept_config)
        else:
            concept_config = ConceptDecisionConfiguration(
                initial_class=None,
                parent_class=parent_class,
                potential_attr=attribute,
                domain_model=domain_model,
                step1_pattern=attr_config,
                step2_pattern=None,
                template_module=template_module
            )

            concept_config.originated_from = ('attribute', attribute)
            concept_config.option_1_dm = attr_config.option_1_dm
            concept_config.option_2_dm = attr_config.option_2_dm

            if is_alt:
                configurations_alt.append(concept_config)
            else:
                configurations_no_alt.append(concept_config)
    for key, (enum_config, is_alt) in attr_vs_enum_by_element.items():
        if '.' in key:
            continue
        if id(enum_config) in used_attr_vs_enum:
            continue
        if enum_config.alternative_1:
            attribute = enum_config.alternative_1[1]
            parent_class = enum_config.alternative_1[0]
            attr_key = f"{parent_class.name}.{attribute.name}"

            used_attr_vs_enum.add(id(enum_config))

            if attr_key in class_vs_attr_by_element:
                class_config, class_is_alt = class_vs_attr_by_element[attr_key]
                used_class_vs_attr.add(id(class_config))
                concept_config = ConceptDecisionConfiguration(
                    initial_class=None,
                    parent_class=parent_class,
                    potential_attr=attribute,
                    domain_model=domain_model,
                    step1_pattern=enum_config,
                    step2_pattern=class_config,
                    template_module=template_module
                )
                concept_config.originated_from = ('enumeration', enum_config.alternative_2[1])
                concept_config.option_1_dm = enum_config.option_1_dm
                concept_config.option_2_dm = enum_config.option_2_dm

                if is_alt:
                    configurations_alt.append(concept_config)
                else:
                    configurations_no_alt.append(concept_config)
            else:
                enum = enum_config.alternative_2[1]
                if hasattr(enum, '_metadata') and enum.get_metadata():
                    if not hasattr(attribute, '_metadata') or not attribute.get_metadata():
                        attribute._metadata = copy.deepcopy(enum._metadata)
                class_name = name_format(attribute.name.replace('_', ' ').title())
                synthetic_class = UMLClass(class_name, [])
                synthetic_rel = UMLRelationship(
                    parent_class, synthetic_class, "Association", "has",
                    sourceCardinality="1", targetCardinality="1"
                )
                if template_module:
                    generate_attribute_question = template_module.generate_attribute_question
                else:
                    generate_attribute_question = get_question_function('generate_attribute_question')
                q, o1, o2 = generate_attribute_question(parent_class, attribute)
                alt1_dm = UMLDomainModel()
                alt1_dm.add_class(copy.deepcopy(parent_class))
                alt1_dm.add_class(synthetic_class)
                alt1_dm.add_relationship(synthetic_rel)
                alt2_dm = UMLDomainModel()
                alt2_cls = copy.deepcopy(parent_class)
                alt2_cls.add_attribute(attribute)
                alt2_dm.add_class(alt2_cls)

                new_class_vs_attr = ClassVsAttributeConfiguration(
                    alternative_1=(synthetic_class, synthetic_rel),
                    alternative_1_dm=alt1_dm,
                    alternative_2=(parent_class, attribute),
                    alternative_2_dm=alt2_dm,
                    question=q,
                    option_1=o1,
                    option_2=o2
                )
                new_class_vs_attr.originated_from = ('attribute', attribute)
                new_class_vs_attr.option_1_dm = None
                new_class_vs_attr.option_2_dm = domain_model
                if hasattr(enum_config, '_metadata') and enum_config.get_metadata():
                    new_class_vs_attr._metadata = copy.deepcopy(enum_config._metadata)

                concept_config = ConceptDecisionConfiguration(
                    initial_class=None,
                    parent_class=parent_class,
                    potential_attr=attribute,
                    domain_model=domain_model,
                    step1_pattern=new_class_vs_attr,
                    step2_pattern=enum_config,
                    template_module=template_module
                )
                concept_config.originated_from = ('enumeration', enum_config.alternative_2[1])
                concept_config.option_1_dm = new_class_vs_attr.option_1_dm
                concept_config.option_2_dm = new_class_vs_attr.option_2_dm
                if is_alt:
                    configurations_alt.append(concept_config)
                else:
                    configurations_no_alt.append(concept_config)
    return configurations_alt, configurations_no_alt
