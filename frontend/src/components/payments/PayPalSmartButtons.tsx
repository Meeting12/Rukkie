import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { fetchJSON } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

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

type PayPalHostedFieldsInstance = {
  submit: (options?: Record<string, any>) => Promise<void>;
  teardown?: () => Promise<void>;
};

type PayPalHostedFieldsNamespace = {
  isEligible: () => boolean;
  render: (config: Record<string, any>) => Promise<PayPalHostedFieldsInstance>;
};

type PayPalNamespace = {
  FUNDING?: {
    PAYPAL?: string;
    CARD?: string;
  };
  Buttons: (config: Record<string, any>) => PayPalButtonInstance;
  HostedFields?: PayPalHostedFieldsNamespace;
};

declare global {
  interface Window {
    paypal?: PayPalNamespace;
  }
}

const PAYPAL_SDK_SCRIPT_ID = "paypal-js-sdk";

type PayPalSdkLoadResult = {
  hostedFieldsAvailable: boolean;
};

async function injectPayPalScript(clientId: string, currency: string, components: string) {
  const sdkUrl =
    `https://www.paypal.com/sdk/js?client-id=${encodeURIComponent(clientId)}` +
    `&currency=${encodeURIComponent(currency)}` +
    `&intent=capture&components=${encodeURIComponent(components)}`;

  const existing = document.getElementById(PAYPAL_SDK_SCRIPT_ID);
  if (existing && window.paypal && (existing as HTMLScriptElement).src === sdkUrl) {
    return sdkUrl;
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

  return sdkUrl;
}

async function loadPayPalScript(clientId: string, currency: string): Promise<PayPalSdkLoadResult> {
  try {
    await injectPayPalScript(clientId, currency, "buttons,hosted-fields");
    if (!window.paypal?.Buttons) {
      throw new Error("PayPal SDK loaded without Buttons.");
    }
    return { hostedFieldsAvailable: Boolean(window.paypal?.HostedFields) };
  } catch {
    // Fallback to wallet-only SDK if hosted fields path crashes in this buyer/browser profile.
    await injectPayPalScript(clientId, currency, "buttons");
    if (!window.paypal?.Buttons) {
      throw new Error("Unable to initialize PayPal.");
    }
    return { hostedFieldsAvailable: false };
  }
}

export function PayPalSmartButtons({
  orderId,
  currency = "USD",
  onSuccess,
  onError,
  onCancel,
}: PayPalSmartButtonsProps) {
  const [checkoutMode, setCheckoutMode] = useState<"card" | "paypal">("card");
  const [clientId, setClientId] = useState("");
  const [sdkReady, setSdkReady] = useState(false);
  const [loading, setLoading] = useState(true);
  const [renderingWallet, setRenderingWallet] = useState(false);
  const [renderingCardFields, setRenderingCardFields] = useState(false);
  const [cardSubmitting, setCardSubmitting] = useState(false);
  const [redirectingWallet, setRedirectingWallet] = useState(false);
  const [redirectingCard, setRedirectingCard] = useState(false);
  const [cardEligible, setCardEligible] = useState(false);
  const [walletEligible, setWalletEligible] = useState(false);
  const [hostedFieldsAvailable, setHostedFieldsAvailable] = useState(false);
  const [cardholderName, setCardholderName] = useState("");
  const [message, setMessage] = useState("");
  const mountedRef = useRef(true);
  const hostedFieldsRef = useRef<PayPalHostedFieldsInstance | null>(null);

  const walletContainerId = useMemo(() => `pp-wallet-${orderId}`, [orderId]);
  const cardNumberId = useMemo(() => `pp-card-number-${orderId}`, [orderId]);
  const cardExpiryId = useMemo(() => `pp-card-expiry-${orderId}`, [orderId]);
  const cardCvvId = useMemo(() => `pp-card-cvv-${orderId}`, [orderId]);

  const recordClientState = useCallback(async (state: "failed" | "cancelled", paypalOrderId = "") => {
    try {
      await fetchJSON("/api/paypal/state/", {
        method: "POST",
        body: JSON.stringify({
          order_id: orderId,
          paypal_order_id: paypalOrderId,
          state,
        }),
      });
    } catch {
      // Keep checkout stable even if state logging fails.
    }
  }, [orderId]);

  const createOrder = useCallback(async () => {
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
  }, [currency, orderId]);

  const handleApprove = useCallback(async (data: any) => {
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
  }, [onSuccess, orderId]);

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
    setCardEligible(false);
    setWalletEligible(false);
    setHostedFieldsAvailable(false);
    setCheckoutMode("card");

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
        const sdkResult = await loadPayPalScript(backendClientId, backendCurrency);
        if (!active || !mountedRef.current) return;
        setHostedFieldsAvailable(sdkResult.hostedFieldsAvailable);
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
    setRenderingWallet(true);
    const walletRoot = document.getElementById(walletContainerId);
    if (walletRoot) walletRoot.innerHTML = "";

    const renderWallet = async () => {
      try {
        const walletConfig: Record<string, any> = {
          style: { shape: "rect", layout: "vertical", label: "paypal" },
          createOrder,
          onApprove: handleApprove,
          onCancel: async () => {
            setMessage("Payment was cancelled. You can try again.");
            await recordClientState("cancelled");
            onCancel?.();
          },
          onError: async (err: any) => {
            const msg = err?.message || "PayPal payment failed.";
            setMessage(msg);
            await recordClientState("failed");
            onError?.(msg);
          },
        };

        const walletFunding = window.paypal?.FUNDING?.PAYPAL;
        if (walletFunding) {
          walletConfig.fundingSource = walletFunding;
        }

        const walletButton = window.paypal!.Buttons(walletConfig);

        if (walletButton?.isEligible()) {
          await walletButton.render(`#${walletContainerId}`);
          setWalletEligible(true);
          return;
        }
        setWalletEligible(false);
      } catch (err: any) {
        const msg = err?.message || "Unable to render PayPal wallet.";
        setMessage(msg);
        onError?.(msg);
        setWalletEligible(false);
      } finally {
        if (mountedRef.current) setRenderingWallet(false);
      }
    };

    renderWallet();
  }, [createOrder, handleApprove, onCancel, onError, recordClientState, sdkReady, walletContainerId]);

  useEffect(() => {
    let active = true;

    const renderHostedFields = async () => {
      if (!sdkReady || !hostedFieldsAvailable || !window.paypal?.HostedFields) {
        setCardEligible(false);
        return;
      }
      if (!window.paypal.HostedFields.isEligible()) {
        setCardEligible(false);
        return;
      }

      if (hostedFieldsRef.current?.teardown) {
        try {
          await hostedFieldsRef.current.teardown();
        } catch {
          // Ignore teardown errors.
        }
      }
      hostedFieldsRef.current = null;

      const numberRoot = document.getElementById(cardNumberId);
      const expiryRoot = document.getElementById(cardExpiryId);
      const cvvRoot = document.getElementById(cardCvvId);
      if (numberRoot) numberRoot.innerHTML = "";
      if (expiryRoot) expiryRoot.innerHTML = "";
      if (cvvRoot) cvvRoot.innerHTML = "";

      setRenderingCardFields(true);
      try {
        const hostedFields = await window.paypal.HostedFields.render({
          createOrder,
          onApprove: handleApprove,
          onError: async (err: any) => {
            const msg = err?.message || "Card payment failed.";
            setMessage(msg);
            await recordClientState("failed");
            onError?.(msg);
          },
          styles: {
            input: {
              "font-size": "16px",
              "font-family": "inherit",
              color: "#0f172a",
            },
            ".invalid": {
              color: "#dc2626",
            },
          },
          fields: {
            number: { selector: `#${cardNumberId}`, placeholder: "4111 1111 1111 1111" },
            cvv: { selector: `#${cardCvvId}`, placeholder: "123" },
            expirationDate: { selector: `#${cardExpiryId}`, placeholder: "MM/YY" },
          },
        });

        if (!active || !mountedRef.current) return;
        hostedFieldsRef.current = hostedFields;
        setCardEligible(true);
      } catch (err: any) {
        if (!active || !mountedRef.current) return;
        setCardEligible(false);
        const msg = err?.message || "Card fields are unavailable for this buyer profile or region.";
        setMessage(msg);
      } finally {
        if (active && mountedRef.current) setRenderingCardFields(false);
      }
    };

    renderHostedFields();

    return () => {
      active = false;
    };
  }, [cardCvvId, cardExpiryId, cardNumberId, createOrder, handleApprove, hostedFieldsAvailable, onError, recordClientState, sdkReady]);

  useEffect(() => {
    return () => {
      if (hostedFieldsRef.current?.teardown) {
        hostedFieldsRef.current.teardown().catch(() => {});
      }
    };
  }, []);

  const handleSubmitCard = async () => {
    if (!hostedFieldsRef.current) {
      setMessage("Card fields are not ready. Try PayPal wallet.");
      return;
    }
    if (!cardholderName.trim()) {
      setMessage("Cardholder name is required.");
      return;
    }

    setCardSubmitting(true);
    setMessage("");
    try {
      await hostedFieldsRef.current.submit({
        cardholderName: cardholderName.trim(),
      });
    } catch (err: any) {
      const msg = err?.message || "Card payment failed.";
      setMessage(msg);
      await recordClientState("failed");
      onError?.(msg);
    } finally {
      setCardSubmitting(false);
    }
  };

  const openPayPalRedirect = useCallback(async (checkoutOption: "paypal" | "card") => {
    if (checkoutOption === "card") {
      setRedirectingCard(true);
    } else {
      setRedirectingWallet(true);
    }
    try {
      const origin = window.location.origin;
      const response = await fetchJSON("/api/payments/paypal/create/", {
        method: "POST",
        body: JSON.stringify({
          order_id: orderId,
          return_url: `${origin}/order/success/`,
          cancel_url: `${origin}/checkout?payment=cancelled&provider=paypal`,
          checkout_option: checkoutOption,
        }),
      });
      const approvalUrl = String(response?.approval_url || "").trim();
      if (!approvalUrl) {
        throw new Error("Unable to open PayPal checkout right now.");
      }
      window.location.href = approvalUrl;
    } catch (err: any) {
      const msg = err?.message || "Unable to open PayPal checkout right now.";
      setMessage(msg);
      onError?.(msg);
    } finally {
      setRedirectingWallet(false);
      setRedirectingCard(false);
    }
  }, [onError, orderId]);

  const handleWalletRedirectFallback = useCallback(async () => {
    await openPayPalRedirect("paypal");
  }, [openPayPalRedirect]);

  const handleCardRedirectFallback = useCallback(async () => {
    await openPayPalRedirect("card");
  }, [openPayPalRedirect]);

  return (
    <div className="space-y-4 rounded-xl border border-border p-4">
      <div>
        <p className="text-sm font-semibold text-foreground">Pay with Card or PayPal</p>
        <p className="text-xs text-muted-foreground">
          Card fields require PayPal guest card eligibility for the current region/profile.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <Button
          type="button"
          variant={checkoutMode === "card" ? "default" : "outline"}
          onClick={() => setCheckoutMode("card")}
        >
          Pay with Card
        </Button>
        <Button
          type="button"
          variant={checkoutMode === "paypal" ? "default" : "outline"}
          onClick={() => setCheckoutMode("paypal")}
        >
          Pay with PayPal
        </Button>
      </div>

      {(loading || renderingWallet || renderingCardFields) && (
        <p className="text-xs text-muted-foreground">Loading secure PayPal checkout...</p>
      )}

      {checkoutMode === "card" && (
        <div className="space-y-3">
          {cardEligible ? (
            <>
              <div className="space-y-2">
                <Label htmlFor={`paypal-cardholder-${orderId}`}>Cardholder Name</Label>
                <Input
                  id={`paypal-cardholder-${orderId}`}
                  value={cardholderName}
                  onChange={(event) => setCardholderName(event.target.value)}
                  placeholder="Name on card"
                />
              </div>

              <div className="space-y-2">
                <Label>Card Number</Label>
                <div id={cardNumberId} className="h-10 rounded-md border border-input bg-background px-3 py-2" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label>Expiry</Label>
                  <div id={cardExpiryId} className="h-10 rounded-md border border-input bg-background px-3 py-2" />
                </div>
                <div className="space-y-2">
                  <Label>CVV</Label>
                  <div id={cardCvvId} className="h-10 rounded-md border border-input bg-background px-3 py-2" />
                </div>
              </div>

              <Button
                type="button"
                className="w-full"
                onClick={handleSubmitCard}
                loading={cardSubmitting}
                loadingText="Processing card payment..."
              >
                Pay with Card
              </Button>
            </>
          ) : (
            <div className="space-y-2 rounded-md border border-border p-3">
              <p className="text-sm text-muted-foreground">
                Card checkout is unavailable for this buyer profile or region.
              </p>
              <Button
                type="button"
                variant="outline"
                className="w-full"
                loading={redirectingCard}
                loadingText="Redirecting to PayPal..."
                onClick={handleCardRedirectFallback}
              >
                Continue with Card on PayPal
              </Button>
              <Button type="button" variant="ghost" className="w-full" onClick={() => setCheckoutMode("paypal")}>
                Use PayPal Wallet Instead
              </Button>
            </div>
          )}
        </div>
      )}

      {checkoutMode === "paypal" && (
        <div className="space-y-2">
          <div id={walletContainerId} className="min-h-10" />
          {!loading && !renderingWallet && !walletEligible && (
            <Button
              type="button"
              variant="outline"
              className="w-full"
              loading={redirectingWallet}
              loadingText="Redirecting to PayPal..."
              onClick={handleWalletRedirectFallback}
            >
              Continue with PayPal Wallet
            </Button>
          )}
        </div>
      )}

      {!!clientId && !loading && (
        <p className="text-[11px] text-muted-foreground">Secure checkout powered by PayPal.</p>
      )}

      {!!message && (
        <p className="text-sm text-muted-foreground">{message}</p>
      )}
    </div>
  );
}

export default PayPalSmartButtons;
