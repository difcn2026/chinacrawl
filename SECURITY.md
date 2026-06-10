# Security Policy

## Reporting a Vulnerability

**DO NOT open a public issue for security vulnerabilities.**

Please report security issues privately to:

📧 `security@xhls-scraper.dev` (placeholder — update before launch)

You can also use GitHub's private vulnerability reporting:
1. Go to the **Security** tab
2. Click **Report a vulnerability**
3. Describe the issue with reproduction steps

## What to include

- Description of the vulnerability
- Steps to reproduce
- Affected versions
- Possible impact
- Suggested fix (if any)

## Response timeline

| Phase | Timeline |
|-------|----------|
| Acknowledgment | Within 48 hours |
| Triage & validation | Within 5 business days |
| Fix release | Depends on severity |

## Scope

- `xhls_scraper.py` core module
- `pyproject.toml` and dependency chain
- Documentation and examples

## Out of scope

- User's own SearXNG instance security
- User's own Ollama deployment
- Third-party APIs (Jina AI, Playwright, trafilatura)

## Responsible Disclosure

We follow responsible disclosure:
- Do not exploit the vulnerability
- Do not disclose publicly before a fix is released
- We will credit you in the release notes (unless you prefer anonymity)
