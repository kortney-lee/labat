"""
labat/schemas.py — Pydantic models for LABAT requests and responses.

Covers: auth/tokens, Page posts, comments, ads, creatives, insights,
conversions, webhooks, and Messenger.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Literal

from pydantic import BaseModel, Field


# ── Enums ─────────────────────────────────────────────────────────────────────

class Platform(str, Enum):
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    THREADS = "threads"


class AdStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    DELETED = "DELETED"
    ARCHIVED = "ARCHIVED"


class CampaignObjective(str, Enum):
    OUTCOME_AWARENESS = "OUTCOME_AWARENESS"
    OUTCOME_ENGAGEMENT = "OUTCOME_ENGAGEMENT"
    OUTCOME_LEADS = "OUTCOME_LEADS"
    OUTCOME_SALES = "OUTCOME_SALES"
    OUTCOME_TRAFFIC = "OUTCOME_TRAFFIC"
    OUTCOME_APP_PROMOTION = "OUTCOME_APP_PROMOTION"


class BidStrategy(str, Enum):
    LOWEST_COST_WITHOUT_CAP = "LOWEST_COST_WITHOUT_CAP"
    LOWEST_COST_WITH_BID_CAP = "LOWEST_COST_WITH_BID_CAP"
    COST_CAP = "COST_CAP"
    MINIMUM_ROAS = "MINIMUM_ROAS"


class WebhookEventType(str, Enum):
    FEED = "feed"
    MENTION = "mention"
    MESSAGES = "messages"
    MESSAGING_POSTBACKS = "messaging_postbacks"


# ── Auth / Tokens ─────────────────────────────────────────────────────────────

class TokenExchangeRequest(BaseModel):
    short_lived_token: str = Field(..., description="Short-lived user access token from OAuth flow")


class TokenExchangeResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: Optional[int] = None


class PageTokenResponse(BaseModel):
    page_id: str
    page_name: str
    access_token: str
    permissions: List[str] = []


# ── Page Posts ────────────────────────────────────────────────────────────────

class CreatePostRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    page_id: Optional[str] = Field(None, description="Optional Page ID override")
    link: Optional[str] = Field(None, description="URL for a link-share post")
    image_url: Optional[str] = Field(None, description="Public image URL — creates a photo post (image uploaded natively, no raw URL shown)")
    published: bool = True
    scheduled_publish_time: Optional[int] = Field(
        None, description="Unix timestamp for scheduled post (10 min–6 months in future)"
    )


class UpdatePostRequest(BaseModel):
    message: Optional[str] = Field(None, max_length=5000)


class PostResponse(BaseModel):
    id: str
    message: Optional[str] = None
    created_time: Optional[str] = None
    permalink_url: Optional[str] = None
    is_published: bool = True


class PostListResponse(BaseModel):
    posts: List[PostResponse]
    paging_next: Optional[str] = None


class CreateInstagramPostRequest(BaseModel):
    caption: str = Field(..., min_length=1, max_length=2200)
    image_url: str = Field(..., min_length=1, description="Public image URL for Instagram media upload")
    page_id: Optional[str] = Field(None, description="Optional Page ID override to resolve linked Instagram account")


class CreateVideoPostRequest(BaseModel):
    description: str = Field(..., min_length=1, max_length=5000)
    file_url: str = Field(..., min_length=1, description="Public URL to the video file")
    title: Optional[str] = Field(None, max_length=200)
    published: bool = True
    page_id: Optional[str] = Field(None, description="Facebook Page ID override")


class VideoPostResponse(BaseModel):
    id: str


class CreateInstagramVideoRequest(BaseModel):
    caption: str = Field(..., min_length=1, max_length=2200)
    video_url: str = Field(..., min_length=1, description="Public URL to the video file")
    media_type: str = Field("REELS", description="REELS or VIDEO")
    page_id: Optional[str] = Field(None, description="Optional Page ID override")


class InstagramPostResponse(BaseModel):
    id: str
    creation_id: Optional[str] = None


class CreateThreadsPostRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)
    image_url: Optional[str] = Field(None, description="Public image URL for Threads image post")
    link_attachment: Optional[str] = Field(None, description="URL to attach as link preview")
    page_id: Optional[str] = Field(None, description="Optional Page ID override to resolve linked Threads account")


class ThreadsPostResponse(BaseModel):
    id: str
    creation_id: Optional[str] = None


# ── Comments ──────────────────────────────────────────────────────────────────

class CreateCommentRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)


class CommentResponse(BaseModel):
    id: str
    message: str
    from_name: Optional[str] = None
    from_id: Optional[str] = None
    created_time: Optional[str] = None
    can_reply_privately: bool = False


class CommentListResponse(BaseModel):
    comments: List[CommentResponse]
    paging_next: Optional[str] = None


# ── Messenger / Private Replies ───────────────────────────────────────────────

class SendMessageRequest(BaseModel):
    recipient_id: str = Field(..., description="Page-scoped user ID")
    message_text: str = Field(..., min_length=1, max_length=2000)
    messaging_type: str = Field("RESPONSE", description="RESPONSE | UPDATE | MESSAGE_TAG")
    tag: Optional[str] = Field(None, description="Message tag (required if messaging_type=MESSAGE_TAG)")


class PrivateReplyRequest(BaseModel):
    comment_id: str = Field(..., description="Comment ID to reply privately to")
    message: str = Field(..., min_length=1, max_length=2000)


class MessageResponse(BaseModel):
    recipient_id: str
    message_id: Optional[str] = None


# ── Ads / Campaigns ──────────────────────────────────────────────────────────

class CreateCampaignRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=400)
    objective: CampaignObjective
    status: AdStatus = AdStatus.PAUSED
    daily_budget: Optional[int] = Field(None, description="Daily budget in cents")
    lifetime_budget: Optional[int] = Field(None, description="Lifetime budget in cents")
    bid_strategy: BidStrategy = BidStrategy.LOWEST_COST_WITHOUT_CAP
    special_ad_categories: List[str] = Field(default_factory=list)
    campaign_budget_optimization: Optional[bool] = Field(None, description="Enable Advantage Campaign Budget (CBO)")


class UpdateCampaignRequest(BaseModel):
    name: Optional[str] = None
    status: Optional[AdStatus] = None
    daily_budget: Optional[int] = None
    bid_strategy: Optional[BidStrategy] = None
    campaign_budget_optimization: Optional[bool] = Field(None, description="Enable/disable CBO")


class CampaignResponse(BaseModel):
    id: str
    name: str
    objective: Optional[str] = None
    status: Optional[str] = None
    daily_budget: Optional[str] = None
    lifetime_budget: Optional[str] = None
    bid_strategy: Optional[str] = None
    created_time: Optional[str] = None


class CreateAdSetRequest(BaseModel):
    campaign_id: str
    name: str = Field(..., min_length=1, max_length=400)
    status: AdStatus = AdStatus.PAUSED
    daily_budget: Optional[int] = Field(None, description="In cents")
    lifetime_budget: Optional[int] = Field(None, description="In cents")
    billing_event: str = "IMPRESSIONS"
    optimization_goal: str = "LINK_CLICKS"
    bid_amount: Optional[int] = Field(None, description="Bid cap in cents")
    targeting: Dict[str, Any] = Field(default_factory=dict)
    destination_type: Optional[str] = Field(None, description="WEBSITE, APP, etc.")
    promoted_object: Optional[Dict[str, Any]] = Field(None, description="E.g. {pixel_id, custom_event_type}")
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    product: Optional[str] = Field(None, description="Brand key (wihy, vowels, communitygroceries). Auto-injects targeting preset when targeting is empty.")
    funnel_stage: Optional[str] = Field(None, description="awareness | consideration | conversion. Sets optimization_goal automatically.")


class AdSetResponse(BaseModel):
    id: str
    name: str
    campaign_id: Optional[str] = None
    status: Optional[str] = None
    daily_budget: Optional[str] = None
    optimization_goal: Optional[str] = None
    destination_type: Optional[str] = None
    created_time: Optional[str] = None


class UpdateAdSetRequest(BaseModel):
    name: Optional[str] = None
    status: Optional[AdStatus] = None
    daily_budget: Optional[int] = None
    lifetime_budget: Optional[int] = None
    bid_amount: Optional[int] = None
    optimization_goal: Optional[str] = None
    billing_event: Optional[str] = None


class CreateAdRequest(BaseModel):
    adset_id: str
    name: str = Field(..., min_length=1, max_length=400)
    status: AdStatus = AdStatus.PAUSED
    creative_id: str


class AdResponse(BaseModel):
    id: str
    name: str
    adset_id: Optional[str] = None
    status: Optional[str] = None
    creative: Optional[Dict[str, Any]] = None
    created_time: Optional[str] = None


class UpdateAdRequest(BaseModel):
    name: Optional[str] = None
    status: Optional[AdStatus] = None
    creative_id: Optional[str] = None


# ── Ad Videos ─────────────────────────────────────────────────────────────────

class UploadAdVideoRequest(BaseModel):
    file_url: str = Field(..., min_length=1, description="Public URL to the video file")
    name: str = Field(..., min_length=1, max_length=400)
    title: Optional[str] = Field(None, max_length=200)


class AdVideoResponse(BaseModel):
    id: str
    name: Optional[str] = None
    title: Optional[str] = None


# ── Creatives ─────────────────────────────────────────────────────────────────

class CreateCreativeRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=400)
    object_story_spec: Optional[Dict[str, Any]] = Field(
        None, description="Page post spec for link ads, video ads, etc."
    )
    object_story_id: Optional[str] = Field(
        None, description="Existing page post ID in format {page_id}_{post_id}"
    )
    url_tags: Optional[str] = None
    variant: Optional[str] = Field(
        None,
        description="Lead variant for UTM auto-injection: weight|kids|energy|groceries|family|confused|warning|realfood|etc. "
                    "If omitted, inferred from creative name. Sets utm_content on all ad destination URLs."
    )


class CreativeResponse(BaseModel):
    id: str
    name: Optional[str] = None
    status: Optional[str] = None
    object_story_spec: Optional[Dict[str, Any]] = None


# ── Insights ──────────────────────────────────────────────────────────────────

class InsightsRequest(BaseModel):
    object_id: Optional[str] = Field(None, description="Campaign/AdSet/Ad ID (uses ad account if empty)")
    level: str = Field("campaign", description="account | campaign | adset | ad")
    date_preset: str = Field("last_7d", description="today | yesterday | last_7d | last_30d | lifetime")
    fields: List[str] = Field(
        default_factory=lambda: [
            "campaign_name", "impressions", "clicks", "spend",
            "cpc", "cpm", "ctr", "reach", "actions",
        ]
    )
    time_increment: Optional[int] = Field(None, description="1=daily, 7=weekly, etc.")
    limit: int = Field(50, ge=1, le=500)


class InsightsResponse(BaseModel):
    data: List[Dict[str, Any]]
    paging: Optional[Dict[str, Any]] = None


# ── Conversions API ───────────────────────────────────────────────────────────

class ConversionEvent(BaseModel):
    event_name: str = Field(..., description="e.g. Purchase, Lead, CompleteRegistration")
    event_time: int = Field(..., description="Unix timestamp of the event")
    action_source: str = Field("website", description="website | app | email | phone_call | other")
    event_source_url: Optional[str] = None
    user_data: Dict[str, Any] = Field(
        ..., description="Hashed PII: em, ph, fn, ln, ct, st, zp, country, external_id, etc."
    )
    custom_data: Optional[Dict[str, Any]] = Field(
        None, description="value, currency, content_ids, content_type, etc."
    )
    event_id: Optional[str] = Field(None, description="Dedup key (match browser pixel event_id)")


class ConversionsBatchRequest(BaseModel):
    events: List[ConversionEvent] = Field(..., min_length=1, max_length=1000)
    test_event_code: Optional[str] = Field(None, description="Test event code from Events Manager")


class ConversionsResponse(BaseModel):
    events_received: int
    messages: List[str] = []
    fbtrace_id: Optional[str] = None


# ── Pixels ────────────────────────────────────────────────────────────────────

class CreatePixelRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Display name for the pixel")


class PixelResponse(BaseModel):
    id: str
    name: Optional[str] = None
    code: Optional[str] = None
    creation_time: Optional[str] = None
    last_fired_time: Optional[str] = None


# ── Webhooks ──────────────────────────────────────────────────────────────────

class WebhookEntry(BaseModel):
    id: str
    time: int
    changes: Optional[List[Dict[str, Any]]] = None
    messaging: Optional[List[Dict[str, Any]]] = None


class WebhookPayload(BaseModel):
    object: str  # "page"
    entry: List[WebhookEntry]


# ── Compliance ────────────────────────────────────────────────────────────────

class DataDeletionRequest(BaseModel):
    signed_request: str = Field(..., description="Signed request from Meta data deletion callback")


class DataDeletionResponse(BaseModel):
    url: str = Field(..., description="Status URL for user to check deletion progress")
    confirmation_code: str


# ── Generic ───────────────────────────────────────────────────────────────────

class LabatHealthResponse(BaseModel):
    status: str = "ok"
    service: str = "wihy-labat"
    config_status: Dict[str, bool] = {}


class LabatErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    meta_error_code: Optional[int] = None
    meta_error_subcode: Optional[int] = None


# ── AI / Gemini Intelligence ─────────────────────────────────────────────────

class GenerateAdCopyRequest(BaseModel):
    product_description: str = Field(..., min_length=10, max_length=2000,
        description="What you're advertising")
    target_audience: str = Field(..., min_length=5, max_length=1000,
        description="Who the ad is for")
    campaign_goal: str = Field(..., min_length=3, max_length=500,
        description="Objective: awareness, traffic, conversions, etc.")
    num_variants: int = Field(3, ge=1, le=10,
        description="Number of copy variants to generate")
    tone: Optional[str] = Field(None, max_length=200,
        description="Optional tone: empowering, urgent, educational, etc.")
    product: Literal["wihy", "communitygroceries", "whatishealthy", "vowels"] = Field(
        "wihy", description="Product/brand context for prompt routing"
    )
    funnel_stage: Optional[Literal["awareness", "consideration", "conversion"]] = Field(
        None, description="Optional funnel stage for message strategy"
    )


class GeneratePostsRequest(BaseModel):
    topic: str = Field(..., min_length=3, max_length=1000,
        description="What the post should be about")
    platform: str = Field("facebook", description="facebook | instagram | both")
    num_posts: int = Field(3, ge=1, le=10)
    content_pillar: Optional[str] = Field(None,
        description="nutrition | fitness | community | product")
    product: Literal["wihy", "communitygroceries", "whatishealthy", "vowels"] = Field(
        "wihy", description="Product/brand context for prompt routing"
    )
    funnel_stage: Optional[Literal["awareness", "consideration", "conversion"]] = Field(
        None, description="Optional funnel stage for message strategy"
    )


class GenerateOutreachRequest(BaseModel):
    recipient_type: str = Field(..., min_length=3, max_length=200,
        description="e.g. influencer, nutritionist, gym owner, brand partner")
    context: str = Field(..., min_length=10, max_length=2000,
        description="Context about the recipient or campaign")
    goal: str = Field(..., min_length=5, max_length=500,
        description="What you want the outreach to achieve")
    num_variants: int = Field(2, ge=1, le=5)


class GenerateReplyRequest(BaseModel):
    comment_text: str = Field(..., min_length=1, max_length=5000,
        description="The comment to reply to")
    post_context: Optional[str] = Field(None, max_length=2000,
        description="Context of the original post")
    sentiment: Optional[str] = Field(None,
        description="positive | negative | neutral | question")


class ContentCalendarRequest(BaseModel):
    weeks: int = Field(1, ge=1, le=4, description="Number of weeks to plan")
    focus_areas: Optional[List[str]] = Field(None,
        description="Topics to emphasize")
    existing_content: Optional[List[str]] = Field(None,
        description="Recent posts to avoid repeating")


class AnalyzeCampaignsRequest(BaseModel):
    insights_data: List[Dict[str, Any]] = Field(..., min_length=1,
        description="Campaign insights data from Meta Ads API")
    product: Literal["wihy", "communitygroceries", "whatishealthy", "vowels"] = Field(
        "wihy", description="Product/brand context for analysis strategy"
    )
    funnel_stage: Optional[Literal["awareness", "consideration", "conversion"]] = Field(
        None, description="Optional funnel stage for optimization framing"
    )


class AudienceRecommendationRequest(BaseModel):
    campaign_context: str = Field(..., min_length=10, max_length=3000,
        description="Product/campaign description for audience targeting")
    performance_data: Optional[List[Dict[str, Any]]] = Field(None,
        description="Historical performance data")
    product: Literal["wihy", "communitygroceries", "whatishealthy", "vowels"] = Field(
        "wihy", description="Product/brand context for analysis strategy"
    )
    funnel_stage: Optional[Literal["awareness", "consideration", "conversion"]] = Field(
        None, description="Optional funnel stage for optimization framing"
    )


class OptimizeCreativesRequest(BaseModel):
    creative_performance: List[Dict[str, Any]] = Field(..., min_length=1,
        description="Creative performance metrics")
    product: Literal["wihy", "communitygroceries", "whatishealthy", "vowels"] = Field(
        "wihy", description="Product/brand context for analysis strategy"
    )
    funnel_stage: Optional[Literal["awareness", "consideration", "conversion"]] = Field(
        None, description="Optional funnel stage for optimization framing"
    )


class OptimizeBudgetRequest(BaseModel):
    performance_data: List[Dict[str, Any]] = Field(..., min_length=1,
        description="Campaign performance data")
    total_daily_budget: Optional[int] = Field(None,
        description="Total daily budget in cents")
    product: Literal["wihy", "communitygroceries", "whatishealthy", "vowels"] = Field(
        "wihy", description="Product/brand context for analysis strategy"
    )
    funnel_stage: Optional[Literal["awareness", "consideration", "conversion"]] = Field(
        None, description="Optional funnel stage for optimization framing"
    )


class DigestRequest(BaseModel):
    performance_data: List[Dict[str, Any]] = Field(..., min_length=1,
        description="Campaign performance data")
    period: str = Field("last_7d",
        description="today | yesterday | last_7d | last_30d | lifetime")


# ── Automated Rules ──────────────────────────────────────────────────────────

class CreateAdRuleRequest(BaseModel):
    name: str = Field(..., description="Rule name")
    evaluation_spec: Dict[str, Any] = Field(...,
        description="Evaluation spec (evaluation_type, filters)")
    execution_spec: Dict[str, Any] = Field(...,
        description="Execution spec (execution_type, execution_options)")
    schedule_spec: Optional[Dict[str, Any]] = Field(None,
        description="Schedule spec (schedule_type)")
    status: str = Field("ENABLED", description="ENABLED or DISABLED")


class UpdateAdRuleRequest(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    evaluation_spec: Optional[Dict[str, Any]] = None
    execution_spec: Optional[Dict[str, Any]] = None
    schedule_spec: Optional[Dict[str, Any]] = None


# ── Amazon Book Affiliate (MVP) ──────────────────────────────────────────────

class BookAffiliatePublishRequest(BaseModel):
    asin: Optional[str] = Field(None, description="Specific ASIN to promote")
    page_id: Optional[str] = Field(None, description="Optional page override for Facebook posting")
    seed: Optional[int] = Field(None, description="Seed for deterministic variant selection")
    dry_run: bool = Field(False, description="Return payload only without publishing")


# ── Amazon Ads API (Scaffolding) ─────────────────────────────────────────────

class AmazonSPCampaignCreateRequest(BaseModel):
    profile_id: Optional[str] = Field(None, description="Amazon Ads profile ID (scope)")
    campaign: Dict[str, Any] = Field(
        ...,
        description="Sponsored Products campaign object as required by Amazon Ads API",
    )
