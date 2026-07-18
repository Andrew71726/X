#!/usr/bin/env python3
import os
import sys
import json
import datetime
import re
import subprocess
import xml.etree.ElementTree as ET

# ---------------------------------------------------------------------------
# 1. Self-Installation of Dependencies
# ---------------------------------------------------------------------------
def setup_dependencies():
    """Ensure all required Python packages are installed."""
    packages = [
        ("google-genai", "google.genai"),
        ("markdown", "markdown")
    ]
    installed_any = False
    for pkg, imp in packages:
        try:
            __import__(imp)
        except ImportError:
            print(f"[Setup] Installing missing package '{pkg}'...", flush=True)
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "--break-system-packages"])
                print(f"[Setup] Successfully installed '{pkg}'", flush=True)
                installed_any = True
            except Exception as e:
                print(f"[Setup] Error: Failed to install '{pkg}': {e}", flush=True)
                print(f"[Setup] Please install it manually: pip install {pkg}", flush=True)
    if installed_any:
        print("[Setup] Dependencies verified. Restarting script module loaders...", flush=True)

# Run setup first before importing anything from external packages
setup_dependencies()

# Now safely import external libraries
try:
    import markdown
    from google import genai
    from google.genai import types
except ImportError as err:
    print(f"\n[Fatal Error] Failed to import dependencies: {err}", file=sys.stderr)
    print("Please make sure you have installed 'google-genai' and 'markdown' packages.", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# 2. Curated Programmatic SEO Niche Topics (Rotating list / fallbacks)
# ---------------------------------------------------------------------------
SUGGESTED_TOPICS = [
    {
        "topic": "Programmatic SEO: Scaling Passive Affiliate Income with Tens of Thousands of Long-Tail Pages",
        "keywords": "programmatic seo, affiliate income, static sites, scale, long-tail keywords",
        "category": "Strategy"
    },
    {
        "topic": "Zero Cost Static Hosting: Moving From Expensive WordPress to Free GitHub Pages and Cloudflare",
        "keywords": "static hosting, wordpress migration, github pages, hosting costs, speed optimization",
        "category": "Strategy"
    },
    {
        "topic": "Core Web Vitals and Search Rankings: The Speed Advantage of Static HTML vs Heavy CMS Core Systems",
        "keywords": "core web vitals, pagespeed, static html, seo rankings, website performance",
        "category": "SEO"
    },
    {
        "topic": "Structured Schema Markup: Integrating Advanced Article and FAQ JSON-LD on Pure Static Sites",
        "keywords": "schema markup, structured data, json-ld, static site seo, google snippets",
        "category": "SEO"
    },
    {
        "topic": "Automated Low-Competition Keyword Discovery: How to Uncover Hidden High-Volume Search Gems",
        "keywords": "keyword research, low competition keywords, niche selection, buyer intent, seo strategy",
        "category": "Research"
    },
    {
        "topic": "Niche Monetization Architectures: Building High-Converting Affiliate & Display Ad Static Templates",
        "keywords": "niche monetization, display ads, affiliate marketing, passive income, static template optimization",
        "category": "Research"
    },
    {
        "topic": "Automating Local Landing Pages: Creating High-Ranking Programmatic Geo-Targeted HTML Directories",
        "keywords": "local seo, programmatic directories, geo-targeted pages, static html generator, local leads",
        "category": "Automation"
    },
    {
        "topic": "Secure Static Sites: Eliminating SQL Injection, Database Exploits, and Brute-Force CMS Hacks",
        "keywords": "static site security, database exploits, secure blog, cms security, web safety",
        "category": "Automation"
    }
]

CATEGORY_IMAGES = {
    "Strategy": "https://images.unsplash.com/photo-1434626881859-194d67b2b86f?w=1200&auto=format&fit=crop&q=80",
    "SEO": "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=1200&auto=format&fit=crop&q=80",
    "Research": "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=1200&auto=format&fit=crop&q=80",
    "Automation": "https://images.unsplash.com/photo-1485827404703-89b55fcc595e?w=1200&auto=format&fit=crop&q=80",
    "Default": "https://images.unsplash.com/photo-1557804506-669a67965ba0?w=1200&auto=format&fit=crop&q=80"
}

# ---------------------------------------------------------------------------
# 3. Helper Functions
# ---------------------------------------------------------------------------
def slugify(text):
    """Convert text to a secure, URL-friendly slug."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s-]+', '-', text)
    return text.strip('-')

def get_existing_slugs():
    """List all slugs generated inside the posts/ directory."""
    posts_dir = "posts"
    if not os.path.exists(posts_dir):
        return set()
    slugs = set()
    for filename in os.listdir(posts_dir):
        if filename.endswith(".html"):
            slugs.add(filename[:-5])
    return slugs

def select_topic_and_metadata():
    """
    Select the next topic to generate based on environment variables
    or rotating through non-generated curated topics.
    """
    # Allow overrides via environment variables (perfect for GitHub Actions workflows)
    env_topic = os.environ.get("ARTICLE_TOPIC")
    env_keywords = os.environ.get("ARTICLE_KEYWORDS")
    env_category = os.environ.get("ARTICLE_CATEGORY", "SEO")
    
    if env_topic:
        print(f"[Topic Selector] Using article topic from environment variable: '{env_topic}'")
        return {
            "topic": env_topic,
            "keywords": env_keywords or "seo, static site, niche, marketing",
            "category": env_category
        }
        
    existing_slugs = get_existing_slugs()
    print(f"[Topic Selector] Detected {len(existing_slugs)} existing articles in '/posts' directory.")
    
    # Try to find a curated topic that hasn't been written yet
    for entry in SUGGESTED_TOPICS:
        slug = slugify(entry["topic"])
        if slug not in existing_slugs:
            print(f"[Topic Selector] Selected curated topic: '{entry['topic']}' (Slug: {slug})")
            return entry
            
    # All curated topics exist, return a random or fallback one with a randomized keyword
    # OR we can let the caller know to generate a completely new topic using Gemini
    print("[Topic Selector] All curated topics have already been published. Generating a brand new unique topic...")
    return None

def update_sitemap(slug, publish_date):
    """
    Safely parse and insert a new post URL to /sitemap.xml.
    Prevents duplicates, keeps correct XML formatting and pretty indent.
    """
    sitemap_path = "sitemap.xml"
    if not os.path.exists(sitemap_path):
        print(f"[Sitemap] Warning: {sitemap_path} does not exist. Skipping sitemap update.")
        return
        
    try:
        ET.register_namespace('', "http://www.sitemaps.org/schemas/sitemap/0.9")
        tree = ET.parse(sitemap_path)
        root = tree.getroot()
        
        target_loc = f"https://nicheblog.example.com/posts/{slug}.html"
        ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
        
        # Check if URL already exists
        for url_node in root.findall(f"{ns}url"):
            loc_node = url_node.find(f"{ns}loc")
            if loc_node is not None and loc_node.text == target_loc:
                print(f"[Sitemap] URL already exists in sitemap: '{target_loc}'. Updating lastmod to {publish_date}.")
                lastmod_node = url_node.find(f"{ns}lastmod")
                if lastmod_node is not None:
                    lastmod_node.text = publish_date
                else:
                    new_lastmod = ET.SubElement(url_node, f"{ns}lastmod")
                    new_lastmod.text = publish_date
                tree.write(sitemap_path, encoding="utf-8", xml_declaration=True)
                return
                
        # Append new URL node
        url_node = ET.SubElement(root, f"{ns}url")
        
        loc_node = ET.SubElement(url_node, f"{ns}loc")
        loc_node.text = target_loc
        
        lastmod_node = ET.SubElement(url_node, f"{ns}lastmod")
        lastmod_node.text = publish_date
        
        changefreq_node = ET.SubElement(url_node, f"{ns}changefreq")
        changefreq_node.text = "monthly"
        
        priority_node = ET.SubElement(url_node, f"{ns}priority")
        priority_node.text = "0.8"
        
        # Helper for pretty print indentation
        def indent(elem, level=0):
            i = "\n" + level*"  "
            if len(elem):
                if not elem.text or not elem.text.strip():
                    elem.text = i + "  "
                if not elem.tail or not elem.tail.strip():
                    elem.tail = i
                for sub_elem in elem:
                    indent(sub_elem, level+1)
                if not elem.tail or not elem.tail.strip():
                    elem.tail = i
            else:
                if level and (not elem.tail or not elem.tail.strip()):
                    elem.tail = i
                    
        indent(root)
        tree.write(sitemap_path, encoding="utf-8", xml_declaration=True)
        print(f"[Sitemap] Successfully added '{target_loc}' to {sitemap_path}")
    except Exception as e:
        print(f"[Sitemap] Error updating sitemap: {e}")

# ---------------------------------------------------------------------------
# 4. Core Blog Generator Logic
# ---------------------------------------------------------------------------
def run_generator():
    """Main execution function to connect to Gemini API and publish an article."""
    print("=========================================================")
    print("✨ Static Passive Income Blog - Automated SEO Publisher ✨")
    print("=========================================================")
    
    # 1. Fetch Gemini API Key
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("\n[Fatal Error] GEMINI_API_KEY environment variable is not defined.", file=sys.stderr)
        print("Please set your API key in your environment or repository secrets before running.", file=sys.stderr)
        print("Example: export GEMINI_API_KEY='your_key_here'\n", file=sys.stderr)
        sys.exit(1)
        
    # 2. Select the Topic
    selected_meta = select_topic_and_metadata()
    
    # Initialize the Google GenAI Client
    try:
        client = genai.Client(
            api_key=api_key,
            http_options={"headers": {"User-Agent": "aistudio-build"}}
        )
    except Exception as e:
        print(f"[Fatal Error] Failed to initialize Google GenAI Client: {e}", file=sys.stderr)
        sys.exit(1)
        
    # If all curated topics are used, query Gemini to give us a brand new topic
    if selected_meta is None:
        print("[Gemini] Brainstorming a completely unique, new niche SEO/Passive Income topic...")
        brainstorm_prompt = (
            "Suggest a highly specific, low-competition, high-value transactional keyword topic "
            "for an authority blog about Passive Income, Static Web Development, Automated SEO, "
            "and Programmatic Site Monetization. The topic must be different from: "
            + ", ".join([f"'{item['topic']}'" for item in SUGGESTED_TOPICS]) + ".\n\n"
            "Respond ONLY with a valid JSON object containing exactly these fields:\n"
            "{\n"
            '  "topic": "The exact title/topic for the article",\n'
            '  "keywords": "comma-separated SEO keywords",\n'
            '  "category": "One of: Strategy, SEO, Research, Automation"\n'
            "}"
        )
        try:
            response = client.models.generate_content(
                model="gemini-3.5-flash",
                contents=brainstorm_prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            data = json.loads(response.text.strip())
            selected_meta = {
                "topic": data.get("topic"),
                "keywords": data.get("keywords", "seo, static, passive income"),
                "category": data.get("category", "SEO")
            }
            print(f"[Gemini] Successfully brainstormed new topic: '{selected_meta['topic']}'")
        except Exception as e:
            print(f"[Error] Failed brainstorming new topic. Falling back to default curated topic. Error: {e}")
            selected_meta = SUGGESTED_TOPICS[0]

    # Clean Slug and Dates
    slug = slugify(selected_meta["topic"])
    publish_date = datetime.date.today().isoformat()
    formatted_date_display = datetime.date.today().strftime("%B %d, %Y")
    
    # 3. Request Gemini to write the high-quality article
    print(f"[Gemini] Generating full professional article on: '{selected_meta['topic']}'...")
    system_instruction = (
        "You are an expert full-stack developer, programmatic SEO architect, and niche site monetization researcher. "
        "Your style is highly authoritative, analytical, and professional, blending clear explanations with technical rigor. "
        "You write comprehensive, long-form articles (minimum 1000 words) packed with technical detail, real-world math, "
        "highly educational structured code snippets, config files, schema implementations, and academic or expert references. "
        "Avoid generic fluff, introductory paragraphs that say 'In this article we will...', and typical AI filler phrases. "
        "Directly address the mechanics of scaling niche publications and static sites for passive affiliate income."
    )
    
    article_prompt = f"""
    Please write a comprehensive authority SEO blog post about the following topic:
    Topic: "{selected_meta['topic']}"
    Target SEO Keywords: "{selected_meta['keywords']}"
    Category: "{selected_meta['category']}"
    
    Requirements:
    1. The article MUST include at least 2-3 genuine, credible academic references, scientific studies, or industry authority research reports (e.g., studies on web performance, Google Search quality raters guidelines, Ahrefs/Backlinko search intent reports, or ACM digital library web performance studies) naturally cited within the body of the article.
    2. End the article with a professional bibliography section titled "Academic References & Citations".
    3. Include at least 1-2 highly educational code blocks (e.g. detailed Python script snippets, Nginx caching configs, custom robots.txt structure, JSON-LD Schema structures, or GitHub Actions YAML workflow templates) that align with the topic.
    4. Provide an SEO-optimized meta description (under 160 characters).
    5. Provide an estimated reading time (e.g. "7 min read", "10 min read").
    
    Respond ONLY with a valid JSON object matching this exact schema:
    {{
      "title": "A catchy, SEO-optimized title for the article",
      "description": "An optimized meta description for search engine ranking (under 160 characters)",
      "reading_time": "Estimated reading time (e.g., '8 min read')",
      "markdown_content": "The complete full-length body content in clean, rich Markdown (including headings, paragraphs, lists, citations, code blocks, and the bibliography section)"
    }}
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=article_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                temperature=0.8
            )
        )
        
        result_json = json.loads(response.text.strip())
        title = result_json.get("title", selected_meta["topic"])
        description = result_json.get("description", "A highly professional technical article on static niche monetization.")
        reading_time = result_json.get("reading_time", "6 min read")
        markdown_body = result_json.get("markdown_content", "")
        
        if not markdown_body:
            raise ValueError("No markdown content was returned from Gemini API.")
            
        print("[Gemini] Generation successful! Formatting output page...")
        
        # 4. Convert Markdown body to structured HTML
        html_body = markdown.markdown(markdown_body, extensions=['fenced_code', 'codehilite'])
        
        # Determine cover image URL
        cover_image = CATEGORY_IMAGES.get(selected_meta["category"], CATEGORY_IMAGES["Default"])
        
        # Get category initials for author badge
        author_initials = "AM"
        author_name = "Alex Mercer"
        author_role = "SEO Architect" if selected_meta["category"] == "SEO" else "Niche Researcher"
        
        # 5. Build static HTML page from template
        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} - Static SEO Blog</title>
  <meta name="description" content="{description}">
  <meta name="author" content="{author_name}">
  <meta name="publish-date" content="{publish_date}">
  <meta name="category" content="{selected_meta['category']}">
  <meta name="reading-time" content="{reading_time}">
  <meta name="cover-image" content="{cover_image}">
  
  <!-- Tailwind CSS compiler link -->
  <link rel="stylesheet" href="../index.css">
  <!-- Tailwind CDN for direct/standalone viewing support -->
  <script src="https://unpkg.com/@tailwindcss/browser@4"></script>
</head>
<body class="bg-slate-50 text-slate-900 antialiased font-sans selection:bg-indigo-100 selection:text-indigo-900">

  <!-- Navigation -->
  <nav class="sticky top-0 z-50 bg-white/90 backdrop-blur-md border-b border-slate-200/80 px-6 py-4 shadow-sm">
    <div class="max-w-4xl mx-auto flex items-center justify-between">
      <a href="../index.html" class="group flex items-center gap-2">
        <span class="inline-flex items-center justify-center w-8 h-8 rounded-lg bg-indigo-600 text-white font-bold text-sm shadow-sm group-hover:bg-indigo-700 transition-colors">S</span>
        <span class="font-bold tracking-tight text-slate-800 group-hover:text-indigo-600 transition-colors">Static SEO Blog</span>
      </a>
      <div class="flex items-center gap-6">
        <a href="../index.html" class="text-sm font-medium text-slate-600 hover:text-indigo-600 transition-colors">All Articles</a>
        <a href="#newsletter" class="px-4 py-1.5 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-all shadow-sm">Subscribe</a>
      </div>
    </div>
  </nav>

  <!-- Article Header -->
  <header class="max-w-3xl mx-auto px-6 pt-12 pb-8">
    <div class="flex items-center gap-3 mb-6">
      <span class="px-2.5 py-1 text-xs font-semibold tracking-wide text-indigo-700 bg-indigo-50 border border-indigo-100/80 rounded-full uppercase">{selected_meta['category']}</span>
      <span class="text-sm text-slate-500 font-mono">{formatted_date_display}</span>
    </div>
    
    <h1 class="text-4xl sm:text-5xl font-extrabold tracking-tight text-slate-900 mb-6 leading-tight">
      {title}
    </h1>
    
    <p class="text-xl text-slate-600 font-serif leading-relaxed mb-8">
      {description}
    </p>

    <!-- Author & Meta Info -->
    <div class="flex items-center gap-4 border-y border-slate-200 py-4">
      <div class="w-10 h-10 rounded-full bg-slate-100 overflow-hidden flex items-center justify-center font-bold text-slate-600 border border-slate-200">
        {author_initials}
      </div>
      <div>
        <div class="text-sm font-bold text-slate-900">{author_name}</div>
        <div class="text-xs text-slate-500 flex items-center gap-2">
          <span>{reading_time}</span>
          <span>•</span>
          <span>{author_role}</span>
        </div>
      </div>
    </div>
  </header>

  <!-- Featured Image -->
  <figure class="max-w-4xl mx-auto px-6 mb-12">
    <div class="aspect-video w-full rounded-2xl overflow-hidden shadow-md">
      <img src="{cover_image}" alt="{title}" class="w-full h-full object-cover">
    </div>
    <figcaption class="text-center text-xs text-stone-400 mt-3 font-mono">
      {selected_meta['category']} Authority Series: Citations, data-backed proof, and technical blueprints.
    </figcaption>
  </figure>

  <!-- Article Content -->
  <main class="max-w-3xl mx-auto px-6 pb-20">
    <article class="markdown-content">
      {html_body}
    </article>

    <!-- Social Share & Return -->
    <div class="flex flex-col sm:flex-row items-center justify-between border-t border-slate-200 mt-12 pt-8 gap-4">
      <a href="../index.html" class="flex items-center gap-2 text-sm font-medium text-indigo-600 hover:text-indigo-800 transition-colors">
        ← Back to Homepage
      </a>
      <div class="flex items-center gap-3">
        <span class="text-xs text-slate-400 font-mono">Share:</span>
        <button onclick="window.open('https://twitter.com/share?url=' + encodeURIComponent(window.location.href), '_blank')" class="p-1.5 rounded-md hover:bg-slate-200 text-slate-600 transition-colors cursor-pointer">
          Share on X
        </button>
      </div>
    </div>
  </main>

  <!-- Newsletter Section -->
  <section id="newsletter" class="bg-slate-900 text-slate-100 py-16 px-6">
    <div class="max-w-2xl mx-auto text-center">
      <span class="text-xs font-bold uppercase tracking-widest text-indigo-400 mb-2 block">Newsletter</span>
      <h3 class="text-3xl font-extrabold tracking-tight mb-4">Build Your Static Income Engine</h3>
      <p class="text-slate-300 mb-8 max-w-lg mx-auto">
        Join 10,000+ developers receiving weekly case studies, automated script blueprints, and profitable niche keyword ideas.
      </p>
      
      <div id="newsletter-form-container">
        <form id="subscribe-form" class="flex flex-col sm:flex-row items-stretch gap-3 max-w-md mx-auto">
          <input type="email" placeholder="Enter your email" required class="flex-1 px-4 py-3 rounded-lg bg-slate-800 border border-slate-700 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm">
          <button type="submit" class="px-6 py-3 font-semibold text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors text-sm shadow-sm cursor-pointer">
            Subscribe Free
          </button>
        </form>
      </div>
      
      <div id="success-message" class="hidden max-w-md mx-auto p-4 bg-slate-800 border border-indigo-500/30 rounded-lg text-indigo-400 text-sm font-medium">
        🎉 Thank you! You've been successfully subscribed.
      </div>
    </div>
  </section>

  <!-- Footer -->
  <footer class="bg-slate-950 text-slate-500 text-xs py-8 text-center border-t border-slate-900">
    <p>© 2026 Static SEO Blog. All rights reserved.</p>
    <p class="mt-2 text-slate-700">Lightweight • Fast • Highly Monetizable</p>
  </footer>

  <script>
    // Handle newsletter subscription
    document.getElementById('subscribe-form')?.addEventListener('submit', function(e) {{
      e.preventDefault();
      document.getElementById('subscribe-form').classList.add('hidden');
      document.getElementById('success-message').classList.remove('hidden');
    }});
  </script>
</body>
</html>
"""
        # Ensure posts directory exists
        os.makedirs("posts", exist_ok=True)
        
        output_path = f"posts/{slug}.html"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_template)
            
        print(f"[Publisher] Successfully wrote generated HTML post to: '{output_path}'")
        
        # 6. Update sitemap
        update_sitemap(slug, publish_date)
        
        print("\n🎉 Article successfully compiled and integrated! The static homepage scanner will load it automatically.\n")
        
    except Exception as e:
        print(f"\n[Fatal Error] Content generation or publishing failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

# ---------------------------------------------------------------------------
# 5. CLI Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    run_generator()
