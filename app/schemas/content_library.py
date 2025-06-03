from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID

class Service(BaseModel):
    name: str = Field(default="", description="Service title (e.g., 'SEO Optimization'). Extract from bolded/titled sections on service pages or proposal headers.")
    category: str = Field(default="", description="Broad industry vertical (e.g., 'Digital Marketing'). Identify parent categories in navigation menus or proposal sections.")
    description: str = Field(default="", description="Service summary. Extract paragraph text following the service title, focusing on outcomes and methodologies.")
    key_features: List[str] = Field(default_factory=list, description="List of unique selling points (e.g., ['Keyword Research']). Parse bullet points, numbered lists, or subheadings under the service description.")
    pricing_model: str = Field(default="", description="Payment structure (e.g., 'Retainer'). Scan for terms like 'retainer,' 'hourly,' or 'performance-based' near pricing tables.")
    duration: str = Field(default="", description="Typical engagement length (e.g., '6-month minimum'). Search for phrases like 'minimum contract' or 'timeline' in service descriptions.")


class PortfolioItem(BaseModel):
    title: str = Field(default="", description="Project name/title. Extract from image captions, project cards, or portfolio page headings.")
    industry: str = Field(default="", description="Sector served (e.g., 'Retail'). Use metadata tags or infer from client logos/company names.")
    project_type: str = Field(default="", description="Work type (e.g., 'UX/UI Design'). Parse subheadings or labels like 'Category: E-commerce'.")
    url: str = Field(default="", description="Live project link. Scrape anchor tags (<a href>) linked to project thumbnails or case study buttons.")
    thumbnail_url: str = Field(default="", description="Thumbnail image source. Locate <img> tags within portfolio cards or galleries.")
    tags: List[str] = Field(default_factory=list, description="Keywords describing the project (e.g., ['Shopify']). Capture hashtags, skill badges, or manually added tags.")


class Metric(BaseModel):
    type: str = Field(default="", description="Metric name (e.g., 'Churn Reduction')")
    value: str = Field(default="", description="Quantified result (e.g., '35%')")


class CaseStudyResults(BaseModel):
    metrics: List[Metric] = Field(default_factory=list, description="Measurable outcomes from the work")


class CaseStudy(BaseModel):
    case_study_title: str = Field(default="", description="Headline summarizing the win (e.g., 'Boosting SaaS Retention'). Look for H1/H2 tags on case study landing pages.")
    client_name: str = Field(default="", description="Client organization name. Find company names in headers or partnership logos.")
    industry: str = Field(default="", description="Client sector (e.g., 'SaaS'). Use metadata or contextual clues (e.g., 'HealthTech Inc.').")
    challenge: str = Field(default="", description="Problem solved. Parse paragraphs starting with 'Challenge:' or 'The Problem'.")
    solution: str = Field(default="", description="Strategy implemented. Extract content after 'Solution' headings or 'We built...' statements.")
    results: CaseStudyResults
    technologies_used: List[str] = Field(description="Tools/platforms involved. Identify tech stacks listed in footers, bullet points, or implementation sections.")
    case_study_url: str = Field(description="Link to full case study. Scrape CTA buttons labeled 'Read More' or 'View Case Study'.")


class TeamMember(BaseModel):
    name: str = Field(default="", description="Full name of team member. Parse names from profile cards or employee bios.")
    role: str = Field(default="", description="Job title. Extract text adjacent to names (e.g., 'Head of Strategy').")
    bio: str = Field(default="", description="Professional background summary. Capture multi-sentence descriptions under role titles.")
    expertise: List[str] = Field(default_factory=list, description="Skill set (e.g., ['SEO']). List skills from bullet points, badges, or LinkedIn-style summaries.")
    linkedin_url: str = Field(default="", description="Professional social media profile. Scrape LinkedIn icons or links labeled 'Connect'.")
    profile_image: str = Field(default="", description="Photo URL. Locate <img> tags within team member cards.")
    years_of_experience: str = Field(default="", description="Numeric value. Parse phrases like '10+ years in...' or 'X years of experience'.")


class Project(BaseModel):
    project_name: str = Field(default="", description="Title of past work. Extract from proposal sections labeled 'Past Projects' or website headers.")
    objective: str = Field(default="", description="Goal achieved. Look for phrases like 'Objective:' or 'Aim: Increase sales by 25%'.")
    deliverables: List[str] = Field(default_factory=list, description="Tangible outputs (e.g., ['Landing Page Redesign']). Parse bulleted lists under 'Deliverables' or 'Scope'.")
    timeline: str = Field(default="", description="Start-to-finish dates. Capture date ranges (e.g., 'Oct–Dec 2023') or duration statements (e.g., '6 months').")
    budget_range: str = Field(default="", description="Cost estimate. Find dollar amounts paired with terms like 'budget' or 'investment'.")
    status: str = Field(default="", description="Current phase (e.g., 'Completed'). Use status badges or labels like 'In Progress', 'On Hold'.")
    client: str = Field(default="", description="Engaged organization. Match project to client names in testimonials or portfolio tags.")


class PricingPackage(BaseModel):
    package_name: str = Field(default="", description="Plan identifier (e.g., 'Starter Growth Package'). Extract tier names from pricing tables (e.g., 'Basic', 'Pro').")
    price: str = Field(default="", description="Monetary cost. Parse numbers with currency symbols (e.g., '$2,500/month').")
    features: List[str] = Field(default_factory=list, description="Included services (e.g., ['Monthly ROI Reports']). List items from package comparison tables or bullet lists.")
    contract_terms: str = Field(default="", description="Binding conditions. Scan for legal language near payment details (e.g., 'Minimum 3-month commitment').")
    add_ons: List[str] = Field(default_factory=list, description="Optional extras. Identify sections labeled 'Add-ons' or 'Upgrades' with price modifiers.")


class Product(BaseModel):
    product_name: str = Field(default="", description="Software/tool name. Extract from product landing page headers or app store listings.")
    description: str = Field(default="", description="Functionality overview. Capture introductory paragraphs or taglines on product pages.")
    features: List[str] = Field(default_factory=list, description="Key capabilities (e.g., ['Real-time Scoring']). Parse feature lists, checkboxes, or comparison grids.")
    pricing_model: str = Field(default="", description="Cost structure (e.g., '$99/month per user'). Look for recurring billing terms or free trial offers.")
    availability: str = Field(default="", description="Distribution channels. Extract phrases like 'Web app + Salesforce AppExchange'.")
    demo_url: str = Field(default="", description="Trial/demo link. Scrape 'Request Demo' or 'Free Trial' CTAs.")


class Award(BaseModel):
    award_name: str = Field(default="", description="Accolade title (e.g., 'Top Digital Agency 2023'). Find bolded titles on award badges or press releases.")
    issuer: str = Field(default="", description="Awarding body. Identify organizations named in citations (e.g., 'AdWeek').")
    year: str = Field(default="", description="Date received. Parse four-digit years near award blurbs.")
    category: str = Field(default="", description="Sub-category (e.g., 'Best B2B Agency'). Capture descriptors in parentheses or subtitles.")
    proof_link: str = Field(default="", description="Verification URL. Scrape hyperlinks attached to award logos or citations.")


class FAQ(BaseModel):
    question: str = Field(default="", description="User query (e.g., 'Do you offer refunds?'). Find text ending with a question mark in FAQ sections.")
    answer: str = Field(default="", description="Response provided. Capture content immediately following questions in accordion/toggle elements.")
    category: str = Field(default="", description="Topic grouping (e.g., 'Billing'). Use tab headers or metadata tags (e.g., 'Frequently Asked Questions > Pricing').")
    tags: List[str] = Field(default_factory=list, description="Searchable keywords (e.g., ['Refunds']). Extract from hashtagged words or manually added tags.")


class Technology(BaseModel):
    technology_name: str = Field(default="", description="Tool/platform name (e.g., 'HubSpot'). Parse from integration pages or tech stack badges.")
    integration_type: str = Field(default="", description="Usage context (e.g., 'CRM Sync'). Identify phrases like 'integrates with' or 'works seamlessly'.")
    use_cases: List[str] = Field(default_factory=list, description="Specific applications (e.g., Lead Tracking). Extract from bullet points or scenario-based descriptions.")
    compatibility: str = Field(default="", description="Interoperability notes. Capture sentences mentioning partnerships (e.g., 'Works with Salesforce').")
    support_level: str = Field(default="", description="Customer assistance tiers. Look for phrases like '24/7 support' or 'dedicated account manager'.")


class Terms(BaseModel):
    payment_terms: str = Field(default="", description="Billing schedule (e.g., 'Net-30'). Search for financial terms like 'Net-30', 'advance payment'.")
    cancellation_policy: str = Field(default="", description="Exit clauses. Parse phrases like '30 days notice required' or 'refund policy'.")
    sla_response_time: str = Field(default="", description="Support SLA (e.g., '2 business days'). Find mentions of response times in contracts/legal docs.")
    jurisdiction: str = Field(default="", description="Governing law (e.g., 'California, USA'). Locate fine print in Terms & Conditions footers.")
    renewal_terms: str = Field(default="", description="Auto-renewal settings. Identify phrases like 'auto-renews unless canceled' near payment sections.")


class LegalCompliance(BaseModel):
    certification: str = Field(default="", description="Official accreditation (e.g., 'GDPR Compliant'). Extract from trust badges, compliance sections, or footers.")
    compliance_standards: List[str] = Field(default_factory=list, description="Certifications (e.g., 'ISO 27001'). Parse lists of standards in legal disclosures.")
    audit_history: str = Field(default="", description="Third-party validation. Capture phrases like 'annual third-party audits' in security policies.")
    data_residency: str = Field(default="", description="Data storage location. Look for clauses specifying server locations (e.g., 'Frankfurt AWS servers').")


class Industries(BaseModel):
    industry: List[str] = Field(default_factory=list, description="Target market (e.g., 'Healthcare'). Extract from homepage hero sections or service page filters.")
    geographic_focus: List[str] = Field(default_factory=list, description="Regions served (e.g., North America). Parse footers, contact pages, or localization selectors.")
    market_segments: List[str] = Field(default_factory=list, description="Sub-audiences (e.g., Hospitals). Identify niche audiences in industry-specific case studies.")
    target_company_size: List[str] = Field(default_factory=list, description="Size brackets (e.g., Enterprise). Capture phrases like 'Mid-market' or 'SMB-focused' in service descriptions.")


class MethodologyPhase(BaseModel):
    phase: str = Field(description="Stage name (e.g., 'Discovery'). Find numbered steps or phase headers in workflow diagrams.")
    steps: List[str] = Field(description="Action items (e.g., 'Kickoff Workshop'). Parse bulleted actions under phase titles.")
    deliverables: List[str] = Field(description="Output artifacts (e.g., 'Strategy Document'). Capture nouns following verbs like 'provide' or 'create'.")
    timeline: str = Field(description="Duration (e.g., 'Weeks 1–2'). Pull timeframes from Gantt charts or process timelines.")
    owner: str = Field(description="Responsible party (e.g., 'Strategy Lead'). Match roles to tasks in organizational flowcharts.")


class KeyMetric(BaseModel):
    metric_name: str = Field(description="Performance indicator (e.g., 'CAC'). Identify acronyms like ROI/CAC or terms like 'customer lifetime value'.")
    baseline_value: str = Field(description="Pre-engagement benchmark. Capture values before improvement claims (e.g., '$150').")
    improved_value: str = Field(description="Post-engagement result. Parse metrics after words like 'increased to' or 'reduced to'.")
    timeframe: str = Field(description="Measurement period (e.g., '6 months'). Find durations linked to results (e.g., 'within 90 days').")
    impact_note: str = Field(description="Contextual explanation. Extract sentences explaining *why* a metric changed (e.g., 'due to optimized ads').")


# Main Business Information Schema Model
class BusinessInformationSchema(BaseModel):
    services: List[Service] = Field(default_factory=list, description="List of all services offered by the business")
    portfolio: List[PortfolioItem] = Field(default_factory=list, description="List of portfolio projects completed by the business")
    case_studies: List[CaseStudy] = Field(default_factory=list, description="List of case studies and success stories")
    team: List[TeamMember] = Field(default_factory=list, description="List of team members at the business")
    projects: List[Project] = Field(default_factory=list, description="List of current and past projects")
    pricing_packages: List[PricingPackage] = Field(default_factory=list, description="List of pricing plans and packages")
    products: List[Product] = Field(default_factory=list, description="List of products offered by the business")
    awards: List[Award] = Field(default_factory=list, description="List of awards and recognition received by the business")
    faqs: List[FAQ] = Field(default_factory=list, description="List of frequently asked questions and answers")
    technologies: List[Technology] = Field(default_factory=list, description="List of technologies and platforms used by the business")
    terms: Terms = Field(default_factory=Terms, description="Business terms and policies")
    legal: LegalCompliance = Field(default_factory=LegalCompliance, description="Legal and compliance information")
    industries: Industries = Field(default_factory=Industries, description="Industry focus and target markets")
    methodology: List[MethodologyPhase] = Field(default_factory=list, description="Business processes and methodologies")
    metrics: List[KeyMetric] = Field(default_factory=list, description="Key performance metrics and statistics")

    class Config:
        json_schema_extra = {
            "name": "business_information_schema",
            "strict": True
        }

class ContentLibraryRequest(BaseModel):
    """Request model for content library processing."""
    org_id: str = Field(..., description="Organization ID")
    source_ids: List[str] = Field(..., description="List of content source IDs to process")

class ContentLibraryStatusResponse(BaseModel):
    """Response model for checking content library processing status."""
    job_id: UUID = Field(..., description="Unique identifier for the processing job")
    org_id: str = Field(None, description="Organization ID that owns this job")
    status: str = Field(..., description="Current status of the processing job")
    source_count: int = Field(0, description="Total number of sources in the job")
    processed_count: int = Field(0, description="Number of sources that have been processed")
    error: Optional[str] = Field(None, description="Error message if job failed")

    class Config:
        json_encoders = {
            UUID: lambda v: str(v)  # Convert UUID to string when serializing to JSON
        }

class ContentLibraryResultResponse(BaseModel):
    """Response model for getting content library processing results."""
    job_id: str = Field(..., description="Unique identifier for the processing job")
    org_id: str = Field(None, description="Organization ID that owns this job")
    status: str = Field(..., description="Overall status of the processing job")
    source_count: int = Field(0, description="Total number of sources in the job")
    processed_count: int = Field(0, description="Number of sources that have been processed")
    data: Optional[BusinessInformationSchema] = Field(None, description="Extracted content items")
    error: Optional[str] = Field(None, description="Error message if job failed")

"""
TO GET THE EXACT NULL FOR THE FEILD WHOSE DATA IS NOT AVAILABLE TO US WE WILL BE USING THE OPTIONAL FIELDS THIS CURRENTLY NOT IN USE:
"""

# from pydantic import BaseModel, Field
# from typing import List, Optional

# class Service(BaseModel):
#     name: Optional[str] = Field(default=None, description="Service title (e.g., 'SEO Optimization'). Extract from bolded/titled sections on service pages or proposal headers.")
#     category: Optional[str] = Field(default=None, description="Broad industry vertical (e.g., 'Digital Marketing'). Identify parent categories in navigation menus or proposal sections.")
#     description: Optional[str] = Field(default=None, description="Service summary. Extract paragraph text following the service title, focusing on outcomes and methodologies.")
#     key_features: Optional[List[str]] = Field(default=None, description="List of unique selling points (e.g., ['Keyword Research']). Parse bullet points, numbered lists, or subheadings under the service description.")
#     pricing_model: Optional[str] = Field(default=None, description="Payment structure (e.g., 'Retainer'). Scan for terms like 'retainer,' 'hourly,' or 'performance-based' near pricing tables.")
#     duration: Optional[str] = Field(default=None, description="Typical engagement length (e.g., '6-month minimum'). Search for phrases like 'minimum contract' or 'timeline' in service descriptions.")


# class PortfolioItem(BaseModel):
#     title: Optional[str] = Field(default=None, description="Project name/title. Extract from image captions, project cards, or portfolio page headings.")
#     industry: Optional[str] = Field(default=None, description="Sector served (e.g., 'Retail'). Use metadata tags or infer from client logos/company names.")
#     project_type: Optional[str] = Field(default=None, description="Work type (e.g., 'UX/UI Design'). Parse subheadings or labels like 'Category: E-commerce'.")
#     url: Optional[str] = Field(default=None, description="Live project link. Scrape anchor tags (<a href>) linked to project thumbnails or case study buttons.")
#     thumbnail_url: Optional[str] = Field(default=None, description="Thumbnail image source. Locate <img> tags within portfolio cards or galleries.")
#     tags: Optional[List[str]] = Field(default=None, description="Keywords describing the project (e.g., ['Shopify']). Capture hashtags, skill badges, or manually added tags.")


# class Metric(BaseModel):
#     type: Optional[str] = Field(default=None, description="Metric name (e.g., 'Churn Reduction')")
#     value: Optional[str] = Field(default=None, description="Quantified result (e.g., '35%')")


# class CaseStudyResults(BaseModel):
#     metrics: Optional[List[Metric]] = Field(default=None, description="Measurable outcomes from the work")


# class CaseStudy(BaseModel):
#     case_study_title: Optional[str] = Field(default=None, description="Headline summarizing the win (e.g., 'Boosting SaaS Retention'). Look for H1/H2 tags on case study landing pages.")
#     client_name: Optional[str] = Field(default=None, description="Client organization name. Find company names in headers or partnership logos.")
#     industry: Optional[str] = Field(default=None, description="Client sector (e.g., 'SaaS'). Use metadata or contextual clues (e.g., 'HealthTech Inc.').")
#     challenge: Optional[str] = Field(default=None, description="Problem solved. Parse paragraphs starting with 'Challenge:' or 'The Problem'.")
#     solution: Optional[str] = Field(default=None, description="Strategy implemented. Extract content after 'Solution' headings or 'We built...' statements.")
#     results: Optional[CaseStudyResults] = Field(default=None)
#     technologies_used: Optional[List[str]] = Field(default=None, description="Tools/platforms involved. Identify tech stacks listed in footers, bullet points, or implementation sections.")
#     case_study_url: Optional[str] = Field(default=None, description="Link to full case study. Scrape CTA buttons labeled 'Read More' or 'View Case Study'.")


# class TeamMember(BaseModel):
#     name: Optional[str] = Field(default=None, description="Full name of team member. Parse names from profile cards or employee bios.")
#     role: Optional[str] = Field(default=None, description="Job title. Extract text adjacent to names (e.g., 'Head of Strategy').")
#     bio: Optional[str] = Field(default=None, description="Professional background summary. Capture multi-sentence descriptions under role titles.")
#     expertise: Optional[List[str]] = Field(default=None, description="Skill set (e.g., ['SEO']). List skills from bullet points, badges, or LinkedIn-style summaries.")
#     linkedin_url: Optional[str] = Field(default=None, description="Professional social media profile. Scrape LinkedIn icons or links labeled 'Connect'.")
#     profile_image: Optional[str] = Field(default=None, description="Photo URL. Locate <img> tags within team member cards.")
#     years_of_experience: Optional[str] = Field(default=None, description="Numeric value. Parse phrases like '10+ years in...' or 'X years of experience'.")


# class Project(BaseModel):
#     project_name: Optional[str] = Field(default=None, description="Title of past work. Extract from proposal sections labeled 'Past Projects' or website headers.")
#     objective: Optional[str] = Field(default=None, description="Goal achieved. Look for phrases like 'Objective:' or 'Aim: Increase sales by 25%'.")
#     deliverables: Optional[List[str]] = Field(default=None, description="Tangible outputs (e.g., ['Landing Page Redesign']). Parse bulleted lists under 'Deliverables' or 'Scope'.")
#     timeline: Optional[str] = Field(default=None, description="Start-to-finish dates. Capture date ranges (e.g., 'Oct–Dec 2023') or duration statements (e.g., '6 months').")
#     budget_range: Optional[str] = Field(default=None, description="Cost estimate. Find dollar amounts paired with terms like 'budget' or 'investment'.")
#     status: Optional[str] = Field(default=None, description="Current phase (e.g., 'Completed'). Use status badges or labels like 'In Progress', 'On Hold'.")
#     client: Optional[str] = Field(default=None, description="Engaged organization. Match project to client names in testimonials or portfolio tags.")


# class PricingPackage(BaseModel):
#     package_name: Optional[str] = Field(default=None, description="Plan identifier (e.g., 'Starter Growth Package'). Extract tier names from pricing tables (e.g., 'Basic', 'Pro').")
#     price: Optional[str] = Field(default=None, description="Monetary cost. Parse numbers with currency symbols (e.g., '$2,500/month').")
#     features: Optional[List[str]] = Field(default=None, description="Included services (e.g., ['Monthly ROI Reports']). List items from package comparison tables or bullet lists.")
#     contract_terms: Optional[str] = Field(default=None, description="Binding conditions. Scan for legal language near payment details (e.g., 'Minimum 3-month commitment').")
#     add_ons: Optional[List[str]] = Field(default=None, description="Optional extras. Identify sections labeled 'Add-ons' or 'Upgrades' with price modifiers.")


# class Product(BaseModel):
#     product_name: Optional[str] = Field(default=None, description="Software/tool name. Extract from product landing page headers or app store listings.")
#     description: Optional[str] = Field(default=None, description="Functionality overview. Capture introductory paragraphs or taglines on product pages.")
#     features: Optional[List[str]] = Field(default=None, description="Key capabilities (e.g., ['Real-time Scoring']). Parse feature lists, checkboxes, or comparison grids.")
#     pricing_model: Optional[str] = Field(default=None, description="Cost structure (e.g., '$99/month per user'). Look for recurring billing terms or free trial offers.")
#     availability: Optional[str] = Field(default=None, description="Distribution channels. Extract phrases like 'Web app + Salesforce AppExchange'.")
#     demo_url: Optional[str] = Field(default=None, description="Trial/demo link. Scrape 'Request Demo' or 'Free Trial' CTAs.")


# class Award(BaseModel):
#     award_name: Optional[str] = Field(default=None, description="Accolade title (e.g., 'Top Digital Agency 2023'). Find bolded titles on award badges or press releases.")
#     issuer: Optional[str] = Field(default=None, description="Awarding body. Identify organizations named in citations (e.g., 'AdWeek').")
#     year: Optional[str] = Field(default=None, description="Date received. Parse four-digit years near award blurbs.")
#     category: Optional[str] = Field(default=None, description="Sub-category (e.g., 'Best B2B Agency'). Capture descriptors in parentheses or subtitles.")
#     proof_link: Optional[str] = Field(default=None, description="Verification URL. Scrape hyperlinks attached to award logos or citations.")


# class FAQ(BaseModel):
#     question: Optional[str] = Field(default=None, description="User query (e.g., 'Do you offer refunds?'). Find text ending with a question mark in FAQ sections.")
#     answer: Optional[str] = Field(default=None, description="Response provided. Capture content immediately following questions in accordion/toggle elements.")
#     category: Optional[str] = Field(default=None, description="Topic grouping (e.g., 'Billing'). Use tab headers or metadata tags (e.g., 'Frequently Asked Questions > Pricing').")
#     tags: Optional[List[str]] = Field(default=None, description="Searchable keywords (e.g., ['Refunds']). Extract from hashtagged words or manually added tags.")


# class Technology(BaseModel):
#     technology_name: Optional[str] = Field(default=None, description="Tool/platform name (e.g., 'HubSpot'). Parse from integration pages or tech stack badges.")
#     integration_type: Optional[str] = Field(default=None, description="Usage context (e.g., 'CRM Sync'). Identify phrases like 'integrates with' or 'works seamlessly'.")
#     use_cases: Optional[List[str]] = Field(default=None, description="Specific applications (e.g., Lead Tracking). Extract from bullet points or scenario-based descriptions.")
#     compatibility: Optional[str] = Field(default=None, description="Interoperability notes. Capture sentences mentioning partnerships (e.g., 'Works with Salesforce').")
#     support_level: Optional[str] = Field(default=None, description="Customer assistance tiers. Look for phrases like '24/7 support' or 'dedicated account manager'.")


# class Terms(BaseModel):
#     payment_terms: Optional[str] = Field(default=None, description="Billing schedule (e.g., 'Net-30'). Search for financial terms like 'Net-30', 'advance payment'.")
#     cancellation_policy: Optional[str] = Field(default=None, description="Exit clauses. Parse phrases like '30 days notice required' or 'refund policy'.")
#     sla_response_time: Optional[str] = Field(default=None, description="Support SLA (e.g., '2 business days'). Find mentions of response times in contracts/legal docs.")
#     jurisdiction: Optional[str] = Field(default=None, description="Governing law (e.g., 'California, USA'). Locate fine print in Terms & Conditions footers.")
#     renewal_terms: Optional[str] = Field(default=None, description="Auto-renewal settings. Identify phrases like 'auto-renews unless canceled' near payment sections.")


# class LegalCompliance(BaseModel):
#     certification: Optional[str] = Field(default=None, description="Official accreditation (e.g., 'GDPR Compliant'). Extract from trust badges, compliance sections, or footers.")
#     compliance_standards: Optional[List[str]] = Field(default=None, description="Certifications (e.g., 'ISO 27001'). Parse lists of standards in legal disclosures.")
#     audit_history: Optional[str] = Field(default=None, description="Third-party validation. Capture phrases like 'annual third-party audits' in security policies.")
#     data_residency: Optional[str] = Field(default=None, description="Data storage location. Look for clauses specifying server locations (e.g., 'Frankfurt AWS servers').")


# class Industries(BaseModel):
#     industry: Optional[List[str]] = Field(default=None, description="Target market (e.g., 'Healthcare'). Extract from homepage hero sections or service page filters.")
#     geographic_focus: Optional[List[str]] = Field(default=None, description="Regions served (e.g., North America). Parse footers, contact pages, or localization selectors.")
#     market_segments: Optional[List[str]] = Field(default=None, description="Sub-audiences (e.g., Hospitals). Identify niche audiences in industry-specific case studies.")
#     target_company_size: Optional[List[str]] = Field(default=None, description="Size brackets (e.g., Enterprise). Capture phrases like 'Mid-market' or 'SMB-focused' in service descriptions.")


# class MethodologyPhase(BaseModel):
#     phase: Optional[str] = Field(default=None, description="Stage name (e.g., 'Discovery'). Find numbered steps or phase headers in workflow diagrams.")
#     steps: Optional[List[str]] = Field(default=None, description="Action items (e.g., 'Kickoff Workshop'). Parse bulleted actions under phase titles.")
#     deliverables: Optional[List[str]] = Field(default=None, description="Output artifacts (e.g., 'Strategy Document'). Capture nouns following verbs like 'provide' or 'create'.")
#     timeline: Optional[str] = Field(default=None, description="Duration (e.g., 'Weeks 1–2'). Pull timeframes from Gantt charts or process timelines.")
#     owner: Optional[str] = Field(default=None, description="Responsible party (e.g., 'Strategy Lead'). Match roles to tasks in organizational flowcharts.")


# class KeyMetric(BaseModel):
#     metric_name: Optional[str] = Field(default=None, description="Performance indicator (e.g., 'CAC'). Identify acronyms like ROI/CAC or terms like 'customer lifetime value'.")
#     baseline_value: Optional[str] = Field(default=None, description="Pre-engagement benchmark. Capture values before improvement claims (e.g., '$150').")
#     improved_value: Optional[str] = Field(default=None, description="Post-engagement result. Parse metrics after words like 'increased to' or 'reduced to'.")
#     timeframe: Optional[str] = Field(default=None, description="Measurement period (e.g., '6 months'). Find durations linked to results (e.g., 'within 90 days').")
#     impact_note: Optional[str] = Field(default=None, description="Contextual explanation. Extract sentences explaining *why* a metric changed (e.g., 'due to optimized ads').")


# # Main Business Information Schema Model
# class BusinessInformationSchema(BaseModel):
#     Services: Optional[List[Service]] = Field(default=None, description="List of all services offered by the business")
#     Portfolio: Optional[List[PortfolioItem]] = Field(default=None, description="List of portfolio projects completed by the business")
#     CaseStudies: Optional[List[CaseStudy]] = Field(default=None, description="List of case studies and success stories")
#     Team: Optional[List[TeamMember]] = Field(default=None, description="List of team members at the business")
#     Projects: Optional[List[Project]] = Field(default=None, description="List of current and past projects")
#     PricingPackages: Optional[List[PricingPackage]] = Field(default=None, description="List of pricing plans and packages")
#     Products: Optional[List[Product]] = Field(default=None, description="List of products offered by the business")
#     AwardsRecognition: Optional[List[Award]] = Field(default=None, description="List of awards and recognition received by the business")
#     FAQs: Optional[List[FAQ]] = Field(default=None, description="List of frequently asked questions and answers")
#     Technologies: Optional[List[Technology]] = Field(default=None, description="List of technologies and platforms used by the business")
#     Terms: Optional["Terms"] = Field(default=None, description="Business terms and policies")  # Using string forward reference
#     LegalCompliance: Optional["LegalCompliance"] = Field(default=None, description="Legal and compliance information")  # Using string forward reference
#     Industries: Optional["Industries"] = Field(default=None, description="Industry focus and target markets")  # Using string forward reference
#     Methodology: Optional[List[MethodologyPhase]] = Field(default=None, description="Business processes and methodologies")
#     KeyMetrics: Optional[List[KeyMetric]] = Field(default=None, description="Key performance metrics and statistics")

#     class Config:
#         json_schema_extra = {
#             "name": "business_information_schema",
#             "strict": True
#         }

# # Update forward references
# BusinessInformationSchema.model_rebuild()