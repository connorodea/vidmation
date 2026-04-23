"""Billing API — Stripe checkout, portal, webhooks, and usage."""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from aividio.auth.dependencies import require_active_user
from aividio.billing.plans import get_plan
from aividio.billing.stripe_service import StripeService
from aividio.config.settings import get_settings
from aividio.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])


# ── Request / Response schemas ────────────────────────────────────────────


class CheckoutRequest(BaseModel):
    plan: Literal["pro", "business"]
    interval: Literal["monthly", "annual"] = "monthly"
    success_url: str = "https://aividio.com/billing/success"
    cancel_url: str = "https://aividio.com/billing/cancel"


class CheckoutResponse(BaseModel):
    checkout_url: str


class PortalRequest(BaseModel):
    return_url: str = "https://aividio.com/billing"


class PortalResponse(BaseModel):
    portal_url: str


class UsageResponse(BaseModel):
    videos_generated: int
    videos_limit: int
    can_generate: bool


class PlanResponse(BaseModel):
    tier: str
    subscription_status: str
    videos_per_month: int
    max_duration_min: int
    resolution: str
    watermark: bool
    price_monthly: int
    price_annual: int
    expires_at: str | None = None


# ── Helpers ───────────────────────────────────────────────────────────────


def _get_stripe() -> StripeService:
    """Lazy-init the Stripe service (fails loudly if keys are missing)."""
    return StripeService()


def _price_id_for(plan: str, interval: str) -> str:
    """Resolve the Stripe Price ID for a plan + interval combination."""
    settings = get_settings()
    key = f"stripe_price_{plan}_{interval}"
    price_id: str = getattr(settings, key, "")
    if not price_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No Stripe price configured for {plan}/{interval}. "
            f"Set AIVIDIO_{key.upper()} in your environment.",
        )
    return price_id


# ── POST /billing/checkout ────────────────────────────────────────────────


@router.post(
    "/checkout",
    response_model=CheckoutResponse,
    summary="Create a Stripe Checkout session",
)
async def create_checkout(
    body: CheckoutRequest,
    user: User = Depends(require_active_user),
):
    """Start a Stripe Checkout flow for the requested plan and interval.

    Returns a URL that the frontend should redirect the user to.
    """
    price_id = _price_id_for(body.plan, body.interval)
    svc = _get_stripe()

    try:
        url = svc.create_checkout_session(
            user_id=user.id,
            price_id=price_id,
            success_url=body.success_url,
            cancel_url=body.cancel_url,
        )
    except Exception:
        logger.exception("Failed to create checkout session")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not create checkout session — please try again",
        )

    return CheckoutResponse(checkout_url=url)


# ── POST /billing/portal ─────────────────────────────────────────────────


@router.post(
    "/portal",
    response_model=PortalResponse,
    summary="Create a Stripe Customer Portal session",
)
async def create_portal(
    body: PortalRequest,
    user: User = Depends(require_active_user),
):
    """Open the Stripe Customer Portal so the user can manage billing.

    Returns a URL that the frontend should redirect the user to.
    """
    if not user.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active subscription — nothing to manage",
        )

    svc = _get_stripe()
    try:
        url = svc.create_portal_session(user_id=user.id, return_url=body.return_url)
    except Exception:
        logger.exception("Failed to create portal session")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not create portal session — please try again",
        )

    return PortalResponse(portal_url=url)


# ── POST /billing/webhook ────────────────────────────────────────────────


@router.post(
    "/webhook",
    status_code=status.HTTP_200_OK,
    summary="Stripe webhook endpoint",
    include_in_schema=False,  # hide from OpenAPI docs — Stripe only
)
async def stripe_webhook(request: Request):
    """Receive and process Stripe webhook events.

    This endpoint is called directly by Stripe; no user auth is required.
    Authentication is performed via the webhook signature.
    """
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")

    if not signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe signature header",
        )

    svc = _get_stripe()
    try:
        svc.handle_webhook(payload, signature)
    except Exception:
        logger.exception("Stripe webhook processing failed")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook processing failed",
        )

    return {"status": "ok"}


# ── GET /billing/usage ────────────────────────────────────────────────────


@router.get(
    "/usage",
    response_model=UsageResponse,
    summary="Get current video generation usage",
)
async def get_usage(user: User = Depends(require_active_user)):
    """Return how many videos the user has generated this month vs. their limit."""
    plan = get_plan(user.subscription_tier.value)
    return UsageResponse(
        videos_generated=user.videos_generated_this_month,
        videos_limit=plan["videos_per_month"],
        can_generate=user.videos_generated_this_month < plan["videos_per_month"],
    )


# ── GET /billing/plan ────────────────────────────────────────────────────


@router.get(
    "/plan",
    response_model=PlanResponse,
    summary="Get current plan details",
)
async def get_current_plan(user: User = Depends(require_active_user)):
    """Return the user's current subscription tier and its feature limits."""
    tier = user.subscription_tier.value
    plan = get_plan(tier)

    expires = None
    if user.subscription_expires_at:
        expires = user.subscription_expires_at.isoformat()

    return PlanResponse(
        tier=tier,
        subscription_status=user.subscription_status,
        videos_per_month=plan["videos_per_month"],
        max_duration_min=plan["max_duration_min"],
        resolution=plan["resolution"],
        watermark=plan["watermark"],
        price_monthly=plan["price_monthly"],
        price_annual=plan["price_annual"],
        expires_at=expires,
    )
