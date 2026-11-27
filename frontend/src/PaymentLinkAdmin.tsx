import { useCallback, useEffect, useState, type FormEvent } from "react";
import { createRoot } from "react-dom/client";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { paymentLinkError, paymentLinkRequest } from "@/lib/paymentLinks";

type StaffAction = { kind: "send" | "revoke"; reference: string };
type GatewayConfig = Record<string, string[]>;
const gatewayNames: Record<string, string> = { stripe: "Stripe", flutterwave: "Flutterwave" };
const api = "/api/payment-links/admin/";

function PaymentLinkAdmin() {
  const [generate, setGenerate] = useState(false);
  const [action, setAction] = useState<StaffAction | null>(null);
  const [gateways, setGateways] = useState<GatewayConfig>({});
  const [gateway, setGateway] = useState("");
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");

  const copy = async (value: string) => {
    try {
      await navigator.clipboard.writeText(value);
      setToast("Payment link copied.");
    } catch {
      setToast("Clipboard unavailable. Copy the link directly.");
    }
  };

  useEffect(() => {
    const onClick = (event: MouseEvent) => {
      const target = (event.target as HTMLElement).closest<HTMLElement>("[data-payment-link-action]");
      if (!target) return;
      const { paymentLinkAction, url, reference } = target.dataset;
      if (paymentLinkAction === "copy" && url) void copy(url);
      if ((paymentLinkAction === "send" || paymentLinkAction === "revoke") && reference) {
        setError("");
        setAction({ kind: paymentLinkAction, reference });
      }
    };
    document.addEventListener("click", onClick);
    return () => document.removeEventListener("click", onClick);
  }, []);

  useEffect(() => {
    if (!toast) return;
    const timeout = window.setTimeout(() => setToast(""), 4000);
    return () => window.clearTimeout(timeout);
  }, [toast]);

  const showGenerator = useCallback(async () => {
    setGenerate(true);
    setLoading(true);
    setUrl("");
    setError("");
    try {
      const { status, data } = await paymentLinkRequest<{ gateways: GatewayConfig }>(api + "config/");
      if (status !== 200) throw new Error(paymentLinkError(data));
      setGateways(data.gateways);
      setGateway(Object.keys(data.gateways)[0] || "");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load the payment gateways.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const button = document.querySelector<HTMLAnchorElement>("[data-payment-link-generator]");
    const open = (event: MouseEvent) => {
      if (window.location.protocol !== "https:") return;
      if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      void showGenerator();
    };
    button?.addEventListener("click", open);
    return () => button?.removeEventListener("click", open);
  }, [showGenerator]);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    const fields = new FormData(event.currentTarget);
    try {
      const expiration = new Date(String(fields.get("expires_at")));
      const { status, data } = await paymentLinkRequest<{ url: string; email_queued: boolean }>(api + "create/", {
        ...Object.fromEntries(fields.entries()),
        expires_at: expiration.toISOString(),
        send_email: fields.has("send_email"),
      });
      if (status !== 201) throw new Error(paymentLinkError(data));
      setUrl(data.url);
      setToast(data.email_queued ? "Payment link generated. Email queued." : "Payment link generated.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not generate the link.");
    } finally {
      setBusy(false);
    }
  };

  const confirmAction = async () => {
    if (!action) return;
    setBusy(true);
    setError("");
    try {
      const { status, data } = await paymentLinkRequest<object>(api + action.reference + "/" + action.kind + "/", {});
      if (status !== 200) throw new Error(paymentLinkError(data));
      if (action.kind === "revoke") {
        sessionStorage.setItem("rukkies:payment-link:notice", "Payment link revoked.");
        window.location.reload();
        return;
      }
      setAction(null);
      setToast("Payment link email queued.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not update the payment link.");
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    const saved = sessionStorage.getItem("rukkies:payment-link:notice");
    if (saved) {
      sessionStorage.removeItem("rukkies:payment-link:notice");
      setToast(saved);
    }
  }, []);

  return (
    <>
      <Dialog open={generate} onOpenChange={(open) => { if (!busy) setGenerate(open); }}>
        <DialogContent className="payment-links-dialog">
          <DialogHeader>
            <DialogTitle>Generate Payment Link</DialogTitle>
            <DialogDescription>Request one payment using a link that expires at the time you set.</DialogDescription>
          </DialogHeader>
          {error && generate && <p className="errornote" role="alert">{error}</p>}
          {loading ? <p role="status">Loading payment gateways…</p> : url ? (
            <div className="payment-links-generated">
              <label>Payment link<input readOnly value={url} onFocus={(event) => event.currentTarget.select()} /></label>
              <button type="button" className="button" onClick={() => copy(url)}>Copy payment link</button>
              <a className="button" href={url + "?preview=1"} target="_blank" rel="noopener noreferrer">Preview payment page</a>
            </div>
          ) : gateway ? (
            <form className="payment-links-form" onSubmit={submit}>
              <label>Customer full name<input name="customer_name" autoComplete="off" maxLength={160} required /></label>
              <label>Customer email<input name="customer_email" autoComplete="off" type="email" maxLength={254} required /></label>
              <label>Gateway<select name="gateway" value={gateway} onChange={(event) => setGateway(event.target.value)}>
                {Object.keys(gateways).map((item) => <option key={item} value={item}>{gatewayNames[item]}</option>)}
              </select></label>
              <label>Currency<select key={gateway} name="currency" required>{gateways[gateway].map((currency) => <option key={currency}>{currency}</option>)}</select></label>
              <label>Payment amount<input name="amount" type="number" step=".01" min="1" max="99999999.99" required /></label>
              <label>Expires (your local time)<input name="expires_at" type="datetime-local" required /></label>
              <label className="payment-links-wide">Description<textarea name="description" maxLength={240} rows={3} required /></label>
              <label className="payment-links-wide">Order reference (optional)<input name="order_reference" maxLength={64} /></label>
              <label className="payment-links-wide payment-links-checkbox"><input name="send_email" type="checkbox" /> Send payment link via email</label>
              <button className="button default" type="submit" disabled={busy}>{busy ? "Generating…" : "Generate Link"}</button>
            </form>
          ) : <p>Payment gateways are unavailable. Check the payment-link settings on the web service.</p>}
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(action)} onOpenChange={(open) => { if (!open && !busy) setAction(null); }}>
        <DialogContent className="payment-links-dialog">
          <DialogHeader>
            <DialogTitle>{action?.kind === "revoke" ? "Revoke payment link?" : "Send payment link?"}</DialogTitle>
            <DialogDescription>{action?.kind === "revoke" ? "The recipient will lose access to this payment link." : "The payment link will be emailed to the customer on file."}</DialogDescription>
          </DialogHeader>
          {error && action && <p className="errornote" role="alert">{error}</p>}
          <div className="payment-links-toolbar">
            <button className="button" type="button" onClick={() => setAction(null)} disabled={busy}>Cancel</button>
            <button className="button default" type="button" onClick={confirmAction} disabled={busy}>
              {busy ? "Working…" : action?.kind === "revoke" ? "Revoke link" : "Queue email"}
            </button>
          </div>
        </DialogContent>
      </Dialog>
      {toast && <p className="payment-links-toast" role="status">{toast}</p>}
    </>
  );
}

const root = document.querySelector<HTMLElement>("[data-payment-link-tools]");
if (root) createRoot(root).render(<PaymentLinkAdmin />);
