from enum import Enum
from typing import Dict, Union, Tuple
from typing import List, Optional

class UMLMetadata:
    #def __init__(self, score: float = 0.0, explanation: str = ""):
    def __init__(self, score: float = 0.0, n_samples: int = 0):
        self.score = score
        self.scores: List[float] = []
        #self.explanation = explanation
        self.subSymbScores: List[float] = []
        self.neuSymbScores: List[float] = []
        self.symbScores: List[float] = []
        self.n_samples = n_samples

    def __repr__(self):
        #return f"(score: {self.score}, explanation: {self.explanation})"
        return f"(score: {round(self.score,2)})"
    
    def set_score(self, score: float) -> None:
        self.score = score

    def get_score(self) -> float:
        s = round(self.score,2)
        return s
    
    def add_score(self, score: float) -> None:
        self.scores.append(score)
    
    def calc_score(self, n_samples: int) -> None:
        #TODO: change for self.n_samples
        self.n_samples = n_samples
        self.score = sum(self.scores) / n_samples
        self.score = self.score / 100 if self.score > 1 else self.score
    
    def review_score_scale(self) -> None:
        self.subSymbScores = [s / 100 if s > 1 else s for s in self.subSymbScores]
        self.neuSymbScores = [s / 100 if s > 1 else s for s in self.neuSymbScores]
        self.symbScores = [s / 100 if s > 1 else s for s in self.symbScores]

    def calc_conf_score(self, n_samples: int) -> None:
        #TODO: change for self.n_samples
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
        #combined_odds = odds_subSymbScores * odds_neuSymbScores * odds_symbScores
        self.score = combined_odds / (1 + combined_odds)
    
class MetadataMixin:
    def __init__(self, *args, **kwargs):
        # Initialize metadata to None by default.
        # If you prefer to always have a metadata object, you could initialize it here.
        self._metadata: Optional[UMLMetadata] = None
        super().__init__(*args, **kwargs)

    @property
    def metadata(self) -> UMLMetadata:
        # Lazy initialization: if metadata hasn't been set, create a default instance.
        if self._metadata is None:
            self._metadata = UMLMetadata()
        return self._metadata

    @metadata.setter
    def metadata(self, value: UMLMetadata):
        self._metadata = value

    #def set_metadata(self, score: float, explanation: str) -> None:
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
        return f"{self.visibility.value} {self.name}: {self.type}"

class UMLEnumeration(MetadataMixin):
    def __init__(self, name: str, literals: List[str]):
        self.name = name
        self.literals = literals
    
    def __repr__(self):
        enum_str = f"enum {self.name} {{\n  " + "\n  ".join(map(str, self.literals)) + "\n}" if self.literals else f"enum {self.name}"
        return enum_str
        #return f"enum {self.name} {{\n {'\n '.join(self.literals)} }}"
        #class_str = f"class {abstract_marker}{self.name} {{\n  " + "\n  ".join(map(str, self.attributes)) + "\n}" if self.attributes else f"class {abstract_marker}{self.name}"

class UMLClass(MetadataMixin):
    def __init__(self, name: str, attributes: Optional[List[UMLAttribute]] = None, is_abstract: bool = False):
        # No need to accept score/explanation here; the mixin handles that.
        super().__init__()  # This calls MetadataMixin.__init__ and sets up metadata.
        self.name = name
        self.attributes = attributes if attributes else []
        self.is_abstract = is_abstract
    
    def add_attribute(self, attribute: UMLAttribute):
        self.attributes.append(attribute)    

    def get_attribute(self, name: str) -> Optional[UMLAttribute]:
        return next((att for att in self.attributes if att.name.lower() == name.lower()), None)
    
    def remove_attribute(self, name: str):
        att =  self.get_attribute(name)
        self.attributes.remove(att)

    def __repr__(self):
        abstract_marker = "(abstract) " if self.is_abstract else ""
        class_str = f"class {abstract_marker}{self.name} {{\n  " + "\n  ".join(map(str, self.attributes)) + "\n}" if self.attributes else f"class {abstract_marker}{self.name}"
        #print score
        #class_str += f"\n {self.metadata}" if self._metadata is not None else ""
        return class_str

class Cardinality(MetadataMixin):
    def __init__(self, value: str = "1"):
        self.value = value

    def __str__(self):
        return self.value
    
    def __repr__(self):
        return f'"{self.value}"'

    def set(self, new_value: str):
        self.value = new_value

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

class UMLRelationship(MetadataMixin):
    def __init__(self, source: UMLClass, target: UMLClass, type: str, name: str, sourceCardinality: str = "1", targetCardinality: str = "1"): 
        super().__init__()  # This calls MetadataMixin.__init__ and sets up metadata.
        self.source = source
        self.target = target
        self.type = type  # Association, Composition, Aggregation, Inheritance
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
        #relation_str = f"{self.source.name} --[{self.type} {self.multiplicity}]--> {self.target.name}"
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
        #print score
        #relation_str += f"\n {self.metadata}" if self._metadata is not None else ""
        return relation_str

class UMLAssociationClass(UMLClass):
    def __init__(self, name: str, source: UMLClass, target: UMLClass, attributes: Optional[List[UMLAttribute]] = None):
        super().__init__(name, attributes)
        self.source = source
        self.target = target
    
    def __repr__(self):
        return f"association class {self.name} between {self.source.name} and {self.target.name}"


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
        #TODO: Change remove by high uncertainty
        if self.get_class(name):
            #remove relationships associated with class:
            self.relationships = [rel for rel in self.relationships if rel.source.name != name and rel.target.name != name]
            #remove class
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


    #def get_relationship(self, source_name: str, target_name: str) -> Optional[UMLRelationship]:
    #    return next((rel for rel in self.relationships if rel.source.name == source_name and rel.target.name == target_name), None)
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
        
        # Group relationships by their source, target, and type
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
        
        # Create a new list with only the highest scoring relationship from each group
        unique_relationships = []
        for group in relationship_groups.values():
            # If there's only one relationship in the group, keep it
            if len(group) == 1:
                unique_relationships.append(group[0])
            else:
                # Find the relationship with the highest score
                highest_score_rel = group[0]
                for rel in group[1:]:
                    if rel.get_metadata().get_score() > highest_score_rel.get_metadata().get_score():
                        highest_score_rel = rel
                
                unique_relationships.append(highest_score_rel)
        
        # Replace the relationships list with our deduplicated list
        self.relationships = unique_relationships

    def get_association_class(self, name: str) -> Optional[UMLAssociationClass]:
        return next((cls for cls in self.association_classes if cls.name == name), None)
    
    def remove_association_class(self, name: str):
        asc_cls = self.get_association_class(name)
        if asc_cls:
            self.association_classes.remove(asc_cls)

    def generate_plantuml(self) -> str:
        plantuml = "@startuml\n"
        for cls in self.classes:
            #plantuml += f"class {cls.name} {{\n"
            if cls.is_abstract:
                plantuml += f"abstract class {cls.name} {{\n"
            else:
                plantuml += f"class {cls.name} {{\n"
            for attr in cls.attributes:
                plantuml += f"    {attr}\n"
            plantuml += "}\n"
        for enum in self.enumerations:
            plantuml += f"enum {enum.name} {{\n"
            for literal in enum.literals:
                plantuml += f"    {literal}\n"
            plantuml += "}\n"
        for rel in self.relationships:
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

            plantuml += f" {rel.target.name}\n"
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
        # Handle class replacement from replacement_map
        for old_class, new_class in replacement_map.items():
            if isinstance(old_class, UMLClass) and isinstance(new_class, UMLClass):
                # Redirect relationships to use the new class
                for rel in self.relationships:
                    #Delete relationship between old element and new element
                    if (rel.source.name == old_class.name and rel.target.name == new_class.name) or \
                    (rel.source.name == new_class.name and rel.target.name == old_class.name):
                        self.remove_relationship(rel.source.name, rel.target.name, rel.type, rel.name)
                    else:
                        if rel.source.name == old_class.name:
                            rel.source = new_class
                        if rel.target.name == old_class.name:
                            rel.target = new_class

                # Transfer attributes that are not already in new_class
                for attr in old_class.attributes:
                    if not new_class.get_attribute(attr.name):  # Avoid duplicates
                        new_class.attributes.append(attr)

                # Remove old class and add new class
                #self.remove_class(old_class.name)
                self.remove_only_class(old_class.name)
                """#check if new class already exists:
                cls_exists = self.get_class(new_class.name)
                if cls_exists:"""

                self.add_class(new_class)

        # Handle relationship replacement from replacement_map
        for old_rel, new_rel in replacement_map.items():
            if isinstance(old_rel, UMLRelationship) and isinstance(new_rel, UMLRelationship):
                self.remove_relationship(old_rel.source.name, old_rel.target.name, old_rel.type, old_rel.name)
                self.add_relationship(new_rel)

        # Remove specified attributes
        for uml_class, attr in attributes_to_remove:
            cls = self.get_class(uml_class.name)
            if cls and uml_class.get_attribute(attr.name):
                cls.remove_attribute(attr.name)

        # Add new attributes
        for uml_class, attr in attributes_to_add:
            if uml_class in self.classes and not uml_class.get_attribute(attr.name):
                uml_class.add_attribute(attr)

        # Remove entities from the model
        for cls in classes_to_remove:
            if cls in self.classes:
                self.remove_class(cls.name)
            #elif self.get_class(cls.name):
            #    self.remove_class(cls.name)
        for rel in relationships_to_remove:
            if rel in self.relationships:
                self.remove_relationship(rel.source.name, rel.target.name, rel.type, rel.name)
        for enum in enumerations_to_remove:
            self.remove_enumeration(enum.name)
        for assoc_class in assoc_classes_to_remove:
            if assoc_class in self.association_classes:
                self.remove_association_class(assoc_class.name)

        # Add new entities to the model
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
