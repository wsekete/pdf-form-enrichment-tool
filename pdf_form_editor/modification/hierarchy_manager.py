#!/usr/bin/env python3
"""
Hierarchy Manager for PDF Field Relationships

Manages field hierarchies during name modifications to preserve parent-child
relationships, radio group structures, and inheritance patterns.
"""

from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field as dataclass_field
from collections import defaultdict

from ..core.field_extractor import FormField
from ..utils.logging import get_logger
from .pdf_modifier import FieldModification

logger = get_logger(__name__)


@dataclass
class HierarchyNode:
    """Node in the field hierarchy tree."""
    field: FormField
    parent: Optional['HierarchyNode'] = None
    children: List['HierarchyNode'] = dataclass_field(default_factory=list)
    qualified_name: str = ""
    depth: int = 0
    inherited_properties: Dict[str, Any] = dataclass_field(default_factory=dict)
    
    def add_child(self, child: 'HierarchyNode') -> None:
        """Add a child node."""
        child.parent = self
        child.depth = self.depth + 1
        self.children.append(child)
    
    def get_siblings(self) -> List['HierarchyNode']:
        """Get sibling nodes."""
        if self.parent:
            return [child for child in self.parent.children if child != self]
        return []
    
    def get_descendants(self) -> List['HierarchyNode']:
        """Get all descendant nodes."""
        descendants = []
        for child in self.children:
            descendants.append(child)
            descendants.extend(child.get_descendants())
        return descendants
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "field_id": self.field.id,
            "field_name": self.field.name,
            "field_type": self.field.field_type,
            "qualified_name": self.qualified_name,
            "depth": self.depth,
            "parent_id": self.parent.field.id if self.parent else None,
            "children_ids": [child.field.id for child in self.children],
            "inherited_properties": self.inherited_properties
        }


@dataclass
class HierarchyTree:
    """Complete hierarchy tree for form fields."""
    root_nodes: List[HierarchyNode]
    node_map: Dict[str, HierarchyNode]  # field_id -> node
    max_depth: int
    total_nodes: int
    
    def get_node(self, field_id: str) -> Optional[HierarchyNode]:
        """Get node by field ID."""
        return self.node_map.get(field_id)
    
    def get_nodes_by_type(self, field_type: str) -> List[HierarchyNode]:
        """Get all nodes of a specific field type."""
        return [node for node in self.node_map.values() 
                if node.field.field_type == field_type]
    
    def get_radio_groups(self) -> List[HierarchyNode]:
        """Get all radio group root nodes."""
        return [node for node in self.node_map.values()
                if node.field.field_type == 'radio' and not node.parent]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "max_depth": self.max_depth,
            "total_nodes": self.total_nodes,
            "root_nodes": [node.field.id for node in self.root_nodes],
            "nodes": {node_id: node.to_dict() for node_id, node in self.node_map.items()},
            "radio_groups": [node.field.id for node in self.get_radio_groups()]
        }


@dataclass
class ConflictReport:
    """Report of naming conflicts in hierarchy."""
    conflict_type: str
    affected_fields: List[str]
    description: str
    suggested_resolution: str
    severity: str = "warning"  # warning, error, critical


@dataclass
class HierarchyValidation:
    """Result of hierarchy validation."""
    is_valid: bool
    orphaned_fields: List[str]
    circular_references: List[str]
    naming_conflicts: List[ConflictReport]
    broken_relationships: List[str]
    warnings: List[str]


@dataclass
class UpdatedHierarchy:
    """Result of hierarchy updates."""
    updated_nodes: List[str]
    preserved_relationships: int
    new_qualified_names: Dict[str, str]
    hierarchy_changes: List[str]


class HierarchyManager:
    """Manage field hierarchies during name modifications."""
    
    def __init__(self):
        """Initialize hierarchy manager."""
        self.tree: Optional[HierarchyTree] = None
        logger.info("HierarchyManager initialized")
    
    def build_hierarchy_map(self, fields: List[FormField]) -> HierarchyTree:
        """
        Build complete hierarchy tree from field relationships.
        
        Args:
            fields: List of form fields
            
        Returns:
            HierarchyTree with complete hierarchy mapping
        """
        logger.info(f"Building hierarchy map for {len(fields)} fields")
        
        # Create nodes for all fields
        nodes = {}
        for field in fields:
            node = HierarchyNode(field=field)
            nodes[field.id] = node
        
        # Build parent-child relationships
        root_nodes = []
        max_depth = 0
        
        for field in fields:
            node = nodes[field.id]
            
            # Set up parent relationship
            if field.parent and field.parent in nodes:
                parent_node = nodes[field.parent]
                parent_node.add_child(node)
            else:
                # This is a root node
                root_nodes.append(node)
            
            # Set up children relationships  
            for child_id in field.children:
                if child_id in nodes:
                    child_node = nodes[child_id]
                    node.add_child(child_node)
            
            # Update max depth
            max_depth = max(max_depth, node.depth)
        
        # Generate qualified names
        self._generate_qualified_names(root_nodes)
        
        # Create tree object
        tree = HierarchyTree(
            root_nodes=root_nodes,
            node_map=nodes,
            max_depth=max_depth,
            total_nodes=len(nodes)
        )
        
        self.tree = tree
        
        logger.info(f"Hierarchy tree built: {len(root_nodes)} root nodes, "
                   f"max depth: {max_depth}, total nodes: {len(nodes)}")
        
        return tree
    
    def _generate_qualified_names(self, root_nodes: List[HierarchyNode]) -> None:
        """
        Generate qualified names for all nodes in the hierarchy.
        
        Args:
            root_nodes: List of root nodes to process
        """
        def process_node(node: HierarchyNode, prefix: str = "") -> None:
            """Recursively process nodes to generate qualified names."""
            if prefix:
                node.qualified_name = f"{prefix}.{node.field.name}"
            else:
                node.qualified_name = node.field.name
            
            # Process children
            for child in node.children:
                process_node(child, node.qualified_name)
        
        # Process all root nodes
        for root_node in root_nodes:
            process_node(root_node)
    
    def update_hierarchy_references(self, tree: HierarchyTree, 
                                  field_updates: Dict[str, str]) -> UpdatedHierarchy:
        """
        Update all hierarchy references when field names change.
        
        Args:
            tree: Current hierarchy tree
            field_updates: Dictionary of field_id -> new_name mappings
            
        Returns:
            UpdatedHierarchy with update results
        """
        logger.info(f"Updating hierarchy references for {len(field_updates)} field changes")
        
        updated_nodes = []
        hierarchy_changes = []
        new_qualified_names = {}
        preserved_relationships = 0
        
        # Update field names in nodes
        for field_id, new_name in field_updates.items():
            node = tree.get_node(field_id)
            if node:
                old_name = node.field.name
                node.field.name = new_name
                updated_nodes.append(field_id)
                hierarchy_changes.append(f"Updated field {field_id}: {old_name} -> {new_name}")
        
        # Regenerate qualified names
        self._generate_qualified_names(tree.root_nodes)
        
        # Collect new qualified names
        for field_id in field_updates.keys():
            node = tree.get_node(field_id)
            if node:
                new_qualified_names[field_id] = node.qualified_name
        
        # Count preserved relationships
        for node in tree.node_map.values():
            if node.parent or node.children:
                preserved_relationships += 1
        
        result = UpdatedHierarchy(
            updated_nodes=updated_nodes,
            preserved_relationships=preserved_relationships,
            new_qualified_names=new_qualified_names,
            hierarchy_changes=hierarchy_changes
        )
        
        logger.info(f"Hierarchy update complete: {len(updated_nodes)} nodes updated, "
                   f"{preserved_relationships} relationships preserved")
        
        return result
    
    def validate_hierarchy_integrity(self, tree: HierarchyTree) -> HierarchyValidation:
        """
        Validate hierarchy remains intact after modifications.
        
        Args:
            tree: Hierarchy tree to validate
            
        Returns:
            HierarchyValidation with validation results
        """
        logger.info("Validating hierarchy integrity")
        
        orphaned_fields = []
        circular_references = []
        naming_conflicts = []
        broken_relationships = []
        warnings = []
        
        # Check for orphaned fields
        for node in tree.node_map.values():
            if node.field.parent and node.field.parent not in tree.node_map:
                orphaned_fields.append(node.field.id)
        
        # Check for circular references
        circular_references = self._detect_circular_references(tree)
        
        # Check for naming conflicts
        naming_conflicts = self._detect_hierarchy_naming_conflicts(tree)
        
        # Check for broken parent-child relationships
        for node in tree.node_map.values():
            # Verify parent relationship
            if node.parent:
                if node.field.id not in [child.field.id for child in node.parent.children]:
                    broken_relationships.append(
                        f"Parent {node.parent.field.id} missing child {node.field.id}"
                    )
            
            # Verify children relationships
            for child in node.children:
                if child.parent != node:
                    broken_relationships.append(
                        f"Child {child.field.id} has incorrect parent reference"
                    )
        
        # Check for inconsistent field types in radio groups
        for radio_group in tree.get_radio_groups():
            children_types = {child.field.field_type for child in radio_group.children}
            if len(children_types) > 1:
                warnings.append(
                    f"Radio group {radio_group.field.id} has mixed child types: {children_types}"
                )
        
        is_valid = (
            len(orphaned_fields) == 0 and
            len(circular_references) == 0 and
            len(broken_relationships) == 0 and
            len([c for c in naming_conflicts if c.severity == "critical"]) == 0
        )
        
        validation = HierarchyValidation(
            is_valid=is_valid,
            orphaned_fields=orphaned_fields,
            circular_references=circular_references,
            naming_conflicts=naming_conflicts,
            broken_relationships=broken_relationships,
            warnings=warnings
        )
        
        logger.info(f"Hierarchy validation complete: {'valid' if is_valid else 'invalid'}")
        if not is_valid:
            logger.warning(f"Validation issues: {len(orphaned_fields)} orphaned, "
                          f"{len(circular_references)} circular, "
                          f"{len(broken_relationships)} broken relationships")
        
        return validation
    
    def _detect_circular_references(self, tree: HierarchyTree) -> List[str]:
        """
        Detect circular references in the hierarchy.
        
        Args:
            tree: Hierarchy tree to check
            
        Returns:
            List of circular reference descriptions
        """
        circular_refs = []
        visited = set()
        path = []
        
        def dfs(node: HierarchyNode) -> None:
            """Depth-first search to detect cycles."""
            if node.field.id in path:
                # Found a cycle
                cycle_start = path.index(node.field.id)
                cycle = path[cycle_start:] + [node.field.id]
                circular_refs.append(" -> ".join(cycle))
                return
            
            if node.field.id in visited:
                return
            
            visited.add(node.field.id)
            path.append(node.field.id)
            
            for child in node.children:
                dfs(child)
            
            path.remove(node.field.id)
        
        # Check each root node
        for root_node in tree.root_nodes:
            dfs(root_node)
        
        return circular_refs
    
    def _detect_hierarchy_naming_conflicts(self, tree: HierarchyTree) -> List[ConflictReport]:
        """
        Detect naming conflicts in hierarchy.
        
        Args:
            tree: Hierarchy tree to check
            
        Returns:
            List of conflict reports
        """
        conflicts = []
        
        # Check for sibling name conflicts
        for node in tree.node_map.values():
            if node.children:
                child_names = [child.field.name for child in node.children]
                duplicate_names = [name for name in child_names if child_names.count(name) > 1]
                
                for dup_name in set(duplicate_names):
                    conflicts.append(ConflictReport(
                        conflict_type="sibling_name_conflict",
                        affected_fields=[child.field.id for child in node.children 
                                       if child.field.name == dup_name],
                        description=f"Sibling fields have duplicate name: {dup_name}",
                        suggested_resolution="Add unique modifiers to sibling field names",
                        severity="error"
                    ))
        
        # Check for parent-child name conflicts
        for node in tree.node_map.values():
            if node.parent and node.field.name == node.parent.field.name:
                conflicts.append(ConflictReport(
                    conflict_type="parent_child_name_conflict",
                    affected_fields=[node.field.id, node.parent.field.id],
                    description=f"Parent and child have same name: {node.field.name}",
                    suggested_resolution="Use hierarchical naming with different element names",
                    severity="warning"
                ))
        
        # Check for qualified name conflicts across the tree
        qualified_names = {}
        for node in tree.node_map.values():
            qname = node.qualified_name
            if qname in qualified_names:
                conflicts.append(ConflictReport(
                    conflict_type="qualified_name_conflict",
                    affected_fields=[node.field.id, qualified_names[qname]],
                    description=f"Duplicate qualified name: {qname}",
                    suggested_resolution="Ensure unique field names within each hierarchy level",
                    severity="critical"
                ))
            else:
                qualified_names[qname] = node.field.id
        
        return conflicts
    
    def generate_qualified_names(self, tree: HierarchyTree) -> Dict[str, str]:
        """
        Generate fully qualified names for all fields.
        
        Args:
            tree: Hierarchy tree
            
        Returns:
            Dictionary mapping field_id to qualified name
        """
        qualified_names = {}
        
        for field_id, node in tree.node_map.items():
            qualified_names[field_id] = node.qualified_name
        
        return qualified_names
    
    def detect_naming_conflicts(self, tree: HierarchyTree, 
                              proposed_names: Dict[str, str]) -> List[ConflictReport]:
        """
        Detect potential naming conflicts with proposed names.
        
        Args:
            tree: Current hierarchy tree
            proposed_names: Dictionary of field_id -> proposed_name
            
        Returns:
            List of conflict reports
        """
        conflicts = []
        
        # Create a temporary copy of the tree with proposed names
        temp_updates = {}
        for field_id, proposed_name in proposed_names.items():
            if field_id in tree.node_map:
                temp_updates[field_id] = proposed_name
        
        # Apply temporary updates
        original_names = {}
        for field_id, new_name in temp_updates.items():
            node = tree.node_map[field_id]
            original_names[field_id] = node.field.name
            node.field.name = new_name
        
        # Regenerate qualified names
        self._generate_qualified_names(tree.root_nodes)
        
        # Check for conflicts
        conflicts = self._detect_hierarchy_naming_conflicts(tree)
        
        # Restore original names
        for field_id, original_name in original_names.items():
            tree.node_map[field_id].field.name = original_name
        
        # Regenerate original qualified names
        self._generate_qualified_names(tree.root_nodes)
        
        return conflicts
    
    def get_hierarchy_statistics(self, tree: HierarchyTree) -> Dict[str, Any]:
        """
        Get statistics about the hierarchy.
        
        Args:
            tree: Hierarchy tree
            
        Returns:
            Dictionary with hierarchy statistics
        """
        stats = {
            "total_nodes": tree.total_nodes,
            "root_nodes": len(tree.root_nodes),
            "max_depth": tree.max_depth,
            "radio_groups": len(tree.get_radio_groups()),
            "field_types": defaultdict(int),
            "nodes_by_depth": defaultdict(int),
            "parent_child_relationships": 0,
            "orphaned_nodes": 0
        }
        
        for node in tree.node_map.values():
            # Count field types
            stats["field_types"][node.field.field_type] += 1
            
            # Count nodes by depth
            stats["nodes_by_depth"][node.depth] += 1
            
            # Count relationships
            if node.parent or node.children:
                stats["parent_child_relationships"] += 1
            
            # Count orphaned nodes (should have parent but parent not found)
            if node.field.parent and not node.parent:
                stats["orphaned_nodes"] += 1
        
        # Convert defaultdicts to regular dicts
        stats["field_types"] = dict(stats["field_types"])
        stats["nodes_by_depth"] = dict(stats["nodes_by_depth"])
        
        return stats