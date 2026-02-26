import json
import logging
import os
import subprocess
from pathlib import Path
from html import escape

from django.conf import settings

logger = logging.getLogger(__name__)

DEFAULT_PUBLIC_SITE_URL = "https://www.rukkies.com"


def get_public_site_url(request=None):
    if request is not None:
        try:
            return request.build_absolute_uri("/").rstrip("/")
        except Exception:
            logger.exception("email.react build_absolute_uri_failed")

    configured = (
        getattr(settings, "PUBLIC_SITE_URL", "")
        or getattr(settings, "SITE_URL", "")
        or getattr(settings, "FRONTEND_URL", "")
    )
    if configured:
        return str(configured).strip().rstrip("/")

    origins = getattr(settings, "CORS_ALLOWED_ORIGINS", []) or []
    if isinstance(origins, str):
        origins = [o.strip() for o in origins.split(",") if o.strip()]
    for origin in origins:
        if origin.startswith("http://") or origin.startswith("https://"):
            return origin.rstrip("/")

    return DEFAULT_PUBLIC_SITE_URL


def _tsx_command(frontend_dir: Path):
    bin_dir = frontend_dir / "node_modules" / ".bin"
    if os.name == "nt":
        tsx_bin = bin_dir / "tsx.cmd"
    else:
        tsx_bin = bin_dir / "tsx"
    if tsx_bin.exists():
        return [str(tsx_bin)]
    return ["npx", "--no-install", "tsx"]


def render_react_email_html(template_name: str, props: dict | None = None) -> str | None:
    if not template_name:
        return None

    frontend_dir = Path(getattr(settings, "BASE_DIR", Path.cwd())) / "frontend"
    script_path = frontend_dir / "scripts" / "render-email.ts"
    if not script_path.exists():
        logger.warning("email.react renderer_missing script=%s", script_path)
        fallback = _render_builtin_email_html(template_name, props or {})
        if fallback:
            logger.info("email.react using_builtin_fallback template=%s reason=missing_script", template_name)
        return fallback

    timeout_seconds = int(getattr(settings, "REACT_EMAIL_RENDER_TIMEOUT_SECONDS", 12) or 12)
    payload = {"template": str(template_name), "props": props or {}}
    cmd = _tsx_command(frontend_dir) + [str(script_path)]
    env = os.environ.copy()
    env.setdefault("NODE_ENV", "production")

    try:
        result = subprocess.run(
            cmd,
            cwd=str(frontend_dir),
            input=json.dumps(payload, ensure_ascii=False),
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            env=env,
            check=False,
        )
    except Exception:
        logger.exception("email.react render_exec_failed template=%s", template_name)
        fallback = _render_builtin_email_html(template_name, props or {})
        if fallback:
            logger.info("email.react using_builtin_fallback template=%s reason=exec_failed", template_name)
        return fallback

    if result.returncode != 0:
        stderr = (result.stderr or "").strip().splitlines()
        logger.warning(
            "email.react render_failed template=%s code=%s detail=%s",
            template_name,
            result.returncode,
            (stderr[-1] if stderr else "unknown"),
        )
        fallback = _render_builtin_email_html(template_name, props or {})
        if fallback:
            logger.info("email.react using_builtin_fallback template=%s reason=render_failed", template_name)
        return fallback

    html = (result.stdout or "").strip()
    if not html:
        logger.warning("email.react render_empty template=%s", template_name)
        fallback = _render_builtin_email_html(template_name, props or {})
        if fallback:
            logger.info("email.react using_builtin_fallback template=%s reason=empty_output", template_name)
        return fallback
    return html


def _text(value, default=""):
    text = str(value or "").strip()
    return text or default


def _money(value):
    return _text(value)


def _card(rows):
    items = []
    for label, value in rows:
        value = _text(value)
        if not value:
            continue
        items.append(
            f"""
            <tr>
              <td style="padding:8px 0;color:#7A6E63;font-size:12px;font-weight:600;">{escape(str(label))}</td>
              <td style="padding:8px 0;color:#3A2F28;font-size:13px;font-weight:600;text-align:right;">{escape(value)}</td>
            </tr>
            """
        )
    if not items:
        return ""
    return (
        '<div style="background:#FBF8F2;border:1px solid #E7DDD0;border-radius:14px;padding:14px 16px;margin:16px 0 20px;">'
        '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;">'
        + "".join(items)
        + "</table></div>"
    )


def _button(href, label, variant="primary"):
    href = _text(href)
    if not href:
        return ""
    primary = variant == "primary"
    return (
        f'<a href="{escape(href)}" '
        'style="display:inline-block;padding:12px 22px;border-radius:9999px;text-decoration:none;'
        'font-size:13px;font-weight:700;letter-spacing:.03em;margin-right:8px;margin-bottom:8px;'
        f'background:{("#C6A96B" if primary else "transparent")};'
        f'color:{("#fff" if primary else "#3A2F28")};'
        f'border:1px solid {("#C6A96B" if primary else "#E7DDD0")};">'
        f"{escape(str(label))}</a>"
    )


def _wrap_email(*, title, subtitle="", body_html="", site_name="De-Rukkies Collections", support_email=""):
    year = "2026"
    return f"""<!doctype html>
<html>
<body style="margin:0;padding:24px 12px;background:#F5EFE6;color:#3A2F28;font-family:Inter,Arial,sans-serif;">
  <div style="max-width:640px;margin:0 auto;background:#fff;border-radius:18px;overflow:hidden;border:1px solid #E7DDD0;box-shadow:0 12px 32px rgba(58,47,40,.08);">
    <div style="background:linear-gradient(135deg,#2F2721,#493A2F);padding:24px 28px;">
      <p style="margin:0;font-family:Georgia,'Times New Roman',serif;font-size:24px;letter-spacing:.06em;color:#F2DDAB;">{escape(site_name)}</p>
    </div>
    <div style="padding:28px;line-height:1.55;">
      <h1 style="margin:0 0 8px;font-family:Georgia,'Times New Roman',serif;font-size:28px;line-height:1.15;color:#3A2F28;">{escape(title)}</h1>
      {f'<p style="margin:0 0 20px;color:#7A6E63;font-size:14px;">{escape(subtitle)}</p>' if subtitle else ''}
      {body_html}
    </div>
    <div style="background:#2F2721;color:rgba(255,255,255,.82);padding:18px 28px 24px;border-top:1px solid rgba(255,255,255,.08);">
      <p style="margin:0;font-size:13px;">{escape(site_name)}</p>
      <p style="margin:8px 0 0;font-size:12px;color:rgba(255,255,255,.65);">© {year} {escape(site_name)}. All rights reserved.</p>
      {f'<p style="margin:8px 0 0;font-size:12px;color:rgba(255,255,255,.65);">Support: {escape(support_email)}</p>' if support_email else ''}
    </div>
  </div>
</body>
</html>"""


def _render_builtin_email_html(template_name: str, props: dict) -> str | None:
    site_name = _text(props.get("siteName"), "De-Rukkies Collections")
    support_email = _text(props.get("supportEmail"))

    if template_name == "SignupVerificationEmail":
        user_name = _text(props.get("userName"), "there")
        verification_url = _text(props.get("verificationUrl"))
        verification_code = _text(props.get("verificationCode"))
        expires_text = _text(props.get("expiresText"), "This verification link may expire automatically.")
        code_html = ""
        if verification_code:
            code_html = (
                '<div style="background:#FBF8F2;border:1px solid #E7DDD0;border-radius:14px;padding:16px;text-align:center;margin:16px 0 20px;">'
                '<p style="margin:0 0 8px;color:#7A6E63;font-size:12px;font-weight:600;">Verification Code</p>'
                f'<p style="margin:0;color:#B6944D;font-size:26px;font-weight:700;letter-spacing:.25em;">{escape(verification_code)}</p>'
                "</div>"
            )
        body_html = (
            f'<p style="margin:0 0 16px;color:#7A6E63;font-size:14px;">Hi {escape(user_name)}, thanks for signing up with {escape(site_name)}. Please confirm your email address to activate your account.</p>'
            + code_html
            + f'<div style="margin:8px 0 18px;">{_button(verification_url, "Verify My Email")}</div>'
            + f'<p style="margin:0 0 12px;color:#7A6E63;font-size:14px;">{escape(expires_text)}</p>'
            + '<p style="margin:0;color:#7A6E63;font-size:14px;">If you did not create this account, you can safely ignore this email.</p>'
        )
        return _wrap_email(title="Verify Your Email", subtitle="One last step to activate your account", body_html=body_html, site_name=site_name, support_email=support_email)

    if template_name == "LoginWarningEmail":
        body_html = (
            f'<p style="margin:0 0 16px;color:#7A6E63;font-size:14px;">Hi {escape(_text(props.get("userName"), "there"))}, we detected a new sign-in to your account. If this was you, no action is needed.</p>'
            + _card([
                ("Time", props.get("loginTime")),
                ("Device", props.get("device")),
                ("IP Address", props.get("ipAddress")),
                ("Location", props.get("location")),
            ])
            + '<div style="background:#FFFAEB;border:1px solid #FEDF89;color:#B54708;border-radius:12px;padding:12px 14px;margin:0 0 18px;font-size:13px;">If this was not you, change your password immediately and review your account activity.</div>'
            + _button(props.get("accountUrl"), "Review Account")
            + _button(props.get("resetPasswordUrl"), "Change Password", variant="secondary")
        )
        return _wrap_email(title="Unusual Login Detected", subtitle="Security alert for your account", body_html=body_html, site_name=site_name, support_email=support_email)

    if template_name == "PaymentConfirmationEmail":
        body_html = (
            f'<p style="margin:0 0 16px;color:#7A6E63;font-size:14px;">{escape(("Hi " + _text(props.get("userName")) + ", your payment was processed successfully.") if _text(props.get("userName")) else "Your payment was processed successfully.")}</p>'
            + _card([
                ("Amount Paid", _money(props.get("amountText"))),
                ("Provider", _text(props.get("provider")).title()),
                ("Payment Method", props.get("paymentMethod")),
                ("Date", props.get("paymentDate")),
                ("Transaction ID", props.get("transactionId")),
                ("Status", _text(props.get("statusText"), "Successful")),
            ])
            + '<div style="background:#ECFDF3;border:1px solid #ABEFC6;color:#027A48;border-radius:12px;padding:12px 14px;margin:0 0 18px;font-size:13px;">We have received your payment and your order is now being processed.</div>'
            + _button(props.get("orderUrl"), "View Order")
        )
        return _wrap_email(
            title="Payment Received",
            subtitle=_text(props.get("orderNumber"), "Payment confirmed"),
            body_html=body_html,
            site_name=site_name,
            support_email=support_email,
        )

    if template_name == "ShippingEmail":
        body_html = (
            f'<p style="margin:0 0 16px;color:#7A6E63;font-size:14px;">{escape(("Hi " + _text(props.get("userName")) + ", good news. Your order has shipped.") if _text(props.get("userName")) else "Good news. Your order has shipped.")}</p>'
            + _card([
                ("Carrier", props.get("carrier")),
                ("Tracking Number", props.get("trackingNumber")),
                ("Estimated Delivery", props.get("estimatedDelivery")),
                ("Delivery Address", props.get("deliveryAddress")),
            ])
            + _button(_text(props.get("trackingUrl")) or _text(props.get("orderUrl")), "Track Package")
            + _button(props.get("orderUrl"), "View Order", variant="secondary")
        )
        return _wrap_email(
            title="Your Order Is On Its Way",
            subtitle=_text(props.get("orderNumber"), "Shipping update"),
            body_html=body_html,
            site_name=site_name,
            support_email=support_email,
        )

    if template_name == "OrderConfirmationEmail":
        items_html = ""
        raw_items = props.get("items")
        if isinstance(raw_items, list) and raw_items:
            item_cards = []
            for item in raw_items:
                if not isinstance(item, dict):
                    continue
                name = _text(item.get("name"), "Product")
                qty = _text(item.get("quantity"), "1")
                unit_price = _text(item.get("unitPriceText"))
                line_total = _text(item.get("lineTotalText"))
                image_url = _text(item.get("imageUrl"))
                qty_line = f"Qty: {qty}" + (f" - {unit_price} each" if unit_price else "")
                item_cards.append(
                    (
                        '<div style="background:#FFFFFF;border:1px solid #E7DDD0;border-radius:10px;padding:12px;'
                        'margin-bottom:10px;">'
                        '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;">'
                        '<tr>'
                        '<td style="vertical-align:top;">'
                        '<table role="presentation" cellspacing="0" cellpadding="0" style="border-collapse:collapse;"><tr>'
                        + (f'<td style="padding-right:12px;vertical-align:top;"><img src="{escape(image_url)}" alt="{escape(name)}" width="80" height="80" style="width:80px;height:80px;object-fit:cover;border-radius:8px;display:block;border:1px solid #E7DDD0;background:#fff;"></td>' if image_url else '')
                        + '<td style="vertical-align:top;">'
                        + f'<p style="margin:0;color:#3A2F28;font-size:13px;font-weight:700;">{escape(name)}</p>'
                        + f'<p style="margin:6px 0 0;color:#7A6E63;font-size:12px;">Qty: {escape(qty)}</p>'
                        + (f'<p style="margin:4px 0 0;color:#7A6E63;font-size:12px;">{escape(unit_price)} each</p>' if unit_price else '')
                        + '</td></tr></table>'
                        '</td>'
                        + f'<td style="vertical-align:middle;text-align:right;white-space:nowrap;color:#3A2F28;font-size:14px;font-weight:700;padding-left:12px;">{escape(line_total)}</td>'
                        '</tr></table></div>'
                    )
                )
            if item_cards:
                item_cards[-1] = item_cards[-1].replace('margin-bottom:10px;', 'margin-bottom:0;', 1)
                items_html = (
                    '<div style="background:#FBF8F2;border:1px solid #E7DDD0;border-radius:14px;padding:14px 16px;margin:16px 0 20px;">'
                    '<p style="margin:0 0 10px;color:#7A6E63;font-size:12px;font-weight:600;">Order Summary</p>'
                    + "".join(item_cards)
                    + "</div>"
                )
        intro = (
            ("Hi " + _text(props.get("userName")) + ", We're preparing your items with care. Here's a summary of your order.")
            if _text(props.get("userName"))
            else "We're preparing your items with care. Here's a summary of your order."
        )
        body_html = (
            '<div style="text-align:center;margin-bottom:12px;">'
            '<div style="width:56px;height:56px;border-radius:9999px;margin:0 auto 12px;background:rgba(198,169,107,0.20);color:#B6944D;font-size:28px;line-height:56px;font-weight:700;">&#10003;</div>'
            '</div>'
            + f'<p style="margin:0 0 16px;color:#7A6E63;font-size:14px;">{escape(intro)}</p>'
            + items_html
            + _card([
                ("Order Number", props.get("orderNumber")),
                ("Status", props.get("statusText")),
                ("Subtotal", props.get("subtotalText")),
                ("Shipping", props.get("shippingText")),
                ("Tax", props.get("taxText")),
                ("Total", _money(props.get("totalText"))),
            ])
        )
        address_text = _text(props.get("addressText"))
        if address_text:
            body_html += (
                '<div style="background:#FBF8F2;border:1px solid #E7DDD0;border-radius:14px;padding:16px;margin:0 0 18px;">'
                '<p style="margin:0 0 8px;color:#7A6E63;font-size:12px;font-weight:600;">Shipping Address</p>'
                f'<p style="margin:0;color:#3A2F28;font-size:13px;white-space:pre-line;">{escape(address_text)}</p>'
                '</div>'
            )
        body_html += f'<div style="text-align:center;">{_button(props.get("orderUrl"), "Track Your Order")}</div>'
        return _wrap_email(
            title="Order Confirmed!",
            subtitle=_text(props.get("orderNumber"), "Your order has been received"),
            body_html=body_html,
            site_name=site_name,
            support_email=support_email,
        )

    if template_name == "SubscriptionEmail":
        promo_code = _text(props.get("promoCode"), "SUBSCRIBED10")
        body_html = (
            f'<p style="margin:0 0 16px;color:#7A6E63;font-size:14px;">You&apos;ve successfully subscribed to {escape(site_name)} updates. You will receive new arrivals, offers, and promotions.</p>'
            '<div style="background:#FBF8F2;border:1px solid #E7DDD0;border-radius:14px;padding:16px;margin:16px 0 14px;">'
            '<p style="margin:0 0 8px;color:#7A6E63;font-size:12px;font-weight:600;">What you&apos;ll get</p>'
            '<ul style="margin:0;padding-left:18px;color:#3A2F28;font-size:13px;line-height:1.6;">'
            '<li>Early access to new arrivals</li>'
            '<li>Subscriber-only discounts and flash-sale alerts</li>'
            '<li>Curated product updates and style inspiration</li>'
            '</ul></div>'
            '<div style="background:#FFF8E8;border:1px solid #F3E4B5;border-radius:12px;padding:12px 14px;margin:0 0 18px;font-size:13px;color:#3A2F28;">'
            f'Welcome gift: use code <strong style="color:#B6944D;">{escape(promo_code)}</strong> on your next order.'
            '</div>'
            + _button(props.get("shopUrl"), "Start Shopping")
        )
        return _wrap_email(title="You're Subscribed", subtitle="Welcome to the inner circle", body_html=body_html, site_name=site_name, support_email=support_email)

    if template_name == "WelcomeEmail":
        promo_code = _text(props.get("promoCode"), "WELCOME15")
        user_name = _text(props.get("userName"), "there")
        body_html = (
            f'<p style="margin:0 0 16px;color:#7A6E63;font-size:14px;">Hi {escape(user_name)}, your email has been verified successfully and your account is now active.</p>'
            f'<p style="margin:0 0 16px;color:#7A6E63;font-size:14px;">We&apos;re glad to have you at {escape(site_name)}. You can now log in, manage your account, and start shopping.</p>'
            '<div style="background:#FBF8F2;border:1px solid #E7DDD0;border-radius:14px;padding:16px;margin:16px 0 18px;">'
            f'<p style="margin:0;color:#3A2F28;font-size:13px;">Use code <strong style="color:#B6944D;">{escape(promo_code)}</strong> for a welcome discount on your first order.</p>'
            '</div>'
            + _button(props.get("shopUrl"), "Start Shopping")
        )
        return _wrap_email(title="Welcome to the Family", subtitle="Your account is now active", body_html=body_html, site_name=site_name, support_email=support_email)

    return None
