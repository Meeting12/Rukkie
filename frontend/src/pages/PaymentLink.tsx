import { useEffect, useState } from "react";
import { CheckCircle2, CircleHelp, Clock, Loader2, LockKeyhole, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { paymentLinkRequest, paymentLinkError, type PaymentLinkState } from "@/lib/paymentLinks";

type PaymentDetails = {
  status: PaymentLinkState;
  name?: string;
  description?: string;
  amount?: string;
  currency?: string;
  reference?: string;
  support?: string;
  can_resume?: boolean;
};

const messages: Record<PaymentLinkState, [string, string]> = {
  invalid: ["Payment link unavailable", "Open the full link from your payment email or contact Rukkies for help."],
  pending: ["Complete your payment", "Review the details before continuing to secure checkout."],
  processing: ["Payment being confirmed", "If you already paid, wait for confirmation before trying again."],
  paid: ["Payment already received", "Your payment has been confirmed. Please check your email for the receipt."],
  failed: ["The last payment was unsuccessful", "You can try again if the link is still valid."],
  expired: ["Payment link expired", "Contact Rukkies to request a new link."],
  revoked: ["Payment link revoked", "Contact Rukkies if you still need to make this payment."],
  too_late: ["Checkout time is too short", "There isn’t enough time left for the payment provider to open checkout. Contact Rukkies for a new link."],
  attempt_limit: ["Retry limit reached", "Contact Rukkies for help completing your payment."],
};

const returnKey = "rukkies:payment-link:return";

function getToken() {
  const path = window.location.pathname.split("/").filter(Boolean);
  if (path[1] !== "return") return path[1] || "";
  try {
    const token = sessionStorage.getItem(returnKey);
    if (token && /^[a-f0-9]{32}\.[a-f0-9]{64}$/.test(token)) {
      window.history.replaceState(null, "", "/pay/" + token);
      return token;
    }
  } catch {
    // The payment remains verifiable from the original link.
  }
  return "";
}

export default function PaymentLink() {
  const [token] = useState(getToken);
  const [details, setDetails] = useState<PaymentDetails | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);
  const preview = new URLSearchParams(window.location.search).get("preview") === "1";

  useEffect(() => {
    let stopped = false;
    let retry: number | undefined;
    const update = async () => {
      if (!/^[a-f0-9]{32}\.[a-f0-9]{64}$/.test(token)) {
        if (!stopped) setDetails({ status: "invalid" });
        return;
      }
      try {
        const { data } = await paymentLinkRequest<PaymentDetails>("/api/payment-links/public/detail/", { token });
        if (stopped) return;
        if (!data.status) throw new Error(paymentLinkError(data));
        setDetails(data);
        if (data.status === "processing" && !preview) retry = window.setTimeout(update, 5000);
      } catch (reason) {
        if (stopped) return;
        setError(reason instanceof Error ? reason.message : "Could not reach the payment service.");
      }
    };
    void update();
    return () => { stopped = true; window.clearTimeout(retry); };
  }, [token, preview, refresh]);

  const start = async () => {
    setBusy(true);
    setError("");
    try {
      const { data } = await paymentLinkRequest<{ status?: PaymentLinkState; checkout_url?: string }>(
        "/api/payment-links/public/start/", { token },
      );
      if (data.checkout_url) {
        const checkout = new URL(data.checkout_url);
        if (checkout.protocol !== "https:" || !["checkout.stripe.com", "checkout.flutterwave.com"].includes(checkout.host)) {
          throw new Error("Could not open the payment provider.");
        }
        try { sessionStorage.setItem(returnKey, token); } catch { /* Optional return navigation. */ }
        window.location.assign(checkout.href);
        return;
      }
      if (data.status && details) setDetails({ ...details, status: data.status, can_resume: false });
      if (data.detail || !data.status) setError(paymentLinkError(data));
      if (data.status === "processing") setRefresh((value) => value + 1);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not open checkout.");
    } finally {
      setBusy(false);
    }
  };

  const state = details?.status;
  const payable = state === "pending" || state === "failed" || (state === "processing" && details?.can_resume);
  const showDetails = details && ["pending", "failed", "processing", "too_late", "attempt_limit"].includes(details.status);

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center px-4 py-8 sm:px-8">
      <p className="mb-6 text-center font-serif text-2xl font-bold tracking-tight" aria-label="De-Rukkies Collections">
        <span className="text-primary">De-Rukkies</span> Collections
      </p>
      <Card className="overflow-hidden shadow-lg">
        <CardHeader className="border-b bg-muted/35">
          <div className="flex items-center gap-2 text-sm font-medium text-primary">
            {state === "paid" ? <CheckCircle2 className="size-4" /> : <ShieldCheck className="size-4" />}
            Secure payment {preview && "· Preview"}
          </div>
          <h1 className="font-serif text-3xl font-bold">{state ? messages[state][0] : "Payment details"}</h1>
          {state && <p className="text-sm text-muted-foreground">{messages[state][1]}</p>}
        </CardHeader>
        <CardContent className="space-y-5 p-6">
          {!details && !error && <p role="status" className="flex items-center gap-2"><Loader2 className="size-4 animate-spin" /> Loading payment details…</p>}
          {showDetails && (
            <dl className="space-y-4 break-words">
              <div><dt className="text-sm text-muted-foreground">Amount due</dt><dd className="text-3xl font-semibold">{details.currency} {details.amount}</dd></div>
              <div><dt className="text-sm text-muted-foreground">Customer</dt><dd>{details.name}</dd></div>
              <div><dt className="text-sm text-muted-foreground">Description</dt><dd>{details.description}</dd></div>
              <div><dt className="text-sm text-muted-foreground">Payment reference</dt><dd className="break-all font-mono text-sm">{details.reference}</dd></div>
            </dl>
          )}
          {error && <p role="alert" className="rounded-md border border-destructive/40 p-3 text-sm">{error}</p>}
          {payable && !preview && (
            <Button className="w-full" size="lg" disabled={busy} onClick={start}>
              {busy ? <Loader2 className="mr-2 size-4 animate-spin" /> : <LockKeyhole className="mr-2 size-4" />}
              {busy ? "Opening secure checkout…" : details?.can_resume ? "Resume secure checkout" : state === "failed" ? "Retry payment" : "Pay Now"}
            </Button>
          )}
          {state === "processing" && !details?.can_resume && <p role="status" className="flex items-center gap-2 text-sm"><Clock className="size-4" /> Checking payment status…</p>}
          <p className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            <CircleHelp className="size-4" /> Need help?
            <a className="font-medium text-primary underline" href={details?.support ? "mailto:" + details.support : "/contact"}>Contact Rukkies</a>
          </p>
        </CardContent>
      </Card>
    </main>
  );
}
