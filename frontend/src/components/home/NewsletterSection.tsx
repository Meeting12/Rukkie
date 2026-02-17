import { useState } from "react";
import { Mail, ArrowRight, Gift, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { fetchJSON } from "@/lib/api";
import { toast } from "sonner";
import { ScrollAnimation } from "@/hooks/useScrollAnimation";

export const NewsletterSection = () => {
  const [email, setEmail] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const parseApiErrorMessage = (raw: string) => {
    try {
      const parsed = JSON.parse(raw);
      return parsed?.detail || parsed?.error || raw;
    } catch {
      return raw;
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;

    setIsLoading(true);
    try {
      const resp = await fetchJSON("/api/newsletter/subscribe/", {
        method: "POST",
        body: JSON.stringify({ email, source: "home_newsletter" }),
      });
      if (resp?.already_subscribed) {
        toast.info("You are already subscribed to our newsletter.");
      } else {
        toast.success("Thanks for subscribing! Check your email for exclusive offers.");
      }
      setEmail("");
    } catch (err: any) {
      toast.error(parseApiErrorMessage(err?.message || "Subscription failed"));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <section className="section-padding relative overflow-hidden">
      {/* Elegant gradient background */}
      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-accent/10 to-secondary/20" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-primary/5 rounded-full blur-3xl" />
      
      <div className="container mx-auto px-5 sm:px-6 lg:px-8 relative z-10">
        <div className="max-w-4xl mx-auto">
          <ScrollAnimation animation="scale">
            <div className="bg-card rounded-3xl p-8 md:p-14 shadow-xl border border-border relative overflow-hidden">
              {/* Decorative corner elements */}
              <div className="absolute top-0 right-0 w-32 h-32 bg-primary/5 rounded-bl-full" />
              <div className="absolute bottom-0 left-0 w-24 h-24 bg-accent/10 rounded-tr-full" />
              
              <div className="relative z-10 text-center">
                <ScrollAnimation animation="fade-up" delay={0.1}>
                  <div className="inline-flex items-center justify-center w-20 h-20 bg-primary/10 rounded-2xl mb-8">
                    <Mail className="h-10 w-10 text-primary" />
                  </div>
                </ScrollAnimation>
                
                <ScrollAnimation animation="fade-up" delay={0.2}>
                  <h2 className="font-serif text-4xl md:text-5xl font-bold text-foreground mb-4">
                    Stay in the Loop
                  </h2>
                </ScrollAnimation>
                
                <ScrollAnimation animation="fade-up" delay={0.3}>
                  <p className="text-muted-foreground text-lg mb-8 max-w-lg mx-auto leading-relaxed">
                    Subscribe to our newsletter and get 15% off your first order, plus exclusive access to new arrivals and special offers.
                  </p>
                </ScrollAnimation>

                {/* Benefits */}
                <ScrollAnimation animation="fade-up" delay={0.4}>
                  <div className="flex flex-wrap justify-center gap-6 mb-10">
                    {[
                      { icon: Gift, text: "15% Off First Order" },
                      { icon: Sparkles, text: "Exclusive Deals" },
                    ].map((item) => (
                      <div key={item.text} className="flex items-center gap-2 text-sm text-muted-foreground">
                        <item.icon className="h-4 w-4 text-primary" />
                        <span>{item.text}</span>
                      </div>
                    ))}
                  </div>
                </ScrollAnimation>

                <ScrollAnimation animation="fade-up" delay={0.5}>
                  <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-4 max-w-md mx-auto">
                    <Input
                      type="email"
                      placeholder="Enter your email address"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="flex-1 h-14 px-6 text-base rounded-xl"
                      required
                    />
                    <Button 
                      variant="hero" 
                      type="submit" 
                      disabled={isLoading}
                      className="h-14 px-8 rounded-xl group"
                    >
                      {isLoading ? (
                        "Subscribing..."
                      ) : (
                        <>
                          Subscribe
                          <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" />
                        </>
                      )}
                    </Button>
                  </form>
                </ScrollAnimation>

                <ScrollAnimation animation="fade-in" delay={0.6}>
                  <p className="text-xs text-muted-foreground mt-6">
                    By subscribing, you agree to our Privacy Policy and consent to receive marketing emails.
                  </p>
                </ScrollAnimation>
              </div>
            </div>
          </ScrollAnimation>
        </div>
      </div>
    </section>
  );
};
