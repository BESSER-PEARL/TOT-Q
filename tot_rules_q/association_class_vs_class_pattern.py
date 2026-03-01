import copy
from tree_of_thought.model_elements import UMLClass, UMLAttribute, UMLEnumeration, Visibility, UMLRelationship, UMLDomainModel, UMLAssociationClass
from .configuration import Configuration
from .configuration import split_camel_case, correct_article, plural, name_format, is_similar
from .configuration import high_confidence, low_confidence, get_question_function
from collections import Counter

##############Association Class vs Class##############
def find_many_to_many_relationships(domain_model):
    results = []
    relations = []
    for rel in domain_model.relationships:
        if "*" in rel.sourceCardinality or "*" in rel.targetCardinality:
            relations.append(rel)
    source_relation_classes = []
    target_relation_classes = []

    for rel in relations:
        uml_class = rel.source
        source_relation_classes = [rel.target.name if rel.source.name == uml_class.name else rel.source.name
        for rel in domain_model.relationships
        if rel.source.name == uml_class.name or rel.target.name == uml_class.name]
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
    for r in results[:]: 
        for ac in domain_model.association_classes:
            ac_candidate_source = r[0].source.name
            ac_candidate_target = r[0].target.name
            ac_candidate = r[1].name
            ac_element_source = ac.source.name
            ac_element_target = ac.target.name
            ac_element = ac.name
            if ac_element_source.lower() == ac_candidate.lower() or ac_element_target.lower() == ac_candidate.lower():
                results.remove(r)
                break
            if (ac_element_source.lower() == ac_candidate_source.lower() and ac_element_target.lower() == ac_candidate_target.lower()):
                results.remove(r)
                break
            if (ac_element_source.lower() == ac_candidate_target.lower() and ac_element_target.lower() == ac_candidate_source.lower()):
                results.remove(r)
                break
    return results

def find_intermediate_class(domain_model):
    results = []
    possible_association_class = []
    for cls in domain_model.classes:
        source_relation_classes = [rel
        for rel in domain_model.relationships
        if rel.source.name == cls.name and
        (domain_model.compare_relationship_type(rel.type, 'Association') or
         domain_model.compare_relationship_type(rel.type, 'Composition'))]

        target_relation_classes = [rel
        for rel in domain_model.relationships
        if rel.target.name == cls.name and
        (domain_model.compare_relationship_type(rel.type, 'Association') or
         domain_model.compare_relationship_type(rel.type, 'Composition'))]
        
        existing_relations = source_relation_classes + target_relation_classes
        if len(existing_relations) >= 2: 
            has_many_cardinality = any(
                "*" in rel.sourceCardinality or "*" in rel.targetCardinality
                for rel in existing_relations
            )
            if has_many_cardinality:
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
    for r in results[:]:
        for ac in domain_model.association_classes:
            ac_candidate_source = r[0].source.name
            ac_candidate_target = r[0].target.name
            ac_candidate = r[1].name
            ac_element_source = ac.source.name
            ac_element_target = ac.target.name
            ac_element = ac.name
            if ac_element_source.lower() == ac_candidate.lower() or ac_element_target.lower() == ac_candidate.lower():
                results.remove(r)
                break
            if (ac_element_source.lower() == ac_candidate_source.lower() and ac_element_target.lower() == ac_candidate_target.lower()):
                results.remove(r)
                break
            if (ac_element_source.lower() == ac_candidate_target.lower() and ac_element_target.lower() == ac_candidate_source.lower()):
                results.remove(r)
                break
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
                if alt1_dm.association_classes:
                    cfg.resulting_element = ('associationclass', alt1_dm.association_classes[0])
            else:
                cfg.update_confidence_model_element(alt2[1], high_confidence)
                cfg.resulting_element = ('class', alt2[1])
            return None
        elif check_option == "Option 1" and not cfg.option_1_dm:
            print()
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
                classes_to_add=[],
                attributes_to_add=[],
                relationships_to_add=alt1_dm.relationships,
                enumerations_to_add=[],
                assoc_classes_to_add=alt1_dm.association_classes,
                replacement_map={},
            )
            if alt1_dm.association_classes:
                cfg.resulting_element = ('associationclass', alt1_dm.association_classes[0])
            return domain_model
        elif check_option == "Option 2" and not cfg.option_2_dm:
            cfg.resulting_element = ('class', alt2[1])
            return domain_model
        
    def set_confidence(self, configurations, alternative = True):
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


def find_association_class_alternatives(association_class_alternatives, many_to_many_alternatives, domain_model, template_module=None):
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
        if rel1 is None or rel2 is None:
            print(f"Skipping configuration for {alt2_intermediate.name}: missing relationships")
            print(f"   rel1 ({alt2_source.name}--{alt2_intermediate.name}): {rel1}")
            print(f"   rel2 ({alt2_intermediate.name}--{alt2_target.name}): {rel2}")
            continue

        alt2_dm.add_relationship(rel1)
        alt2_dm.add_relationship(rel2)

        rel_original = next(
            (domain_model.get_relationship_ignore_name(s, t, r)
            for s, t in [(alt2_source.name, alt2_target.name), (alt2_target.name, alt2_source.name)]
            for r in ['Association', 'Composition']
            if domain_model.get_relationship_ignore_name(s, t, r)),
            None
        )
        if rel_original:
            alt2_dm.add_relationship(rel_original) 

        if template_module:
            generate_many_to_many_association_class_question = template_module.generate_many_to_many_association_class_question
        else:
            generate_many_to_many_association_class_question = get_question_function('generate_many_to_many_association_class_question')
        q, o1, o2 = generate_many_to_many_association_class_question(alt2[0], alt2[1])
        config = AssociationClassVsClassConfiguration(alternative_2= alt2, alternative_2_dm = alt2_dm, question = q, option_1 = o1, option_2 = o2)
        config.originated_from = ('class', alt2[1])
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
            alt_1_dm.add_relationship(alt2[0])
            config.add_alternative_1(alternative_1 = None, alternative_1_dm = alt_1_dm)
            no_alternatives.append(config)
    return alternatives, no_alternatives

def review_association_class_vs_class_configurations(asc_cls_from_intermediate_class, asc_cls_from_many_to_many):
    new_asc_cls_from_intermediate_class = []
    for conf_intcls in asc_cls_from_intermediate_class:
        conf_intcls_alt_2_rel = conf_intcls.alternative_2[0]
        exists = False
        for conf_m2m in asc_cls_from_many_to_many:
            conf_m2m_alt_2_rel = conf_m2m.alternative_2[0]
            if conf_m2m_alt_2_rel.source.name == conf_intcls_alt_2_rel.source.name and \
               conf_m2m_alt_2_rel.target.name == conf_intcls_alt_2_rel.target.name:
                print('Duplicate configuration found between many to many and intermediate class.')
                exists = True
                break
            elif conf_m2m_alt_2_rel.source.name == conf_intcls_alt_2_rel.target.name and \
                 conf_m2m_alt_2_rel.target.name == conf_intcls_alt_2_rel.source.name:
                print('Duplicate configuration found between many to many and intermediate class.')
                exists = True
                break
        if not exists:
            new_asc_cls_from_intermediate_class.append(conf_intcls)
    return new_asc_cls_from_intermediate_class

def setup_association_class_vs_class_patterns(domain_model, domain_model_alternatives, template_module=None):
    many_to_many_dm = find_many_to_many_relationships(domain_model)
    # Find concrete and abstract class alternatives
    many_to_many_alternatives = find_many_to_many_relationships(domain_model_alternatives)
    association_class_alternatives = []

    # Generate alternative configurations for concrete and abstract classes
    asc_cls_from_many_to_many_conf_alt, asc_cls_from_many_to_many_conf_no_alt = find_association_class_alternatives(association_class_alternatives, many_to_many_dm, domain_model, template_module)
    asc_cls_from_many_to_many = asc_cls_from_many_to_many_conf_alt + asc_cls_from_many_to_many_conf_no_alt

    intermediate_class_dm = find_intermediate_class(domain_model)
    association_class_alternatives = []
    check_many_to_many = [(rel.source.name, rel.target.name, ascl.name)for rel, ascl in many_to_many_dm]
    filtered_intermediate_class_dm = [ (rel, ascl) for rel, ascl in intermediate_class_dm
    if (rel.source.name, rel.target.name, ascl.name) not in check_many_to_many]
    asc_cls_from_intermediate_class_conf_alt, asc_cls_from_intermediate_class_conf_no_alt = find_association_class_alternatives(association_class_alternatives, filtered_intermediate_class_dm, domain_model, template_module)

    new_asc_cls_from_intermediate_class_conf_alt = review_association_class_vs_class_configurations(asc_cls_from_intermediate_class_conf_alt, asc_cls_from_many_to_many)
    new_asc_cls_from_intermediate_class_conf_no_alt = review_association_class_vs_class_configurations(asc_cls_from_intermediate_class_conf_no_alt, asc_cls_from_many_to_many)
   
    configurations_alt = asc_cls_from_many_to_many_conf_alt + new_asc_cls_from_intermediate_class_conf_alt
    configurations_no_alt = asc_cls_from_many_to_many_conf_no_alt + new_asc_cls_from_intermediate_class_conf_no_alt 

    return configurations_alt, configurations_no_alt

