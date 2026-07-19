"""
Seed the database with initial domains to crawl.
Uses a curated list of popular websites across industries.
"""

import asyncio
import os
from crawler.db import get_pool, add_domains_batch, init_db, close_pool

# Curated seed domains across industries
SEED_DOMAINS = [
    # Tech / SaaS
    {"domain": "github.com", "industry": "Technology", "country": "US"},
    {"domain": "stackoverflow.com", "industry": "Technology", "country": "US"},
    {"domain": "gitlab.com", "industry": "Technology", "country": "US"},
    {"domain": "bitbucket.org", "industry": "Technology", "country": "US"},
    {"domain": "vercel.com", "industry": "Technology", "country": "US"},
    {"domain": "netlify.com", "industry": "Technology", "country": "US"},
    {"domain": "heroku.com", "industry": "Technology", "country": "US"},
    {"domain": "digitalocean.com", "industry": "Technology", "country": "US"},
    {"domain": "cloudflare.com", "industry": "Technology", "country": "US"},
    {"domain": "stripe.com", "industry": "Technology", "country": "US"},
    {"domain": "twilio.com", "industry": "Technology", "country": "US"},
    {"domain": "sendgrid.com", "industry": "Technology", "country": "US"},
    {"domain": "slack.com", "industry": "Technology", "country": "US"},
    {"domain": "notion.so", "industry": "Technology", "country": "US"},
    {"domain": "figma.com", "industry": "Technology", "country": "US"},
    {"domain": "linear.app", "industry": "Technology", "country": "US"},
    {"domain": "supabase.com", "industry": "Technology", "country": "US"},
    {"domain": "firebase.google.com", "industry": "Technology", "country": "US"},
    {"domain": "aws.amazon.com", "industry": "Technology", "country": "US"},
    {"domain": "cloud.google.com", "industry": "Technology", "country": "US"},
    {"domain": "azure.microsoft.com", "industry": "Technology", "country": "US"},
    {"domain": "docker.com", "industry": "Technology", "country": "US"},
    {"domain": "kubernetes.io", "industry": "Technology", "country": "US"},
    {"domain": "terraform.io", "industry": "Technology", "country": "US"},
    {"domain": "datadoghq.com", "industry": "Technology", "country": "US"},
    {"domain": "newrelic.com", "industry": "Technology", "country": "US"},
    {"domain": "sentry.io", "industry": "Technology", "country": "US"},
    {"domain": "logrocket.com", "industry": "Technology", "country": "US"},
    {"domain": "algolia.com", "industry": "Technology", "country": "US"},
    {"domain": "elastic.co", "industry": "Technology", "country": "US"},

    # E-commerce
    {"domain": "shopify.com", "industry": "E-commerce", "country": "CA"},
    {"domain": "woocommerce.com", "industry": "E-commerce", "country": "US"},
    {"domain": "bigcommerce.com", "industry": "E-commerce", "country": "US"},
    {"domain": "magento.com", "industry": "E-commerce", "country": "US"},
    {"domain": "etsy.com", "industry": "E-commerce", "country": "US"},
    {"domain": "ebay.com", "industry": "E-commerce", "country": "US"},
    {"domain": "amazon.com", "industry": "E-commerce", "country": "US"},
    {"domain": "walmart.com", "industry": "E-commerce", "country": "US"},
    {"domain": "target.com", "industry": "E-commerce", "country": "US"},
    {"domain": "bestbuy.com", "industry": "E-commerce", "country": "US"},
    {"domain": "wayfair.com", "industry": "E-commerce", "country": "US"},
    {"domain": "asos.com", "industry": "E-commerce", "country": "UK"},
    {"domain": "zara.com", "industry": "E-commerce", "country": "ES"},
    {"domain": "nike.com", "industry": "E-commerce", "country": "US"},
    {"domain": "adidas.com", "industry": "E-commerce", "country": "DE"},
    {"domain": "apple.com", "industry": "E-commerce", "country": "US"},
    {"domain": "samsung.com", "industry": "E-commerce", "country": "KR"},

    # Media / Content
    {"domain": "nytimes.com", "industry": "Media", "country": "US"},
    {"domain": "washingtonpost.com", "industry": "Media", "country": "US"},
    {"domain": "theguardian.com", "industry": "Media", "country": "UK"},
    {"domain": "bbc.com", "industry": "Media", "country": "UK"},
    {"domain": "cnn.com", "industry": "Media", "country": "US"},
    {"domain": "medium.com", "industry": "Media", "country": "US"},
    {"domain": "substack.com", "industry": "Media", "country": "US"},
    {"domain": "wordpress.com", "industry": "Media", "country": "US"},
    {"domain": "blogger.com", "industry": "Media", "country": "US"},
    {"domain": "tumblr.com", "industry": "Media", "country": "US"},
    {"domain": "reddit.com", "industry": "Media", "country": "US"},
    {"domain": "quora.com", "industry": "Media", "country": "US"},
    {"domain": "ycombinator.com", "industry": "Media", "country": "US"},
    {"domain": "producthunt.com", "industry": "Media", "country": "US"},
    {"domain": "techcrunch.com", "industry": "Media", "country": "US"},
    {"domain": "theverge.com", "industry": "Media", "country": "US"},
    {"domain": "wired.com", "industry": "Media", "country": "US"},
    {"domain": "buzzfeed.com", "industry": "Media", "country": "US"},
    {"domain": "vox.com", "industry": "Media", "country": "US"},
    {"domain": "vice.com", "industry": "Media", "country": "US"},

    # Social
    {"domain": "twitter.com", "industry": "Social", "country": "US"},
    {"domain": "facebook.com", "industry": "Social", "country": "US"},
    {"domain": "instagram.com", "industry": "Social", "country": "US"},
    {"domain": "linkedin.com", "industry": "Social", "country": "US"},
    {"domain": "pinterest.com", "industry": "Social", "country": "US"},
    {"domain": "tiktok.com", "industry": "Social", "country": "CN"},
    {"domain": "snapchat.com", "industry": "Social", "country": "US"},
    {"domain": "discord.com", "industry": "Social", "country": "US"},
    {"domain": "twitch.tv", "industry": "Social", "country": "US"},
    {"domain": "youtube.com", "industry": "Social", "country": "US"},
    {"domain": "vimeo.com", "industry": "Social", "country": "US"},
    {"domain": "spotify.com", "industry": "Social", "country": "SE"},
    {"domain": "soundcloud.com", "industry": "Social", "country": "DE"},

    # Finance
    {"domain": "paypal.com", "industry": "Finance", "country": "US"},
    {"domain": "squareup.com", "industry": "Finance", "country": "US"},
    {"domain": "wise.com", "industry": "Finance", "country": "UK"},
    {"domain": "plaid.com", "industry": "Finance", "country": "US"},
    {"domain": "robinhood.com", "industry": "Finance", "country": "US"},
    {"domain": "coinbase.com", "industry": "Finance", "country": "US"},
    {"domain": "binance.com", "industry": "Finance", "country": "KY"},
    {"domain": "kraken.com", "industry": "Finance", "country": "US"},

    # Marketing / SaaS
    {"domain": "hubspot.com", "industry": "Marketing", "country": "US"},
    {"domain": "mailchimp.com", "industry": "Marketing", "country": "US"},
    {"domain": "convertkit.com", "industry": "Marketing", "country": "US"},
    {"domain": "klaviyo.com", "industry": "Marketing", "country": "US"},
    {"domain": "intercom.com", "industry": "Marketing", "country": "US"},
    {"domain": "zendesk.com", "industry": "Marketing", "country": "US"},
    {"domain": "drift.com", "industry": "Marketing", "country": "US"},
    {"domain": "crisp.chat", "industry": "Marketing", "country": "FR"},
    {"domain": "calendly.com", "industry": "Marketing", "country": "US"},
    {"domain": "typeform.com", "industry": "Marketing", "country": "ES"},
    {"domain": "surveymonkey.com", "industry": "Marketing", "country": "US"},
    {"domain": "optimizely.com", "industry": "Marketing", "country": "US"},
    {"domain": "unbounce.com", "industry": "Marketing", "country": "CA"},
    {"domain": "instapage.com", "industry": "Marketing", "country": "US"},

    # Education
    {"domain": "coursera.org", "industry": "Education", "country": "US"},
    {"domain": "udemy.com", "industry": "Education", "country": "US"},
    {"domain": "khanacademy.org", "industry": "Education", "country": "US"},
    {"domain": "edx.org", "industry": "Education", "country": "US"},
    {"domain": "skillshare.com", "industry": "Education", "country": "US"},
    {"domain": "duolingo.com", "industry": "Education", "country": "US"},

    # Travel
    {"domain": "airbnb.com", "industry": "Travel", "country": "US"},
    {"domain": "booking.com", "industry": "Travel", "country": "NL"},
    {"domain": "expedia.com", "industry": "Travel", "country": "US"},
    {"domain": "tripadvisor.com", "industry": "Travel", "country": "US"},
    {"domain": "uber.com", "industry": "Travel", "country": "US"},
    {"domain": "lyft.com", "industry": "Travel", "country": "US"},

    # Food
    {"domain": "doordash.com", "industry": "Food", "country": "US"},
    {"domain": "ubereats.com", "industry": "Food", "country": "US"},
    {"domain": "grubhub.com", "industry": "Food", "country": "US"},
    {"domain": "postmates.com", "industry": "Food", "country": "US"},
    {"domain": "instacart.com", "industry": "Food", "country": "US"},

    # Health
    {"domain": "webmd.com", "industry": "Health", "country": "US"},
    {"domain": "healthline.com", "industry": "Health", "country": "US"},
    {"domain": "myfitnesspal.com", "industry": "Health", "country": "US"},
    {"domain": "headspace.com", "industry": "Health", "country": "US"},
    {"domain": "calm.com", "industry": "Health", "country": "US"},

    # More tech
    {"domain": "mongodb.com", "industry": "Technology", "country": "US"},
    {"domain": "redis.io", "industry": "Technology", "country": "US"},
    {"domain": "postgresql.org", "industry": "Technology", "country": "US"},
    {"domain": "mysql.com", "industry": "Technology", "country": "US"},
    {"domain": "sqlite.org", "industry": "Technology", "country": "US"},
    {"domain": "nginx.com", "industry": "Technology", "country": "US"},
    {"domain": "apache.org", "industry": "Technology", "country": "US"},
    {"domain": "djangoproject.com", "industry": "Technology", "country": "US"},
    {"domain": "rubyonrails.org", "industry": "Technology", "country": "US"},
    {"domain": "laravel.com", "industry": "Technology", "country": "US"},
    {"domain": "spring.io", "industry": "Technology", "country": "US"},
    {"domain": "expressjs.com", "industry": "Technology", "country": "US"},
    {"domain": "nextjs.org", "industry": "Technology", "country": "US"},
    {"domain": "nuxtjs.org", "industry": "Technology", "country": "US"},
    {"domain": "svelte.dev", "industry": "Technology", "country": "US"},
    {"domain": "react.dev", "industry": "Technology", "country": "US"},
    {"domain": "vuejs.org", "industry": "Technology", "country": "US"},
    {"domain": "angular.io", "industry": "Technology", "country": "US"},
    {"domain": "getbootstrap.com", "industry": "Technology", "country": "US"},
    {"domain": "tailwindcss.com", "industry": "Technology", "country": "US"},
    {"domain": "jquery.com", "industry": "Technology", "country": "US"},

    # Additional popular sites
    {"domain": "dropbox.com", "industry": "Technology", "country": "US"},
    {"domain": "box.com", "industry": "Technology", "country": "US"},
    {"domain": "zoom.us", "industry": "Technology", "country": "US"},
    {"domain": "webex.com", "industry": "Technology", "country": "US"},
    {"domain": "gotomeeting.com", "industry": "Technology", "country": "US"},
    {"domain": "meet.google.com", "industry": "Technology", "country": "US"},
    {"domain": "teams.microsoft.com", "industry": "Technology", "country": "US"},
    {"domain": "skype.com", "industry": "Technology", "country": "US"},
    {"domain": "telegram.org", "industry": "Technology", "country": "AE"},
    {"domain": "signal.org", "industry": "Technology", "country": "US"},
    {"domain": "whatsapp.com", "industry": "Technology", "country": "US"},
    {"domain": "messenger.com", "industry": "Technology", "country": "US"},
    {"domain": "wechat.com", "industry": "Technology", "country": "CN"},
    {"domain": "line.me", "industry": "Technology", "country": "JP"},
    {"domain": "viber.com", "industry": "Technology", "country": "JP"},
]


async def seed_database():
    """Seed the database with initial domains."""
    await init_db()

    print(f"[*] Seeding {len(SEED_DOMAINS)} domains...")
    await add_domains_batch(SEED_DOMAINS)

    print("[OK] Database seeded successfully!")
    print(f"   Total domains: {len(SEED_DOMAINS)}")
    print("   Run the crawler to start detecting technologies.")

    await close_pool()


if __name__ == "__main__":
    asyncio.run(seed_database())
