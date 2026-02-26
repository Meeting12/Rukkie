import EmailHeader from "./EmailHeader";
import EmailFooter from "./EmailFooter";
import EmailButton from "./EmailButton";
import { PartyPopper } from "lucide-react";

const SubscriptionEmail = () => (
  <div className="max-w-[600px] mx-auto bg-card shadow-xl overflow-hidden">
    <EmailHeader />

    <div className="px-8 py-10 text-center">
      <div className="w-14 h-14 rounded-full bg-brand-gold/20 flex items-center justify-center mx-auto mb-4">
        <PartyPopper className="h-7 w-7 text-brand-gold" />
      </div>
      <h3 className="font-display text-2xl text-foreground mb-2">You're Subscribed!</h3>
      <p className="text-muted-foreground font-body text-sm">Welcome to the inner circle</p>
      <div className="w-12 h-0.5 bg-brand-gold mx-auto mt-4" />
    </div>

    <div className="px-8 pb-8">
      <p className="text-muted-foreground font-body text-sm leading-relaxed mb-6">
        You've successfully subscribed to the <strong className="text-foreground">De-Rukkies Collection</strong> newsletter. 
        Get ready for exclusive drops, style tips, and members-only deals straight to your inbox.
      </p>

      <div className="bg-secondary rounded p-6 mb-6">
        <h4 className="font-display text-lg text-secondary-foreground mb-4 text-center">What You'll Get</h4>
        <div className="space-y-3">
          {[
            { emoji: "🛍️", title: "Early Access", desc: "Be first to shop new collections before anyone else" },
            { emoji: "💰", title: "Exclusive Discounts", desc: "Subscriber-only offers and flash sale alerts" },
            { emoji: "✨", title: "Style Guides", desc: "Curated looks and seasonal styling tips" },
            { emoji: "🎁", title: "Birthday Surprise", desc: "A special gift waiting for you on your birthday" },
          ].map((perk) => (
            <div key={perk.title} className="flex items-start gap-3">
              <span className="text-lg">{perk.emoji}</span>
              <div>
                <p className="font-body text-sm font-semibold text-secondary-foreground">{perk.title}</p>
                <p className="font-body text-xs text-muted-foreground">{perk.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="border border-brand-gold/30 rounded p-4 mb-8 bg-brand-gold/5 text-center">
        <p className="font-body text-sm text-foreground font-semibold mb-1">🎉 Subscriber Welcome Gift</p>
        <p className="font-body text-xs text-muted-foreground">
          Use code <span className="font-bold text-brand-gold">SUBSCRIBED10</span> for 10% off your next order!
        </p>
      </div>

      <div className="text-center">
        <EmailButton>Start Shopping</EmailButton>
      </div>
    </div>

    <EmailFooter />
  </div>
);

export default SubscriptionEmail;
