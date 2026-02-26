import EmailHeader from "./EmailHeader";
import EmailFooter from "./EmailFooter";
import EmailButton from "./EmailButton";
import { Truck, MapPin, CalendarDays } from "lucide-react";

const steps = [
  { label: "Ordered", date: "Feb 20", done: true },
  { label: "Shipped", date: "Feb 22", done: true },
  { label: "In Transit", date: "Feb 24", done: true },
  { label: "Delivered", date: "Feb 26", done: false },
];

const ShippingEmail = () => (
  <div className="max-w-[600px] mx-auto bg-card shadow-xl overflow-hidden">
    <EmailHeader />

    <div className="px-8 py-10 text-center">
      <div className="w-14 h-14 rounded-full bg-brand-gold/20 flex items-center justify-center mx-auto mb-4">
        <Truck className="h-7 w-7 text-brand-gold" />
      </div>
      <h3 className="font-display text-2xl text-foreground mb-2">Your Order is On Its Way!</h3>
      <p className="text-muted-foreground font-body text-sm">Order #DRC-2026-00847</p>
      <div className="w-12 h-0.5 bg-brand-gold mx-auto mt-4" />
    </div>

    <div className="px-8 pb-8">
      {/* Progress tracker */}
      <div className="flex items-center justify-between mb-8 px-2">
        {steps.map((step, i) => (
          <div key={step.label} className="flex flex-col items-center flex-1 relative">
            {i > 0 && (
              <div className={`absolute top-3 -left-1/2 w-full h-0.5 ${step.done ? "bg-brand-gold" : "bg-border"}`} />
            )}
            <div className={`relative z-10 w-6 h-6 rounded-full flex items-center justify-center text-xs font-body font-semibold ${
              step.done ? "bg-brand-gold text-accent-foreground" : "bg-border text-muted-foreground"
            }`}>
              {step.done ? "✓" : i + 1}
            </div>
            <p className="font-body text-xs font-semibold text-foreground mt-2">{step.label}</p>
            <p className="font-body text-xs text-muted-foreground">{step.date}</p>
          </div>
        ))}
      </div>

      <div className="bg-secondary rounded p-5 space-y-4 mb-6">
        <div className="flex items-start gap-3">
          <Truck className="h-4 w-4 text-brand-gold mt-0.5 shrink-0" />
          <div>
            <p className="font-body text-xs font-semibold text-secondary-foreground">Carrier</p>
            <p className="font-body text-sm text-muted-foreground">DHL Express — Tracking: 7849302856</p>
          </div>
        </div>
        <div className="flex items-start gap-3">
          <CalendarDays className="h-4 w-4 text-brand-gold mt-0.5 shrink-0" />
          <div>
            <p className="font-body text-xs font-semibold text-secondary-foreground">Estimated Delivery</p>
            <p className="font-body text-sm text-muted-foreground">February 26, 2026</p>
          </div>
        </div>
        <div className="flex items-start gap-3">
          <MapPin className="h-4 w-4 text-brand-gold mt-0.5 shrink-0" />
          <div>
            <p className="font-body text-xs font-semibold text-secondary-foreground">Delivering To</p>
            <p className="font-body text-sm text-muted-foreground">14 Victoria Island Crescent, Lagos</p>
          </div>
        </div>
      </div>

      <div className="text-center">
        <EmailButton>Track Package</EmailButton>
      </div>
    </div>

    <EmailFooter />
  </div>
);

export default ShippingEmail;
