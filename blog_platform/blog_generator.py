"""Blog generation using OpenRouter API."""

import json
import logging
from typing import Dict, Optional, List
import requests

logger = logging.getLogger(__name__)


class BlogGenerator:
    """Generate blog posts using OpenRouter API."""
    
    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def generate_blog(
        self,
        topic: str,
        topic_description: str,
        keywords: list,
        word_count_min: int = 500,
        word_count_max: int = 800
    ) -> Optional[Dict[str, str]]:
        """
        Generate a blog post for a specific topic.
        
        Returns:
            {"title": str, "body": str} or None on error
        """
        logger.info(f"[GENERATE_BLOG] Starting for topic: {topic}")
        logger.info(f"[GENERATE_BLOG] Using model: {self.model}")
        
        system_prompt = f"""You are a creative technical content writer for a cutting-edge AI and LLM tech blog.

Write an ORIGINAL blog post about: {topic}

Description: {topic_description}

Requirements:
- Title: max 10 words, MUST be CREATIVE and UNIQUE - use compelling language, avoid generic phrases
  * NO titles like "Guide to...", "Understanding...", "Exploring...", "Best Practices for..."
  * Use active, specific, interesting angles: challenges, paradoxes, unexpected insights
  * VERY IMPORTANT: Make each title distinct and memorable - never repeat similar patterns
  * Examples of GOOD titles: "Why Your LLM Router Keeps Failing (And What Actually Works)", "The Hidden Cost of Model Selection"
  * NO brand mentions, NO common overused phrases
- Body: {word_count_min}-{word_count_max} words, insightful and actionable
- Focus on: The problem, innovative solutions, practical impact
- Include: Real-world examples, specific metrics, unexpected insights
- Optional: Briefly mention LLM routing, cost optimization, performance, or reliability if relevant
- Use direct, energetic technical language - make it engaging
- Target CTOs and AI engineers who value originality

Return ONLY valid JSON (no markdown):
{{
  "title": "Your creative, unique title here",
  "body": "Your insightful blog post here..."
}}"""
        
        user_prompt = f"""Create a CREATIVE, ORIGINAL technical blog post for CTOs and AI engineers about:
Topic: {topic}
Key points: {', '.join(keywords)}

CRITICAL TITLE REQUIREMENTS:
- Your title MUST be CREATIVE and NOT repeated
- Avoid generic openers: "Guide", "Understanding", "Exploring", "Best Practices", "How to"
- Use INTERESTING angles: problems solved, surprising facts, technical depth, real impact
- Make it UNIQUE and memorable - as if no one has written this exact title before

BLOG REQUIREMENTS:
1. Hook the reader immediately with a fresh perspective on {topic}
2. Explain why this matters (avoid obvious statements)
3. Present actionable insights and real-world solutions
4. Include specific data, tradeoffs, or practical examples
5. Sound like expert advice, not a marketing piece
6. Title is brand-agnostic, solution-focused
7. Each sentence should feel necessary and valuable

Optionally, if naturally relevant, mention LLM routing, cost optimization, performance, or reliability strategies.

Return valid JSON with CREATIVE title and engaging body fields only."""

        try:
            logger.info(f"[GEN] Calling OpenRouter API for topic: {topic}")
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.8,
                    "max_tokens": 2000
                },
                timeout=120
            )
            
            logger.info(f"[GEN] API Response Status: {response.status_code}")
            response.raise_for_status()
            data = response.json()
            raw_response = data["choices"][0]["message"]["content"]
            logger.info(f"[GEN] Raw response length: {len(raw_response)}")
            
            # Parse JSON response
            cleaned = raw_response.replace("```json", "").replace("```", "").strip()
            start = cleaned.find('{')
            end = cleaned.rfind('}')
            
            logger.info(f"[GEN] JSON start={start}, end={end}")
            
            if start == -1 or end == -1:
                logger.error(f"[GEN] Invalid JSON format in response: {raw_response[:200]}")
                return None
            
            parsed = json.loads(cleaned[start:end+1])
            logger.info(f"[GEN] JSON parsed successfully")
            
            # Validate fields
            if "title" not in parsed or "body" not in parsed:
                logger.error(f"[GEN] Missing title or body in response: {parsed}")
                return None
            
            logger.info(f"[GEN] SUCCESS - Blog generated: {parsed['title'][:50]}")
            return {
                "title": parsed["title"].strip(),
                "body": parsed["body"].strip()
            }
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"API HTTP error: {e.response.status_code} - {e.response.reason}")
            logger.error(f"Response body: {e.response.text[:500]}")
            if e.response.status_code == 429:
                logger.error("Rate limit exceeded (429)")
            elif e.response.status_code == 401:
                logger.error("Unauthorized - check API key")
            elif e.response.status_code == 400:
                logger.error("Bad request - check model name and parameters")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            logger.error(f"Raw response was: {raw_response[:300] if 'raw_response' in locals() else 'N/A'}")
            return None
        except Exception as e:
            logger.error(f"Blog generation error: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    def generate_blog_from_article(
        self,
        article: Dict,
        word_count_min: int = 500,
        word_count_max: int = 800
    ) -> Optional[Dict[str, str]]:
        """
        Generate a blog post based on a scraped article.
        
        Args:
            article: Article dict with title, content, source, categories, etc.
            word_count_min: Minimum words for blog body
            word_count_max: Maximum words for blog body
        
        Returns:
            {"title": str, "body": str} or None on error
        """
        article_title = article.get("title", "Unknown")
        article_content = article.get("content", article.get("contentSnippet", ""))[:2000]
        article_source = article.get("source", "Unknown")
        categories = article.get("categories", [])
        
        logger.info(f"[FROM_ARTICLE] Generating blog from: {article_title[:50]}")
        
        system_prompt = f"""You are an exceptionally creative technical writer for an innovative AI and LLM blog.

Your task is to write a UNIQUE, ORIGINAL blog post inspired by (but not summarizing) an article from {article_source}.

Requirements:
- Write an ORIGINAL, CREATIVE blog post that EXPANDS on the article's themes
- Title: max 10 words, MUST be CREATIVE, UNIQUE, and attention-grabbing
  * NEVER use generic titles: "Guide to...", "Understanding...", "Exploring...", "How to...", "Best Practices"
  * Use compelling angles: unexpected insights, technical depth, real problems solved, surprising connections
  * Make it MEMORABLE and DIFFERENT - the kind of title that stands out in a feed
  * NO brand mentions - focus on technical value and insights
- Body: {word_count_min}-{word_count_max} words, deeply insightful
- Style: Engaging, authoritative, direct - make every word count
- Include: Real-world impact, specific examples, technical nuance, actionable insights
- NO marketing speak or brand promotions - pure technical excellence
- This should feel like expert perspective, not a summary
- Target audience: CTOs and AI engineers who value original thinking"""

        user_prompt = f"""Based on this article, write an ORIGINAL, CREATIVE technical blog post:

Article Title: {article_title}
Source: {article_source}
Categories: {', '.join(categories)}

Article Content:
{article_content}

IMPORTANT:
1. Create a UNIQUE, CREATIVE title that stands out - NOT a variation of the article title
2. Avoid generic title patterns like "Guide", "Understanding", "How to", "Best Practices"
3. Make the title MEMORABLE and DIFFERENT - something that would catch a reader's eye
4. Expand on the article with original insights, examples, and analysis
5. Provide perspective that goes beyond what the article says
6. Write from a place of deep expertise - assume the reader is technically savvy
7. Every sentence should add value and insight

Return ONLY valid JSON (no markdown):
{{
  "title": "Your creative, unique, memorable title here",
  "body": "Your original, insightful blog post here..."
}}"""

        try:
            logger.info(f"[FROM_ARTICLE] Calling OpenRouter API")
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.85,
                    "max_tokens": 2500
                },
                timeout=120
            )
            
            logger.info(f"[FROM_ARTICLE] API Response Status: {response.status_code}")
            response.raise_for_status()
            data = response.json()
            raw_response = data["choices"][0]["message"]["content"]
            
            # Parse JSON response
            cleaned = raw_response.replace("```json", "").replace("```", "").strip()
            start = cleaned.find('{')
            end = cleaned.rfind('}')
            
            if start == -1 or end == -1:
                logger.error(f"[FROM_ARTICLE] Invalid JSON format in response: {raw_response[:200]}")
                return None
            
            parsed = json.loads(cleaned[start:end+1])
            
            # Validate fields
            if "title" not in parsed or "body" not in parsed:
                logger.error(f"[FROM_ARTICLE] Missing title or body in response: {parsed}")
                return None
            
            logger.info(f"[FROM_ARTICLE] SUCCESS - Blog generated: {parsed['title'][:50]}")
            return {
                "title": parsed["title"].strip(),
                "body": parsed["body"].strip(),
                "source_article_id": str(article.get("_id", "")),
                "source_article_title": article_title
            }
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"[FROM_ARTICLE] API HTTP error: {e.response.status_code}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"[FROM_ARTICLE] JSON decode error: {e}")
            return None
        except Exception as e:
            logger.error(f"[FROM_ARTICLE] Error: {type(e).__name__}: {e}")
            return None
    
    def batch_generate(
        self,
        topics: Dict[str, Dict],
        blogs_per_topic: int = 1
    ) -> Dict[str, list]:
        """
        Generate multiple blogs across topics.
        
        Args:
            topics: Dict mapping topic_id -> {name, description, keywords}
            blogs_per_topic: Number of blogs per topic
        
        Returns:
            {topic_id -> [list of generated blogs]}
        """
        result = {}
        
        for topic_id, topic_info in topics.items():
            result[topic_id] = []
            logger.info(f"Generating {blogs_per_topic} blogs for topic: {topic_id}")
            
            for i in range(blogs_per_topic):
                blog = self.generate_blog(
                    topic=topic_info.get("name", topic_id),
                    topic_description=topic_info.get("description", ""),
                    keywords=topic_info.get("keywords", [])
                )
                
                if blog:
                    result[topic_id].append(blog)
                    logger.info(f"✓ Generated blog {i+1}/{blogs_per_topic} for {topic_id}")
                else:
                    logger.error(f"✗ Failed to generate blog {i+1}/{blogs_per_topic} for {topic_id}")
        
        return result
    
    def generate_blog_variants(
        self,
        blog_content: str,
        blog_title: str,
        num_variants: int = 5,
        account_names: Optional[list] = None
    ) -> Optional[list]:
        """
        Generate multiple variants of a blog post with different titles and angles.
        
        Args:
            blog_content: The original blog content
            blog_title: The original blog title
            num_variants: Number of variants to generate (default: 5)
            account_names: Optional list of account names to tailor variants
        
        Returns:
            List of variant dicts with different titles and slightly modified content
        """
        logger.info(f"[VARIANTS] Generating {num_variants} variants of: {blog_title[:50]}")
        
        system_prompt = """You are a creative technical content strategist who creates multiple unique angles on the same core technical insight.

Your task is to generate variant titles and slight perspective shifts on an existing blog post.
Each variant should:
- Have a COMPLETELY DIFFERENT, UNIQUE title (max 10 words)
- Preserve the core technical content (90% same body, 10% angle shift)
- Use a different hook/framing to appeal to the same audience
- Pick one aspect of the blog to emphasize differently

IMPORTANT:
- NO title should be similar to any other
- Each title must be creative and stand out
- Vary the tone slightly: one more urgent, one more analytical, one more practical, one more speculative, one more strategic
- Keep the technical depth and accuracy
- Body can be reframed with 1-2 sentences changed at the start/end to match the new title angle

Return ONLY valid JSON array (no markdown):
[
  {
    "title": "Variant 1 title",
    "body": "Variant 1 body with modified framing"
  },
  ...
]"""
        
        user_prompt = f"""Create {num_variants} unique variants of this blog post.

ORIGINAL TITLE: {blog_title}

ORIGINAL BODY:
{blog_content}

Generate {num_variants} complete variants with:
1. COMPLETELY DIFFERENT, UNIQUE titles (each one fresh and different from the others)
2. Same core technical content but with different framing/angles
3. Different tone for each: vary between urgent, analytical, practical, speculative, strategic

Variant perspectives:
1. Risk/Problem angle: Emphasize what goes wrong if you don't do this
2. Opportunity angle: Focus on competitive advantage
3. Practical/How-to angle: Emphasize implementation and steps
4. Strategic/Business angle: Focus on business value and ROI
5. Technical/Deep dive angle: Emphasize technical depth and architecture

Each title MUST be unique and creative - no similar patterns to other titles.
Return valid JSON array ONLY."""
        
        try:
            logger.info(f"[VARIANTS] Calling OpenRouter API to generate {num_variants} variants")
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.85,
                    "max_tokens": 4000
                },
                timeout=180
            )
            
            logger.info(f"[VARIANTS] API Response Status: {response.status_code}")
            response.raise_for_status()
            data = response.json()
            raw_response = data["choices"][0]["message"]["content"]
            
            # Parse JSON array response
            cleaned = raw_response.replace("```json", "").replace("```", "").strip()
            start = cleaned.find('[')
            end = cleaned.rfind(']')
            
            if start == -1 or end == -1:
                logger.error(f"[VARIANTS] Invalid JSON format in response")
                return None
            
            variants = json.loads(cleaned[start:end+1])
            logger.info(f"[VARIANTS] SUCCESS - Generated {len(variants)} variants")
            
            # Validate all variants have required fields
            valid_variants = []
            for i, variant in enumerate(variants, 1):
                if "title" in variant and "body" in variant:
                    valid_variants.append({
                        "title": variant["title"].strip(),
                        "body": variant["body"].strip()
                    })
                    logger.info(f"[VARIANTS] Variant {i}: {variant['title'][:50]}")
            
            return valid_variants if valid_variants else None
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"[VARIANTS] API HTTP error: {e.response.status_code}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"[VARIANTS] JSON decode error: {e}")
            return None
        except Exception as e:
            logger.error(f"[VARIANTS] Error: {type(e).__name__}: {e}")
            return None
