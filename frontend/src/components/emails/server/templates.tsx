import React from "react";

type ButtonVariant = "primary" | "secondary";

const colors = {
  bg: "#F5EFE6",
  panel: "#FFFFFF",
  text: "#3A2F28",
  muted: "#7A6E63",
  border: "#E7DDD0",
  gold: "#C6A96B",
  goldDark: "#B6944D",
  soft: "#FBF8F2",
  successBg: "#ECFDF3",
  successText: "#027A48",
  warningBg: "#FFFAEB",
  warningText: "#B54708",
};

const styles = {
  body: {
    margin: 0,
    padding: "24px 12px",
    backgroundColor: colors.bg,
    color: colors.text,
    fontFamily: "Inter, Arial, sans-serif",
  } as React.CSSProperties,
  wrapper: {
    maxWidth: 640,
    margin: "0 auto",
    backgroundColor: colors.panel,
    borderRadius: 18,
    overflow: "hidden",
    boxShadow: "0 12px 32px rgba(58,47,40,0.08)",
    border: `1px solid ${colors.border}`,
  } as React.CSSProperties,
  header: {
    background: "linear-gradient(135deg, #2F2721, #493A2F)",
    padding: "24px 28px",
    color: "#fff",
  } as React.CSSProperties,
  brand: {
    margin: 0,
    fontFamily: "Georgia, 'Times New Roman', serif",
    fontSize: 24,
    letterSpacing: "0.06em",
    color: "#F2DDAB",
  } as React.CSSProperties,
  content: {
    padding: "28px",
    lineHeight: 1.55,
  } as React.CSSProperties,
  title: {
    margin: "0 0 8px",
    fontFamily: "Georgia, 'Times New Roman', serif",
    fontSize: 28,
    lineHeight: 1.15,
    color: colors.text,
  } as React.CSSProperties,
  subtitle: {
    margin: "0 0 20px",
    color: colors.muted,
    fontSize: 14,
  } as React.CSSProperties,
  p: {
    margin: "0 0 16px",
    color: colors.muted,
    fontSize: 14,
  } as React.CSSProperties,
  card: {
    backgroundColor: colors.soft,
    border: `1px solid ${colors.border}`,
    borderRadius: 14,
    padding: "16px",
    margin: "16px 0 20px",
  } as React.CSSProperties,
  row: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    gap: 12,
    padding: "8px 0",
    borderBottom: `1px solid ${colors.border}`,
  } as React.CSSProperties,
  rowLast: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    gap: 12,
    padding: "8px 0",
    borderBottom: "none",
  } as React.CSSProperties,
  rowLabel: {
    margin: 0,
    color: colors.muted,
    fontSize: 12,
    fontWeight: 600,
  } as React.CSSProperties,
  rowValue: {
    margin: 0,
    color: colors.text,
    fontSize: 13,
    textAlign: "right",
    fontWeight: 600,
  } as React.CSSProperties,
  footer: {
    backgroundColor: "#2F2721",
    color: "rgba(255,255,255,0.82)",
    padding: "18px 28px 24px",
    borderTop: `1px solid rgba(255,255,255,0.08)`,
  } as React.CSSProperties,
  footerSmall: {
    margin: "8px 0 0",
    fontSize: 12,
    color: "rgba(255,255,255,0.65)",
  } as React.CSSProperties,
};

function formatYear() {
  return new Date().getFullYear();
}

function EmailShell({
  children,
  siteName = "De-Rukkies Collections",
  supportEmail,
}: {
  children: React.ReactNode;
  siteName?: string;
  supportEmail?: string;
}) {
  return (
    <html>
      <body style={styles.body}>
        <div style={styles.wrapper}>
          <div style={styles.header}>
            <p style={styles.brand}>{siteName}</p>
          </div>
          {children}
          <div style={styles.footer}>
            <p style={{ margin: 0, fontSize: 13 }}>
              {siteName}
            </p>
            <p style={styles.footerSmall}>
              &copy; {formatYear()} {siteName}. All rights reserved.
            </p>
            {supportEmail ? (
              <p style={styles.footerSmall}>Support: {supportEmail}</p>
            ) : null}
          </div>
        </div>
      </body>
    </html>
  );
}

function EmailButton({
  href,
  label,
  variant = "primary",
}: {
  href?: string;
  label: string;
  variant?: ButtonVariant;
}) {
  if (!href) return null;
  const primary = variant === "primary";
  return (
    <a
      href={href}
      style={{
        display: "inline-block",
        padding: "12px 22px",
        borderRadius: 9999,
        textDecoration: "none",
        fontSize: 13,
        fontWeight: 700,
        letterSpacing: "0.03em",
        marginRight: 8,
        marginBottom: 8,
        backgroundColor: primary ? colors.gold : "transparent",
        color: primary ? "#fff" : colors.text,
        border: primary ? `1px solid ${colors.gold}` : `1px solid ${colors.border}`,
      }}
    >
      {label}
    </a>
  );
}

function InfoRows({ rows }: { rows: Array<{ label: string; value?: string | null }> }) {
  const filtered = rows.filter((row) => row.value);
  return (
    <div style={styles.card}>
      <table role="presentation" width="100%" cellPadding={0} cellSpacing={0} style={{ borderCollapse: "collapse" }}>
        <tbody>
          {filtered.map((row, index) => (
            <tr key={row.label}>
              <td
                style={{
                  padding: "8px 0",
                  borderBottom: index === filtered.length - 1 ? "none" : `1px solid ${colors.border}`,
                  color: colors.muted,
                  fontSize: 12,
                  fontWeight: 600,
                  textAlign: "left",
                }}
              >
                {row.label}
              </td>
              <td
                style={{
                  padding: "8px 0",
                  borderBottom: index === filtered.length - 1 ? "none" : `1px solid ${colors.border}`,
                  color: colors.text,
                  fontSize: 13,
                  fontWeight: 600,
                  textAlign: "right",
                }}
              >
                {row.value}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

type TemplateProps = Record<string, unknown>;
type EmailOrderItem = {
  name?: string;
  quantity?: number | string;
  unitPriceText?: string;
  lineTotalText?: string;
  imageUrl?: string;
};

function asText(v: unknown, fallback = "") {
  const s = typeof v === "string" ? v.trim() : String(v ?? "").trim();
  return s || fallback;
}

function titleCaseProvider(v: unknown) {
  const raw = asText(v);
  if (!raw) return "";
  return raw.charAt(0).toUpperCase() + raw.slice(1);
}

function SignupVerificationEmail(props: TemplateProps) {
  const userName = asText(props.userName, "there");
  const verificationUrl = asText(props.verificationUrl);
  const verificationCode = asText(props.verificationCode);
  const siteName = asText(props.siteName, "De-Rukkies Collections");
  const supportEmail = asText(props.supportEmail);
  const expiresText = asText(props.expiresText, "This link may expire in 24 hours.");

  return (
    <EmailShell siteName={siteName} supportEmail={supportEmail}>
      <div style={styles.content}>
        <h1 style={styles.title}>Verify Your Email</h1>
        <p style={styles.subtitle}>One last step to activate your account</p>
        <p style={styles.p}>
          Hi {userName}, thanks for signing up with {siteName}. Please confirm your email address to activate your account.
        </p>
        {verificationCode ? (
          <div style={{ ...styles.card, textAlign: "center" }}>
            <p style={{ ...styles.rowLabel, marginBottom: 8 }}>Verification Code</p>
            <p
              style={{
                margin: 0,
                fontSize: 28,
                letterSpacing: "0.35em",
                color: colors.goldDark,
                fontWeight: 700,
              }}
            >
              {verificationCode}
            </p>
          </div>
        ) : null}
        <div style={{ margin: "8px 0 18px" }}>
          <EmailButton href={verificationUrl} label="Verify My Email" />
        </div>
        <p style={styles.p}>{expiresText}</p>
        <p style={{ ...styles.p, marginBottom: 0 }}>
          If you did not create this account, you can safely ignore this email.
        </p>
      </div>
    </EmailShell>
  );
}

function LoginWarningEmail(props: TemplateProps) {
  const userName = asText(props.userName, "there");
  const loginTime = asText(props.loginTime);
  const device = asText(props.device);
  const ipAddress = asText(props.ipAddress);
  const location = asText(props.location);
  const accountUrl = asText(props.accountUrl);
  const resetPasswordUrl = asText(props.resetPasswordUrl);
  const siteName = asText(props.siteName, "De-Rukkies Collections");
  const supportEmail = asText(props.supportEmail);

  return (
    <EmailShell siteName={siteName} supportEmail={supportEmail}>
      <div style={styles.content}>
        <h1 style={styles.title}>Unusual Login Detected</h1>
        <p style={styles.subtitle}>Security alert for your account</p>
        <p style={styles.p}>
          Hi {userName}, we detected a new sign-in to your {siteName} account. If this was you, no action is needed.
        </p>
        <InfoRows
          rows={[
            { label: "Time", value: loginTime },
            { label: "Device", value: device },
            { label: "IP Address", value: ipAddress },
            { label: "Location", value: location },
          ]}
        />
        <div
          style={{
            backgroundColor: colors.warningBg,
            color: colors.warningText,
            border: "1px solid #FEDF89",
            borderRadius: 12,
            padding: "12px 14px",
            marginBottom: 18,
            fontSize: 13,
          }}
        >
          If this was not you, change your password immediately and review your account activity.
        </div>
        <div>
          <EmailButton href={accountUrl} label="Review Account" />
          <EmailButton href={resetPasswordUrl} label="Change Password" variant="secondary" />
        </div>
      </div>
    </EmailShell>
  );
}

function PaymentConfirmationEmail(props: TemplateProps) {
  const siteName = asText(props.siteName, "De-Rukkies Collections");
  const supportEmail = asText(props.supportEmail);
  const orderNumber = asText(props.orderNumber);
  const amountText = asText(props.amountText);
  const paymentMethod = asText(props.paymentMethod);
  const paymentDate = asText(props.paymentDate);
  const provider = titleCaseProvider(props.provider);
  const statusText = asText(props.statusText, "Successful");
  const transactionId = asText(props.transactionId);
  const orderUrl = asText(props.orderUrl);
  const userName = asText(props.userName);
  const supportEmailSafe = asText(props.supportEmail);
  const orderReference = orderNumber ? (orderNumber.startsWith("#") ? orderNumber : `#${orderNumber}`) : "";

  return (
    <EmailShell siteName={siteName} supportEmail={supportEmail}>
      <div style={styles.content}>
        <div style={{ textAlign: "center", marginBottom: 12 }}>
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: "9999px",
              margin: "0 auto 12px",
              background: "rgba(198,169,107,0.20)",
              color: colors.goldDark,
              fontSize: 24,
              lineHeight: "56px",
              fontWeight: 700,
            }}
          >
            &#128179;
          </div>
          <h1 style={{ ...styles.title, marginBottom: 6 }}>Payment Received</h1>
          <p style={{ ...styles.subtitle, marginBottom: 0 }}>
            {transactionId ? `Transaction ID: ${transactionId}` : "Transaction completed"}
          </p>
          <div style={{ width: 48, height: 2, background: colors.gold, margin: "14px auto 0" }} />
        </div>

        <p style={styles.p}>We&apos;ve successfully processed your payment. Here are your transaction details:</p>

        <InfoRows
          rows={[
            { label: "Amount Paid", value: amountText },
            { label: "Payment Method", value: paymentMethod },
            { label: "Date", value: paymentDate },
            { label: "Order Reference", value: orderReference },
            { label: "Status", value: "✓ Successful" },
          ]}
        />

        <div
          style={{
            backgroundColor: "#FFF8E8",
            border: "1px solid #F3E4B5",
            borderRadius: 12,
            padding: "12px 14px",
            marginBottom: 18,
            fontSize: 12,
            color: colors.muted,
          }}
        >
          A receipt has been sent to your email. If you did not authorize this transaction,
          {supportEmailSafe ? (
            <>
              {" "}
              please{" "}
              <a href={`mailto:${supportEmailSafe}`} style={{ color: colors.goldDark, fontWeight: 700, textDecoration: "none" }}>
                contact our support team
              </a>{" "}
              immediately.
            </>
          ) : (
            " please contact our support team immediately."
          )}
        </div>

        <div style={{ textAlign: "center" }}>
          <EmailButton href={orderUrl} label="View Order Details" />
        </div>
      </div>
    </EmailShell>
  );
}

function ShippingEmail(props: TemplateProps) {
  const siteName = asText(props.siteName, "De-Rukkies Collections");
  const supportEmail = asText(props.supportEmail);
  const userName = asText(props.userName);
  const orderNumber = asText(props.orderNumber);
  const carrier = asText(props.carrier);
  const trackingNumber = asText(props.trackingNumber);
  const estimatedDelivery = asText(props.estimatedDelivery);
  const deliveryAddress = asText(props.deliveryAddress);
  const trackingUrl = asText(props.trackingUrl);
  const orderUrl = asText(props.orderUrl);

  return (
    <EmailShell siteName={siteName} supportEmail={supportEmail}>
      <div style={styles.content}>
        <h1 style={styles.title}>Your Order Is On Its Way</h1>
        <p style={styles.subtitle}>{orderNumber ? `Order ${orderNumber}` : "Shipping update"}</p>
        {userName ? <p style={styles.p}>Hi {userName}, good news. Your order has shipped.</p> : null}
        <InfoRows
          rows={[
            { label: "Carrier", value: carrier },
            { label: "Tracking Number", value: trackingNumber },
            { label: "Estimated Delivery", value: estimatedDelivery },
            { label: "Delivery Address", value: deliveryAddress },
          ]}
        />
        <div>
          <EmailButton href={trackingUrl || orderUrl} label="Track Package" />
          <EmailButton href={orderUrl} label="View Order" variant="secondary" />
        </div>
      </div>
    </EmailShell>
  );
}

function OrderConfirmationEmail(props: TemplateProps) {
  const siteName = asText(props.siteName, "De-Rukkies Collections");
  const supportEmail = asText(props.supportEmail);
  const userName = asText(props.userName);
  const orderNumber = asText(props.orderNumber);
  const statusText = asText(props.statusText);
  const totalText = asText(props.totalText);
  const shippingText = asText(props.shippingText);
  const taxText = asText(props.taxText);
  const subtotalText = asText(props.subtotalText);
  const addressText = asText(props.addressText);
  const orderUrl = asText(props.orderUrl);
  const items = (Array.isArray(props.items) ? props.items : []) as EmailOrderItem[];

  return (
    <EmailShell siteName={siteName} supportEmail={supportEmail}>
      <div style={styles.content}>
        <div style={{ textAlign: "center", marginBottom: 12 }}>
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: "9999px",
              margin: "0 auto 12px",
              background: "rgba(198,169,107,0.20)",
              color: colors.goldDark,
              fontSize: 28,
              lineHeight: "56px",
              fontWeight: 700,
            }}
          >
            &#10003;
          </div>
          <h1 style={{ ...styles.title, marginBottom: 6 }}>Order Confirmed!</h1>
          <p style={{ ...styles.subtitle, marginBottom: 0 }}>{orderNumber ? `Order ${orderNumber}` : "Your order has been received"}</p>
          <div style={{ width: 48, height: 2, background: colors.gold, margin: "14px auto 0" }} />
        </div>

        <p style={styles.p}>Thank you for your purchase! We&apos;re preparing your items with care. Here&apos;s a summary of your order:</p>

        {items.length ? (
          <div style={styles.card}>
            <p style={{ ...styles.rowLabel, marginBottom: 10 }}>Order Summary</p>
            <div>
              {items.map((item, index) => {
                const name = asText(item?.name, "Product");
                const qty = asText(item?.quantity, "1");
                const unitPriceText = asText(item?.unitPriceText);
                const lineTotalText = asText(item?.lineTotalText);
                const imageUrl = asText(item?.imageUrl);
                return (
                  <div
                    key={`${name}-${index}`}
                    style={{
                      background: "#FFFFFF",
                      border: `1px solid ${colors.border}`,
                      borderRadius: 10,
                      padding: 12,
                      marginBottom: index === items.length - 1 ? 0 : 10,
                    }}
                  >
                    <table role="presentation" width="100%" cellPadding={0} cellSpacing={0} style={{ borderCollapse: "collapse" }}>
                      <tbody>
                        <tr>
                          <td style={{ verticalAlign: "top" }}>
                            <table role="presentation" cellPadding={0} cellSpacing={0} style={{ borderCollapse: "collapse" }}>
                              <tbody>
                                <tr>
                                  {imageUrl ? (
                                    <td style={{ paddingRight: 12, verticalAlign: "top" }}>
                                      <img
                                        src={imageUrl}
                                        alt={name}
                                        width={80}
                                        height={80}
                                        style={{
                                          width: 80,
                                          height: 80,
                                          objectFit: "cover",
                                          borderRadius: 8,
                                          display: "block",
                                          border: `1px solid ${colors.border}`,
                                          background: "#fff",
                                        }}
                                      />
                                    </td>
                                  ) : null}
                                  <td style={{ verticalAlign: "top" }}>
                                    <p style={{ margin: 0, color: colors.text, fontSize: 13, fontWeight: 700 }}>{name}</p>
                                    <p style={{ margin: "6px 0 0", color: colors.muted, fontSize: 12 }}>
                                      Qty: {qty}
                                    </p>
                                    {unitPriceText ? (
                                      <p style={{ margin: "4px 0 0", color: colors.muted, fontSize: 12 }}>
                                        {unitPriceText} each
                                      </p>
                                    ) : null}
                                  </td>
                                </tr>
                              </tbody>
                            </table>
                          </td>
                          <td
                            style={{
                              verticalAlign: "middle",
                              textAlign: "right",
                              whiteSpace: "nowrap",
                              color: colors.text,
                              fontSize: 14,
                              fontWeight: 700,
                              paddingLeft: 12,
                            }}
                          >
                            {lineTotalText}
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                );
              })}
            </div>
          </div>
        ) : null}

        <InfoRows
          rows={[
            { label: "Order Number", value: orderNumber },
            { label: "Status", value: statusText },
            { label: "Subtotal", value: subtotalText },
            { label: "Tax", value: taxText },
            { label: "Total", value: totalText },
          ]}
        />

        {addressText ? (
          <div style={{ ...styles.card, marginTop: 0 }}>
            <p style={{ ...styles.rowLabel, marginBottom: 8 }}>Shipping Address</p>
            <p style={{ margin: 0, color: colors.text, fontSize: 13, whiteSpace: "pre-line" }}>{addressText}</p>
          </div>
        ) : null}

        <div style={{ textAlign: "center" }}>
          <EmailButton href={orderUrl} label="Track Your Order" />
        </div>
      </div>
    </EmailShell>
  );
}

function SubscriptionEmail(props: TemplateProps) {
  const siteName = asText(props.siteName, "De-Rukkies Collections");
  const supportEmail = asText(props.supportEmail);
  const userName = asText(props.userName);
  const shopUrl = asText(props.shopUrl);
  const promoCode = asText(props.promoCode, "SUBSCRIBED10");

  return (
    <EmailShell siteName={siteName} supportEmail={supportEmail}>
      <div style={styles.content}>
        <h1 style={styles.title}>You&apos;re Subscribed</h1>
        <p style={styles.subtitle}>Welcome to the inner circle</p>
        <p style={styles.p}>
          {userName ? `Hi ${userName}, ` : ""}
          you&apos;ve successfully subscribed to {siteName} updates. You will receive new arrivals, offers, and promotions.
        </p>
        <div style={styles.card}>
          <p style={{ ...styles.rowLabel, marginBottom: 10 }}>What You&apos;ll Get</p>
          <ul style={{ margin: 0, paddingLeft: 18, color: colors.text, fontSize: 13, lineHeight: 1.6 }}>
            <li>Early access to new arrivals</li>
            <li>Subscriber-only discounts and flash-sale alerts</li>
            <li>Curated product updates and style inspiration</li>
          </ul>
        </div>
        <div
          style={{
            ...styles.card,
            backgroundColor: "#FFF8E8",
            borderColor: "#F3E4B5",
            marginTop: 0,
          }}
        >
          <p style={{ margin: 0, color: colors.text, fontSize: 13 }}>
            Welcome gift: use code <strong style={{ color: colors.goldDark }}>{promoCode}</strong> on your next order.
          </p>
        </div>
        <EmailButton href={shopUrl} label="Start Shopping" />
      </div>
    </EmailShell>
  );
}

function WelcomeEmail(props: TemplateProps) {
  const siteName = asText(props.siteName, "De-Rukkies Collections");
  const supportEmail = asText(props.supportEmail);
  const userName = asText(props.userName, "there");
  const shopUrl = asText(props.shopUrl);
  const promoCode = asText(props.promoCode, "WELCOME15");

  return (
    <EmailShell siteName={siteName} supportEmail={supportEmail}>
      <div style={styles.content}>
        <h1 style={styles.title}>Welcome to the Family</h1>
        <p style={styles.subtitle}>Your account is now active</p>
        <p style={styles.p}>
          Hi {userName}, your email has been verified successfully and your account is now active.
        </p>
        <p style={styles.p}>
          We&apos;re glad to have you at {siteName}. You can now log in, manage your account, and start shopping.
        </p>
        <div style={styles.card}>
          <p style={{ margin: 0, color: colors.text, fontSize: 13 }}>
            Use code <strong style={{ color: colors.goldDark }}>{promoCode}</strong> for a welcome discount on your first order.
          </p>
        </div>
        <EmailButton href={shopUrl} label="Start Shopping" />
      </div>
    </EmailShell>
  );
}

export function getEmailTemplateElement(templateName: string, props: TemplateProps) {
  switch (templateName) {
    case "SignupVerificationEmail":
      return <SignupVerificationEmail {...props} />;
    case "LoginWarningEmail":
      return <LoginWarningEmail {...props} />;
    case "PaymentConfirmationEmail":
      return <PaymentConfirmationEmail {...props} />;
    case "ShippingEmail":
      return <ShippingEmail {...props} />;
    case "OrderConfirmationEmail":
      return <OrderConfirmationEmail {...props} />;
    case "SubscriptionEmail":
      return <SubscriptionEmail {...props} />;
    case "WelcomeEmail":
      return <WelcomeEmail {...props} />;
    default:
      throw new Error(`Unknown email template: ${templateName}`);
  }
}
