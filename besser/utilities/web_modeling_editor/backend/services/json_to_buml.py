import re
from fastapi import HTTPException
from besser.BUML.metamodel.structural import DomainModel, Class, Enumeration, Property, Method, BinaryAssociation, \
    Generalization, PrimitiveDataType, EnumerationLiteral, Multiplicity, UNLIMITED_MAX_MULTIPLICITY, Constraint, \
    AssociationClass
from besser.utilities.web_modeling_editor.backend.constants.constants import VISIBILITY_MAP, VALID_PRIMITIVE_TYPES

def parse_attribute(attribute_name, domain_model=None):
    """Parse an attribute string to extract visibility, name, and type, removing any colons."""
    parts = attribute_name.replace(":", "").split()  # Remove colons from the attribute name
    if len(parts) == 1:
        visibility = "public"
        name = parts[0]
        attr_type = "str"
    else:
        visibility_symbol = parts[0] if parts[0] in VISIBILITY_MAP else "+"
        visibility = VISIBILITY_MAP.get(visibility_symbol, "public")  # Default to "public"
        name = parts[1] if len(parts) > 1 else "Unnamed"

        # Check if type is specified
        if len(parts) > 2:
            type_name = parts[2]
            # Check if type is an enumeration in the domain model
            if domain_model and any(isinstance(t, Enumeration) and t.name == type_name for t in domain_model.types):
                attr_type = type_name  # Keep the enumeration type name
            else:
                # Convert to primitive type if not an enumeration
                attr_type = VALID_PRIMITIVE_TYPES.get(type_name.lower(), "str")
        else:
            attr_type = "str"  # Default to "str" if no type specified

    return visibility, name, attr_type


def parse_method(method_str, domain_model=None):
    """
    Parse a method string to extract visibility, name, parameters, and return type.
    Examples:
    "+ notify(sms: str = 'message')" -> ("public", "notify", [{"name": "sms", "type": "str", "default": "message"}], None)
    "- findBook(title: str): Book" -> ("private", "findBook", [{"name": "title", "type": "str"}], "Book")
    "validate()" -> ("public", "validate", [], None)
    """

    # Default values
    visibility = "public"
    parameters = []
    return_type = None

    # Check if this is actually a method (contains parentheses)
    if '(' not in method_str:
        return visibility, method_str, parameters, return_type

    # Extract visibility if present
    method_str = method_str.strip()
    if method_str.startswith(tuple(VISIBILITY_MAP.keys())):
        visibility = VISIBILITY_MAP.get(method_str[0], "public")
        method_str = method_str[2:].strip()

    # Parse method using regex
    pattern = r"([^(]+)\((.*?)\)(?:\s*:\s*(.+))?"
    match = re.match(pattern, method_str)

    if not match:
        return visibility, method_str.replace("()", ""), parameters, return_type

    method_name, params_str, return_type = match.groups()
    method_name = method_name.strip()

    # Parse parameters if present
    if params_str:
        # Handle nested parentheses in default values
        param_list = []
        current_param = []
        paren_count = 0

        for char in params_str + ',':
            if char == '(' and paren_count >= 0:
                paren_count += 1
                current_param.append(char)
            elif char == ')' and paren_count > 0:
                paren_count -= 1
                current_param.append(char)
            elif char == ',' and paren_count == 0:
                param_list.append(''.join(current_param).strip())
                current_param = []
            else:
                current_param.append(char)

        for param in param_list:
            if not param:
                continue

            param_dict = {'name': param, 'type': 'any'}

            # Handle parameter with default value
            if '=' in param:
                param_parts = param.split('=', 1)
                param_name_type = param_parts[0].strip()
                default_value = param_parts[1].strip().strip('"\'')

                if ':' in param_name_type:
                    param_name, param_type = [p.strip() for p in param_name_type.split(':')]
                    param_dict.update({
                        'name': param_name,
                        'type': VALID_PRIMITIVE_TYPES.get(param_type.lower(), param_type),
                        'default': default_value
                    })
                else:
                    param_dict.update({
                        'name': param_name_type,
                        'default': default_value
                    })

            # Handle parameter with type annotation
            elif ':' in param:
                param_name, param_type = [p.strip() for p in param.split(':')]

                # Handle the type
                if domain_model and any(isinstance(t, (Enumeration, Class)) and t.name == param_type for t in domain_model.types):
                    type_param = param_type
                else:
                    type_param = VALID_PRIMITIVE_TYPES.get(param_type.lower(), None)
                    if type_param is None:
                        raise ValueError(f"Invalid type '{param_type}' for the parameter '{param_name}'")

                param_dict.update({
                    'name': param_name,
                    'type': type_param
                })
            else:
                param_dict['name'] = param.strip()

            parameters.append(param_dict)

    # Clean up return type if present
    if return_type:
        return_type = return_type.strip()
        # Keep the original return type if it's not a primitive type
        if domain_model and any(isinstance(t, (Enumeration, Class)) and t.name == return_type for t in domain_model.types):
            type_return = return_type
        else:
            type_return = VALID_PRIMITIVE_TYPES.get(return_type.lower(), None)
            if type_return is None:
                raise ValueError(f"Invalid return type '{return_type}' for the method '{method_name}'")

    return visibility, method_name, parameters, return_type

def parse_multiplicity(multiplicity_str):
    """Parse a multiplicity string and return a Multiplicity object with defaults."""
    if not multiplicity_str:
        return Multiplicity(min_multiplicity=1, max_multiplicity=1)

    # Handle single "*" case
    if multiplicity_str == "*":
        return Multiplicity(min_multiplicity=0, max_multiplicity=UNLIMITED_MAX_MULTIPLICITY)

    parts = multiplicity_str.split("..")
    try:
        min_multiplicity = int(parts[0]) if parts[0] and parts[0] != "*" else 0
        max_multiplicity = (
            UNLIMITED_MAX_MULTIPLICITY if len(parts) > 1 and (not parts[1] or parts[1] == "*")
            else int(parts[1]) if len(parts) > 1
            else min_multiplicity
        )
    except ValueError:
        # If parsing fails, return default multiplicity of 1..1
        return Multiplicity(min_multiplicity=1, max_multiplicity=1)

    return Multiplicity(min_multiplicity=min_multiplicity, max_multiplicity=max_multiplicity)

def process_ocl_constraints(ocl_text: str, domain_model: DomainModel, counter: int) -> tuple[list, list]:
    """Process OCL constraints and convert them to BUML Constraint objects."""
    if not ocl_text:
        return [], []

    constraints = []
    warnings = []
    lines = re.split(r'[,]', ocl_text)
    constraint_count = 1

    domain_classes = {cls.name.lower(): cls for cls in domain_model.types}

    for line in lines:

        line = line.strip().replace('\n', '')
        if not line or not line.lower().startswith('context'):
            continue

        # Extract context class name
        parts = line.split()
        if len(parts) < 4:  # Minimum: "context ClassName inv name:"
            continue

        context_class_name = parts[1]
        context_class = domain_classes.get(context_class_name.lower())

        if not context_class:
            warning_msg = f"Warning: Context class {context_class_name} not found"
            warnings.append(warning_msg)
            continue

        constraint_name = f"constraint_{context_class_name}_{counter}_{constraint_count}"
        constraint_count += 1

        constraints.append(
            Constraint(
                name=constraint_name,
                context=context_class,
                expression=line,
                language="OCL"
            )
        )

    return constraints, warnings

def generate_unique_class_name(base_name, existing_names):
    """Generate a unique class name by appending a number if necessary."""
    # If base_name is "Class", always add a number
    if base_name == "Class":
        counter = 1
        while f"{base_name}{counter}" in existing_names:
            counter += 1
        return f"{base_name}{counter}"

    # For other names, only add number if name exists
    if base_name not in existing_names:
        return base_name

    counter = 1
    while f"{base_name}{counter}" in existing_names:
        counter += 1
    return f"{base_name}{counter}"



def process_class_diagram(json_data):
    """Process Class Diagram specific elements."""
    title = json_data.get('title', '')
    if ' ' in title:
        title = title.replace(' ', '_')

    domain_model = DomainModel(title)
    # Get elements and OCL constraints from the JSON data
    elements = json_data.get('model', {}).get('elements', {})
    relationships = json_data.get('model', {}).get('relationships', {})

    # FIRST PASS: Process all type declarations (enumerations and classes)
    # 1. First process enumerations
    for element_id, element in elements.items():
        if element.get("type") == "Enumeration":
            element_name = element.get("name", "").strip()
            if not element_name or any(char.isspace() for char in element_name):
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid enumeration name: '{element_name}'. Names cannot contain whitespace or be empty."
                )
            literals = set()
            for literal_id in element.get("attributes", []):
                literal = elements.get(literal_id)
                if literal:
                    literal_obj = EnumerationLiteral(name=literal.get("name", ""))
                    literals.add(literal_obj)
            enum = Enumeration(name=element_name, literals=literals)
            domain_model.types.add(enum)
    
    # 2. Then create all class structures without attributes or methods
    for element_id, element in elements.items():
        if element.get("type") in ["Class", "AbstractClass"]:
            class_name = element.get("name", "").strip()
            if not class_name or any(char.isspace() for char in class_name):
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid class name: '{class_name}'. Names cannot contain whitespace or be empty."
                )
            
            is_abstract = element.get("type") == "AbstractClass"
              # Handle metadata with description and URI
            metadata = None
            description = element.get("description")
            uri = element.get("uri")
            
            if description or uri:
                #metadata = Metadata(description=description, uri=uri)
                print()
            try:
                #cls = Class(name=class_name, is_abstract=is_abstract, metadata=metadata)
                cls = Class(name=class_name, is_abstract=is_abstract)
                domain_model.types.add(cls)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))

    # SECOND PASS: Now add attributes and methods to classes
    for element_id, element in elements.items():
        if element.get("type") in ["Class", "AbstractClass"]:
            class_name = element.get("name", "").strip()
            cls = domain_model.get_class_by_name(class_name)
            
            if not cls:
                continue  # Skip if class wasn't created successfully in first pass
                
            # Add attributes
            attribute_names = set()
            for attr_id in element.get("attributes", []):
                attr = elements.get(attr_id)
                if attr:
                    visibility, name, attr_type = parse_attribute(attr.get("name", ""), domain_model)
                    if name is None:  # Skip if no name was returned
                        continue
                    if name in attribute_names:
                        raise HTTPException(status_code=400, detail=f"Duplicate attribute name '{name}' found in class '{class_name}'")
                    attribute_names.add(name)
                    
                    # Find the type in the domain model
                    type_obj = None
                    for t in domain_model.types:
                        if isinstance(t, (Enumeration, Class)) and t.name == attr_type:
                            type_obj = t
                            break
                    
                    if type_obj:
                        property_ = Property(name=name, type=type_obj, visibility=visibility)
                    else:
                        property_ = Property(name=name, type=PrimitiveDataType(attr_type), visibility=visibility)
                    cls.attributes.add(property_)

            # Add methods
            for method_id in element.get("methods", []):
                method = elements.get(method_id)
                if method:
                    visibility, name, parameters, return_type = parse_method(method.get("name", ""), domain_model)

                    # Create method parameters
                    method_params = []
                    for param in parameters:
                        param_type_obj = None
                        param_type_name = param['type']
                        
                        # Try to find parameter type in domain model
                        for t in domain_model.types:
                            if isinstance(t, (Enumeration, Class)) and t.name == param_type_name:
                                param_type_obj = t
                                break
                                
                        if not param_type_obj:
                            param_type_obj = PrimitiveDataType(param_type_name)
                            
                        param_obj = Property(
                            name=param['name'],
                            type=param_type_obj,
                            visibility='public'
                        )
                        if 'default' in param:
                            param_obj.default_value = param['default']
                        method_params.append(param_obj)

                    # Create method with parameters and return type
                    method_obj = Method(
                        name=name,
                        visibility=visibility,
                        parameters=method_params
                    )
                    
                    # Handle return type
                    if return_type:
                        return_type_obj = None
                        # Find return type in domain model
                        for t in domain_model.types:
                            if isinstance(t, (Enumeration, Class)) and t.name == return_type:
                                return_type_obj = t
                                break
                                
                        if return_type_obj:
                            method_obj.type = return_type_obj
                        else:
                            method_obj.type = PrimitiveDataType(return_type)
                    
                    cls.methods.add(method_obj)

    # Processing relationships (Associations, Generalizations, and Compositions)
    # Store association classes candidates and their links for third pass processing
    association_class_candidates = {}  # {class_id: {association_id}}
    association_by_id = {}  # {association_id: association_object}

    for rel_id, relationship in relationships.items():
        rel_type = relationship.get("type")
        source = relationship.get("source")
        target = relationship.get("target")

        if not rel_type or not source or not target:
            print(f"Skipping relationship {rel_id} due to missing data.")
            continue

        # Skip OCL links
        if rel_type == "ClassOCLLink":
            continue

        # Handle ClassLinkRel (association class links) later
        if rel_type == "ClassLinkRel":
            source_element_id = source.get("element")
            target_element_id = target.get("element")
            
            # Check if source is a class and target is a relationship
            if source_element_id in elements and target_element_id in relationships:
                # Source is a class, target is an association
                if source_element_id not in association_class_candidates:
                    association_class_candidates[source_element_id] = set()
                association_class_candidates[source_element_id].add(target_element_id)
            
            # Check if target is a class and source is a relationship
            elif target_element_id in elements and source_element_id in relationships:
                # Target is a class, source is an association
                if target_element_id not in association_class_candidates:
                    association_class_candidates[target_element_id] = set()
                association_class_candidates[target_element_id].add(source_element_id)
                
            continue

        # Retrieve source and target elements
        source_element = elements.get(source.get("element"))
        target_element = elements.get(target.get("element"))

        if not source_element or not target_element:
            print(f"Skipping relationship {rel_id} due to missing elements.")
            continue

        source_class = domain_model.get_class_by_name(source_element.get("name", ""))
        target_class = domain_model.get_class_by_name(target_element.get("name", ""))

        if not source_class or not target_class:
            print(f"Skipping relationship {rel_id} because classes are missing in the domain model.")
            continue

        # Handle each type of relationship
        if rel_type == "ClassBidirectional" or rel_type == "ClassUnidirectional" or rel_type == "ClassComposition" or rel_type == "ClassAggregation" :
            is_composite = rel_type == "ClassComposition"
            source_navigable = rel_type != "ClassUnidirectional"
            target_navigable = True

            source_multiplicity = parse_multiplicity(source.get("multiplicity", "1"))
            target_multiplicity = parse_multiplicity(target.get("multiplicity", "1"))

            source_role = source.get("role")
            if not source_role:
                source_role = source_class.name.lower()
                existing_roles = {end.name for assoc in domain_model.associations for end in assoc.ends}

                if source_role in existing_roles:
                    counter = 1
                    while f"{source_role}_{counter}" in existing_roles:
                        counter += 1
                    source_role = f"{source_role}_{counter}"

            source_property = Property(
                name=source_role,
                type=source_class,
                multiplicity=source_multiplicity,
                is_navigable=source_navigable
            )

            target_role = target.get("role")
            if not target_role:
                target_role = target_class.name.lower()
                existing_roles = {end.name for assoc in domain_model.associations for end in assoc.ends}

                if target_role in existing_roles:
                    counter = 1
                    while f"{target_role}_{counter}" in existing_roles:
                        counter += 1
                    target_role = f"{target_role}_{counter}"

            target_property = Property(
                name=target_role,
                type=target_class,
                multiplicity=target_multiplicity,
                is_navigable=target_navigable,
                is_composite=is_composite
            )

            association_name = relationship.get("name") or f"{source_class.name}_{target_class.name}"

            # Check if association name already exists and add increment if needed
            if association_name in [assoc.name for assoc in domain_model.associations]:
                counter = 1
                while f"{association_name}_{counter}" in [assoc.name for assoc in domain_model.associations]:
                    counter += 1
                association_name = f"{association_name}_{counter}"

            association = BinaryAssociation(
                name=association_name,
                ends={source_property, target_property}
            )
            domain_model.associations.add(association)

            # Store the association for association class processing
            association_by_id[rel_id] = association

        elif rel_type == "ClassInheritance":
            generalization = Generalization(general=target_class, specific=source_class)
            domain_model.generalizations.add(generalization)

    # THIRD PASS: Process association classes
    for class_id, association_ids in association_class_candidates.items():
        class_element = elements.get(class_id)
        if not class_element:
            continue

        class_name = class_element.get("name", "")
        class_obj = domain_model.get_class_by_name(class_name)

        if not class_obj:
            continue

        # An association class should only be linked to one association
        if len(association_ids) > 1:
            print(f"Warning: Class '{class_name}' is linked to multiple associations. Only using the first one.")

        # Get the first association
        association_id = next(iter(association_ids))
        association = association_by_id.get(association_id)

        if not association:
            continue

        # Get attributes and methods from the original class
        attributes = class_obj.attributes
        methods = class_obj.methods

        # Create the association class with attributes and methods
        association_class = AssociationClass(
            name=class_name,
            attributes=attributes,
            association=association
        )

        # Add methods to the association class if they exist
        if methods:
            association_class.methods = methods

        # Update the domain model - remove the regular class and add the association class
        domain_model.types.discard(class_obj)
        domain_model.types.add(association_class)

    # Process OCL constraints
    all_constraints = set()
    all_warnings = []
    constraint_counter = 0
    for element_id, element in elements.items():
        if element.get("type") in ["ClassOCLConstraint"]:
            ocl = element.get("constraint")
            if ocl:
                try:
                    new_constraints, warnings = process_ocl_constraints(ocl, domain_model, constraint_counter)
                    all_constraints.update(new_constraints)
                    all_warnings.extend(warnings)
                    constraint_counter += 1
                except Exception as e:
                    error_msg = f"Error processing OCL constraint for element {element_id}: {e}"
                    all_warnings.append(error_msg)
                    continue    # Attach warnings to domain model for later use
    domain_model.ocl_warnings = all_warnings
    domain_model.constraints = all_constraints

    # Store the association_by_id mapping for object diagram processing
    domain_model.association_by_id = association_by_id

    return domain_model