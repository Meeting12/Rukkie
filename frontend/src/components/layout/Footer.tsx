import { useState } from "react";
import { Link } from "react-router-dom";
import { Facebook, Instagram, Twitter, Youtube, Mail, MapPin, Phone } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { fetchJSON } from "@/lib/api";
import { toast } from "sonner";

const footerLinks = {
  shop: [
    { name: "Electronics", href: "/products?category=electronics" },
    { name: "Fashion", href: "/products?category=fashion" },
    { name: "Beauty", href: "/products?category=beauty" },
    { name: "Home & Kitchen", href: "/products?category=home-kitchen" },
  ],
  company: [
    { name: "About Us", href: "/about" },
    { name: "Contact", href: "/contact" },
    { name: "FAQ", href: "/faq" },
    { name: "My Account", href: "/account" },
  ],
  support: [
    { name: "Shipping & Returns", href: "/shipping-returns" },
    { name: "Track Order", href: "/order-tracking" },
    { name: "Wishlist", href: "/wishlist" },
    { name: "Contact Support", href: "/contact" },
  ],
  legal: [
    { name: "Privacy Policy", href: "/privacy-policy" },
    { name: "Terms of Service", href: "/terms-of-service" },
  ],
};

const socialLinks = [
  { name: "Facebook", icon: Facebook, href: "https://facebook.com" },
  { name: "Instagram", icon: Instagram, href: "https://instagram.com" },
  { name: "Twitter", icon: Twitter, href: "https://twitter.com" },
  { name: "YouTube", icon: Youtube, href: "https://youtube.com" },
];

export const Footer = () => {
  const [email, setEmail] = useState("");
  const [isSubscribing, setIsSubscribing] = useState(false);

  const parseApiErrorMessage = (raw: string) => {
    try {
      const parsed = JSON.parse(raw);
      return parsed?.detail || parsed?.error || raw;
    } catch {
      return raw;
    }
  };

  const handleSubscribe = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;
    setIsSubscribing(true);
    try {
      const resp = await fetchJSON("/api/newsletter/subscribe/", {
        method: "POST",
        body: JSON.stringify({ email, source: "footer" }),
      });
      if (resp?.already_subscribed) {
        toast.info("You are already subscribed to our newsletter.");
      } else {
        toast.success("Subscription successful. Please check your email.");
      }
      setEmail("");
    } catch (err: any) {
      toast.error(parseApiErrorMessage(err?.message || "Subscription failed"));
    } finally {
      setIsSubscribing(false);
    }
  };

  return (
    <footer className="bg-foreground text-background">
      {/* Newsletter Section */}
      <div className="border-b border-background/10">
        <div className="container mx-auto px-4 py-12">
          <div className="max-w-2xl mx-auto text-center">
            <h3 className="font-serif text-2xl md:text-3xl font-semibold mb-3">
              Join Our Community
            </h3>
            <p className="text-background/70 mb-6">
              Subscribe to get exclusive offers, new arrivals, and style tips delivered to your inbox.
            </p>
            <form onSubmit={handleSubscribe} className="flex flex-col sm:flex-row gap-3 max-w-md mx-auto">
              <Input
                type="email"
                placeholder="Enter your email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="bg-background/10 border-background/20 text-background placeholder:text-background/50 focus:border-primary"
                required
              />
              <Button type="submit" variant="hero" className="bg-primary hover:bg-primary/90" disabled={isSubscribing}>
                {isSubscribing ? "Subscribing..." : "Subscribe"}
              </Button>
            </form>
          </div>
        </div>
      </div>

      {/* Main Footer */}
      <div className="container mx-auto px-4 py-12">
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-8">
          {/* Brand */}
          <div className="col-span-2">
            <Link to="/" className="inline-block mb-4">
              <h2 className="font-serif text-xl font-bold">
                <span className="text-primary">De-Rukkies</span>
                <span> Collections</span>
              </h2>
            </Link>
            <p className="text-background/70 text-sm mb-6 max-w-xs">
              Your destination for quality products. We curate the finest electronics, fashion, beauty, and home essentials for the modern lifestyle.
            </p>
            {/* Contact Info */}
            <div className="space-y-2 text-sm text-background/70">
              <div className="flex items-center gap-2">
                <Mail className="h-4 w-4" />
                <span className="force-normal-case">support@rukkies.com</span>
              </div>
              <div className="flex items-center gap-2">
                <Phone className="h-4 w-4" />
                <span className="force-normal-case">+234803 397 2142</span>
              </div>
              <div className="flex items-center gap-2">
                <MapPin className="h-4 w-4" />
                <span className="force-normal-case">21 Off Ughelli Patani Expressway, Uhweru Town, Ughelli, Delta State</span>
              </div>
            </div>
          </div>

          {/* Shop Links */}
          <div>
            <h4 className="font-semibold mb-4 text-sm uppercase tracking-wider">Shop</h4>
            <ul className="space-y-2">
              {footerLinks.shop.map((link) => (
                <li key={link.name}>
                  <Link
                    to={link.href}
                    className="text-sm text-background/70 hover:text-primary transition-colors"
                  >
                    {link.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Company Links */}
          <div>
            <h4 className="font-semibold mb-4 text-sm uppercase tracking-wider">Company</h4>
            <ul className="space-y-2">
              {footerLinks.company.map((link) => (
                <li key={link.name}>
                  <Link
                    to={link.href}
                    className="text-sm text-background/70 hover:text-primary transition-colors"
                  >
                    {link.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Support Links */}
          <div>
            <h4 className="font-semibold mb-4 text-sm uppercase tracking-wider">Support</h4>
            <ul className="space-y-2">
              {footerLinks.support.map((link) => (
                <li key={link.name}>
                  <Link
                    to={link.href}
                    className="text-sm text-background/70 hover:text-primary transition-colors"
                  >
                    {link.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Legal Links */}
          <div>
            <h4 className="font-semibold mb-4 text-sm uppercase tracking-wider">Legal</h4>
            <ul className="space-y-2">
              {footerLinks.legal.map((link) => (
                <li key={link.name}>
                  <Link
                    to={link.href}
                    className="text-sm text-background/70 hover:text-primary transition-colors"
                  >
                    {link.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="mt-12 pt-8 border-t border-background/10">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4">
            <p className="text-sm text-background/60">
              © 2024 De-Rukkies Collections. All rights reserved.
            </p>
            
            {/* Social Links */}
            <div className="flex items-center gap-4">
              {socialLinks.map((social) => (
                <a
                  key={social.name}
                  href={social.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-background/60 hover:text-primary transition-colors"
                  aria-label={social.name}
                >
                  <social.icon className="h-5 w-5" />
                </a>
              ))}
            </div>

            {/* Trust Badges */}
            <div className="flex items-center gap-4 text-sm text-background/60">
              <span className="flex items-center gap-1">
                <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
                </svg>
                Secure Payments
              </span>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
};
