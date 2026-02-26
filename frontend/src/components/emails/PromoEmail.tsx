import EmailHeader from "./EmailHeader";
import EmailFooter from "./EmailFooter";
import EmailButton from "./EmailButton";
import heroBanner from "@/assets/hero-banner.jpg";
import product1 from "@/assets/product-1.jpg";
import product3 from "@/assets/product-3.jpg";

const products = [
  { name: "Classic Leather Handbag", old: "₦85,000", price: "₦59,500", image: product1 },
  { name: "Executive Watch Set", old: "₦120,000", price: "₦84,000", image: product3 },
];

const PromoEmail = () => (
  <div className="max-w-[600px] mx-auto bg-card shadow-xl overflow-hidden">
    <EmailHeader />

    <div className="relative">
      <img src={heroBanner} alt="Sale Banner" className="w-full h-64 object-cover" />
      <div className="absolute inset-0 bg-primary/60 flex flex-col items-center justify-center text-center px-8">
        <p className="font-body text-xs uppercase tracking-[0.3em] text-brand-gold mb-2">Limited Time Offer</p>
        <h2 className="font-display text-4xl text-primary-foreground font-bold mb-2">30% OFF</h2>
        <p className="font-display text-lg text-primary-foreground/80 italic">The Entire Collection</p>
        <div className="w-16 h-0.5 bg-brand-gold mx-auto mt-4" />
      </div>
    </div>

    <div className="px-8 py-10 text-center">
      <h3 className="font-display text-xl text-foreground mb-4">Season's Best, Now On Sale</h3>
      <p className="text-muted-foreground font-body text-sm leading-relaxed mb-2">
        For a limited time, enjoy <strong className="text-foreground">30% off</strong> all items in our collection. 
        From premium leather goods to signature accessories — this is your moment.
      </p>
      <p className="text-muted-foreground font-body text-sm mb-6">
        Use code <span className="font-semibold text-brand-gold">SALE30</span> at checkout.
      </p>

      <div className="grid grid-cols-2 gap-4 mb-8">
        {products.map((p) => (
          <div key={p.name} className="bg-secondary rounded overflow-hidden text-left">
            <img src={p.image} alt={p.name} className="w-full h-40 object-cover" />
            <div className="p-3">
              <p className="font-body text-xs font-semibold text-secondary-foreground">{p.name}</p>
              <div className="flex items-center gap-2 mt-1">
                <span className="font-body text-xs text-muted-foreground line-through">{p.old}</span>
                <span className="font-body text-sm font-bold text-brand-gold">{p.price}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      <EmailButton>Shop the Sale</EmailButton>
    </div>

    {/* Urgency bar */}
    <div className="bg-brand-gold px-8 py-4 text-center">
      <p className="font-body text-sm font-semibold text-accent-foreground">
        ⏰ Offer ends February 28, 2026 — Don't miss out!
      </p>
    </div>

    <EmailFooter />
  </div>
);

export default PromoEmail;
