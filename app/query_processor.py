#!/usr/bin/env python3
"""
Query Processor for RAG-KG Customer Service QA System

Handles entity extraction, intent detection, and query preprocessing.
"""

import re
import logging
from typing import Dict, List, Any, Optional
import ollama
from dotenv import load_dotenv
import os

load_dotenv()
logger = logging.getLogger(__name__)

class QueryProcessor:
    """Processes customer queries for entity extraction and intent detection"""

    def __init__(self):
        self.model_name = os.getenv("PARSING_MODEL", "mistral:7b-instruct-q4_0")

        # Entity extraction patterns
        self.entity_patterns = {
            'product': [
                r'\b(mobile app|web portal|api|desktop client|mobile website)\b',
                r'\b(ios|android|windows|mac|linux)\b',
                r'\b(browser|chrome|firefox|safari|edge)\b'
            ],
            'error': [
                r'\b(error|exception|failed|crash|bug)\b',
                r'\b(404|500|403|401|502)\b',
                r'\b(null|undefined|timeout|connection)\b'
            ],
            'action': [
                r'\b(login|logout|click|submit|upload|download)\b',
                r'\b(reset|change|update|create|delete)\b'
            ]
        }

        # Intent patterns
        self.intent_patterns = {
            'troubleshooting': [
                r'\b(problem|issue|error|not working|broken|stuck)\b',
                r'\b(help|fix|solve|resolve)\b'
            ],
            'feature_request': [
                r'\b(add|implement|feature|enhancement|improvement)\b',
                r'\b(would like|need|want|missing)\b'
            ],
            'bug_report': [
                r'\b(bug|defect|crash|freeze|hang)\b',
                r'\b(report|found|discovered|experienced)\b'
            ],
            'general_inquiry': [
                r'\b(how|what|when|where|why|can i|do you)\b',
                r'\b(information|details|explain|tell me)\b'
            ]
        }

    def extract_entities_rule_based(self, text: str) -> Dict[str, List[str]]:
        """Extract entities using regex patterns"""
        entities = {}

        for entity_type, patterns in self.entity_patterns.items():
            matches = []
            for pattern in patterns:
                found = re.findall(pattern, text, re.IGNORECASE)
                matches.extend(found)

            if matches:
                entities[entity_type] = list(set(matches))  # Remove duplicates

        return entities

    def detect_intent_rule_based(self, text: str) -> str:
        """Detect user intent using pattern matching"""
        text_lower = text.lower()

        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return intent

        return 'general_inquiry'  # Default intent

    def extract_entities_llm(self, text: str) -> Dict[str, List[str]]:
        """Extract entities using LLM"""
        try:
            prompt = f"""
Analyze this customer service query and extract key entities. Return JSON format only.

Query: {text}

Extract:
1. Products/platforms mentioned
2. Actions being performed
3. Error types or issues
4. Specific features or components

Format: {{"products": [], "actions": [], "errors": [], "features": []}}
"""

            response = ollama.chat(
                model=self.model_name,
                messages=[{'role': 'user', 'content': prompt}],
                options={'temperature': 0.1, 'num_predict': 200}
            )

            result_text = response['message']['content']

            # Parse JSON response
            try:
                # Clean up response
                json_start = result_text.find('{')
                json_end = result_text.rfind('}') + 1
                if json_start != -1 and json_end != -1:
                    json_str = result_text[json_start:json_end]
                    entities = eval(json_str)  # Using eval for simple dict parsing
                    return entities
            except:
                logger.warning(f"Failed to parse LLM entity extraction response: {result_text}")

        except Exception as e:
            logger.error(f"LLM entity extraction failed: {str(e)}")

        return {}

    def detect_intent_llm(self, text: str) -> str:
        """Detect intent using LLM"""
        try:
            prompt = f"""
Classify this customer service query into one of these categories:
- troubleshooting: Technical problems, errors, fixes needed
- feature_request: New features, enhancements, additions wanted
- bug_report: Reporting bugs, crashes, defects found
- general_inquiry: Questions about how to use, information requests

Query: {text}

Return only the category name.
"""

            response = ollama.chat(
                model=self.model_name,
                messages=[{'role': 'user', 'content': prompt}],
                options={'temperature': 0.0, 'num_predict': 50}
            )

            intent = response['message']['content'].strip().lower()

            # Validate intent
            valid_intents = ['troubleshooting', 'feature_request', 'bug_report', 'general_inquiry']
            if intent in valid_intents:
                return intent

        except Exception as e:
            logger.error(f"LLM intent detection failed: {str(e)}")

        return 'general_inquiry'  # Default

    def process(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process a query with hybrid entity extraction and intent detection"""
        logger.info(f"Processing query: {query[:100]}...")

        # Rule-based extraction (fast, reliable)
        rule_entities = self.extract_entities_rule_based(query)
        rule_intent = self.detect_intent_rule_based(query)

        # LLM-based extraction (more accurate, slower)
        llm_entities = {}
        llm_intent = rule_intent

        try:
            llm_entities = self.extract_entities_llm(query)
            llm_intent = self.detect_intent_llm(query)
        except Exception as e:
            logger.warning(f"LLM processing failed, using rule-based only: {str(e)}")

        # Combine results (prefer LLM when available, fallback to rules)
        final_entities = {}
        for key in set(list(rule_entities.keys()) + list(llm_entities.keys())):
            rule_vals = rule_entities.get(key, [])
            llm_vals = llm_entities.get(key, [])
            final_entities[key] = list(set(rule_vals + llm_vals))

        # Use LLM intent if available, otherwise rule-based
        final_intent = llm_intent if llm_intent != 'general_inquiry' else rule_intent

        # Add context information
        if context:
            final_entities['context'] = context

        result = {
            'original_query': query,
            'entities': final_entities,
            'intent': final_intent,
            'confidence': 0.8 if llm_entities else 0.6,  # Higher confidence with LLM
            'processing_method': 'hybrid' if llm_entities else 'rule_based'
        }

        logger.info(f"Query processed - Intent: {final_intent}, Entities: {len(final_entities)}")
        return result