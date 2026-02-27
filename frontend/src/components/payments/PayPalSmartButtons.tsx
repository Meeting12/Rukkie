import { useEffect, useMemo, useRef, useState } from "react";
import { fetchJSON } from "@/lib/api";

type PayPalSmartButtonsProps = {
  orderId: number;
  currency?: string;
  onSuccess: (payload: any) => void | Promise<void>;
  onError?: (message: string) => void;
  onCancel?: () => void;
};

type PayPalButtonInstance = {
  isEligible: () => boolean;
  render: (selector: string) => Promise<void>;
};

type PayPalNamespace = {
  FUNDING?: {
    PAYPAL?: string;
    CARD?: string;
  };
  getFundingSources?: () => string[];
  Buttons: (config: Record<string, any>) => PayPalButtonInstance;
};

declare global {
  interface Window {
    paypal?: PayPalNamespace;
  }
}

const PAYPAL_SDK_SCRIPT_ID = "paypal-js-sdk";

async function loadPayPalScript(clientId: string, currency: string) {
  const sdkUrl =
    `https://www.paypal.com/sdk/js?client-id=${encodeURIComponent(clientId)}` +
    `&currency=${encodeURIComponent(currency)}` +
    "&intent=capture&components=buttons";

  const existing = document.getElementById(PAYPAL_SDK_SCRIPT_ID);
  if (existing && window.paypal && (existing as HTMLScriptElement).src === sdkUrl) {
    return;
  }
  if (existing) {
    existing.remove();
    (window as any).paypal = undefined;
  }

  await new Promise<void>((resolve, reject) => {
    const script = document.createElement("script");
    script.id = PAYPAL_SDK_SCRIPT_ID;
    script.src = sdkUrl;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Unable to load PayPal SDK."));
    document.body.appendChild(script);
  });
}

export function PayPalSmartButtons({
  orderId,
  currency = "USD",
  onSuccess,
  onError,
  onCancel,
}: PayPalSmartButtonsProps) {
  const cardContainerId = useMemo(() => `pp-card-${orderId}`, [orderId]);
  const [clientId, setClientId] = useState("");
  const [sdkReady, setSdkReady] = useState(false);
  const [loading, setLoading] = useState(true);
  const [renderingButtons, setRenderingButtons] = useState(false);
  const [message, setMessage] = useState("");
  const [cardEligible, setCardEligible] = useState(true);
  const [walletFallbackShown, setWalletFallbackShown] = useState(false);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setMessage("");
    setSdkReady(false);
    setCardEligible(true);
    setWalletFallbackShown(false);

    (async () => {
      try {
        const config = await fetchJSON("/api/paypal/config/");
        const backendClientId = String(config?.client_id || "").trim();
        const backendCurrency = String(config?.currency || currency || "USD").trim().toUpperCase();
        if (!backendClientId) {
          throw new Error("PayPal is not configured.");
        }
        if (!active || !mountedRef.current) return;
        setClientId(backendClientId);
        await loadPayPalScript(backendClientId, backendCurrency);
        if (!active || !mountedRef.current) return;
        setSdkReady(true);
      } catch (err: any) {
        if (!active || !mountedRef.current) return;
        const msg = err?.message || "Unable to initialize PayPal.";
        setMessage(msg);
        onError?.(msg);
      } finally {
        if (active && mountedRef.current) {
          setLoading(false);
        }
      }
    })();

    return () => {
      active = false;
    };
  }, [currency, onError, orderId]);

  useEffect(() => {
    if (!sdkReady || !window.paypal) return;
    setRenderingButtons(true);
    setMessage("");

    const cardRoot = document.getElementById(cardContainerId);
    if (cardRoot) cardRoot.innerHTML = "";

    const sharedConfig = {
      style: { shape: "rect", layout: "vertical", label: "pay" },
      createOrder: async () => {
        const response = await fetchJSON("/api/paypal/create-order/", {
          method: "POST",
          body: JSON.stringify({
            order_id: orderId,
            currency,
          }),
        });
        const createdOrderId = String(response?.orderID || "").trim();
        if (!createdOrderId) {
          throw new Error("Unable to create PayPal order.");
        }
        return createdOrderId;
      },
      onApprove: async (data: any) => {
        const approvedOrderId = String(data?.orderID || "").trim();
        if (!approvedOrderId) {
          throw new Error("Missing PayPal order ID.");
        }
        const captureResponse = await fetchJSON("/api/paypal/capture-order/", {
          method: "POST",
          body: JSON.stringify({
            order_id: orderId,
            paypal_order_id: approvedOrderId,
          }),
        });
        await onSuccess(captureResponse);
      },
      onCancel: () => {
        setMessage("Payment was cancelled. You can try again.");
        onCancel?.();
      },
      onError: (err: any) => {
        const msg = err?.message || "PayPal payment failed.";
        setMessage(msg);
        onError?.(msg);
      },
    };

    const renderButtons = async () => {
      const renderGenericFallback = async (fallbackMessage: string) => {
        try {
          const genericButton = window.paypal!.Buttons({
            ...sharedConfig,
          });
          if (genericButton?.isEligible()) {
            await genericButton.render(`#${cardContainerId}`);
            setWalletFallbackShown(true);
            setMessage(fallbackMessage);
            return true;
          }
        } catch {
          // no-op: caller handles terminal message
        }
        return false;
      };

      try {
        const cardFunding = window.paypal?.FUNDING?.CARD;
        const paypalFunding = window.paypal?.FUNDING?.PAYPAL;
        if (!cardFunding) {
          setCardEligible(false);
          if (
            await renderGenericFallback(
              "Card checkout is unavailable for this buyer profile. You can complete payment securely with PayPal."
            )
          ) {
            return;
          }
          setMessage("Card checkout is unavailable right now. Please try another payment method.");
          return;
        }
        const fundingSources =
          typeof window.paypal?.getFundingSources === "function" ? window.paypal.getFundingSources() : [];
        const supportsCardFunding = Array.isArray(fundingSources) && fundingSources.includes(cardFunding);

        try {
          if (supportsCardFunding) {
            const cardButton = window.paypal!.Buttons({
              ...sharedConfig,
              fundingSource: cardFunding,
            });
            if (cardButton?.isEligible()) {
              await cardButton.render(`#${cardContainerId}`);
              setCardEligible(true);
              setWalletFallbackShown(false);
            } else {
              setCardEligible(false);
              if (
                await renderGenericFallback(
                  "Card checkout is currently unavailable for this buyer profile or region. You can continue with PayPal."
                )
              ) {
                return;
              }
              setMessage("Card checkout is currently unavailable for this buyer profile or region.");
            }
          } else {
            setCardEligible(false);
            if (
              await renderGenericFallback(
                "Card checkout is currently unavailable for this buyer profile or region. You can continue with PayPal."
              )
            ) {
              return;
            }
            setMessage("Card checkout is currently unavailable for this buyer profile or region.");
          }
        } catch {
          setCardEligible(false);
          if (
            await renderGenericFallback(
              "Card checkout could not be rendered. You can continue with PayPal."
            )
          ) {
            return;
          }
          setMessage("Unable to render PayPal checkout. Please refresh and try again.");
        }
      } catch (err: any) {
        const msg = err?.message || "Failed to render PayPal buttons.";
        setMessage(msg);
        onError?.(msg);
      } finally {
        if (mountedRef.current) {
          setRenderingButtons(false);
        }
      }
    };

    renderButtons();
  }, [cardContainerId, currency, onCancel, onError, onSuccess, orderId, sdkReady]);

  return (
    <div className="space-y-4 rounded-xl border border-border p-4">
      <div>
        <p className="text-sm font-semibold text-foreground">Pay with PayPal (Card when eligible)</p>
        <p className="text-xs text-muted-foreground mb-2">
          Use debit or credit card via guest checkout where eligible, or continue with PayPal.
        </p>
        <div id={cardContainerId} className="min-h-10" />
        {!loading && !renderingButtons && !cardEligible && !walletFallbackShown && (
          <p className="text-xs text-muted-foreground mt-2">
            Card checkout may be unavailable in this region or for this buyer profile.
          </p>
        )}
      </div>

      {(loading || renderingButtons) && (
        <p className="text-xs text-muted-foreground">Loading secure PayPal checkout...</p>
      )}
      {!!clientId && !loading && (
        <p className="text-[11px] text-muted-foreground">
          Secure checkout powered by PayPal.
        </p>
      )}
      {!!message && (
        <p className={walletFallbackShown ? "text-sm text-muted-foreground" : "text-sm text-destructive"}>
          {message}
        </p>
      )}
    </div>
  );
}

export default PayPalSmartButtons;
