"""Blog generation using MegaLLM API."""

import json
import logging
import time
import re
import random
import html
from datetime import datetime, timezone
from typing import Dict, Optional, List, Tuple, Any
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

    def _extract_json_object(self, raw_response: str) -> Optional[Dict[str, Any]]:
        """Extract and parse first JSON object from model response."""
        cleaned = (raw_response or "").replace("```json", "").replace("```", "").strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None

        try:
            return json.loads(cleaned[start:end + 1])
        except json.JSONDecodeError:
            return None

    def _sanitize_professional_title(self, title: str, topic: str = "") -> str:
        """Normalize generated titles to a professional, non-promotional style."""
        raw = re.sub(r"\s+", " ", (title or "").strip())
        raw = raw.strip("\"'")

        # Remove clickbait parentheticals such as "(And How ... )".
        cleaned = re.sub(r"\s*\((?:and\s+how|why|what)\b[^)]*\)", "", raw, flags=re.IGNORECASE).strip()

        # Tone down sensational terms.
        replacements = {
            r"\bkilling\b": "slowing",
            r"\btrap\b": "bottleneck",
            r"\bshocking\b": "notable",
            r"\bsecret\b": "approach",
            r"\bultimate\b": "practical",
            r"\bgame[-\s]?changer\b": "improvement",
            r"\brevolutionary\b": "effective",
            r"\bmust[-\s]?have\b": "useful",
        }
        for pattern, replacement in replacements.items():
            cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)

        cleaned = re.sub(r"\s+", " ", cleaned).strip(" -:")

        promo_signals = bool(
            re.search(
                r"\b(?:killing|trap|shocking|secret|ultimate|game[-\s]?changer|revolutionary|must[-\s]?have)\b",
                raw,
                flags=re.IGNORECASE,
            ) or "(" in raw
        )

        if not cleaned or promo_signals:
            fallback_topic = re.sub(r"\s+", " ", (topic or "LLM architecture").strip())
            fallback_topic = re.sub(r"\bmegallm\b", "", fallback_topic, flags=re.IGNORECASE).strip(" -:")
            cleaned = fallback_topic if fallback_topic else "LLM architecture insights"

        words = cleaned.split()
        if len(words) > 12:
            cleaned = " ".join(words[:12]).rstrip(" -:")

        return cleaned

    def _analyze_medium_quality(self, title: str, body: str) -> Dict[str, Any]:
        """Deterministic analyzer stage for readability and structure quality."""
        normalized_body = (body or "").strip()
        normalized_title = (title or "").strip()

        words = re.findall(r"\b\w+\b", normalized_body)
        sentences = [s for s in re.split(r"(?<=[.!?])\s+", normalized_body) if s.strip()]
        paragraphs = [p for p in normalized_body.split("\n\n") if p.strip()]
        heading_count = len(re.findall(r"(?m)^#{1,3}\s", normalized_body))
        bullet_count = len(re.findall(r"(?m)^\s*[-*]\s+", normalized_body))
        question_count = normalized_body.count("?")

        word_count = len(words)
        sentence_count = max(1, len(sentences))
        avg_sentence_len = round(word_count / sentence_count, 2)
        long_paragraphs = sum(1 for p in paragraphs if len(re.findall(r"\b\w+\b", p)) > 120)
        has_hook = len((paragraphs[0] if paragraphs else "")) >= 80
        has_backlink = "https://beta.megallm.io" in normalized_body or "https://megallm.io" in normalized_body
        has_megallm = "megallm" in (normalized_title + " " + normalized_body).lower()
        megallm_mentions = len(re.findall(r"\bmegallm\b", normalized_body, flags=re.IGNORECASE))
        cta_count = len(
            re.findall(
                r"\b(?:book\s+a\s+demo|contact\s+sales|sign\s+up|start\s+(?:a\s+)?free\s+trial|click\s+here|try\s+it\s+today|buy\s+now|subscribe\s+now)\b",
                normalized_body,
                flags=re.IGNORECASE,
            )
        )
        promo_terms = re.findall(
            r"\b(?:best|ultimate|game[-\s]?changer|revolutionary|must[-\s]?have|unmatched|world[-\s]?class|breakthrough)\b",
            normalized_body,
            flags=re.IGNORECASE,
        )
        promo_ratio = round(len(promo_terms) / max(1, word_count), 4)
        has_tradeoffs = bool(
            re.search(
                r"\b(?:trade[-\s]?off|limitation|constraint|downside|risk|caveat)\b",
                normalized_body,
                flags=re.IGNORECASE,
            )
        )

        score = 100
        if word_count < 500:
            score -= 20
        if avg_sentence_len > 28:
            score -= 15
        if long_paragraphs > 2:
            score -= 10
        if heading_count < 3:
            score -= 10
        if bullet_count > 4:
            score -= 8
        if question_count < 1:
            score -= 5
        if not has_hook:
            score -= 10
        if not has_megallm:
            score -= 15
        if not has_backlink:
            score -= 5
        if megallm_mentions > 3:
            score -= 10
        if cta_count > 1:
            score -= 10
        if promo_ratio > 0.02:
            score -= 10
        if not has_tradeoffs:
            score -= 10
        score = max(0, min(100, score))

        recommendations: List[str] = []
        if heading_count < 3:
            recommendations.append("Add clearer section headings for scannability.")
        if bullet_count > 4:
            recommendations.append("Reduce long bullet sections and prefer connected prose.")
        if avg_sentence_len > 28:
            recommendations.append("Shorten long sentences for better readability.")
        if long_paragraphs > 2:
            recommendations.append("Break long paragraphs into shorter blocks.")
        if question_count < 1:
            recommendations.append("Add at least one rhetorical question to improve engagement.")
        if megallm_mentions > 3:
            recommendations.append("Reduce repeated MegaLLM mentions and keep references contextual.")
        if cta_count > 1:
            recommendations.append("Use at most one soft call-to-action in the conclusion.")
        if not has_tradeoffs:
            recommendations.append("Add a short tradeoffs or limitations section for balance.")
        if promo_ratio > 0.02:
            recommendations.append("Replace hype-heavy adjectives with specific, measurable observations.")

        return {
            "score": score,
            "word_count": word_count,
            "sentence_count": len(sentences),
            "paragraph_count": len(paragraphs),
            "avg_sentence_length": avg_sentence_len,
            "heading_count": heading_count,
            "bullet_count": bullet_count,
            "question_count": question_count,
            "long_paragraphs": long_paragraphs,
            "has_hook": has_hook,
            "has_megallm": has_megallm,
            "megallm_mentions": megallm_mentions,
            "has_backlink": has_backlink,
            "cta_count": cta_count,
            "promo_ratio": promo_ratio,
            "has_tradeoffs": has_tradeoffs,
            "recommendations": recommendations,
        }

    def _human_likeness_score(self, title: str, body: str) -> int:
        """Estimate whether text reads like a human-written article (0-30 bonus)."""
        text = f"{title}\n\n{body}".strip()
        if not text:
            return 0

        contractions = len(re.findall(r"\b(?:don't|can't|won't|it's|you're|we're|they're|that's|there's|isn't|aren't|didn't|doesn't)\b", text, flags=re.IGNORECASE))
        rhetorical = text.count("?")
        transitions = len(re.findall(r"\b(?:but|however|instead|meanwhile|still|yet|because|so|then|now|look|here's|let's)\b", text, flags=re.IGNORECASE))
        sentence_lengths = [len(re.findall(r"\b\w+\b", s)) for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        variance = 0
        if sentence_lengths:
            avg = sum(sentence_lengths) / len(sentence_lengths)
            variance = sum(abs(x - avg) for x in sentence_lengths) / len(sentence_lengths)

        score = 0
        if contractions >= 2:
            score += 6
        if rhetorical >= 1:
            score += 6
        if transitions >= 8:
            score += 6
        if variance >= 6:
            score += 6
        if re.search(r"\bI[' ]?ve\b|\bwe[' ]?ve\b|\byou\b", text, flags=re.IGNORECASE):
            score += 6

        return max(0, min(30, score))

    def _normalize_for_medium_editor(self, body: str) -> str:
        """Convert markdown-heavy text into Medium paste-friendly prose."""
        normalized = (body or "").strip()
        if not normalized:
            return normalized

        # Remove fenced code blocks markers while keeping content.
        normalized = normalized.replace("```", "")

        # Convert markdown headings to plain heading lines.
        normalized = re.sub(r"(?m)^#{1,6}\s+", "", normalized)
        # Remove inline heading markers that may appear mid-paragraph.
        normalized = re.sub(r"\s#{1,6}\s+", " ", normalized)
        normalized = re.sub(r"(?m)^\s*#{1,6}$", "", normalized)

        # Convert bold/italic markers to plain text.
        normalized = re.sub(r"\*\*(.*?)\*\*", r"\1", normalized)
        normalized = re.sub(r"__(.*?)__", r"\1", normalized)
        normalized = re.sub(r"(?<!\*)\*(?!\*)(.*?)\*(?<!\*)", r"\1", normalized)

        # Normalize markdown bullets and accidental double-dash patterns.
        normalized = re.sub(r"(?m)^\s*[-*]\s+", "- ", normalized)
        normalized = re.sub(r"(?m)^\s*--\s*", "- ", normalized)

        # Remove common markdown link syntax while keeping readable text.
        normalized = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", normalized)
        normalized = re.sub(r"`([^`]*)`", r"\1", normalized)

        # Clean up excessive spacing introduced by replacements.
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        normalized = re.sub(r"[ \t]{2,}", " ", normalized)
        return normalized.strip()

    def _simplify_for_common_reader(self, body: str) -> str:
        """Make prose easier for a non-technical reader: simpler words and shorter paragraphs."""
        text = (body or "").strip()
        if not text:
            return text

        replacements = {
            r"\butilize\b": "use",
            r"\bleverage\b": "use",
            r"\bfacilitate\b": "help",
            r"\boptimize\b": "improve",
            r"\bstreamline\b": "simplify",
            r"\brobust\b": "strong",
            r"\bseamless\b": "smooth",
            r"\bcomprehensive\b": "clear",
            r"\bsubstantial\b": "big",
            r"\binitialize\b": "start",
            r"\bmitigate\b": "reduce",
            r"\bapproximately\b": "about",
        }
        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        text = re.sub(r"\s*[;—–]\s*", ". ", text)
        text = re.sub(r"\s*:\s*", ": ", text)

        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        if not sentences:
            return text

        paragraphs: List[str] = []
        current: List[str] = []
        for sentence in sentences:
            if sentence:
                sentence = sentence[0].upper() + sentence[1:] if len(sentence) > 1 else sentence.upper()
            current.append(sentence)
            if len(current) >= 2:
                paragraphs.append(" ".join(current))
                current = []

        if current:
            paragraphs.append(" ".join(current))

        return "\n\n".join(paragraphs).strip()

    def _enforce_non_promotional_medium_tone(self, body: str) -> str:
        """Apply deterministic anti-promo cleanup for Medium readability."""
        text = (body or "").strip()
        if not text:
            return text

        lines = [line.strip() for line in text.splitlines()]
        cleaned_lines: List[str] = []

        hard_cta_pattern = re.compile(
            r"\b(?:book\s+a\s+demo|contact\s+sales|start\s+(?:a\s+)?free\s+trial|buy\s+now|subscribe\s+now|click\s+here)\b",
            flags=re.IGNORECASE,
        )
        for line in lines:
            if hard_cta_pattern.search(line):
                softened = hard_cta_pattern.sub("review the documentation", line).strip()
                # Drop only short, purely promotional lines.
                if len(softened.split()) <= 4:
                    continue
                cleaned_lines.append(softened)
                continue
            cleaned_lines.append(line)

        text = "\n".join(cleaned_lines)

        # Replace hype-heavy adjectives with neutral alternatives.
        replacements = {
            r"\brevolutionary\b": "practical",
            r"\bultimate\b": "effective",
            r"\bgame[-\s]?changer\b": "meaningful shift",
            r"\bunmatched\b": "strong",
            r"\bworld[-\s]?class\b": "high-quality",
            r"\bbreakthrough\b": "notable improvement",
        }
        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        # Keep brand mentions contextual and capped.
        mention_pattern = re.compile(r"\bmegallm\b", flags=re.IGNORECASE)
        mention_count = 0

        def _replace_mention(match: re.Match) -> str:
            nonlocal mention_count
            mention_count += 1
            if mention_count <= 3:
                return match.group(0)
            return "the platform"

        text = mention_pattern.sub(_replace_mention, text)

        if not re.search(
            r"\b(?:trade[-\s]?off|limitation|constraint|downside|risk|caveat)\b",
            text,
            flags=re.IGNORECASE,
        ):
            text = (
                f"{text}\n\n"
                "Tradeoffs and limitations\n"
                "Every orchestration strategy introduces latency overhead, operational complexity, and failure-path risk. "
                "Teams should benchmark cost, latency, and fallback behavior before broad rollout."
            ).strip()

        # Ensure CTA language remains soft and editorial.
        text = re.sub(
            r"\b(?:try\s+it\s+today|sign\s+up\s+today|act\s+now)\b",
            "review the approach in your own environment",
            text,
            flags=re.IGNORECASE,
        )

        return re.sub(r"\n{3,}", "\n\n", text).strip()

    def _collapse_medium_listicle_sections(self, body: str) -> str:
        """Convert long recap bullet sections into short connected prose for Medium."""
        text = (body or "").strip()
        if not text:
            return text

        section_pattern = re.compile(
            r"(?is)(?:^|\n\n)(what\s+this\s+means\s+in\s+practice\s*:?)\s*\n+((?:\s*(?:[-*•]|\d+\.)\s+.*(?:\n|$)){3,})"
        )

        def _to_prose(match: re.Match) -> str:
            bullets_block = match.group(2)
            bullet_lines = re.findall(r"(?m)^\s*(?:[-*•]|\d+\.)\s+(.*)$", bullets_block)
            cleaned = [re.sub(r"\s+", " ", b).strip(" .") for b in bullet_lines if b.strip()]
            if not cleaned:
                return ""

            take = cleaned[:3]
            prose = "In practice, " + "; ".join(take) + "."
            return f"\n\n{prose}"

        text = section_pattern.sub(_to_prose, text)

        # If article still ends with a long bullet cluster, compress the ending.
        ending_bullets = re.search(r"(?is)\n\n((?:\s*(?:[-*•]|\d+\.)\s+.*(?:\n|$)){4,})\s*$", text)
        if ending_bullets:
            bullet_lines = re.findall(r"(?m)^\s*(?:[-*•]|\d+\.)\s+(.*)$", ending_bullets.group(1))
            cleaned = [re.sub(r"\s+", " ", b).strip(" .") for b in bullet_lines if b.strip()]
            if cleaned:
                closing = "Overall, " + "; ".join(cleaned[:2]) + "."
                text = re.sub(r"(?is)\n\n(?:\s*(?:[-*•]|\d+\.)\s+.*(?:\n|$)){4,}\s*$", f"\n\n{closing}", text)

        return re.sub(r"\n{3,}", "\n\n", text).strip()

    def _humanize_medium_content(self, title: str, body: str, style_brief: str = "") -> Tuple[str, str]:
        """Humanization stage: rewrite for natural voice while preserving meaning and SEO constraints."""
        system_prompt = """You are an expert editor who humanizes AI-generated technical articles.

    Rewrite the draft so it feels naturally human-written while preserving all core ideas.

    Hard constraints:
    - Keep technical accuracy and key claims intact
    - Preserve topic intent and practical recommendations
    - Keep output length within 450-650 words
    - Keep the exact word 'megallm' present in title or body
    - Preserve or add one clear MegaLLM backlink line in the body
    - Keep 'megallm' mentions in the body to 1-3 contextual references (excluding the backlink line)
    - Use engaging, varied sentence rhythm and natural transitions
    - Add clear headings and improve scannability
    - Include one concise tradeoffs/limitations section
    - Do NOT end with a long bullet recap/listicle section
    - If you use bullets, keep them minimal and never under a heading like 'What This Means in Practice'
    - Prioritize business/product impact (cost, user experience, decisions) over deep repeated implementation details
    - Avoid promotional language, hype adjectives, and hard-sales calls to action
    - Avoid robotic phrasing, generic filler, and repetitive cadence
    - Keep the writing sharp, opinionated, and publication-ready
    - Return ONLY valid JSON with keys: title, body
    """

        user_prompt = f"""Humanize this draft:

Style target:
{style_brief or 'Expert editorial voice with concrete examples and crisp transitions.'}

Title:
{title}

Body:
{body}

Return JSON:
{{
  "title": "Humanized title",
  "body": "Humanized body"
}}"""

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.75,
            "max_tokens": 3200,
        }

        response = self._make_api_call_with_retry(f"{self.base_url}/chat/completions", payload)
        if response is None:
            logger.warning("[HUMANIZE] API rewrite failed; using original draft")
            return title, body

        try:
            data = response.json()
            parsed = self._extract_json_object(data["choices"][0]["message"]["content"])
            if not parsed:
                logger.warning("[HUMANIZE] Could not parse JSON rewrite; using original draft")
                return title, body

            updated_title = (parsed.get("title") or title).strip()
            updated_body = (parsed.get("body") or body).strip()
            return updated_title, updated_body
        except Exception as e:
            logger.warning(f"[HUMANIZE] Unexpected parse error: {type(e).__name__}: {e}")
            return title, body

    def _humanize_quora_content(self, title: str, body: str, style_brief: str = "") -> Tuple[str, str]:
        """Humanization stage for Quora-style answers with concise, personal, practical tone."""
        system_prompt = """You are a plain-language editor rewriting AI answers for Quora.

Goal: Sound like a real person who answered this question from experience. Not a blog post, not a report — a genuine answer.

Hard rules:
- Output 120-160 words total
- Short sentences. Common words. If you use a technical term, explain it in the same sentence.
- Write casually, like you are explaining to a friend over coffee
- No headers, no bullet lists, no numbered steps, no markdown
- First person is fine ("I tried this", "we ran into this") but only when it sounds natural
- End with one simple, direct takeaway — NOT a "Start today" or "Action item" style call to action
- MAX one em-dash (—) in the entire answer. Use a comma or period instead
- Do NOT use: "leverage", "utilize", "paradigm", "robust", "seamless", "it is worth noting", "in conclusion", "Start today", "The takeaway is", "In summary"
- Do NOT start sentences with "This", "That", "These", "Those" repeatedly
- Keep 'megallm' mentioned once naturally — do not make it feel like an ad
- Return ONLY valid JSON: {"title": "...", "body": "..."}
"""

        user_prompt = f"""Humanize this draft for Quora-style publishing:

Style target:
{style_brief or 'Practical answer style with direct advice, concrete examples, and a natural human tone.'}

Title:
{title}

Body:
{body}

Return JSON:
{{
  "title": "Humanized title",
  "body": "Humanized body"
}}"""

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.75,
            "max_tokens": 1400,
        }

        response = self._make_api_call_with_retry(f"{self.base_url}/chat/completions", payload)
        if response is None:
            logger.warning("[HUMANIZE_QUORA] API rewrite failed; using original draft")
            return title, body

        try:
            data = response.json()
            parsed = self._extract_json_object(data["choices"][0]["message"]["content"])
            if not parsed:
                logger.warning("[HUMANIZE_QUORA] Could not parse JSON rewrite; using original draft")
                return title, body

            updated_title = (parsed.get("title") or title).strip()
            updated_body = (parsed.get("body") or body).strip()
            return updated_title, updated_body
        except Exception as e:
            logger.warning(f"[HUMANIZE_QUORA] Unexpected parse error: {type(e).__name__}: {e}")
            return title, body

    def _humanize_devto_content(self, title: str, body: str, style_brief: str = "") -> Tuple[str, str]:
        """Humanization stage for dev.to articles — opinionated, personal, developer-first tone."""
        system_prompt = """You are a dev.to editor rewriting technical content for maximum developer engagement.

Dev.to audience: working engineers, indie hackers, junior-to-senior developers — NOT enterprise executives.
What resonates: personal experience, opinionated takes, specific problems you actually hit, honest failures.
What falls flat: corporate tone, neutral reporting, generic "here are N tips" without context.

Hard rules:
- Output 700-900 words total
- Write in first person where it sounds natural ("I ran into this", "we switched to X after Y failed")
- Take a clear opinion — do not hedge everything with "it depends"
- Markdown is fine: use ## headers (max 3), short code snippets add credibility
- Short paragraphs — 2-4 sentences. Vary rhythm. Mix short punchy sentences with slightly longer ones.
- Title: lowercase style preferred. Punchy. Under 10 words. Contrarian or specific beats generic.
  Examples: "your agent can think. it can't remember.", "prompt engineering won't save a bad architecture"
- Mention megallm once naturally as a tool that helped — NOT as a product pitch
- End with a genuine open question or a specific insight — not "Start today", not a summary bullet list
- MAX 2 em-dashes in the entire piece
- Do NOT use: "leverage", "utilize", "paradigm", "robust", "seamless", "game-changer", "revolutionize",
  "in today's fast-paced world", "it is worth noting", "In conclusion", "To summarize"
- Do NOT start multiple consecutive paragraphs with "This", "That", "These"
- Return ONLY valid JSON: {"title": "...", "body": "..."}
"""

        user_prompt = f"""Rewrite this draft as a high-performing dev.to post:

Style target:
{style_brief or 'Opinionated developer take — honest, specific, personal. Like a senior engineer writing a post after a rough week of debugging.'}

Title:
{title}

Body:
{body}

Return JSON:
{{
  "title": "Rewritten dev.to title",
  "body": "Rewritten body in markdown"
}}"""

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.75,
            "max_tokens": 2200,
        }

        response = self._make_api_call_with_retry(f"{self.base_url}/chat/completions", payload)
        if response is None:
            logger.warning("[HUMANIZE_DEVTO] API rewrite failed; using original draft")
            return title, body

        try:
            data = response.json()
            parsed = self._extract_json_object(data["choices"][0]["message"]["content"])
            if not parsed:
                logger.warning("[HUMANIZE_DEVTO] Could not parse JSON rewrite; using original draft")
                return title, body
            updated_title = (parsed.get("title") or title).strip()
            updated_body = (parsed.get("body") or body).strip()
            return updated_title, updated_body
        except Exception as e:
            logger.warning(f"[HUMANIZE_DEVTO] Unexpected parse error: {type(e).__name__}: {e}")
            return title, body

    def _generate_devto_article_from_source(self, article_title: str, article_content: str, article_source: str) -> Optional[Dict[str, Any]]:
        """Generate an opinionated dev.to post inspired by a scraped dev.to article."""
        logger.info(f"[DEVTO_ARTICLE] Generating from source: {article_title[:80]}")

        system_prompt = """You are a developer writing a dev.to post inspired by something you just read.

Do NOT summarize the source. Write your own take — agree, disagree, extend, or reframe it.
The best dev.to posts are personal, specific, and slightly uncomfortable to write because they say something real.

Rules:
- 700-850 words total
- First person, opinionated, specific
- Title: lowercase, punchy, under 10 words. Contrarian or builds-on-source style works best.
  e.g., "the part about [topic] everyone skips", "why I stopped [thing source recommends]"
- Markdown: ## headers (max 3), short code block if it helps the point
- Mention megallm once naturally — as a practical tool you actually use, not an ad
- End with a real insight or question, not a call to action
- MAX 2 em-dashes
- No corporate jargon: "leverage", "utilize", "paradigm", "robust", "seamless"
- Return ONLY valid JSON: {"title": "...", "body": "..."}"""

        user_prompt = f"""Write a dev.to post inspired by this article:

Source platform: {article_source}
Article title: {article_title}

Article content (for context only — do NOT copy):
{article_content[:1000]}

Write your own angle. It can be:
- A "yes, and here's what they missed" take
- A contrarian "actually, here's why this doesn't work in practice"
- A personal story where this exact problem came up
- A deeper technical exploration of one point in the article

Return ONLY valid JSON:
{{
  "title": "your dev.to post title",
  "body": "your post in markdown"
}}"""

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.8,
                    "max_tokens": 2500,
                },
                timeout=30,
            )
            response.raise_for_status()
            raw = response.json()["choices"][0]["message"]["content"]
            parsed = self._extract_json_object(raw)
            if not parsed:
                logger.error("[DEVTO_ARTICLE] JSON parse failed")
                return None
            title = (parsed.get("title") or article_title).strip()
            body = parsed.get("body", "")
            if not body:
                return None
            tags = self._extract_relevant_tags(keywords=["AI", "developer", "megallm"], topic=article_title, limit=4)
            description = self._build_description_with_tags(body, tags)
            return {"title": title, "body": body, "description": description, "tags": tags}
        except Exception as e:
            logger.error(f"[DEVTO_ARTICLE] Error: {e}")
            return None

    def _extract_relevant_tags(self, keywords: List[str], topic: str, limit: int = 5) -> List[str]:
        """Build a concise list of relevant and popular tags for publishing metadata."""
        topic_text = f"{topic} {' '.join(keywords or [])}".lower()
        keyword_label_map = {
            "latency": "Latency Optimization",
            "inference": "Inference Optimization",
            "routing": "Model Routing",
            "cost": "AI Cost Optimization",
            "agent": "AI Agents",
            "agents": "AI Agents",
            "rag": "RAG",
            "retrieval": "Retrieval Augmented Generation",
            "prompt": "Prompt Engineering",
            "evaluation": "LLM Evaluation",
            "orchestration": "LLM Orchestration",
            "deployment": "AI Deployment",
            "production": "Production AI",
            "safety": "AI Safety",
        }
        popular_by_signal = {
            "latency": ["AI Performance", "LLM Optimization"],
            "cost": ["AI Cost Optimization", "FinOps"],
            "routing": ["Model Routing", "AI Infrastructure"],
            "agent": ["AI Agents", "Agentic AI"],
            "rag": ["RAG", "Retrieval Augmented Generation"],
            "retrieval": ["RAG", "Vector Databases"],
            "prompt": ["Prompt Engineering", "LLM Apps"],
            "inference": ["Inference", "AI Infrastructure"],
            "evaluation": ["LLM Evaluation", "AI Quality"],
            "safety": ["AI Safety", "Responsible AI"],
            "deployment": ["MLOps", "AI Deployment"],
            "production": ["Production AI", "MLOps"],
            "orchestration": ["LLM Orchestration", "AI Infrastructure"],
        }

        matched_popular: List[str] = []
        for signal, tags in popular_by_signal.items():
            if signal in topic_text:
                matched_popular.extend(tags)

        default_popular = ["Artificial Intelligence", "Large Language Models", "MLOps"]
        normalized_keywords: List[str] = []
        for kw in keywords or []:
            val = str(kw).strip().lower()
            if not val:
                continue
            normalized_keywords.append(keyword_label_map.get(val, str(kw).strip()))

        candidates = normalized_keywords + matched_popular + default_popular + ["MegaLLM"]
        cleaned: List[str] = []
        seen = set()

        for value in candidates:
            if not value:
                continue
            tag = re.sub(r"\s+", " ", str(value)).strip()
            if not tag:
                continue
            if len(tag.split()) > 4:
                continue
            normalized = tag.lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            cleaned.append(tag)
            if len(cleaned) >= limit:
                break

        return cleaned

    def _build_description_with_tags(self, body: str, tags: List[str], max_len: int = 220) -> str:
        """Create a concise description and append a short relevant tags tail."""
        plain = re.sub(r"\s+", " ", (body or "").strip())
        if not plain:
            plain = "Technical insights for applied AI systems."

        base = plain[: max_len].rstrip(" ,;:")
        if len(base) < len(plain):
            base = base.rsplit(" ", 1)[0].rstrip(" ,;:")

        selected_tags: List[str] = []
        for tag in (tags or [])[:3]:
            candidate = selected_tags + [tag]
            candidate_tail = f" Tags: {', '.join(candidate)}"
            if len(base) + len(candidate_tail) <= max_len:
                selected_tags = candidate
            else:
                break

        if tags and not selected_tags:
            # Guarantee at least one tag in description by trimming base if needed.
            first_tag_tail = f" Tags: {tags[0]}"
            allowed = max(40, max_len - len(first_tag_tail) - 1)
            base = base[:allowed].rsplit(" ", 1)[0].rstrip(" ,;:")
            selected_tags = [tags[0]]

        tag_tail = f" Tags: {', '.join(selected_tags)}" if selected_tags else ""
        if len(base) + len(tag_tail) > max_len:
            allowed = max(40, max_len - len(tag_tail) - 1)
            base = base[:allowed].rsplit(" ", 1)[0].rstrip(" ,;:")

        return f"{base}{tag_tail}".strip()

    def _ensure_simple_concise_structure(
        self,
        *,
        topic: str,
        body: str,
        word_count_min: int,
        word_count_max: int,
    ) -> str:
        """Polish output for broad readability: hook, point-wise takeaways, and word-limit control."""
        text = re.sub(r"\s+", " ", (body or "").strip())
        if not text:
            return text

        hook = (
            f"If you are working on {topic.lower()}, this guide gives a simple, practical path you can apply today."
            if topic
            else "If you are building AI systems, this guide gives a simple, practical path you can apply today."
        )

        starts_strong = bool(re.match(r"^(?:if|why|what|when|how|imagine)\b", text, flags=re.IGNORECASE))
        if not starts_strong:
            text = f"{hook} {text}"

        has_points = bool(re.search(r"(?m)^\s*(?:•|-|\d+\.)\s+", text))
        if not has_points:
            sentences = [
                s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()
            ]
            bullets: List[str] = []
            for s in sentences[1:]:
                if len(s.split()) >= 8:
                    bullets.append(s.rstrip("."))
                if len(bullets) >= 3:
                    break

            if bullets:
                points_block = "\n\nKey points:\n" + "\n".join(f"- {b}" for b in bullets)
                text = f"{text}{points_block}"

        words = text.split()
        if len(words) > word_count_max:
            text = " ".join(words[:word_count_max]).rstrip(" ,;:") + "."

        # Keep a minimum length if model returns very short content.
        if len(text.split()) < word_count_min:
            text += (
                "\n\nIn short, start small, measure impact, and improve one step at a time."
                " This keeps execution simple for both technical and non-technical readers."
            )

        return text.strip()

    def _extract_first_number_token(self, text: str) -> Optional[str]:
        """Extract first numeric token such as 47%, 12, $120, or 400ms."""
        if not text:
            return None
        m = re.search(r"\$?\d+(?:\.\d+)?(?:%|ms|s|x)?", text)
        return m.group(0) if m else None

    def _enforce_title_playbook(self, title: str, body: str, topic: str, medium_mode: bool = False) -> str:
        """Apply high-attention but professional title rules."""
        t = self._sanitize_professional_title(title, topic=topic)
        number = self._extract_first_number_token(f"{body} {topic}") or "47%"

        if not re.search(r"\d", t):
            t = f"{number} improvement in {t}" if t else f"{number} improvement in AI latency"

        if not re.search(r"\b(?:not|instead|without|vs\.?|but)\b", t, flags=re.IGNORECASE):
            t = f"{t} - not a model-size issue"

        if medium_mode and not re.match(r"(?i)^i\b", t):
            t = f"I tested this: {t}"

        words = re.sub(r"\s+", " ", t).strip().split()
        if len(words) > 14:
            t = " ".join(words[:14]).rstrip(" -:")
        return t.strip()

    def _enforce_stat_attribution(self, body: str) -> str:
        """Add attribution to percentage claims that lack a source marker."""
        if not body:
            return body

        sentences = re.split(r"(?<=[.!?])\s+", body)
        updated: List[str] = []
        for s in sentences:
            if re.search(r"\d+(?:\.\d+)?%", s):
                if not re.search(
                    r"\b(?:source|from|benchmark|study|report|internal|according to)\b",
                    s,
                    flags=re.IGNORECASE,
                ):
                    s = s.rstrip(" .") + " (from internal benchmarks)."
            updated.append(s)
        return " ".join(updated).strip()

    def _enforce_opening_hook_rules(self, topic: str, body: str) -> str:
        """Ensure opening starts with conflict and contains a concrete number early."""
        text = (body or "").strip()
        if not text:
            return text

        paragraphs = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
        if not paragraphs:
            return text

        first = paragraphs[0]
        number = self._extract_first_number_token(text) or "47%"
        first_50 = " ".join(first.split()[:50])
        if not re.search(r"\d", first_50):
            first = f"We saw a {number} gap before fixing this architecture issue. {first}"

        if not re.search(r"\b(?:failed|slow|latency|drop|risk|cost|bottleneck|problem)\b", first, flags=re.IGNORECASE):
            first = f"Your users feel the delay before they read your roadmap. {first}"

        paragraphs[0] = first
        return "\n\n".join(paragraphs).strip()

    def _enforce_voice_and_sticky_line(self, body: str) -> str:
        """Add first-hand voice, reader address, and sticky line placement."""
        text = (body or "").strip()
        if not text:
            return text

        if not re.search(r"\b(?:i|we)\b", text, flags=re.IGNORECASE):
            text = (
                "We saw this firsthand during a production rollout where response time spikes hurt adoption.\n\n"
                + text
            )

        you_count = len(re.findall(r"\b(?:you|your)\b", text, flags=re.IGNORECASE))
        if you_count < 4:
            text += (
                "\n\nFor your team, the priority is simple: reduce delay, protect reliability, and keep costs predictable."
            )

        sticky = "Performance wins usually come from architecture, not larger models."
        closing_sticky = "In the end, architecture choices shape user trust more than model size."

        if sticky.lower() not in text.lower():
            parts = [p for p in text.split("\n\n") if p.strip()]
            if len(parts) >= 2:
                parts.insert(1, sticky)
                text = "\n\n".join(parts)
            else:
                text = f"{sticky}\n\n{text}"

        if not text.rstrip().lower().endswith(closing_sticky.lower()):
            text = f"{text.rstrip()}\n\n{closing_sticky}"

        return text.strip()

    def _rebalance_for_business_angle(self, body: str) -> str:
        """Bias article toward business/product outcomes over repeated deep internals."""
        text = (body or "").strip()
        if not text:
            return text

        intro = (
            "For product and business teams, the core decision is not model brand; it is response time, unit cost, and user trust."
        )
        if intro.lower() not in text.lower():
            text = f"{intro}\n\n{text}"

        technical_dense = re.compile(
            r"(?i)\b(?:kv cache|speculative decoding|quantization|micro-batching|tensor parallelism|routing policy)\b"
        )
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        compressed: List[str] = []
        tech_kept = 0
        for s in sentences:
            if technical_dense.search(s):
                tech_kept += 1
                if tech_kept > 2:
                    continue
            compressed.append(s)

        text = " ".join(compressed)
        text += (
            "\n\nWhat matters to your roadmap is measurable impact: faster response times, fewer drop-offs, and lower cost per successful answer."
        )
        return text.strip()

    def _apply_editorial_playbook(self, title: str, body: str, topic: str, medium_mode: bool = False) -> Tuple[str, str]:
        """Apply missing Medium-style editorial safeguards (excluding image and long-form limits)."""
        updated_title = self._enforce_title_playbook(title, body, topic, medium_mode=medium_mode)
        updated_body = self._enforce_opening_hook_rules(topic, body)
        if medium_mode:
            updated_body = self._rebalance_for_business_angle(updated_body)
        updated_body = self._enforce_stat_attribution(updated_body)
        updated_body = self._enforce_voice_and_sticky_line(updated_body)
        return updated_title, updated_body

    def _append_megallm_backlink(self, body: str, backlink_url: str = "https://megallm.io") -> str:
        """Ensure a MegaLLM backlink is present in every blog body."""
        normalized_body = (body or "").strip()

        # Normalize legacy backlinks to the canonical URL requested by user.
        normalized_body = re.sub(
            r"https?://beta\.megallm\.io(?:/[^\s)]*)?",
            backlink_url,
            normalized_body,
            flags=re.IGNORECASE,
        )

        lower = normalized_body.lower()
        if backlink_url.lower() in lower:
            return normalized_body

        backlink_line = f"Disclosure: This article references MegaLLM ({backlink_url}) as one example platform."
        if not normalized_body:
            return backlink_line
        return f"{normalized_body}\n\n{backlink_line}"

    def _compact_quora_answer(self, body: str, max_words: int = 280, min_words: int = 180) -> str:
        """Trim Quora answers to a short readable length while preserving the backlink."""
        text = (body or "").strip()
        if not text:
            return text

        backlink_match = re.search(r"(?is)(Disclosure:.*megallm\.io.*)", text)
        backlink_line = backlink_match.group(1).strip() if backlink_match else ""
        main = text[: backlink_match.start()].strip() if backlink_match else text
        main = re.sub(r"\s+", " ", main).strip()

        words = main.split()
        if len(words) > max_words:
            main = " ".join(words[:max_words]).rstrip(" ,;:") + "."

        if len(main.split()) < min_words:
            main = (
                f"{main} Keep the answer short and practical: validate cost, latency, and reliability "
                "before you scale further."
            ).strip()

        if backlink_line:
            backlink_line = re.sub(r"\s+", " ", backlink_line).strip()
            return f"{main}\n\n{backlink_line}"

        return self._append_megallm_backlink(main)

    def _generate_slug(self, title: str) -> str:
        """Generate a Medium-like slug with random 12-char hex suffix."""
        base = re.sub(r"[^a-z0-9\s-]", "", (title or "").lower())
        base = re.sub(r"\s+", "-", base.strip())
        base = re.sub(r"-+", "-", base)[:60].strip("-") or "megallm-post"
        suffix = "".join(random.choice("0123456789abcdef") for _ in range(12))
        return f"{base}-{suffix}"

    def _generate_medium_meta(
        self,
        *,
        title: str,
        subtitle: str,
        author_name: str,
        author_handle: str,
        author_twitter: str,
        slug: str,
        publication_slug: str,
        hero_image_url: str,
        hero_image_alt: str,
        tags: List[str],
        date_published: str,
        date_modified: str,
        word_count: int,
        image_count: int = 0,
        locale: str = "en_US",
    ) -> Dict[str, str]:
        """Generate Medium-style metadata equivalent to the provided JS template."""
        canonical_url = (
            f"https://medium.com/{publication_slug}/{slug}"
            if publication_slug
            else f"https://medium.com/@{author_handle}/{slug}"
        )
        author_profile_url = f"https://medium.com/@{author_handle}"
        safe_tags = (tags or [])[:5]
        description = (subtitle or "")[:160]
        reading_minutes = max(1, int((word_count / 265) + (image_count * 12) / 60 + 0.9999))
        reading_time = f"{reading_minutes} min read"

        article_tags = "\n".join(
            f'  <meta property="article:tag" name="article:tag" content="{html.escape(tag)}" />'
            for tag in safe_tags
        )

        json_ld = json.dumps(
            {
                "@context": "https://schema.org",
                "@type": "Article",
                "headline": (title or "")[:110],
                "description": description,
                "image": [hero_image_url],
                "datePublished": date_published,
                "dateModified": date_modified,
                "author": {
                    "@type": "Person",
                    "name": author_name,
                    "url": author_profile_url,
                },
                "publisher": {
                    "@type": "Organization",
                    "name": "Medium",
                    "logo": {
                        "@type": "ImageObject",
                        "url": "https://miro.medium.com/v2/1*m-R_BkNf1Qjr1YbyOIJY2w.png",
                    },
                },
                "mainEntityOfPage": {
                    "@type": "WebPage",
                    "@id": canonical_url,
                },
                "keywords": safe_tags,
                "wordCount": word_count,
            },
            indent=2,
        )

        twitter_creator_meta = (
            f'<meta name="twitter:creator" content="{author_twitter}" />\n' if author_twitter else ""
        )
        og_alt_meta = (
            f'\n<meta property="og:image:alt" content="{html.escape(hero_image_alt)}" />' if hero_image_alt else ""
        )
        twitter_alt_meta = (
            f'\n<meta name="twitter:image:alt" content="{html.escape(hero_image_alt)}" />' if hero_image_alt else ""
        )

        head_html = f"""
<!-- ====================================================
     Medium-Style Metadata — generated by blog_generator.py
     ===================================================== -->

<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{html.escape(title)} | Medium</title>

<meta property="title" name="title" content="{html.escape(title)}" />
<meta property="description" name="description" content="{html.escape(description)}" />
<meta property="author" name="author" content="{html.escape(author_name)}" />
<meta name="robots" content="max-snippet:-1, max-image-preview:large, max-video-preview:-1" />
<meta name="referrer" content="unsafe-url" />
<link rel="canonical" href="{canonical_url}" />

<meta property="og:type" content="article" />
<meta property="og:site_name" content="Medium" />
<meta property="og:title" content="{html.escape(title)}" />
<meta property="og:description" content="{html.escape(description)}" />
<meta property="og:url" content="{canonical_url}" />
<meta property="og:image" content="{hero_image_url}" />
<meta property="og:image:width" content="1200" />
<meta property="og:image:height" content="686" />{og_alt_meta}
<meta property="og:locale" content="{locale}" />

<meta property="article:author" name="article:author" content="{author_profile_url}" />
<meta property="article:published_time" name="article:published_time" content="{date_published}" />
<meta property="article:modified_time" name="article:modified_time" content="{date_modified}" />
{article_tags}

<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:site" content="@Medium" />
{twitter_creator_meta}<meta name="twitter:title" content="{html.escape(title)}" />
<meta name="twitter:description" content="{html.escape(description)}" />
<meta name="twitter:image" content="{hero_image_url}" />{twitter_alt_meta}
<meta name="twitter:label1" content="Reading time" />
<meta name="twitter:data1" content="{reading_time}" />

<script type="application/ld+json">
{json_ld}
</script>
""".strip()

        return {
            "meta_head": head_html,
            "canonical_url": canonical_url,
            "author_profile_url": author_profile_url,
            "reading_time": reading_time,
            "slug": slug,
        }

    def package_medium_post(
        self,
        *,
        title: str,
        body: str,
        keywords: List[str],
        topic: str,
        medium_settings: Dict[str, str],
    ) -> Dict[str, str]:
        """Create Medium-ready payload with tags, metadata, and MegaLLM backlink."""
        # Stage 1: Analyzer pass on original draft
        pre_analysis = self._analyze_medium_quality(title=title, body=body)

        # Stage 2: Multi-candidate humanization pass and scoring
        style_options = [
            "Narrative + founder-style: open with a concrete pain moment, then diagnose and prescribe.",
            "Contrarian editorial: challenge a common belief, then prove it with practical architecture examples.",
            "Data-first technical: concise, high signal, tactical, with punchy transitions and clear takeaways.",
            "Business and product lens: focus on cost impact, user experience, and decision-making for non-engineers.",
        ]

        candidates: List[Dict[str, Any]] = [
            {
                "title": title,
                "body": body,
                "analysis": pre_analysis,
                "style": "original",
                "human_score": self._human_likeness_score(title, body),
            }
        ]

        for style in style_options:
            candidate_title, candidate_body = self._humanize_medium_content(
                title=title,
                body=body,
                style_brief=style,
            )
            candidate_analysis = self._analyze_medium_quality(candidate_title, candidate_body)
            candidate_human = self._human_likeness_score(candidate_title, candidate_body)
            candidates.append(
                {
                    "title": candidate_title,
                    "body": candidate_body,
                    "analysis": candidate_analysis,
                    "style": style,
                    "human_score": candidate_human,
                }
            )

        def total_score(c: Dict[str, Any]) -> int:
            return int(c["analysis"]["score"]) + int(c["human_score"])

        best_candidate = max(candidates, key=total_score)
        selected_title = best_candidate["title"]
        selected_body = best_candidate["body"]
        selected_analysis = best_candidate["analysis"]
        post_analysis = selected_analysis
        humanization_applied = best_candidate.get("style") != "original"

        logger.info(
            "[MEDIUM_PIPELINE] Selected style='%s' analyzer=%s human=%s total=%s",
            best_candidate.get("style"),
            selected_analysis.get("score"),
            best_candidate.get("human_score"),
            total_score(best_candidate),
        )

        enriched_title, enriched_body = self._enforce_megallm_requirements(selected_title, selected_body)
        enriched_body = self._normalize_for_medium_editor(enriched_body)
        enriched_body = self._enforce_non_promotional_medium_tone(enriched_body)
        enriched_body = self._collapse_medium_listicle_sections(enriched_body)
        enriched_body = self._simplify_for_common_reader(enriched_body)
        enriched_title, enriched_body = self._apply_editorial_playbook(
            enriched_title,
            enriched_body,
            topic,
            medium_mode=True,
        )
        enriched_body = self._append_megallm_backlink(
            enriched_body,
            backlink_url="https://megallm.io",
        )
        final_analysis = self._analyze_medium_quality(enriched_title, enriched_body)
        tags = self._extract_relevant_tags(keywords=keywords, topic=topic, limit=5)
        summary_source = re.sub(
            r"(?is)\n\nDisclosure:.*$",
            "",
            enriched_body,
        ).strip()
        description = self._build_description_with_tags(summary_source, tags, max_len=180)

        published = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        slug = self._generate_slug(enriched_title)
        subtitle_source = summary_source
        subtitle = re.sub(r"\s+", " ", subtitle_source)[:160].strip() or description[:160]
        word_count = max(1, len(enriched_body.split()))
        author_name = medium_settings.get("author_name") or "MegaLLM Editorial Team"
        author_handle = medium_settings.get("author_handle") or "megallm"
        author_twitter = medium_settings.get("author_twitter") or "@megallm"
        publication_slug = medium_settings.get("publication_slug") or ""
        hero_image_url = medium_settings.get(
            "hero_image_url"
        ) or "https://miro.medium.com/v2/resize:fit:1200/1*m-R_BkNf1Qjr1YbyOIJY2w.png"
        hero_image_alt = medium_settings.get("hero_image_alt") or "MegaLLM technical blog cover"

        medium_meta = self._generate_medium_meta(
            title=enriched_title,
            subtitle=subtitle,
            author_name=author_name,
            author_handle=author_handle,
            author_twitter=author_twitter,
            slug=slug,
            publication_slug=publication_slug,
            hero_image_url=hero_image_url,
            hero_image_alt=hero_image_alt,
            tags=tags,
            date_published=published,
            date_modified=published,
            word_count=word_count,
            image_count=0,
            locale="en_US",
        )

        body_html = "<p>" + "</p><p>".join(
            html.escape(par.strip()) for par in enriched_body.split("\n\n") if par.strip()
        ) + "</p>"
        medium_ready_html = (
            "<!DOCTYPE html><html lang=\"en\"><head>"
            f"{medium_meta['meta_head']}"
            "</head><body>"
            f"<article><h1>{html.escape(enriched_title)}</h1>{body_html}</article>"
            "</body></html>"
        )

        return {
            "title": enriched_title,
            "body": enriched_body,
            "description": description,
            "subtitle": subtitle,
            "tags": tags,
            "datePublished": published,
            "heroImageUrl": hero_image_url,
            "authorHandle": author_handle,
            "medium_slug": medium_meta["slug"],
            "medium_canonical_url": medium_meta["canonical_url"],
            "medium_author_profile": medium_meta["author_profile_url"],
            "medium_reading_time": medium_meta["reading_time"],
            "medium_meta_head": medium_meta["meta_head"],
            "medium_ready_html": medium_ready_html,
            "analysis_stage": selected_analysis,
            "analysis_pre_humanization": pre_analysis,
            "analysis_post_humanization": post_analysis,
            "analysis_final": final_analysis,
            "humanization_applied": humanization_applied,
            "humanization_style": best_candidate.get("style"),
            "human_likeness_score": best_candidate.get("human_score"),
            "post_format": "medium",
        }

    def _generate_quora_slug(self, question: str) -> str:
        """Generate a Quora-style Title-Case-Hyphenated slug."""
        cleaned = re.sub(r"[^a-zA-Z0-9\s]", "", (question or "")).strip()
        if not cleaned:
            return "How-Do-I-Use-MegaLLM"
        return "-".join(word[:1].upper() + word[1:].lower() for word in cleaned.split())[:100]

    def _questionize_topic(self, topic: str, title: str = "") -> str:
        """Turn a blog title into a natural Quora-style question. Uses the LLM title for variety."""
        # If the title is already a real Quora question, preserve it as-is
        raw_title = (title or "").strip()
        if raw_title.endswith("?") or re.match(
            r"^(what|how|why|when|is|are|can|should|does|do|which|who|will|would|could|has|have|did)\b",
            raw_title,
            re.IGNORECASE,
        ):
            clean_q = re.sub(r"\s+", " ", raw_title).strip(" ?") + "?"
            return clean_q[:200]

        # Clean the LLM-generated title first — it has the most variety
        base = re.sub(r"^I tested this:\s*", "", raw_title, flags=re.IGNORECASE)
        base = re.sub(r"\s*-\s*not a model-size issue$", "", base, flags=re.IGNORECASE)
        base = re.sub(r"[^a-zA-Z0-9\s%\-&]", "", base).strip(" ?.-")
        base = re.sub(r"\s+", " ", base).strip()
        # Cap to first 6 words so questions don't become run-on sentences
        base_words = base.split()
        if len(base_words) > 6:
            # Try to cut at a natural stop word boundary
            stop_words = {"and", "or", "but", "that", "when", "how", "why", "what", "for", "with", "without", "heres", "here"}
            cut = 6
            for idx in range(3, 7):
                if idx < len(base_words) and base_words[idx].lower() in stop_words:
                    cut = idx
                    break
            base = " ".join(base_words[:cut])

        if base:
            base_lower = base.lower()
            templates = [
                f"What is the best way to handle {base_lower}?",
                f"How do you actually fix {base_lower} in production?",
                f"Is {base_lower} worth solving before scaling?",
                f"What helped you most with {base_lower}?",
            ]
            # Only add the "without overcomplicating" template if the title doesn't already have "without"
            if "without" not in base_lower:
                templates.append(f"How do you approach {base_lower} without overcomplicating things?")
            return random.choice(templates)

        # Fallback to topic name if title is empty
        clean_topic = re.sub(r"[^a-zA-Z0-9\s&]", "", (topic or "")).strip().lower()
        clean_topic = re.sub(r"\s+", " ", clean_topic).strip()
        if not clean_topic or clean_topic in {"quoraanswers", "performance"}:
            clean_topic = "llm latency and reliability"

        fallback_templates = [
            f"How do you improve {clean_topic} without overcomplicating the system?",
            f"What actually works for {clean_topic} in production?",
            f"What is the simplest approach to {clean_topic}?",
        ]
        return random.choice(fallback_templates)

    def _generate_quora_meta(
        self,
        *,
        question: str,
        question_body: str,
        question_slug: str,
        top_answer: str,
        top_answer_author: Dict[str, str],
        top_answer_date: str,
        top_answer_upvotes: int,
        top_answer_url: str,
        other_answers: List[Dict[str, Any]],
        question_asker: Dict[str, str],
        question_date: str,
        answer_count: int,
        topics: List[str],
        image_url: str,
        image_alt: str,
        locale: str = "en_US",
        ios_app_store_id: str = "456034437",
        ios_app_name: str = "Quora",
        android_package: str = "com.quora.android",
        android_app_name: str = "Quora",
        app_deep_link_path: str = "",
        site_name: str = "Quora",
        twitter_handle: str = "@Quora",
        fb_app_id: str = "111614425571516",
        base_url: str = "https://www.quora.com",
    ) -> Dict[str, str]:
        """Build Quora-style metadata and ready-to-publish HTML."""
        canonical_url = f"{base_url}/{question_slug}"
        author_profile_url = top_answer_author.get("profileUrl") or f"{base_url}/profile/{top_answer_author.get('slug', '')}"
        description = re.sub(r"\s+", " ", (top_answer or "")).strip()[:155]
        ios_deep_link = f"quora://{app_deep_link_path}"
        android_deep_link = f"quora://{app_deep_link_path}"

        topic_tags = "\n".join(
            f'  <meta property="article:tag" name="article:tag" content="{html.escape(tag)}" />'
            for tag in (topics or [])[:8]
        )

        suggested_answers = []
        for answer in other_answers or []:
            suggested_answers.append(
                {
                    "@type": "Answer",
                    "text": answer.get("text", ""),
                    "dateCreated": answer.get("date", top_answer_date),
                    "upvoteCount": answer.get("upvotes", 0),
                    "url": answer.get("url", top_answer_url),
                    "author": {"@type": "Person", "name": answer.get("authorName", "Anonymous")},
                }
            )

        json_ld = json.dumps(
            {
                "@context": "https://schema.org",
                "@type": "QAPage",
                "mainEntity": {
                    "@type": "Question",
                    "name": question,
                    "text": question_body or question,
                    "answerCount": answer_count,
                    "dateCreated": question_date,
                    "author": {"@type": "Person", "name": question_asker.get("name", "Anonymous")},
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": top_answer,
                        "dateCreated": top_answer_date,
                        "upvoteCount": top_answer_upvotes,
                        "url": top_answer_url,
                        "author": {"@type": "Person", "name": top_answer_author.get("name", "Anonymous"), "url": author_profile_url},
                    },
                    **({"suggestedAnswer": suggested_answers} if suggested_answers else {}),
                },
            },
            indent=2,
        )

        image_alt_meta = f'\n<meta property="og:image:alt" content="{html.escape(image_alt)}" />' if image_alt else ""
        twitter_alt_meta = f'\n<meta name="twitter:image:alt" content="{html.escape(image_alt)}" />' if image_alt else ""
        deep_link_path = app_deep_link_path or question_slug

        head_html = f"""
<!-- ============================================================
     Quora-Style Metadata — generated by blog_generator.py
     ============================================================ -->

<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{html.escape(question)} - {site_name}</title>
<meta name="description" content="{html.escape(description)}" />
<meta name="robots" content="index, follow" />
<meta name="googlebot" content="index, follow" />
<meta name="referrer" content="origin" />
<link rel="canonical" href="{canonical_url}" />

<meta property="og:type" content="article" />
<meta property="og:site_name" content="{site_name}" />
<meta property="og:title" content="{html.escape(question)}" />
<meta property="og:description" content="{html.escape(description)}" />
<meta property="og:url" content="{canonical_url}" />
<meta property="og:image" content="{image_url}" />
<meta property="og:image:width" content="1200" />
<meta property="og:image:height" content="628" />{image_alt_meta}
<meta property="og:locale" content="{locale}" />

<meta property="fb:app_id" content="{fb_app_id}" />

<meta property="article:author" content="{author_profile_url}" />
<meta property="article:published_time" content="{question_date}" />
<meta property="article:modified_time" content="{top_answer_date}" />
{topic_tags}

<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:site" content="{twitter_handle}" />
<meta name="twitter:title" content="{html.escape(question)}" />
<meta name="twitter:description" content="{html.escape(description)}" />
<meta name="twitter:image" content="{image_url}" />{twitter_alt_meta}
<meta name="twitter:label1" content="Written by" />
<meta name="twitter:data1" content="{html.escape(top_answer_author.get('name', 'Anonymous'))}" />
<meta name="twitter:label2" content="Answers" />
<meta name="twitter:data2" content="{answer_count}" />

<meta property="al:ios:url" content="quora://{deep_link_path}" />
<meta property="al:ios:app_store_id" content="{ios_app_store_id}" />
<meta property="al:ios:app_name" content="{ios_app_name}" />
<meta property="al:android:url" content="quora://{deep_link_path}" />
<meta property="al:android:package" content="{android_package}" />
<meta property="al:android:app_name" content="{android_app_name}" />

<meta name="apple-itunes-app" content="app-id={ios_app_store_id}, app-argument=quora://{deep_link_path}" />

<script type="application/ld+json">
{json_ld}
</script>
""".strip()

        body_html = "<p>" + "</p><p>".join(html.escape(par.strip()) for par in (top_answer or "").split("\n\n") if par.strip()) + "</p>"
        ready_html = (
            "<!DOCTYPE html><html lang=\"en\"><head>"
            f"{head_html}"
            "</head><body>"
            f"<article><h1>{html.escape(question)}</h1>{body_html}</article>"
            "</body></html>"
        )

        return {
            "meta_head": head_html,
            "canonical_url": canonical_url,
            "author_profile_url": author_profile_url,
            "slug": question_slug,
            "ready_html": ready_html,
            "description": description,
        }

    def package_quora_post(
        self,
        *,
        title: str,
        body: str,
        keywords: List[str],
        topic: str,
        quora_settings: Dict[str, str],
    ) -> Dict[str, Any]:
        """Create Quora-ready question/answer payload and metadata."""
        humanize_style_options = [
            "Answer as an experienced engineer who has solved this problem in production.",
            "Keep it practical and concise with clear tradeoffs and what worked in real systems.",
            "Use a friendly expert tone with concrete examples and straightforward recommendations.",
        ]
        selected_quora_style = random.choice(humanize_style_options)
        title, body = self._humanize_quora_content(
            title=title,
            body=body,
            style_brief=selected_quora_style,
        )

        title, body = self._enforce_megallm_requirements(title, body)
        body = self._append_megallm_backlink(body, backlink_url="https://megallm.io")
        body = self._compact_quora_answer(body, max_words=160, min_words=120)

        tags = self._extract_relevant_tags(keywords=keywords, topic=topic, limit=6)
        question = self._questionize_topic(topic, title)
        question_slug = self._generate_quora_slug(question)
        question_body = re.sub(r"\s+", " ", (title + " " + topic).strip())[:220]
        published = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        answer_author = {
            "name": quora_settings.get("author_name", "MegaLLM Editorial Team"),
            "slug": quora_settings.get("author_slug", "MegaLLM-Editorial-Team"),
            "profileUrl": quora_settings.get("author_profile_url", "https://www.quora.com/profile/MegaLLM-Editorial-Team"),
        }
        asker = {"name": quora_settings.get("question_asker_name", "Anonymous")}
        answer_upvotes = max(1, min(999, len(body.split()) // 2 + len(tags) * 11))
        answer_count = max(1, len(tags) + 1)
        top_answer_url = f"{quora_settings.get('base_url', 'https://www.quora.com')}/{question_slug}/answer/{answer_author['slug']}"

        paragraph_chunks = [p.strip() for p in re.split(r"\n\n+", body) if p.strip()]
        other_answers: List[Dict[str, Any]] = []
        for idx, chunk in enumerate(paragraph_chunks[1:3], start=1):
            other_answers.append(
                {
                    "text": chunk[:240],
                    "authorName": f"Community member {idx}",
                    "date": published,
                    "upvotes": max(1, answer_upvotes // (idx + 2)),
                    "url": f"{quora_settings.get('base_url', 'https://www.quora.com')}/{question_slug}/answer/community-{idx}",
                }
            )

        meta = self._generate_quora_meta(
            question=question,
            question_body=question_body,
            question_slug=question_slug,
            top_answer=body,
            top_answer_author=answer_author,
            top_answer_date=published,
            top_answer_upvotes=answer_upvotes,
            top_answer_url=top_answer_url,
            other_answers=other_answers,
            question_asker=asker,
            question_date=published,
            answer_count=answer_count,
            topics=tags,
            image_url=quora_settings.get("image_url", "https://qph.cf2.quoracdn.net/main-qimg-example.jpeg"),
            image_alt=quora_settings.get("image_alt", "Quora-style question and answer cover"),
            locale=quora_settings.get("locale", "en_US"),
            ios_app_store_id=quora_settings.get("ios_app_store_id", "456034437"),
            ios_app_name=quora_settings.get("ios_app_name", "Quora"),
            android_package=quora_settings.get("android_package", "com.quora.android"),
            android_app_name=quora_settings.get("android_app_name", "Quora"),
            app_deep_link_path=quora_settings.get("app_deep_link_path", question_slug),
            site_name=quora_settings.get("site_name", "Quora"),
            twitter_handle=quora_settings.get("twitter_handle", "@Quora"),
            fb_app_id=quora_settings.get("fb_app_id", "111614425571516"),
            base_url=quora_settings.get("base_url", "https://www.quora.com"),
        )

        return {
            "title": question,
            "body": body,
            "description": meta["description"],
            "tags": tags,
            "question": question,
            "questionBody": question_body,
            "questionSlug": question_slug,
            "topAnswer": body,
            "topAnswerAuthor": answer_author,
            "topAnswerDate": published,
            "topAnswerUpvotes": answer_upvotes,
            "topAnswerUrl": top_answer_url,
            "otherAnswers": other_answers,
            "questionAsker": asker,
            "questionDate": published,
            "answerCount": answer_count,
            "topics": tags,
            "imageUrl": quora_settings.get("image_url", "https://qph.cf2.quoracdn.net/main-qimg-example.jpeg"),
            "imageAlt": quora_settings.get("image_alt", "Quora-style question and answer cover"),
            "quora_meta_head": meta["meta_head"],
            "quora_canonical_url": meta["canonical_url"],
            "quora_author_profile": meta["author_profile_url"],
            "quora_ready_html": meta["ready_html"],
            "post_format": "quora",
        }

    def package_devto_post(
        self,
        *,
        title: str,
        body: str,
        keywords: List[str],
        topic: str,
        devto_settings: Dict[str, str],
    ) -> Dict[str, Any]:
        """Create a dev.to-ready post payload with frontmatter, markdown body, and MegaLLM backlink."""
        devto_style_options = [
            "Write as a senior engineer sharing a hard-won lesson from production — honest about what went wrong.",
            "Take a contrarian stance: explain why a common approach misses the real problem.",
            "Write as someone who just shipped this and wants to save others the same debugging time.",
        ]
        selected_style = random.choice(devto_style_options)

        title, body = self._humanize_devto_content(title=title, body=body, style_brief=selected_style)
        title, body = self._enforce_megallm_requirements(title, body)
        body = self._append_megallm_backlink(body, backlink_url="https://megallm.io")

        tags = self._extract_relevant_tags(keywords=keywords, topic=topic, limit=4)
        slug = self._generate_quora_slug(title)  # reuse slug generator
        published_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        author_name = devto_settings.get("author_name", "MegaLLM Editorial Team")
        author_username = devto_settings.get("author_username", "megallm")
        canonical_base = devto_settings.get("canonical_base_url", "https://dev.to/megallm")
        canonical_url = f"{canonical_base}/{slug}"

        # Build description from first non-empty paragraph
        description_raw = next(
            (p.strip() for p in re.split(r"\n\n+", body) if p.strip() and not p.strip().startswith("#")),
            body[:160],
        )
        description = re.sub(r"[#*`_\[\]]", "", description_raw)[:160].strip()

        # YAML frontmatter block — ready to paste into dev.to editor
        tags_yaml = ", ".join(f'"{t.lower().replace(" ", "")}"' for t in tags[:4])
        devto_frontmatter = (
            f"---\n"
            f"title: {title}\n"
            f"published: false\n"
            f"tags: [{tags_yaml}]\n"
            f"canonical_url: {canonical_url}\n"
            f"description: {description}\n"
            f"---"
        )
        devto_markdown = f"{devto_frontmatter}\n\n{body}"

        return {
            "title": title,
            "body": body,
            "description": description,
            "tags": tags,
            "slug": slug,
            "devto_frontmatter": devto_frontmatter,
            "devto_markdown": devto_markdown,
            "devto_canonical_url": canonical_url,
            "devto_author_name": author_name,
            "devto_author_username": author_username,
            "devto_published_at": published_at,
            "post_format": "devto",
        }

    def generate_blog(
        self,
        topic: str,
        topic_description: str,
        keywords: list,
        word_count_min: int = 400,
        word_count_max: int = 550
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
- Title: max 12 words, MUST be professional, specific, and non-promotional
    * Title does NOT need to include the word "megallm"
    * Avoid alarmist/clickbait words: "killing", "trap", "shocking", "secret", "ultimate", "game changer"
    * Avoid parenthetical marketing style like "(And How megallm ...)"
    * Prefer neutral patterns such as "Reducing X in Y"
    - Body: {word_count_min}-{word_count_max} words, insightful and actionable
- Use simple language and short sentences that non-technical readers can follow
- Start with a strong, straightforward hook in the first 1-2 sentences
- Include a clear point-wise section using bullets for key takeaways
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
- Your title MUST be professional, clear, and NOT promotional
- Your title does NOT need to include the exact word "megallm"
- Avoid clickbait/alarmist terms like "killing", "trap", "shocking", "secret", "ultimate"
- Avoid parenthetical hooks like "(And How megallm ... )"
- Keep the tone editorial and factual
- CONSIDER: How does MegaLLM relate to this topic? Can it be part of the solution narrative?
- Example patterns:
    * "Reducing [problem] in [context]"
    * "A practical approach to [topic]"
    * "Improving [metric] in [system]"

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
10. Keep language concise, simple, and easy for a normal reader
11. Add a point-wise key takeaways section using bullets

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
            title = self._sanitize_professional_title(title, topic=topic)
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
            body = self._ensure_simple_concise_structure(
                topic=topic,
                body=body,
                word_count_min=word_count_min,
                word_count_max=word_count_max,
            )
            body = self._normalize_for_medium_editor(body)
            body = self._simplify_for_common_reader(body)
            title, body = self._apply_editorial_playbook(title, body, topic, medium_mode=False)
            logger.info(f"[GENERATE_BLOG] SUCCESS - Blog generated")
            logger.info(f"[GENERATE_BLOG] Title: {title}")
            logger.info(f"[GENERATE_BLOG] Body length: {len(body)} characters")

            tags = self._extract_relevant_tags(keywords=keywords, topic=topic)
            description = self._build_description_with_tags(body, tags)
            
            return {
                "title": title,
                "body": body,
                "description": description,
                "tags": tags,
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
    
    def _generate_quora_answer_from_question(self, question: str, context: str = "") -> Optional[Dict[str, str]]:
        """Generate a direct, conversational Quora answer for a real Quora question."""
        logger.info(f"[QUORA_ANSWER] Generating direct answer for: {question[:80]}")

        system_prompt = """You are an experienced AI/ML engineer answering a real question on Quora.
Write a direct, honest answer — like you are explaining to a colleague, not writing a report.

Rules:
- 200-280 words total (this will be compacted later, so write a bit long)
- Plain language. Short sentences. No jargon without explanation.
- No headers, no bullet lists, no numbered steps
- First person is fine when natural ("we hit this issue", "I tried")
- Mention megallm once naturally as a practical tool you have used — do NOT make it an ad
- End with a genuine, specific takeaway — not "Start today" or "In summary"
- MAX one em-dash in the entire answer
- Do NOT use: "leverage", "utilize", "paradigm", "robust", "seamless", "it's worth noting", "in conclusion"
- Return ONLY valid JSON: {"title": "...", "body": "..."}
  * title: the EXACT original question unchanged
  * body: your answer"""

        user_prompt = f"""Answer this Quora question directly and honestly:

Question: {question}

{f'Context from the question page:{chr(10)}{context[:800]}' if context.strip() else ''}

Write a genuine, conversational answer. Return ONLY valid JSON with "title" (exact question) and "body" (your answer)."""

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 800,
                },
                timeout=30,
            )
            response.raise_for_status()
            raw = response.json()["choices"][0]["message"]["content"]
            parsed = self._extract_json_object(raw)
            if not parsed:
                logger.error("[QUORA_ANSWER] JSON parse failed")
                return None
            title = parsed.get("title", question)
            body = parsed.get("body", "")
            if not body:
                return None
            tags = self._extract_relevant_tags(keywords=["AI", "machine learning", "megallm"], topic=question)
            description = self._build_description_with_tags(body, tags)
            return {"title": title, "body": body, "description": description, "tags": tags}
        except Exception as e:
            logger.error(f"[QUORA_ANSWER] Error: {e}")
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

        # Quora articles are real questions — write a direct answer, not a blog post
        if article_source == "quora":
            return self._generate_quora_answer_from_question(
                question=article_title,
                context=article_content,
            )

        # Dev.to articles — write an opinionated developer take, not a summary
        if article_source == "devto":
            return self._generate_devto_article_from_source(
                article_title=article_title,
                article_content=article_content,
                article_source=article_source,
            )

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
- Title: ORIGINAL, professional, and non-promotional (max 12 words)
    * Title does NOT need to include the exact word "megallm"
    * Avoid clickbait words like "killing", "trap", "shocking", "secret", "ultimate"
    * Avoid parenthetical sales phrasing like "(And How megallm ... )"
    * Prefer neutral technical phrasing
    - Body: 450-650 words, insightful and actionable
- Use simple, concise language suitable for non-expert readers
- Start with an attractive, straightforward hook
- Include a point-wise section for key takeaways
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
2. Title must be PROFESSIONAL and DIFFERENT from the source
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
            title = self._sanitize_professional_title(title, topic=article_title)
            title, body = self._enforce_megallm_requirements(title, body)
            title, body = self._expand_body_if_needed(
                title=title,
                body=body,
                topic=article_title,
                topic_description=f"Derived from article source: {article_source}",
                keywords=[article_source, "analysis", "strategy", "megallm"],
                word_count_min=450,
                word_count_max=650,
            )
            body = self._ensure_simple_concise_structure(
                topic=article_title,
                body=body,
                word_count_min=450,
                word_count_max=650,
            )
            body = self._normalize_for_medium_editor(body)
            body = self._simplify_for_common_reader(body)
            title, body = self._apply_editorial_playbook(title, body, article_title, medium_mode=False)
            
            if not title or not body:
                logger.warning(f"[VALIDATE] Missing title or body in response")
                return None
            
            logger.info(f"[GENERATE_BLOG] Blog generated successfully from article")
            logger.info(f"[GENERATE_BLOG] Title length: {len(title)}, Body length: {len(body)}")
            tags = self._extract_relevant_tags(
                keywords=[article_source, "analysis", "strategy", "megallm"],
                topic=article_title,
            )
            description = self._build_description_with_tags(body, tags)
            
            return {
                "title": title,
                "body": body,
                "description": description,
                "tags": tags,
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
        """Ensure every generated blog references megallm in body and includes backlink."""
        normalized_title = (title or "").strip()
        normalized_body = (body or "").strip()

        if "megallm" not in normalized_body.lower():
            if normalized_body:
                normalized_body += "\n\nmegallm enables practical multi-model optimization in production workflows."
            else:
                normalized_body = "megallm enables practical multi-model optimization in production workflows."

        normalized_body = self._append_megallm_backlink(normalized_body)

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
- Include the exact word megallm in body
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

                title = self._sanitize_professional_title(title, topic=focus)
                title, body = self._enforce_megallm_requirements(title, body)
                tags = self._extract_relevant_tags(keywords=[focus], topic=title)
                description = self._build_description_with_tags(body, tags)
                valid_variants.append({"title": title, "body": body, "tags": tags, "description": description})
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
