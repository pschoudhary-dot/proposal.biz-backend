# """
# Enhanced schemas for website data extraction.
# """
# from typing import List, Optional
# from pydantic import BaseModel, Field, HttpUrl
# # from uuid import UUID


# class Logo(BaseModel):
#     """Schema for logo information"""
#     url: str = Field(..., description="URL of the logo image")
#     alt_text: str = Field(..., description="Alternative text for the logo")


# class BrandFonts(BaseModel):
#     """Schema for brand typography"""
#     primary: str = Field(..., description="Primary font family")
#     secondary: str = Field(..., description="Secondary font family")


# class CompanyInfo(BaseModel):
#     """Schema for company details"""
#     name: str = Field(..., description="Company name")
#     description: Optional[str] = Field(None, description="Company description or tagline")
#     industry: Optional[str] = Field(None, description="Industry sector")
#     location: Optional[str] = Field(None, description="City and state/country")
#     address: Optional[str] = Field(None, description="Full street address")


# class LegalLinks(BaseModel):
#     """Schema for legal documentation links"""
#     terms_of_service: Optional[str] = Field(None, description="Terms of service URL")
#     privacy_policy: Optional[str] = Field(None, description="Privacy policy URL")
#     copyright: Optional[str] = Field(None, description="Copyright information URL")

# class SocialProfiles(BaseModel):
#     """Schema for social media presence"""
#     linkedin: Optional[str] = Field(None, description="LinkedIn company profile")
#     twitter: Optional[str] = Field(None, description="Twitter/X profile")
#     facebook: Optional[str] = Field(None, description="Facebook page")
#     instagram: Optional[str] = Field(None, description="Instagram profile")
#     crunchbase: Optional[str] = Field(None, description="Crunchbase profile")
#     github: Optional[str] = Field(None, description="GitHub organization")
#     youtube: Optional[str] = Field(None, description="YouTube channel")

# # class SocialProfiles(BaseModel):
# #     """Schema for a single social media profile"""
# #     platform: str = Field(..., description="Social media platform (e.g., 'LinkedIn')")
# #     url: str = Field(..., description="Profile URL")

# class SEOData(BaseModel):
#     """Schema for SEO metadata"""
#     meta_title: Optional[str] = Field(None, description="Page meta title")
#     meta_description: Optional[str] = Field(None, description="Page meta description")
#     h1: Optional[str] = Field(None, description="Main heading")
#     h2: Optional[str] = Field(None, description="Subheading")
#     keywords: Optional[List[str]] = Field(None, description="List of keywords")


# class Link(BaseModel):
#     """Individual link information"""
#     url: str = Field(..., description="Relative URL path")
#     full_url: str = Field(..., description="Full URL including domain")
#     link_text: Optional[str] = Field(None, description="Visible text of the link")
#     source: str = Field(..., description="Location on the page (header/footer/main/etc.)")
#     category: str = Field(..., description="Link category (company/product/legal/etc.)")

#     confidence_score: Optional[float] = Field(None, description="Confidence score of the categorization")


# class CrawlingInstructions(BaseModel):
#     """Instructions for further crawling"""
#     priority_crawl: List[str] = Field(default_factory=list, description="URLs to prioritize for crawling")
#     skip_crawl: List[str] = Field(default_factory=list, description="URLs to skip when crawling")


# class LinkAnalysis(BaseModel):
#     """Complete link analysis information"""
#     base_domain: str = Field(..., description="Base domain of the website")
#     links: List[Link] = Field(default_factory=list, description="All extracted links")
#     ignored_categories: Optional[List[str]] = Field(default_factory=list, description="Categories to ignore during crawling")
#     crawling_instructions: Optional[CrawlingInstructions] = Field(None, description="Crawling instructions")


# # class WebsiteExtraction(BaseModel):
# #     """Complete schema for website extraction data"""
# #     url: str = Field(..., description="Target URL that was processed")
# #     favicon: Optional[str] = Field(None, description="Favicon URL")
# #     logo: Optional[Logo] = Field(None, description="Logo information")
# #     color_palette: Optional[List[str]] = Field(None, description="Brand color codes")
# #     brand_fonts: Optional[BrandFonts] = Field(None, description="Typography information")
# #     company: Optional[CompanyInfo] = Field(None, description="Company information")
# #     legal_links: Optional[LegalLinks] = Field(None, description="Legal documentation")
# #     social_profiles: Optional[SocialProfiles] = Field(None, description="Social media profiles")
# #     link_analysis: Optional[LinkAnalysis] = Field(None, description="Complete link structure analysis")
# #     seo_data: Optional[SEOData] = Field(None, description="SEO metadata")
# class WebsiteExtraction(BaseModel):
#     """Complete schema for website extraction data"""
#     url: str = Field(..., description="Target URL that was processed")
#     favicon: Optional[str] = Field(None, description="Favicon URL")
#     logo: Optional[dict] = Field(None, description="Logo information")  # Changed from Logo to dict
#     color_palette: Optional[List[str]] = Field(default_factory=list, description="Brand color codes")  # Default empty list
#     brand_fonts: Optional[dict] = Field(default_factory=dict, description="Typography information")  # Changed from BrandFonts to dict
#     company: Optional[dict] = Field(None, description="Company information")  # Changed from CompanyInfo to dict
#     legal_links: Optional[dict] = Field(None, description="Legal documentation")
#     social_profiles: Optional[dict] = Field(None, description="Social media profiles")
#     link_analysis: Optional[dict] = Field(None, description="Complete link structure analysis")
#     seo_data: Optional[dict] = Field(None, description="SEO metadata")

# # Status tracking models
# class ExtractionRequest(BaseModel):
#     url: HttpUrl
#     org_id: Optional[str] = Field(None, description="Organization ID. If not provided, user's default organization will be used.")

# class ExtractionResponse(BaseModel):
#     """Response schema for extraction job creation"""
#     job_id: str = Field(..., alias="jobId", description="Job ID")
#     org_id: str = Field(..., alias="orgId", description="Organization ID")
#     status: str = Field("pending", description="Job status")
#     message: str = Field("Extraction job started", description="Status message")

#     class Config:
#         populate_by_name = True
#         alias_generator = lambda x: x  # This will preserve the original field names

# class ExtractionStatusResponse(BaseModel):
#     job_id: str
#     org_id: str = Field(..., description="Organization ID that owns this job")
#     status: str
#     message: Optional[str] = None

# class ExtractionResultResponse(BaseModel):
#     job_id: str
#     org_id: str = Field(..., description="Organization ID that owns this job")
#     status: str
#     data: Optional[WebsiteExtraction] = None
#     error: Optional[str] = None


"""
Enhanced schemas for website data extraction - CORRECTED VERSION
"""
from typing import List, Optional, Union
from pydantic import BaseModel, Field, HttpUrl, validator


class Logo(BaseModel):
    """Schema for logo information"""
    url: str = Field(..., description="URL of the logo image")
    alt_text: Optional[str] = Field(None, description="Alternative text for the logo")


class CompanyInfo(BaseModel):
    """Schema for company details"""
    name: Optional[str] = Field(None, description="Company name")
    description: Optional[str] = Field(None, description="Company description or tagline")
    industry: Optional[str] = Field(None, description="Industry sector")
    location: Optional[str] = Field(None, description="City and state/country")


class SocialProfiles(BaseModel):
    """Schema for social media presence"""
    linkedin: Optional[str] = Field(None, description="LinkedIn company profile URL")
    twitter: Optional[str] = Field(None, description="Twitter/X profile URL")
    facebook: Optional[str] = Field(None, description="Facebook page URL")
    github: Optional[str] = Field(None, description="GitHub organization URL")


class LegalLinks(BaseModel):
    """Schema for legal documentation links"""
    terms_of_service: Optional[str] = Field(None, description="Terms of service URL")
    privacy_policy: Optional[str] = Field(None, description="Privacy policy URL")


class SEOData(BaseModel):
    """Schema for SEO metadata"""
    meta_title: Optional[str] = Field(None, description="Page meta title")
    meta_description: Optional[str] = Field(None, description="Page meta description")
    h1: Optional[str] = Field(None, description="Main heading H1 tag")


class WebsiteExtraction(BaseModel):
    """Complete schema for website extraction data - STRUCTURED VERSION"""
    url: str = Field(..., description="Target URL that was processed")
    
    # Basic elements
    favicon: Optional[str] = Field(None, description="Favicon URL")
    logo: Optional[Logo] = Field(None, description="Logo information with URL and alt text")
    
    # Company information  
    company: Optional[CompanyInfo] = Field(None, description="Company details")
    
    # Social media
    social_profiles: Optional[SocialProfiles] = Field(None, description="Social media profile URLs")
    
    # Legal links
    legal_links: Optional[LegalLinks] = Field(None, description="Legal documentation URLs")
    
    # SEO data
    seo_data: Optional[SEOData] = Field(None, description="SEO metadata from the page")
    
    # Simple lists
    color_palette: Optional[List[str]] = Field(None, description="Brand color codes in hex format")
    key_services: Optional[List[str]] = Field(None, description="Main services offered")


# Status tracking models (keep these unchanged)
class ExtractionRequest(BaseModel):
    url: HttpUrl
    org_id: Optional[Union[str, int]] = Field(None, description="Organization ID")
    
    @validator('org_id', pre=True)
    def convert_org_id_to_int(cls, v):
        if v is None:
            return v
        if isinstance(v, str):
            try:
                return int(v)
            except ValueError:
                raise ValueError("org_id must be a valid integer")
        return v


class ExtractionResponse(BaseModel):
    job_id: str
    org_id: Union[str, int] = Field(..., description="Organization ID")
    status: str = "pending"
    message: str = "Extraction job started"


class ExtractionStatusResponse(BaseModel):
    job_id: str
    org_id: Union[str, int] = Field(..., description="Organization ID")
    status: str
    message: Optional[str] = None


class ExtractionResultResponse(BaseModel):
    job_id: str
    org_id: Union[str, int] = Field(..., description="Organization ID")
    status: str
    data: Optional[WebsiteExtraction] = None
    error: Optional[str] = None