#!/usr/bin/env python3
"""
Assembles Yogyakarta pages from Claude-generated editorial content.
Takes the homepage as template, replaces <main> with per-page content.
"""
import re, os, sys

SITE_DIR = os.path.expanduser("~/sites/yogyakarta-temple-tours")
DOMAIN = "https://www.yogyakarta-temple-tours.com"

def load_template():
    """Extract the HTML shell from homepage (everything outside <main>)."""
    with open(f"{SITE_DIR}/index.html") as f:
        html = f.read()
    
    # Extract head (before <main>) and footer (after </main>)
    head_end = html.find('<main id="main-content">')
    main_close = html.find('</main>')
    footer_start = html.find('<footer', main_close)
    
    shell_before = html[:head_end]
    shell_after = html[footer_start:]
    
    return shell_before, shell_after

def nav_with_active(slug):
    """Generate nav HTML with active class on the current page."""
    links = [
        ("/", "Home"),
        ("/borobudur", "Borobudur"),
        ("/prambanan", "Prambanan"),
        ("/merapi", "Merapi"),
        ("/caves", "Caves"),
        ("/cycling", "Cycling"),
        ("/food-tours", "Food"),
        ("/multi-day", "Multi-Day"),
        ("/planning", "Plan"),
        ("/about", "About"),
    ]
    nav_links = []
    for href, label in links:
        active = ' class="active"' if f"/{slug}" == href or (slug == "home" and href == "/") else ""
        nav_links.append(f'<a href="{href}"{active}>{label}</a>')
    
    return f"""<nav class="nav">
    <div class="nav-inner">
      <a class="nav-logo" href="/">Yogyakarta Temple Tours</a>
      <button class="hamburger" aria-label="Open menu" aria-expanded="false">☰</button>
      <div class="nav-links">
        {' '.join(nav_links)}
      </div>
    </div>
  </nav>"""

def head_block(title, description, og_title, og_desc, canonical, og_image):
    """Generate <head> block with per-page meta tags."""
    img_url = f"{DOMAIN}/images/og-{og_image}.jpg" if not og_image.startswith("http") else og_image
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>{title}</title>
  <meta name="description" content="{description}">
  <meta property="og:title" content="{og_title}">
  <meta property="og:description" content="{og_desc}">
  <meta property="og:url" content="{canonical}">
  <meta property="og:type" content="website">
  <meta property="og:image" content="{img_url}">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:image" content="{img_url}">
  <link rel="canonical" href="{canonical}">
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <link rel="icon" sizes="32x32" href="/images/favicon-32x32.png" type="image/png">
  <link rel="apple-touch-icon" href="/images/apple-touch-icon.png">
  <link rel="stylesheet" href="/css/style.css">
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-52JY0TL356"></script>
  <script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-52JY0TL356',{{'anonymize_ip':true}});</script>
</head>
<body>
  <a class="skip-link" href="#main-content">Skip to content</a>
"""

def footer_block():
    return """<footer class="footer">
    <div class="footer-inner">
      <div class="footer-col">
        <h4>Temples &amp; Volcanoes</h4>
        <a href="/borobudur">Borobudur</a>
        <a href="/prambanan">Prambanan</a>
        <a href="/merapi">Merapi</a>
        <a href="/borobudur-vs-prambanan">Borobudur vs Prambanan</a>
        <a href="/jeep-vs-hiking">Merapi: Jeep vs Hiking</a>
      </div>
      <div class="footer-col">
        <h4>Adventure &amp; Local</h4>
        <a href="/caves">Caves</a>
        <a href="/cycling">Cycling</a>
        <a href="/food-tours">Food Tours</a>
        <a href="/multi-day">Multi-Day Trips</a>
      </div>
      <div class="footer-col">
        <h4>Plan &amp; About</h4>
        <a href="/planning">Plan Your Trip</a>
        <a href="/about">About Rama</a>
        <a href="/contact">Contact</a>
        <a href="/privacy">Privacy</a>
      </div>
      <div class="footer-col">
        <h4>About this site</h4>
        <p>Honest, independent tour guides by Rama Kusuma — 20 years on these temples. No 'best', no sales pitch.</p>
      </div>
    </div>
    <div class="footer-bottom">
      <p>© 2026 Yogyakarta Temple Tours · Written in Sleman, on the slope of Merapi · Rama earns a commission on Viator bookings at no extra cost to you.</p>
    </div>
  </footer>
</body>
</html>"""

def article_jsonld(title, description, url, image_url):
    return f"""<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "{title}",
  "description": "{description}",
  "author": {{
    "@type": "Person",
    "name": "Rama Kusuma",
    "description": "Javanese temple guide, 20 years leading tours in Central Java",
    "url": "{DOMAIN}/about"
  }},
  "publisher": {{
    "@type": "Organization",
    "name": "Yogyakarta Temple Tours",
    "url": "{DOMAIN}",
    "logo": {{
      "@type": "ImageObject",
      "url": "{DOMAIN}/images/logo.png"
    }}
  }},
  "datePublished": "2026-06-15",
  "dateModified": "2026-06-15",
  "mainEntityOfPage": {{
    "@type": "WebPage",
    "@id": "{url}"
  }},
  "url": "{url}",
  "image": "{image_url}"
}}
</script>"""

# Page routing
PAGE_ROUTES = {
    "borobudur": "borobudur/index.html",
    "prambanan": "prambanan/index.html",
    "merapi": "merapi/index.html",
    "caves": "caves/index.html",
    "cycling": "cycling/index.html",
    "food-tours": "food-tours/index.html",
    "multi-day": "multi-day/index.html",
    "planning": "planning/index.html",
    "about": "about.html",
    "contact": "contact.html",
    "privacy": "privacy.html",
    "borobudur-vs-prambanan": "borobudur-vs-prambanan.html",
    "jeep-vs-hiking": "jeep-vs-hiking.html",
}

def assemble_page(slug, title, description, og_title, og_desc, canonical, og_image, main_content):
    """Assemble a complete page from components."""
    nav = nav_with_active(slug)
    # Fix Viator links in content
    main_content = main_content.replace('d5364-', 'd22560-')
    main_content = main_content.replace('rel="nofollow sponsored"', 'rel="sponsored noopener noreferrer"')
    
    head = head_block(title, description, og_title, og_desc, canonical, og_image)
    jsonld = article_jsonld(title, description, canonical, f"{DOMAIN}/images/og-{og_image}.jpg")
    
    # Insert JSON-LD before </head>
    head = head.replace('</head>', f'{jsonld}</head>')
    
    footer = footer_block()
    
    return f"""{head}
{nav}

{main_content}

{footer}"""

# Quick test
if __name__ == "__main__":
    print("Assembler ready. Run with: python3 assemble.py <claude_output.txt>")
    print(f"Pages will be written to: {SITE_DIR}")
