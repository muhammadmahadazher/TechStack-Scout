"""
Technology detection signatures for TechStack Scout.
Each signature defines how to detect a specific technology on a webpage.
"""

from dataclasses import dataclass
from typing import List, Optional, Callable
import re

@dataclass
class DetectionSignature:
    tech_slug: str
    tech_name: str
    category: str
    methods: dict  # detection methods with their patterns
    confidence: float = 1.0

# Detection methods:
# - 'header': Check HTTP response headers
# - 'html_meta': Check HTML meta tags
# - 'script_src': Check script src attributes
# - 'html_content': Check raw HTML content (regex)
# - 'css_class': Check for CSS class patterns
# - 'dns_cname': Check DNS CNAME records (simulated via headers)
# - 'cookie': Check for specific cookies

TECH_SIGNATURES = [
    # === ANALYTICS ===
    DetectionSignature(
        tech_slug="google-analytics",
        tech_name="Google Analytics",
        category="Analytics",
        confidence=0.95,
        methods={
            "script_src": [r"google-analytics\.com/analytics", r"googletagmanager\.com/gtag", r"google-analytics\.com/ga"],
            "html_content": [r"gtag\('config',\s*'UA-", r"gtag\('config',\s*'G-", r"_gaq\.push", r"google-analytics\.com/collect"],
            "cookie": [r"_ga", r"_gid"],
        }
    ),
    DetectionSignature(
        tech_slug="google-tag-manager",
        tech_name="Google Tag Manager",
        category="Analytics",
        confidence=0.95,
        methods={
            "script_src": [r"googletagmanager\.com/gtm\.js"],
            "html_content": [r"dataLayer\s*=\s*\[", r"googletagmanager\.com/ns\.html"],
        }
    ),
    DetectionSignature(
        tech_slug="mixpanel",
        tech_name="Mixpanel",
        category="Analytics",
        confidence=0.9,
        methods={
            "script_src": [r"mixpanel\.com", r"mixpanel-api"],
            "html_content": [r"mixpanel\.track", r"mixpanel\.identify"],
        }
    ),
    DetectionSignature(
        tech_slug="amplitude",
        tech_name="Amplitude",
        category="Analytics",
        confidence=0.9,
        methods={
            "script_src": [r"amplitude\.com", r"amplitude\.min\.js"],
            "html_content": [r"amplitude\.getInstance", r"amplitude\.init"],
        }
    ),
    DetectionSignature(
        tech_slug="segment",
        tech_name="Segment",
        category="Analytics",
        confidence=0.9,
        methods={
            "script_src": [r"segment\.com", r"segment\.io"],
            "html_content": [r"analytics\.load", r"analytics\.track", r"window\.analytics"],
        }
    ),
    DetectionSignature(
        tech_slug="hotjar",
        tech_name="Hotjar",
        category="Analytics",
        confidence=0.9,
        methods={
            "script_src": [r"hotjar\.com", r"static\.hotjar\.com"],
            "html_content": [r"hj\.q", r"hotjar\.com/c/hotjar"],
        }
    ),
    DetectionSignature(
        tech_slug="adobe-analytics",
        tech_name="Adobe Analytics",
        category="Analytics",
        confidence=0.85,
        methods={
            "script_src": [r"adobedtm\.com", r"launch\.adobe\.com"],
            "html_content": [r"s\.t\(\)", r"satelliteLib", r"_satellite"],
        }
    ),

    # === CDN ===
    DetectionSignature(
        tech_slug="cloudflare",
        tech_name="Cloudflare",
        category="CDN",
        confidence=0.95,
        methods={
            "header": [r"cloudflare", r"cf-ray"],
            "script_src": [r"cloudflare\.com", r"cdnjs\.cloudflare"],
            "html_content": [r"__cf_bm", r"cf\.clearTimeout"],
        }
    ),
    DetectionSignature(
        tech_slug="fastly",
        tech_name="Fastly",
        category="CDN",
        confidence=0.9,
        methods={
            "header": [r"fastly"],
            "html_content": [r"fastly\.io"],
        }
    ),
    DetectionSignature(
        tech_slug="aws-cloudfront",
        tech_name="AWS CloudFront",
        category="CDN",
        confidence=0.9,
        methods={
            "header": [r"cloudfront", r"x-amz-cf"],
            "script_src": [r"cloudfront\.net"],
        }
    ),
    DetectionSignature(
        tech_slug="akamai",
        tech_name="Akamai",
        category="CDN",
        confidence=0.85,
        methods={
            "header": [r"akamai", r"x-akamai"],
            "script_src": [r"akamaized\.net"],
        }
    ),

    # === FRONTEND FRAMEWORKS ===
    DetectionSignature(
        tech_slug="react",
        tech_name="React",
        category="Frontend Framework",
        confidence=0.85,
        methods={
            "html_content": [r"data-reactroot", r"data-reactid", r"__REACT_INSPECTOR__", r"reactRoot"],
            "script_src": [r"react\.umd", r"react\.production\.min", r"react\.development"],
        }
    ),
    DetectionSignature(
        tech_slug="vuejs",
        tech_name="Vue.js",
        category="Frontend Framework",
        confidence=0.85,
        methods={
            "html_content": [r"data-v-", r"__VUE__", r"vue-router", r"v-if="],
            "script_src": [r"vue\.js", r"vue\.min\.js", r"vue@"],
        }
    ),
    DetectionSignature(
        tech_slug="angular",
        tech_name="Angular",
        category="Frontend Framework",
        confidence=0.85,
        methods={
            "html_content": [r"ng-app", r"ng-controller", r"ng-model", r"ng-bind", r"ng-repeat", r"ng-if", r"ng-show"],
            "script_src": [r"angular\.js", r"angular\.min\.js"],
        }
    ),
    DetectionSignature(
        tech_slug="nextjs",
        tech_name="Next.js",
        category="Frontend Framework",
        confidence=0.85,
        methods={
            "html_content": [r"__NEXT_DATA__", r"_next/static"],
            "script_src": [r"/_next/"],
        }
    ),
    DetectionSignature(
        tech_slug="nuxtjs",
        tech_name="Nuxt.js",
        category="Frontend Framework",
        confidence=0.85,
        methods={
            "html_content": [r"__NUXT__", r"_nuxt/"],
            "script_src": [r"/_nuxt/"],
        }
    ),
    DetectionSignature(
        tech_slug="svelte",
        tech_name="Svelte",
        category="Frontend Framework",
        confidence=0.8,
        methods={
            "html_content": [r"svelte-", r"__svelte"],
        }
    ),
    DetectionSignature(
        tech_slug="jquery",
        tech_name="jQuery",
        category="Frontend Framework",
        confidence=0.9,
        methods={
            "script_src": [r"jquery", r"jquery\.min\.js", r"jquery-"],
            "html_content": [r"\$\.fn\.jquery", r"jQuery\.fn\.jquery"],
        }
    ),

    # === CSS FRAMEWORKS ===
    DetectionSignature(
        tech_slug="bootstrap",
        tech_name="Bootstrap",
        category="CSS Framework",
        confidence=0.9,
        methods={
            "script_src": [r"bootstrap", r"bootstrap\.min\.js", r"bootstrap\.min\.css"],
            "html_content": [r'class="[^"]*btn-primary', r'class="[^"]*container-fluid', r'class="[^"]*col-md-'],
            "css_class": [r"bootstrap"],
        }
    ),
    DetectionSignature(
        tech_slug="tailwind-css",
        tech_name="Tailwind CSS",
        category="CSS Framework",
        confidence=0.8,
        methods={
            "html_content": [r'class="[^"]*flex', r'class="[^"]*grid', r'class="[^"]*md:', r'class="[^"]*lg:', r'class="[^"]*bg-'],
            "script_src": [r"tailwindcss"],
        }
    ),

    # === CMS ===
    DetectionSignature(
        tech_slug="wordpress",
        tech_name="WordPress",
        category="CMS",
        confidence=0.95,
        methods={
            "html_meta": [r"WordPress"],
            "script_src": [r"wp-content", r"wp-includes"],
            "html_content": [r"/wp-content/", r"/wp-includes/", r"wp-json", r"generator.*WordPress"],
            "header": [r"X-Powered-By.*PHP"],
        }
    ),
    DetectionSignature(
        tech_slug="drupal",
        tech_name="Drupal",
        category="CMS",
        confidence=0.9,
        methods={
            "html_meta": [r"Drupal"],
            "html_content": [r"/sites/default/", r"drupal\.js", r"Drupal\.settings"],
        }
    ),
    DetectionSignature(
        tech_slug="joomla",
        tech_name="Joomla",
        category="CMS",
        confidence=0.9,
        methods={
            "html_meta": [r"Joomla"],
            "html_content": [r"/media/jui/", r"/templates/", r"Joomla\.Text"],
        }
    ),

    # === E-COMMERCE ===
    DetectionSignature(
        tech_slug="shopify",
        tech_name="Shopify",
        category="E-commerce",
        confidence=0.95,
        methods={
            "html_content": [r"Shopify\.theme", r"shopify\.com", r"cdn\.shopify\.com", r"myshopify\.com"],
            "script_src": [r"shopify\.com", r"cdn\.shopify"],
            "header": [r"x-shopify"],
        }
    ),
    DetectionSignature(
        tech_slug="woocommerce",
        tech_name="WooCommerce",
        category="E-commerce",
        confidence=0.9,
        methods={
            "html_content": [r"woocommerce", r"wc-", r"woocommerce\.js"],
            "script_src": [r"woocommerce"],
        }
    ),
    DetectionSignature(
        tech_slug="magento",
        tech_name="Magento",
        category="E-commerce",
        confidence=0.9,
        methods={
            "html_content": [r"Magento", r"mage\.js", r"requirejs-config"],
            "script_src": [r"magento", r"require\.js"],
        }
    ),

    # === PAYMENT ===
    DetectionSignature(
        tech_slug="stripe",
        tech_name="Stripe",
        category="Payment",
        confidence=0.9,
        methods={
            "script_src": [r"stripe\.com", r"stripe\.js"],
            "html_content": [r"Stripe\(", r"stripe\.com/v3", r"StripeCheckout"],
        }
    ),
    DetectionSignature(
        tech_slug="paypal",
        tech_name="PayPal",
        category="Payment",
        confidence=0.9,
        methods={
            "script_src": [r"paypal\.com", r"paypalobjects\.com"],
            "html_content": [r"paypal\.com/sdk", r"PayPal\.Button"],
        }
    ),

    # === WEB SERVERS ===
    DetectionSignature(
        tech_slug="nginx",
        tech_name="Nginx",
        category="Web Server",
        confidence=0.9,
        methods={
            "header": [r"nginx"],
        }
    ),
    DetectionSignature(
        tech_slug="apache",
        tech_name="Apache",
        category="Web Server",
        confidence=0.9,
        methods={
            "header": [r"apache", r"Apache"],
        }
    ),
    DetectionSignature(
        tech_slug="microsoft-iis",
        tech_name="Microsoft IIS",
        category="Web Server",
        confidence=0.9,
        methods={
            "header": [r"Microsoft-IIS"],
        }
    ),

    # === BACKEND FRAMEWORKS ===
    DetectionSignature(
        tech_slug="expressjs",
        tech_name="Express.js",
        category="Backend Framework",
        confidence=0.7,
        methods={
            "header": [r"Express"],
            "html_content": [r"X-Powered-By.*Express"],
        }
    ),
    DetectionSignature(
        tech_slug="django",
        tech_name="Django",
        category="Backend Framework",
        confidence=0.85,
        methods={
            "html_content": [r"csrfmiddlewaretoken", r"django", r"__admin_media_prefix__"],
            "cookie": [r"csrftoken"],
        }
    ),
    DetectionSignature(
        tech_slug="ruby-on-rails",
        tech_name="Ruby on Rails",
        category="Backend Framework",
        confidence=0.85,
        methods={
            "html_content": [r"csrf-param", r"csrf-token", r"data-method", r"rails"],
            "cookie": [r"_session_id"],
        }
    ),
    DetectionSignature(
        tech_slug="laravel",
        tech_name="Laravel",
        category="Backend Framework",
        confidence=0.85,
        methods={
            "html_content": [r"csrf-token", r"laravel_session"],
            "cookie": [r"laravel_session"],
        }
    ),

    # === RUNTIMES ===
    DetectionSignature(
        tech_slug="php",
        tech_name="PHP",
        category="Runtime",
        confidence=0.85,
        methods={
            "header": [r"X-Powered-By.*PHP", r"PHP/"],
            "html_content": [r"\.php\?", r"phpinfo\(\)"],
        }
    ),
    DetectionSignature(
        tech_slug="nodejs",
        tech_name="Node.js",
        category="Runtime",
        confidence=0.7,
        methods={
            "header": [r"Node\.js"],
        }
    ),

    # === MARKETING ===
    DetectionSignature(
        tech_slug="hubspot",
        tech_name="HubSpot",
        category="Marketing",
        confidence=0.9,
        methods={
            "script_src": [r"hubspot\.com", r"hs-scripts\.com", r"hs-analytics"],
            "html_content": [r"hubspot\.com", r"hs-cta", r"hs-form"],
        }
    ),
    DetectionSignature(
        tech_slug="mailchimp",
        tech_name="Mailchimp",
        category="Marketing",
        confidence=0.9,
        methods={
            "script_src": [r"mailchimp\.com", r"chimpstatic\.com"],
            "html_content": [r"mc-embed-signup", r"mailchimp"],
        }
    ),
    DetectionSignature(
        tech_slug="intercom",
        tech_name="Intercom",
        category="Customer Support",
        confidence=0.9,
        methods={
            "script_src": [r"intercom\.io", r"intercomcdn\.com"],
            "html_content": [r"Intercom\(", r"intercomSettings"],
        }
    ),
    DetectionSignature(
        tech_slug="zendesk",
        tech_name="Zendesk",
        category="Customer Support",
        confidence=0.9,
        methods={
            "script_src": [r"zendesk\.com", r"zdassets\.com"],
            "html_content": [r"zE\(", r"zendesk"],
        }
    ),
    DetectionSignature(
        tech_slug="drift",
        tech_name="Drift",
        category="Customer Support",
        confidence=0.9,
        methods={
            "script_src": [r"drift\.com"],
            "html_content": [r"drift\.load", r"drift\.com"],
        }
    ),

    # === CLOUD INFRASTRUCTURE ===
    DetectionSignature(
        tech_slug="aws",
        tech_name="AWS",
        category="Cloud Infrastructure",
        confidence=0.8,
        methods={
            "header": [r"x-amz", r"amazon", r"aws"],
            "script_src": [r"amazonaws\.com", r"aws\.amazon\.com"],
        }
    ),
    DetectionSignature(
        tech_slug="google-cloud",
        tech_name="Google Cloud",
        category="Cloud Infrastructure",
        confidence=0.75,
        methods={
            "header": [r"google", r"gcp"],
            "script_src": [r"googleapis\.com", r"googleusercontent\.com"],
        }
    ),
    DetectionSignature(
        tech_slug="vercel",
        tech_name="Vercel",
        category="Cloud Infrastructure",
        confidence=0.85,
        methods={
            "header": [r"vercel", r"x-vercel"],
            "html_content": [r"_vercel"],
        }
    ),
    DetectionSignature(
        tech_slug="netlify",
        tech_name="Netlify",
        category="Cloud Infrastructure",
        confidence=0.85,
        methods={
            "header": [r"netlify", r"x-nf-request-id"],
            "html_content": [r"netlify"],
        }
    ),
    DetectionSignature(
        tech_slug="heroku",
        tech_name="Heroku",
        category="Cloud Infrastructure",
        confidence=0.85,
        methods={
            "header": [r"heroku"],
        }
    ),

    # === BACKEND-AS-A-SERVICE ===
    DetectionSignature(
        tech_slug="firebase",
        tech_name="Firebase",
        category="Backend-as-a-Service",
        confidence=0.9,
        methods={
            "script_src": [r"firebase\.google\.com", r"firebaseio\.com", r"firebaseapp\.com"],
            "html_content": [r"firebase\.initializeApp", r"firebase\.auth"],
        }
    ),
    DetectionSignature(
        tech_slug="supabase",
        tech_name="Supabase",
        category="Backend-as-a-Service",
        confidence=0.85,
        methods={
            "script_src": [r"supabase\.co", r"supabase\.io"],
            "html_content": [r"supabase", r"createClient.*supabase"],
        }
    ),

    # === DATABASE (indirect detection) ===
    DetectionSignature(
        tech_slug="mongodb",
        tech_name="MongoDB",
        category="Database",
        confidence=0.6,
        methods={
            "html_content": [r"mongodb", r"mongoose"],
        }
    ),

    # === SEARCH ===
    DetectionSignature(
        tech_slug="algolia",
        tech_name="Algolia",
        category="Search",
        confidence=0.9,
        methods={
            "script_src": [r"algolia\.net", r"algolianet\.com"],
            "html_content": [r"algoliasearch", r"algolia\.com"],
        }
    ),
    DetectionSignature(
        tech_slug="elasticsearch",
        tech_name="Elasticsearch",
        category="Search",
        confidence=0.7,
        methods={
            "html_content": [r"elasticsearch"],
        }
    ),

    # === FONTS ===
    DetectionSignature(
        tech_slug="google-fonts",
        tech_name="Google Fonts",
        category="Font",
        confidence=0.95,
        methods={
            "script_src": [r"fonts\.googleapis\.com", r"fonts\.gstatic\.com"],
            "html_content": [r"fonts\.googleapis", r"Google Fonts"],
        }
    ),

    # === ICONS ===
    DetectionSignature(
        tech_slug="font-awesome",
        tech_name="Font Awesome",
        category="Icon",
        confidence=0.9,
        methods={
            "script_src": [r"fontawesome", r"font-awesome"],
            "html_content": [r"fa-", r"fontawesome"],
        }
    ),

    # === MONITORING ===
    DetectionSignature(
        tech_slug="sentry",
        tech_name="Sentry",
        category="Monitoring",
        confidence=0.9,
        methods={
            "script_src": [r"sentry\.io", r"browser\.sentry-cdn"],
            "html_content": [r"Sentry\.init", r"sentry\.io"],
        }
    ),
    DetectionSignature(
        tech_slug="new-relic",
        tech_name="New Relic",
        category="Monitoring",
        confidence=0.9,
        methods={
            "script_src": [r"newrelic\.com", r"nr-data\.net"],
            "html_content": [r"NREUM", r"newrelic"],
        }
    ),
    DetectionSignature(
        tech_slug="datadog",
        tech_name="Datadog",
        category="Monitoring",
        confidence=0.85,
        methods={
            "script_src": [r"datadoghq\.com"],
            "html_content": [r"DD_RUM", r"datadog"],
        }
    ),

    # === SECURITY ===
    DetectionSignature(
        tech_slug="recaptcha",
        tech_name="reCAPTCHA",
        category="Security",
        confidence=0.95,
        methods={
            "script_src": [r"google\.com/recaptcha", r"grecaptcha"],
            "html_content": [r"g-recaptcha", r"recaptcha"],
        }
    ),
    DetectionSignature(
        tech_slug="hcaptcha",
        tech_name="hCaptcha",
        category="Security",
        confidence=0.9,
        methods={
            "script_src": [r"hcaptcha\.com"],
            "html_content": [r"h-captcha", r"hcaptcha"],
        }
    ),

    # === SOCIAL ===
    DetectionSignature(
        tech_slug="twitter",
        tech_name="Twitter/X",
        category="Social",
        confidence=0.9,
        methods={
            "script_src": [r"twitter\.com", r"platform\.twitter"],
            "html_content": [r"twitter\.com/widgets", r"twitter-wjs"],
        }
    ),
    DetectionSignature(
        tech_slug="facebook",
        tech_name="Facebook",
        category="Social",
        confidence=0.9,
        methods={
            "script_src": [r"facebook\.com", r"connect\.facebook"],
            "html_content": [r"fb-root", r"FB\.init"],
        }
    ),

    # === MEDIA ===
    DetectionSignature(
        tech_slug="youtube",
        tech_name="YouTube",
        category="Media",
        confidence=0.95,
        methods={
            "script_src": [r"youtube\.com", r"youtube-nocookie\.com"],
            "html_content": [r"youtube\.com/embed", r"youtube\.com/watch"],
        }
    ),
    DetectionSignature(
        tech_slug="vimeo",
        tech_name="Vimeo",
        category="Media",
        confidence=0.9,
        methods={
            "script_src": [r"vimeo\.com", r"player\.vimeo"],
            "html_content": [r"vimeo\.com"],
        }
    ),

    # === COMPLIANCE ===
    DetectionSignature(
        tech_slug="cookiebot",
        tech_name="Cookiebot",
        category="Compliance",
        confidence=0.9,
        methods={
            "script_src": [r"cookiebot\.com", r"cookiebot\.eu"],
            "html_content": [r"Cookiebot", r"cookieconsent"],
        }
    ),
    DetectionSignature(
        tech_slug="onetrust",
        tech_name="OneTrust",
        category="Compliance",
        confidence=0.9,
        methods={
            "script_src": [r"onetrust\.com", r"cookielaw\.org"],
            "html_content": [r"OneTrust", r"onetrust"],
        }
    ),

    # === A/B TESTING ===
    DetectionSignature(
        tech_slug="optimizely",
        tech_name="Optimizely",
        category="A/B Testing",
        confidence=0.9,
        methods={
            "script_src": [r"optimizely\.com", r"optimizely\.js"],
            "html_content": [r"optimizely", r"window\.optimizely"],
        }
    ),
    DetectionSignature(
        tech_slug="google-optimize",
        tech_name="Google Optimize",
        category="A/B Testing",
        confidence=0.85,
        methods={
            "script_src": [r"googleoptimize\.com"],
            "html_content": [r"google_optimize", r"optimize\.js"],
        }
    ),

    # === DEVOPS ===
    DetectionSignature(
        tech_slug="github",
        tech_name="GitHub",
        category="DevOps",
        confidence=0.8,
        methods={
            "html_content": [r"github\.com", r"github\.io"],
        }
    ),

    # === COMMUNICATION ===
    DetectionSignature(
        tech_slug="slack",
        tech_name="Slack",
        category="Communication",
        confidence=0.8,
        methods={
            "html_content": [r"slack\.com", r"slack\.com/apps"],
        }
    ),
    DetectionSignature(
        tech_slug="discord",
        tech_name="Discord",
        category="Communication",
        confidence=0.8,
        methods={
            "html_content": [r"discord\.com", r"discord\.gg"],
        }
    ),
]

# Build lookup dict
TECH_BY_SLUG = {sig.tech_slug: sig for sig in TECH_SIGNATURES}
TECH_BY_NAME = {sig.tech_name: sig for sig in TECH_SIGNATURES}


def detect_technologies(headers: dict, html_content: str, scripts: list) -> list:
    """
    Detect technologies from crawled page data.
    Returns list of dicts: [{tech_slug, tech_name, category, confidence, method, evidence}]
    """
    detections = []

    # Normalize inputs
    if headers is None:
        headers = {}
    if html_content is None:
        html_content = ""
    if scripts is None:
        scripts = []

    headers_str = "\n".join([f"{k}: {v}" for k, v in headers.items()])
    html_lower = html_content.lower()
    scripts_str = " ".join([s for s in scripts if s]).lower()
    all_content = f"{html_lower} {scripts_str}"

    for sig in TECH_SIGNATURES:
        detected = False
        evidence = ""
        method_used = ""

        # Check headers
        if "header" in sig.methods and headers_str:
            for pattern in sig.methods["header"]:
                if re.search(pattern, headers_str, re.IGNORECASE):
                    detected = True
                    evidence = f"Header match: {pattern}"
                    method_used = "header"
                    break

        # Check HTML meta
        if not detected and "html_meta" in sig.methods:
            meta_pattern = r'<meta[^>]*(?:name|property)=["\']?(?:generator|powered-by|platform)["\']?[^>]*content=["\']?([^"\']*)["\']?[^>]*>'
            for match in re.finditer(meta_pattern, html_content, re.IGNORECASE):
                meta_content = match.group(1)
                for pattern in sig.methods["html_meta"]:
                    if re.search(pattern, meta_content, re.IGNORECASE):
                        detected = True
                        evidence = f"Meta tag: {meta_content}"
                        method_used = "html_meta"
                        break
                if detected:
                    break

        # Check script sources
        if not detected and "script_src" in sig.methods:
            for script in scripts:
                for pattern in sig.methods["script_src"]:
                    if re.search(pattern, script, re.IGNORECASE):
                        detected = True
                        evidence = f"Script: {script[:100]}"
                        method_used = "script_src"
                        break
                if detected:
                    break

        # Check HTML content
        if not detected and "html_content" in sig.methods:
            for pattern in sig.methods["html_content"]:
                if re.search(pattern, all_content, re.IGNORECASE):
                    detected = True
                    evidence = f"HTML match: {pattern[:100]}"
                    method_used = "html_content"
                    break

        # Check cookies (simulated via html content for now)
        if not detected and "cookie" in sig.methods:
            for pattern in sig.methods["cookie"]:
                if re.search(pattern, all_content, re.IGNORECASE):
                    detected = True
                    evidence = f"Cookie indicator: {pattern}"
                    method_used = "cookie"
                    break

        if detected:
            detections.append({
                "tech_slug": sig.tech_slug,
                "tech_name": sig.tech_name,
                "category": sig.category,
                "confidence": sig.confidence,
                "method": method_used,
                "evidence": evidence[:500]
            })

    return detections
