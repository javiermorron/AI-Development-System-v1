# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repository Is

This is a **documentation-only framework** — a specification and philosophy for AI-native software development. There is no source code, build system, or test runner. The repository contains structured Markdown documents that define how to build software using AI agents.

## Repository Structure

```
docs/
  vision.md          — Philosophy and long-term goals
  architecture.md    — Nine-layer development pipeline overview
  roadmap.md         — v1 → v4 evolution plan
  threat-model.md    — AI-specific risk classification (Levels 1/2/3)
  security-rules.md  — Mandatory security rules for agent-based systems
assets/
  architecture-diagram.png
  architecture-security.png
```

## Core Architecture Concept

The system defines a **13-stage pipeline**:

> Human Direction → Specification → Threat Modeling → Security Rules → Agent Implementation → Automated Testing → AI Code Review → AI Security Review → Policy Validation → Pull Request → CI/CD → Deployment → Observability

Each stage in `docs/` represents a layer. When implementing any feature for this system, that feature must trace through all relevant stages — starting with a spec in `docs/`, threat modeling in `docs/threat-model.md`, and security rules validation against `docs/security-rules.md`.

## Agent Model

Agents are specialized and scoped:
- Each agent type (`backend-agent`, `testing-agent`, `security-agent`, etc.) works in its own feature branch
- Agents operate under **least privilege** — only the tools explicitly required for their task
- All agent actions must be logged (executor, tool, input, output, timestamp)
- No agent has full autonomy; behavior is bounded by rules, permissions, and human-in-the-loop for critical actions

## Security-First Principles (from `docs/security-rules.md` and `docs/threat-model.md`)

Action classification governs agent behavior:
- **Level 1 (Safe):** read/analyze — no approval needed
- **Level 2 (Sensitive):** data modification — log and proceed
- **Level 3 (Critical):** financial ops, deploys, permission changes, data deletion — **requires human approval or double validation**

Key mandatory rules:
- Secrets via environment variables or secret managers only — never hardcoded
- All external inputs (prompts, webhooks, files, APIs) must be validated and sanitized
- Prompt injection mitigation: validate context, strip malicious instructions, limit tool access
- Strict environment separation: dev agents must not access production resources

## Development Philosophy

When adding to this system, the correct order is:
1. Define spec/requirements in `docs/`
2. Update threat model for new attack surfaces
3. Apply security rules before any implementation
4. Implement via agents on feature branches — no direct commits to `main`
5. All PRs go through CI (lint → tests → security check → build) before merge
