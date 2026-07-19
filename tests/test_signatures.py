import unittest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from crawler.signatures import detect_technologies


class TestSignatures(unittest.TestCase):
    """Unit tests for technology detection signatures."""

    def test_detect_google_analytics(self):
        """Test detection of Google Analytics from script source and inline content."""
        # 1. Script source detection (Google Analytics via gtag)
        headers = {}
        html = "<html><body></body></html>"
        scripts = ["https://www.googletagmanager.com/gtag/js?id=G-XXXXXX"]
        
        detections = detect_technologies(headers, html, scripts)
        tech_slugs = [d["tech_slug"] for d in detections]
        self.assertIn("google-analytics", tech_slugs)

        # Test Google Tag Manager detection via gtm.js
        scripts = ["https://www.googletagmanager.com/gtm.js?id=GTM-XXXXXX"]
        detections = detect_technologies(headers, html, scripts)
        tech_slugs = [d["tech_slug"] for d in detections]
        self.assertIn("google-tag-manager", tech_slugs)

        # 2. Inline content detection
        scripts = ["gtag('config', 'UA-123456-1');"]
        detections = detect_technologies(headers, html, scripts)
        tech_slugs = [d["tech_slug"] for d in detections]
        self.assertIn("google-analytics", tech_slugs)

    def test_detect_react_and_tailwind(self):
        """Test detection of React and Tailwind CSS from HTML content and class names."""
        headers = {}
        html = """
        <html>
            <head>
                <link href="/cdn/tailwind.css" rel="stylesheet">
            </head>
            <body>
                <div id="root" class="flex min-h-screen bg-slate-900 text-white md:flex-row">
                    <button class="btn-primary flex items-center justify-center">Click me</button>
                </div>
            </body>
        </html>
        """
        scripts = ["/static/js/react.production.min.js"]
        
        detections = detect_technologies(headers, html, scripts)
        tech_slugs = [d["tech_slug"] for d in detections]
        
        self.assertIn("react", tech_slugs)
        self.assertIn("tailwind-css", tech_slugs)
        self.assertIn("bootstrap", tech_slugs)  # class="btn-primary" matches bootstrap

    def test_detect_web_servers_from_headers(self):
        """Test detection of Nginx and Cloudflare from HTTP headers."""
        headers = {
            "Server": "nginx/1.24.0",
            "Content-Type": "text/html",
        }
        html = "<html></html>"
        scripts = []

        detections = detect_technologies(headers, html, scripts)
        tech_slugs = [d["tech_slug"] for d in detections]
        self.assertIn("nginx", tech_slugs)

        # Test Cloudflare header detection
        headers = {
            "CF-RAY": "8a5cfba97f4f6977-LHR",
            "Server": "cloudflare",
        }
        detections = detect_technologies(headers, html, scripts)
        tech_slugs = [d["tech_slug"] for d in detections]
        self.assertIn("cloudflare", tech_slugs)

    def test_edge_cases(self):
        """Test empty inputs, case sensitivity, and malformed inputs."""
        # Empty inputs
        self.assertEqual(detect_technologies({}, "", []), [])
        self.assertEqual(detect_technologies(None, None, None), [])

        # Case-insensitive headers
        headers = {"server": "NGINX"}
        detections = detect_technologies(headers, "<html></html>", [])
        tech_slugs = [d["tech_slug"] for d in detections]
        self.assertIn("nginx", tech_slugs)


if __name__ == "__main__":
    unittest.main()
