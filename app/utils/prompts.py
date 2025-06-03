"""
Prompts for the extraction and other usages.
"""

# Detailed Hyperbrowser Extraction Prompt for business website data extraction
METADATA_AND_LINKS_EXTRACTION_PROMPT = """
Analyze the primary content and structure of the website at {TARGET_URL}.
Your goal is to extract comprehensive business information according to the schema provided.

**Extraction Instructions:**

1. **Branding Elements:**
   * Extract the company logo URL and alt text
   * Identify the favicon URL if available
   * Extract the website's primary color palette (hex codes)
   * Identify the brand fonts used (font family names)

2. **Company Profile:**
   * Extract the company name
   * Identify the company tagline or brief description
   * Determine the industry if mentioned
   * Extract the primary location and address information

3. **Site Links Analysis:**
   * Record the base domain URL
   * Analyze important links on the site, including:
     * For each link: relative URL, full URL, link text, source location, and category
   * Identify key pages such as:
     * About Us, Services/Solutions, Portfolio/Case Studies, Team, Pricing, Contact, Blog
   * Identify social profiles:
     * LinkedIn, Twitter/X, Facebook, GitHub, Crunchbase, Instagram
   * Identify legal links:
     * Terms of Service, Privacy Policy, Cookie Policy, Copyright information

4. **Basic SEO Elements:**
   * Extract meta title
   * Extract meta description
   * Extract H1 text if available
"""