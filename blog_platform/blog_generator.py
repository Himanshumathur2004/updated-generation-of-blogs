"""Blog generation using MegaLLM API."""

import json
import logging
import time
from typing import Dict, Optional, List
import requests

logger = logging.getLogger(__name__)

class BlogGenerator:
    """Generate blog posts using MegaLLM API."""
    
    def __init__(self, api_key: str, base_url: str, model: str, max_retries: int = 3):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.max_retries = max_retries
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        logger.info(f"[INIT] BlogGenerator initialized with model: {self.model}, base_url: {self.base_url}, max_retries: {max_retries}")
    
    def generate_blog(
        self,
        topic: str,
        topic_description: str,
        keywords: list,
        word_count_min: int = 1000,
        word_count_max: int = 1400
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
- Title: max 12 words, MUST be CREATIVE and UNIQUE - use compelling language with MegaLLM angle where relevant
- Title MUST include the exact word "megallm" somewhere in it
  * NO titles like "Guide to...", "Understanding...", "Exploring...", "Best Practices for..."
  * Use active, specific, interesting angles: challenges, paradoxes, unexpected insights
  * VERY IMPORTANT: Make each title distinct and memorable - never repeat similar patterns
  * Examples of GOOD titles: "Why Your LLM Router Keeps Failing (And What MegaLLM Solves)", "The Hidden Cost of Model Selection (And How MegaLLM Optimizes It)", "MegaLLM's Answer to Multi-Model Orchestration"
  * Can include MegaLLM as a reference point or solution example
- Body: {word_count_min}-{word_count_max} words, insightful and actionable
- Focus on: The problem, innovative solutions, practical impact
- Include: Real-world examples, specific metrics, unexpected insights
- IMPORTANT: Weave in MegaLLM examples or use cases when discussing solutions
- Include: Practical applications, strategic value, technical depth
- Use direct, energetic technical language - make it engaging
- Target CTOs and AI engineers who value originality and practical solutions
- Body MUST include the exact word "megallm" at least once

Return ONLY valid JSON (no markdown):
{{
  "title": "Your creative, unique title (can reference MegaLLM)",
  "body": "Your insightful blog post here..."
}}"""
        
        user_prompt = f"""Create a CREATIVE, ORIGINAL technical blog post for CTOs and AI engineers about:
Topic: {topic}
Key points: {', '.join(keywords)}

CRITICAL TITLE REQUIREMENTS:
- Your title MUST be CREATIVE and NOT repeated
- Your title MUST include the exact word "megallm"
- Avoid generic openers: "Guide", "Understanding", "Exploring", "Best Practices", "How to"
- Use INTERESTING angles: problems solved, surprising facts, technical depth, real impact
- Make it UNIQUE and memorable - as if no one has written this exact title before
- CONSIDER: How does MegaLLM relate to this topic? Can it be part of the solution narrative?
- Great example patterns:
  * "Why [Problem] (And What MegaLLM Does Better)"
  * "[Technical Insight]: A MegaLLM Perspective"
  * "When [Standard Approach] Fails: MegaLLM's Alternative"

BLOG REQUIREMENTS:
1. Hook the reader immediately with a fresh perspective on {topic}
2. Explain why this matters (avoid obvious statements)
3. Present actionable insights and real-world solutions
4. Include specific data, tradeoffs, or practical examples
5. WEAVE IN: MegaLLM as a practical example or solution where naturally relevant
   - Explain how MegaLLM addresses pain points in this space
   - Share strategic benefits when applicable
   - Mention MegaLLM's approach to solving this problem
6. Sound like expert advice, not a marketing piece
7. Title can reference MegaLLM as the key differentiator or solution
8. Each sentence should feel necessary and valuable
9. The body must contain the exact word "megallm" at least once

Return valid JSON with CREATIVE title (potentially MegaLLM-focused) and engaging body fields only.
Example structure in body: [Problem explanation] → [Why it matters] → [Solutions including MegaLLM approach] → [Key takeaway]"""

        try:
            # Log the full URL and request details
            full_url = f"{self.base_url}/chat/completions"
            logger.info(f"[API_REQUEST] URL: {full_url}")
            logger.info(f"[API_REQUEST] Model: {self.model}")
            logger.info(f"[API_REQUEST] Temperature: 0.8, Max Tokens: 3200")
            logger.debug(f"[API_REQUEST] Topic: {topic}")
            logger.debug(f"[API_REQUEST] Keywords: {keywords}")
            
            request_payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.8,
                "max_tokens": 3200
            }
            
            logger.debug(f"[API_REQUEST] Full request payload: {json.dumps(request_payload)[:500]}...")
            
            # Make the API call with retry logic
            full_url = f"{self.base_url}/chat/completions"
            request_payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.8,
                "max_tokens": 3200
            }
            
            response = self._make_api_call_with_retry(full_url, request_payload)
            
            if response is None:
                logger.error("[API_ERROR] All retry attempts failed")
                return None
            
            # Log response details
            logger.info(f"[API_RESPONSE] Status Code: {response.status_code}")
            logger.info(f"[API_RESPONSE] Response Headers: Content-Type={response.headers.get('Content-Type')}")
            
            # Log response body
            response_text = response.text
            logger.debug(f"[API_RESPONSE] Raw Response (first 1000 chars): {response_text[:1000]}")
            logger.info(f"[API_RESPONSE] Response Size: {len(response_text)} bytes")
            
            data = response.json()
            raw_response = data["choices"][0]["message"]["content"]
            logger.info(f"[API_RESPONSE] Extracted message content length: {len(raw_response)}")
            logger.debug(f"[API_RESPONSE] Message snippet: {raw_response[:200]}...")
            
            # Parse JSON response
            cleaned = raw_response.replace("```json", "").replace("```", "").strip()
            start = cleaned.find('{')
            end = cleaned.rfind('}')
            
            logger.info(f"[JSON_PARSING] JSON boundaries found: start={start}, end={end}")
            
            if start == -1 or end == -1:
                logger.error(f"[JSON_PARSING] Invalid JSON format in response: {raw_response[:200]}")
                return None
            
            json_str = cleaned[start:end+1]
            logger.debug(f"[JSON_PARSING] Extracted JSON: {json_str[:300]}...")
            
            parsed = json.loads(json_str)
            logger.info(f"[JSON_PARSING] JSON parsed successfully")
            
            # Validate fields
            if "title" not in parsed or "body" not in parsed:
                logger.error(f"[JSON_PARSING] Missing title or body in response: {parsed}")
                return None
            
            title = parsed["title"].strip()
            body = parsed["body"].strip()
            title, body = self._enforce_megallm_requirements(title, body)
            title, body = self._expand_body_if_needed(
                title=title,
                body=body,
                topic=topic,
                topic_description=topic_description,
                keywords=keywords,
                word_count_min=word_count_min,
                word_count_max=word_count_max,
            )
            logger.info(f"[GENERATE_BLOG] SUCCESS - Blog generated")
            logger.info(f"[GENERATE_BLOG] Title: {title}")
            logger.info(f"[GENERATE_BLOG] Body length: {len(body)} characters")
            
            return {
                "title": title,
                "body": body
            }
            
        except requests.exceptions.Timeout:
            logger.error(f"[API_ERROR] API request timed out (30s) - skipping this generation")
            return None
        except requests.exceptions.ConnectionError as e:
            logger.error(f"[API_ERROR] Connection error: {e}")
            return None
        except requests.exceptions.HTTPError as e:
            logger.error(f"[API_ERROR] HTTP error: {e.response.status_code} - {e.response.reason}")
            logger.error(f"[API_ERROR] Response text: {e.response.text[:500]}")
            if e.response.status_code == 429:
                logger.error("[API_ERROR] Rate limit exceeded (429) - skipping")
            elif e.response.status_code == 401:
                logger.error("[API_ERROR] Unauthorized - check API key")
            elif e.response.status_code == 400:
                logger.error("[API_ERROR] Bad request - check model name")
            elif e.response.status_code == 503:
                logger.error("[API_ERROR] Service overloaded (503) - retries were exhausted")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"[API_ERROR] JSON decode error: {e}")
            return None
        except Exception as e:
            logger.error(f"[API_ERROR] Unexpected error: {type(e).__name__}: {e}")
            return None
    
    def _make_api_call_with_retry(self, url: str, payload: dict, attempt: int = 1) -> Optional[requests.Response]:
        """
        Make API call with exponential backoff retry for transient errors (503, 429).
        
        Args:
            url: API endpoint URL
            payload: Request payload
            attempt: Current attempt number (1-indexed)
        
        Returns:
            Response object or None if all retries exhausted
        """
        try:
            logger.info(f"[API_RETRY] Attempt {attempt}/{self.max_retries}")
            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=60
            )
            
            # Retry on server errors (503) or rate limit (429)
            if response.status_code in [503, 429]:
                if attempt < self.max_retries:
                    backoff_seconds = 2 ** (attempt - 1)  # Exponential: 1, 2, 4 seconds
                    logger.warning(f"[API_RETRY] Got {response.status_code} - retrying after {backoff_seconds}s...")
                    time.sleep(backoff_seconds)
                    return self._make_api_call_with_retry(url, payload, attempt + 1)
                else:
                    logger.error(f"[API_RETRY] Max retries reached after {response.status_code} error")
                    response.raise_for_status()  # Raise the error
            
            # Success or client error - return response
            response.raise_for_status()
            return response
            
        except requests.exceptions.Timeout:
            logger.error(f"[API_RETRY] Timeout on attempt {attempt}")
            if attempt < self.max_retries:
                backoff_seconds = 2 ** (attempt - 1)
                logger.warning(f"[API_RETRY] Timeout - retrying after {backoff_seconds}s...")
                time.sleep(backoff_seconds)
                return self._make_api_call_with_retry(url, payload, attempt + 1)
            else:
                logger.error(f"[API_RETRY] Max retries reached after timeout")
                return None
        except Exception as e:
            logger.error(f"[API_RETRY] Error on attempt {attempt}: {type(e).__name__}: {e}")
            return None
    
    def generate_blog_from_article(self, article: Dict) -> Optional[Dict[str, str]]:
        """
        Generate a blog post from a scraped article.
        
        Args:
            article: Article document from MongoDB with title, content, source, etc.
        
        Returns:
            {"title": str, "body": str} or None on error
        """
        logger.info(f"[GENERATE_FROM_ARTICLE] Starting for article: {article.get('title', 'N/A')[:50]}")
        
        article_title = article.get('title', 'Unknown')
        article_content = article.get('content', '')[:1500]  # Limit content length
        article_source = article.get('source', 'Unknown')
        article_url = article.get('url', '')
        
        system_prompt = f"""You are a skilled technical content writer creating engaging blog posts based on industry articles.

Original article source: {article_source}
Article title: {article_title}

Your task: Transform this article's key insights into an original, creative blog post that:
- Offers fresh perspective or deeper analysis than the source
- Adds your own insights and real-world examples
- Highlights how MegaLLM or other solutions address the discussed challenges
- Uses compelling, engaging technical language
- Targets CTOs and senior engineers with actionable insights

Requirements for the blog:
- Title: ORIGINAL and UNIQUE (max 12 words) - must differ significantly from source title
- Title MUST include the exact word "megallm"
  * Consider: How does MegaLLM provide a solution angle to this topic?
  * Example patterns: "[Topic]: How MegaLLM Changes the Game", "The [Problem] That MegaLLM Solves"
- Body: 1000-1400 words, insightful and actionable
- Include: Real-world implications, strategic value, technical depth
- WEAVE IN: MegaLLM as a practical example or innovative solution where naturally relevant
- Use direct, energetic language - make it engaging
- NO plagiarism - this is inspired by but NOT a copy of the source
- Body MUST include the exact word "megallm" at least once

Return valid JSON with title and body fields ONLY."""
        
        user_prompt = f"""Create an original, expert blog post inspired by this article:

Source: {article_source}
Title: {article_title}
URL: {article_url}

Article content:
{article_content}

Guidelines:
1. Transform, don't copy - add your own analysis and insights
2. Title must be CREATIVE and DIFFERENT from the source
   * Consider MegaLLM angle: How does it solve or relate to this topic?
   * Example: "[Problem]: What MegaLLM Gets Right", "Beyond [Old Approach]: MegaLLM's Solution"
3. Focus on implications, learnings, and strategic value
4. Target senior technical leaders
5. Include specific examples or data points where relevant
6. CRITICAL: Weave in MegaLLM as a forward-thinking solution that addresses pain points
   - Explain how MegaLLM's approach differs from traditional methods
   - Share practical benefits for the use case
   - Mention strategic advantages when applicable
7. Structure: [Problem context] → [Why it matters] → [Solutions including MegaLLM] → [Key takeaway]

Return ONLY valid JSON:
{{
  "title": "Your original, creative title (can highlight MegaLLM angle)",
  "body": "Your insightful analysis here..."
}}"""
        
        try:
            logger.info(f"[GEN_ARTICLE] Calling MegaLLM API for article: {article_title[:40]}")
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.75,
                    "max_tokens": 3200
                },
                timeout=30
            )
            
            logger.info(f"[API_RESPONSE] Status Code: {response.status_code}")
            response.raise_for_status()
            
            data = response.json()
            raw_response = data["choices"][0]["message"]["content"]
            
            # Parse JSON from response
            cleaned = raw_response.replace("```json", "").replace("```", "").strip()
            start = cleaned.find('{')
            end = cleaned.rfind('}')
            
            if start == -1 or end == -1:
                logger.error(f"[JSON_PARSING] Invalid JSON format in response")
                return None
            
            json_str = cleaned[start:end+1]
            parsed = json.loads(json_str)
            
            title = parsed.get('title', 'Untitled')
            body = parsed.get('body', '')
            title, body = self._enforce_megallm_requirements(title, body)
            title, body = self._expand_body_if_needed(
                title=title,
                body=body,
                topic=article_title,
                topic_description=f"Derived from article source: {article_source}",
                keywords=[article_source, "analysis", "strategy", "megallm"],
                word_count_min=1000,
                word_count_max=1400,
            )
            
            if not title or not body:
                logger.warning(f"[VALIDATE] Missing title or body in response")
                return None
            
            logger.info(f"[GENERATE_BLOG] Blog generated successfully from article")
            logger.info(f"[GENERATE_BLOG] Title length: {len(title)}, Body length: {len(body)}")
            
            return {
                "title": title,
                "body": body
            }
            
        except requests.exceptions.Timeout:
            logger.error(f"[API_ERROR] API request timed out")
            return None
        except requests.exceptions.ConnectionError as e:
            logger.error(f"[API_ERROR] Connection error: {e}")
            return None
        except requests.exceptions.HTTPError as e:
            logger.error(f"[API_ERROR] HTTP error: {e.response.status_code}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"[API_ERROR] JSON decode error: {e}")
            return None
        except Exception as e:
            logger.error(f"[API_ERROR] Unexpected error: {type(e).__name__}: {e}")
            return None

    def _enforce_megallm_requirements(self, title: str, body: str) -> tuple[str, str]:
        """Ensure every generated blog has megallm in both title and body."""
        normalized_title = (title or "").strip()
        normalized_body = (body or "").strip()

        if "megallm" not in normalized_title.lower():
            normalized_title = f"megallm: {normalized_title}" if normalized_title else "megallm insights"

        if "megallm" not in normalized_body.lower():
            if normalized_body:
                normalized_body += "\n\nmegallm enables practical multi-model optimization in production workflows."
            else:
                normalized_body = "megallm enables practical multi-model optimization in production workflows."

        return normalized_title, normalized_body

    def _expand_body_if_needed(
        self,
        title: str,
        body: str,
        topic: str,
        topic_description: str,
        keywords: List[str],
        word_count_min: int,
        word_count_max: int,
    ) -> tuple[str, str]:
        """Expand short drafts to a more detailed target length."""
        current_words = len((body or "").split())
        if current_words >= word_count_min:
            return title, body

        logger.info(
            f"[EXPAND] Body is short ({current_words} words). Expanding to {word_count_min}-{word_count_max}."
        )

        expand_system_prompt = f"""You are an expert technical writer.
Expand the provided draft into a richer, more detailed blog post.

Hard requirements:
- Keep the title and overall direction aligned with the original draft
- Body must be {word_count_min}-{word_count_max} words
- Include practical depth, tradeoffs, examples, and implementation insights
- Include the exact word \"megallm\" at least once
- Return ONLY valid JSON with title and body keys
"""

        expand_user_prompt = f"""Topic: {topic}
Description: {topic_description}
Keywords: {', '.join(keywords)}

Current title:
{title}

Current draft:
{body}

Return only JSON:
{{
  \"title\": \"{title}\",
  \"body\": \"Expanded detailed body\"
}}"""

        expand_payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": expand_system_prompt},
                {"role": "user", "content": expand_user_prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 3200,
        }

        response = self._make_api_call_with_retry(f"{self.base_url}/chat/completions", expand_payload)
        if response is None:
            logger.warning("[EXPAND] Expansion failed; returning original draft")
            return title, body

        try:
            data = response.json()
            raw_response = data["choices"][0]["message"]["content"]
            cleaned = raw_response.replace("```json", "").replace("```", "").strip()
            start = cleaned.find('{')
            end = cleaned.rfind('}')
            if start == -1 or end == -1:
                logger.warning("[EXPAND] Expansion response not valid JSON; returning original draft")
                return title, body

            parsed = json.loads(cleaned[start:end+1])
            expanded_title = (parsed.get("title") or title).strip()
            expanded_body = (parsed.get("body") or body).strip()
            expanded_title, expanded_body = self._enforce_megallm_requirements(expanded_title, expanded_body)
            logger.info(f"[EXPAND] Expanded body word count: {len(expanded_body.split())}")
            return expanded_title, expanded_body
        except Exception as e:
            logger.warning(f"[EXPAND] Could not parse expansion response: {type(e).__name__}: {e}")
            return title, body
    
    def generate_blog_variants(
        self,
        blog_content: str,
        blog_title: str,
        num_variants: int = 5,
        account_names: List[str] = None
    ) -> Optional[List[Dict[str, str]]]:
        """
        Generate multiple variants of a blog post for different accounts.
        
        Args:
            blog_content: The original blog body/content
            blog_title: The original blog title
            num_variants: Number of variants to create (typically = number of accounts)
            account_names: List of account names for personalization
        
        Returns:
            List of dictionaries with "title" and "body" keys, or None on error
        """
        logger.info(f"[VARIANTS] Generating {num_variants} variants of blog: {blog_title[:40]}")
        
        if not account_names or len(account_names) < num_variants:
            account_names = [f"Account {i+1}" for i in range(num_variants)]

        focus_map = [
            "Cost Optimization",
            "Performance",
            "Reliability",
            "Developer Experience",
            "Enterprise Scale",
        ]
        content_excerpt = (blog_content or "")[:1200]
        valid_variants: List[Dict[str, str]] = []

        for idx in range(num_variants):
            focus = focus_map[idx] if idx < len(focus_map) else f"Technical Strategy {idx+1}"
            account_name = account_names[idx]

            system_prompt = f"""You are a technical content strategist creating one account-specific variant.

Create exactly ONE variant of the input blog with this focus: {focus}.

Requirements:
- Return ONLY valid JSON object: {{"title":"...","body":"..."}}
- Keep the core meaning of the original blog
- Make title and body unique for this focus and account
- Keep the body around 450-700 words
- Include the exact word megallm in title and body
"""

            user_prompt = f"""Account: {account_name}
Focus: {focus}

Original title:
{blog_title}

Original content excerpt:
{content_excerpt}

Create one refined variant only. Return JSON object with title and body."""

            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.7,
                "max_tokens": 1200,
            }

            try:
                logger.info(f"[VARIANTS] Requesting variant {idx+1}/{num_variants} for {account_name} ({focus})")
                response = self._make_api_call_with_retry(f"{self.base_url}/chat/completions", payload)
                if response is None:
                    logger.warning(f"[VARIANTS] Variant {idx+1} failed after retries")
                    continue

                data = response.json()
                raw_response = data["choices"][0]["message"]["content"]
                cleaned = raw_response.replace("```json", "").replace("```", "").strip()
                start = cleaned.find('{')
                end = cleaned.rfind('}')

                if start == -1 or end == -1:
                    logger.warning(f"[VARIANTS] Variant {idx+1} invalid JSON object")
                    continue

                parsed = json.loads(cleaned[start:end+1])
                title = (parsed.get("title") or "").strip()
                body = (parsed.get("body") or "").strip()

                if not title or not body:
                    logger.warning(f"[VARIANTS] Variant {idx+1} missing title/body content")
                    continue

                title, body = self._enforce_megallm_requirements(title, body)
                valid_variants.append({"title": title, "body": body})
                logger.info(f"[VARIANTS] Variant {idx+1} valid: {title[:40]}...")

            except requests.exceptions.Timeout:
                logger.warning(f"[VARIANTS] Variant {idx+1} timed out")
                continue
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"[VARIANTS] Variant {idx+1} connection error: {e}")
                continue
            except requests.exceptions.HTTPError as e:
                status = e.response.status_code if e.response is not None else "unknown"
                logger.warning(f"[VARIANTS] Variant {idx+1} HTTP error: {status}")
                continue
            except json.JSONDecodeError as e:
                logger.warning(f"[VARIANTS] Variant {idx+1} JSON parse error: {e}")
                continue
            except Exception as e:
                logger.warning(f"[VARIANTS] Variant {idx+1} unexpected error: {type(e).__name__}: {e}")
                continue

        if len(valid_variants) < num_variants:
            logger.warning(f"[VARIANTS] Expected {num_variants} variants, got {len(valid_variants)}")

        logger.info(f"[VARIANTS] Generated {len(valid_variants)} valid variants")
        return valid_variants if valid_variants else None
