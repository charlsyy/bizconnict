import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def create_stripe_session(order, success_url=None, cancel_url=None):
    """
    Creates a Stripe Checkout Session.
    Returns (session_url, session_id, error)
    """
    try:
        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY

        site_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')

        if not success_url:
            success_url = (
                f"{site_url}/shop/order/{order.id}/payment/stripe/success/"
                f"?session_id={{CHECKOUT_SESSION_ID}}"
            )
        if not cancel_url:
            cancel_url = f"{site_url}/shop/order/{order.id}/payment/"

        line_items = []
        for item in order.items.all():
            line_items.append({
                'price_data': {
                    'currency': 'php',
                    'product_data': {'name': item.product_name},
                    'unit_amount': int(item.unit_price * 100),
                },
                'quantity': item.quantity,
            })

        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                'order_id': str(order.id),
                'order_number': order.order_number,
            },
        )
        return session.url, session.id, None

    except Exception as e:
        logger.error(f"Stripe session error: {e}")
        return None, None, str(e)


def verify_stripe_session(session_id):
    """
    Returns 'paid', 'unpaid', or 'error'
    """
    try:
        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY
        session = stripe.checkout.Session.retrieve(session_id)
        return session.payment_status
    except Exception as e:
        logger.error(f"Stripe verify error: {e}")
        return 'error'