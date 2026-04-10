---
name: project-handoff
description: "Use when resuming work on this blog generation pipeline, asking what has already been implemented, or needing a quick project state summary for a new chat."
---

# Project Handoff

## Current State

This repository is a Flask-based blog generation pipeline that uses MegaLLM to generate content, store it in MongoDB, and package it for different publishing formats.

## What Has Already Been Implemented

- Medium editorial playbook enforcement is in place in `blog_platform/blog_generator.py`.
- Markdown cleanup, readability simplification, and shorter output sizing are already implemented.
- Medium posts use a multi-candidate humanization stage with style scoring.
- Quora support has been added for `account_4`.
- Quora posts now run through a dedicated humanization step before Q&A packaging.
- Quora output length has been tightened so it stays short and readable.
- Medium support remains mapped to `account_5`.
- Bulk generation excludes the reserved Medium and Quora accounts.
- The UI includes separate generation actions for Medium and Quora.

## Important Behavior

- Standard accounts still use the raw generated blog content unless they are packaged for Medium or Quora.
- Medium packaging applies the strongest editorial and humanization logic.
- Quora packaging now produces a concise question-and-answer style response with a MegaLLM backlink preserved.

## Files To Know

- `blog_platform/blog_generator.py` contains the generation, humanization, and packaging logic.
- `blog_platform/app.py` routes generation requests and applies account-specific packaging.
- `blog_platform/config.py` contains account and platform configuration.
- `blog_platform/templates/index.html` contains the dashboard UI actions.

## If Continuing Work

Start by checking `blog_platform/blog_generator.py` for the generation path you want to change, then verify the matching route in `blog_platform/app.py`.

## Notes

- Keep secrets out of version control.
- Prefer small changes that preserve the current Medium and Quora behavior.
