import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from dsl.exportTree import import_tree_from_json
import numpy as np
from pydantic import BaseModel
from enum import Enum
from tree_of_thought.llm import gpt,client, model_name
import copy
import sys

class AssociationType(str, Enum):
    Association = "Association"
    Containment = "Containment"
    Inheritance = "Inheritance"

class ConceptType(str, Enum):
    Class = "Class"
    Enumeration = "Enumeration"

class Attributes(BaseModel):
    name: str
    type: str
    confidence: float

class Enumeration(BaseModel):
    name: str
    literals: list[str]
    confidence: float

class DomainConcept(BaseModel):
    name: str
    attributes: list[Attributes]
    enumeration: list[Enumeration]
    #type: str
    type: ConceptType
    isAbstract: bool
    #rule: list[str]
    #traceability: str
    confidence: float

class RelationCardinality(BaseModel):
    value: str
    confidence: float

class Association(BaseModel):
    source: DomainConcept
    target: DomainConcept
    #rule: list[str]
    #traceability: str
    source: str
    target: str
    name: str
    #sourceCardinality: str
    #targetCardinality: str
    sourceCardinality: RelationCardinality
    targetCardinality: RelationCardinality
    #association_type: str
    association_type: AssociationType
    confidence: float

class ListConcepts(BaseModel):
    classes: list[DomainConcept]

class ListRelationships(BaseModel):
    relationship: list[Association]

def class_extract(output):
    completion = client.beta.chat.completions.parse(
        model = model_name,
        messages=[
            {"role": "system", "content": "Extract the class information."},
            {"role": "user", "content": output},
        ],
        response_format=ListConcepts,
    )

    event = completion.choices[0].message.parsed
    print(completion.choices[0].message.parsed.model_dump_json(indent=2))

def relationship_extract(output):
    completion = client.beta.chat.completions.parse(
        model = model_name,
        messages=[
            {"role": "system", "content": "Extract the relationship information."},
            {"role": "user", "content": output},
        ],
        response_format=ListRelationships
,
    )

    event = completion.choices[0].message.parsed
    print(completion.choices[0].message.parsed.model_dump_json(indent=2))

def element_struct_output(output, element= 'class'):
    if element == 'class': 
        so_format = ListConcepts
    elif element == 'relationship': 
        so_format = ListRelationships
    completion = client.beta.chat.completions.parse(
        model = model_name,
        messages=[
            {"role": "system", "content": "Extract the information."},
            {"role": "user", "content": output},
        ],
        response_format=so_format,
    )

    result = completion.choices[0].message.parsed
    print(completion.choices[0].message.parsed.model_dump_json(indent=2))
    return result


from tree_of_thought.model_elements import UMLClass, UMLAttribute, UMLEnumeration, Visibility, UMLRelationship, UMLDomainModel, Cardinality

def name_format(str_name):
    checklist = ['abstract', 'Abstract']
    for c in checklist:
        str_name = str_name.replace(c, "")
    str_name = str_name.strip()
    str_name = str_name[0].upper() + str_name[1:] if str_name else str_name
    return str_name

def struct_output_to_class(so):
    attributes = []
    for at in so.attributes:
        attr = UMLAttribute(at.name, at.type, Visibility.PRIVATE)
        attr.set_metadata(score=at.confidence)
        attributes.append(attr)
    elem = UMLClass(name_format(so.name), attributes, so.isAbstract)
    elem.set_metadata(score=so.confidence)
    return elem, attributes

def struct_output_to_enum(so):
    """for e in so.enumeration:
        literals = e.literals
        elem = UMLEnumeration(name_format(so.name), literals)
        elem.set_metadata(score=so.confidence)"""
    literals = []
    for e in so.enumeration:
        literals.append(e.name)
    elem = UMLEnumeration(name_format(so.name), literals)
    elem.set_metadata(score=so.confidence)
    return elem

def class_enum_elements(elements_list):
    classes = []
    allAttributes = []
    enumerations = []
    for so in list(elements_list):
        elClass = elEnum = None
        if "class" in so.type.lower() or "enum" not in so.type.lower(): 
            elClass, attribute = struct_output_to_class(so)
            allAttributes += attribute
            classes.append(elClass)
        elif "enum" in so.type.lower():
            elEnum = struct_output_to_enum(so)
            enumerations.append(elEnum)        
    for e in enumerations:
        attEnum = [a for a in allAttributes if a.name.lower() == e.name.lower()]
        for a in attEnum:
            a.type = e.name
    return classes, enumerations

def review_class_elements(elements_list, domain_model, conf_score, n_samples):
    for so in list(elements_list.classes):
        name = domain_model.get_class(name_format(so.name))
        if not name:
            attributes = []
            for at in so.attributes:
                attr = UMLAttribute(at.name, at.type, Visibility.PRIVATE)
                attr.set_metadata(score=at.confidence)
                attributes.append(attr)
            elem = UMLClass(name_format(so.name), attributes)
            elem.set_metadata(score=so.confidence)
            domain_model.add_class(elem)
            parse_single_element(
                elem, 
                conf_score, 
                conf_score.add_class, 
                conf_score.get_class, 
                n_samples
            )
    return domain_model


def relationship_elements(elements_list, domain_model):
    elements = []
    for so in list(elements_list):
        source = domain_model.get_class(name_format(so.source))
        target = domain_model.get_class(name_format(so.target))
        #create cardinalities
        source_cardinality = Cardinality(so.sourceCardinality.value)
        source_cardinality.set_metadata(score=so.sourceCardinality.confidence)
        target_cardinality = Cardinality(so.targetCardinality.value)
        target_cardinality.set_metadata(score=so.targetCardinality.confidence)        
        if so.association_type is AssociationType.Inheritance:
            source,target = target, source    
        elem = UMLRelationship(source, target, name_format(so.association_type), name_format(so.name), source_cardinality, target_cardinality)
        elem.set_metadata(score=so.confidence)
        if source is None or target is None:
            str_irrelevant = f"{so.source} {'is irrelevant' if source is None else 'exists'},"
            str_irrelevant += f"{so.target} {'is irrelevant' if target is None else 'exists'}."
            print(str_irrelevant)# check bug
        else:
            elements.append(elem)
    return elements

def elements(output, element= 'class', domain_model = None, conf_score= None, n_samples=1):
    struct_output = element_struct_output(output, element)
    if element == 'class': 
        classes, enumerations = class_enum_elements(struct_output.classes)
        elements = {"classes": classes, "enumerations": enumerations}
    elif element == 'relationship': 
        classes_missing = False
        for so in struct_output.relationship:
            source = domain_model.get_class(name_format(so.source))
            target = domain_model.get_class(name_format(so.target))
            if source is None or target is None:
                classes_missing = True
                break
        if classes_missing:
            struct_output_review = element_struct_output(output, element = 'class')
            domain_model = review_class_elements(struct_output_review, domain_model, conf_score, n_samples)

        elements = relationship_elements(struct_output.relationship, domain_model)
    return elements

def parse_single_element(e, conf_score, add_func, get_func, n_samples):
    e_score = get_func(name_format(e.name)) if hasattr(e, 'name') else None
    if not e_score:
        e_score = copy.deepcopy(e)
        e_score.set_metadata()
        add_func(e_score)
    e_score.get_metadata().add_score(e.get_metadata().get_score())
    e_score.get_metadata().calc_score(n_samples)

def compare_confidence_attributes(e,conf_score,n_samples):
    e_score = conf_score.get_class(name_format(e.name))
    for at in e.attributes:
        at_score = e_score.get_attribute(at.name)
        if at_score is None:
            at_score = copy.deepcopy(at)
            e_score.add_attribute(at_score)
            at_score.set_metadata()
        at_score.get_metadata().add_score(e.get_metadata().get_score())
        at_score.get_metadata().calc_score(n_samples)


def compare_confidence_cardinality(e,conf_score,n_samples):
    e_score = conf_score.get_relationship_ignore_name(
                    name_format(e.source.name),
                    name_format(e.target.name),
                    name_format(e.type))
    all_cardinalities = [e_score.sourceCardinality, e_score.targetCardinality]
    for card in all_cardinalities:
        card_score = card
        card_score.get_metadata().add_score(e.get_metadata().get_score())
        card_score.get_metadata().calc_score(n_samples)


def parse_elements(output, element='class', domain_model=None, conf_score=None, n_samples=1):
    if element == 'class': 
        extracted_elements = elements(output, element='class')
        for e in extracted_elements['classes']:
            domain_model.add_class(e)
            parse_single_element(
                e, 
                conf_score, 
                conf_score.add_class, 
                conf_score.get_class, 
                n_samples
            )
            compare_confidence_attributes(e, conf_score, n_samples)
        for e in extracted_elements['enumerations']:
            domain_model.add_enumeration(e)
            parse_single_element(
                e, 
                conf_score, 
                conf_score.add_enumeration, 
                conf_score.get_enumeration, 
                n_samples
            )
    elif element == 'relationship':
        extracted_elements = elements(output, element='relationship', domain_model=domain_model, conf_score = conf_score, n_samples = n_samples)
        for e in extracted_elements:
            domain_model.add_relationship(e)
            parse_single_element(
                e, 
                conf_score, 
                lambda rel: conf_score.add_relationship(rel),
                #lambda name: conf_score.get_relationship(
                lambda name: conf_score.get_relationship_ignore_name(
                    name_format(e.source.name),
                    name_format(e.target.name),
                    name_format(e.type),
                #    name_format(e.name)
                ),
                n_samples
            )
            compare_confidence_cardinality(e,conf_score,n_samples)
    return domain_model, conf_score

def selected_model_confidence(domain_model, domain_model_alternatives):
    domain_model_with_confidence = UMLDomainModel()
    for cls in domain_model.classes:
        cls_conf = domain_model_alternatives.get_class(cls.name)
        domain_model_with_confidence.add_class(copy.deepcopy(cls_conf))
    
    for enum in domain_model.enumerations:
        enum_conf = domain_model_alternatives.get_enumeration(enum.name)
        domain_model_with_confidence.add_enumeration(copy.deepcopy(enum_conf))
    
    for rel in domain_model.relationships:
        #rel_conf = domain_model_alternatives.get_relationship(rel.source.name, rel.target.name, rel.type, rel.name)
        rel_conf = domain_model_alternatives.get_relationship_ignore_name(rel.source.name, rel.target.name, rel.type)
        domain_model_with_confidence.add_relationship(copy.deepcopy(rel_conf))

    for asoc_cls in domain_model.association_classes:
        asoc_cls_conf = domain_model_alternatives.get_association_class(asoc_cls.name)
        domain_model_with_confidence.add_association_class(copy.deepcopy(asoc_cls_conf))

    return domain_model_with_confidence

def alternatives_model_confidence(domain_model, domain_model_alternatives):
    alternatives_domain_model_with_confidence = UMLDomainModel()
    for cls in domain_model_alternatives.classes:
        cls_conf = domain_model.get_class(cls.name)
        if cls_conf is None:
            alternatives_domain_model_with_confidence.add_class(copy.deepcopy(cls))
    
    for enum in domain_model_alternatives.enumerations:
        enum_conf = domain_model.get_enumeration(enum.name)
        if enum_conf is None:
            alternatives_domain_model_with_confidence.add_enumeration(copy.deepcopy(enum))
    
    for rel in domain_model_alternatives.relationships:
        #rel_conf = domain_model.get_relationship(rel.source.name, rel.target.name, rel.type, rel.name)
        rel_conf = domain_model_alternatives.get_relationship_ignore_name(rel.source.name, rel.target.name, rel.type)
        if rel_conf is None:
            alternatives_domain_model_with_confidence.add_relationship(copy.deepcopy(rel))

    for asoc_cls in domain_model_alternatives.association_classes:
        asoc_cls_conf = domain_model.get_association_class(asoc_cls.name)
        if asoc_cls_conf is None:
            alternatives_domain_model_with_confidence.add_association_class(copy.deepcopy(asoc_cls))

    return alternatives_domain_model_with_confidence

def get_embedding(text: str, model="text-embedding-ada-002"):
    response = client.embeddings.create(
        input = text,
        model= "text-embedding-3-large"
    )
    return np.array(response.data[0].embedding)

def cosine_similarity(vec1, vec2):
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

def create_similarity_matrix(sentences, dm_conf_score, dm_conf_score2, threshold = 0.8):
    similar_names = []
    str_classes = [f'{c}' for c in sentences]
    embeddings = [get_embedding(f'class {s.name}') for s in sentences]
    
    n = len(embeddings)
    similarity_matrix = np.zeros((n, n))
    str_output = f"Similar words with t >{threshold}: \n"
    for i in range(n):
        for j in range(i+1, n):
            similarity = cosine_similarity(embeddings[i], embeddings[j])           
            similarity_matrix[i][j] = similarity
            if i != j and similarity >= threshold:
                str_output += f"'{sentences[i].name}' and '{sentences[j].name}' have similarity: {similarity:.2f}\n"
                similar_names.append((sentences[i].name, sentences[j].name))
                

    return similarity_matrix, similar_names, str_output

def review_semantic_similarity(similar_names, cname_llm, cname_nlp, dm_conf_score, dm_conf_score2):
    for s in similar_names:
        keep = None
        remove = None
        if s[0] in cname_llm and s[1] in cname_llm:
            keep = dm_conf_score.get_class(s[0])
            remove = dm_conf_score.get_class(s[1])
            if (keep and remove) and (remove.get_metadata().get_score() > keep.get_metadata().get_score()):
                keep, remove = remove, keep
        elif s[0] in cname_nlp and s[1] in cname_nlp:
            keep = dm_conf_score2.get_class(s[0])
            remove = dm_conf_score2.get_class(s[1])
            if (keep and remove) and (remove.get_metadata().get_score() > keep.get_metadata().get_score()):
                keep, remove = remove, keep

        #update score
        if keep and remove:
            if keep.name != remove.name:
                if remove.name in cname_llm:
                    dm_conf_score.remove_class(remove.name)
                elif remove.name in cname_nlp:
                    dm_conf_score2.remove_class(remove.name)
    #review two elements from different group (llm and nlp)
    for s in similar_names:
        keep = None
        remove = None
        if s[0] in cname_llm and s[1] in cname_nlp:
            keep = dm_conf_score.get_class(s[0])
            remove = dm_conf_score2.get_class(s[1])
        elif s[0] in cname_nlp and s[1] in cname_llm:
            keep = dm_conf_score.get_class(s[1])
            remove = dm_conf_score2.get_class(s[0])
        #update score
        if keep and remove:
            dm_conf_score2.remove_class(remove.name)

    return dm_conf_score, dm_conf_score2

def check_inheritance_attributes(domain_model):
    new_domain_model = copy.deepcopy(domain_model)
    inheritance = [(new_domain_model.get_class(rel.source.name), new_domain_model.get_class(rel.target.name)) for rel in new_domain_model.relationships if new_domain_model.compare_relationship_type(rel.type.lower(), "inheritance")]
    for supc, subc  in inheritance:
        attributes_parent = [a.name.lower() for a in supc.attributes]
        attributes_child = copy.deepcopy(subc.attributes)
        for att in attributes_child:
            if att.name.lower() in attributes_parent:
                new_domain_model.get_class(subc.name).remove_attribute(att.name)
    return new_domain_model

def check_relationships(domain_model):
    new_domain_model = copy.deepcopy(domain_model)
    association = [(new_domain_model.get_class(rel.source.name), new_domain_model.get_class(rel.target.name), rel) for rel in new_domain_model.relationships if new_domain_model.compare_relationship_type(rel.type.lower(), "association")]
    composition = [(new_domain_model.get_class(rel.source.name), new_domain_model.get_class(rel.target.name), rel) for rel in new_domain_model.relationships if new_domain_model.compare_relationship_type(rel.type.lower(), "composition")]
    associations_review= []
    for asoc_src, asoc_tgt, asoc  in association:
        for comp_src, comp_tgt, comp in composition:
            if (asoc_src.name.lower() == comp_src.name.lower()) and \
                (asoc_tgt.name.lower() == comp_tgt.name.lower()):
                new_domain_model.remove_relationship(asoc.source.name, asoc.target.name, asoc.type, asoc.name)
            elif (asoc_src.name.lower() == comp_tgt.name.lower()) and \
                (asoc_tgt.name.lower() == comp_src.name.lower()):
                new_domain_model.remove_relationship(asoc.source.name, asoc.target.name, asoc.type, asoc.name)
    
    association = [(new_domain_model.get_class(rel.source.name), new_domain_model.get_class(rel.target.name), rel) for rel in new_domain_model.relationships if new_domain_model.compare_relationship_type(rel.type.lower(), "association")]
    index = 1
    for asoc_src, asoc_tgt, asoc  in association:
        for asoc2_src, asoc2_tgt, asoc2  in association[index:]:
            if (asoc_src.name.lower() == asoc2_tgt.name.lower()) and \
                (asoc_tgt.name.lower() == asoc2_src.name.lower()):
                if (asoc.get_metadata().get_score() > asoc2.get_metadata().get_score()):
                    new_domain_model.remove_relationship(asoc2.source.name, asoc2.target.name, asoc2.type, asoc2.name)
                else:
                    new_domain_model.remove_relationship(asoc.source.name, asoc.target.name, asoc.type, asoc.name)
        index +=1

    association = [(new_domain_model.get_class(rel.source.name), new_domain_model.get_class(rel.target.name), rel) for rel in new_domain_model.relationships ]#if new_domain_model.compare_relationship_type(rel.type.lower(), "association")]
    enum_names = [e.name.lower() for e in new_domain_model.enumerations]
    for asoc_src, asoc_tgt, asoc  in association:
        if (asoc_src.name.lower() in enum_names) or \
            (asoc_tgt.name.lower() in enum_names):
            new_domain_model.remove_relationship(asoc.source.name, asoc.target.name, asoc.type, asoc.name)

    enum_list= [e for e in new_domain_model.enumerations]
    for enum  in enum_list:
        attr_list = [(c, at) for c in new_domain_model.classes for at in c.attributes if \
                    (at.name.lower() == enum.name.lower() or at.type.lower() == enum.name.lower())]
        if len(attr_list) == 0:
            new_domain_model.remove_enumeration(enum.name)

    class_list= [c for c in new_domain_model.classes]
    for cls  in class_list:
        rel_list = [r for r in new_domain_model.relationships if \
                    (r.source.name.lower() == cls.name.lower() or r.target.name.lower() == cls.name.lower())]
        if len(rel_list) == 0:
            new_domain_model.remove_class(cls.name)

    return new_domain_model


level1 = []
level2 = []
level1_selected = None
level2_selected = None

def tree_to_levels(filename):
    global level1, level2, level1_selected, level2_selected
    tree = import_tree_from_json(filename)
    level1 = tree["levels"][0]["thoughts"]
    level2 = tree["levels"][1]["thoughts"]
    level1_selected = int(tree["selected_thoughts"][0]) + 1
    level2_selected = int(tree["selected_thoughts"][1]) + 1

def get_domain_models(filename):
    tree_to_levels(filename)

    dm_l1 = []
    dm_conf_score = UMLDomainModel()
    n_samples = len(level1)

    for l in level1:
        dm = UMLDomainModel()
        dm, dm_conf_score = parse_elements(l, element='class', domain_model=dm, conf_score=dm_conf_score, n_samples=n_samples)
        dm_l1.append(dm)

    dm_l2 = []
    for l in level2:
        dm = copy.deepcopy(dm_l1[level1_selected - 1])
        dm, dm_conf_score = parse_elements(l, element='relationship', domain_model=dm, conf_score=dm_conf_score, n_samples=n_samples)
        dm_l2.append(dm)

    tot_selected = dm_l2[level2_selected - 1]

    domain_model = selected_model_confidence(tot_selected, dm_conf_score)
    domain_model = check_inheritance_attributes(domain_model)
    domain_model = check_relationships(domain_model)
    domain_model_alternatives = alternatives_model_confidence(tot_selected, dm_conf_score)

    return domain_model, domain_model_alternatives

