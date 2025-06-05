"""
Prompts for website data extraction - CORRECTED VERSION
"""

# Simple and clear prompt for Hyperbrowser AI extraction
METADATA_AND_LINKS_EXTRACTION_PROMPT = """
Extract business information from the website at {TARGET_URL}.

Find and extract these specific details:

**COMPANY INFO:**
- company.name: The main company/organization name
- company.description: Company tagline or brief description  
- company.industry: Business sector (e.g. "Software", "Marketing", "Healthcare")
- company.location: Primary location (city, state/country)

**BRANDING:**
- favicon: Favicon URL (small icon in browser tab)
- logo.url: Main company logo image URL
- logo.alt_text: Logo alt text or description

**SOCIAL MEDIA:**
- social_profiles.linkedin: LinkedIn company page URL
- social_profiles.twitter: Twitter/X profile URL
- social_profiles.facebook: Facebook page URL  
- social_profiles.github: GitHub organization URL

**LEGAL PAGES:**
- legal_links.terms_of_service: Terms of Service page URL
- legal_links.privacy_policy: Privacy Policy page URL

**SEO INFO:**
- seo_data.meta_title: Page title tag content
- seo_data.meta_description: Meta description content
- seo_data.h1: Main H1 heading text

**SERVICES:**
- key_services: List of main services/products offered (max 5)
- color_palette: Primary brand colors in hex format (e.g. ["#FF0000", "#00FF00"])

**RULES:**
1. Only extract information clearly visible on the website
2. Use complete URLs, not relative paths
3. If information not found, leave field empty/null
4. Extract exact text, don't make up information
5. Focus on accuracy over completeness

Extract only what you can clearly see and identify on the website.
"""