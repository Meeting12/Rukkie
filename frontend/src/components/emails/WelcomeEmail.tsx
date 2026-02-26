import EmailHeader from "./EmailHeader";
import EmailFooter from "./EmailFooter";
import EmailButton from "./EmailButton";
import heroBanner from "@/assets/hero-banner.jpg";

const WelcomeEmail = () => (
  <div className="max-w-[600px] mx-auto bg-card shadow-xl overflow-hidden">
    <EmailHeader />

    <div className="relative">
      <img src={heroBanner} alt="De-Rukkies Collection" className="w-full h-56 object-cover" />
      <div className="absolute inset-0 bg-primary/40 flex items-center justify-center">
        <h2 className="font-display text-3xl text-primary-foreground font-semibold tracking-wide">
          Welcome to the Family
        </h2>
      </div>
    </div>

    <div className="px-8 py-10 text-center">
      <p className="text-muted-foreground font-body text-sm leading-relaxed mb-2">Dear Valued Customer,</p>
      <h3 className="font-display text-2xl text-foreground mb-4">Thank You for Joining Us</h3>
      <div className="w-12 h-0.5 bg-brand-gold mx-auto mb-6" />
      <p className="text-muted-foreground font-body text-sm leading-relaxed mb-6">
        We're thrilled to welcome you to <strong className="text-foreground">De-Rukkies Collection</strong> — where elegance meets everyday style. 
        As a member, you'll enjoy exclusive access to new arrivals, special promotions, and curated style guides.
      </p>
      <p className="text-muted-foreground font-body text-sm leading-relaxed mb-8">
        Use code <span className="font-semibold text-brand-gold">WELCOME15</span> for 15% off your first order.
      </p>
      <EmailButton>Start Shopping</EmailButton>
    </div>

    <div className="bg-secondary px-8 py-8">
      <h4 className="font-display text-lg text-center text-secondary-foreground mb-6">Why Shop With Us?</h4>
      <div className="grid grid-cols-3 gap-4 text-center">
        {[
          { title: "Free Shipping", desc: "On orders over ₦50,000" },
          { title: "Easy Returns", desc: "30-day return policy" },
          { title: "Premium Quality", desc: "Handpicked materials" },
        ].map((item) => (
          <div key={item.title}>
            <p className="font-body text-xs font-semibold text-secondary-foreground uppercase tracking-wide mb-1">{item.title}</p>
            <p className="font-body text-xs text-muted-foreground">{item.desc}</p>
          </div>
        ))}
      </div>
    </div>

    <EmailFooter />
  </div>
);

export default WelcomeEmail;
