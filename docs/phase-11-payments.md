# Phase 11 — Payments (Razorpay + Stripe)

## Files

```
payments/
├── base.py       # PaymentBackend protocol
├── razorpay.py   # Orders, signature verify, webhooks
├── stripe.py     # Checkout sessions, webhooks
└── factory.py    # get_payment_backend()

modules/payments/
├── router.py
├── service.py
├── repository.py
└── schemas.py

database/models/payment.py
```

## Configuration

```env
PAYMENT_DEFAULT_PROVIDER=razorpay   # or stripe

RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=
RAZORPAY_WEBHOOK_SECRET=

STRIPE_SECRET_KEY=
STRIPE_PUBLISHABLE_KEY=
STRIPE_WEBHOOK_SECRET=
```

## API

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/payments/create-order` | Create Razorpay order or Stripe checkout session |
| `POST` | `/api/v1/payments/verify/razorpay` | Verify Razorpay payment signature |
| `POST` | `/api/v1/payments/verify/stripe` | Verify Stripe checkout session |
| `GET` | `/api/v1/payments/{id}` | Payment status (requires `payments.view`) |
| `POST` | `/api/v1/payments/webhook/razorpay` | Razorpay webhook |
| `POST` | `/api/v1/payments/webhook/stripe` | Stripe webhook |

## Status

✅ Complete
