-- TechStack Scout Database Schema (SQLite Version)
-- Designed for local testing and lightweight development

-- Domains / Websites table
CREATE TABLE IF NOT EXISTS domains (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT UNIQUE NOT NULL,
    first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_crawled DATETIME,
    crawl_status TEXT DEFAULT 'pending',
    industry TEXT,
    country TEXT,
    page_title TEXT,
    http_status INTEGER,
    page_size_bytes INTEGER,
    server_header TEXT,
    meta_generator TEXT,
    ssl_issuer TEXT,
    crawl_count INTEGER DEFAULT 0,
    fail_count INTEGER DEFAULT 0
);

-- Technologies catalog
CREATE TABLE IF NOT EXISTS technologies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    slug TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    description TEXT,
    website_url TEXT,
    icon_url TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Technology detections (the core data)
CREATE TABLE IF NOT EXISTS tech_detections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain_id INTEGER NOT NULL REFERENCES domains(id) ON DELETE CASCADE,
    tech_id INTEGER NOT NULL REFERENCES technologies(id) ON DELETE CASCADE,
    detected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    confidence_score REAL DEFAULT 1.00,
    detection_method TEXT NOT NULL,
    evidence TEXT,
    UNIQUE(domain_id, tech_id, detection_method)
);

-- Crawl jobs queue
CREATE TABLE IF NOT EXISTS crawl_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain_id INTEGER NOT NULL REFERENCES domains(id) ON DELETE CASCADE,
    status TEXT DEFAULT 'pending',
    priority INTEGER DEFAULT 5,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    started_at DATETIME,
    completed_at DATETIME,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0
);

-- Crawl history / snapshots for trend detection
CREATE TABLE IF NOT EXISTS crawl_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain_id INTEGER NOT NULL REFERENCES domains(id) ON DELETE CASCADE,
    crawled_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    http_status INTEGER,
    page_title TEXT,
    headers TEXT, -- stored as JSON string
    technologies_found TEXT -- stored as comma-separated IDs or JSON
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_domains_status ON domains(crawl_status);
CREATE INDEX IF NOT EXISTS idx_domains_last_crawled ON domains(last_crawled);
CREATE INDEX IF NOT EXISTS idx_domains_domain ON domains(domain);

CREATE INDEX IF NOT EXISTS idx_tech_detections_domain ON tech_detections(domain_id);
CREATE INDEX IF NOT EXISTS idx_tech_detections_tech ON tech_detections(tech_id);
CREATE INDEX IF NOT EXISTS idx_tech_detections_method ON tech_detections(detection_method);
CREATE INDEX IF NOT EXISTS idx_tech_detections_detected_at ON tech_detections(detected_at);

CREATE INDEX IF NOT EXISTS idx_crawl_jobs_status ON crawl_jobs(status) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_crawl_jobs_domain ON crawl_jobs(domain_id);

CREATE INDEX IF NOT EXISTS idx_crawl_snapshots_domain ON crawl_snapshots(domain_id);
CREATE INDEX IF NOT EXISTS idx_crawl_snapshots_date ON crawl_snapshots(crawled_at);

-- SQLite view for leaderboard (standard view is fast enough for SQLite scale)
CREATE VIEW IF NOT EXISTS tech_leaderboard AS
SELECT 
    t.id,
    t.name,
    t.slug,
    t.category,
    COUNT(DISTINCT td.domain_id) as site_count,
    ROUND(
        CAST(COUNT(DISTINCT td.domain_id) AS REAL) / 
        NULLIF((SELECT COUNT(*) FROM domains WHERE crawl_status = 'crawled'), 0) * 100, 
        2
    ) as penetration_pct
FROM technologies t
LEFT JOIN tech_detections td ON t.id = td.tech_id
GROUP BY t.id, t.name, t.slug, t.category;

-- SQLite view for domain tech stacks
CREATE VIEW IF NOT EXISTS domain_tech_stacks AS
SELECT 
    d.id as domain_id,
    d.domain,
    d.page_title,
    d.last_crawled,
    COUNT(td.id) as tech_count,
    group_concat(DISTINCT t.name) as technologies,
    group_concat(DISTINCT t.category) as categories
FROM domains d
LEFT JOIN tech_detections td ON d.id = td.domain_id
LEFT JOIN technologies t ON td.tech_id = t.id
WHERE d.crawl_status = 'crawled'
GROUP BY d.id, d.domain, d.page_title, d.last_crawled;

-- Insert seed technologies
INSERT OR IGNORE INTO technologies (name, slug, category, description) VALUES
('Google Analytics', 'google-analytics', 'Analytics', 'Web analytics service by Google'),
('Google Tag Manager', 'google-tag-manager', 'Analytics', 'Tag management system'),
('Mixpanel', 'mixpanel', 'Analytics', 'Product analytics platform'),
('Amplitude', 'amplitude', 'Analytics', 'Product analytics and event tracking'),
('Segment', 'segment', 'Analytics', 'Customer data platform'),
('Hotjar', 'hotjar', 'Analytics', 'Behavior analytics and feedback'),
('Cloudflare', 'cloudflare', 'CDN', 'CDN, DNS, and security services'),
('Fastly', 'fastly', 'CDN', 'Edge cloud platform and CDN'),
('AWS CloudFront', 'aws-cloudfront', 'CDN', 'Amazon content delivery network'),
('Akamai', 'akamai', 'CDN', 'Content delivery and cloud services'),
('React', 'react', 'Frontend Framework', 'JavaScript library for UI'),
('Vue.js', 'vuejs', 'Frontend Framework', 'Progressive JavaScript framework'),
('Angular', 'angular', 'Frontend Framework', 'Platform for building mobile and desktop web applications'),
('Next.js', 'nextjs', 'Frontend Framework', 'React framework for production'),
('Nuxt.js', 'nuxtjs', 'Frontend Framework', 'Vue framework for production'),
('Svelte', 'svelte', 'Frontend Framework', 'Cybernetically enhanced web apps'),
('jQuery', 'jquery', 'Frontend Framework', 'Fast, small, feature-rich JavaScript library'),
('Bootstrap', 'bootstrap', 'CSS Framework', 'Popular CSS framework'),
('Tailwind CSS', 'tailwind-css', 'CSS Framework', 'Utility-first CSS framework'),
('WordPress', 'wordpress', 'CMS', 'Open source content management system'),
('Drupal', 'drupal', 'CMS', 'Open source CMS platform'),
('Joomla', 'joomla', 'CMS', 'Content management system'),
('Shopify', 'shopify', 'E-commerce', 'E-commerce platform'),
('WooCommerce', 'woocommerce', 'E-commerce', 'WordPress e-commerce plugin'),
('Magento', 'magento', 'E-commerce', 'Adobe e-commerce platform'),
('Stripe', 'stripe', 'Payment', 'Online payment processing'),
('PayPal', 'paypal', 'Payment', 'Online payments system'),
('Nginx', 'nginx', 'Web Server', 'High-performance web server'),
('Apache', 'apache', 'Web Server', 'Open source web server'),
('Microsoft IIS', 'microsoft-iis', 'Web Server', 'Internet Information Services'),
('Express.js', 'expressjs', 'Backend Framework', 'Fast, unopinionated web framework for Node.js'),
('Django', 'django', 'Backend Framework', 'High-level Python web framework'),
('Ruby on Rails', 'ruby-on-rails', 'Backend Framework', 'Server-side web application framework'),
('Laravel', 'laravel', 'Backend Framework', 'PHP web application framework'),
('Spring', 'spring', 'Backend Framework', 'Java application framework'),
('ASP.NET', 'aspnet', 'Backend Framework', 'Web framework for .NET'),
('Node.js', 'nodejs', 'Runtime', 'JavaScript runtime environment'),
('PHP', 'php', 'Runtime', 'Server-side scripting language'),
('Python', 'python', 'Runtime', 'Programming language'),
('Ruby', 'ruby', 'Runtime', 'Dynamic, open source programming language'),
('Go', 'go', 'Runtime', 'Statically typed, compiled programming language'),
('HubSpot', 'hubspot', 'Marketing', 'Inbound marketing and sales software'),
('Mailchimp', 'mailchimp', 'Marketing', 'Email marketing platform'),
('Intercom', 'intercom', 'Customer Support', 'Customer messaging platform'),
('Zendesk', 'zendesk', 'Customer Support', 'Customer service software'),
('Drift', 'drift', 'Customer Support', 'Conversational marketing platform'),
('AWS', 'aws', 'Cloud Infrastructure', 'Amazon Web Services'),
('Google Cloud', 'google-cloud', 'Cloud Infrastructure', 'Google Cloud Platform'),
('Azure', 'azure', 'Cloud Infrastructure', 'Microsoft Azure'),
('Heroku', 'heroku', 'Cloud Infrastructure', 'Cloud platform as a service'),
('Vercel', 'vercel', 'Cloud Infrastructure', 'Frontend cloud platform'),
('Netlify', 'netlify', 'Cloud Infrastructure', 'Web development and hosting platform'),
('Firebase', 'firebase', 'Backend-as-a-Service', 'Google app development platform'),
('Supabase', 'supabase', 'Backend-as-a-Service', 'Open source Firebase alternative'),
('MongoDB', 'mongodb', 'Database', 'Document-oriented NoSQL database'),
('PostgreSQL', 'postgresql', 'Database', 'Open source relational database'),
('MySQL', 'mysql', 'Database', 'Open source relational database'),
('Redis', 'redis', 'Database', 'In-memory data structure store'),
('Elasticsearch', 'elasticsearch', 'Search', 'Distributed search and analytics engine'),
('Algolia', 'algolia', 'Search', 'Search and discovery API platform'),
('Google Fonts', 'google-fonts', 'Font', 'Library of free licensed font families'),
('Typekit', 'typekit', 'Font', 'Adobe font subscription service'),
('Font Awesome', 'font-awesome', 'Icon', 'Icon library and toolkit'),
('Cloudinary', 'cloudinary', 'Media', 'Cloud-based image and video management'),
('Imgix', 'imgix', 'Media', 'Real-time image processing and CDN'),
('Sentry', 'sentry', 'Monitoring', 'Application monitoring and error tracking'),
('New Relic', 'new-relic', 'Monitoring', 'Application performance monitoring'),
('Datadog', 'datadog', 'Monitoring', 'Cloud monitoring and security platform'),
('Docker', 'docker', 'DevOps', 'Containerization platform'),
('Kubernetes', 'kubernetes', 'DevOps', 'Container orchestration system'),
('Terraform', 'terraform', 'DevOps', 'Infrastructure as code tool'),
('GitHub', 'github', 'DevOps', 'Code hosting platform'),
('GitLab', 'gitlab', 'DevOps', 'DevOps platform'),
('Slack', 'slack', 'Communication', 'Business communication platform'),
('Discord', 'discord', 'Communication', 'Voice, video and text communication'),
('Twitter/X', 'twitter', 'Social', 'Social networking service'),
('Facebook', 'facebook', 'Social', 'Social media platform'),
('LinkedIn', 'linkedin', 'Social', 'Professional networking platform'),
('YouTube', 'youtube', 'Media', 'Video sharing platform'),
('Vimeo', 'vimeo', 'Media', 'Video hosting platform'),
('Figma', 'figma', 'Design', 'Interface design tool'),
('Sketch', 'sketch', 'Design', 'Digital design toolkit'),
('Adobe Analytics', 'adobe-analytics', 'Analytics', 'Adobe marketing analytics'),
('Optimizely', 'optimizely', 'A/B Testing', 'Experimentation platform'),
('Google Optimize', 'google-optimize', 'A/B Testing', 'Website optimization tool'),
('Cookiebot', 'cookiebot', 'Compliance', 'Cookie consent management'),
('OneTrust', 'onetrust', 'Compliance', 'Privacy and consent management'),
('reCAPTCHA', 'recaptcha', 'Security', 'Google security service'),
('hCaptcha', 'hcaptcha', 'Security', 'Bot detection service');
