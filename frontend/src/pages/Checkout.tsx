import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ChevronDown, CreditCard, Truck, Shield } from "lucide-react";
import { Layout } from "@/components/layout/Layout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Checkbox } from "@/components/ui/checkbox";
import { useCart } from "@/context/CartContext";
import { useAuth } from "@/context/AuthContext";
import PayPalSmartButtons from "@/components/payments/PayPalSmartButtons";
import { toast } from "sonner";
import { fetchJSON } from "@/lib/api";

const FALLBACK_IMAGE =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 160 160'%3E%3Crect width='160' height='160' fill='%23f1f1f1'/%3E%3Ctext x='50%25' y='50%25' fill='%23777' font-size='14' text-anchor='middle' dominant-baseline='middle'%3ENo Image%3C/text%3E%3C/svg%3E";

type AddressRecord = {
  id: number;
  full_name: string;
  line1: string;
  line2?: string;
  city: string;
  state?: string;
  postal_code: string;
  country: string;
  phone?: string;
};

const Checkout = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { items, getCartTotal, clearCart } = useCart();
  const { isAuthenticated } = useAuth();
  const [paymentMethod, setPaymentMethod] = useState<"flutterwave" | "paypal" | "stripe">("flutterwave");
  const [isProcessing, setIsProcessing] = useState(false);
  const [checkoutOrderId, setCheckoutOrderId] = useState<number | null>(null);
  const [savedAddresses, setSavedAddresses] = useState<AddressRecord[]>([]);
  const [addressesLoading, setAddressesLoading] = useState(false);
  const [shippingMode, setShippingMode] = useState<"saved" | "new">("new");
  const [billingMode, setBillingMode] = useState<"same_as_shipping" | "saved">("same_as_shipping");
  const [selectedShippingAddressId, setSelectedShippingAddressId] = useState<string>("");
  const [selectedBillingAddressId, setSelectedBillingAddressId] = useState<string>("");

  const subtotal = getCartTotal();
  const shipping = subtotal > 100 ? 0 : 9.99;
  const tax = subtotal * 0.08;
  const total = subtotal + shipping + tax;

  useEffect(() => {
    const paymentState = (searchParams.get("payment") || "").toLowerCase();
    if (paymentState === "cancelled") {
      toast.info("Payment was cancelled. Your cart has been kept.");
    }
  }, [searchParams]);

  useEffect(() => {
    let mounted = true;
    const loadSavedAddresses = async () => {
      if (!isAuthenticated) {
        setSavedAddresses([]);
        setShippingMode("new");
        setBillingMode("same_as_shipping");
        setSelectedShippingAddressId("");
        setSelectedBillingAddressId("");
        return;
      }
      setAddressesLoading(true);
      try {
        const data = await fetchJSON("/api/account/addresses/");
        const rows = Array.isArray(data) ? data : [];
        if (!mounted) return;
        setSavedAddresses(rows);
        if (rows.length > 0) {
          const firstId = String(rows[0].id);
          setShippingMode("saved");
          setSelectedShippingAddressId(firstId);
          setSelectedBillingAddressId(firstId);
        } else {
          setShippingMode("new");
        }
      } catch {
        if (!mounted) return;
        setSavedAddresses([]);
        setShippingMode("new");
      } finally {
        if (mounted) setAddressesLoading(false);
      }
    };

    loadSavedAddresses();
    return () => {
      mounted = false;
    };
  }, [isAuthenticated]);

  useEffect(() => {
    if (paymentMethod !== "paypal") {
      setCheckoutOrderId(null);
    }
  }, [paymentMethod]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsProcessing(true);
    try {
      const form = e.currentTarget as HTMLFormElement;
      const fd = new FormData(form);
      const contactEmail = String(fd.get("email") || "").trim();
      const shipping_address = {
        full_name: `${fd.get("firstName") || ""} ${fd.get("lastName") || ""}`.trim(),
        line1: fd.get("address"),
        city: fd.get("city"),
        state: fd.get("state"),
        postal_code: fd.get("zip"),
        country: fd.get("country"),
        phone: fd.get("phone") || "",
      };

      const checkoutPayload: Record<string, unknown> = {
        shipping_method: null,
        contact_email: contactEmail,
      };

      if (shippingMode === "saved") {
        if (!selectedShippingAddressId) {
          throw new Error("Select a saved shipping address.");
        }
        checkoutPayload.shipping_address_id = Number(selectedShippingAddressId);
      } else {
        checkoutPayload.shipping_address = shipping_address;
      }

      if (billingMode === "same_as_shipping") {
        if (shippingMode === "saved") {
          checkoutPayload.billing_address_id = Number(selectedShippingAddressId);
        } else {
          checkoutPayload.billing_address = { ...shipping_address };
        }
      } else {
        if (!selectedBillingAddressId) {
          throw new Error("Select a saved billing address.");
        }
        checkoutPayload.billing_address_id = Number(selectedBillingAddressId);
      }

      const checkoutRes = await fetchJSON('/api/checkout/', {
        method: 'POST',
        body: JSON.stringify(checkoutPayload),
      });
      const orderId = Number(checkoutRes.id);
      if (!orderId) {
        throw new Error("Unable to create order.");
      }

      if (paymentMethod === "flutterwave" || paymentMethod === "stripe") {
        const redirect = window.location.origin + "/";
        if (paymentMethod === "flutterwave") {
          const redirectWithParams = `${window.location.origin}/?payment=success&provider=flutterwave&order=${orderId}`;
          const resp = await fetchJSON("/api/payments/flutterwave/create/", {
            method: "POST",
            body: JSON.stringify({ order_id: orderId, redirect_url: redirectWithParams }),
          });
          if (resp.link) {
            window.location.href = resp.link;
            return;
          }
        } else {
          const resp = await fetchJSON("/api/payments/stripe/create/", {
            method: "POST",
            body: JSON.stringify({ order_id: orderId, redirect_url: redirect }),
          });
          if (resp.checkout_url) {
            window.location.href = resp.checkout_url;
            return;
          }
        }
      }

      if (paymentMethod === "paypal") {
        setCheckoutOrderId(orderId);
        toast.success("Order created. Complete card payment below.");
        return;
      }

      toast.success("Order created. Complete payment to confirm your order.");
      navigate("/account");
      return;
    } catch (err:any) {
      toast.error(err.message || 'Checkout failed');
    } finally {
      setIsProcessing(false);
    }
  };

  if (items.length === 0) {
    navigate("/cart");
    return null;
  }

  return (
    <Layout>
      {/* Breadcrumb */}
      <div className="bg-secondary/30 py-4">
        <div className="container mx-auto px-4">
          <nav className="breadcrumb">
            <Link to="/">Home</Link>
            <ChevronDown className="h-4 w-4 rotate-[-90deg]" />
            <Link to="/cart">Cart</Link>
            <ChevronDown className="h-4 w-4 rotate-[-90deg]" />
            <span className="text-foreground">Checkout</span>
          </nav>
        </div>
      </div>

      <div className="container mx-auto px-4 py-8 md:py-12">
        <h1 className="font-serif text-3xl font-bold text-foreground mb-8">Checkout</h1>

        <form onSubmit={handleSubmit}>
          <div className="grid lg:grid-cols-3 gap-8">
            {/* Checkout Form */}
            <div className="lg:col-span-2 space-y-8">
              {/* Contact Information */}
              <div className="bg-card border border-border rounded-xl p-6">
                <h2 className="font-serif text-xl font-semibold mb-6">Contact Information</h2>
                <div className="grid md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="email">Email Address</Label>
                      <Input id="email" name="email" type="email" required placeholder="your@email.com" />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="phone">Phone Number</Label>
                      <Input id="phone" name="phone" type="tel" required placeholder="+1 (555) 123-4567" />
                    </div>
                </div>
              </div>

              {/* Shipping Address */}
              <div className="bg-card border border-border rounded-xl p-6">
                <h2 className="font-serif text-xl font-semibold mb-6">Shipping Address</h2>
                {isAuthenticated && (
                  <div className="mb-5 rounded-lg border border-border p-4 space-y-3">
                    <p className="text-sm font-medium">Choose shipping address</p>
                    <RadioGroup
                      value={shippingMode}
                      onValueChange={(value) => setShippingMode(value as "saved" | "new")}
                      className="flex flex-col sm:flex-row gap-3"
                    >
                      <div className="flex items-center gap-2 text-sm">
                        <RadioGroupItem
                          value="saved"
                          id="shipping-mode-saved"
                          disabled={!savedAddresses.length || addressesLoading}
                        />
                        <Label htmlFor="shipping-mode-saved" className="cursor-pointer">
                          Use saved address
                        </Label>
                      </div>
                      <div className="flex items-center gap-2 text-sm">
                        <RadioGroupItem value="new" id="shipping-mode-new" />
                        <Label htmlFor="shipping-mode-new" className="cursor-pointer">
                          Use new address
                        </Label>
                      </div>
                    </RadioGroup>
                    {shippingMode === "saved" && (
                      <select
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                        value={selectedShippingAddressId}
                        onChange={(e) => setSelectedShippingAddressId(e.target.value)}
                      >
                        {savedAddresses.map((address) => (
                          <option key={address.id} value={address.id}>
                            {address.full_name} - {address.line1}, {address.city}, {address.country}
                          </option>
                        ))}
                      </select>
                    )}
                  </div>
                )}

                {shippingMode === "new" && (
                  <div className="grid gap-4">
                    <div className="grid md:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="firstName">First Name</Label>
                        <Input id="firstName" name="firstName" required={shippingMode === "new"} />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="lastName">Last Name</Label>
                        <Input id="lastName" name="lastName" required={shippingMode === "new"} />
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="address">Street Address</Label>
                      <Input id="address" name="address" required={shippingMode === "new"} />
                    </div>
                    <div className="grid md:grid-cols-3 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="city">City</Label>
                        <Input id="city" name="city" required={shippingMode === "new"} />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="state">State/Region</Label>
                        <Input id="state" name="state" required={shippingMode === "new"} />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="zip">ZIP/Postal Code</Label>
                        <Input id="zip" name="zip" required={shippingMode === "new"} />
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="country">Country</Label>
                      <Input id="country" name="country" required={shippingMode === "new"} defaultValue="United States" />
                    </div>
                  </div>
                )}
              </div>

              <div className="bg-card border border-border rounded-xl p-6">
                <h2 className="font-serif text-xl font-semibold mb-6">Billing Address</h2>
                <div className="space-y-3">
                  <RadioGroup
                    value={billingMode}
                    onValueChange={(value) => setBillingMode(value as "same_as_shipping" | "saved")}
                    className="space-y-3"
                  >
                    <div className="flex items-center gap-2 text-sm">
                      <RadioGroupItem value="same_as_shipping" id="billing-mode-same" />
                      <Label htmlFor="billing-mode-same" className="cursor-pointer">
                        Use shipping address
                      </Label>
                    </div>
                    {isAuthenticated && savedAddresses.length > 0 && (
                      <div className="flex items-center gap-2 text-sm">
                        <RadioGroupItem value="saved" id="billing-mode-saved" />
                        <Label htmlFor="billing-mode-saved" className="cursor-pointer">
                          Use another saved address
                        </Label>
                      </div>
                    )}
                  </RadioGroup>
                  {billingMode === "saved" && (
                    <select
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      value={selectedBillingAddressId}
                      onChange={(e) => setSelectedBillingAddressId(e.target.value)}
                    >
                      {savedAddresses.map((address) => (
                        <option key={address.id} value={address.id}>
                          {address.full_name} - {address.line1}, {address.city}, {address.country}
                        </option>
                      ))}
                    </select>
                  )}
                </div>
              </div>

              {/* Payment Method */}
              <div className="bg-card border border-border rounded-xl p-6">
                <h2 className="font-serif text-xl font-semibold mb-6">Payment Method</h2>
                <RadioGroup value={paymentMethod} onValueChange={(value) => setPaymentMethod(value as "flutterwave" | "paypal" | "stripe")} className="space-y-4">
                  <div className="flex items-center space-x-3 p-4 border border-border rounded-lg hover:border-primary transition-colors">
                    <RadioGroupItem value="flutterwave" id="flutterwave" />
                    <Label htmlFor="flutterwave" className="flex items-center gap-3 cursor-pointer flex-1">
                      <CreditCard className="h-5 w-5 text-primary" />
                      <div>
                        <p className="font-medium">Pay with Flutterwave</p>
                        <p className="text-sm text-muted-foreground">
                          Credit/Debit Cards, Bank Transfer, Mobile Money (International)
                        </p>
                      </div>
                    </Label>
                  </div>

                  <div className="flex items-center space-x-3 p-4 border border-border rounded-lg hover:border-primary transition-colors">
                    <RadioGroupItem value="paypal" id="paypal" />
                    <Label htmlFor="paypal" className="flex items-center gap-3 cursor-pointer flex-1">
                      <CreditCard className="h-5 w-5 text-primary" />
                      <div>
                        <p className="font-medium">Pay with PayPal Card Checkout</p>
                        <p className="text-sm text-muted-foreground">
                          Card-only checkout via PayPal. No PayPal account needed where eligible.
                        </p>
                      </div>
                    </Label>
                  </div>

                  <div className="flex items-center space-x-3 p-4 border border-border rounded-lg hover:border-primary transition-colors">
                    <RadioGroupItem value="stripe" id="stripe" />
                    <Label htmlFor="stripe" className="flex items-center gap-3 cursor-pointer flex-1">
                      <CreditCard className="h-5 w-5 text-primary" />
                      <div>
                        <p className="font-medium">Pay with Stripe</p>
                        <p className="text-sm text-muted-foreground">Cards (via Stripe)</p>
                      </div>
                    </Label>
                  </div>
                </RadioGroup>

                {/* Card Details Preview */}
                <div className="mt-6 p-4 bg-secondary/50 rounded-lg">
                  <p className="text-sm text-muted-foreground text-center">
                    {paymentMethod === "paypal"
                      ? "After creating your order, complete PayPal card checkout below."
                      : `You will be redirected to ${paymentMethod === "flutterwave" ? "Flutterwave" : "Stripe"} to complete payment securely.`}
                  </p>
                </div>
              </div>

              {paymentMethod === "paypal" && checkoutOrderId && (
                <PayPalSmartButtons
                  orderId={checkoutOrderId}
                  currency="USD"
                  onSuccess={async () => {
                    await clearCart();
                    toast.success("Payment successful. Your order is confirmed.");
                    navigate("/order/success/");
                  }}
                  onError={(msg) => {
                    toast.error(msg || "PayPal payment failed.");
                  }}
                  onCancel={() => {
                    toast.info("Payment cancelled. You can retry.");
                  }}
                />
              )}

              {/* Terms */}
              <div className="flex items-start gap-3">
                <Checkbox id="terms" required />
                <Label htmlFor="terms" className="text-sm text-muted-foreground leading-relaxed">
                  I agree to the{" "}
                  <Link to="/terms" className="text-primary hover:underline">
                    Terms of Service
                  </Link>{" "}
                  and{" "}
                  <Link to="/privacy" className="text-primary hover:underline">
                    Privacy Policy
                  </Link>
                </Label>
              </div>
            </div>

            {/* Order Summary */}
            <div className="lg:col-span-1">
              <div className="bg-secondary/30 rounded-xl p-6 sticky top-24">
                <h2 className="font-serif text-xl font-semibold mb-6">Order Summary</h2>

                {/* Items */}
                <div className="space-y-4 max-h-60 overflow-y-auto mb-6">
                  {items.map((item) => (
                    <div key={item.product.id} className="flex gap-3">
                      <img
                        src={item.product.images?.[0] || FALLBACK_IMAGE}
                        alt={item.product.name}
                        className="w-16 h-16 object-cover rounded-lg"
                        onError={(e) => {
                          e.currentTarget.src = FALLBACK_IMAGE;
                        }}
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium line-clamp-2">{item.product.name}</p>
                        <p className="text-xs text-muted-foreground">Qty: {item.quantity}</p>
                        <p className="text-sm font-medium mt-1">
                          ${(item.product.price * item.quantity).toFixed(2)}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Summary */}
                <div className="space-y-3 pb-4 border-b border-border">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Subtotal</span>
                    <span>${subtotal.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Shipping</span>
                    <span>{shipping === 0 ? "FREE" : `$${shipping.toFixed(2)}`}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Tax</span>
                    <span>${tax.toFixed(2)}</span>
                  </div>
                </div>

                {/* Total */}
                <div className="flex justify-between py-4">
                  <span className="font-semibold">Total</span>
                  <span className="text-xl font-bold">${total.toFixed(2)}</span>
                </div>

                {/* Place Order Button */}
                <Button
                  variant="hero"
                  className="w-full"
                  type="submit"
                  disabled={isProcessing || (paymentMethod === "paypal" && checkoutOrderId !== null)}
                >
                  {isProcessing
                    ? "Processing..."
                    : paymentMethod === "paypal" && checkoutOrderId !== null
                      ? "Order Created - Complete Card Payment"
                      : paymentMethod === "paypal"
                        ? `Create Order - $${total.toFixed(2)}`
                        : `Pay $${total.toFixed(2)}`}
                </Button>

                {/* Trust Badges */}
                <div className="flex flex-col gap-2 mt-6 text-sm text-muted-foreground">
                  <span className="flex items-center gap-2">
                    <Shield className="h-4 w-4 text-primary" />
                    Secure SSL Encrypted Payment
                  </span>
                  <span className="flex items-center gap-2">
                    <Truck className="h-4 w-4 text-primary" />
                    Free shipping on orders over $100
                  </span>
                </div>
              </div>
            </div>
          </div>
        </form>
      </div>
    </Layout>
  );
};

export default Checkout;
