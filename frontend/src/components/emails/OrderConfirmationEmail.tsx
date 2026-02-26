import EmailHeader from "./EmailHeader";
import EmailFooter from "./EmailFooter";
import EmailButton from "./EmailButton";
import product1 from "@/assets/product-1.jpg";
import product3 from "@/assets/product-3.jpg";
import { Check } from "lucide-react";

const orderItems = [
  { name: "Classic Leather Handbag", variant: "Cognac / One Size", qty: 1, price: "₦85,000", image: product1 },
  { name: "Executive Watch & Wallet Set", variant: "Dark Brown / Standard", qty: 1, price: "₦120,000", image: product3 },
];

const OrderConfirmationEmail = () => (
  <div className="max-w-[600px] mx-auto bg-card shadow-xl overflow-hidden">
    <EmailHeader />

    <div className="px-8 py-10 text-center">
      <div className="w-14 h-14 rounded-full bg-brand-gold/20 flex items-center justify-center mx-auto mb-4">
        <Check className="h-7 w-7 text-brand-gold" />
      </div>
      <h3 className="font-display text-2xl text-foreground mb-2">Order Confirmed!</h3>
      <p className="text-muted-foreground font-body text-sm">Order #DRC-2026-00847</p>
      <div className="w-12 h-0.5 bg-brand-gold mx-auto mt-4" />
    </div>

    <div className="px-8 pb-6">
      <p className="text-muted-foreground font-body text-sm leading-relaxed mb-6">
        Thank you for your purchase! We're preparing your items with care. Here's a summary of your order:
      </p>

      <div className="space-y-4 mb-6">
        {orderItems.map((item) => (
          <div key={item.name} className="flex gap-4 p-3 bg-secondary rounded">
            <img src={item.image} alt={item.name} className="w-20 h-20 object-cover rounded" />
            <div className="flex-1">
              <p className="font-body text-sm font-semibold text-foreground">{item.name}</p>
              <p className="font-body text-xs text-muted-foreground mt-1">{item.variant}</p>
              <p className="font-body text-xs text-muted-foreground">Qty: {item.qty}</p>
            </div>
            <p className="font-body text-sm font-semibold text-foreground self-center">{item.price}</p>
          </div>
        ))}
      </div>

      <div className="border-t border-border pt-4 space-y-2">
        {[
          ["Subtotal", "₦205,000"],
          ["Shipping", "Free"],
          ["Tax", "₦15,375"],
        ].map(([label, value]) => (
          <div key={label} className="flex justify-between font-body text-sm text-muted-foreground">
            <span>{label}</span>
            <span>{value}</span>
          </div>
        ))}
        <div className="flex justify-between font-body text-base font-semibold text-foreground pt-2 border-t border-border">
          <span>Total</span>
          <span>₦220,375</span>
        </div>
      </div>
    </div>

    <div className="px-8 pb-8">
      <div className="bg-secondary rounded p-5">
        <h4 className="font-body text-sm font-semibold text-secondary-foreground mb-3">Shipping Address</h4>
        <p className="font-body text-sm text-muted-foreground leading-relaxed">
          Adewale Johnson<br />
          14 Victoria Island Crescent<br />
          Lagos, Nigeria 101241
        </p>
      </div>
    </div>

    <div className="px-8 pb-10 text-center">
      <EmailButton>Track Your Order</EmailButton>
    </div>

    <EmailFooter />
  </div>
);

export default OrderConfirmationEmail;
