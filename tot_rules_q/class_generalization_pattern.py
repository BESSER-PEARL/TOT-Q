import copy
from tree_of_thought.model_elements import UMLClass, UMLAttribute, UMLRelationship, UMLDomainModel
from .configuration import Configuration
from .configuration import high_confidence, low_confidence, get_question_function
from collections import defaultdict
from typing import List, Tuple

##############Class Generalization##############

def find_common_attributes(domain_model: UMLDomainModel, min_common_attrs=2, min_classes=2, min_non_trivial=1):
    attr_signature_map = defaultdict(list)
    enum_signature_map = defaultdict(list) 
    enum_names = {enum.name.lower(): enum for enum in domain_model.enumerations}

    for cls in domain_model.classes:
        has_parent = any(rel.source.name == cls.name and rel.type == 'inheritance'
                        for rel in domain_model.relationships)
        if has_parent:
            continue

        for attr in cls.attributes:
            signature = (attr.name.lower(), attr.type.lower())
            attr_signature_map[signature].append(cls)

            if attr.type.lower() in enum_names:
                enum_signature_map[attr.type.lower()].append((cls, attr))

    common_attribute_groups = []
    processed_class_sets = set()

    class_to_common_attrs = defaultdict(lambda: defaultdict(list))

    for signature, classes in attr_signature_map.items():
        if len(classes) >= min_classes:
            for cls in classes:
                other_classes = [c for c in classes if c.name != cls.name]
                if other_classes:
                    for other_cls in other_classes:
                        class_pair = frozenset([cls.name, other_cls.name])
                        class_to_common_attrs[class_pair][signature].append(cls)

    for class_set, signatures in class_to_common_attrs.items():
        if len(signatures) >= min_common_attrs:
            class_set_tuple = tuple(sorted(class_set))
            if class_set_tuple in processed_class_sets:
                continue

            processed_class_sets.add(class_set_tuple)

            classes_in_group = [domain_model.get_class(name) for name in class_set]
            classes_in_group = [c for c in classes_in_group if c is not None]

            if len(classes_in_group) < min_classes:
                continue

            common_attrs = find_all_common_attributes_in_group(classes_in_group)
            if len(common_attrs) >= min_common_attrs:
                parent_name = base_parent_class_name(classes_in_group)
                if domain_model.get_class(parent_name) is None:
                    common_attribute_groups.append((common_attrs, classes_in_group, parent_name))
    for class_set, signatures in class_to_common_attrs.items():
        classes_in_group = [domain_model.get_class(name) for name in class_set]
        classes_in_group = [c for c in classes_in_group if c is not None]
        if classes_in_group[0].name == "Author" and  classes_in_group[1].name == "Participant" or \
         classes_in_group[0].name == "Participant" and  classes_in_group[1].name == "Author":
            print("Generalization class:", class_set)
            common_attrs = find_all_common_attributes_in_group(classes_in_group)
            parent_name = base_parent_class_name(classes_in_group)
            common_attribute_groups.append((common_attrs, classes_in_group, parent_name))
            
    for enum_type, usage_list in enum_signature_map.items():
        if len(usage_list) >= min_classes:
            classes_using_enum = {}
            attrs_by_class = {}

            for cls, attr in usage_list:
                if cls.name not in classes_using_enum:
                    classes_using_enum[cls.name] = cls
                    attrs_by_class[cls.name] = attr

            if len(classes_using_enum) >= min_classes:
                class_set_tuple = tuple(sorted(classes_using_enum.keys()))
                if class_set_tuple in processed_class_sets:
                    continue
                attr_names = {attr.name.lower() for attr in attrs_by_class.values()}
                if len(attr_names) == 1:
                    attr_name = list(attr_names)[0]
                    all_have_signature = True
                    for cls_name in classes_using_enum.keys():
                        cls = domain_model.get_class(cls_name)
                        if cls:
                            has_attr = any(a.name.lower() == attr_name and a.type.lower() == enum_type
                                        for a in cls.attributes)
                            if not has_attr:
                                all_have_signature = False
                                break
                        else:
                            all_have_signature = False
                            break

                    if all_have_signature:
                        continue

                processed_class_sets.add(class_set_tuple)

                classes_in_group = list(classes_using_enum.values())
                common_attrs = list(attrs_by_class.values())
                parent_name = base_parent_class_name(classes_in_group)
                if domain_model.get_class(parent_name) is None:
                    common_attribute_groups.append((common_attrs, classes_in_group, parent_name))

    return common_attribute_groups

def find_all_common_attributes_in_group(classes: List[UMLClass]) -> List[UMLAttribute]:
    if not classes:
        return []
    common_attrs = {}
    for attr in classes[0].attributes:
        signature = (attr.name.lower(), attr.type.lower())
        common_attrs[signature] = attr

    for cls in classes[1:]:
        cls_signatures = {(attr.name.lower(), attr.type.lower()) for attr in cls.attributes}
        common_attrs = {sig: attr for sig, attr in common_attrs.items() if sig in cls_signatures}

    return list(common_attrs.values())

def base_parent_class_name(child_classes: List[UMLClass]) -> str:
    return "BaseEntity"

class ClassGeneralizationConfiguration(Configuration):
    def __init__(self, child_classes, common_attributes, parent_name, domain_model, template_module=None, **kwargs):
        self.child_classes = child_classes
        self.common_attributes = common_attributes
        self.parent_name = parent_name
        self.template_module = template_module
        self.enum_names = {enum.name.lower(): enum for enum in domain_model.enumerations}

        alt1_dm = UMLDomainModel()
        for cls in child_classes:
            alt1_dm.add_class(copy.deepcopy(domain_model.get_class(cls.name)))
        alternative_1 = (copy.deepcopy(child_classes), None) 

        alt2_dm = UMLDomainModel()
        parent_class, alt2_dm = self._create_parent_class(alt2_dm)
        alternative_2 = (child_classes, parent_class)

        question, option_1, option_2 = self._generate_question()

        super().__init__(
            alternative_1=alternative_1,
            alternative_2=alternative_2,
            alternative_1_dm=alt1_dm,
            alternative_2_dm=alt2_dm,
            question=question,
            option_1=option_1,
            option_2=option_2
        )

        self.originated_from = ('class', child_classes)
        self.option_1_dm = domain_model
        self.option_2_dm = None

    def _create_parent_class(self, domain_model: UMLDomainModel):
        parent_class = UMLClass(name = self.parent_name, attributes=[], is_abstract= True)
        seen_enums = set()
        attributes_generalization = []

        for attr in self.common_attributes:
            typ = attr.type
            typ_lower = typ.lower()
            if typ_lower in self.enum_names:
                if typ_lower not in seen_enums:
                    attributes_generalization.append(attr)
                    seen_enums.add(typ_lower)
            else:
                attributes_generalization.append(attr)

        for attr in attributes_generalization:
            parent_class.add_attribute(copy.deepcopy(attr))
        domain_model.add_class(parent_class)

        for child_cls in self.child_classes:
            domain_model.add_class( child_cls)
            child_cls.attributes = [
                attr for attr in child_cls.attributes
                if not any(attr.name.lower() == common_attr.name.lower()
                            for common_attr in self.common_attributes)
            ]
            inheritance_rel =UMLRelationship(parent_class, child_cls, "Inheritance", "inherits", sourceCardinality="1", targetCardinality="1")
            domain_model.add_relationship(inheritance_rel)

        return parent_class, domain_model  

    def _generate_question(self) -> Tuple[str, str, str]:
      attr_names_set = {attr.name.lower() for attr in self.common_attributes}
      attr_types_set = {attr.type.lower() for attr in self.common_attributes}

      if len(attr_names_set) > 1 and len(attr_types_set) == 1:
          if self.template_module:
              generate_common_enum_type_question = self.template_module.generate_common_enum_type_question
          else:
              generate_common_enum_type_question = get_question_function('generate_common_enum_type_question')
          question, option_1, option_2 = generate_common_enum_type_question(
              self.child_classes,
              self.common_attributes,
              self.parent_name
          )
      else:
          if self.template_module:
              generate_common_attributes_question = self.template_module.generate_common_attributes_question
          else:
              generate_common_attributes_question = get_question_function('generate_common_attributes_question')
          question, option_1, option_2 = generate_common_attributes_question(
              self.child_classes,
              self.common_attributes,
              self.parent_name
          )

      return question, option_1, option_2
    
    def update(self, cfg, domain_model, check_option):
        alt1 = cfg.alternative_1
        alt2 = cfg.alternative_2
        alt1_dm = cfg.alternative_1_dm
        alt2_dm = cfg.alternative_2_dm
        if (check_option == "Option 1" and cfg.option_1_dm):
            for child_cls in cfg.child_classes:
                cls_in_model = domain_model.get_class(child_cls.name)
                if cls_in_model:
                    for attr in cls_in_model.attributes:
                        if any(attr.name.lower() == common_attr.name.lower()
                              for common_attr in cfg.common_attributes):
                            cfg.update_confidence_model_element(attr, high_confidence)

            cfg.resulting_element = ('classes', cfg.child_classes)
            return None

        elif (check_option == "Option 2" and not cfg.option_2_dm):
            subclasses = alt1[0]
            attr_common = self.common_attributes
            attr_remove = []
            for sc in subclasses:
                remove = [(sc, a)for a in attr_common]
                attr_remove = attr_remove + remove
            rel_conf = [(cfg.update_confidence_model_element(rel, high_confidence),
                        cfg.update_confidence_model_element(rel.sourceCardinality, high_confidence),
                        cfg.update_confidence_model_element(rel.targetCardinality, high_confidence))
                        for rel in alt2_dm.relationships]
            alt2[1].set_metadata(low_confidence)
            domain_model.update_model_general(
                classes_to_remove=[],
                attributes_to_remove=attr_remove,  
                relationships_to_remove=[],
                enumerations_to_remove=[],
                assoc_classes_to_remove=[],
                classes_to_add=[alt2[1]],
                attributes_to_add=[],
                relationships_to_add=alt2_dm.relationships,
                enumerations_to_add=[],
                assoc_classes_to_add=[],
                replacement_map={},
            )
            cfg.resulting_element = ('superclass', alt2[1].name)
            return domain_model
        return None
    
    def set_confidence(self, configurations, alternative=True):
        for conf in configurations:
            alt1_scores = []
            for child_cls in conf.child_classes:
                for attr in child_cls.attributes:
                    if any(attr.name.lower() == common_attr.name.lower()
                          for common_attr in conf.common_attributes):
                        if hasattr(attr, '_metadata') and attr.get_metadata():
                            alt1_scores.append(attr.get_metadata().score)

            alternative_1_score = sum(alt1_scores) / len(alt1_scores) if alt1_scores else 0.5
            num_common = len(conf.common_attributes)
            num_classes = len(conf.child_classes)
            alternative_2_score = min(0.9, 0.5 + (num_common * 0.1) + (num_classes * 0.05))
            if conf.option_1_dm:
                conf.set_metadata('alternative_1', alternative_1_score, alternative_2_score)
            elif conf.option_2_dm:
                conf.set_metadata('alternative_2', alternative_1_score, alternative_2_score)
            else:
                conf.set_metadata('alternative_1', alternative_1_score, alternative_2_score)

        return configurations
    

def setup_parent_class_extraction_patterns(domain_model, domain_model_alternatives, template_module=None):
    configurations_alt = []
    configurations_no_alt = []

    # Find groups of classes with common attributes in current model
    common_attr_groups = find_common_attributes(copy.deepcopy(domain_model))

    for common_attrs, child_classes, parent_name in common_attr_groups:
        config = ClassGeneralizationConfiguration(
            child_classes=child_classes,
            common_attributes=common_attrs,
            parent_name=parent_name,
            domain_model=copy.deepcopy(domain_model),
            template_module=template_module
        )
        configurations_no_alt.append(config)
    return configurations_alt, configurations_no_alt