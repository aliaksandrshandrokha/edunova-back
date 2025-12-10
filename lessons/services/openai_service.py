"""
OpenAI service for generating lesson content.
"""
import os
import json
import logging
from typing import Dict, List, Optional, Any
from openai import OpenAI
from django.conf import settings

logger = logging.getLogger(__name__)

# Lazy-load OpenAI client to avoid initialization errors
_client = None

def get_openai_client():
    """Get or create OpenAI client instance (lazy initialization)."""
    global _client
    if _client is None:
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            try:
                _client = OpenAI(api_key=api_key)
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                _client = False  # Mark as failed
        else:
            logger.warning("OPENAI_API_KEY not found in environment variables. OpenAI features will not work.")
            _client = False  # Mark as not configured
    return _client if _client is not False else None


def generate_lesson_content(
    topic: str,
    subject: str,
    grade_level: str,
    duration_minutes: int
) -> Dict[str, Any]:
    """
    Generate lesson content using OpenAI API.
    
    Args:
        topic: The lesson topic (e.g., "Photosynthesis")
        subject: The subject area (e.g., "Biology")
        grade_level: The grade level (e.g., "Grade 8")
        duration_minutes: Duration of the lesson in minutes
    
    Returns:
        Dictionary containing:
        - description: str (2-3 paragraphs)
        - activities: List[str] (3-6 activities)
        - questions: List[str] (4-8 questions)
        - summary: str (2-3 sentences)
    
    Raises:
        ValueError: If OpenAI API key is not configured
        Exception: If OpenAI API call fails
    """
    client = get_openai_client()
    if not client:
        raise ValueError(
            "OpenAI API key not configured. Please set OPENAI_API_KEY in your environment variables."
        )
    
    # Construct the prompt
    prompt = f"""You are an expert educational content creator. Generate comprehensive lesson content for the following:

Topic: {topic}
Subject: {subject}
Grade Level: {grade_level}
Duration: {duration_minutes} minutes

Please provide:
1. Description: Write 2-3 paragraphs explaining the lesson topic in an engaging, age-appropriate way for {grade_level} students studying {subject}.

2. Activities: Provide 3-6 classroom activities (as a numbered list) that students can do to learn about {topic}. Each activity should be practical and suitable for a {duration_minutes}-minute lesson.

3. Questions: Provide 4-8 practice questions (as a numbered list) that test understanding of {topic}. Include a mix of comprehension and application questions.

4. Summary: Write a 2-3 sentence conclusion that summarizes the key takeaways from this lesson.

Format your response as a JSON object with the following structure:
{{
    "description": "2-3 paragraphs of text",
    "activities": ["Activity 1", "Activity 2", ...],
    "questions": ["Question 1", "Question 2", ...],
    "summary": "2-3 sentence summary"
}}

Return ONLY the JSON object, no additional text or markdown formatting."""

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert educational content creator. Always respond with valid JSON only, no markdown formatting."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=2000,
            response_format={"type": "json_object"}  # Request JSON response
        )
        
        # Extract the content from the response
        content = response.choices[0].message.content.strip()
        
        # Remove markdown code blocks if present
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        # Parse JSON response
        try:
            result = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI response as JSON: {e}")
            logger.error(f"Response content: {content}")
            raise ValueError(f"Invalid JSON response from OpenAI: {str(e)}")
        
        # Validate and structure the response
        return {
            "description": result.get("description", ""),
            "activities": result.get("activities", []),
            "questions": result.get("questions", []),
            "summary": result.get("summary", "")
        }
        
    except Exception as e:
        logger.error(f"OpenAI API error: {str(e)}")
        raise Exception(f"Failed to generate lesson content: {str(e)}")

