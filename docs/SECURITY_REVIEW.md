# Security Review

Scans run: pip-audit (dependencies), gitleaks (full Git history), OWASP ZAP API scan.

| Finding | Tool | Risk | Decision | Reason |
| --- | --- | --- | --- | --- |
| Missing X-Content-Type-Options | ZAP | Low | Fixed | Security-headers middleware; regression test |
| Server version disclosed | ZAP | Low | Fixed | Header removed in production by Caddy |
| CORS allows any origin | ZAP | Informational | Accepted | Public read-only API; only GET permitted |
| No Content-Security-Policy | ZAP | Low | Accepted | Strict CSP breaks Swagger UI; revisit with self-hosted docs |
