"""
NexAudit — AI Engine
Sends scraped SEO data to OpenAI for optimization analysis.
Requires OPENAI_API_KEY environment variable.
"""

import os
import json
from openai import AsyncOpenAI

# Initialize the async OpenAI client
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You are a senior SEO strategist and e-commerce conversion specialist.
Analyze the provided page metadata and technical issues, then return a JSON object with exactly these fields:

{
    "optimized_title": "A new SEO title under 70 characters, keyword-rich, with brand name",
    "optimized_description": "A new meta description between 150-160 characters, with a compelling CTA",
    "conversion_steps": [
        {
            "step": "Short actionable title for the step",
            "detail": "Detailed explanation (2-3 sentences) with specific data-backed reasoning"
        }
    ],
    "commercial_description": "A full product description (100-150 words) written with commercial intent. Use persuasive copywriting techniques: social proof, urgency, sensory language, and clear value propositions. Format as plain text with paragraph breaks."
}

Requirements:
- optimized_title must be under 70 characters
- optimized_description must be 150-160 characters
- conversion_steps must have exactly 3 items
- commercial_description should be 100-150 words
- All content must be specific to the analyzed page, not generic advice
- Return ONLY valid JSON, no markdown fences or extra text"""


async def generate_ai_analysis(scraped_data: dict, issues: list[dict]) -> dict:
    """
    Send scraped SEO data to GPT-4 for analysis and optimization suggestions.

    Args:
        scraped_data: Dictionary of extracted page metadata
        issues: List of detected SEO issues

    Returns:
        Dictionary with optimized_title, optimized_description,
        conversion_steps, and commercial_description
    """
    user_message = f"""Analyze this e-commerce page and optimize it:

PAGE METADATA:
- URL: {scraped_data.get('url', 'N/A')}
- Title: {scraped_data.get('title', 'MISSING')}
- Meta Description: {scraped_data.get('description', 'MISSING')}
- H1: {scraped_data.get('h1', 'MISSING')}
- H2 tags: {scraped_data.get('h2_tags', [])}
- Images: {scraped_data.get('images_total', 0)} total, {scraped_data.get('images_missing_alt', 0)} missing alt
- Canonical: {scraped_data.get('canonical', 'MISSING')}
- Has Schema: {scraped_data.get('schema_markup', False)}
- Lang: {scraped_data.get('lang_attr', 'MISSING')}

DETECTED ISSUES:
{json.dumps(issues, indent=2)}

Provide your analysis as a JSON object following the system prompt format."""

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.7,
        max_tokens=1200,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content

    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        # Fallback: try to extract JSON from potential markdown fences
        import re
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
        else:
            raise ValueError("AI returned invalid JSON")

    # Validate required fields
    required_fields = ["optimized_title", "optimized_description", "conversion_steps", "commercial_description"]
    for field in required_fields:
        if field not in result:
            raise ValueError(f"AI response missing required field: {field}")

    return result