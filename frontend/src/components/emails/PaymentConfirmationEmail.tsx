import EmailHeader from "./EmailHeader";
import EmailFooter from "./EmailFooter";
import EmailButton from "./EmailButton";
import { CreditCard } from "lucide-react";

const PaymentConfirmationEmail = () => (
  <div className="max-w-[600px] mx-auto bg-card shadow-xl overflow-hidden">
    <EmailHeader />

    <div className="px-8 py-10 text-center">
      <div className="w-14 h-14 rounded-full bg-brand-gold/20 flex items-center justify-center mx-auto mb-4">
        <CreditCard className="h-7 w-7 text-brand-gold" />
      </div>
      <h3 className="font-display text-2xl text-foreground mb-2">Payment Received</h3>
      <p className="text-muted-foreground font-body text-sm">Transaction ID: TXN-2026-DR-90412</p>
      <div className="w-12 h-0.5 bg-brand-gold mx-auto mt-4" />
    </div>

    <div className="px-8 pb-8">
      <p className="text-muted-foreground font-body text-sm leading-relaxed mb-6">
        We've successfully processed your payment. Here are your transaction details:
      </p>

      <div className="bg-secondary rounded p-5 mb-6 space-y-3">
        {[
          ["Amount Paid", "₦220,375"],
          ["Payment Method", "Visa •••• 4829"],
          ["Date", "February 25, 2026 • 2:34 PM"],
          ["Order Reference", "#DRC-2026-00847"],
          ["Status", "✅ Successful"],
        ].map(([label, value]) => (
          <div key={label} className="flex justify-between items-center">
            <span className="font-body text-xs text-muted-foreground">{label}</span>
            <span className="font-body text-sm font-semibold text-secondary-foreground">{value}</span>
          </div>
        ))}
      </div>

      <div className="border border-brand-gold/30 rounded p-4 mb-8 bg-brand-gold/5">
        <p className="font-body text-xs text-muted-foreground leading-relaxed">
          💡 A receipt has been sent to your email. If you did not authorize this transaction, please 
          <a href="#" className="text-brand-gold font-semibold"> contact our support team</a> immediately.
        </p>
      </div>

      <div className="text-center">
        <EmailButton>View Order Details</EmailButton>
      </div>
    </div>

    <EmailFooter />
  </div>
);

export default PaymentConfirmationEmail;
