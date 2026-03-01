from .configuration import split_camel_case, correct_article, plural, name_format, is_similar

##############Class vs Attribute ##############
def generate_class_with_single_association_question(uml_associated_class, uml_relationship):
    uml_class_name = ''
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

    question = f"""Should {attribute_name} be modeled as a separate class associated with {uml_class.name}, or as a simple representation within {uml_class.name}?

For example:
1. {attribute_name.capitalize()} is a separate class with attributes: {sub_attrs_str}. This allows users to query and filter by individual {attribute_name} properties.
2. {attribute_name.capitalize()} is modeled as a simple represntation in {uml_class.name}. This is suitable when {attribute_name} details are not needed.
Which option is better for you?
"""
    opt1 = f"Option 1: The {uml_associated_class.name} is a separate class with its own attributes."
    opt2 = f"Option 2: The {attribute_name} is a simple representation in {uml_class.name}."
    return question, opt1, opt2


def generate_attribute_question(uml_class, uml_attribute):
    uml_class_name = split_camel_case(uml_class.name).lower()
    attribute_name = split_camel_case(uml_attribute.name).lower()

    article_uml_class_name = f"{correct_article('a', uml_class_name)} {uml_class_name}"
    article_attribute_name = f"{correct_article('a', attribute_name)} {attribute_name}"

    question = f"""Should {uml_attribute.name} be modeled as a separate class associated with {uml_class.name}, or remain as a simple representation?

For example:
1. {attribute_name.capitalize()} is a separate class with its own attributes. This allows users to query and filter by individual {attribute_name} properties.
2. {attribute_name.capitalize()} is modeled as a simple representation in {uml_class.name}. This is suitable when {attribute_name} details are not needed.

Which option is better for you?
"""
    opt1 = f"Option 1: The {attribute_name.capitalize()} is a separate class with its own attributes."
    opt2 = f"Option 2: The {attribute_name} is a simple representation in {uml_class.name}."
    return question, opt1, opt2

##############Enumeration vs Inheritance##############

def generate_subclass_with_no_attributes_question(uml_superclass, uml_subclasses):
    uml_class_name = uml_superclass.name.lower()
    attribute = 'type'
    literals = [split_camel_case(sc.name).lower() for sc in uml_subclasses]
    literals_str = ", ".join(literals[:-1]) + " and " + literals[-1]
    literals_or_str = ", ".join(literals[:-1]) + " or " + literals[-1]
    subclass_names = [sc.name for sc in uml_subclasses]
    subclass_names_str = ", ".join(subclass_names[:-1]) + " and " + subclass_names[-1]

    question = f"""Should {literals_str} be represented as separate subclasses of {uml_superclass.name}, or as instances of {uml_superclass.name} distinguished by an enumeration attribute?
Consider whether these types have distinct attributes or behavior.

For example:
1. {subclass_names_str} are modeled as separate subclasses of {uml_superclass.name}. Each subclass can have its own specific attributes and methods.
2. A single {uml_superclass.name} class with a Type enumeration attribute with literals: {literals_or_str}. All types share the same structure.

Which option is better for you?
"""
    opt1 = f"Option 1: Use inheritance, create separate subclasses for {literals_str}."
    opt2 = f"Option 2: Use enumeration {uml_superclass.name} type with with literals: {literals_or_str}."
    return question, opt1, opt2

def generate_enumeration_question(uml_class, uml_enumeration):
    uml_class_name = uml_class.name.lower()
    attribute = [split_camel_case(at.name).lower() for at in uml_class.attributes if \
                 (at.name.lower() == uml_enumeration.name.lower() or \
                 at.type.lower() == uml_enumeration.name.lower())][0]
    literals = [split_camel_case(l).lower() for l in uml_enumeration.literals]
    literals_str = ", ".join(literals[:-1]) + " and " + literals[-1]
    literals_or_str = ", ".join(literals[:-1]) + " or " + literals[-1]

    question = f"""Should the different types of {plural(uml_class_name)} ({literals_str}) be represented as separate subclasses, or as instances distinguished by an enumeration attribute?
Consider whether these types require distinct attributes or behavior.

For example:
1. {literals_str.capitalize()} are modeled as separate subclasses of {uml_class.name}. Each subclass can define its own specific attributes and methods.
2. A single {uml_class.name} class with a {uml_enumeration.name} enumeration attribute with literals: {literals_or_str}. All types share the same structure.

Which option is better for you?
"""
    opt1 = f"Option 1: Use inheritance, create separate subclasses for {literals_str}."
    opt2 = f"Option 2: Use enumeration {uml_enumeration.name} with literals: {literals_or_str}."
    return question, opt1, opt2

##############Attribute vs Inheritance##############

def generate_single_empty_subclass_question(parent, subclass):
    parent_class_name = split_camel_case(parent.name).lower()
    subclass_name = split_camel_case(subclass.name).lower()
    article_parent_class = f"{correct_article('a', parent_class_name)} {parent_class_name}"
    article_subclass = f"{correct_article('a', subclass_name)} {subclass_name}"

    question = f"""Should {subclass_name} be modeled as a subclass of {parent_class_name}, or is it better to keep a simple boolean like {parent.name} in {plural(subclass_name)}?
Consider whether {subclass_name} has or will have distinct attributes or behavior.

For example:
1. {subclass_name.capitalize()} is a subclass of {parent.name}. This allows {subclass_name} to have its own specific attributes and methods.
2. {parent_class_name.capitalize()} has a boolean attribute  {subclass_name} to identify {plural(subclass_name)}. All instances share the same structure.

Which option is better for you?
"""
    opt1 = f"Option 1: Use inheritance, {subclass_name} as a subclass of {parent_class_name}."
    opt2 = f"Option 2: Use {subclass_name} as a boolean attribute of {parent_class_name}."
    return question, opt1, opt2


def generate_boolean_attributes_question(uml_class, uml_attribute):
    class_name = split_camel_case(uml_class.name).lower()
    attribute_name = split_camel_case(uml_attribute.name).lower()
    article_class = f"{correct_article('a', class_name)} {class_name}"
    article_attribute = f"{correct_article('a', attribute_name)} {attribute_name}"

    question = f"""Should {plural(attribute_name)} be modeled as a subclass of {class_name}, or is it better to keep a simple boolean like {class_name} in {attribute_name} to distinguish them?
Consider whether {plural(attribute_name)} have or will have distinct attributes or behavior.

For example:
1. {attribute_name.capitalize()} is a subclass of {class_name}. This allows {plural(attribute_name)} to have their own specific attributes and methods.
2. {attribute_name.capitalize()} is an attribute in class {class_name}. All instances share the same structure, with the attribute indicating the type.

Which option is better for you?
"""
    opt1 = f"Option 1: Use inheritance, {attribute_name.capitalize()} as a subclass of{class_name}."
    opt2 = f"Option 2: Use {attribute_name} as a boolean attribute of  {class_name}."
    return question, opt1, opt2


##############Concrete Class vs Abstract Class##############

def generate_abstract_superclass_question(uml_class, subclasses):
    uml_class_name = uml_class.name.lower()
    sub_classes = [split_camel_case(sub.name).lower() for sub in subclasses]
    subclass_names = [sub.name for sub in subclasses]
    if len(sub_classes) == 1:
        sub_classes_str = sub_classes[0]
        subclass_names_str = subclass_names[0]
    else:
        sub_classes_str = ", ".join(sub_classes[0:-1]) + " or " + sub_classes[-1]
        subclass_names_str = ", ".join(subclass_names[0:-1]) + " or " + subclass_names[-1]

    article_sub_classes_str = f"{correct_article('a', sub_classes[0])} {sub_classes_str}"
    article_uml_class_name = f"{correct_article('a', uml_class_name)} {uml_class_name}"

    question = f"""Should {uml_class.name} be modeled as an abstract class or as a concrete class?
Consider whether {uml_class.name} can be instantiated directly, or only through its subclasses ({subclass_names_str}).

For example:
1. Concrete class {uml_class.name} that can be instantiated. Class {plural(uml_class_name)} can exist independently.
2. Abstract class {uml_class.name} that cannot be instantiated. Every {uml_class_name} must be a specific type {sub_classes_str}.

Which option is better for you?
"""
    opt1 = f"Option 1: Concrete class {uml_class.name} that can be instantiated directly."
    opt2 = f"Option 2: Abstract class {uml_class.name}, where only the subclasses can be instantiated."
    return question, opt1, opt2


def generate_concrete_superclass_question(uml_class, subclasses):
    uml_class_name = uml_class.name.lower()
    sub_classes = [split_camel_case(sub.name).lower() for sub in subclasses]
    subclass_names = [sub.name for sub in subclasses]
    if len(sub_classes) == 1:
        sub_classes_str = sub_classes[0]
        subclass_names_str = subclass_names[0]
    else:
        sub_classes_str = ", ".join(sub_classes[0:-1]) + " or " + sub_classes[-1]
        subclass_names_str = ", ".join(subclass_names[0:-1]) + " or " + subclass_names[-1]

    article_sub_classes_str = f"{correct_article('a', sub_classes[0])} {sub_classes_str}"
    article_uml_class_name = f"{correct_article('a', uml_class_name)} {uml_class_name}"

    question = f"""Should {uml_class.name} be modeled as an abstract class or as a concrete class?
Consider whether {uml_class.name} can be instantiated directly, or only through its subclasses ({subclass_names_str}).

For example:
1. Concrete class  {uml_class.name} ithat can be instantiated. Class {plural(uml_class_name)} can exist independently.
2. Abstract class  {uml_class.name} that cannot be instantiated. Every {uml_class_name} must be a specific type {sub_classes_str}.

Which option is better for you?
"""
    opt1 = f"Option 1: Concrete class {uml_class.name} that can be instantiated directly."
    opt2 = f"Option 2: Abstract class {uml_class.name}, where only the subclasses can be instantiated."
    return question, opt1, opt2

##############Composition vs Association##############

def generate_association_question(rel):
    source_class_name = split_camel_case(rel.source.name).lower()
    target_class_name = split_camel_case(rel.target.name).lower()
    article_source_class = f"{correct_article('a', source_class_name)} {source_class_name}"
    article_target_class = f"{correct_article('a', target_class_name)} {target_class_name}"

    question = f"""Should the relationship between {rel.source.name} and {rel.target.name} be modeled as a composition or as an association?

For example:
1. Use composition, {rel.target.name} would depend on {rel.source.name} for its existence.
2. Use association, {rel.target.name} could exist independently of {rel.source.name}, and can also be linked to multiple {plural(source_class_name)}.

Which option is better for you?
"""
    opt1 = f"Option 1: Composition is needed because class {rel.target.name} depends on {rel.source.name}."
    opt2 = f"Option 2: Association is sufficient because class {rel.target.name} exists independently of {rel.source.name}."
    return question, opt1, opt2

##############Lowerbound Cardinality: 0 vs 1##############

def generate_target_lowerbound_cardinality_zero_question(rel):
    source_class_name = split_camel_case(rel.source.name).lower()
    target_class_name = split_camel_case(rel.target.name).lower()
    article_source_class = f"{correct_article('a', source_class_name)} {source_class_name}"
    article_target_class = f"{correct_article('a', target_class_name)} {target_class_name}"

    question = f"""What is the minimum cardinality of {rel.target.name} in the relationship with {rel.source.name}?

For example:
1. Minimum cardinality of zero, {article_source_class} can exist without any associated {target_class_name}.
2. Minimum cardinality of one, {article_source_class} must have at least one associated {target_class_name}.

Which option is better for you?
"""
    opt1 = f"Option 1: Zero as minimum cardinality, {rel.source.name} can exist without {rel.target.name}."
    opt2 = f"Option 2: One as minimum cardinality,{rel.source.name} must have at least one {rel.target.name}."
    return question, opt1, opt2


def generate_source_lowerbound_cardinality_zero_question(rel):
    source_class_name = split_camel_case(rel.source.name).lower()
    target_class_name = split_camel_case(rel.target.name).lower()
    article_source_class = f"{correct_article('a', source_class_name)} {source_class_name}"
    article_target_class = f"{correct_article('a', target_class_name)} {target_class_name}"

    question = f"""What is the minimum cardinality of {rel.source.name} in the relationship with {rel.target.name}?

For example:
1. Minimum cardinality of zero, {article_target_class} can exist without any associated {source_class_name}.
2. Minimum cardinality of one, {article_target_class} must have at least one associated {source_class_name}.

Which option is better for you?
"""
    opt1 = f"Option 1: Zero as minimum cardinality, {rel.target.name} can exist without {rel.source.name}."
    opt2 = f"Option 2: One as minimum cardinality, {rel.target.name} must have at least one {rel.source.name}."
    return question, opt1, opt2


def generate_target_lowerbound_cardinality_one_question(rel):
    source_class_name = split_camel_case(rel.source.name).lower()
    target_class_name = split_camel_case(rel.target.name).lower()
    article_source_class = f"{correct_article('a', source_class_name)} {source_class_name}"
    article_target_class = f"{correct_article('a', target_class_name)} {target_class_name}"

    question = f"""What is the minimum cardinality of {rel.target.name} in the relationship with {rel.source.name}?

For example:
1. Minimum cardinality of zero, {article_source_class} can exist without any associated {target_class_name}.
2. Minimum cardinality of one, {article_source_class} must have at least one associated {target_class_name}.

Which option is better for you?
"""
    opt1 = f"Option 1: Zero as minimum cardinality, {rel.source.name} can exist without {rel.target.name}."
    opt2 = f"Option 2: One as minimum cardinality, {rel.source.name} must have at least one {rel.target.name}."
    return question, opt1, opt2


def generate_source_lowerbound_cardinality_one_question(rel):
    source_class_name = split_camel_case(rel.source.name).lower()
    target_class_name = split_camel_case(rel.target.name).lower()
    article_source_class = f"{correct_article('a', source_class_name)} {source_class_name}"
    article_target_class = f"{correct_article('a', target_class_name)} {target_class_name}"

    question = f"""What is the minimum cardinality of {rel.source.name} in the relationship with {rel.target.name}?

For example:
1. Minimum cardinality of zero, {article_target_class} can exist without any associated {source_class_name}.
2. Minimum cardinality of one, {article_target_class} must have at least one associated {source_class_name}.

Which option is better for you?
"""
    opt1 = f"Option 1: Zero as minimum cardinality, {rel.target.name} can exist without {rel.source.name}."
    opt2 = f"Option 2: One as minimum cardinality,{rel.target.name} must have at least one {rel.source.name}."
    return question, opt1, opt2

##############Upperbound Cardinality: 1 vs Many (*)##############

def generate_target_upperbound_cardinality_one_question(rel):
    source_class_name = split_camel_case(rel.source.name).lower()
    target_class_name = split_camel_case(rel.target.name).lower()
    article_source_class = f"{correct_article('a', source_class_name)} {source_class_name}"
    article_target_class = f"{correct_article('a', target_class_name)} {target_class_name}"

    question = f"""What is the maximum cardinality of {rel.target.name} in the relationship with {rel.source.name}?

For example:
1. Maximum cardinality of one, {article_source_class} is associated with exactly one {target_class_name}.
2. Maximum cardinality of many, {article_source_class} can be associated with multiple {plural(target_class_name)}.

Which option is better for you?
"""
    opt1 = f"Option 1: One as maximun cardinality, each {source_class_name} links to one {target_class_name}."
    opt2 = f"Option 2: Many as maximun cardinality, each {source_class_name} can link to multiple {plural(target_class_name)}."
    return question, opt1, opt2


def generate_source_upperbound_cardinality_one_question(rel):
    source_class_name = split_camel_case(rel.source.name).lower()
    target_class_name = split_camel_case(rel.target.name).lower()
    article_source_class = f"{correct_article('a', source_class_name)} {source_class_name}"
    article_target_class = f"{correct_article('a', target_class_name)} {target_class_name}"

    question = f"""What is the maximum cardinality of {rel.source.name} in the relationship with {rel.target.name}?

For example:
1. Maximum cardinality of one, {article_target_class} is associated with exactly one {source_class_name}.
2. Maximum cardinality of many, {article_target_class} can be associated with multiple {plural(source_class_name)}.

Which option is better for you?
"""
    opt1 = f"Option 1: One as maximun cardinality, each {target_class_name} links to one {source_class_name}."
    opt2 = f"Option 2: Many as maximun cardinality, each {target_class_name} can link to multiple {plural(source_class_name)}."
    return question, opt1, opt2


def generate_target_upperbound_cardinality_many_question(rel):
    source_class_name = split_camel_case(rel.source.name).lower()
    target_class_name = split_camel_case(rel.target.name).lower()
    article_source_class = f"{correct_article('a', source_class_name)} {source_class_name}"
    article_target_class = f"{correct_article('a', target_class_name)} {target_class_name}"

    question = f"""What is the maximum cardinality of {rel.target.name} in the relationship with {rel.source.name}?

For example:
1. Maximum cardinality of one, {article_source_class} is associated with exactly one {target_class_name}.
2. Maximum cardinality of many, {article_source_class} can be associated with multiple {plural(target_class_name)}.

Which option is better for you?
"""
    opt1 = f"Option 1: One as maximun cardinality, each {source_class_name} links to one {target_class_name}."
    opt2 = f"Option 2: Many as maximun cardinality, each {source_class_name} can link to multiple {plural(target_class_name)}."
    return question, opt1, opt2


def generate_source_upperbound_cardinality_many_question(rel):
    source_class_name = split_camel_case(rel.source.name).lower()
    target_class_name = split_camel_case(rel.target.name).lower()
    article_source_class = f"{correct_article('a', source_class_name)} {source_class_name}"
    article_target_class = f"{correct_article('a', target_class_name)} {target_class_name}"

    question = f"""What is the maximum cardinality of {rel.source.name} in the relationship with {rel.target.name}?

For example:
1. Maximum cardinality of one, {article_target_class} is associated with exactly one {source_class_name}.
2. Maximum cardinality of many, {article_target_class} can be associated with multiple {plural(source_class_name)}.

Which option is better for you?
"""
    opt1 = f"Option 1: One as maximun cardinality, each {target_class_name} links to one {source_class_name}."
    opt2 = f"Option 2: Many as maximun cardinality, each {target_class_name} can link to multiple {plural(source_class_name)}."
    return question, opt1, opt2

##############Association Class vs Class##############

def generate_many_to_many_association_class_question(rel, asc_cls):
    source_class_name = split_camel_case(rel.source.name).lower()
    target_class_name = split_camel_case(rel.target.name).lower()
    association_class = split_camel_case(asc_cls.name).lower()
    article_source_class = f"{correct_article('a', source_class_name)} {source_class_name}"
    article_target_class = f"{correct_article('a', target_class_name)} {target_class_name}"
    article_association_class = f"{correct_article('a', association_class)} {association_class}"

    question = f"""Should {asc_cls.name} be modeled as an association class linking {rel.source.name} and {rel.target.name}, or as a regular class with two separate associations?

For example:
1. Association class: {asc_cls.name} exists only as part of the relationship between {rel.source.name} and {rel.target.name}. A {association_class} cannot exist without the link between {rel.source.name} and {rel.target.name}.
2. Regular class: {asc_cls.name} is a class that has links to {rel.source.name} and {rel.target.name}. In this case multiple {plural(association_class)} can exist for every {rel.source.name} and {rel.target.name}.


Which option is better for you?
"""
    opt1 = f"Option 1: Association class, {asc_cls.name} as association class linking {rel.source.name} and {rel.target.name}."
    opt2 = f"Option 2: Regular class, {asc_cls.name} as separate class with two associations."
    return question, opt1, opt2

##############Attribute vs Enumeration##############

def generate_string_attribute_question(uml_class, uml_attribute, uml_enumeration):
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

    question = f"""Should the {attribute_name} in {class_name} be modeled as a an attribute which allows free text input, or as an enumeration with predefined literals?

For example:
1. Use {attribute_name} as string attribute in {class_name}, which allows any text value.
2. Use {attribute_name} as an enumeration which uses predefined values in literals: {literals_or_str}.

Which option is better for you?
"""
    opt1 = f"Option 1: String attribute that allows any text value for {uml_attribute.name}."
    opt2 = f"Option 2: Enumeration {uml_attribute.name} with predefined values: {literals_str}."
    return question, opt1, opt2


def generate_enumeration_attribute_question(uml_class, uml_attribute, uml_enumeration):
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

    question = f"""Should the attribute {attribute_name} in {class_name} be modeled as a an attribute which allows free text input, or as an enumeration with predefined literals?

For example:
1. Use {enum_name} as string attribute in {uml_class.name}, which allows any text value.
2. Use {enum_name} as an enumeration which uses predefined values in literals: ({literals_or_str}).

Which option is better for you?
"""
    opt1 = f"Option 1: String attribute that allows any text value for {enum_name}."
    opt2 = f"Option 2: Enumeration {enum_name} with predefined values: {literals_str}."
    return question, opt1, opt2

##############Class Generalization##############

def generate_common_attributes_question(child_classes, common_attributes, parent_name):
    class_names = [split_camel_case(cls.name).lower() for cls in child_classes]
    class_names_original = [cls.name for cls in child_classes]
    if len(class_names) == 2:
        class_list = f"{class_names[0]} and {class_names[1]}"
        class_list_original = f"{class_names_original[0]} and {class_names_original[1]}"
    else:
        class_list = ", ".join(class_names[:-1]) + f", and {class_names[-1]}"
        class_list_original = ", ".join(class_names_original[:-1]) + f", and {class_names_original[-1]}"

    attr_names = [split_camel_case(attr.name).lower() for attr in common_attributes]
    if len(attr_names) == 1:
        attr_list = f"{attr_names[0]}"
    elif len(attr_names) == 2:
        attr_list = f"{attr_names[0]} and {attr_names[1]}"
    else:
        attr_list = ", ".join(attr_names[:-1]) + f", and {attr_names[-1]}"

    parent_name_lower = split_camel_case(parent_name).lower()

    question = f"""Should a generalization hierarchy be introduced between classes {class_list_original} that share the following attributes: {attr_list}?

For example:
1. Generalization is not needed, the classes {class_list_original} maintains independent attributes.
2. Generalization is neede to use a common superclass {parent_name} containing the shared attributes {attr_list}. This removes duplication in subclasses {class_list_original}.

Which option is better for you?
"""

    option_1 = f"Option 1: Generalization is not needed, keep attributes ({attr_list}) duplicated in each class."
    option_2 = f"Option 2: Generalization is needed, create {parent_name} superclass with shared attributes, {class_list_original} as subclasses."

    return question, option_1, option_2


def generate_common_enum_type_question(child_classes, common_attributes, parent_name):
    class_names = [split_camel_case(cls.name).lower() for cls in child_classes]
    class_names_original = [cls.name for cls in child_classes]
    if len(class_names) == 2:
        class_list = f"{class_names[0]} and {class_names[1]}"
        class_list_original = f"{class_names_original[0]} and {class_names_original[1]}"
    else:
        class_list = ", ".join(class_names[:-1]) + f", and {class_names[-1]}"
        class_list_original = ", ".join(class_names_original[:-1]) + f", and {class_names_original[-1]}"

    attr_names = [split_camel_case(attr.name).lower() for attr in common_attributes]
    if len(attr_names) == 2:
        attr_list = f"{attr_names[0]} and {attr_names[1]}"
    else:
        attr_list = ", ".join(attr_names[:-1]) + f", and {attr_names[-1]}"
    attr_type = split_camel_case(common_attributes[0].type).lower()
    parent_name_lower = split_camel_case(parent_name).lower()

    question = f"""Should a generalization hierarchy be introduced between classes {class_list_original} that share the following attributes: {attr_list}?

For example:
1. Use the attributes {attr_list} separated. The classes {class_list_original} maintains independent attributes.
2. Use a common superclass {parent_name} containing the shared attributes {attr_list}. This removes duplication in subclasses {class_list_original}.

Which option is better for you?
"""

    option_1 = f"Option 1: Generalization is not needed, keep attributes {attr_list} duplicated in each class."
    option_2 = f"Option 2: Generalization is needed, create {parent_name} superclass with shared attributes, and {class_list_original} as subclasses."

    return question, option_1, option_2

##############Element Relevance##############

def generate_class_relevance_question(uml_class):
    element_name = split_camel_case(uml_class.name).lower()

    question = f"""Is {element_name} a relevant domain concept that should be included in the model?

For example:
1. {element_name.capitalize()} is a relevant concept in this domain and should be represented in the model.
2. {element_name.capitalize()} does not correspond to any relevant domain concept and should be removed from the model.

Which option is better for you?
"""
    option_1 = f"Option 1: Keep {element_name}, it is a relevant domain concept."
    option_2 = f"Option 2: Remove {element_name}, it is not relevant."

    return question, option_1, option_2


def generate_attribute_relevance_question(parent_class, uml_attribute):
    parent_name = split_camel_case(parent_class.name).lower()
    element_name = split_camel_case(uml_attribute.name).lower()

    question = f"""Is {element_name} a relevant attribute of {parent_name} that should be included in the model?

For example:
1. {element_name.capitalize()} captures important domain information about {parent_name}.
2. {element_name.capitalize()} does not represent important domain information for {parent_name}.

Which option is better for you?
"""
    option_1 = f"Option 1: Keep {element_name}, it is relevant information for {parent_name}."
    option_2 = f"Option 2: Remove {element_name}, it is not a relevant information."

    return question, option_1, option_2
