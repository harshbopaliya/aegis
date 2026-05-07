# Security Policy

## Supported Versions

The following versions of the Aegis are currently being supported with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of our project seriously. If you discover a security vulnerability, we'd like to know about it so we can take steps to address it as quickly as possible.

**Please DO NOT report security vulnerabilities via public GitHub issues.**

Instead, please report them to: **security@example.com**

Please include the following information in your report:

- Type of issue (e.g. buffer overflow, SQL injection, cross-site scripting, etc.)
- Full paths of source file(s) related to the manifestation of the issue
- The location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit the issue

### Response Timeline

You can expect to receive a response to your report within 48 hours. Our security team will update you on our progress towards a fix, and will notify you when we publish a patch.

## Security Best Practices

For those deploying the Aegis in production, please adhere to the following best practices:

- Always use HTTPS for deployed instances.
- Enable token scoping and authentication for all API endpoints.
- Secure your backup and logs encryption keys.
- Keep dependencies up-to-date.
- Follow the guidelines established in the `DEPLOYMENT.md` documentation.
