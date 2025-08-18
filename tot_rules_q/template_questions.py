from configuration import split_camel_case, correct_article, plural, name_format, is_similar

##############Class vs Attribute ##############
def generate_class_with_single_association_question(uml_associated_class, uml_relationship):
    #attribute_name = uml_class.attributes[0]  # Pick the first attribute for simplicity
    uml_class_name=''
    if uml_relationship.source.name == uml_associated_class.name:
        uml_class = uml_relationship.target
    else:
        uml_class = uml_relationship.source
    uml_class_name = split_camel_case(uml_class.name).lower()
    attribute_name = split_camel_case(uml_associated_class.name).lower()
    sub_attrs = [split_camel_case(a.name).lower() for a in uml_associated_class.attributes]
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
    sub_attrs = []#[a.name for a in uml_associated_class.attributes]
    sub_attrs_str = "detail"#ask llm?
    #sub_attrs = extract_subattributes(attribute_name)
    #sub_attrs_str = ", ".join(sub_attrs)

    article_uml_class_name = f"{correct_article('a', uml_class_name)} {uml_class_name}"
    article_attribute_name = f"{correct_article('a', attribute_name)} {attribute_name}"

    question = f"""We know that each {uml_class_name} has {article_attribute_name}. When we think about {attribute_name}, is it just a simple piece of information, like a line of text? 
Or is {attribute_name} made up of different parts that might be important?
For example:
1. For each {attribute_name}, the {sub_attrs_str} information is saved separately, so users can filter {uml_class_name} by {sub_attrs_str}.
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
2. Every {uml_class_name} {attribute} is classified as either {literals_or_str}. Both {plural(attribute)} have the same details, and there’s no need for extra information.

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
    literals = [l.lower() for l in uml_enumeration.literals]
    literals_str = ", ".join(literals[:-1]) + " and " + literals[-1]
    literals_or_str = ", ".join(literals[:-1]) + " or " + literals[-1]
    
    #question = f"""There are different {plural(attribute)} for {plural(uml_class_name)}: {literals_str}. Do these {plural(attribute)} have distinct characteristics or requirements?
    question = f"""There are different {plural(attribute)}: {literals_str}. Do these {plural(attribute)} have distinct characteristics or requirements?
For example:
1. {literals_str.capitalize()} are considered different {plural(attribute)}, allowing for distinct details for each {attribute}.
2. Every {uml_class_name} {attribute} is classified as either {literals_or_str}. Both {plural(attribute)} have the same details, and there’s no need for extra information.

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
    parent_class_name = parent.name.lower()
    subclass_name = split_camel_case(subclass.name).lower()
    article_parent_class = f"{correct_article('a', parent_class_name)} {parent_class_name}"
    article_subclass = f"{correct_article('a', subclass_name)} {subclass_name}"

    question = f"""When thinking about {plural(parent_class_name)}, what makes {article_subclass} different from a regular one? \
Is there a specific role or responsibility that comes with being {article_subclass}? Are there additional factors we need to consider when dealing with {plural(subclass_name)} compared to regular {plural(parent_class_name)}?

For example:
1. {article_subclass.capitalize()} is treated as a different kind of {parent_class_name}.
2. {plural(parent_class_name).capitalize()} include a status that identifies if it is {article_subclass} or not.

Which option is better for you?
"""
    """
    Choice 1: {plural(subclass_name).capitalize()} are a special kind of {parent_class_name}.
    Choice 2: {plural(subclass_name).capitalize()} are similar to other {plural(parent_class_name)}.
    """
    opt1 = f"Option 1: {plural(subclass_name).capitalize()} are a special kind of {parent_class_name}.."
    opt2 = f"Option 2: {plural(subclass_name).capitalize()} are similar to other {plural(parent_class_name)}."
    return question, opt1, opt2


def generate_boolean_attributes_question(uml_class, uml_attribute):
    class_name = uml_class.name.lower()
    attribute_name = split_camel_case(uml_attribute.name).lower()
    article_class = f"{correct_article('a', class_name)} {class_name}"
    article_attribute = f"{correct_article('a', attribute_name)} {attribute_name}"

    question = f"""When thinking about {plural(class_name)}, what makes {article_attribute} different from a regular one? \
Is there a specific role or responsibility that comes with being {article_attribute}? Are there additional factors we need to consider when dealing with {plural(attribute_name)} compared to regular {plural(class_name)}?

For example:
1. {article_attribute.capitalize()} is treated as a different kind of {class_name}.
2. {plural(class_name).capitalize()} include a status that identifies if it is {article_attribute} or not.

Which option is better for you?
"""
    """
    Choice 1: {plural(attribute_name).capitalize()} are a special kind of {class_name}.
    Choice 2: {plural(attribute_name).capitalize()} are similar to other {plural(class_name)}.
    """
    opt1 = f"Option 1: {plural(attribute_name).capitalize()} are a special kind of {class_name}."
    opt2 = f"Option 2: {plural(attribute_name).capitalize()} are similar to other {plural(class_name)}."
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

    question = f"""When we talk about {plural(uml_class_name)}, do we always have a clear idea of a specific example, or do we sometimes speak about it in a more general way? Should we think of {uml_class.name} as a general concept that covers all possible forms, or is it always tied to a particular type or instance?

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

    question = f"""Does {article_target_class} always require {article_source_class} to exist, or could it exist independently and possibly be linked to multiple {plural(source_class_name)} instances? \
If {article_source_class} is removed, would all the associated {plural(target_class_name)} also need to be removed, or could a {target_class_name} still make sense on its own?

For example:
1. {article_target_class.capitalize()} belongs to {article_source_class} and cannot exist without a specific {source_class_name}.
2. {article_target_class.capitalize()} is linked to {article_source_class} but can exist independently of it.

Which option is better for you?
"""
    """Option 1: A {target_class_name} is always for a specific {source_class_name}.
    Option 2: A {target_class_name} is independent and can still exist even if the {source_class_name} is removed.
    """
    opt1 = f"Option 1: A {target_class_name} is always for a specific {source_class_name}."
    opt2 = f"Option 2: A {target_class_name} is independent and can still exist even if the {source_class_name} is removed."
    return question, opt1, opt2

##############Lowerbound Cardinality: 0 vs 1##############

def generate_target_lowerbound_cardinality_zero_question(rel):
    source_class_name = split_camel_case(rel.source.name).lower()
    target_class_name = split_camel_case(rel.target.name).lower()
    article_source_class = f"{correct_article('a', source_class_name)} {source_class_name}"
    article_target_class = f"{correct_article('a', target_class_name)} {target_class_name}"
    question = f"""In the context of {article_source_class}, does it always involve at least one {target_class_name}, or can it exist without any?.
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
    #source_class_name = rel.source.name.lower()
    #target_class_name = rel.target.name.lower()
    source_class_name = split_camel_case(rel.source.name).lower()
    target_class_name = split_camel_case(rel.target.name).lower()
    article_source_class = f"{correct_article('a', source_class_name)} {source_class_name}"
    article_target_class = f"{correct_article('a', target_class_name)} {target_class_name}"
    question = f"""In the context of a {target_class_name}, does it always involve at least one {source_class_name}, or can it exist without any?.
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
    question = f"""In the context of {article_source_class}, does it always involve at least one {target_class_name}, or can it exist without any?.
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
    question = f"""In the context of a {target_class_name}, does it always involve at least one {source_class_name}, or can it exist without any?.
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
    source_class_name = rel.source.name.lower()
    target_class_name = rel.target.name.lower()
    # Heuristic for naming association class: combine both class names
    #association_class = f"{source_class}_{target_class}_link"
    association_class = asc_cls.name.lower()
    article_source_class = f"{correct_article('a', source_class_name)} {source_class_name}"
    article_target_class = f"{correct_article('a', target_class_name)} {target_class_name}"
    article_association_class = f"{correct_article('a', association_class)} {association_class}"

#Should we think of the relationship between {article_source_class} and {article_target_class} as something that only exists when {article_association_class} happens? \
    question = f"""{article_source_class.capitalize()} has multiple {plural(association_class)} at different {plural(target_class_name)}. \
Should we think of the link between {article_source_class} and {article_target_class} as something that only exists when {article_association_class} happens? \
Or would you say {article_source_class} and {article_target_class} should have a link even outside of specific {plural(association_class)}?
For example:
1. {article_source_class.capitalize()} has a direct link with {article_target_class}. \
The {association_class} is a separate event that connects the {source_class_name} and {target_class_name} temporarily.
2. The {association_class} is the key event that establishes the link between {article_source_class} and {article_target_class}. \
The {source_class_name} and {target_class_name} are only linked when {article_association_class} occurs.


Which option is better for you?
"""
    """Choice 1: {article_source_class.capitalize()} and {article_target_class} are always linked, even when no {association_class} happens.
    Choice 2: The {source_class_name} and the {target_class_name} are linked only when {article_association_class} happens.
    """
    opt1 = f"Option 1: {article_source_class.capitalize()} and {article_target_class} are always linked, even when no {association_class} happens."
    opt2 = f"Option 2: The {source_class_name} and the {target_class_name} are linked only when {article_association_class} happens."
    return question, opt1, opt2