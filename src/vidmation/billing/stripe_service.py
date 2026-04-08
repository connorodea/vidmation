"""Stripe API integration — customer management, checkout, webhooks."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import stripe
from sqlalchemy.orm import Session

from vidmation.billing.plans import get_plan
from vidmation.config.settings import get_settings
from vidmation.db.engine import get_session
from vidmation.models.user import SubscriptionTier, User

logger = logging.getLogger(__name__)


class StripeService:
    """Thin wrapper around the Stripe SDK, wired to our DB models."""

    def __init__(self) -> None:
        settings = get_settings()
        key = settings.stripe_secret_key.get_secret_value()
        if not key:
            raise RuntimeError(
                "VIDMATION_STRIPE_SECRET_KEY is not configured. "
                "Set it in .env or the environment before using billing features."
            )
        stripe.api_key = key

    # ── Customer management ───────────────────────────────────────────────

    def create_customer(self, user_id: str, email: str) -> str:
        """Create a Stripe customer for an existing user and persist the ID.

        Returns the Stripe customer ID (``cus_xxx``).
        """
        db: Session = get_session()
        try:
            user = db.get(User, user_id)
            if user is None:
                raise ValueError(f"User {user_id!r} not found")

            # Don't create a duplicate
            if user.stripe_customer_id:
                return user.stripe_customer_id

            customer = stripe.Customer.create(
                email=email,
                metadata={"vidmation_user_id": user_id},
            )
            user.stripe_customer_id = customer.id
            db.commit()
            logger.info("Created Stripe customer %s for user %s", customer.id, user_id[:8])
            return customer.id
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    # ── Checkout ──────────────────────────────────────────────────────────

    def create_checkout_session(
        self,
        user_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
    ) -> str:
        """Create a Stripe Checkout session and return the URL.

        If the user doesn't yet have a Stripe customer, one is created first.
        """
        db: Session = get_session()
        try:
            user = db.get(User, user_id)
            if user is None:
                raise ValueError(f"User {user_id!r} not found")

            # Ensure customer exists
            customer_id = user.stripe_customer_id
            if not customer_id:
                customer_id = self.create_customer(user_id, user.email)

            session = stripe.checkout.Session.create(
                customer=customer_id,
                mode="subscription",
                line_items=[{"price": price_id, "quantity": 1}],
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={"vidmation_user_id": user_id},
                subscription_data={"metadata": {"vidmation_user_id": user_id}},
            )
            logger.info(
                "Created checkout session %s for user %s (price=%s)",
                session.id,
                user_id[:8],
                price_id,
            )
            return session.url  # type: ignore[return-value]
        finally:
            db.close()

    # ── Customer Portal ───────────────────────────────────────────────────

    def create_portal_session(self, user_id: str, return_url: str | None = None) -> str:
        """Create a Stripe Customer Portal session.

        Returns the portal URL so the customer can manage their subscription.
        """
        db: Session = get_session()
        try:
            user = db.get(User, user_id)
            if user is None:
                raise ValueError(f"User {user_id!r} not found")
            if not user.stripe_customer_id:
                raise ValueError("User has no Stripe customer — cannot open portal")

            params: dict = {"customer": user.stripe_customer_id}
            if return_url:
                params["return_url"] = return_url

            session = stripe.billing_portal.Session.create(**params)
            return session.url  # type: ignore[return-value]
        finally:
            db.close()

    # ── Webhook handling ──────────────────────────────────────────────────

    def handle_webhook(self, payload: bytes, signature: str) -> None:
        """Verify and dispatch a Stripe webhook event."""
        settings = get_settings()
        webhook_secret = settings.stripe_webhook_secret.get_secret_value()
        if not webhook_secret:
            raise RuntimeError("VIDMATION_STRIPE_WEBHOOK_SECRET is not configured")

        try:
            event = stripe.Webhook.construct_event(payload, signature, webhook_secret)
        except stripe.SignatureVerificationError:
            logger.warning("Stripe webhook signature verification failed")
            raise
        except ValueError:
            logger.warning("Invalid Stripe webhook payload")
            raise

        event_type: str = event["type"]
        logger.info("Processing Stripe event: %s (%s)", event_type, event["id"])

        handler = {
            "checkout.session.completed": self._on_checkout_completed,
            "customer.subscription.updated": self._on_subscription_updated,
            "customer.subscription.deleted": self._on_subscription_deleted,
            "invoice.payment_failed": self._on_payment_failed,
        }.get(event_type)

        if handler:
            handler(event["data"]["object"])
        else:
            logger.debug("Unhandled Stripe event type: %s", event_type)

    # ── Internal webhook handlers ─────────────────────────────────────────

    def _resolve_user(self, obj: dict, db: Session) -> User | None:
        """Try to find the user from Stripe object metadata or customer ID."""
        # First try our metadata
        user_id = (obj.get("metadata") or {}).get("vidmation_user_id")
        if user_id:
            user = db.get(User, user_id)
            if user:
                return user

        # Fall back to stripe customer ID lookup
        customer_id = obj.get("customer")
        if customer_id:
            from sqlalchemy import select

            stmt = select(User).where(User.stripe_customer_id == customer_id)
            user = db.scalars(stmt).first()
            if user:
                return user

        return None

    def _tier_from_price(self, price_id: str) -> SubscriptionTier:
        """Map a Stripe Price ID back to our tier enum."""
        settings = get_settings()
        price_map = {
            settings.stripe_price_pro_monthly: SubscriptionTier.PRO,
            settings.stripe_price_pro_annual: SubscriptionTier.PRO,
            settings.stripe_price_business_monthly: SubscriptionTier.BUSINESS,
            settings.stripe_price_business_annual: SubscriptionTier.BUSINESS,
        }
        return price_map.get(price_id, SubscriptionTier.PRO)

    def _on_checkout_completed(self, session_obj: dict) -> None:
        """Handle checkout.session.completed — activate the subscription."""
        db: Session = get_session()
        try:
            user = self._resolve_user(session_obj, db)
            if user is None:
                logger.error(
                    "checkout.session.completed: could not resolve user for session %s",
                    session_obj.get("id"),
                )
                return

            subscription_id = session_obj.get("subscription")
            if not subscription_id:
                logger.warning("Checkout session has no subscription")
                return

            # Fetch the subscription to get price info
            sub = stripe.Subscription.retrieve(subscription_id)
            price_id = sub["items"]["data"][0]["price"]["id"]
            tier = self._tier_from_price(price_id)
            plan = get_plan(tier.value)

            # Update user
            user.subscription_tier = tier
            user.subscription_status = "active"
            user.monthly_video_limit = plan["videos_per_month"]

            # Set expiry from current_period_end
            period_end = sub.get("current_period_end")
            if period_end:
                user.subscription_expires_at = datetime.fromtimestamp(
                    period_end, tz=timezone.utc
                )

            # Persist stripe customer if not already set
            customer_id = session_obj.get("customer")
            if customer_id and not user.stripe_customer_id:
                user.stripe_customer_id = customer_id

            db.commit()
            logger.info(
                "Activated %s subscription for user %s",
                tier.value,
                user.id[:8],
            )
        except Exception:
            db.rollback()
            logger.exception("Failed to process checkout.session.completed")
        finally:
            db.close()

    def _on_subscription_updated(self, sub_obj: dict) -> None:
        """Handle customer.subscription.updated — plan changes, renewals."""
        db: Session = get_session()
        try:
            user = self._resolve_user(sub_obj, db)
            if user is None:
                logger.error(
                    "subscription.updated: could not resolve user for sub %s",
                    sub_obj.get("id"),
                )
                return

            status = sub_obj.get("status", "active")
            price_id = sub_obj["items"]["data"][0]["price"]["id"]
            tier = self._tier_from_price(price_id)
            plan = get_plan(tier.value)

            user.subscription_tier = tier
            user.subscription_status = (
                "active" if status in ("active", "trialing") else status
            )
            user.monthly_video_limit = plan["videos_per_month"]

            period_end = sub_obj.get("current_period_end")
            if period_end:
                user.subscription_expires_at = datetime.fromtimestamp(
                    period_end, tz=timezone.utc
                )

            db.commit()
            logger.info(
                "Subscription updated for user %s: tier=%s status=%s",
                user.id[:8],
                tier.value,
                user.subscription_status,
            )
        except Exception:
            db.rollback()
            logger.exception("Failed to process customer.subscription.updated")
        finally:
            db.close()

    def _on_subscription_deleted(self, sub_obj: dict) -> None:
        """Handle customer.subscription.deleted — downgrade to free."""
        db: Session = get_session()
        try:
            user = self._resolve_user(sub_obj, db)
            if user is None:
                logger.error(
                    "subscription.deleted: could not resolve user for sub %s",
                    sub_obj.get("id"),
                )
                return

            free_plan = get_plan("free")
            user.subscription_tier = SubscriptionTier.FREE
            user.subscription_status = "cancelled"
            user.monthly_video_limit = free_plan["videos_per_month"]
            user.subscription_expires_at = None

            db.commit()
            logger.info("Subscription cancelled — user %s downgraded to free", user.id[:8])
        except Exception:
            db.rollback()
            logger.exception("Failed to process customer.subscription.deleted")
        finally:
            db.close()

    def _on_payment_failed(self, invoice_obj: dict) -> None:
        """Handle invoice.payment_failed — mark subscription as past_due."""
        db: Session = get_session()
        try:
            user = self._resolve_user(invoice_obj, db)
            if user is None:
                logger.error(
                    "invoice.payment_failed: could not resolve user for invoice %s",
                    invoice_obj.get("id"),
                )
                return

            user.subscription_status = "past_due"
            db.commit()
            logger.warning("Payment failed for user %s — marked past_due", user.id[:8])

            # TODO: send dunning email via Resend
        except Exception:
            db.rollback()
            logger.exception("Failed to process invoice.payment_failed")
        finally:
            db.close()
