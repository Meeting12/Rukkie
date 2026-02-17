import { Link } from "react-router-dom";
import { CheckCircle2 } from "lucide-react";
import { Layout } from "@/components/layout/Layout";
import { Button } from "@/components/ui/button";

const OrderSuccess = () => {
  return (
    <Layout>
      <div className="container mx-auto px-4 py-16">
        <div className="max-w-2xl mx-auto rounded-2xl border border-border bg-card p-8 text-center">
          <CheckCircle2 className="h-14 w-14 text-primary mx-auto mb-4" />
          <h1 className="font-serif text-3xl font-bold text-foreground">Payment Successful</h1>
          <p className="mt-3 text-muted-foreground">
            Your payment has been captured successfully and your order is now confirmed.
          </p>
          <div className="mt-8 flex flex-col sm:flex-row gap-3 justify-center">
            <Button asChild>
              <Link to="/account">View My Orders</Link>
            </Button>
            <Button asChild variant="outline">
              <Link to="/products">Continue Shopping</Link>
            </Button>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default OrderSuccess;
