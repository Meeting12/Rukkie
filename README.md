# De-Rukkies Collections

## Assistant API

Endpoint: `POST /api/assistant/chat/`

Request body:

```json
{
  "message": "find glow soap",
  "session_id": null,
  "context": null
}
```

Response body:

```json
{
  "reply": "Top matches for 'glow soap':\n- Glow Soap - $15.00 (In stock)",
  "suggestions": ["Show featured products", "Find skincare products", "Search by category"],
  "intent": "product_search",
  "session_id": "2ab9f0f655f24cc1a167887f5e437f26"
}
```

Example curl:

```bash
curl -X POST http://127.0.0.1:8000/api/assistant/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message":"track order ABC123DEF456","session_id":null,"context":null}'
```

Notes:
- Intent routing is deterministic (custom keyword/regex rules first).
- Shipping, returns, and payment replies use DB-backed `AssistantPolicy` records.
- Product search replies include top 5 matching products with price and stock status.

## One-time payment links

In Django admin, select **Generate Payment Link** on the dashboard or under **Store → Payment Links**. The button opens a modal when JavaScript loads and a standard admin form otherwise. It appears for superusers and staff with **Can add payment link**. The list includes status and gateway filters, search, per-currency revenue, and each link's copy, preview, delivery, transaction, revoke, and receipt actions. Existing shop checkout retains its own transactions. An optional order reference is informational and does not change an order or its inventory.

### Local HTTPS testing

Payment-link operations require HTTPS. With a local certificate covering `127.0.0.1`, run `python manage.py runserver_https --certfile <cert.pem> --keyfile <key.pem>` and sign in at `https://127.0.0.1:8443/admin/`. This development command binds only to loopback and requires `DEBUG=True`. Set `PAYMENT_LINK_ORIGIN=https://127.0.0.1:8443` and use sandbox gateway credentials for local testing. Test provider webhooks on your HTTPS staging service.

### Render deployment

1. Deploy all code together, including `store/migrations/0015_payment_links.py`. The existing Render build runs `npm run build:django` and `collectstatic`. Its pre-deploy command runs `python manage.py migrate --noinput`. Keep both steps enabled. Use PostgreSQL in production.
2. Configure the values below. Share the same signing key and origin between `rukkie-web` and `rukkie-worker`. Generate a private random key with `python -c "import secrets; print(secrets.token_urlsafe(48))"`. Changing it invalidates links issued under the old key.
3. Keep the existing Celery worker, Redis URLs, and SMTP delivery configured. A single Celery Beat scheduler (`celery -A Rukkie beat --loglevel=info` using the same broker) runs the built-in two-minute recovery job for pending email deliveries, provider reconciliation, and rate-limit cleanup. Webhooks and immediate email enqueue also work without Beat.
4. Test each enabled provider with staging keys, its webhook, and the staging HTTPS origin before enabling it on the production payment-link screen. Confirm the link goes from Processing to Paid only after provider verification, the receipt opens, emails arrive, and a second attempt cannot charge.

| Environment variable | Service | Value |
| --- | --- | --- |
| `PAYMENT_LINK_ORIGIN` | Web and worker | Bare HTTPS origin, e.g. `https://rukkies.com` |
| `PAYMENT_LINK_SIGNING_KEY` | Web and worker | Same random secret, at least 32 characters. Leave unset to keep creation disabled. |
| `PAYMENT_LINK_ADMIN_EMAIL` | Web | Recipient of payment alerts. Defaults to the existing contact mailbox. |
| `STRIPE_SECRET_KEY` | Web and reconciliation worker | Existing Stripe API key for the same account and mode as its webhook. |
| `PAYMENT_LINK_STRIPE_WEBHOOK_SECRET` | Web and worker | Signing secret for the new Stripe endpoint. |
| `FLUTTERWAVE_SECRET_KEY` | Web and reconciliation worker | Existing Flutterwave v3 API key. |
| `PAYMENT_LINK_FLUTTERWAVE_WEBHOOK_SECRET` | Web and worker | Optional override. Defaults to `FLUTTERWAVE_WEBHOOK_SECRET`. |

- **Stripe** uses `POST /api/payment-links/webhook/stripe/`. Subscribe to `checkout.session.completed`, `checkout.session.expired`, and `checkout.session.async_payment_succeeded`. Keep the existing order webhook configured separately. Use the final HTTPS hostname for each endpoint.
- **Flutterwave** can keep its existing `POST /api/payments/webhook/flutterwave/` endpoint. It routes payment-link references to the dedicated handler. A separate account may use `POST /api/payment-links/webhook/flutterwave/`. Enable charge webhooks. Both handlers independently verify the transaction against Flutterwave.
- Stripe supports USD, EUR, GBP, CAD, and AUD, and Flutterwave supports NGN and USD, subject to merchant account support. Both use hosted card checkout. Stripe requires advance session expiry, so a new checkout cannot begin during the last 31 minutes of its link. An open checkout can be resumed from the same browser while its provider session remains valid.
- Administrators can revoke pending or failed links. Processing links stay reserved until the gateway confirms an outcome. If checkout creation times out with no provider reference, investigate the attempt reference in the gateway dashboard before issuing any replacement link.
- Receipt downloads are printable HTML. Keep payment-link paths and API bodies out of proxy logs and analytics. Provider-hosted checkout keeps card entry off Rukkies; confirm applicable PCI requirements with your acquirer.

### Files and checks

- Models and migration: `store/models.py`, `store/migrations/0015_payment_links.py`.
- State, gateways, and API: `store/payment_links.py`, `store/payment_link_gateways.py`, `store/payment_link_serializers.py`, `store/payment_link_views.py`, `store/payment_link_urls.py`, `Rukkie/urls.py`.
- Admin and checkout compatibility: `store/admin.py`, `store/payment_link_admin.py`, `store/views.py`, `templates/admin/index.html`, `templates/admin/store/paymentlink/`.
- Frontend: `frontend/src/PaymentLinkAdmin.tsx`, `frontend/src/paymentLinkPage.tsx`, `frontend/src/pages/PaymentLink.tsx`, `frontend/src/lib/paymentLinks.ts`, `frontend/src/components/products/ProductCard.tsx`, `frontend/vite.config.ts`, `templates/payment_link_page.html`, `store/static/store/admin/payment-links.css`.
- Email: `store/payment_link_mail.py`, `store/tasks.py`, `templates/payment_link_email.html`, `templates/payment_link_receipt.html`.
- Configuration and redaction: `.env.example`, `Rukkie/settings.py`, `Rukkie/security_headers.py`, `Rukkie/gunicorn_logger.py`, `Rukkie/sentry.py`.
- Tests: `store/test_payment_links.py` and the existing Stripe checkout fixture in `store/tests.py`. Run `python manage.py test store.test_payment_links store.tests`. Use a disposable PostgreSQL database for the concurrency test. It is skipped on SQLite because SQLite does not implement the row locks under test.
