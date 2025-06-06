"""
Enhanced prompts for comprehensive website data extraction
"""

# Comprehensive prompt to match ideal output quality
METADATA_AND_LINKS_EXTRACTION_PROMPT = """
You are an expert website analyzer. Extract comprehensive business information from {TARGET_URL}.

**COMPANY INFORMATION:**
- company.name: The main company/organization name
- company.description: Company tagline, slogan, or brief description
- company.industry: Business sector (e.g., "Technology", "Software Development", "Marketing")
- company.location: Primary business location (city, state, country)
- company.address: Full street address if visible

**BRANDING & DESIGN:**
- favicon: URL of the website's favicon (browser tab icon)
- logo.url: Main company logo image URL
- logo.alt_text: Logo alt text or image description
- color_palette: Extract 3-6 primary brand colors in hex format (e.g., ["#FF0000", "#00FF00", "#0000FF"])
  * Look at header/footer backgrounds, button colors, accent colors, brand elements
  * Convert RGB values to hex format
- brand_fonts.primary: Main font family used for headings/branding (e.g., "Helvetica", "Arial", "Open Sans")
- brand_fonts.secondary: Secondary font family used for body text

**SOCIAL MEDIA PROFILES:**
- social_profiles.linkedin: LinkedIn company page URL
- social_profiles.twitter: Twitter/X profile URL  
- social_profiles.facebook: Facebook page URL
- social_profiles.instagram: Instagram profile URL
- social_profiles.github: GitHub organization URL
- social_profiles.youtube: YouTube channel URL
- social_profiles.crunchbase: Crunchbase company profile URL

**LEGAL & POLICY PAGES:**
- legal_links.terms_of_service: Terms of Service/Use page URL
- legal_links.privacy_policy: Privacy Policy page URL
- legal_links.copyright: Copyright or legal information page URL

**SEO & METADATA:**
- seo_data.meta_title: HTML <title> tag content
- seo_data.meta_description: Meta description tag content
- seo_data.h1: Main H1 heading text
- seo_data.h2: First H2 subheading text
- seo_data.keywords: Meta keywords if present

**NAVIGATION & LINKS:**
- link_analysis.base_domain: Extract base domain (e.g., "apple.com")
- link_analysis.links: Categorize navigation links as follows:
  * Category "main": Primary navigation (Products, Services, About, etc.)
  * Category "legal": Legal pages (Terms, Privacy, etc.)
  * Category "store": Shopping/store related links
  * Category "account": User account related links
  * Category "quick_links": Utility links (Contact, Support, etc.)
  * Category "business": Business-specific pages
  * Category "footer": Footer-only links
  * For each link include: url, full_url, link_text, source (header/footer/main), category, confidence_score (0.8-1.0)

**SERVICES & OFFERINGS:**
- key_services: List main services, products, or solutions offered (max 8 items)

**EXTRACTION GUIDELINES:**
1. **Color Extraction**: Analyze CSS styles, look for:
   - Header/footer background colors
   - Button colors and hover states  
   - Brand accent colors
   - Navigation element colors
   - Convert all colors to hex format (#RRGGBB)

2. **Font Detection**: Examine CSS font-family declarations:
   - Look at headings (h1, h2) for primary fonts
   - Check body text for secondary fonts
   - Extract actual font family names (not generic like "serif")

3. **Link Analysis**: Systematically categorize all navigation:
   - Main navigation in header
   - Footer links by section
   - Sidebar or secondary navigation
   - Assign appropriate categories and confidence scores

4. **Social Media**: Check multiple locations:
   - Footer social media icons/links
   - Header social links
   - About/Contact pages
   - Look for various social platforms

5. **Accuracy Rules**:
   - Only extract clearly visible information
   - Use complete URLs (not relative paths)
   - If information isn't found, set to null
   - Extract exact text content, don't paraphrase
   - Be precise with categorization

**TARGET OUTPUT QUALITY**: Aim for the comprehensiveness shown in major company websites (Apple, Google, etc.) - rich color palettes, detailed navigation analysis, complete social profiles, and accurate brand information.

Extract systematically and thoroughly to provide maximum business intelligence value.
"""




"""
Prompts for the extraction and other usages.
"""

# # Detailed Hyperbrowser Extraction Prompt for business website data extraction
# METADATA_AND_LINKS_EXTRACTION_PROMPT = """
# Analyze the primary content and structure of the website at {TARGET_URL}.
# Your goal is to extract comprehensive business information according to the schema provided.

# **Extraction Instructions:**

# 1. **Branding Elements:**
#    * Extract the company logo URL and alt text
#    * Identify the favicon URL if available
#    * Extract the website's primary color palette (hex codes)
#    * Identify the brand fonts used (font family names)

# 2. **Company Profile:**
#    * Extract the company name
#    * Identify the company tagline or brief description
#    * Determine the industry if mentioned
#    * Extract the primary location and address information

# 3. **Site Links Analysis:**
#    * Record the base domain URL
#    * Analyze important links on the site, including:
#      * For each link: relative URL, full URL, link text, source location, and category
#    * Identify key pages such as:
#      * About Us, Services/Solutions, Portfolio/Case Studies, Team, Pricing, Contact, Blog
#    * Identify social profiles:
#      * LinkedIn, Twitter/X, Facebook, GitHub, Crunchbase, Instagram
#    * Identify legal links:
#      * Terms of Service, Privacy Policy, Cookie Policy, Copyright information

# 4. **Basic SEO Elements:**
#    * Extract meta title
#    * Extract meta description
#    * Extract H1 text if available
# """