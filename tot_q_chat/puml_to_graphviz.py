import graphviz
from graphviz import Source

import re

def transform_plantuml_to_graphviz(plantuml_code: str) -> str:

    class_pattern = re.compile(r'\bclass (\w+) \{(.+?)\}', re.DOTALL)
    abstract_class_pattern = re.compile(r'\babstract class (\w+) \{(.+?)\}', re.DOTALL)
    enum_pattern = re.compile(r'enum (\w+) \{(.+?)\}', re.DOTALL)

    association_pattern = re.compile(r'(\w+)\s+"([^"]+)"\s+--\s+"([^"]+)"\s+(\w+)')
    composition_pattern = re.compile(r'(\w+)\s+"([^"]+)"\s+\*--\s+"([^"]+)"\s+(\w+)')
    association_classes_pattern = re.compile(r'\((\w+), (\w+)\) .. (\w+)')

    # Inheritance patterns
    inheritance_pattern_forward = re.compile(r'(\w+)\s+--\|>\s+(\w+)')  # Child --|> Parent
    inheritance_pattern_reverse = re.compile(r'(\w+)\s+<\|--\s+(\w+)')  # Parent <|-- Child

    # Extract elements from the PlantUML input
    abstract_classes = abstract_class_pattern.findall(plantuml_code)

    classes = class_pattern.findall(plantuml_code)
    enums = enum_pattern.findall(plantuml_code)
    associations = association_pattern.findall(plantuml_code)
    compositions = composition_pattern.findall(plantuml_code)
    association_classes = association_classes_pattern.findall(plantuml_code)

    # Handle both directions of inheritance
    inheritances = inheritance_pattern_forward.findall(plantuml_code)
    inheritances += [(child, parent) for parent, child in inheritance_pattern_reverse.findall(plantuml_code)]

    # Start building DOT code
    dot_code = "digraph G {\n  rankdir=BT;\n"
    
    # Add classes
    for class_name, class_body in classes:
        attLine = '\\n'
        attributes = class_body.strip().split('\n')
        #class_label = f"{class_name.upper()}|{attLine.join(attributes)}"
        class_label = f"{class_name}|{attLine.join(attributes)}"
        if class_name.lower() in [c.lower() for c, _ in abstract_classes]:
            dot_code += f'  {class_name.upper()} [shape=record, label="{{{class_label}}}", fontname="Times-Italic"];\n'
        else:
            dot_code += f'  {class_name.upper()} [shape=record, label="{{{class_label}}}"];\n'
    
    # Add enums
    for enum_name, enum_body in enums:
        attLine = '\\n'
        attributes = enum_body.strip().split('\n')
        enum_label = f"[E] {enum_name.upper()}|{attLine.join(attributes)}"
        dot_code += f'  {enum_name.upper()} [shape=record, label="{{{enum_label}}}"];\n'

    # Add inheritances
    for child, parent in inheritances:
        dot_code += f'  {child.upper()} -> {parent.upper()} [arrowhead=empty];\n'

    # Add association classes
    i = 0
    for assoc_class in association_classes:
        card_s = ""
        card_t = ""
        for association in associations:
            card_s = association[1]
            card_t = association[2]
            if association[0] == assoc_class[0] and association[3] == assoc_class[1]:
                associations.remove(association)
        source, target, assoc = assoc_class
        dot_code += f'  dummy{i} [shape=point, width=0];\n'
        dot_code += f'  edge [arrowhead=none];\n  {source.upper()} -> dummy{i} [taillabel="{card_s}"];\n'
        dot_code += f'  edge [arrowhead=none];\n  dummy{i} -> {target.upper()} [headlabel="{card_t}"];\n'
        dot_code += f'  edge [arrowhead=none style=dashed];\n  dummy{i} -> {assoc.upper()};\n'
        i += 1

    # Add associations
    for source, card_s, card_t, target in associations:
        dot_code += f'  edge [arrowhead=none style=solid];\n  {source.upper()} -> {target.upper()} [headlabel="{card_t}" taillabel="{card_s}"];\n'

    # Add compositions
    for source, card_s, card_t, target in compositions:
        dot_code += f'  edge [arrowhead=none dir=back arrowtail=diamond style=solid];\n  {source.upper()} -> {target.upper()} [headlabel="{card_t}" taillabel="{card_s}"];\n'

    dot_code += "}\n"
    return dot_code
