#!/usr/bin/env python3
"""
Answer Generator for RAG-KG Customer Service QA System

Generates natural language answers using retrieved information and OLLAMA models.
"""

import logging
from typing import List, Dict, Any, Tuple
import ollama
from dotenv import load_dotenv
import os

load_dotenv()
logger = logging.getLogger(__name__)

class AnswerGenerator:
    """Generates answers using retrieved sources and LLM"""

    def __init__(self):
        self.model_name = os.getenv("LLM_MODEL", "llama2:7b-chat-q4_0")
        self.max_context_length = 2048  # Limit context to avoid token limits

    def format_sources(self, sources: List[Dict[str, Any]]) -> str:
        """Format retrieved sources into context string"""
        context_parts = []

        for i, source in enumerate(sources[:5]):  # Limit to top 5 sources
            ticket_id = source.get('ticket_id', 'Unknown')
            node_type = source.get('node_type', 'Unknown')
            text = source.get('text', '')[:300]  # Truncate long text
            score = source.get('score', 0)

            context_parts.append(f"Source {i+1} (Score: {score:.2f}):\n"
                               f"Ticket: {ticket_id}\n"
                               f"Type: {node_type}\n"
                               f"Content: {text}\n")

        return "\n".join(context_parts)

    def generate(self, question: str, sources: List[Dict[str, Any]],
                processed_query: Dict[str, Any]) -> Tuple[str, float]:
        """Generate answer using retrieved sources"""
        try:
            # Format context from sources
            context = self.format_sources(sources)

            # Get query intent and entities for better prompting
            intent = processed_query.get('intent', 'general_inquiry')
            entities = processed_query.get('entities', {})

            # Create intent-specific prompt
            if intent == 'troubleshooting':
                system_prompt = """You are a customer service expert helping users solve technical problems.
Use the provided sources to give step-by-step solutions. Be clear, concise, and actionable."""
            elif intent == 'feature_request':
                system_prompt = """You are a product manager responding to feature requests.
Acknowledge the request and explain current capabilities or roadmap plans."""
            elif intent == 'bug_report':
                system_prompt = """You are a support engineer handling bug reports.
Acknowledge the issue and provide immediate workarounds or next steps."""
            else:
                system_prompt = """You are a helpful customer service assistant.
Provide clear, accurate information based on the available sources."""

            # Build the full prompt
            prompt = f"""{system_prompt}

Question: {question}

Relevant Information:
{context}

Instructions:
1. Answer based primarily on the provided sources
2. If sources don't contain enough information, say so clearly
3. Be helpful, professional, and concise
4. Include specific steps when applicable
5. Reference source tickets when relevant

Answer:"""

            # Generate response
            response = ollama.chat(
                model=self.model_name,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': prompt}
                ],
                options={
                    'temperature': 0.3,  # Lower temperature for more consistent answers
                    'top_p': 0.9,
                    'num_predict': 512  # Limit response length
                }
            )

            answer = response['message']['content'].strip()

            # Calculate confidence based on sources and answer quality
            confidence = self._calculate_confidence(sources, answer, question)

            logger.info(".2f")

            return answer, confidence

        except Exception as e:
            logger.error(f"Answer generation failed: {str(e)}")
            fallback_answer = ("I'm sorry, I encountered an error while processing your question. "
                             "Please try rephrasing your question or contact support directly.")
            return fallback_answer, 0.0

    def _calculate_confidence(self, sources: List[Dict[str, Any]], answer: str, question: str) -> float:
        """Calculate confidence score for the generated answer"""
        if not sources:
            return 0.0

        # Base confidence from source scores
        avg_source_score = sum(s.get('score', 0) for s in sources) / len(sources)

        # Boost confidence if answer references specific sources
        source_references = sum(1 for s in sources if str(s.get('ticket_id', '')) in answer)

        # Boost confidence if answer is substantial (not just fallback)
        answer_length_score = min(len(answer) / 100, 1.0)  # Cap at 100 chars

        # Boost confidence if answer addresses the question
        question_words = set(question.lower().split())
        answer_words = set(answer.lower().split())
        overlap = len(question_words.intersection(answer_words)) / len(question_words) if question_words else 0

        confidence = (
            avg_source_score * 0.4 +
            (source_references / len(sources)) * 0.2 +
            answer_length_score * 0.2 +
            overlap * 0.2
        )

        return min(confidence, 1.0)  # Cap at 1.0

    def generate_fallback(self, question: str, intent: str) -> str:
        """Generate fallback response when no good sources are found"""
        fallbacks = {
            'troubleshooting': (
                "I couldn't find specific information about your technical issue. "
                "Please provide more details about the problem you're experiencing, "
                "including any error messages or steps to reproduce the issue."
            ),
            'feature_request': (
                "Thank you for your feature request suggestion. "
                "While I don't have specific information about this feature in our current system, "
                "I recommend submitting it through our official feature request channel."
            ),
            'bug_report': (
                "Thank you for reporting this potential bug. "
                "Please provide additional details such as the exact steps to reproduce, "
                "your system information, and any error messages you're seeing."
            ),
            'general_inquiry': (
                "I couldn't find specific information to answer your question. "
                "Please try rephrasing your question or provide more context about what you're looking for."
            )
        }

        return fallbacks.get(intent, fallbacks['general_inquiry'])