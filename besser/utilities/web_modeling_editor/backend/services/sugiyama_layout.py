"""
Sugiyama-style hierarchical layout algorithm for class diagrams.
This implements the classic layered graph drawing algorithm used by PlantUML.

The algorithm consists of four main phases:
1. Layer Assignment (Rank Assignment)
2. Crossing Reduction (Node Ordering)
3. Coordinate Assignment (X-positioning)
4. Edge Routing
"""

import math
from typing import Dict, List, Tuple, Set, Optional
from collections import defaultdict, deque


class SugiyamaLayout:
    """
    Implements Sugiyama-style hierarchical layout algorithm.
    This provides deterministic, collision-free layouts for class diagrams.
    """

    def __init__(self,
                 layer_spacing: float = 175.0,  # Reduced by 30% from 250.0
                 node_spacing: float = 245.0,   # Reduced by 30% from 350.0
                 min_padding: float = 50.0):
        """
        Initialize the Sugiyama layout algorithm.

        Args:
            layer_spacing: Vertical spacing between layers
            node_spacing: Horizontal spacing between nodes in the same layer
            min_padding: Minimum padding around nodes
        """
        self.layer_spacing = layer_spacing
        self.node_spacing = node_spacing
        self.min_padding = min_padding

    def calculate_layout(self, elements: Dict, relationships: Dict) -> Tuple[Dict, Dict]:
        """
        Calculate layout using Sugiyama algorithm.

        Args:
            elements: Dictionary of elements with their current bounds
            relationships: Dictionary of relationships between elements

        Returns:
            Tuple of (updated elements dictionary, updated relationships dictionary)
        """
        # Filter only class-like elements
        main_elements = {
            eid: elem for eid, elem in elements.items()
            if elem.get('type') in ['Class', 'AbstractClass', 'Enumeration', 'ClassOCLConstraint']
            and elem.get('owner') is None
        }

        if len(main_elements) == 0:
            return elements, relationships

        # Phase 1: Layer Assignment
        graph = self._build_graph(main_elements, relationships)
        layers = self._assign_layers(main_elements, graph)

        # Phase 2: Crossing Reduction
        layers = self._reduce_crossings(layers, graph, main_elements)

        # Phase 3: Coordinate Assignment
        positioned_elements = self._assign_coordinates(main_elements, layers, graph)

        # Phase 3.5: Center siblings below their parents
        positioned_elements = self._center_siblings_under_parents(positioned_elements, main_elements, graph)

        # Phase 4: Update all elements (including children)
        updated_elements = self._update_elements(elements, main_elements, positioned_elements)

        # Phase 5: Update relationship directions based on new positions
        updated_relationships = self._update_relationship_directions(updated_elements, relationships)

        return updated_elements, updated_relationships

    def _build_graph(self, elements: Dict, relationships: Dict) -> Dict:
        """
        Build a directed graph from relationships.

        Returns:
            Graph structure with edges categorized by type
        """
        graph = {
            'nodes': set(elements.keys()),
            'inheritance_edges': [],  # Parent -> Child (downward)
            'association_edges': [],   # Bidirectional or unidirectional
            'directed_edges': [],      # Composition/Aggregation (for layer dependencies)
            'edges_out': defaultdict(list),  # Node -> [target nodes]
            'edges_in': defaultdict(list),   # Node -> [source nodes]
            'layering_edges_in': defaultdict(list),  # ONLY directed edges (for layer assignment)
        }

        for rel_id, rel in relationships.items():
            rel_type = rel.get('type')
            source = rel.get('source', {}).get('element')
            target = rel.get('target', {}).get('element')

            if not source or not target:
                continue

            if source not in graph['nodes'] or target not in graph['nodes']:
                continue

            if rel_type == 'ClassInheritance':
                # Inheritance: target (parent) should be above source (child)
                graph['inheritance_edges'].append((target, source))
                graph['edges_out'][target].append(source)
                graph['edges_in'][source].append(target)
                # Inheritance creates strict layering dependency
                graph['layering_edges_in'][source].append(target)
            elif rel_type in ['ClassComposition', 'ClassAggregation']:
                # Composition/Aggregation: directed relationship (container -> contained)
                # IMPORTANT: Unlike inheritance, composition does NOT require vertical hierarchy
                # Container and contained can be horizontally adjacent - no layering dependency needed
                # This allows much better horizontal space utilization
                graph['directed_edges'].append((source, target))
                graph['association_edges'].append((source, target))
                graph['edges_out'][source].append(target)
                graph['edges_out'][target].append(source)
                graph['edges_in'][source].append(target)
                graph['edges_in'][target].append(source)
                # DO NOT add to layering_edges_in - allow horizontal placement
            elif rel_type in ['ClassBidirectional', 'ClassUnidirectional']:
                # Pure associations: NO layering dependency (allows horizontal placement)
                # We still track them for path routing, but don't use for layer assignment
                graph['association_edges'].append((source, target))
                graph['edges_out'][source].append(target)
                graph['edges_out'][target].append(source)
                graph['edges_in'][source].append(target)
                graph['edges_in'][target].append(source)
                # CRITICAL: Do NOT add to layering_edges_in - this allows horizontal layout

        return graph

    def _assign_layers(self, elements: Dict, graph: Dict) -> List[List[str]]:
        """
        Phase 1: Assign nodes to layers (ranks).
        Uses longest path layering considering all relationships.
        """
        # Calculate layer for each node
        node_layers = {}

        # First, handle inheritance hierarchies (strict vertical ordering)
        if graph['inheritance_edges']:
            node_layers = self._layer_by_inheritance(graph)

        # Assign remaining nodes without inheritance based on associations
        unassigned = graph['nodes'] - set(node_layers.keys())

        if unassigned:
            # Use a greedy approach: place nodes to minimize edge spans
            # CRITICAL: Use layering_edges_in (only directed dependencies), NOT edges_in (all edges)
            # This allows nodes connected by bidirectional associations to be on the same layer
            # IMPORTANT: Assign ALL nodes with no dependencies to the SAME layer in each pass
            # This maximizes horizontal space utilization

            # Start from the next available layer after inheritance
            # If inheritance has already placed nodes, start after the max inheritance layer
            current_layer = max(node_layers.values()) + 1 if node_layers else 0

            while unassigned:
                # Find ALL nodes that can be placed in current layer
                # These are nodes whose directed dependencies are all in earlier layers
                nodes_for_this_layer = []

                for node in list(unassigned):
                    # Check if this node has DIRECTED dependencies not yet satisfied
                    # Use layering_edges_in instead of edges_in to ignore bidirectional associations
                    can_place_now = True
                    for neighbor in graph['layering_edges_in'][node]:
                        # Check if dependency is not placed yet, OR is in current/later layer
                        # For a node to be placed in current_layer, ALL its dependencies must be in EARLIER layers
                        if neighbor not in node_layers:
                            # Dependency not yet placed
                            can_place_now = False
                            break
                        if node_layers[neighbor] >= current_layer:
                            # Dependency is in current or later layer - can't place node yet
                            can_place_now = False
                            break

                    if can_place_now:
                        nodes_for_this_layer.append(node)

                # If no nodes can be placed, we have a cycle or error - place remaining nodes
                if not nodes_for_this_layer:
                    # Safety check: place all remaining nodes in next layer
                    for node in unassigned:
                        node_layers[node] = current_layer
                    break

                # Assign ALL nodes to this layer
                for node in nodes_for_this_layer:
                    node_layers[node] = current_layer
                    unassigned.remove(node)

                # Move to next layer
                current_layer += 1

                # Prevent infinite loop
                if current_layer > 10:
                    for node in unassigned:
                        node_layers[node] = current_layer
                    break

        # If there are still isolated nodes, place them
        for node in graph['nodes']:
            if node not in node_layers:
                node_layers[node] = 0

        # CRITICAL: DO NOT move association-only nodes to separate layers
        # This was causing excessive horizontal spacing in diagrams with inheritance
        # The adaptive spacing logic below will handle proper distribution
        # REMOVED the logic that moved enumerations and other non-inheritance nodes to separate layers

        # Spread layers intelligently based on inheritance and association structure
        if graph['inheritance_edges']:
            # Diagram HAS inheritance relationships - use smart spreading WITH adaptive max_per_layer
            # Identify which nodes are part of inheritance chains
            # These should be kept tightly packed vertically
            inheritance_nodes = set()
            for parent, child in graph['inheritance_edges']:
                inheritance_nodes.add(parent)
                inheritance_nodes.add(child)

            # Calculate adaptive max_per_layer based on total elements
            # This allows better horizontal space usage while preserving sibling grouping
            # IMPROVED: Scale more aggressively for larger diagrams to prevent excessive vertical growth
            total_elements = len(graph['nodes'])

            # Adaptive scaling for inheritance diagrams:
            # 1-3 elements: 2 per layer (very small diagrams - keep tight)
            # 4-6 elements: 3 per layer (small diagrams)
            # 7-9 elements: 4 per layer (medium diagrams)
            # 10-15 elements: 5 per layer (large diagrams)
            # 16+ elements: 6 per layer (very large diagrams - maximize horizontal space)
            if total_elements <= 3:
                max_per_layer_inheritance = 2
                max_per_layer_other = 2
            elif total_elements <= 6:
                max_per_layer_inheritance = 3
                max_per_layer_other = 3
            elif total_elements <= 9:
                max_per_layer_inheritance = 4
                max_per_layer_other = 4
            elif total_elements <= 15:
                max_per_layer_inheritance = 5
                max_per_layer_other = 4
            else:
                max_per_layer_inheritance = 6
                max_per_layer_other = 5

            # Apply spreading with adaptive limits
            # CRITICAL: siblings (children with same parent) MUST stay together on same layer
            node_layers = self._spread_dense_layers_smart(
                node_layers,
                inheritance_nodes,
                max_per_layer_inheritance=max_per_layer_inheritance,
                max_per_layer_other=max_per_layer_other
            )

            # Post-process: Fix hierarchy interruptions by moving non-inheritance nodes
            # that fall between parent and child in inheritance hierarchies
            node_layers = self._fix_hierarchy_interruptions(node_layers, graph)
        else:
            # For diagrams with NO inheritance, use adaptive spreading
            # Adjust max_per_layer based on total number of elements to optimize vertical space
            # More elements → more per layer → fewer layers → shorter vertical height
            total_elements = len(graph['nodes'])

            # Adaptive scaling:
            # 1-3 elements: 2 per layer (minimize horizontal spread)
            # 4-6 elements: 3 per layer (balanced)
            # 7+ elements: 4 per layer (maximize horizontal space usage)
            if total_elements <= 3:
                max_per_layer = 2
            elif total_elements <= 6:
                max_per_layer = 3
            else:
                max_per_layer = 4

            # Start from layer 0 (no reserved space for inheritance)
            node_layers = self._spread_dense_layers(node_layers, max_per_layer=max_per_layer, graph=graph)

        # Organize nodes into layer lists
        max_layer = max(node_layers.values()) if node_layers else 0
        layers = [[] for _ in range(max_layer + 1)]

        for node, layer in node_layers.items():
            layers[layer].append(node)

        return layers

    def _spread_dense_layers(self, node_layers: Dict[str, int], max_per_layer: int = 4, graph: Dict = None) -> Dict[str, int]:
        """
        Spread out layers that have too many nodes to improve vertical distribution.
        IMPROVED: Uses relationship density to keep highly-connected nodes together.
        """
        # Count nodes per layer
        layer_counts = defaultdict(list)
        for node, layer in node_layers.items():
            layer_counts[layer].append(node)

        # Redistribute nodes from dense layers
        new_node_layers = {}
        layer_offset = 0

        for layer in sorted(layer_counts.keys()):
            nodes_in_layer = layer_counts[layer]

            if len(nodes_in_layer) <= max_per_layer:
                # Keep layer as is
                for node in nodes_in_layer:
                    new_node_layers[node] = layer + layer_offset
            else:
                # Split into multiple sub-layers
                # IMPROVED: Sort nodes by relationship density (connection count) before splitting
                # This keeps highly-connected nodes together in earlier sublayers
                if graph:
                    # Calculate connection count for each node (both in and out)
                    node_connection_counts = []
                    for node in nodes_in_layer:
                        connection_count = len(graph.get('edges_in', {}).get(node, [])) + len(graph.get('edges_out', {}).get(node, []))
                        node_connection_counts.append((node, connection_count))

                    # Sort by connection count (descending) - most connected first
                    node_connection_counts.sort(key=lambda x: -x[1])
                    sorted_nodes = [node for node, _ in node_connection_counts]
                else:
                    # Fallback: use original order
                    sorted_nodes = nodes_in_layer

                num_sublayers = (len(sorted_nodes) + max_per_layer - 1) // max_per_layer
                for i, node in enumerate(sorted_nodes):
                    sublayer = i // max_per_layer
                    new_node_layers[node] = layer + layer_offset + sublayer

                # Add offset for next layers
                layer_offset += num_sublayers - 1

        return new_node_layers

    def _spread_dense_layers_smart(self, node_layers: Dict[str, int], inheritance_nodes: Set[str],
                                   max_per_layer_inheritance: int = 4,
                                   max_per_layer_other: int = 2) -> Dict[str, int]:
        """
        Spread out layers intelligently, treating inheritance-related nodes differently.
        Inheritance-related nodes can be packed more densely than unrelated nodes.
        Association-only nodes are placed to avoid interrupting inheritance hierarchies.

        CRITICAL CONSTRAINT: Siblings (children with same parent) MUST stay on the same layer.
        """
        # Build sibling groups from inheritance edges in the graph
        # This is needed to ensure siblings are never separated
        from collections import defaultdict
        parent_children_map = defaultdict(list)

        # We need to rebuild this from the graph, but we don't have direct access here
        # Instead, we'll identify potential siblings by checking their layer assignment
        # Siblings will have been assigned to the same layer by _layer_by_inheritance

        # Count nodes per layer, separating inheritance from non-inheritance nodes
        layer_info = defaultdict(lambda: {'inheritance': [], 'other': []})
        for node, layer in node_layers.items():
            if node in inheritance_nodes:
                layer_info[layer]['inheritance'].append(node)
            else:
                layer_info[layer]['other'].append(node)

        # Redistribute nodes from dense layers
        new_node_layers = {}
        layer_offset = 0

        for layer in sorted(layer_info.keys()):
            inheritance_in_layer = layer_info[layer]['inheritance']
            other_in_layer = layer_info[layer]['other']

            # Calculate how many sublayers we need
            num_sublayers_inheritance = (len(inheritance_in_layer) + max_per_layer_inheritance - 1) // max_per_layer_inheritance if inheritance_in_layer else 0
            num_sublayers_other = (len(other_in_layer) + max_per_layer_other - 1) // max_per_layer_other if other_in_layer else 0
            num_sublayers = max(num_sublayers_inheritance, num_sublayers_other, 1)

            if num_sublayers == 1:
                # All nodes fit in one layer - keep them together
                for node in inheritance_in_layer + other_in_layer:
                    new_node_layers[node] = layer + layer_offset
            else:
                # CRITICAL: When splitting layers, we MUST keep all inheritance nodes
                # from the SAME original layer TOGETHER, because they are likely siblings.
                # DO NOT split inheritance nodes across sublayers within the same original layer.

                # Strategy: Place ALL inheritance nodes in the FIRST sublayer (sublayer 0)
                # This ensures siblings stay together
                for node in inheritance_in_layer:
                    new_node_layers[node] = layer + layer_offset

                # For other nodes, place them in subsequent sublayers to avoid interruption
                if inheritance_in_layer:
                    # Place other nodes in last sublayer to avoid interrupting
                    for node in other_in_layer:
                        new_node_layers[node] = layer + layer_offset + num_sublayers - 1
                else:
                    # No inheritance nodes, spread normally
                    for i, node in enumerate(other_in_layer):
                        sublayer = min(i // max_per_layer_other, num_sublayers - 1)
                        new_node_layers[node] = layer + layer_offset + sublayer

                # Add offset for next layers
                layer_offset += num_sublayers - 1

        return new_node_layers

    def _fix_hierarchy_interruptions(self, node_layers: Dict[str, int], graph: Dict) -> Dict[str, int]:
        """
        Fix hierarchy interruptions by moving non-inheritance nodes that fall between
        parent and child nodes in inheritance hierarchies.

        Strategy: Move interrupting nodes to a layer that doesn't interrupt any hierarchy.
        Preference is to move them to layer 0 (top) if possible, otherwise to the bottom.
        """
        # Build parent-child map from inheritance edges
        parent_child_map = defaultdict(list)
        for parent, child in graph['inheritance_edges']:
            parent_child_map[parent].append(child)

        # Identify inheritance nodes
        inheritance_nodes = set()
        for parent, child in graph['inheritance_edges']:
            inheritance_nodes.add(parent)
            inheritance_nodes.add(child)

        # Find interrupting nodes
        interruptions_found = True
        max_iterations = 5  # Prevent infinite loops
        iteration = 0

        while interruptions_found and iteration < max_iterations:
            interruptions_found = False
            iteration += 1

            for parent_id, children_ids in parent_child_map.items():
                if parent_id not in node_layers:
                    continue

                parent_layer = node_layers[parent_id]

                # Find the range of layers occupied by children
                children_layers = [node_layers[child_id] for child_id in children_ids if child_id in node_layers]
                if not children_layers:
                    continue

                min_child_layer = min(children_layers)
                max_child_layer = max(children_layers)

                # Find nodes that are between parent and children
                for node_id, layer in list(node_layers.items()):
                    # Skip if this is the parent or one of the children
                    if node_id == parent_id or node_id in children_ids:
                        continue

                    # Skip if this is an inheritance node (shouldn't move it)
                    if node_id in inheritance_nodes:
                        continue

                    # Check if this node is interrupting (between parent and children)
                    is_interrupting = False
                    if parent_layer < min_child_layer:
                        # Parent above children
                        if parent_layer < layer < min_child_layer:
                            is_interrupting = True
                    elif parent_layer > max_child_layer:
                        # Parent below children
                        if max_child_layer < layer < parent_layer:
                            is_interrupting = True

                    if is_interrupting:
                        interruptions_found = True

                        # Move this node to a non-interrupting layer
                        # Try to place it at the top (layer 0) or bottom (max layer + 1)
                        max_layer = max(node_layers.values())

                        # Check if layer 0 would work (doesn't interrupt any hierarchy)
                        can_use_layer_0 = True
                        for other_parent, other_children in parent_child_map.items():
                            if other_parent in node_layers:
                                other_parent_layer = node_layers[other_parent]
                                other_children_layers = [node_layers[c] for c in other_children if c in node_layers]
                                if other_children_layers:
                                    min_other_child = min(other_children_layers)
                                    max_other_child = max(other_children_layers)

                                    if other_parent_layer < min_other_child and 0 < min_other_child:
                                        can_use_layer_0 = False
                                        break
                                    elif other_parent_layer > max_other_child and 0 > max_other_child:
                                        can_use_layer_0 = False
                                        break

                        if can_use_layer_0:
                            node_layers[node_id] = 0
                        else:
                            # Place at bottom
                            node_layers[node_id] = max_layer + 1

        return node_layers

    def _layer_by_inheritance(self, graph: Dict) -> Dict[str, int]:
        """
        Assign layers based on inheritance hierarchy using longest path.
        IMPORTANT: Only assigns layers to nodes that are part of the inheritance hierarchy.
        Other nodes (connected only by associations) should remain unassigned.
        """
        node_layers = {}

        # Find all nodes that are part of the inheritance hierarchy
        inheritance_nodes = set()
        for parent, child in graph['inheritance_edges']:
            inheritance_nodes.add(parent)
            inheritance_nodes.add(child)

        # Find root nodes (no incoming inheritance edges, but ARE part of inheritance hierarchy)
        roots = []
        inheritance_in = defaultdict(list)

        for parent, child in graph['inheritance_edges']:
            inheritance_in[child].append(parent)

        # CRITICAL: Only add nodes that are part of inheritance hierarchy as roots
        for node in inheritance_nodes:
            if node not in inheritance_in:
                roots.append(node)

        if not roots:
            # Handle cycles by picking nodes with minimal incoming edges
            for node in graph['nodes']:
                if node not in node_layers:
                    roots.append(node)
                    break

        # BFS to assign layers
        queue = deque([(root, 0) for root in roots])
        visited = set()

        while queue:
            node, layer = queue.popleft()

            if node in visited:
                continue

            visited.add(node)

            # Assign layer (use maximum if already assigned)
            if node in node_layers:
                node_layers[node] = max(node_layers[node], layer)
            else:
                node_layers[node] = layer

            # Process children (increase layer)
            for parent, child in graph['inheritance_edges']:
                if parent == node and child not in visited:
                    queue.append((child, layer + 1))

        return node_layers

    def _reduce_crossings(self, layers: List[List[str]], graph: Dict, elements: Dict) -> List[List[str]]:
        """
        Phase 2: Reduce edge crossings by reordering nodes within layers.
        Uses barycenter heuristic with special handling for inheritance siblings and enumerations.
        """
        if len(layers) <= 1:
            return layers

        # Perform multiple passes (sweep up and down)
        for iteration in range(10):
            # Downward pass
            for i in range(1, len(layers)):
                layers[i] = self._order_by_barycenter(layers[i], layers[i-1], graph, elements, direction='down')

            # Upward pass
            for i in range(len(layers) - 2, -1, -1):
                layers[i] = self._order_by_barycenter(layers[i], layers[i+1], graph, elements, direction='up')

        return layers

    def _order_by_barycenter(self, layer: List[str], reference_layer: List[str],
                             graph: Dict, elements: Dict, direction: str) -> List[str]:
        """
        Order nodes in a layer by their barycenter relative to ALL connected nodes.
        Special handling:
        - Sibling children (sharing same parent) are grouped together
        - Enumerations are pushed to the edges
        - Uses connections to ALL layers, weighted by proximity
        """
        if not layer:
            return layer

        # Create position map for reference layer (if provided)
        ref_positions = {node: idx for idx, node in enumerate(reference_layer)} if reference_layer else {}

        # Identify sibling groups (children with same parent)
        sibling_groups = defaultdict(list)
        standalone_nodes = []
        enumerations = []

        for node in layer:
            # Check if it's an enumeration
            if elements[node].get('type') == 'Enumeration':
                enumerations.append(node)
                continue

            # Check if this node has inheritance parents
            parents = [parent for parent, child in graph['inheritance_edges'] if child == node]

            if parents:
                # Group by parent (use first parent for simplicity)
                parent_key = parents[0]
                sibling_groups[parent_key].append(node)
            else:
                standalone_nodes.append(node)

        # Calculate barycenter for each group/node
        group_barycenters = []

        # Process sibling groups (keep them together and center them below parent)
        for parent, siblings in sibling_groups.items():
            # Calculate group barycenter based on parent position
            # Siblings should be centered around their parent
            if parent in ref_positions:
                group_barycenter = ref_positions[parent]
            else:
                # Parent not in reference layer, calculate from children's connections
                all_positions = []
                for sibling in siblings:
                    neighbors = graph['edges_in'][sibling] if direction == 'down' else graph['edges_out'][sibling]
                    for neighbor in neighbors:
                        if neighbor in ref_positions:
                            all_positions.append(ref_positions[neighbor])
                group_barycenter = sum(all_positions) / len(all_positions) if all_positions else len(reference_layer) / 2

            # Store siblings with their group barycenter
            # The barycenter represents where the GROUP should be centered, not where it starts
            group_barycenters.append((siblings, group_barycenter, 'siblings'))

        # Process standalone nodes
        # IMPROVED: Consider connections to nodes in the SAME layer to group related elements
        for node in standalone_nodes:
            connected_positions = []

            # Get all neighbors (bidirectional - both incoming and outgoing)
            all_neighbors = set(graph['edges_in'][node]) | set(graph['edges_out'][node])

            # First, try to use reference layer positions
            for neighbor in all_neighbors:
                if neighbor in ref_positions:
                    connected_positions.append(ref_positions[neighbor])

            # If no connections to reference layer, check connections within the SAME layer
            # This helps group elements that are related to each other
            if not connected_positions:
                for i, other_node in enumerate(layer):
                    if other_node != node and other_node in all_neighbors:
                        # Use a pseudo-position based on current order
                        # This creates clustering of connected elements
                        connected_positions.append(i)

            # Calculate barycenter
            if connected_positions:
                barycenter = sum(connected_positions) / len(connected_positions)
            else:
                # No connections at all - use middle position
                barycenter = len(layer) / 2 if layer else 0

            group_barycenters.append(([node], barycenter, 'standalone'))

        # Sort groups by barycenter
        group_barycenters.sort(key=lambda x: x[1])

        # Build final ordered layer: enumerations at edges, regular nodes in middle
        ordered_layer = []

        # Add enumerations to the start (left side)
        ordered_layer.extend(enumerations[:len(enumerations)//2] if len(enumerations) > 1 else enumerations)

        # Add ordered groups (siblings stay together)
        for nodes, _, _ in group_barycenters:
            ordered_layer.extend(nodes)

        # Add remaining enumerations to the end (right side)
        if len(enumerations) > 1:
            ordered_layer.extend(enumerations[len(enumerations)//2:])

        return ordered_layer

    def _assign_coordinates(self, elements: Dict, layers: List[List[str]], graph: Dict) -> Dict[str, Tuple[float, float]]:
        """
        Phase 3: Assign final (x, y) coordinates to nodes.
        Uses dynamic layer spacing based on element heights to prevent collisions.
        Sibling children (sharing same parent) are positioned closer together.
        PlantUML-style: Enumerations are placed at far left/right edges outside main hierarchy.
        """
        positioned_elements = {}

        # Build sibling map for identifying consecutive siblings
        parent_children_map = defaultdict(set)
        for parent, child in graph['inheritance_edges']:
            parent_children_map[parent].add(child)

        start_y = -300  # Starting Y position
        current_y = start_y

        for layer_idx, layer in enumerate(layers):
            y = current_y

            # Separate enumerations from regular nodes (PlantUML style)
            enumerations = [nid for nid in layer if elements[nid].get('type') == 'Enumeration']
            regular_nodes = [nid for nid in layer if elements[nid].get('type') != 'Enumeration']

            # Calculate layer width for REGULAR nodes only (enumerations placed at edges)
            # Sibling spacing is 50% of normal spacing
            sibling_spacing = self.node_spacing * 0.5
            layer_width = 0
            prev_node = None

            for i, node_id in enumerate(regular_nodes):
                elem = elements[node_id]
                width = elem['bounds']['width']

                # Determine spacing before this node
                if i > 0:
                    # Check if current and previous nodes are siblings
                    are_siblings = self._are_siblings(prev_node, node_id, parent_children_map)
                    spacing = sibling_spacing if are_siblings else self.node_spacing
                    layer_width += spacing

                layer_width += width
                prev_node = node_id

            # Center the regular nodes layer
            start_x = -layer_width / 2
            current_x = start_x

            # Find the maximum height in this layer
            max_height_in_layer = 0
            for node_id in layer:
                elem = elements[node_id]
                height = elem['bounds']['height']
                max_height_in_layer = max(max_height_in_layer, height)

            # Position REGULAR nodes in the center
            prev_node = None
            for i, node_id in enumerate(regular_nodes):
                elem = elements[node_id]
                width = elem['bounds']['width']

                # Add spacing before this node (except for first node)
                if i > 0:
                    are_siblings = self._are_siblings(prev_node, node_id, parent_children_map)
                    spacing = sibling_spacing if are_siblings else self.node_spacing
                    current_x += spacing

                # Position at current x
                x = current_x

                positioned_elements[node_id] = (x, y)

                # Move past this node's width
                current_x += width
                prev_node = node_id

            # Position ENUMERATIONS at far edges (PlantUML style)
            # This prevents them from interfering with the main inheritance hierarchy layout
            # PlantUML convention: All enumerations on the SAME SIDE (left edge)
            if enumerations:
                # Calculate how far out to place enumerations
                # ADAPTIVE SPACING: Use node_spacing instead of fixed 400px to avoid excessive horizontal space
                # This allows better horizontal/vertical balance when there are enumerations in the same layer
                edge_spacing = self.node_spacing  # Use adaptive node_spacing (245px by default)

                # Calculate the leftmost position of regular nodes in this layer
                if regular_nodes:
                    leftmost_x = start_x
                else:
                    leftmost_x = 0

                # IMPROVED: Place enumerations with COLLISION AVOIDANCE
                # Instead of stacking vertically with fixed spacing, spread horizontally when needed
                # This prevents collisions when multiple enumerations are in the same or nearby layers

                # Check how many enumerations we have already positioned (from previous layers)
                enum_x_positions = []  # Track horizontal positions used

                for enum_idx, enum_id in enumerate(enumerations):
                    elem = elements[enum_id]
                    width = elem['bounds']['width']
                    height = elem['bounds']['height']

                    # Start with the default left edge position
                    x = leftmost_x - edge_spacing - width

                    # Check if this position would collide with previously positioned enumerations
                    # We need to check ALL previously positioned enumerations, not just in this layer
                    collision_detected = True
                    horizontal_offset = 0
                    max_attempts = 10  # Prevent infinite loops

                    for attempt in range(max_attempts):
                        # Calculate test position
                        test_x = x - (horizontal_offset * (width + edge_spacing))

                        # Check for collisions with all previously positioned enumerations
                        collision_detected = False
                        for other_id, (other_x, other_y) in positioned_elements.items():
                            if other_id in elements and elements[other_id].get('type') == 'Enumeration':
                                other_width = elements[other_id]['bounds']['width']
                                other_height = elements[other_id]['bounds']['height']

                                # Check overlap with padding
                                padding = 30.0
                                if not (test_x + width + padding < other_x or
                                       test_x > other_x + other_width + padding or
                                       y + height + padding < other_y or
                                       y > other_y + other_height + padding):
                                    # Collision detected - try next horizontal position
                                    collision_detected = True
                                    break

                        if not collision_detected:
                            # Found a collision-free position
                            x = test_x
                            break

                        # Try next horizontal offset
                        horizontal_offset += 1

                    positioned_elements[enum_id] = (x, y)

            # Calculate spacing to next layer based on the tallest element in current layer
            # Add minimum padding (60px = 30px on each side) plus base layer spacing
            if layer_idx < len(layers) - 1:
                required_spacing = max_height_in_layer + (2 * 30)  # height + padding
                actual_spacing = max(self.layer_spacing, required_spacing)
                current_y += actual_spacing

        return positioned_elements

    def _are_siblings(self, node1: str, node2: str, parent_children_map: Dict) -> bool:
        """Check if two nodes are siblings (share the same parent)."""
        for parent, children in parent_children_map.items():
            if node1 in children and node2 in children:
                return True
        return False

    def _center_siblings_under_parents(self, positioned_elements: Dict[str, Tuple[float, float]],
                                       elements: Dict, graph: Dict) -> Dict[str, Tuple[float, float]]:
        """
        Adjust sibling positions to center them under their parent's X position.
        This creates the PlantUML-style layout where children are centered below the parent.
        """
        # Build parent-children map
        parent_children_map = defaultdict(list)
        for parent, child in graph['inheritance_edges']:
            parent_children_map[parent].append(child)

        new_positions = positioned_elements.copy()

        # Process each parent-children group
        for parent, children in parent_children_map.items():
            if parent not in positioned_elements or not children:
                continue

            # Get parent position
            parent_x, parent_y = positioned_elements[parent]
            parent_center_x = parent_x + elements[parent]['bounds']['width'] / 2

            # Get children that are positioned
            positioned_children = [child for child in children if child in positioned_elements]
            if not positioned_children:
                continue

            # Calculate total width of sibling group
            sibling_spacing = self.node_spacing * 0.5
            total_width = 0
            for i, child in enumerate(positioned_children):
                if i > 0:
                    total_width += sibling_spacing
                total_width += elements[child]['bounds']['width']

            # Calculate offset to center the group under parent
            group_center_x = total_width / 2
            parent_to_group_offset = parent_center_x - group_center_x

            # Reposition siblings to be centered under parent
            current_x = parent_to_group_offset
            for i, child in enumerate(positioned_children):
                if i > 0:
                    current_x += sibling_spacing

                # Update position
                child_y = positioned_elements[child][1]
                new_positions[child] = (current_x, child_y)

                current_x += elements[child]['bounds']['width']

        return new_positions

    def _update_elements(self, all_elements: Dict, main_elements: Dict,
                        positioned_elements: Dict[str, Tuple[float, float]]) -> Dict:
        """
        Update element bounds with new positions and move child elements.
        """
        updated_elements = all_elements.copy()

        for eid, (new_x, new_y) in positioned_elements.items():
            if eid in main_elements:
                elem = updated_elements[eid]
                old_bounds = elem['bounds']

                # Calculate offset
                offset_x = new_x - old_bounds['x']
                offset_y = new_y - old_bounds['y']

                # Update main element
                updated_elements[eid]['bounds']['x'] = new_x
                updated_elements[eid]['bounds']['y'] = new_y

                # Update child elements (attributes, methods)
                for child_id in all_elements.keys():
                    child = all_elements[child_id]
                    if child.get('owner') == eid:
                        updated_elements[child_id]['bounds']['x'] += offset_x
                        updated_elements[child_id]['bounds']['y'] += offset_y

        return updated_elements

    def _update_relationship_directions(self, elements: Dict, relationships: Dict) -> Dict:
        """
        Update relationship connection directions based on element positions.
        This ensures that relationships connect from the appropriate sides of elements.
        IMPROVED: Distributes multiple relationships from the same element to different sides
        to avoid path convergence and reduce crossings.
        """
        updated_relationships = {}

        # Build a map of which elements have inheritance children
        # This is needed to avoid associations using the same connection point (Down) as inheritance
        elements_with_inheritance_children = set()
        for rel_id, rel in relationships.items():
            if rel.get('type') == 'ClassInheritance':
                parent_id = rel.get('target', {}).get('element')  # target is parent in inheritance
                if parent_id:
                    elements_with_inheritance_children.add(parent_id)

        # Track how many relationships use each direction from each element
        # Format: {element_id: {direction: count}}
        element_direction_usage = defaultdict(lambda: defaultdict(int))

        # First pass: determine preferred directions for each relationship
        rel_preferred_dirs = {}
        for rel_id, rel in relationships.items():
            source_elem_id = rel.get('source', {}).get('element')
            target_elem_id = rel.get('target', {}).get('element')
            rel_type = rel.get('type')

            if not source_elem_id or not target_elem_id:
                continue

            if source_elem_id not in elements or target_elem_id not in elements:
                continue

            source_bounds = elements[source_elem_id]['bounds']
            target_bounds = elements[target_elem_id]['bounds']

            # Check if source or target has inheritance children
            source_has_children = source_elem_id in elements_with_inheritance_children
            target_has_children = target_elem_id in elements_with_inheritance_children

            # Calculate preferred connection directions
            source_dir, target_dir = self._determine_connection_direction(
                source_bounds, target_bounds, rel_type,
                source_has_inheritance_children=source_has_children,
                target_has_inheritance_children=target_has_children
            )

            rel_preferred_dirs[rel_id] = (source_elem_id, target_elem_id, source_dir, target_dir, rel_type)

        # Second pass: distribute relationships with same preferred direction to alternative sides
        for rel_id, rel in relationships.items():
            updated_rel = rel.copy()

            if rel_id not in rel_preferred_dirs:
                updated_relationships[rel_id] = updated_rel
                continue

            source_elem_id, target_elem_id, source_dir, target_dir, rel_type = rel_preferred_dirs[rel_id]

            # Check if this direction is already heavily used
            # If so, try to use an alternative direction to distribute the load
            source_bounds = elements[source_elem_id]['bounds']
            target_bounds = elements[target_elem_id]['bounds']

            # For non-inheritance relationships, try to distribute across sides
            if rel_type != 'ClassInheritance':
                source_dir = self._distribute_direction(
                    source_elem_id, source_dir, source_bounds, target_bounds,
                    element_direction_usage, source_has_inheritance_children=
                    source_elem_id in elements_with_inheritance_children
                )
                target_dir = self._distribute_direction(
                    target_elem_id, target_dir, target_bounds, source_bounds,
                    element_direction_usage, source_has_inheritance_children=
                    target_elem_id in elements_with_inheritance_children
                )

            # Record usage
            element_direction_usage[source_elem_id][source_dir] += 1
            element_direction_usage[target_elem_id][target_dir] += 1

            # Update source direction
            if 'source' not in updated_rel:
                updated_rel['source'] = {}
            updated_rel['source'] = rel['source'].copy()
            updated_rel['source']['direction'] = source_dir

            # Update target direction
            if 'target' not in updated_rel:
                updated_rel['target'] = {}
            updated_rel['target'] = rel['target'].copy()
            updated_rel['target']['direction'] = target_dir

            updated_relationships[rel_id] = updated_rel

        return updated_relationships

    def _distribute_direction(self, element_id: str, preferred_dir: str,
                             element_bounds: Dict, other_bounds: Dict,
                             direction_usage: Dict, source_has_inheritance_children: bool = False) -> str:
        """
        Distribute relationship to an alternative direction if the preferred direction
        is already heavily used. This reduces path convergence and crossings.

        Strategy: If preferred direction has 2+ relationships, try adjacent directions.
        IMPORTANT: Only distribute when geometry is ambiguous. Never override strong geometry.
        """
        current_usage = direction_usage[element_id][preferred_dir]

        # If this direction is not yet crowded (< 2 relationships), use it
        if current_usage < 2:
            return preferred_dir

        # Calculate relative position to determine geometry strength
        dx = other_bounds['x'] - element_bounds['x']
        dy = other_bounds['y'] - element_bounds['y']
        abs_dx = abs(dx)
        abs_dy = abs(dy)

        # CRITICAL: Do NOT distribute if geometry is clearly defined
        # If one axis is dominant (>1.2x the other), ALWAYS use that direction
        # This prevents geometry violations where we connect the wrong way
        # Threshold of 1.2 means: if |dy| > |dx| OR |dx| > |dy|, follow the primary axis
        geometry_ratio_threshold = 1.2  # If one axis is 1.2x stronger, it's dominant

        if preferred_dir in ['Up', 'Down']:
            # Vertical preferred - check if vertical is strongly dominant
            if abs_dy > abs_dx * geometry_ratio_threshold:
                # Strongly vertical geometry - NEVER use horizontal alternatives
                return preferred_dir
        elif preferred_dir in ['Left', 'Right']:
            # Horizontal preferred - check if horizontal is strongly dominant
            if abs_dx > abs_dy * geometry_ratio_threshold:
                # Strongly horizontal geometry - NEVER use vertical alternatives
                return preferred_dir

        # Geometry is ambiguous (similar dx and dy) - distribution is safe
        # Direction is crowded - try to find a less-used alternative
        # Priority order depends on preferred direction
        alternatives = {
            'Up': ['Left', 'Right', 'Down'],  # Try sides first, then opposite
            'Down': ['Left', 'Right', 'Up'] if not source_has_inheritance_children else ['Left', 'Right'],  # Avoid Up if has inheritance
            'Left': ['Up', 'Down', 'Right'],
            'Right': ['Up', 'Down', 'Left']
        }

        # Reorder alternatives based on geometry
        if preferred_dir in ['Up', 'Down']:
            # Vertical preferred - prioritize horizontal alternatives based on dx
            if dx > 0:
                alternatives[preferred_dir] = ['Right', 'Left'] + ([preferred_dir] if preferred_dir == 'Up' else [])
            else:
                alternatives[preferred_dir] = ['Left', 'Right'] + ([preferred_dir] if preferred_dir == 'Up' else [])
        elif preferred_dir in ['Left', 'Right']:
            # Horizontal preferred - prioritize vertical alternatives based on dy
            if dy > 0:
                alternatives[preferred_dir] = ['Down', 'Up', alternatives[preferred_dir][-1]]
            else:
                alternatives[preferred_dir] = ['Up', 'Down', alternatives[preferred_dir][-1]]

        # Find the least-used alternative
        for alt_dir in alternatives.get(preferred_dir, [preferred_dir]):
            if direction_usage[element_id][alt_dir] < current_usage:
                return alt_dir

        # All alternatives are equally or more crowded - stick with preferred
        return preferred_dir

    def _determine_connection_direction(self, source_bounds: Dict, target_bounds: Dict,
                                       rel_type: str = None,
                                       source_has_inheritance_children: bool = False,
                                       target_has_inheritance_children: bool = False) -> Tuple[str, str]:
        """
        Determine the best connection directions between two elements.
        Returns (source_direction, target_direction).

        IMPROVED: Uses strict geometry-based direction selection.
        If target is LEFT of source, source connects from LEFT (not right).
        If target is RIGHT of source, source connects from RIGHT (not left).
        If target is ABOVE source, source connects from UP (not down).
        If target is BELOW source, source connects from DOWN (not up).

        This ensures the shortest, most direct path and minimizes crossings.

        Args:
            source_bounds: Bounds of source element
            target_bounds: Bounds of target element
            rel_type: Type of relationship (e.g., 'ClassInheritance')
            source_has_inheritance_children: Whether source element has inheritance children
            target_has_inheritance_children: Whether target element has inheritance children
        """
        # Calculate center points
        source_center_x = source_bounds['x'] + source_bounds['width'] / 2
        source_center_y = source_bounds['y'] + source_bounds['height'] / 2
        target_center_x = target_bounds['x'] + target_bounds['width'] / 2
        target_center_y = target_bounds['y'] + target_bounds['height'] / 2

        dx = target_center_x - source_center_x
        dy = target_center_y - source_center_y

        # For inheritance relationships, ALWAYS use vertical alignment (Up/Down only)
        # In the graph, source is the CHILD and target is the PARENT
        # Parent should always be above child, so:
        # - Child connects upward (Up) to reach the parent
        # - Parent connects downward (Down) to reach the child
        # This is true regardless of current positions
        if rel_type == 'ClassInheritance':
            # Always use Up for child (source) and Down for parent (target)
            return "Up", "Down"

        # For ASSOCIATION relationships (not inheritance):
        # GEOMETRY-FIRST APPROACH: Choose direction based on actual relative positions
        # This ensures we always connect toward the target, not away from it

        # Determine primary axis (which is stronger: horizontal or vertical offset?)
        abs_dx = abs(dx)
        abs_dy = abs(dy)

        # CASE 1: Primarily horizontal relationship (target is to left or right)
        if abs_dx > abs_dy:
            # Target is primarily to the left or right of source

            # Source direction: Connect from the side TOWARD the target
            if dx > 0:
                # Target is to the RIGHT of source -> source connects from RIGHT
                source_dir = "Right"
            else:
                # Target is to the LEFT of source -> source connects from LEFT
                source_dir = "Left"

            # Target direction: Connect from the side TOWARD the source (opposite)
            if dx > 0:
                # Source is to the LEFT of target -> target connects from LEFT
                target_dir = "Left"
            else:
                # Source is to the RIGHT of target -> target connects from RIGHT
                target_dir = "Right"

            return source_dir, target_dir

        # CASE 2: Primarily vertical relationship (target is above or below)
        else:
            # Target is primarily above or below source

            # Check if we should avoid vertical connections due to inheritance conflicts
            # Only avoid if elements have inheritance children AND there's some horizontal offset
            horizontal_offset_exists = abs_dx > 20  # At least 20px horizontal offset

            # If source has children below and target is below, avoid using Down
            if source_has_inheritance_children and dy > 0 and horizontal_offset_exists:
                # Source has children below, but target is also below
                # Use horizontal connection instead to avoid interference
                if dx > 0:
                    return "Right", "Left"
                else:
                    return "Left", "Right"

            # If target has children below and source is below target, avoid using Down on target
            if target_has_inheritance_children and dy < 0 and horizontal_offset_exists:
                # Target has children below, but source is also below target
                # Use horizontal connection instead
                if dx > 0:
                    return "Right", "Left"
                else:
                    return "Left", "Right"

            # No inheritance conflict - use vertical connections based on geometry
            # Source direction: Connect from the side TOWARD the target
            if dy > 0:
                # Target is BELOW source -> source connects from DOWN
                source_dir = "Down"
            else:
                # Target is ABOVE source -> source connects from UP
                source_dir = "Up"

            # Target direction: Connect from the side TOWARD the source (opposite)
            if dy > 0:
                # Source is ABOVE target -> target connects from UP
                target_dir = "Up"
            else:
                # Source is BELOW target -> target connects from DOWN
                target_dir = "Down"

            return source_dir, target_dir


def detect_collisions(elements: Dict) -> List[Tuple[str, str]]:
    """
    Detect collisions between elements.

    Args:
        elements: Dictionary of elements with bounds

    Returns:
        List of tuples containing IDs of colliding elements
    """
    collisions = []
    main_elements = {
        eid: elem for eid, elem in elements.items()
        if elem.get('type') in ['Class', 'AbstractClass', 'Enumeration', 'ClassOCLConstraint']
        and elem.get('owner') is None
    }

    element_ids = list(main_elements.keys())
    for i, eid1 in enumerate(element_ids):
        for eid2 in element_ids[i+1:]:
            if _check_collision(main_elements[eid1], main_elements[eid2]):
                collisions.append((eid1, eid2))

    return collisions


def _check_collision(elem1: Dict, elem2: Dict, padding: float = 30.0) -> bool:
    """Check if two elements overlap with padding."""
    b1 = elem1['bounds']
    b2 = elem2['bounds']

    # Add padding to bounds
    left1 = b1['x'] - padding
    right1 = b1['x'] + b1['width'] + padding
    top1 = b1['y'] - padding
    bottom1 = b1['y'] + b1['height'] + padding

    left2 = b2['x'] - padding
    right2 = b2['x'] + b2['width'] + padding
    top2 = b2['y'] - padding
    bottom2 = b2['y'] + b2['height'] + padding

    # Check for overlap
    return not (right1 <= left2 or right2 <= left1 or bottom1 <= top2 or bottom2 <= top1)


def optimize_path_routing(elements: Dict, relationships: Dict) -> Dict:
    """
    Optimize relationship paths to avoid crossing through elements.
    Uses orthogonal routing similar to PlantUML.

    Args:
        elements: Dictionary of elements with final positions
        relationships: Dictionary of relationships with paths

    Returns:
        Updated relationships with optimized paths
    """
    updated_relationships = relationships.copy()

    main_elements = {
        eid: elem for eid, elem in elements.items()
        if elem.get('type') in ['Class', 'AbstractClass', 'Enumeration', 'ClassOCLConstraint']
        and elem.get('owner') is None
    }

    for rel_id, rel in relationships.items():
        if 'path' not in rel:
            continue

        path = rel['path']
        source_elem_id = rel.get('source', {}).get('element')
        target_elem_id = rel.get('target', {}).get('element')

        # Iteratively fix crossings
        # Strategy: Make multiple passes, and in each pass fix ONE crossing per element
        # This prevents oscillations where fixing crossing A creates crossing B, then fixing B recreates A
        max_passes = 3

        for _ in range(max_passes):
            # Track which obstacles we've already added detours for in this pass
            obstacles_detourred = set()
            crossing_found_this_pass = False

            # Check each segment for crossings
            i = 0
            while i < len(path) - 1:
                # Skip zero-length segments (duplicate points)
                if path[i]['x'] == path[i+1]['x'] and path[i]['y'] == path[i+1]['y']:
                    i += 1
                    continue

                segment_crosses = False
                crossing_elem_id = None
                crossing_elem = None

                # Check if this segment crosses any element
                for eid, elem in main_elements.items():
                    if eid == source_elem_id or eid == target_elem_id:
                        continue

                    # Skip if we already added a detour for this element in this pass
                    if eid in obstacles_detourred:
                        continue

                    if _segment_crosses_element(path[i], path[i+1], elem):
                        segment_crosses = True
                        crossing_elem_id = eid
                        crossing_elem = elem
                        break

                if segment_crosses:
                    crossing_found_this_pass = True
                    # Add detour point to avoid this element
                    path = _add_detour_point(path, i, crossing_elem)
                    obstacles_detourred.add(crossing_elem_id)

                    # After adding detour, check THE SAME segment index again
                    # (because we inserted points, the next segment to check is still at index i)
                    # But limit how many times we retry the same segment to prevent infinite loops
                    continue

                # Move to next segment
                i += 1

            # If no crossings found in this pass, we're done
            if not crossing_found_this_pass:
                break

        # Clean up duplicate consecutive points from the path
        path = _remove_duplicate_points(path)

        # Update the path
        updated_relationships[rel_id]['path'] = path

        # Update bounds based on new path
        if path:
            updated_relationships[rel_id]['bounds'] = _calculate_path_bounds(path)

    return updated_relationships


def _calculate_path_bounds(path: List[Dict]) -> Dict:
    """Calculate bounding box for a path."""
    if not path:
        return {"x": 0, "y": 0, "width": 0, "height": 0}

    min_x = min(p['x'] for p in path)
    max_x = max(p['x'] for p in path)
    min_y = min(p['y'] for p in path)
    max_y = max(p['y'] for p in path)

    return {
        "x": min_x - 10,
        "y": min_y - 10,
        "width": max_x - min_x + 20,
        "height": max_y - min_y + 20
    }


def _segment_crosses_element(point1: Dict, point2: Dict, element: Dict) -> bool:
    """Check if a line segment crosses through an element."""
    bounds = element['bounds']

    min_x = min(point1['x'], point2['x'])
    max_x = max(point1['x'], point2['x'])
    min_y = min(point1['y'], point2['y'])
    max_y = max(point1['y'], point2['y'])

    elem_left = bounds['x']
    elem_right = bounds['x'] + bounds['width']
    elem_top = bounds['y']
    elem_bottom = bounds['y'] + bounds['height']

    return not (max_x < elem_left or min_x > elem_right or
                max_y < elem_top or min_y > elem_bottom)


def _remove_duplicate_points(path: List[Dict]) -> List[Dict]:
    """Remove consecutive duplicate points from a path."""
    if not path:
        return path

    cleaned_path = [path[0]]
    for point in path[1:]:
        # Only add if different from last point
        if point['x'] != cleaned_path[-1]['x'] or point['y'] != cleaned_path[-1]['y']:
            cleaned_path.append(point)

    return cleaned_path


def _add_detour_point(path: List[Dict], segment_index: int, obstacle: Dict) -> List[Dict]:
    """
    Add detour points to route around an obstacle.
    Uses orthogonal routing with TWO points to properly go around the obstacle.
    """
    bounds = obstacle['bounds']
    point1 = path[segment_index]
    point2 = path[segment_index + 1]

    margin = 40  # Safety margin around obstacles

    # Calculate obstacle edges with margin
    left_edge = bounds['x'] - margin
    right_edge = bounds['x'] + bounds['width'] + margin
    top_edge = bounds['y'] - margin
    bottom_edge = bounds['y'] + bounds['height'] + margin

    # Determine primary direction of the segment
    dx = point2['x'] - point1['x']
    dy = point2['y'] - point1['y']

    detour_points = []

    if abs(dx) > abs(dy):
        # Primarily horizontal segment - route above or below
        # Choose side based on which is closer to point1
        if point1['y'] < bounds['y'] + bounds['height'] / 2:
            # Route above the obstacle
            detour_y = top_edge
        else:
            # Route below the obstacle
            detour_y = bottom_edge

        # Add two points for orthogonal routing:
        # 1. Move vertically to detour level
        # 2. Move horizontally past the obstacle
        # 3. Return to target level (point2 handles this)
        detour_points.append({'x': point1['x'], 'y': detour_y})
        detour_points.append({'x': point2['x'], 'y': detour_y})
    else:
        # Primarily vertical segment - route left or right
        # Choose side based on which is closer to point1
        if point1['x'] < bounds['x'] + bounds['width'] / 2:
            # Route to the left of the obstacle
            detour_x = left_edge
        else:
            # Route to the right of the obstacle
            detour_x = right_edge

        # Add two points for orthogonal routing:
        # 1. Move horizontally to detour level
        # 2. Move vertically past the obstacle
        detour_points.append({'x': detour_x, 'y': point1['y']})
        detour_points.append({'x': detour_x, 'y': point2['y']})

    # Insert detour points into path
    new_path = path[:segment_index + 1] + detour_points + path[segment_index + 1:]
    return new_path