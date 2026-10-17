# Security Review

Scans run: pip-audit (dependencies), gitleaks (full Git history), OWASP ZAP API scan.

| Finding | Tool | Risk | Decision | Reason |
| --- | --- | --- | --- | --- |
| Missing X-Content-Type-Options | ZAP | Low | Fixed | Security-headers middleware; regression test |
| Server version disclosed | ZAP | Low | Fixed | Header removed in production by Caddy |
| CORS allows any origin | ZAP | Informational | Accepted | Public read-only API; only GET permitted |
| No Content-Security-Policy | ZAP | Low | Accepted | Strict CSP breaks Swagger UI; revisit with self-hosted docs |
Unexpected Content-Type on /docs and /	ZAP	Informational	Accepted (false positive)	Swagger UI is an HTML page by design
Cross-Origin-Resource-Policy missing	ZAP	Low	Fixed: cross-origin	Public API used cross-origin by the demo page; same-origin would break it
ocker run --rm --network scoresync_default -v "$(pwd)":/zap/wrk:rw -t ghcr.io/zaproxy/zaproxy:stable \
  zap-api-scan.py -t http://api:8000/openapi.json -f openapi -r zap-report.html
FAIL-NEW: 0     FAIL-INPROG: 0  WARN-NEW: 2     WARN-INPROG: 0  INFO: 0 IGNORE: 0       PASS: 118
