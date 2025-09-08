import stripe
import os

# Set your Stripe secret key (ensure you load from env in production)
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# -------- Payment Intents --------

def create_payment_intent(amount, currency, customer_id=None, payment_method_types=["card"], **kwargs):
    """
    Create a Stripe PaymentIntent.
    :param amount: Amount in the smallest currency unit (e.g., cents)
    :param currency: Currency code (e.g., 'usd')
    :param customer_id: Optional Stripe customer ID
    :param payment_method_types: List of allowed payment method types
    :param kwargs: Additional Stripe PaymentIntent parameters
    """
    return stripe.PaymentIntent.create(
        amount=amount,
        currency=currency,
        customer=customer_id,
        payment_method_types=payment_method_types,
        **kwargs
    )

def retrieve_payment_intent(payment_intent_id):
    """Retrieve a PaymentIntent by ID."""
    return stripe.PaymentIntent.retrieve(payment_intent_id)

def update_payment_intent(payment_intent_id, **kwargs):
    """Update a PaymentIntent."""
    return stripe.PaymentIntent.modify(payment_intent_id, **kwargs)

def cancel_payment_intent(payment_intent_id):
    """Cancel a PaymentIntent."""
    return stripe.PaymentIntent.cancel(payment_intent_id)

def list_payment_intents(limit=10, **kwargs):
    """List PaymentIntents."""
    return stripe.PaymentIntent.list(limit=limit, **kwargs)

# -------- Events (Webhooks) --------

def retrieve_event(event_id):
    """Retrieve a Stripe event by ID."""
    return stripe.Event.retrieve(event_id)

def list_events(limit=10, **kwargs):
    """List Stripe events."""
    return stripe.Event.list(limit=limit,