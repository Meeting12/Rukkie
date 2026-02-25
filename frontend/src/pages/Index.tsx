import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Layout } from "@/components/layout/Layout";
import { HeroSection } from "@/components/home/HeroSection";
import { CategoriesSection } from "@/components/home/CategoriesSection";
import { FeaturedProducts } from "@/components/home/FeaturedProducts";
import { FlashSaleSection } from "@/components/home/FlashSaleSection";
import { NewsletterSection } from "@/components/home/NewsletterSection";
import { useCart } from "@/context/CartContext";
import { fetchJSON } from "@/lib/api";
import { toast } from "sonner";

const PAID_STATUSES = ["paid", "processing", "shipped", "delivered"];

const Index = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { refreshCart } = useCart();

  useEffect(() => {
    const payment = (searchParams.get("payment") || "").toLowerCase();
    const provider = (searchParams.get("provider") || "").toLowerCase();
    const orderId = searchParams.get("order");
    const stripeSessionId = searchParams.get("session_id");
    const flutterwaveStatus = (searchParams.get("status") || "").toLowerCase();
    const flutterwaveTransactionId = searchParams.get("transaction_id") || searchParams.get("transactionId");
    const flutterwaveTxRef = searchParams.get("tx_ref");
    const paypalPaymentId = searchParams.get("payment_id") || searchParams.get("paymentId");
    const paypalPayerId = searchParams.get("payer_id") || searchParams.get("PayerID");

    if (!payment) return;

    const done = () => navigate("/", { replace: true });

    if (payment === "cancelled") {
      toast.info("Payment was cancelled. Your cart has been kept.");
      done();
      return;
    }

    if (provider === "flutterwave" && flutterwaveStatus && !["successful", "completed"].includes(flutterwaveStatus)) {
      toast.info("Flutterwave payment was not successful. Your cart has been kept.");
      done();
      return;
    }

    if (payment !== "success" || !orderId) {
      done();
      return;
    }

    const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

    const readOrderStatus = async () => {
      const order = await fetchJSON(`/api/orders/track/?order_id=${encodeURIComponent(orderId)}`);
      return String(order?.status || "").toLowerCase();
    };

    const waitUntilPaid = async () => {
      for (let i = 0; i < 6; i += 1) {
        const status = await readOrderStatus();
        if (PAID_STATUSES.includes(status)) return true;
        await sleep(1500);
      }
      return false;
    };

    const checkAndClear = async () => {
      let confirmAttemptError = false;
      try {
        if (provider === "stripe" && stripeSessionId) {
          await fetchJSON("/api/payments/stripe/confirm/", {
            method: "POST",
            body: JSON.stringify({ order_id: orderId, session_id: stripeSessionId }),
          });
        } else if (provider === "flutterwave") {
          await fetchJSON("/api/payments/flutterwave/confirm/", {
            method: "POST",
            body: JSON.stringify({
              order_id: orderId,
              transaction_id: flutterwaveTransactionId,
              tx_ref: flutterwaveTxRef,
              status: flutterwaveStatus,
            }),
          });
        } else if (provider === "paypal") {
          await fetchJSON("/api/payments/paypal/confirm/", {
            method: "POST",
            body: JSON.stringify({
              order_id: orderId,
              payment_id: paypalPaymentId,
              payer_id: paypalPayerId,
            }),
          });
        }
      } catch {
        // Provider confirm can fail when webhook already marked payment paid.
        confirmAttemptError = true;
      }

      try {
        const isPaid = await waitUntilPaid();

        if (isPaid) {
          await refreshCart();
          toast.success("Payment confirmed and cart updated.");
        } else if (confirmAttemptError) {
          toast.info("Payment is being confirmed. Cart will be kept until payment is successful.");
        } else {
          toast.info("Payment is being processed. Cart is kept until confirmation is complete.");
        }
      } catch {
        toast.info("Payment return received. Check your order status in your account.");
      } finally {
        done();
      }
    };

    checkAndClear();
  }, [
    searchParams,
    navigate,
    refreshCart,
  ]);

  return (
    <Layout>
      <HeroSection />
      <CategoriesSection />
      <FeaturedProducts />
      <FlashSaleSection />
      <NewsletterSection />
    </Layout>
  );
};

export default Index;
