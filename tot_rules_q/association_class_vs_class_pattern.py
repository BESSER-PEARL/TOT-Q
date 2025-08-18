import copy
from tree_of_thought.model_elements import UMLClass, UMLAttribute, UMLEnumeration, Visibility, UMLRelationship, UMLDomainModel, UMLAssociationClass
from configuration import Configuration
from configuration import split_camel_case, correct_article, plural, name_format, is_similar
from configuration import high_confidence, low_confidence
from collections import Counter
from template_questions import generate_many_to_many_association_class_question

##############Association Class vs Class##############
###Association Class vs Class: many to many relationship and intermediate class
def find_many_to_many_relationships(domain_model):
    results = []
    relations = []
    for rel in domain_model.relationships:
        if "*" in rel.sourceCardinality and "*" in rel.targetCardinality:
            relations.append(rel)
    source_relation_classes = []
    target_relation_classes = []

    for rel in relations:
        uml_class = rel.source
        source_relation_classes = [rel.target.name if rel.source.name == uml_class.name else rel.source.name
        for rel in domain_model.relationships
        if rel.source.name == uml_class.name or rel.target.name == uml_class.name]
    #for r in results:
        uml_class = rel.target
        target_relation_classes = [rel.target.name if rel.source.name == uml_class.name else rel.source.name
        for rel in domain_model.relationships
        if rel.source.name == uml_class.name or rel.target.name == uml_class.name]
        possible_association_class = [s for s in source_relation_classes if s in target_relation_classes]
        for p in possible_association_class:
            association_class_relationships = [rel for rel in domain_model.relationships
            if rel.source.name == p or rel.target.name == p]
            if len(association_class_relationships) == 2:
                results.append((rel, domain_model.get_class(p)))
    return results

def find_intermediate_class(domain_model):
    results = []
    possible_association_class = []
    for cls in domain_model.classes:
        #source_relation_classes = [rel.target.name if rel.source.name == cls.name else rel.source.name
        source_relation_classes = [rel
        for rel in domain_model.relationships
        if rel.source.name == cls.name and "*" in rel.sourceCardinality and
        (domain_model.compare_relationship_type(rel.type, 'Association') or 
         domain_model.compare_relationship_type(rel.type, 'Composition'))]
        #target_relation_classes = [rel.target.name if rel.source.name == cls.name else rel.source.name
        target_relation_classes = [rel
        for rel in domain_model.relationships
        if rel.target.name == cls.name and "*" in rel.targetCardinality and
        (domain_model.compare_relationship_type(rel.type, 'Association') or 
         domain_model.compare_relationship_type(rel.type, 'Composition'))]
        existing_relations = source_relation_classes + target_relation_classes
        if len(existing_relations) >= 2: 
            possible_association_class.append((cls, existing_relations))
        print(f'{cls.name}: {source_relation_classes} / {target_relation_classes}')
    for p, _ in possible_association_class:
        association_class_relationships = [rel for rel in domain_model.relationships
        if rel.source.name == p.name or rel.target.name == p.name]
        if len(association_class_relationships) == 2:
            source = association_class_relationships[0].source if association_class_relationships[0].source.name != p.name else association_class_relationships[0].target
            target = association_class_relationships[1].source if association_class_relationships[1].source.name != p.name else association_class_relationships[1].target
            rel = UMLRelationship(source, target, "Association", "associates", sourceCardinality="*", targetCardinality="*")
            results.append((rel, p))
    return results


class AssociationClassVsClassConfiguration(Configuration):
    def update(self, cfg, domain_model, check_option):
        alt1 = cfg.alternative_1
        alt2 = cfg.alternative_2
        alt1_dm = cfg.alternative_1_dm
        alt2_dm = cfg.alternative_2_dm
        if (check_option == "Option 1" and cfg.option_1_dm) or \
            (check_option == "Option 2" and cfg.option_2_dm):
            if check_option == "Option 1":
                cls_conf = [cfg.update_confidence_model_element(domain_model.get_association_class(cls.name), high_confidence) 
                            for cls in alt1_dm.association_classes]
                #do not update relationship to trigger assocaition vs composition and cardinalitites templates.
                #rel_to_update = [domain_model.get_relationship(r.source.name, r.target.name, r.type, r.name )for r in alt1_dm.relationships]
                #rel_conf = [(cfg.update_confidence_model_element(rel, high_confidence), 
                #            cfg.update_confidence_model_element(rel.sourceCardinality, low_confidence),
                #            cfg.update_confidence_model_element(rel.targetCardinality, low_confidence))
                #            for rel in rel_to_update]
            else:
                cfg.update_confidence_model_element(alt2[1], high_confidence)
                #do not update relationship to trigger assocaition vs composition and cardinalitites templates.
                #rel_conf = [(cfg.update_confidence_model_element(rel, high_confidence), 
                #            cfg.update_confidence_model_element(rel.sourceCardinality, low_confidence),
                #            cfg.update_confidence_model_element(rel.targetCardinality, low_confidence))
                #            for rel in alt1_dm.relationships]
            return None
        elif check_option == "Option 1" and not cfg.option_1_dm:
            print()
            #update confidence
            cls_conf = [cfg.update_confidence_model_element(cls, high_confidence) for cls in alt1_dm.association_classes]
            rel_conf = [(cfg.update_confidence_model_element(rel, low_confidence), 
                        cfg.update_confidence_model_element(rel.sourceCardinality, low_confidence),
                        cfg.update_confidence_model_element(rel.targetCardinality, low_confidence))
                        for rel in alt1_dm.relationships]
            domain_model.update_model_general(
                classes_to_remove=[alt2[1]],
                attributes_to_remove=[],  
                relationships_to_remove=alt2_dm.relationships,
                enumerations_to_remove=[],
                assoc_classes_to_remove=[],
                #classes_to_add=alt1_dm.classes,
                classes_to_add=[],
                attributes_to_add=[],
                relationships_to_add=alt1_dm.relationships,
                enumerations_to_add=[],
                assoc_classes_to_add=alt1_dm.association_classes,
                replacement_map={},
            )
            return domain_model
        elif check_option == "Option 2" and not cfg.option_2_dm:
            print('Not required')
            #update confidence
            #cls_conf = [cfg.update_confidence_model_element(cls, high_confidence) for cls in alt1_dm.association_classes]
            return domain_model
        
    def set_confidence(self, configurations, alternative = True):
    #def confidence_configuration_association_class(configurations, alternative = True):
        for conf in configurations:
            alternative_1_score = None
            if hasattr(conf.alternative_1, '_metadata') and conf.alternative_1.get_metadata():
                #alternative 1 do not exits in all configurations
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


def find_association_class_alternatives(association_class_alternatives, many_to_many_alternatives, domain_model):
    alternatives = []
    no_alternatives = []
    for alt2 in many_to_many_alternatives:
        alt2_source = alt2[0].source
        alt2_target = alt2[0].target
        alt2_intermediate = alt2[1]
        alt2_dm = UMLDomainModel()
        alt2_dm.add_class(alt2_source)
        alt2_dm.add_class(alt2_target)
        alt2_dm.add_class(alt2_intermediate)
        rel1 = next(
            (domain_model.get_relationship_ignore_name(s, t, r)
            for s, t in [(alt2_source.name, alt2_intermediate.name), (alt2_intermediate.name, alt2_source.name)]
            for r in ['Association', 'Composition']
            if domain_model.get_relationship_ignore_name(s, t, r)),
            None
        )
        rel2 = next(
            (domain_model.get_relationship_ignore_name(s, t, r)
            for s, t in [(alt2_intermediate.name, alt2_target.name), (alt2_target.name, alt2_intermediate.name)]
            for r in ['Association', 'Composition']
            if domain_model.get_relationship_ignore_name(s, t, r)),
            None
        )
        alt2_dm.add_relationship(rel1)
        alt2_dm.add_relationship(rel2)
        q, o1, o2 = generate_many_to_many_association_class_question(alt2[0], alt2[1])
        #config = Configuration(alternative_2= alt2, alternative_2_dm = alt2_dm, question = q, option_1 = o1, option_2 = o2)
        config = AssociationClassVsClassConfiguration(alternative_2= alt2, alternative_2_dm = alt2_dm, question = q, option_1 = o1, option_2 = o2)
        config.option_2_dm = domain_model
        alt1_found = None
        for alt1 in association_class_alternatives:
            cls = alt1[0]
            if is_similar(alt1, alt2):
                alt_1_dm = UMLDomainModel()
                alt_1_dm.add_class(alt1[1].source)
                alt_1_dm.add_class(alt1[1].target)
                alt_1_dm.add_relationship(alt1[1])
                config.add_alternative_1(alternative_1 = alt1, alternative_1_dm = alt_1_dm)
                alt1_found = alt1
                alternatives.append(config)
                break
        if not alt1_found:
            alt_1_dm = UMLDomainModel()
            alt_1_dm.add_class(alt2[0].source)
            alt_1_dm.add_class(alt2[0].target)
            assoc_class = UMLAssociationClass(alt2[1].name, alt2[0].source, alt2[0].target, alt2[1].attributes)
            alt_1_dm.add_association_class(assoc_class)
            #alt_1_dm.add_relationship(alt2[0])
            #alt_1_rel = UMLRelationship(alt2[0].source, alt2[0].target, alt2[0].type, "has", alt2[0].sourceCardinality, alt2[0].targetCardinality)
            #Trigger CompositionVsAssociation
            #alt2[0].name ="has"
            alt_1_dm.add_relationship(alt2[0])
            config.add_alternative_1(alternative_1 = None, alternative_1_dm = alt_1_dm)
            no_alternatives.append(config)
    return alternatives, no_alternatives


def setup_association_class_vs_class_patterns(domain_model, domain_model_alternatives):
    many_to_many_dm = find_many_to_many_relationships(domain_model)
    #association_class_dm = find_association_class(domain_model)
    # Find concrete and abstract class alternatives
    many_to_many_alternatives = find_many_to_many_relationships(domain_model_alternatives)
    #association_class_dm = find_association_class(domain_model_alternatives)
    association_class_alternatives = []
    
    # Generate alternative configurations for concrete and abstract classes
    asc_cls_from_many_to_many_conf_alt, asc_cls_from_many_to_many_conf_no_alt = find_association_class_alternatives(association_class_alternatives, many_to_many_dm, domain_model)
    #many_to_many_conf_alt, many_to_many_conf_no_alt = find_many_to_many_alternatives(association_class_dm, many_to_many_alternatives, domain_model)
    
    intermediate_class_dm = find_intermediate_class(domain_model)
    association_class_alternatives = []
    check_many_to_many = [(rel.source.name, rel.target.name, ascl.name)for rel, ascl in many_to_many_dm]
    filtered_intermediate_class_dm = [ (rel, ascl) for rel, ascl in intermediate_class_dm
    if (rel.source.name, rel.target.name, ascl.name) not in check_many_to_many]
    asc_cls_from_intermediate_class_conf_alt, asc_cls_from_intermediate_class_conf_no_alt = find_association_class_alternatives(association_class_alternatives, filtered_intermediate_class_dm, domain_model)
   
    configurations_alt = asc_cls_from_many_to_many_conf_alt + asc_cls_from_intermediate_class_conf_alt # + many_to_many_configurations
    configurations_no_alt = asc_cls_from_many_to_many_conf_no_alt + asc_cls_from_intermediate_class_conf_no_alt # + many_to_many_conf_no_alt
    return configurations_alt, configurations_no_alt

