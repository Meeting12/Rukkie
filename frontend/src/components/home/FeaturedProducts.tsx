import { Link } from "react-router-dom";
import { ArrowRight, Crown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ProductCard } from "@/components/products/ProductCard";
import { fetchFeaturedProducts, prefetchProductsPage } from "@/data/products";
import { useEffect, useState } from "react";
import { ScrollAnimation } from "@/hooks/useScrollAnimation";

const shuffleProducts = (items: any[]) => {
  const copied = [...items];
  for (let i = copied.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [copied[i], copied[j]] = [copied[j], copied[i]];
  }
  return copied;
};

export const FeaturedProducts = () => {
  const [featuredProducts, setFeaturedProducts] = useState<any[]>([]);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        const list = await fetchFeaturedProducts();
        if (!mounted) return;
        const items = Array.isArray(list) ? list : [];
        setFeaturedProducts(shuffleProducts(items));
      } catch (e) {
        try {
          const mod = await import("@/data/products");
          const local = mod.getFeaturedProducts();
          if (!mounted) return;
          setFeaturedProducts(shuffleProducts(local));
        } catch {
          if (!mounted) return;
          setFeaturedProducts([]);
        }
      }
    };
    load();
    return () => { mounted = false; };
  }, []);

  return (
    <section className="section-padding bg-secondary/20 relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute bottom-0 left-0 w-80 h-80 bg-primary/5 rounded-full blur-3xl translate-y-1/2 -translate-x-1/2" />
      
      <div className="container mx-auto px-5 sm:px-6 lg:px-8 relative z-10">
        {/* Section Header - More sophisticated */}
        <div className="flex flex-col lg:flex-row justify-between items-center gap-8 mb-14">
          <ScrollAnimation animation="fade-up" className="text-center lg:text-left max-w-xl">
            <div className="inline-flex items-center gap-2 text-primary mb-4">
              <Crown className="h-5 w-5" />
              <span className="text-sm font-medium uppercase tracking-[0.2em]">
                Handpicked
              </span>
            </div>
            <h2 className="font-serif text-4xl md:text-5xl font-bold text-foreground mb-4">
              Featured Products
            </h2>
            <p className="text-muted-foreground text-lg">
              Discover our most loved items, curated for quality and style
            </p>
          </ScrollAnimation>
          
          <ScrollAnimation animation="slide-left" delay={0.2}>
            <Button variant="outline" size="lg" className="group" asChild>
              <Link
                to="/products"
                onMouseEnter={prefetchProductsPage}
                onFocus={prefetchProductsPage}
                onTouchStart={prefetchProductsPage}
              >
                View All Products
                <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" />
              </Link>
            </Button>
          </ScrollAnimation>
        </div>

        {/* Products Grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5 md:gap-8">
          {featuredProducts.map((product) => (
            <ScrollAnimation
              key={product.id}
              animation="fade-up"
              delay={0}
            >
              <ProductCard product={product} />
            </ScrollAnimation>
          ))}
        </div>
      </div>
    </section>
  );
};
