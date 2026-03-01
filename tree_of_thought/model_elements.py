from enum import Enum
from typing import Dict, Union, Tuple
from typing import List, Optional
from datetime import datetime
from besser.BUML.metamodel.structural.structural import *
import base64
from besser.agent.exceptions.logger import logger
import logging

import heapq
from collections import defaultdict, deque

import os
from tot_rules_q.rule_agent_config import REFINEMENT_THRESHOLD

confidence_threshold = REFINEMENT_THRESHOLD

logger.setLevel(logging.INFO)

class UMLMetadata:
    def __init__(self, score: float = 0.0, n_samples: int = 0):
        self.score = score
        self.scores: List[float] = []
        self.subSymbScores: List[float] = []
        self.neuSymbScores: List[float] = []
        self.symbScores: List[float] = []
        self.n_samples = n_samples

    def __repr__(self):
        return f"(score: {round(self.score,2)})"
    
    def set_score(self, score: float) -> None:
        self.score = score

    def get_score(self) -> float:
        s = round(self.score,2)
        return s
    
    def add_score(self, score: float) -> None:
        self.scores.append(score)
    
    def calc_score(self, n_samples: int) -> None:
        self.n_samples = n_samples
        self.score = sum(self.scores) / n_samples
        self.score = self.score / 100 if self.score > 1 else self.score
    
    def review_score_scale(self) -> None:
        self.subSymbScores = [s / 100 if s > 1 else s for s in self.subSymbScores]
        self.neuSymbScores = [s / 100 if s > 1 else s for s in self.neuSymbScores]
        self.symbScores = [s / 100 if s > 1 else s for s in self.symbScores]

    def calc_conf_score(self, n_samples: int) -> None:
        self.review_score_scale()
        subSymbScore = 0
        neuSymbScore = 0
        symbScore = 0
        if len(self.subSymbScores) > 0:
            subSymbScore = sum(self.subSymbScores) / n_samples
        if len(self.neuSymbScores) > 0:
            neuSymbScore = sum(self.neuSymbScores) / n_samples
        if len(self.symbScores) > 0:
            symbScore = max(self.symbScores)

        combined_odds = 1
        if len(self.subSymbScores) > 0:
            odds_subSymbScores = subSymbScore / (1 - subSymbScore)
            combined_odds = combined_odds * odds_subSymbScores
        if len(self.neuSymbScores) > 0:
            odds_neuSymbScores = neuSymbScore / (1 - neuSymbScore)
            combined_odds = combined_odds * odds_neuSymbScores
        if len(self.symbScores) > 0:
            odds_symbScores = symbScore / (1 - symbScore)
            combined_odds = combined_odds * odds_symbScores
        self.score = combined_odds / (1 + combined_odds)
    
class MetadataMixin:
    def __init__(self, *args, **kwargs):
        self._metadata: Optional[UMLMetadata] = None
        super().__init__(*args, **kwargs)

    @property
    def metadata(self) -> UMLMetadata:
        if self._metadata is None:
            self._metadata = UMLMetadata()
        return self._metadata

    @metadata.setter
    def metadata(self, value: UMLMetadata):
        self._metadata = value

    def set_metadata(self, score: float = 0.0) -> None:
        self._metadata = UMLMetadata(score)
    
    def get_metadata(self) -> UMLMetadata:
        return self._metadata

class Visibility(Enum):
    PUBLIC = "+"
    PRIVATE = "-"
    PROTECTED = "#"
    PACKAGE = "~"

class UMLAttribute (MetadataMixin):
    def __init__(self, name: str, type: str, visibility: Visibility = Visibility.PUBLIC):
        self.name = name
        self.type = type
        self.visibility = visibility
    
    def __repr__(self):
        return f"{self.visibility.value} {self.name} : {self.type}"

class UMLEnumeration(MetadataMixin):
    def __init__(self, name: str, literals: List[str]):
        self.name = name
        self.literals = literals
    
    def __repr__(self):
        enum_str = f"enum {self.name} {{\n  " + "\n  ".join(map(str, self.literals)) + "\n}" if self.literals else f"enum {self.name}"
        return enum_str

class UMLMethod(MetadataMixin):
    def __init__(
        self,
        name: str,
        return_type: str = "void",
        parameters: list[UMLAttribute] = None,
        visibility: Visibility = Visibility.PUBLIC
    ):
        self.name = name
        self.return_type = return_type
        self.parameters = parameters if parameters is not None else []
        self.visibility = visibility

    def __repr__(self):
        params_str = ", ".join(f"{p.name}: {p.type}" for p in self.parameters)
        return f"{self.visibility.value} {self.name}({params_str}) : {self.return_type.lower()}"

class UMLClass(MetadataMixin):
    def __init__(self, name: str, attributes: Optional[List[UMLAttribute]] = None, is_abstract: bool = False, methods: Optional[List[UMLMethod]] = None):
        super().__init__()
        self.name = name
        self.attributes = attributes if attributes else []
        self.methods = methods if methods else []
        self.is_abstract = is_abstract
    
    def add_attribute(self, attribute: UMLAttribute):
        self.attributes.append(attribute)    

    def get_attribute(self, name: str) -> Optional[UMLAttribute]:
        return next((att for att in self.attributes if att.name.lower() == name.lower()), None)
    
    def remove_attribute(self, name: str):
        att =  self.get_attribute(name)
        if att:
            self.attributes.remove(att)
        return att

    def __repr__(self):
        abstract_marker = "(abstract) " if self.is_abstract else ""
        class_str = f"class {abstract_marker}{self.name} {{\n  " + "\n  ".join(map(str, self.attributes)) + "\n}" if self.attributes else f"class {abstract_marker}{self.name}"
        return class_str

class Cardinality(MetadataMixin):
    def __init__(self, value: str = "1"):
        if hasattr(value, 'min_value') and hasattr(value, 'max_value'):
            self.value = getattr(value, 'value', None)
            self.min_value = value.min_value
            self.max_value = value.max_value
            self.min_metadata = getattr(value, 'min_metadata', MetadataMixin())
            self.max_metadata = getattr(value, 'max_metadata', MetadataMixin())

            if not hasattr(self.min_metadata, 'metadata'):
                 if hasattr(self.min_metadata, 'set_metadata'): self.min_metadata.set_metadata()

            return
        temp_value = value.strip()
        if len(value) > 4:
            value = temp_value[:4]
            if value[-1] =="0":
                value = temp_value[-3:] 
            if temp_value[:4] == "1..0":
                print("Warning: Cardinality '1..0' is invalid")
        self.value = value
        # granular values
        self.min_value, self.max_value = self._parse_value(value)
        self.min_metadata = MetadataMixin()
        self.min_metadata.set_metadata()
        self.max_metadata = MetadataMixin()
        self.max_metadata.set_metadata()
        
    def __str__(self):
        return self.value
    
    def __repr__(self):
        return f'"{self.value}"'

    def set(self, new_value: str):
        self.value = new_value
        self.min_value, self.max_value = self._parse_value(new_value)

    def is_optional(self):
        return self.value in ("0..1", "0", "*")

    def is_multiple(self):
        return "*" in self.value or ".." in self.value and not self.value.endswith("1")

    # Optional: allow assignment like a string
    def __eq__(self, other):
        return self.value == str(other)

    # Optional: make it usable like a string
    def __contains__(self, item):
        return item in self.value
    
    def __getitem__(self, key):
        return self.value[key]
    
    # Granular values
    def _parse_value(self, value: str):
        value = value.strip()
        if ".." in value:
            low, high = value.split("..")
            return low, high
        if value == "*":
            return "0", "*"
        return value, value

    def set_min_score(self, score):
        self.min_metadata.set_metadata(score=score)

    def set_max_score(self, score):
        self.max_metadata.set_metadata(score=score)

    def get_min_score(self):
        return self.min_metadata.get_metadata()

    def get_max_score(self):
        return self.max_metadata.get_metadata()

    def add_min_score(self, score):
        self.min_metadata.get_metadata().add_score(score=score)

    def add_max_score(self, score):
        self.max_metadata.get_metadata().add_score(score=score)

    def calc_min_confidence(self, n_samples):
        self.min_metadata.get_metadata().calc_score(n_samples)

    def calc_max_confidence(self, n_samples):
        self.max_metadata.get_metadata().calc_score(n_samples)

class UMLRelationship(MetadataMixin):
    def __init__(self, source: UMLClass, target: UMLClass, type: str, name: str, sourceCardinality: str = "1", targetCardinality: str = "1"):
        super().__init__()
        self.source = source
        self.target = target
        self.type = type
        self.name = name
        self._sourceCardinality = sourceCardinality if isinstance(sourceCardinality, Cardinality) else Cardinality(sourceCardinality)
        self._targetCardinality = targetCardinality if isinstance(targetCardinality, Cardinality) else Cardinality(targetCardinality)

    @property
    def targetCardinality(self):
        return self._targetCardinality

    @targetCardinality.setter
    def targetCardinality(self, value):
        if isinstance(value, Cardinality):
            self._targetCardinality = value
        else:
            self._targetCardinality = Cardinality(value)

    @property
    def sourceCardinality(self):
        return self._sourceCardinality

    @sourceCardinality.setter
    def sourceCardinality(self, value):
        if isinstance(value, Cardinality):
            self._sourceCardinality = value
        else:
            self._sourceCardinality = Cardinality(value)

    def __repr__(self):
        plantuml = f"{self.source.name}"
        if self.type == "Inheritance":
            plantuml += "<|--"
        elif self.type == "Association":
            plantuml += f" \"{self.sourceCardinality}\" "
            plantuml += "--"
            plantuml += f" \"{self.targetCardinality}\" "
        elif self.type == "Composition" or self.type == 'Containment':
            plantuml += f" \"{self.sourceCardinality}\" "
            plantuml += "*--"
            plantuml += f" \"{self.targetCardinality}\" "

        plantuml += f" {self.target.name}"
        relation_str = plantuml
        return relation_str

class UMLAssociationClass(UMLClass):
    def __init__(self, name: str, source: UMLClass, target: UMLClass, attributes: Optional[List[UMLAttribute]] = None):
        super().__init__(name, attributes)
        self.source = source
        self.target = target
    
    def __repr__(self):
        source_name = getattr(self.source, "name", str(self.source))
        target_name = getattr(self.target, "name", str(self.target))
        return f"association class {self.name} between {source_name} and {target_name}"


class UMLDomainModel:
    def __init__(self):
        self.classes: List[UMLClass] = []
        self.enumerations: List[UMLEnumeration] = []
        self.relationships: List[UMLRelationship] = []
        self.association_classes : List[UMLAssociationClass] = []
    
    def add_class(self, uml_class: UMLClass):
        self.classes.append(uml_class)

    def add_enumeration(self, uml_enum: UMLEnumeration):
        self.enumerations.append(uml_enum)
    
    def add_relationship(self, relationship: UMLRelationship):
        self.relationships.append(relationship)

    def add_association_class(self, uml_class: UMLAssociationClass):
        self.association_classes.append(uml_class)

    def get_class(self, name: str) -> Optional[UMLClass]:
        return next((cls for cls in self.classes if cls.name == name), None)
    
    def get_enumeration(self, name: str) -> Optional[UMLEnumeration]:
        return next((enum for enum in self.enumerations if enum.name.lower() == name.lower()), None)

    def remove_class(self, name: str):
        if self.get_class(name):
            self.relationships = [rel for rel in self.relationships if rel.source.name != name and rel.target.name != name]
            self.classes.remove(self.get_class(name))

    def remove_only_class(self, name: str):
        if self.get_class(name):
            self.classes.remove(self.get_class(name))

    def remove_enumeration(self, name: str):
        if self.get_enumeration(name):
            delete_relationship = [(cls, attr) for cls in self.classes for attr in cls.attributes if attr.name == name or attr.type == name]
            for rel in delete_relationship:
                rel[0].attributes.remove(rel[1])
            self.enumerations.remove(self.get_enumeration(name))

    def get_relationship(self, source_name: str, target_name: str, type: str, name: str) -> Optional[UMLRelationship]:
        return next((rel for rel in self.relationships \
                     if rel.source.name == source_name and \
                     rel.target.name == target_name and \
                     rel.type == type and \
                     rel.name == name \
                        ), None)
    
    def remove_relationship(self, source_name: str, target_name: str, type: str, name: str):
        relationship = self.get_relationship(source_name, target_name, type, name)
        if relationship:
            self.relationships.remove(relationship)
    
    def compare_relationship_type(self, type1, type2) -> bool:
        type1 = type1.lower()
        type2 = type2.lower()
        association = ['association', 'associate']
        composition = ['composition', 'contain', 'containment', 'contains']
        inheritance = ['inheritance', 'inherit', 'generalization']
        if (type1 == type2):
            return True
        elif type1 in association and type2 in association:
            return True
        elif type1 in composition and type2 in composition:
            return True
        elif type1 in inheritance and type2 in inheritance:
            return True
        return False


    def get_relationship_ignore_name(self, source_name: str, target_name: str, type: str) -> Optional[UMLRelationship]:
        for rel in self.relationships:
            if (rel.source.name == source_name and 
                rel.target.name == target_name and 
                self.compare_relationship_type(rel.type, type)):
                return rel
        return None

    def remove_duplicate_relationships(self):
        relationship_groups = {}

        for relationship in self.relationships:
            key = (relationship.source.name, relationship.target.name, relationship.type.lower())
            if key not in relationship_groups:
                is_new = True
                for k in relationship_groups.keys():
                    if (relationship.source.name == k[0] and 
                        relationship.target.name == k[1] and 
                        self.compare_relationship_type(relationship.type, k[2])):
                        is_new = False
                        key = k
                if is_new:
                    relationship_groups[key] = []
            relationship_groups[key].append(relationship)

        unique_relationships = []
        for group in relationship_groups.values():
            if len(group) == 1:
                unique_relationships.append(group[0])
            else:
                highest_score_rel = group[0]
                for rel in group[1:]:
                    if rel.get_metadata().get_score() > highest_score_rel.get_metadata().get_score():
                        highest_score_rel = rel

                unique_relationships.append(highest_score_rel)

        self.relationships = unique_relationships

    def get_association_class(self, name: str) -> Optional[UMLAssociationClass]:
        return next((cls for cls in self.association_classes if cls.name == name), None)
    
    def remove_association_class(self, name: str):
        asc_cls = self.get_association_class(name)
        if asc_cls:
            self.association_classes.remove(asc_cls)

    def refresh_relationship_references(self):
        class_map = {cls.name: cls for cls in self.classes}

        for rel in self.relationships:
            if rel.source.name in class_map:
                rel.source = class_map[rel.source.name]
            if rel.target.name in class_map:
                rel.target = class_map[rel.target.name]

    def refresh_enum_references(self):
        class_map = {cls.name: cls for cls in self.classes}
        enum_count = {enum.name: 0 for enum in self.enumerations}

        for cls in self.classes:
            for attr in cls.attributes:
                if attr.type in enum_count:
                    enum_count[attr.type] += 1

        for assoc_cls in self.association_classes:
            for attr in assoc_cls.attributes:
                if attr.type in enum_count:
                    enum_count[attr.type] += 1

        for enum_name, count in enum_count.items():
            if count == 0:
                self.remove_enumeration(enum_name)
        
    def generate_plantuml(self) -> str:
        plantuml = "@startuml\n"
        for cls in self.classes:
            if cls.is_abstract:
                plantuml += f"abstract class {cls.name} {{\n"
            else:
                plantuml += f"class {cls.name} {{\n"
            for attr in cls.attributes:
                plantuml += f"    {attr}\n"
            for mtd in cls.methods:
                params_str = ", ".join(f"{p.name}: {p.type}" for p in mtd.parameters)
                return_type = "" if mtd.return_type in ['void','null'] \
                                or "list" in mtd.return_type.lower() \
                                else f": {mtd.return_type}"
                plantuml += f"    {mtd.visibility.value} {mtd.name}({params_str}) {return_type}\n"
            plantuml += "}\n"
        for enum in self.enumerations:
            plantuml += f"enum {enum.name} {{\n"
            for literal in enum.literals:
                plantuml += f"    {literal}\n"
            plantuml += "}\n"
        all_rel_name = []
        for rel in self.relationships:
            rel_name = None
            plantuml += f"{rel.source.name}"
            if rel.type == "Inheritance":
                plantuml += " <|--"
            elif rel.type == "Association":
                plantuml += f" \"{rel.sourceCardinality}\" "
                plantuml += "--"
                plantuml += f" \"{rel.targetCardinality}\" "
            elif rel.type in ["Composition", "Containment"]:
                plantuml += f" \"{rel.sourceCardinality}\" "
                plantuml += "*--"
                plantuml += f" \"{rel.targetCardinality}\" "

            plantuml += f" {rel.target.name}"
            if rel.type == "Association" and rel.name.lower() not in all_rel_name:
                if rel.name == 'Contains':
                    rel_name = f"{rel.source.name}_{rel.name}_{rel.target.name}".replace(" ", "_")
                else:
                    rel_name = rel.name.replace(" ", "_")
                plantuml += f" : {rel_name}"
            elif rel.type in ["Composition", "Containment"] and rel.name == 'Contains' \
                    and rel.name.lower() not in all_rel_name:
                rel_name = f"{rel.source.name}_{rel.name}_{rel.target.name}".replace(" ", "_")
                plantuml += f" : {rel_name}"
            plantuml += f"\n"
            if rel_name:
                all_rel_name.append(rel.name.lower())
        for cls in self.association_classes:
            plantuml += f"class {cls.name} {{\n"
            for attr in cls.attributes:
                plantuml += f"    {attr}\n"
            plantuml += "}\n"
            plantuml += f"({cls.source.name}, {cls.target.name}) .. {cls.name}\n"
        plantuml += "@enduml"
        return plantuml

    def __repr__(self):
        return self.generate_plantuml()
        
    def to_buml(self) -> DomainModel:
        domain_model = DomainModel("DomainModel")
        domain_types = set()
        associations = set()
        generalizations = set()
        enum_lookup = {}
        class_lookup = {}

        for uml_enum in self.enumerations:
            enum = Enumeration(
                name=uml_enum.name,
                literals=set(EnumerationLiteral(name=l) for l in uml_enum.literals)
            )
            domain_types.add(enum)
            enum_lookup[uml_enum.name] = enum

        for uml_cls in self.classes:
            cls_type = Class
            cls = cls_type(
                name=uml_cls.name,
                timestamp=int(datetime.now().timestamp()),
                is_abstract = uml_cls.is_abstract
            )

            domain_types.add(cls)
            class_lookup[cls.name] = cls

        for uml_cls in self.classes:
            cls = class_lookup[uml_cls.name]

            properties = set()
            for attr in uml_cls.attributes:
                prop_type = map_type(attr.type,class_lookup,enum_lookup)
                prop = Property(name=attr.name, type=prop_type)
                properties.add(prop)
            cls.attributes = properties

            methods = set()
            for mtd in uml_cls.methods:
                params = set()
                for p in mtd.parameters:
                    param_type = map_type(p.type,class_lookup,enum_lookup)
                    param = Parameter(name=p.name, type=param_type)
                    params.add(param)
                return_type = map_type(mtd.return_type,class_lookup,enum_lookup)
                method = Method(name=mtd.name, parameters=params, type=return_type)
                methods.add(method)
            cls.methods = methods

        for rel in self.relationships:
            if rel.type == "Inheritance":
                specific_cls = class_lookup.get(rel.target.name)  # subclass
                general_cls = class_lookup.get(rel.source.name)   # superclass
                if specific_cls and general_cls:
                    generalization = Generalization(general=general_cls, specific=specific_cls)
                    generalizations.add(generalization)

        existing_assoc_names = set()

        for rel in self.relationships:
            source = class_lookup.get(rel.source.name)
            target = class_lookup.get(rel.target.name)
            if not source or not target:
                continue

            src_mult = parse_multiplicity(rel.sourceCardinality or "1")
            tgt_mult = parse_multiplicity(rel.targetCardinality or "*")

            if hasattr(rel, "is_association_class") and rel.is_association_class:
                assoc_name = get_unique_assoc_name(rel.name or "", source.name, target.name, existing_assoc_names)
                assoc_cls = class_lookup.get(assoc_name)
                if not assoc_cls:
                    assoc_cls = Class(
                        name=assoc_name,
                        timestamp=int(datetime.now().timestamp()),
                        synonyms=rel.synonyms or []
                    )
                    domain_model.add_type(assoc_cls)
                    class_lookup[assoc_name] = assoc_cls

                domain_model.add_association(AssociationClass(
                    name=assoc_name,
                    source=source,
                    target=target,
                    association_class=assoc_cls,
                    source_multiplicity=src_mult,
                    target_multiplicity=tgt_mult,
                    is_bidirectional=rel.is_bidirectional,
                    timestamp=int(datetime.now().timestamp())
                ))

            elif rel.type == "Association":
                assoc_name = get_unique_assoc_name(rel.name or "", source.name, target.name, existing_assoc_names)
                if source.name == target.name:
                    editor_name = assoc_name
                else:
                    editor_name = ""
                end1 = Property(
                    name=editor_name,
                    type=source,
                    multiplicity=src_mult,
                )
                end2 = Property(
                    name="",
                    type=target,
                    multiplicity=tgt_mult,
                )
                ends = {end1, end2}

                assoc = BinaryAssociation(
                    name=assoc_name,
                    ends=ends,
                    timestamp=datetime.now(),
                    synonyms=None
                )
                domain_model.add_association(assoc)

            elif rel.type in ["Composition", "Containment", "Contain"]:
                assoc_name = get_unique_assoc_name(rel.name or "", source.name, target.name, existing_assoc_names)
                if source.name == target.name:
                    editor_name = assoc_name
                else:
                    editor_name = ""

                container_end = Property(
                    name=editor_name,
                    type=target,
                    owner=None,
                    multiplicity=tgt_mult,
                    is_composite=True,
                    is_navigable=True,
                    timestamp=datetime.now()
                )
                containee_end = Property(
                    name="",
                    type=source,
                    owner=None,
                    multiplicity=src_mult,
                    is_composite=False,
                    is_navigable=True,
                    timestamp=datetime.now()
                )
                ends = (container_end, containee_end)

                containment_assoc = BinaryAssociation(
                    name=assoc_name,
                    ends=ends,
                    timestamp=datetime.now()
                )
                domain_model.add_association(containment_assoc)

        for assoc_cls_rel in self.association_classes:
            source = class_lookup.get(assoc_cls_rel.source.name)
            target = class_lookup.get(assoc_cls_rel.target.name)
            if not source or not target:
                continue

            assoc_name = get_unique_assoc_name(assoc_cls_rel.name or "", source.name, target.name, existing_assoc_names)

            existing_assoc = next(
                (
                    a for a in domain_model.associations
                    if isinstance(a, BinaryAssociation) and
                    {end.type.name for end in a.ends} == {source.name, target.name}
                ),
                None
            )

            if existing_assoc:
                assoc = existing_assoc
            else:
                end1 = Property(name="", type=source, multiplicity="1")
                end2 = Property(name="", type=target, multiplicity="1")
                assoc = BinaryAssociation(
                    name=assoc_name,
                    ends={end1, end2},
                    timestamp=None
                )
                domain_model.add_association(assoc)
                existing_assoc_names.add(assoc_name)

            attributes = set()
            for attr in assoc_cls_rel.attributes:
                prop_type = map_type(attr.type, class_lookup, enum_lookup)
                attributes.add(Property(name=attr.name, type=prop_type))

            assoc_class_obj = AssociationClass(
                name=assoc_cls_rel.name or assoc.name,
                attributes=attributes,
                association=assoc,
                timestamp=None,
                synonyms=None
            )
            domain_model.add_type(assoc_class_obj)

        for t in domain_types:
            domain_model.add_type(t)
        for g in generalizations:
            domain_model.add_generalization(g)
        return domain_model

    def from_buml(self, domain_model: DomainModel):
        uml_model = self
        type_lookup = {}

        for enum in domain_model.get_enumerations():
            uml_enum = UMLEnumeration(
                name=enum.name,
                literals=[lit.name for lit in enum.literals]
            )
            uml_model.add_enumeration(uml_enum)
            type_lookup[enum] = uml_enum

        for dm_cls in domain_model.get_classes():
            uml_cls = UMLClass(
                name=dm_cls.name,
                is_abstract=getattr(dm_cls, "is_abstract", False),
                attributes=[],
                methods=[]
            )

            for prop in dm_cls.attributes:
                attr = UMLAttribute(
                    name=prop.name,
                    type=getattr(prop.type, "name", str(prop.type))
                )
                uml_cls.attributes.append(attr)

            for m in getattr(dm_cls, "methods", []):
                params = []
                for p in m.parameters:
                    params.append(UMLAttribute(name=p.name, type=getattr(p.type, "name", str(p.type))))
                uml_method = UMLMethod(
                    name=m.name,
                    parameters=params,
                    return_type=getattr(m.type, "name", str(m.type))
                )
                uml_cls.methods.append(uml_method)

            uml_model.add_class(uml_cls)
            type_lookup[dm_cls] = uml_cls

        for gen in domain_model.generalizations:
            rel = UMLRelationship(
                source=type_lookup[gen.general],
                target=type_lookup[gen.specific],
                type="Inheritance",
                name=""
            )
            uml_model.add_relationship(rel)

        for assoc in domain_model.associations:
            if isinstance(assoc, AssociationClass):
                source = next(iter(assoc.ends)).type
                target = next(iter(assoc.ends)).type
                uml_assoc_cls = UMLAssociationClass(
                    name=assoc.association_class.name,
                    attributes=[],
                    source=type_lookup[source],
                    target=type_lookup[target]
                )
                uml_model.add_association_class(uml_assoc_cls)
            elif isinstance(assoc, BinaryAssociation):
                ends = list(assoc.ends)
                if len(ends) != 2:
                    continue
                src_end, tgt_end = ends[0], ends[1]
                rel_type="Association"
                if tgt_end.is_composite:
                    rel_type = "Composition"
                elif src_end.is_composite:
                    src_end, tgt_end = ends[1], ends[0]
                    rel_type = "Composition"
                uml_rel = UMLRelationship(
                    source=type_lookup[src_end.type],
                    target=type_lookup[tgt_end.type],
                    type=rel_type,
                    name=assoc.name,
                    sourceCardinality=buml_multiplicity_to_cardinality(src_end.multiplicity),
                    targetCardinality=buml_multiplicity_to_cardinality(tgt_end.multiplicity)
                )
                uml_model.add_relationship(uml_rel)

        return uml_model

    def model_with_confidence_values(self) -> str:
        plantuml = "@startuml\n"

        for cls in self.classes:
            class_conf = getattr(cls.get_metadata(), "get_score", lambda: None)()
            conf_str = f"  # C: {class_conf:.2f}" if class_conf else ""

            if cls.is_abstract:
                plantuml += f"abstract class {cls.name}{conf_str} {{\n"
            else:
                plantuml += f"class {cls.name}{conf_str} {{\n"

            for attr in cls.attributes:
                attr_conf = None

                try:
                    metadata = attr.get_metadata()

                    if metadata:
                        attr_conf = metadata.get_score()

                except (AttributeError, TypeError):
                    pass

                conf_str = f"  # {attr_conf:.2f}" if attr_conf is not None else ""
                plantuml += f"    {attr}{conf_str}\n"

            for mtd in cls.methods:
                params_str = ", ".join(f"{p.name}: {p.type}" for p in mtd.parameters)
                return_type = "" if mtd.return_type in ['void', 'null'] or "list" in mtd.return_type.lower() \
                            else f": {mtd.return_type}"
                mtd_conf = getattr(mtd.get_metadata(), "get_score", lambda: None)()
                conf_str = f"  # {mtd_conf:.2f}" if mtd_conf else ""
                plantuml += f"    {mtd.visibility.value} {mtd.name}({params_str}) {return_type}{conf_str}\n"

            plantuml += "}\n"

        for enum in self.enumerations:
            enum_conf = getattr(enum.get_metadata(), "get_score", lambda: None)()
            conf_str = f"  # {enum_conf:.2f}" if enum_conf else ""
            plantuml += f"enum {enum.name}{conf_str} {{\n"
            for literal in enum.literals:
                lit_conf = getattr(literal, "confidence", None)
                conf_str = f"  # {lit_conf:.2f}" if lit_conf else ""
                plantuml += f"    {literal}{conf_str}\n"
            plantuml += "}\n"

        all_rel_name = []
        for rel in self.relationships:
            rel_name = None
            rel_conf = getattr(rel.get_metadata(), "get_score", lambda: None)()
            rel_sc_min = getattr(rel.sourceCardinality.min_metadata.get_metadata(), "get_score", lambda: None)()
            rel_sc_max = getattr(rel.sourceCardinality.max_metadata.get_metadata(), "get_score", lambda: None)()
            rel_tc_min = getattr(rel.targetCardinality.min_metadata.get_metadata(), "get_score", lambda: None)()
            rel_tc_max = getattr(rel.targetCardinality.max_metadata.get_metadata(), "get_score", lambda: None)()
            conf_str = f"  # RC: {rel_conf:.2f}, SCmin: {rel_sc_min}, SCmax: {rel_sc_max}, TCmin: {rel_tc_min}, TCmax: {rel_tc_max}" if rel_conf else ""

            plantuml += f"{rel.source.name}"
            if rel.type == "Inheritance":
                plantuml += " <|--"
            elif rel.type == "Association":
                plantuml += f" \"{rel.sourceCardinality}\" -- \"{rel.targetCardinality}\""
            elif rel.type in ["Composition", "Containment"]:
                plantuml += f" \"{rel.sourceCardinality}\" *-- \"{rel.targetCardinality}\""

            plantuml += f" {rel.target.name}"
            if rel.type == "Association" and rel.name.lower() not in all_rel_name:
                rel_name = rel.name.replace(" ", "_")
                plantuml += f" : {rel_name}"
            elif rel.type in ["Composition", "Containment"] and rel.name.lower() not in all_rel_name:
                rel_name = f"{rel.source.name}_{rel.name}_{rel.target.name}".replace(" ", "_")
                plantuml += f" : {rel_name}"
            
            plantuml += f"{conf_str}\n"
            if rel_name:
                all_rel_name.append(rel.name.lower())

        for cls in self.association_classes:
            cls_conf = getattr(cls.get_metadata(), "get_score", lambda: None)()
            conf_str = f"  # confidence: {cls_conf:.2f}" if cls_conf else ""
            plantuml += f"class {cls.name}{conf_str} {{\n"
            for attr in cls.attributes:
                attr_conf = getattr(attr, "confidence", None)
                conf_str = f"  # {attr_conf:.2f}" if attr_conf else ""
                plantuml += f"    {attr}{conf_str}\n"
            plantuml += "}\n"
            plantuml += f"({cls.source.name}, {cls.target.name}) .. {cls.name}\n"

        plantuml += "@enduml"
        return plantuml

    def bfs_traverse_classes_priority(self):
        graph = defaultdict(list)
        for rel in self.relationships:
            src_name = rel.source.name
            tgt_name = rel.target.name
            graph[src_name].append(tgt_name)
            graph[tgt_name].append(src_name)

        rel_count = {
            cls.name: sum(
                1 for rel in self.relationships
                if (rel.source.name == cls.name or rel.target.name == cls.name)
                and rel.type != "Inheritance"
            )
            for cls in self.classes
        }

        if not rel_count:
            return []

        start_name = max(rel_count, key=rel_count.get)

        visited = set()
        bfs_order = []

        global_heap = [(-rel_count[start_name], start_name)]
        heapq.heapify(global_heap)

        local_queue = deque()

        def get_conf(name):
            cls = self.get_class(name)
            return getattr(cls.get_metadata(), "get_score", lambda: None)() or 0.0

        while global_heap or local_queue:
            if local_queue:
                current_name = local_queue.popleft()
            else:
                _, current_name = heapq.heappop(global_heap)

            if current_name in visited:
                continue

            visited.add(current_name)
            bfs_order.append(self.get_class(current_name))

            neighbors = [n for n in graph[current_name] if n not in visited]

            low_confidence_neighbors = [
                n for n in neighbors
                if get_conf(n) < confidence_threshold and rel_count[n] != 0
            ]
            low_connected_neighbors = [
                n for n in neighbors
                if (rel_count[n] == 1)
            ]

            high_priority_neighbors = list(dict.fromkeys(low_confidence_neighbors + low_connected_neighbors))
            high_priority_neighbors2 = low_confidence_neighbors + low_connected_neighbors

            for n in high_priority_neighbors:
                local_queue.append(n)

            for n in neighbors:
                if rel_count[n] > 0:
                    heapq.heappush(global_heap, (-rel_count[n], n))
        
        for cls in self.classes:
            if cls.name not in visited:
                bfs_order.append(cls)

        return bfs_order
    
    def extract_submodel(self, visited_classes: List[str]) -> "UMLDomainModel":
        submodel = UMLDomainModel()
        for dm_cls in self.classes:
            if dm_cls.name in visited_classes:
                submodel.add_class(dm_cls)
        
        used_enum_names = set()
        for cls in submodel.classes:
            for attr in cls.attributes:
                if attr.type in [enum.name for enum in self.enumerations]:
                    used_enum_names.add(attr.type)
        
        for enum in self.enumerations:
            if enum.name in used_enum_names:
                submodel.add_enumeration(enum)
        
        for rel in self.relationships:
            if rel.source.name in visited_classes and rel.target.name in visited_classes:
                submodel.add_relationship(rel)

        for asc in self.association_classes:
            if asc.source.name in visited_classes and asc.target.name in visited_classes:
                submodel.add_association_class(asc)

        return submodel

    def update_model_general(
        self,
        classes_to_remove: List[UMLClass],
        attributes_to_remove: List[Tuple[UMLClass, UMLAttribute]],
        relationships_to_remove: List[UMLRelationship],
        enumerations_to_remove: List[UMLEnumeration],
        assoc_classes_to_remove: List[UMLAssociationClass],
        classes_to_add: List[UMLClass],
        attributes_to_add: List[Tuple[UMLClass, UMLAttribute]],
        relationships_to_add: List[UMLRelationship],
        enumerations_to_add: List[UMLEnumeration],
        assoc_classes_to_add: List[UMLAssociationClass],
        replacement_map: Dict,
    ):
        for old_class, new_class in replacement_map.items():
            if isinstance(old_class, UMLClass) and isinstance(new_class, UMLClass):
                for rel in self.relationships:
                    if (rel.source.name == old_class.name and rel.target.name == new_class.name) or \
                    (rel.source.name == new_class.name and rel.target.name == old_class.name):
                        if rel.source.name != rel.target.name:
                            self.remove_relationship(rel.source.name, rel.target.name, rel.type, rel.name)
                    else:
                        if rel.source.name == old_class.name:
                            rel.source = new_class
                        if rel.target.name == old_class.name:
                            rel.target = new_class

                for attr in old_class.attributes:
                    if not new_class.get_attribute(attr.name):
                        new_class.attributes.append(attr)

                self.remove_only_class(old_class.name)

                self.add_class(new_class)

        for old_rel, new_rel in replacement_map.items():
            if isinstance(old_rel, UMLRelationship) and isinstance(new_rel, UMLRelationship):
                self.remove_relationship(old_rel.source.name, old_rel.target.name, old_rel.type, old_rel.name)
                self.add_relationship(new_rel)

        for uml_class, attr in attributes_to_remove:
            cls = self.get_class(uml_class.name)
            if cls and uml_class.get_attribute(attr.name):
                cls.remove_attribute(attr.name)

        for uml_class, attr in attributes_to_add:
            if uml_class in self.classes and not uml_class.get_attribute(attr.name):
                uml_class.add_attribute(attr)

        for cls in classes_to_remove:
            if cls in self.classes:
                self.remove_class(cls.name)
        for rel in relationships_to_remove:
            if rel in self.relationships:
                self.remove_relationship(rel.source.name, rel.target.name, rel.type, rel.name)
        for enum in enumerations_to_remove:
            self.remove_enumeration(enum.name)
        for assoc_class in assoc_classes_to_remove:
            if assoc_class in self.association_classes:
                self.remove_association_class(assoc_class.name)

        for cls in classes_to_add:
            if cls not in self.classes:
                self.add_class(cls)
        for rel in relationships_to_add:
            if rel not in self.relationships:
                self.add_relationship(rel)
        for enum in enumerations_to_add:
            if enum not in self.enumerations:
                self.add_enumeration(enum)
        for assoc_class in assoc_classes_to_add:
            if assoc_class not in self.association_classes:
                self.add_association_class(assoc_class)

        self.refresh_relationship_references()
        self.refresh_enum_references()

def buml_multiplicity_to_cardinality(mult) -> Cardinality:
    lower = mult.min
    upper = mult.max

    if lower is None: lower = 0
    if upper is None: upper = 9999

    if lower == upper:
        value = str(lower)
    elif lower == 0 and (upper >= 9999):
        value = "*"
    elif lower == 1 and (upper >= 9999):
        value = "1..*"
    elif lower == 0 and upper == 1:
        value = "0..1"
    elif upper >= 9999:
        value = f"{lower}..*"
    else:
        value = f"{lower}..{upper}"

    return Cardinality(value)


def map_type(type_name: str, class_lookup: dict, enum_lookup: dict):
    type_map = {
        "str": StringType,
        "string": StringType,
        "int": IntegerType,
        "integer": IntegerType,
        "float": FloatType,
        "bool": BooleanType,
        "boolean": BooleanType,
        "date": DateType,
        "datetime": DateTimeType,
        "time": TimeType,
        "timedelta": TimeDeltaType,
    }
    
    if not type_name:
        return StringType
    
    key = type_name.lower()
    if key == "void":
        return ""
    if key in type_map:
        return type_map[key]
    if type_name in enum_lookup:
        return enum_lookup[type_name]
    if type_name in class_lookup:
        return class_lookup[type_name]
    return StringType

def get_unique_assoc_name(base_name: str, source_name: str, target_name: str, existing_names: set) -> str:
    if not base_name:
        base_name = f"{source_name}_{target_name}_assoc"

    unique_name = base_name
    index = 1
    while unique_name in existing_names:
        unique_name = f"{base_name}_{index}"
        index += 1

    existing_names.add(unique_name)
    return unique_name

UNLIMITED_MAX_MULTIPLICITY = 9999

def parse_multiplicity(cardinality) -> Multiplicity:
    if cardinality == "one" or cardinality == "N/A" or cardinality == "n/a" or cardinality == "":
        print("Warning: Replacing unsupported cardinality:'", cardinality)
        cardinality = "1"
    if hasattr(cardinality, 'value') and cardinality.value is not None:
        s = cardinality.value
    elif isinstance(cardinality, str):
        s = cardinality
    else:
        raise ValueError(f"Unsupported cardinality type: {type(cardinality)}")

    s = s.strip()
    if ".." in s:
        lower_str, upper_str = s.split("..")
    else:
        lower_str = s
        upper_str = s

    lower = int(lower_str.strip()) if lower_str.strip().isdigit() else 0
    upper_str = upper_str.strip()
    if upper_str == "*" or upper_str == "many":
        upper = UNLIMITED_MAX_MULTIPLICITY
    elif upper_str.isdigit():
        upper = int(upper_str)
    else:
        raise ValueError(f"Invalid upper bound in multiplicity: {upper_str}")
    try:
        m = Multiplicity(min_multiplicity=lower, max_multiplicity=upper)
    except Exception as e:
        print(f"Error parsing multiplicity from cardinality '{cardinality}': {e}")

    return Multiplicity(min_multiplicity=lower, max_multiplicity=upper)