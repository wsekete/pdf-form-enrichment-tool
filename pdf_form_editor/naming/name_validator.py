"""
BEM Name Validator

Comprehensive validation for generated BEM names including syntax,
uniqueness, and hierarchy compliance.
"""

import re
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from enum import Enum

from ..utils.logging import get_logger

logger = get_logger(__name__)


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """Individual validation issue."""
    severity: ValidationSeverity
    message: str
    field_name: str = ""
    suggestion: str = ""


@dataclass
class ValidationResult:
    """Result of BEM name validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]
    issues: List[ValidationIssue] = None
    
    def __post_init__(self):
        if self.issues is None:
            self.issues = []


@dataclass
class UniquenessResult:
    """Result of uniqueness checking."""
    is_unique: bool
    conflicts: List[str]
    suggested_alternatives: List[str]
    scope: str = "document"


@dataclass
class HierarchyValidation:
    """Result of hierarchy compliance validation."""
    is_compliant: bool
    parent_child_consistent: bool
    inheritance_valid: bool
    issues: List[str]
    suggestions: List[str]


class BEMNameValidator:
    """Comprehensive validation for generated BEM names."""
    
    # BEM syntax pattern (block_element__modifier format)
    # Note: No consecutive hyphens allowed within components
    BEM_PATTERN = re.compile(
        r'^[a-z]([a-z0-9]|-(?!-|$))*(_[a-z]([a-z0-9]|-(?!-|$))*)?(__[a-z]([a-z0-9]|-(?!-|$))*)?$'
    )
    
    # Reserved words that shouldn't be used in BEM names
    RESERVED_WORDS = {
        'group', 'custom', 'temp', 'field', 'form', 'pdf', 'document',
        'page', 'section', 'container', 'wrapper', 'holder', 'box',
        'input', 'button', 'text', 'number', 'date', 'time'
    }
    
    # Maximum recommended lengths
    MAX_LENGTH = 100
    MAX_BLOCK_LENGTH = 40
    MAX_ELEMENT_LENGTH = 30
    MAX_MODIFIER_LENGTH = 20
    
    # Minimum lengths
    MIN_LENGTH = 3
    MIN_COMPONENT_LENGTH = 2
    
    def __init__(self):
        """Initialize the validator."""
        self.validated_names = set()
        logger.info("BEMNameValidator initialized")
    
    def validate_bem_syntax(self, name: str) -> ValidationResult:
        """
        Validate BEM syntax compliance.
        
        Args:
            name: BEM name to validate
            
        Returns:
            ValidationResult with syntax validation details
        """
        errors = []
        warnings = []
        suggestions = []
        issues = []
        
        # Basic format validation
        if not name:
            errors.append("BEM name cannot be empty")
            return ValidationResult(False, errors, warnings, suggestions, issues)
        
        # Length validation
        if len(name) < self.MIN_LENGTH:
            errors.append(f"BEM name too short: {len(name)} chars (minimum: {self.MIN_LENGTH})")
        elif len(name) > self.MAX_LENGTH:
            errors.append(f"BEM name too long: {len(name)} chars (maximum: {self.MAX_LENGTH})")
            suggestions.append(f"Consider shortening to under {self.MAX_LENGTH} characters")
        
        # Pattern validation
        if not self.BEM_PATTERN.match(name):
            errors.append("Invalid BEM syntax - must follow block_element__modifier pattern")
            suggestions.append("Use format: block_element__modifier (lowercase, hyphens, underscores)")
            
            # Provide specific syntax issues
            if not name[0].islower():
                issues.append(ValidationIssue(
                    ValidationSeverity.ERROR,
                    "BEM name must start with lowercase letter",
                    name,
                    f"Try: {name[0].lower()}{name[1:]}"
                ))
            
            if re.search(r'[^a-z0-9_-]', name):
                invalid_chars = set(re.findall(r'[^a-z0-9_-]', name))
                issues.append(ValidationIssue(
                    ValidationSeverity.ERROR,
                    f"Invalid characters found: {', '.join(invalid_chars)}",
                    name,
                    "Use only lowercase letters, numbers, hyphens, and underscores"
                ))
        
        # Component validation
        components = self._parse_bem_components(name)
        if components:
            block, element, modifier = components
            
            # Validate individual components
            self._validate_component(block, "block", errors, warnings, suggestions, issues)
            if element:
                self._validate_component(element, "element", errors, warnings, suggestions, issues)
            if modifier:
                self._validate_component(modifier, "modifier", errors, warnings, suggestions, issues)
        
        # Reserved word validation
        reserved_violations = self._check_reserved_words(name)
        if reserved_violations:
            warnings.extend([f"Contains reserved word: {word}" for word in reserved_violations])
            suggestions.append("Consider using more specific terminology")
        
        # Structure validation
        structure_issues = self._validate_bem_structure(name)
        warnings.extend(structure_issues)
        
        is_valid = len(errors) == 0
        
        result = ValidationResult(is_valid, errors, warnings, suggestions, issues)
        
        logger.debug(f"Syntax validation for '{name}': {'PASS' if is_valid else 'FAIL'} "
                    f"({len(errors)} errors, {len(warnings)} warnings)")
        
        return result
    
    def check_uniqueness(self, name: str, existing_names: List[str], 
                        scope: str = 'document') -> UniquenessResult:
        """
        Ensure name uniqueness within specified scope.
        
        Args:
            name: BEM name to check
            existing_names: List of already used names
            scope: Scope for uniqueness checking
            
        Returns:
            UniquenessResult with uniqueness status and alternatives
        """
        is_unique = name not in existing_names
        conflicts = [name] if not is_unique else []
        
        alternatives = []
        if not is_unique:
            alternatives = self.suggest_alternatives(name, existing_names)
        
        result = UniquenessResult(
            is_unique=is_unique,
            conflicts=conflicts,
            suggested_alternatives=alternatives,
            scope=scope
        )
        
        logger.debug(f"Uniqueness check for '{name}': {'UNIQUE' if is_unique else 'CONFLICT'}")
        
        return result
    
    def suggest_alternatives(self, base_name: str, existing_names: List[str]) -> List[str]:
        """
        Generate alternative names for conflicts.
        
        Args:
            base_name: Original name that conflicts
            existing_names: List of existing names to avoid
            
        Returns:
            List of alternative names
        """
        alternatives = []
        
        # Parse base name components
        components = self._parse_bem_components(base_name)
        if not components:
            return alternatives
        
        block, element, modifier = components
        
        # Strategy 1: Add numeric modifiers
        for i in range(2, 10):
            if modifier:
                candidate = f"{block}_{element}__{modifier}-{i}"
            elif element:
                candidate = f"{block}_{element}__{i}"
            else:
                candidate = f"{block}__{i}"
            
            if candidate not in existing_names:
                alternatives.append(candidate)
        
        # Strategy 2: Add descriptive modifiers
        descriptive_modifiers = ['primary', 'secondary', 'additional', 'alternate', 'extra']
        for desc_mod in descriptive_modifiers:
            if modifier:
                candidate = f"{block}_{element}__{modifier}-{desc_mod}"
            elif element:
                candidate = f"{block}_{element}__{desc_mod}"
            else:
                candidate = f"{block}__{desc_mod}"
            
            if candidate not in existing_names:
                alternatives.append(candidate)
        
        # Strategy 3: Modify element name
        if element:
            element_variants = [
                f"{element}-field",
                f"{element}-input",
                f"{element}-value",
                f"{element}-data"
            ]
            
            for variant in element_variants:
                candidate = f"{block}_{variant}"
                if modifier:
                    candidate += f"__{modifier}"
                
                if candidate not in existing_names:
                    alternatives.append(candidate)
        
        # Strategy 4: Modify block name
        block_variants = [
            f"{block}-section",
            f"{block}-group",
            f"{block}-area"
        ]
        
        for variant in block_variants:
            candidate = variant
            if element:
                candidate += f"_{element}"
            if modifier:
                candidate += f"__{modifier}"
            
            if candidate not in existing_names:
                alternatives.append(candidate)
        
        return alternatives[:5]  # Return top 5 alternatives
    
    def validate_hierarchy_compliance(self, name: str, parent_name: Optional[str], 
                                    children: List[str]) -> HierarchyValidation:
        """
        Validate hierarchical naming consistency.
        
        Args:
            name: Current field name
            parent_name: Parent field name (if any)
            children: List of child field names
            
        Returns:
            HierarchyValidation with compliance status
        """
        issues = []
        suggestions = []
        parent_child_consistent = True
        inheritance_valid = True
        
        # Parse current name components
        components = self._parse_bem_components(name)
        if not components:
            issues.append("Cannot validate hierarchy - invalid BEM syntax")
            return HierarchyValidation(False, False, False, issues, suggestions)
        
        current_block, current_element, current_modifier = components
        
        # Validate parent-child relationship
        if parent_name:
            parent_components = self._parse_bem_components(parent_name)
            if parent_components:
                parent_block, parent_element, parent_modifier = parent_components
                
                # Check block inheritance
                if current_block != parent_block:
                    parent_child_consistent = False
                    issues.append(f"Block mismatch with parent: '{current_block}' vs '{parent_block}'")
                    suggestions.append(f"Consider using parent block: {parent_block}_{current_element}")
        
        # Validate children consistency
        for child_name in children:
            child_components = self._parse_bem_components(child_name)
            if child_components:
                child_block, child_element, child_modifier = child_components
                
                # Children should share the same block
                if child_block != current_block:
                    parent_child_consistent = False
                    issues.append(f"Child block mismatch: '{child_block}' should be '{current_block}'")
        
        # Check for circular references (basic check)
        if parent_name and parent_name in children:
            inheritance_valid = False
            issues.append("Circular reference detected: parent appears in children list")
        
        # Radio group specific validations
        if 'radio' in name.lower() or any('radio' in child.lower() for child in children):
            if not children and 'group' not in name:
                suggestions.append("Radio fields should have group container or children")
        
        is_compliant = parent_child_consistent and inheritance_valid and len(issues) == 0
        
        result = HierarchyValidation(
            is_compliant=is_compliant,
            parent_child_consistent=parent_child_consistent,
            inheritance_valid=inheritance_valid,
            issues=issues,
            suggestions=suggestions
        )
        
        logger.debug(f"Hierarchy validation for '{name}': {'PASS' if is_compliant else 'FAIL'}")
        
        return result
    
    def _parse_bem_components(self, bem_name: str) -> Optional[tuple]:
        """Parse BEM name into block, element, and modifier components."""
        try:
            # Split by modifier delimiter
            parts = bem_name.split('__')
            base = parts[0]
            modifier = parts[1] if len(parts) > 1 else None
            
            # Split base by element delimiter
            if '_' in base:
                base_parts = base.split('_')
                block = '_'.join(base_parts[:-1])
                element = base_parts[-1]
            else:
                block = base
                element = None
            
            return (block, element, modifier)
        
        except Exception:
            return None
    
    def _validate_component(self, component: str, component_type: str, 
                          errors: List[str], warnings: List[str], 
                          suggestions: List[str], issues: List[ValidationIssue]):
        """Validate individual BEM component."""
        if not component:
            return
        
        # Length validation
        max_lengths = {
            'block': self.MAX_BLOCK_LENGTH,
            'element': self.MAX_ELEMENT_LENGTH,
            'modifier': self.MAX_MODIFIER_LENGTH
        }
        
        max_len = max_lengths.get(component_type, 30)
        
        if len(component) < self.MIN_COMPONENT_LENGTH:
            errors.append(f"{component_type.capitalize()} too short: '{component}'")
        elif len(component) > max_len:
            warnings.append(f"{component_type.capitalize()} is long: '{component}' "
                          f"({len(component)} chars)")
            suggestions.append(f"Consider shortening {component_type} to under {max_len} chars")
        
        # Character validation
        if not re.match(r'^[a-z][a-z0-9-]*$', component):
            issues.append(ValidationIssue(
                ValidationSeverity.ERROR,
                f"Invalid {component_type} format: '{component}'",
                component,
                f"{component_type.capitalize()} must start with letter, use only lowercase, numbers, hyphens"
            ))
        
        # Consecutive hyphens
        if '--' in component:
            warnings.append(f"{component_type.capitalize()} has consecutive hyphens: '{component}'")
            suggestions.append("Avoid consecutive hyphens within components")
        
        # Leading/trailing hyphens
        if component.startswith('-') or component.endswith('-'):
            errors.append(f"{component_type.capitalize()} cannot start/end with hyphen: '{component}'")
    
    def _check_reserved_words(self, name: str) -> List[str]:
        """Check for reserved words in BEM name."""
        name_lower = name.lower()
        violations = []
        
        for reserved in self.RESERVED_WORDS:
            if reserved in name_lower:
                violations.append(reserved)
        
        return violations
    
    def _validate_bem_structure(self, name: str) -> List[str]:
        """Validate overall BEM structure and provide warnings."""
        warnings = []
        
        # Check for common anti-patterns
        if name.count('_') > 2:
            warnings.append("Complex element structure - consider simplifying")
        
        if name.count('__') > 1:
            warnings.append("Multiple modifiers detected - BEM recommends single modifier")
        
        if len(name.split('_')[0]) < 3:
            warnings.append("Very short block name - consider more descriptive naming")
        
        # Check for numeric-only components
        components = self._parse_bem_components(name)
        if components:
            block, element, modifier = components
            
            if block and block.replace('-', '').isdigit():
                warnings.append("Block name is numeric - use descriptive names")
            
            if element and element.replace('-', '').isdigit():
                warnings.append("Element name is numeric - use descriptive names")
        
        return warnings
    
    def validate_batch(self, names: List[str]) -> Dict[str, ValidationResult]:
        """
        Validate multiple BEM names for batch processing.
        
        Args:
            names: List of BEM names to validate
            
        Returns:
            Dictionary mapping names to their validation results
        """
        results = {}
        existing_names = set()
        
        for name in names:
            # Syntax validation
            syntax_result = self.validate_bem_syntax(name)
            
            # Uniqueness validation
            uniqueness_result = self.check_uniqueness(name, list(existing_names))
            
            # Combine results
            combined_result = ValidationResult(
                is_valid=syntax_result.is_valid and uniqueness_result.is_unique,
                errors=syntax_result.errors + ([] if uniqueness_result.is_unique else 
                                             [f"Duplicate name: {name}"]),
                warnings=syntax_result.warnings,
                suggestions=syntax_result.suggestions + uniqueness_result.suggested_alternatives,
                issues=syntax_result.issues
            )
            
            results[name] = combined_result
            
            # Track for uniqueness checking
            if uniqueness_result.is_unique:
                existing_names.add(name)
        
        logger.info(f"Batch validation completed: {len(names)} names, "
                   f"{sum(1 for r in results.values() if r.is_valid)} valid")
        
        return results
    
    def get_validation_summary(self, results: Dict[str, ValidationResult]) -> Dict[str, Any]:
        """Generate summary statistics for validation results."""
        total_names = len(results)
        valid_names = sum(1 for r in results.values() if r.is_valid)
        total_errors = sum(len(r.errors) for r in results.values())
        total_warnings = sum(len(r.warnings) for r in results.values())
        
        return {
            'total_names': total_names,
            'valid_names': valid_names,
            'invalid_names': total_names - valid_names,
            'success_rate': valid_names / total_names if total_names > 0 else 0,
            'total_errors': total_errors,
            'total_warnings': total_warnings,
            'average_errors_per_name': total_errors / total_names if total_names > 0 else 0,
            'average_warnings_per_name': total_warnings / total_names if total_names > 0 else 0
        }