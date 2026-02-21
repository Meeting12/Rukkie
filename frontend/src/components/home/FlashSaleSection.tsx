import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Clock, ArrowRight, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ProductCard } from "@/components/products/ProductCard";
import { fetchProducts } from "@/data/products";
import { ScrollAnimation } from "@/hooks/useScrollAnimation";

export const FlashSaleSection = () => {
  const [flashSaleProducts, setFlashSaleProducts] = useState<any[]>([]);
  const [timeLeft, setTimeLeft] = useState({
    hours: 12,
    minutes: 45,
    seconds: 30,
  });

  useEffect(() => {
    const timer = setInterval(() => {
      setTimeLeft((prev) => {
        let { hours, minutes, seconds } = prev;
        
        if (seconds > 0) {
          seconds--;
        } else {
          seconds = 59;
          if (minutes > 0) {
            minutes--;
          } else {
            minutes = 59;
            if (hours > 0) {
              hours--;
            } else {
              hours = 12;
              minutes = 0;
              seconds = 0;
            }
          }
        }
        
        return { hours, minutes, seconds };
      });
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    let mounted = true;
    const isFlashSaleProduct = (product: any): boolean => {
      const price = Number(product?.price ?? 0);
      const originalPrice = Number(product?.originalPrice ?? product?.original_price ?? 0);
      const hasDiscount = Number.isFinite(originalPrice) && originalPrice > 0 && originalPrice > price;
      return Boolean(product?.isFlashSale || product?.is_flash_sale || hasDiscount);
    };

    const shuffle = <T,>(items: T[]): T[] => {
      const list = [...items];
      for (let i = list.length - 1; i > 0; i -= 1) {
        const j = Math.floor(Math.random() * (i + 1));
        [list[i], list[j]] = [list[j], list[i]];
      }
      return list;
    };
    const load = async () => {
      try {
        const list = await fetchProducts();
        if (!mounted) return;
        const items = Array.isArray(list) ? list : [];
        setFlashSaleProducts(shuffle(items.filter(isFlashSaleProduct)));
      } catch (e) {
        try {
          const mod = await import("@/data/products");
          if (!mounted) return;
          const local = Array.isArray(mod.products) ? mod.products : mod.getFlashSaleProducts();
          setFlashSaleProducts(shuffle(local.filter(isFlashSaleProduct)));
        } catch {
          if (!mounted) return;
          setFlashSaleProducts([]);
        }
      }
    };
    load();
    return () => { mounted = false; };
  }, []);

  if (flashSaleProducts.length === 0) return null;

  return (
    <section className="section-padding bg-foreground text-background relative overflow-hidden">
      {/* Decorative elements */}
      <div className="absolute top-0 right-0 w-96 h-96 bg-primary/10 rounded-full blur-3xl" />
      <div className="absolute bottom-0 left-0 w-80 h-80 bg-primary/5 rounded-full blur-3xl" />
      
      <div className="container mx-auto px-5 sm:px-6 lg:px-8 relative z-10">
        {/* Section Header - Enhanced */}
        <div className="flex flex-col lg:flex-row justify-between items-center gap-8 mb-14">
          <ScrollAnimation animation="fade-up" className="text-center lg:text-left">
            <div className="inline-flex items-center gap-2 bg-primary/20 text-primary px-4 py-2 rounded-full text-sm font-medium mb-4">
              <Zap className="h-4 w-4" />
              Limited Time Offer
            </div>
            <h2 className="font-serif text-4xl md:text-5xl font-bold mb-3">
              Flash Sale
            </h2>
            <p className="text-background/70 text-lg">
              Grab these exclusive deals before they're gone!
            </p>
          </ScrollAnimation>
          
          {/* Countdown Timer - More elegant */}
          <ScrollAnimation animation="slide-left" delay={0.2}>
            <div className="flex items-center gap-4 bg-background/10 backdrop-blur-sm px-6 py-4 rounded-2xl border border-background/10">
              <Clock className="h-6 w-6 text-primary" />
              <div className="flex gap-4">
                {[
                  { value: timeLeft.hours, label: "Hours" },
                  { value: timeLeft.minutes, label: "Mins" },
                  { value: timeLeft.seconds, label: "Secs" },
                ].map((item, index) => (
                  <div key={item.label} className="flex items-center gap-4">
                    <div className="text-center min-w-[50px]">
                      <span className="block text-3xl md:text-4xl font-bold font-serif">
                        {String(item.value).padStart(2, "0")}
                      </span>
                      <span className="text-xs text-background/60 uppercase tracking-wider">
                        {item.label}
                      </span>
                    </div>
                    {index < 2 && (
                      <span className="text-3xl font-light text-background/40">:</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </ScrollAnimation>
        </div>

        {/* Products Grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5 md:gap-8">
          {flashSaleProducts.map((product, index) => (
            <ScrollAnimation
              key={product.id}
              animation="fade-up"
              delay={index * 0.1}
            >
              <ProductCard product={product} />
            </ScrollAnimation>
          ))}
        </div>

        {/* View All */}
        <ScrollAnimation animation="fade-up" delay={0.3} className="text-center mt-12">
          <Button
            variant="heroOutline"
            size="lg"
            className="border-background/30 text-background hover:bg-background hover:text-foreground group"
            asChild
          >
            <Link to="/products?sale=true">
              View All Deals
              <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" />
            </Link>
          </Button>
        </ScrollAnimation>
      </div>
    </section>
  );
};
