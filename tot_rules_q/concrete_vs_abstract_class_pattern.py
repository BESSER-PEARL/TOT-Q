import copy
from tree_of_thought.model_elements import UMLClass, UMLAttribute, UMLEnumeration, Visibility, UMLRelationship, UMLDomainModel, UMLAssociationClass
from configuration import Configuration
from configuration import split_camel_case, correct_article, plural, name_format, is_similar
from configuration import high_confidence, low_confidence
from collections import Counter
from template_questions import generate_abstract_superclass_question, generate_concrete_superclass_question


##############Concrete Class vs Abstract Class##############
###Concrete Class vs Abstract Class - concrete identified
def find_concrete_superclasses(domain_model):
    concrete_superclasses = []
    for uml_class in domain_model.classes:
        if uml_class.is_abstract is False:  # Concrete class
            # Check if it's a superclass (has child classes)
            subclasses = [rel.target for rel in domain_model.relationships if rel.type.lower() == "inheritance" and rel.source.name == uml_class.name]
            if subclasses:
                concrete_superclasses.append((uml_class, subclasses))
    return concrete_superclasses

###Concrete Class vs Abstract Class - abstract identified
def find_abstract_superclasses(domain_model):
    abstract_superclasses = []
    for uml_class in domain_model.classes:
        if uml_class.is_abstract is True:  # Abstract class
            # Check if it's a superclass (has child classes)
            subclasses = [rel.target for rel in domain_model.relationships if rel.type.lower() == "inheritance" and rel.source.name == uml_class.name]
            if subclasses:
                abstract_superclasses.append((uml_class, subclasses))
    return abstract_superclasses


class ConcreteVsAbstractClassConfiguration(Configuration):
    def update(self,cfg, domain_model, check_option):
        alt1 = cfg.alternative_1
        alt2 = cfg.alternative_2
        alt1_dm = cfg.alternative_1_dm
        alt2_dm = cfg.alternative_2_dm
        if (check_option == "Option 1" and cfg.option_1_dm) or \
            (check_option == "Option 2" and cfg.option_2_dm):
            if check_option == "Option 1":
                cfg.update_confidence_model_element(domain_model.get_class(alt1[0].name), high_confidence)
            else:
                cfg.update_confidence_model_element(domain_model.get_class(alt2[0].name), high_confidence)
            return None
        elif check_option == "Option 1" and not cfg.option_1_dm:
            cfg.update_confidence_model_element(alt1[0], high_confidence)
            domain_model.update_model_general(
                classes_to_remove=[alt2[0]],
                attributes_to_remove=[],  
                relationships_to_remove=[],
                enumerations_to_remove=[],
                assoc_classes_to_remove=[],
                classes_to_add=[alt1[0]],
                attributes_to_add=[],
                relationships_to_add=[],
                enumerations_to_add=[],
                assoc_classes_to_add=[],
                replacement_map={alt2[0]: alt1[0]},
            )
            return domain_model
        elif check_option == "Option 2" and not cfg.option_2_dm:
            cfg.update_confidence_model_element(alt2[0], high_confidence)
            domain_model.update_model_general(
                classes_to_remove=[alt1[0]],
                attributes_to_remove=[],  
                relationships_to_remove=[],
                enumerations_to_remove=[],
                assoc_classes_to_remove=[],
                classes_to_add=[alt2[0]],
                attributes_to_add=[],
                relationships_to_add=[],
                enumerations_to_add=[],
                assoc_classes_to_add=[],
                replacement_map={alt1[0]: alt2[0]},
            )
            return domain_model
        

    def set_confidence(self, configurations, alternative = True):
    #def confidence_configuration_abstract_class(configurations, alternative = True):
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


###Concrete Class vs Abstract Class - concrete identified
def find_abstract_class_alternatives(concrete_class_alternatives, abstract_class_alternatives, domain_model):
    alternatives = []
    no_alternatives = []
    for concrete_class in concrete_class_alternatives:
        concrete_class_name = concrete_class[0].name
        concrete_class_dm = UMLDomainModel()
        concrete_class_dm.add_class(concrete_class[0])
        subclasses = [concrete_class_dm.add_class(sc) for sc in concrete_class[1]]
        relationships =[concrete_class_dm.add_relationship(
                        UMLRelationship(concrete_class[0], sc, "Inheritance", "inherits", sourceCardinality="1", targetCardinality="1"))
                        for sc in concrete_class[1]]
        #inheritance
        q, o1, o2 = generate_concrete_superclass_question(concrete_class[0], concrete_class[1])
        #config = Configuration(alternative_1= concrete_class, alternative_1_dm= concrete_class_dm, question=q, option_1=o1, option_2=o2)
        config = ConcreteVsAbstractClassConfiguration(alternative_1= concrete_class, alternative_1_dm= concrete_class_dm, question=q, option_1=o1, option_2=o2)
        config.option_1_dm = domain_model
        alt2_found = None
        for abstract_class in abstract_class_alternatives:
            abstract_class_name = abstract_class[0].name
            if is_similar(concrete_class_name, abstract_class_name):
                abstract_class_dm = UMLDomainModel()
                abstract_class_dm.add_class(abstract_class[0])
                subclasses = [abstract_class_dm.add_class(sc) for sc in abstract_class[1]]
                relationships =[abstract_class_dm.add_relationship(
                        UMLRelationship(abstract_class[0], sc, "Inheritance", "inherits", sourceCardinality="1", targetCardinality="1"))
                        for sc in abstract_class[1]]
                
                config.add_alternative_2(alternative_2= abstract_class, alternative_2_dm= abstract_class_dm)
                
                alternatives.append(config)
                alt2_found = abstract_class
                break
        if not alt2_found:
            abstract_class_dm = UMLDomainModel()
            new_cls = copy.deepcopy(concrete_class[0])
            new_cls.is_abstract = True
            abstract_class_dm.add_class(new_cls)
            new_subclasses = [copy.deepcopy(sc) for sc in concrete_class[1]]
            subclasses = [abstract_class_dm.add_class(sc) for sc in concrete_class[1]]
            relationships =[abstract_class_dm.add_relationship(
                        UMLRelationship(concrete_class[0], sc, "Inheritance", "inherits", sourceCardinality="1", targetCardinality="1"))
                        for sc in concrete_class[1]]
            alt2 = (new_cls, new_subclasses)
            config.add_alternative_2(alternative_2= alt2, alternative_2_dm= abstract_class_dm)
            no_alternatives.append(config)
    return alternatives, no_alternatives

###Concrete Class vs Abstract Class - abstract identified
def find_concrete_class_alternatives(concrete_class_alternatives, abstract_class_alternatives, domain_model):
    alternatives = []
    no_alternatives = []
    for abstract_class in abstract_class_alternatives:
        abstract_class_name = abstract_class[0].name
        abstract_class_dm = UMLDomainModel()
        abstract_class_dm.add_class(abstract_class[0])
        subclasses = [abstract_class_dm.add_class(sc) for sc in abstract_class[1]]
        relationships =[abstract_class_dm.add_relationship(
                        UMLRelationship(abstract_class[0], sc, "Inheritance", "inherits", sourceCardinality="1", targetCardinality="1"))
                        for sc in abstract_class[1]]
        q, o1, o2 = generate_abstract_superclass_question(abstract_class[0], abstract_class[1])
        #config = Configuration(alternative_2= abstract_class, alternative_2_dm= abstract_class_dm, question=q, option_1=o1, option_2=o2)
        config = ConcreteVsAbstractClassConfiguration(alternative_2= abstract_class, alternative_2_dm= abstract_class_dm, question=q, option_1=o1, option_2=o2)
        config.option_2_dm = domain_model
        alt1_found = None
        for concrete_class in concrete_class_alternatives:
            concrete_class_name = concrete_class[0].name
            if is_similar(abstract_class_name, concrete_class_name):
                concrete_class_dm = UMLDomainModel()
                concrete_class_dm.add_class(concrete_class[0])
                subclasses = [concrete_class_dm.add_class(sc) for sc in concrete_class[1]]
                relationships =[concrete_class_dm.add_relationship(
                        UMLRelationship(concrete_class[0], sc, "Inheritance", "inherits", sourceCardinality="1", targetCardinality="1"))
                        for sc in concrete_class[1]]
                
                config.add_alternative_1(alternative_1= concrete_class, alternative_1_dm= concrete_class_dm)
                
                alternatives.append(config)
                alt1_found = concrete_class
                break
        if not alt1_found:
            concrete_class_dm = UMLDomainModel()
            new_cls = copy.deepcopy(abstract_class[0])
            new_cls.is_abstract = False
            concrete_class_dm.add_class(new_cls)
            new_subclasses = [copy.deepcopy(sc) for sc in abstract_class[1]]
            subclasses = [concrete_class_dm.add_class(sc) for sc in abstract_class[1]]
            relationships =[concrete_class_dm.add_relationship(
                        UMLRelationship(abstract_class[0], sc, "Inheritance", "inherits", sourceCardinality="1", targetCardinality="1"))
                        for sc in abstract_class[1]]
            alt1 = (new_cls, new_subclasses)
            config.add_alternative_1(alternative_1= alt1, alternative_1_dm= concrete_class_dm)
            no_alternatives.append(config)
                
    return alternatives, no_alternatives


def setup_concrete_vs_abstract_class_patterns(domain_model, domain_model_alternatives):
    concrete_class_dm = find_concrete_superclasses(domain_model)
    abstract_class_dm = find_abstract_superclasses(domain_model)
    # Find concrete and abstract class alternatives
    concrete_class_alternatives = find_concrete_superclasses(domain_model_alternatives)
    abstract_class_alternatives = find_abstract_superclasses(domain_model_alternatives)
    
    # Generate alternative configurations for concrete and abstract classes
    concrete_class_conf_alt, concrete_class_conf_no_alt = find_concrete_class_alternatives(concrete_class_alternatives, abstract_class_dm, domain_model)
    abstract_class_conf_alt, abstract_class_conf_no_alt = find_abstract_class_alternatives(concrete_class_dm, abstract_class_alternatives, domain_model)
    
    # Combine configurations
    configurations_alt = concrete_class_conf_alt + abstract_class_conf_alt
    configurations_no_alt = concrete_class_conf_no_alt + abstract_class_conf_no_alt
    return configurations_alt, configurations_no_alt
