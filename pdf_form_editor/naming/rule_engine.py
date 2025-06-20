"""
Rule-Based Fallback Engine

Fallback BEM generation when training patterns are insufficient.
Uses semantic analysis and established naming conventions.
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum

from ..core.field_extractor import FormField, FieldContext
from ..utils.logging import get_logger

logger = get_logger(__name__)


class SemanticCategory(Enum):
    """Semantic categories for form fields."""
    PERSONAL_INFO = "personal"
    CONTACT_INFO = "contact"
    FINANCIAL = "financial"
    LEGAL = "legal"
    SELECTION = "selection"
    DATE_TIME = "datetime"
    IDENTIFICATION = "identification"
    UNKNOWN = "unknown"


@dataclass
class SemanticAnalysis:
    """Analysis of field meaning from context."""
    primary_category: SemanticCategory
    secondary_category: str  # More specific subcategory
    confidence: float
    supporting_evidence: List[str]
    suggested_block: str = ""
    suggested_element: str = ""


@dataclass
class RuleBasedResult:
    """Result from rule-based name generation."""
    bem_name: str
    confidence: float
    reasoning: str
    semantic_analysis: Optional[SemanticAnalysis] = None


class RuleBasedEngine:
    """Fallback BEM generation using rule-based approach."""
    
    # Predefined naming rules based on semantic analysis
    BEM_RULES = {
        # Personal information
        'personal_name': 'owner-information_name',
        'personal_first_name': 'owner-information_name__first',
        'personal_last_name': 'owner-information_name__last',
        'personal_middle_name': 'owner-information_name__middle',
        'personal_full_name': 'owner-information_name__full',
        'personal_birth_date': 'owner-information_date__birth',
        'personal_age': 'owner-information_age',
        'personal_gender': 'owner-information_gender',
        'personal_marital_status': 'owner-information_status__marital',
        
        # Contact information
        'contact_address': 'contact-information_address',
        'contact_street': 'contact-information_address__street',
        'contact_city': 'contact-information_address__city',
        'contact_state': 'contact-information_address__state',
        'contact_zip': 'contact-information_address__zip',
        'contact_country': 'contact-information_address__country',
        'contact_phone': 'contact-information_phone',
        'contact_home_phone': 'contact-information_phone__home',
        'contact_work_phone': 'contact-information_phone__work',
        'contact_mobile_phone': 'contact-information_phone__mobile',
        'contact_email': 'contact-information_email',
        'contact_work_email': 'contact-information_email__work',
        'contact_personal_email': 'contact-information_email__personal',
        
        # Financial information
        'financial_amount': 'payment_amount',
        'financial_premium': 'payment_amount__premium',
        'financial_deductible': 'payment_amount__deductible',
        'financial_benefit': 'payment_amount__benefit',
        'financial_currency': 'payment_currency',
        'financial_frequency': 'payment_frequency',
        'financial_method': 'payment_method',
        'financial_account': 'payment_account',
        'financial_routing': 'payment_routing',
        
        # Legal and signature fields
        'legal_signature': 'signatures_owner',
        'legal_witness_signature': 'signatures_witness',
        'legal_notary_signature': 'signatures_notary',
        'legal_date_signed': 'signatures_date',
        'legal_agreement': 'acknowledgment_agreement',
        'legal_consent': 'acknowledgment_consent',
        'legal_authorization': 'acknowledgment_authorization',
        
        # Selection fields
        'selection_radio': 'selection_option',
        'selection_checkbox': 'selection_checkbox',
        'selection_dropdown': 'selection_choice',
        'selection_yes_no': 'selection_boolean',
        
        # Identification
        'id_ssn': 'identification_ssn',
        'id_license': 'identification_license',
        'id_passport': 'identification_passport',
        'id_tax_id': 'identification_tax-id',
        'id_employee_id': 'identification_employee-id',
        'id_policy_number': 'identification_policy-number',
        'id_account_number': 'identification_account-number',
        
        # Date and time
        'datetime_date': 'general_date',
        'datetime_time': 'general_time',
        'datetime_effective': 'general_date__effective',
        'datetime_expiration': 'general_date__expiration',
        'datetime_birth': 'general_date__birth',
        
        # Generic fallbacks
        'generic_text': 'general_input',
        'generic_number': 'general_number',
        'generic_field': 'general_field'
    }
    
    # Keyword patterns for semantic analysis
    SEMANTIC_PATTERNS = {
        SemanticCategory.PERSONAL_INFO: {
            'keywords': [
                'name', 'first', 'last', 'middle', 'full', 'fname', 'lname', 'mname',
                'birth', 'age', 'gender', 'sex', 'marital', 'married', 'single',
                'spouse', 'occupation', 'title', 'suffix', 'prefix'
            ],
            'context_words': [
                'personal', 'applicant', 'owner', 'insured', 'policyholder',
                'individual', 'person', 'client', 'customer'
            ]
        },
        
        SemanticCategory.CONTACT_INFO: {
            'keywords': [
                'address', 'street', 'city', 'state', 'zip', 'postal', 'country',
                'phone', 'telephone', 'mobile', 'cell', 'fax', 'email', 'mail',
                'contact', 'home', 'work', 'business', 'residence'
            ],
            'context_words': [
                'contact', 'address', 'location', 'residence', 'mailing',
                'correspondence', 'communication'
            ]
        },
        
        SemanticCategory.FINANCIAL: {
            'keywords': [
                'amount', 'dollar', 'price', 'cost', 'fee', 'premium', 'payment',
                'deposit', 'balance', 'total', 'sum', 'value', 'benefit',
                'deductible', 'coverage', 'limit', 'currency', 'account',
                'routing', 'bank', 'financial', 'money', 'cash'
            ],
            'context_words': [
                'payment', 'financial', 'billing', 'premium', 'cost',
                'monetary', 'economic', 'fiscal'
            ]
        },
        
        SemanticCategory.LEGAL: {
            'keywords': [
                'signature', 'sign', 'consent', 'agreement', 'authorization',
                'acknowledge', 'witness', 'notary', 'legal', 'terms',
                'conditions', 'policy', 'contract', 'document'
            ],
            'context_words': [
                'signature', 'legal', 'authorization', 'consent', 'agreement',
                'acknowledgment', 'witness', 'notarization'
            ]
        },
        
        SemanticCategory.IDENTIFICATION: {
            'keywords': [
                'ssn', 'social', 'security', 'license', 'passport', 'id',
                'identification', 'number', 'policy', 'account', 'member',
                'employee', 'tax', 'tin', 'ein'
            ],
            'context_words': [
                'identification', 'id', 'number', 'policy', 'account',
                'member', 'reference'
            ]
        },
        
        SemanticCategory.DATE_TIME: {
            'keywords': [
                'date', 'time', 'day', 'month', 'year', 'effective', 'expiration',
                'birth', 'dob', 'timestamp', 'when', 'schedule'
            ],
            'context_words': [
                'date', 'time', 'when', 'schedule', 'effective', 'expiration'
            ]
        },
        
        SemanticCategory.SELECTION: {
            'keywords': [
                'select', 'choose', 'option', 'choice', 'radio', 'checkbox',
                'dropdown', 'list', 'yes', 'no', 'true', 'false', 'check'
            ],
            'context_words': [
                'selection', 'choice', 'option', 'pick', 'choose'
            ]
        }
    }
    
    def __init__(self):
        """Initialize the rule-based engine."""
        logger.info("RuleBasedEngine initialized")
    
    def generate_fallback_name(self, field: FormField, context: FieldContext) -> Optional[RuleBasedResult]:
        """
        Generate BEM name using rule-based approach.
        
        Args:
            field: Form field to generate name for
            context: Field context information
            
        Returns:
            RuleBasedResult with generated name and reasoning
        """
        logger.debug(f"Generating rule-based name for field {field.id}")
        
        # Perform semantic analysis
        semantic_analysis = self.analyze_field_semantics(context)
        
        # Apply naming rules based on semantic analysis
        bem_name = self.apply_naming_rules(semantic_analysis, field)
        
        if bem_name:
            result = RuleBasedResult(
                bem_name=bem_name,
                confidence=semantic_analysis.confidence * 0.8,  # Reduce for rule-based
                reasoning=f"Rule-based generation: {semantic_analysis.primary_category.value} -> "
                         f"{semantic_analysis.secondary_category}",
                semantic_analysis=semantic_analysis
            )
            
            logger.debug(f"Generated rule-based name: {bem_name}")
            return result
        
        logger.warning(f"Failed to generate rule-based name for field {field.id}")
        return None
    
    def analyze_field_semantics(self, context: FieldContext) -> SemanticAnalysis:
        """
        Analyze field meaning from context.
        
        Args:
            context: Field context to analyze
            
        Returns:
            SemanticAnalysis with categorization and confidence
        """
        # Combine all context text
        context_text = self._extract_context_text(context).lower()
        
        # Score each semantic category
        category_scores = {}
        
        for category, patterns in self.SEMANTIC_PATTERNS.items():
            score = self._calculate_semantic_score(context_text, patterns)
            category_scores[category] = score
        
        # Find best matching category
        best_category = max(category_scores, key=category_scores.get)
        best_score = category_scores[best_category]
        
        # Determine secondary category (more specific)
        secondary = self._determine_secondary_category(context_text, best_category)
        
        # Find supporting evidence
        evidence = self._find_supporting_evidence(context_text, best_category)
        
        analysis = SemanticAnalysis(
            primary_category=best_category,
            secondary_category=secondary,
            confidence=best_score,
            supporting_evidence=evidence
        )
        
        logger.debug(f"Semantic analysis: {best_category.value}/{secondary} "
                    f"(confidence: {best_score:.2f})")
        
        return analysis
    
    def apply_naming_rules(self, semantic_analysis: SemanticAnalysis, field: FormField) -> str:
        """
        Apply established naming rules based on field semantics.
        
        Args:
            semantic_analysis: Semantic analysis of the field
            field: Form field properties
            
        Returns:
            BEM-compliant name string
        """
        category = semantic_analysis.primary_category
        subcategory = semantic_analysis.secondary_category
        
        # Create rule key
        rule_key = f"{category.value}_{subcategory}"
        
        # Try exact rule match first
        if rule_key in self.BEM_RULES:
            base_name = self.BEM_RULES[rule_key]
        else:
            # Try category-level fallback
            category_key = f"{category.value}_generic"
            if category_key in self.BEM_RULES:
                base_name = self.BEM_RULES[category_key]
            else:
                # Use generic fallback based on field type
                base_name = self._get_type_based_fallback(field.field_type)
        
        # Add field-specific modifiers if needed
        modifier = self._determine_modifier(field, semantic_analysis)
        if modifier and '__' not in base_name:  # Don't add if already has modifier
            base_name = f"{base_name}__{modifier}"
        
        return self._sanitize_bem_name(base_name)
    
    def _extract_context_text(self, context: FieldContext) -> str:
        """Extract all text from field context."""
        text_parts = []
        
        if context.label:
            text_parts.append(context.label)
        if context.section_header:
            text_parts.append(context.section_header)
        if context.nearby_text:
            text_parts.extend(context.nearby_text)
        if hasattr(context, 'text_above') and context.text_above:
            text_parts.append(context.text_above)
        if hasattr(context, 'text_below') and context.text_below:
            text_parts.append(context.text_below)
        if hasattr(context, 'text_left') and context.text_left:
            text_parts.append(context.text_left)
        if hasattr(context, 'text_right') and context.text_right:
            text_parts.append(context.text_right)
        
        return ' '.join(text_parts)
    
    def _calculate_semantic_score(self, context_text: str, patterns: Dict[str, List[str]]) -> float:
        """Calculate semantic match score for a category."""
        keyword_score = 0.0
        context_score = 0.0
        
        # Score based on keyword matches
        keywords = patterns.get('keywords', [])
        if keywords:
            keyword_matches = sum(1 for keyword in keywords if keyword in context_text)
            keyword_score = keyword_matches / len(keywords)
        
        # Score based on context word matches
        context_words = patterns.get('context_words', [])
        if context_words:
            context_matches = sum(1 for word in context_words if word in context_text)
            context_score = context_matches / len(context_words)
        
        # Weighted combination (keywords more important)
        total_score = (keyword_score * 0.7) + (context_score * 0.3)
        
        return min(total_score, 1.0)
    
    def _determine_secondary_category(self, context_text: str, primary_category: SemanticCategory) -> str:
        """Determine more specific subcategory within primary category."""
        
        # Define subcategory patterns
        subcategory_patterns = {
            SemanticCategory.PERSONAL_INFO: {
                'name': ['name', 'fname', 'lname', 'first', 'last', 'middle', 'full'],
                'birth_date': ['birth', 'dob', 'born'],
                'age': ['age', 'years', 'old'],
                'gender': ['gender', 'sex', 'male', 'female'],
                'marital_status': ['marital', 'married', 'single', 'spouse'],
                'occupation': ['occupation', 'job', 'work', 'profession', 'title']
            },
            
            SemanticCategory.CONTACT_INFO: {
                'address': ['address', 'street', 'location', 'residence'],
                'city': ['city', 'town', 'municipality'],
                'state': ['state', 'province', 'region'],
                'zip': ['zip', 'postal', 'code'],
                'phone': ['phone', 'telephone', 'mobile', 'cell'],
                'email': ['email', 'mail', 'electronic']
            },
            
            SemanticCategory.FINANCIAL: {
                'amount': ['amount', 'dollar', 'value', 'sum', 'total'],
                'premium': ['premium', 'payment', 'cost'],
                'account': ['account', 'bank', 'routing'],
                'benefit': ['benefit', 'coverage', 'limit']
            },
            
            SemanticCategory.LEGAL: {
                'signature': ['signature', 'sign', 'signed'],
                'agreement': ['agreement', 'consent', 'acknowledge'],
                'authorization': ['authorization', 'authorize', 'permit']
            },
            
            SemanticCategory.IDENTIFICATION: {
                'ssn': ['ssn', 'social', 'security'],
                'license': ['license', 'drivers', 'dl'],
                'policy_number': ['policy', 'number', 'member'],
                'account_number': ['account', 'number']
            },
            
            SemanticCategory.DATE_TIME: {
                'date': ['date', 'day', 'month', 'year'],
                'effective': ['effective', 'start', 'begin'],
                'expiration': ['expiration', 'expire', 'end'],
                'birth': ['birth', 'dob', 'born']
            },
            
            SemanticCategory.SELECTION: {
                'radio': ['radio', 'option', 'choice'],
                'checkbox': ['checkbox', 'check', 'tick'],
                'yes_no': ['yes', 'no', 'true', 'false']
            }
        }
        
        if primary_category in subcategory_patterns:
            patterns = subcategory_patterns[primary_category]
            
            best_subcategory = 'generic'
            best_score = 0
            
            for subcategory, keywords in patterns.items():
                matches = sum(1 for keyword in keywords if keyword in context_text)
                if matches > best_score:
                    best_score = matches
                    best_subcategory = subcategory
            
            return best_subcategory
        
        return 'generic'
    
    def _find_supporting_evidence(self, context_text: str, category: SemanticCategory) -> List[str]:
        """Find specific words that support the semantic categorization."""
        if category not in self.SEMANTIC_PATTERNS:
            return []
        
        evidence = []
        patterns = self.SEMANTIC_PATTERNS[category]
        
        # Find matching keywords
        for keyword in patterns.get('keywords', []):
            if keyword in context_text:
                evidence.append(f"keyword: {keyword}")
        
        # Find matching context words
        for word in patterns.get('context_words', []):
            if word in context_text:
                evidence.append(f"context: {word}")
        
        return evidence[:5]  # Limit to top 5 pieces of evidence
    
    def _get_type_based_fallback(self, field_type: str) -> str:
        """Get fallback BEM name based on field type."""
        type_fallbacks = {
            'text': 'general_input',
            'checkbox': 'selection_checkbox',
            'radio': 'selection_option',
            'choice': 'selection_choice',
            'signature': 'signatures_field',
            'button': 'general_button'
        }
        
        return self.BEM_RULES.get(type_fallbacks.get(field_type, 'generic_field'), 
                                  'general_field')
    
    def _determine_modifier(self, field: FormField, semantic_analysis: SemanticAnalysis) -> Optional[str]:
        """Determine appropriate modifier for the field."""
        # Check field properties for modifiers
        if field.properties.get('required', False):
            return 'required'
        elif field.properties.get('readonly', False):
            return 'readonly'
        
        # Check context for positional modifiers
        context_text = ' '.join(semantic_analysis.supporting_evidence).lower()
        
        if any(word in context_text for word in ['first', 'primary', 'main']):
            return 'primary'
        elif any(word in context_text for word in ['second', 'secondary', 'additional']):
            return 'secondary'
        elif any(word in context_text for word in ['last', 'final']):
            return 'final'
        
        return None
    
    def _sanitize_bem_name(self, bem_name: str) -> str:
        """Ensure BEM name follows proper conventions."""
        # Convert to lowercase
        sanitized = bem_name.lower()
        
        # Replace invalid characters with hyphens
        sanitized = re.sub(r'[^a-z0-9_-]', '-', sanitized)
        
        # Remove multiple consecutive hyphens/underscores
        sanitized = re.sub(r'-+', '-', sanitized)
        sanitized = re.sub(r'_+', '_', sanitized)
        
        # Remove leading/trailing hyphens
        sanitized = sanitized.strip('-_')
        
        # Ensure it starts with a letter
        if sanitized and not sanitized[0].isalpha():
            sanitized = f"field-{sanitized}"
        
        return sanitized or 'general-field'