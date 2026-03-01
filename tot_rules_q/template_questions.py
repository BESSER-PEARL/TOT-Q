from .configuration import split_camel_case, correct_article, plural, name_format, is_similar

##############Class vs Attribute ##############
def generate_class_with_single_association_question(uml_associated_class, uml_relationship):
    uml_class_name=''
    if uml_relationship.source.name == uml_associated_class.name:
        uml_class = uml_relationship.target
    else:
        uml_class = uml_relationship.source
    uml_class_name = split_camel_case(uml_class.name).lower()
    attribute_name = split_camel_case(uml_associated_class.name).lower()
    sub_attrs = [split_camel_case(a.name).lower() for a in uml_associated_class.attributes]
    if len(sub_attrs) == 0:
      sub_attrs_str = ""
    elif len(sub_attrs) == 1:
        sub_attrs_str = sub_attrs[0]
    else:
        sub_attrs_str = ", ".join(sub_attrs[:-1]) + " and " + sub_attrs[-1]
    
    article_uml_class_name = f"{correct_article('a', uml_class_name)} {uml_class_name}"
    article_attribute_name = f"{correct_article('a', attribute_name)} {attribute_name}"

    question = f"""We know that each {uml_class_name} has {article_attribute_name}. When we think about {attribute_name}, is it just a simple piece of information, like a line of text? 
Or is {attribute_name} made up of different parts that might be important?
For example:
1. For each {attribute_name}, the {sub_attrs_str} information is saved separately, so users can filter {plural(uml_class_name)} by {sub_attrs_str}.
2. The {attribute_name} is a single piece of text. This works well when we just need to show the {attribute_name}.

Which option is better for you?
"""
    """Option 1: We need the {attribute_name} details separately
    Option 2: A single line of text for {attribute_name} is enough
    """
    opt1 = f"Option 1: We need the {attribute_name} details separately."
    opt2 = f"Option 2: A single line of text for {attribute_name} is enough."
    return question, opt1, opt2


def generate_attribute_question(uml_class, uml_attribute):
    uml_class_name = split_camel_case(uml_class.name).lower()
    attribute_name = split_camel_case(uml_attribute.name).lower()
    article_uml_class_name = f"{correct_article('a', uml_class_name)} {uml_class_name}"
    article_attribute_name = f"{correct_article('a', attribute_name)} {attribute_name}"

    question = f"""We know that each {uml_class_name} has {article_attribute_name}. When we think about {attribute_name}, is it just a simple piece of information, like a line of text? 
Or is {attribute_name} made up of different parts that might be important?
For example:
1. For each {attribute_name}, the information is saved separately, so users can filter {uml_class_name}.
2. The {attribute_name} is a single piece of text. This works well when we just need to show the {attribute_name}.

Which option is better for you?
"""
    """Option 1: We need the {attribute_name} details separately.
    Option 2: A single line of text for {attribute_name} is enough.
    """
    opt1 = f"Option 1: We need the {attribute_name} details separately."
    opt2 = f"Option 2: A single line of text for {attribute_name} is enough."
    return question, opt1, opt2

##############Enumeration vs Inheritance##############

def generate_subclass_with_no_attributes_question(uml_superclass, uml_subclasses):
    uml_class_name = uml_superclass.name.lower()
    attribute = 'type' ## check with llm?
    literals = [split_camel_case(sc.name).lower() for sc in uml_subclasses]
    literals_str = ", ".join(literals[:-1]) + " and " + literals[-1]
    literals_or_str = ", ".join(literals[:-1]) + " or " + literals[-1]
    
    
    question = f"""There are different {plural(attribute)} for {plural(uml_class_name)}: {literals_str}. Do these {plural(attribute)} have distinct characteristics or requirements?
For example:
1. {literals_str.capitalize()} are considered different {plural(attribute)}, allowing for distinct details for each {attribute}.
2. Every {uml_class_name} {attribute} is classified as either {literals_or_str}. All {plural(attribute)} have the same details, and there’s no need for extra information.

Which option is better for you?
"""
    """Option 1: {literals_str.capitalize()} do have distinct characteristics.
    Option 2: {literals_str.capitalize()} doesn't have distinct characteristics.
    """
    opt1 = f"Option 1: {literals_str.capitalize()} do have distinct characteristics."
    opt2 = f"Option 2: {literals_str.capitalize()} doesn't have distinct characteristics."
    return question, opt1, opt2


def generate_enumeration_question(uml_class, uml_enumeration):
    uml_class_name = uml_class.name.lower()
    attribute = [split_camel_case(at.name).lower() for at in uml_class.attributes if \
                 (at.name.lower() == uml_enumeration.name.lower() or \
                 at.type.lower() == uml_enumeration.name.lower())][0]
    literals = [l.replace('_', ' ').lower() for l in uml_enumeration.literals]
    literals_str = ", ".join(literals[:-1]) + " and " + literals[-1]
    literals_or_str = ", ".join(literals[:-1]) + " or " + literals[-1]
    
    question = f"""There are different {plural(attribute)}: {literals_str}. Do these {plural(attribute)} have distinct characteristics or requirements?
For example:
1. {literals_str.capitalize()} are considered different {plural(attribute)}, allowing for distinct details for each {attribute}.
2. Every {uml_class_name} {attribute} is classified as either {literals_or_str}. All {plural(attribute)} have the same details, and there’s no need for extra information.

Which option is better for you?
"""
    """Option 1: {literals_str.capitalize()} do have distinct characteristics.
    Option 2: {literals_str.capitalize()} doesn't have distinct characteristics.
    """
    opt1 = f"Option 1: {literals_str.capitalize()} do have distinct characteristics."
    opt2 = f"Option 2: {literals_str.capitalize()} doesn't have distinct characteristics."
    return question, opt1, opt2

##############Attribute vs Inheritance##############

def generate_single_empty_subclass_question(parent, subclass):
    parent_class_name = split_camel_case(parent.name).lower()
    subclass_name = split_camel_case(subclass.name).lower()
    article_parent_class = f"{correct_article('a', parent_class_name)} {parent_class_name}"
    article_subclass = f"{correct_article('a', subclass_name)} {subclass_name}"

    question = f"""
When thinking about {plural(parent_class_name)}, how should we represent {article_subclass}? 

Does being {article_subclass} involve additional information that a regular {parent_class_name} does not have, 
or is it enough to label it as {article_subclass}?

For example:
1. {article_subclass.capitalize()} is a separate kind of {parent_class_name}, because it may have additional information.
2. {plural(parent_class_name).capitalize()} include a status to indicate whether it is {article_subclass} or not.

Which option best reflects the situation?
"""
    opt1 = f"Option 1: {plural(subclass_name).capitalize()} are a special kind of {parent_class_name}."
    opt2 = f"Option 2: {plural(subclass_name).capitalize()} are similar to other {plural(parent_class_name)}."

    """
    Choice 1: {plural(subclass_name).capitalize()} are a special kind of {parent_class_name}.
    Choice 2: {plural(subclass_name).capitalize()} are similar to other {plural(parent_class_name)}.
    """
    return question, opt1, opt2


def generate_boolean_attributes_question(uml_class, uml_attribute):
    class_name = split_camel_case(uml_class.name).lower()
    attribute_name = split_camel_case(uml_attribute.name).lower()
    article_class = f"{correct_article('a', class_name)} {class_name}"
    article_attribute = f"{correct_article('a', attribute_name)} {attribute_name}"
    
    question = f"""
When thinking about {plural(class_name)}, how should we represent {article_attribute}? 

Does being {article_attribute} involve additional information that a regular {class_name} does not have, 
or is it enough to label it as {article_attribute}?

For example:
1. {article_attribute.capitalize()} is a separate kind of {class_name}, because it may have additional information.
2. {plural(class_name).capitalize()} include a status to indicate whether it is {article_attribute} or not.

Which option best reflects the situation?
"""
    opt1 = f"Option 1: {plural(article_attribute).capitalize()} are a special kind of {class_name}."
    opt2 = f"Option 2: {plural(article_attribute).capitalize()} are similar to other {plural(class_name)}."

    return question, opt1, opt2


##############Concrete Class vs Abstract Class##############

def generate_abstract_superclass_question(uml_class, subclasses):
    uml_class_name = uml_class.name.lower()
    sub_classes = [split_camel_case(sub.name).lower() for sub in subclasses]
    if len(sub_classes) == 1:
        sub_classes_str = sub_classes[0]
    else:
        sub_classes_str = ", ".join(sub_classes[0:-1]) + " or " + sub_classes[-1]
    
    article_sub_classes_str = f"{correct_article('a', sub_classes[0])} {sub_classes_str}"
    article_uml_class_name = f"{correct_article('a', uml_class_name)} {uml_class_name}"

    question = f"""Thinking about {uml_class_name}, and its kinds: {sub_classes_str}. Is it possible to have a {uml_class_name} that is not one of those specific types?

For example:
1. There are some {plural(uml_class_name)} that are not part of the kinds {sub_classes_str}.
2. Every {uml_class_name} must be of a specific kind {sub_classes_str}.

Which option is better for you?
"""
    opt1 = f"Option 1: Some {plural(uml_class_name)} exists that is not of the kind {sub_classes_str}."
    opt2 = f"Option 2: Every {uml_class_name} is of a specific kind {sub_classes_str}."
    return question, opt1, opt2

def generate_concrete_superclass_question(uml_class, subclasses):
    uml_class_name = uml_class.name.lower()
    sub_classes = [split_camel_case(sub.name).lower() for sub in subclasses]
    if len(sub_classes) == 1:
        sub_classes_str = sub_classes[0]
    else:
        sub_classes_str = ", ".join(sub_classes[0:-1]) + " or " + sub_classes[-1]

    article_sub_classes_str = f"{correct_article('a', sub_classes[0])} {sub_classes_str}"
    article_uml_class_name = f"{correct_article('a', uml_class_name)} {uml_class_name}"

    question = f"""When we talk about {uml_class_name}, do we always have a clear idea of a specific example, or do we sometimes speak about it in a more general way? Should we think of {uml_class.name} as a general concept that covers all possible forms, or is it always tied to a particular type or instance?

For example:
1. A general {uml_class_name} can exist that is not {article_sub_classes_str}.
2. {article_uml_class_name.capitalize()} is just a concept and cannot exist on its own. We only need specific types like {sub_classes_str}.

Which option is better for you?
"""
    """Option 1: We should think of general {uml_class_name} independent of its types.
    Option 2: The general {uml_class_name} is not needed, and we only need its types.
    """
    opt1 = f"Option 1: We should think of general {uml_class_name} independent of its types."
    opt2 = f"Option 2: The general {uml_class_name} is not needed, and we only need its types."
    return question, opt1, opt2

##############Composition vs Association##############

def generate_association_question(rel):
    source_class_name = split_camel_case(rel.source.name).lower()
    target_class_name = split_camel_case(rel.target.name).lower()
    article_source_class = f"{correct_article('a', source_class_name)} {source_class_name}"
    article_target_class = f"{correct_article('a', target_class_name)} {target_class_name}"

    question = f"""Does {article_target_class} always require {article_source_class} to exist. 
If {article_source_class} is removed, would all the associated {plural(target_class_name)} also need to be removed?

For example:
1. {article_target_class.capitalize()} belongs to {article_source_class} and cannot exist on its own.
2. {article_target_class.capitalize()} is linked to {article_source_class} but can exist independently of it.

Which option is better for you?
"""
    
    opt1 = f"Option 1: A {target_class_name} always belongs to a {source_class_name}."
    opt2 = f"Option 2: A {target_class_name} is linked to {source_class_name} but can exist independently."
    return question, opt1, opt2

##############Lowerbound Cardinality: 0 vs 1##############

def generate_target_lowerbound_cardinality_zero_question(rel):
    source_class_name = split_camel_case(rel.source.name).lower()
    target_class_name = split_camel_case(rel.target.name).lower()
    article_source_class = f"{correct_article('a', source_class_name)} {source_class_name}"
    article_target_class = f"{correct_article('a', target_class_name)} {target_class_name}"
    #question = f"""In the context of {article_source_class}, does it always involve at least one {target_class_name}, or can it exist without any?
    question = f"""In the context of {article_source_class}, is it always associated with at least one {target_class_name}, or can it exist without any?
For example:
1. {article_source_class.capitalize()} can exist without any {target_class_name}.
2. {article_source_class.capitalize()} must have at least one {target_class_name}.

Which option is better for you?
"""
    """Option 1: {article_source_class.capitalize()} can exist without any {target_class_name}.
    Option 2: {article_source_class.capitalize()} must have at least one {target_class_name}.
    """
    opt1 = f"Option 1: {article_source_class.capitalize()} can exist without any {target_class_name}."
    opt2 = f"Option 2: {article_source_class.capitalize()} must have at least one {target_class_name}."
    return question, opt1, opt2


def generate_source_lowerbound_cardinality_zero_question(rel):
    source_class_name = split_camel_case(rel.source.name).lower()
    target_class_name = split_camel_case(rel.target.name).lower()
    article_source_class = f"{correct_article('a', source_class_name)} {source_class_name}"
    article_target_class = f"{correct_article('a', target_class_name)} {target_class_name}"
    question = f"""In the context of a {target_class_name}, is it always associated with at least one {source_class_name}, or can it exist without any?
For example:
1. {article_target_class.capitalize()} can exist without any {source_class_name}.
2. {article_target_class.capitalize()} must have at least one {source_class_name}.

Which option is better for you?
"""
    """Option 1: {article_target_class.capitalize()} can exist without any {source_class_name}.
    Option 2: {article_target_class.capitalize()} must have at least one {source_class_name}.
    """
    opt1 = f"Option 1: {article_target_class.capitalize()} can exist without any {source_class_name}."
    opt2 = f"Option 2: {article_target_class.capitalize()} must have at least one {source_class_name}."
    return question, opt1, opt2


def generate_target_lowerbound_cardinality_one_question(rel):
    source_class_name = split_camel_case(rel.source.name).lower()
    target_class_name = split_camel_case(rel.target.name).lower()
    article_source_class = f"{correct_article('a', source_class_name)} {source_class_name}"
    article_target_class = f"{correct_article('a', target_class_name)} {target_class_name}"
    question = f"""In the context of {article_source_class}, is it always association with at least one {target_class_name}, or can it exist without any?
For example:
1. {article_source_class.capitalize()} can exist without any {target_class_name}.
2. {article_source_class.capitalize()} must have at least one {target_class_name}.

Which option is better for you?
"""
    """Option 1: {article_source_class.capitalize()} can exist without any {target_class_name}.
    Option 2: {article_source_class.capitalize()} must have at least one {target_class_name}.
    """    
    opt1 = f"Option 1: {article_source_class.capitalize()} can exist without any {target_class_name}."
    opt2 = f"Option 2: {article_source_class.capitalize()} must have at least one {target_class_name}."
    return question, opt1, opt2


def generate_source_lowerbound_cardinality_one_question(rel):
    source_class_name = split_camel_case(rel.source.name).lower()
    target_class_name = split_camel_case(rel.target.name).lower()
    article_source_class = f"{correct_article('a', source_class_name)} {source_class_name}"
    article_target_class = f"{correct_article('a', target_class_name)} {target_class_name}"
    question = f"""In the context of a {target_class_name}, is it always association with at least one {source_class_name}, or can it exist without any?
For example:
1. {article_target_class.capitalize()} can exist without any {source_class_name}.
2. {article_target_class.capitalize()} must have at least one {source_class_name}.

Which option is better for you?
"""
    """Option 1: {article_target_class.capitalize()} can exist without any {source_class_name}.
    Option 2: {article_target_class.capitalize()} must have at least one {source_class_name}.
    """
    opt1 = f"Option 1: {article_target_class.capitalize()} can exist without any {source_class_name}."
    opt2 = f"Option 2: {article_target_class.capitalize()} must have at least one {source_class_name}."
    return question, opt1, opt2

##############Upperbound Cardinality: 1 vs Many (*)##############

def generate_target_upperbound_cardinality_one_question(rel):
    source_class_name = split_camel_case(rel.source.name).lower()
    target_class_name = split_camel_case(rel.target.name).lower()
    article_source_class = f"{correct_article('a', source_class_name)} {source_class_name}"
    article_target_class = f"{correct_article('a', target_class_name)} {target_class_name}"
    question = f"""In the context of {article_source_class}, can there be more than one {target_class_name} involved, or is it always associated with just one?

For example:
1. {article_source_class.capitalize()} is linked to a single {target_class_name}.
2. {article_source_class.capitalize()} is linked to multiple {plural(target_class_name)}.

Which option is better for you?
"""
    """Option 1: Each {source_class_name} is always linked to a single {target_class_name}.
    Option 2: {article_source_class.capitalize()} can be linked to multiple {plural(target_class_name)}.
    """
    opt1 = f"Option 1: Each {source_class_name} is always linked to a single {target_class_name}."
    opt2 = f"Option 2: {article_source_class.capitalize()} can be linked to multiple {plural(target_class_name)}."
    return question, opt1, opt2


def generate_source_upperbound_cardinality_one_question(rel):
    source_class_name = split_camel_case(rel.source.name).lower()
    target_class_name = split_camel_case(rel.target.name).lower()

    article_source_class = f"{correct_article('a', source_class_name)} {source_class_name}"
    article_target_class = f"{correct_article('a', target_class_name)} {target_class_name}"
    question = f"""In the context of {article_target_class}, can there be more than one {source_class_name} involved, or is it always associated with just one? 
For example:
1. {article_target_class.capitalize()} is linked to a single {source_class_name}.
2. {article_target_class.capitalize()} is linked to multiple {plural(source_class_name)}.

Which option is better for you?
"""
    """Option 1: Each {target_class_name} is always linked to a single {source_class_name}.
    Option 2: {article_target_class.capitalize()} can be linked to multiple {plural(source_class_name)}.
    """
    opt1 = f"Option 1: Each {target_class_name} is always linked to a single {source_class_name}."
    opt2 = f"Option 2: {article_target_class.capitalize()} can be linked to multiple {plural(source_class_name)}."
    return question, opt1, opt2


def generate_target_upperbound_cardinality_many_question(rel):
    source_class_name = split_camel_case(rel.source.name).lower()
    target_class_name = split_camel_case(rel.target.name).lower()
    article_source_class = f"{correct_article('a', source_class_name)} {source_class_name}"
    article_target_class = f"{correct_article('a', target_class_name)} {target_class_name}"
    question = f"""In the context of {article_source_class}, can there be more than one {target_class_name} involved, or is it always associated with just one?
For example:
1. {article_source_class.capitalize()} is linked to a single {target_class_name}.
2. {article_source_class.capitalize()} is linked to multiple {plural(target_class_name)}.

Which option is better for you?
"""
    """Option 1: Each {source_class_name} is always linked to a single {target_class_name}.
    Option 2: {article_source_class.capitalize()} can be linked to multiple {plural(target_class_name)}.
    """
    opt1 = f"Option 1: Each {source_class_name} is always linked to a single {target_class_name}."
    opt2 = f"Option 2: {article_source_class.capitalize()} can be linked to multiple {plural(target_class_name)}."
    return question, opt1, opt2


def generate_source_upperbound_cardinality_many_question(rel):
    source_class_name = split_camel_case(rel.source.name).lower()
    target_class_name = split_camel_case(rel.target.name).lower()
    article_source_class = f"{correct_article('a', source_class_name)} {source_class_name}"
    article_target_class = f"{correct_article('a', target_class_name)} {target_class_name}"
    question = f"""In the context of {article_target_class}, can there be more than one {source_class_name} involved, or is it always associated with just one? 
For example:
1. {article_target_class.capitalize()} is linked to a single {source_class_name}.
2. {article_target_class.capitalize()} is linked to multiple {plural(source_class_name)}.

Which option is better for you?
"""
    """Option 1: Each {target_class_name} is always linked to a single {source_class_name}.
    Option 2: {article_target_class.capitalize()} can be linked to multiple {plural(source_class_name)}.
    """
    opt1 = f"Option 1: Each {target_class_name} is always linked to a single {source_class_name}."
    opt2 = f"Option 2: {article_target_class.capitalize()} can be linked to multiple {plural(source_class_name)}."
    return question, opt1, opt2

##############Association Class vs Class##############

def generate_many_to_many_association_class_question(rel, asc_cls):
    source_class_name = split_camel_case(rel.source.name).lower()
    target_class_name = split_camel_case(rel.target.name).lower()
    association_class = split_camel_case(asc_cls.name).lower()
    article_source_class = f"{correct_article('a', source_class_name)} {source_class_name}"
    article_target_class = f"{correct_article('a', target_class_name)} {target_class_name}"
    article_association_class = f"{correct_article('a', association_class)} {association_class}"

    question = f"""The concept {association_class} potentially represents a link between {plural(source_class_name)} and {plural(target_class_name)}. \
How should we understand this connection?

For example:
1. {article_association_class.capitalize()} is a concept and a link that connects {article_source_class} and {article_target_class}. 
2. {article_association_class.capitalize()} is a concept, but it does not represent a link between {article_source_class} and {article_target_class}.

Which option is better for you?
"""
    opt1 = f"Option 1: The {association_class} is a concept and a link between {article_source_class} and {article_target_class}."
    opt2 = f"Option 2: The {association_class} does not represent a link between {article_source_class} and {article_target_class}."    

    return question, opt1, opt2

##############Attribute vs Enumeration##############

def generate_string_attribute_question(uml_class, uml_attribute, uml_enumeration):
    """Generate question for string attribute vs enumeration pattern (attribute already exists)."""
    class_name = split_camel_case(uml_class.name).lower()
    attribute_name = split_camel_case(uml_attribute.name).lower()
    enum_name = split_camel_case(uml_enumeration.name).lower()

    literals = [l.replace('_', ' ').lower() for l in uml_enumeration.literals]
    
    if len(literals) > 1:
        literals_str = ", ".join(literals[:-1]) + " and " + literals[-1]
        literals_or_str = ", ".join(literals[:-1]) + " or " + literals[-1]
    else:
        literals_str = literals[0] if literals else "value1, value2"
        literals_or_str = literals_str

    article_class = f"{correct_article('a', class_name)} {class_name}"
    article_attribute = f"{correct_article('a', attribute_name)} {attribute_name}"

    question = f"""When thinking about the {attribute_name} of {plural(class_name)}, are there only specific, predefined values it can have, or can it be any text?
For example:
1. The {attribute_name} can be any text value that users want to enter.
2. The {attribute_name} must be one of these specific values: {literals_or_str}.

Which option is better for you?
"""
    opt1 = f"Option 1: The {attribute_name} can be any text value."
    opt2 = f"Option 2: The {attribute_name} must be one of these: {literals_str}."
    return question, opt1, opt2


def generate_enumeration_attribute_question(uml_class, uml_attribute, uml_enumeration):
    """Generate question for enumeration vs string attribute pattern (enumeration already exists)."""
    class_name = split_camel_case(uml_class.name).lower()
    attribute_name = split_camel_case(uml_attribute.name).lower()
    enum_name = split_camel_case(uml_enumeration.name).lower()

    literals = [l.replace('_', ' ').lower() for l in uml_enumeration.literals]
    if len(literals) > 1:
        literals_str = ", ".join(literals[:-1]) + " and " + literals[-1]
        literals_or_str = ", ".join(literals[:-1]) + " or " + literals[-1]
    else:
        literals_str = literals[0] if literals else "value1, value2"
        literals_or_str = literals_str

    article_class = f"{correct_article('a', class_name)} {class_name}"

    question = f"""When thinking about {plural(class_name)}, should the {enum_name} be limited to specific predefined values ({literals_or_str}), or should it allow any text?
For example:
1. Users can enter any text for {enum_name}.
2. The {enum_name} must be one of these specific values: {literals_or_str}.

Which option is better for you?
"""
    opt1 = f"Option 1: Users can enter any text for {enum_name}."
    opt2 = f"Option 2: The {enum_name} must be one of these: {literals_str}."
    return question, opt1, opt2

##############Class Generalization##############

def generate_common_attributes_question(child_classes, common_attributes, parent_name):
    class_names = [split_camel_case(cls.name).lower() for cls in child_classes]
    if len(class_names) == 2:
        class_list = f"{class_names[0]} and {class_names[1]}"
    else:
        class_list = ", ".join(class_names[:-1]) + f", and {class_names[-1]}"

    attr_names = [split_camel_case(attr.name).lower() for attr in common_attributes]
    if len(attr_names) == 1:
        attr_list = f"{attr_names[0]}"
    elif len(attr_names) == 2:
        attr_list = f"{attr_names[0]} and {attr_names[1]}"
    else:
        attr_list = ", ".join(attr_names[:-1]) + f", and {attr_names[-1]}"

    parent_name_lower = split_camel_case(parent_name).lower()

    """question = fWe noticed that {class_list} share some information such as {attr_list}. How should we manage this common information?

For example: 
1. Keep them information separate, where each {class_list} have their own {attr_list} fields.
2. Introduce the concept {parent_name_lower} that centralizes the {attr_list} fields, which {class_list} then use.

Which option is better for you?\n
"""
   
    question = f"""Do the concepts ({class_list}) represent different kinds of a more general concept called {parent_name_lower}?.

For example: 
1. {class_list.capitalize()} are unrelated concepts, with no connection to {parent_name_lower}.
2. {class_list.capitalize()} are different kinds of {parent_name_lower}.

Which option is better for you?\n
    """   
    option_1 = (
        f"Option 1: Keep {class_list} as unrelated concepts."
    )

    option_2 = (
        f"Option 2: Create the concept {parent_name_lower}, with {class_list} as its kinds."
    )

    return question, option_1, option_2


def generate_common_enum_type_question(child_classes, common_attributes, parent_name):
    class_names = [split_camel_case(cls.name).lower() for cls in child_classes]
    if len(class_names) == 2:
        class_list = f"{class_names[0]} and {class_names[1]}"
    else:
        class_list = ", ".join(class_names[:-1]) + f", and {class_names[-1]}"

    # Format attribute names (different names)
    attr_names = [split_camel_case(attr.name).lower() for attr in common_attributes]
    if len(attr_names) == 2:
        attr_list = f"{attr_names[0]} and {attr_names[1]}"
    else:
        attr_list = ", ".join(attr_names[:-1]) + f", and {attr_names[-1]}"

    # Get the common enum type
    attr_type = split_camel_case(common_attributes[0].type).lower()
    parent_name_lower = split_camel_case(parent_name).lower()

    """question = fWe noticed that {class_list} share some information such as {attr_list}. How should we manage this common information?

For example: 
1. Keep them information separate, where each {class_list} have their own {attr_list} fields.
2. Introduce the concept {parent_name_lower} that centralizes the {attr_list} fields, which {class_list} then use.

Which option is better for you?\n
"""
    question = f"""Do the concepts ({class_list}) represent different kinds of a more general concept called {parent_name_lower}?.

For example: 
1. {class_list.capitalize()} are unrelated concepts, with no connection to {parent_name_lower}.
2. {class_list.capitalize()} are different kinds of {parent_name_lower}.

Which option is better for you?\n
"""   
    option_1 = (
        f"Option 1: Keep {class_list} as unrelated concepts."
    )

    option_2 = (
        f"Option 2: Create the concept {parent_name_lower}, with {class_list} as its kinds."
    )

    return question, option_1, option_2

##############Element Relevance##############

def generate_class_relevance_question(uml_class):
    element_name = split_camel_case(uml_class.name).lower()

    question = (
        f"When thinking about the domain, is {element_name} a relevant concept "
        f"that should be included in the model?\n\n"
        f"For example:\n"
        f"1. {element_name.capitalize()} is a key concept in this domain and should be modeled.\n"
        f"2. {element_name.capitalize()} is not relevant or seems like an error and should be removed.\n\n"
        f"Which option is better for you?\n"
    )
    option_1 = f"Option 1: {element_name.capitalize()} is relevant and should be kept."
    option_2 = f"Option 2: {element_name.capitalize()} is not relevant and should be removed."

    return question, option_1, option_2


def generate_attribute_relevance_question(parent_class, uml_attribute):
    parent_name = split_camel_case(parent_class.name).lower()
    element_name = split_camel_case(uml_attribute.name).lower()

    question = (
        f"When thinking about {parent_name}, is {element_name} a relevant "
        f"piece of information that should be tracked?\n\n"
        f"For example:\n"
        f"1. {element_name.capitalize()} is important information about {parent_name}.\n"
        f"2. {element_name.capitalize()} is not relevant or seems like an error.\n\n"
        f"Which option is better for you?\n"
    )
    option_1 = f"Option 1: {element_name} is relevant information."
    option_2 = f"Option 2: {element_name} is not relevant and should be removed."

    return question, option_1, option_2