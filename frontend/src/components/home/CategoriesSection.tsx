import { CategoryCard } from "@/components/products/CategoryCard";
import { fetchHomeContent } from "@/data/products";
import { ScrollAnimation } from "@/hooks/useScrollAnimation";
import { useEffect, useState } from "react";
import { Category } from "@/types/product";

export const CategoriesSection = () => {
  return (
    <section className="section-padding bg-background relative overflow-hidden">
      {/* Subtle background decoration */}
      <div className="absolute top-0 right-0 w-96 h-96 bg-accent/20 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />
      
      <div className="container mx-auto px-5 sm:px-6 lg:px-8 relative z-10">
        {/* Section Header - More elegant */}
        <ScrollAnimation animation="fade-up" className="text-center mb-16 max-w-2xl mx-auto">
          <span className="inline-block text-sm font-medium text-primary uppercase tracking-[0.2em] mb-4">
            Browse By
          </span>
          <h2 className="font-serif text-4xl md:text-5xl font-bold text-foreground mb-4">
            Shop Categories
          </h2>
          <div className="w-24 h-1 bg-gradient-to-r from-transparent via-primary to-transparent mx-auto mb-6" />
          <p className="text-muted-foreground text-lg leading-relaxed">
            Explore our curated collections across electronics, fashion, beauty, and home essentials
          </p>
        </ScrollAnimation>

        {/* Categories Grid - Enhanced */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-5 md:gap-8">
          {/* fetch categories from API */}
          <CategoriesList />
        </div>
      </div>
    </section>
  );
};

const CategoriesList = () => {
  const [cats, setCats] = useState<Category[]>([]);

  useEffect(() => {
    let mounted = true;
    fetchHomeContent().then((content) => {
      if (!mounted) return;
      setCats(content.categories || []);
    }).catch(() => {});
    return () => { mounted = false; };
  }, []);

  return (
    <>
      {cats.map((category) => (
        <ScrollAnimation key={category.id} animation="fade-up" delay={0}>
          <CategoryCard category={category} />
        </ScrollAnimation>
      ))}
    </>
  );
};
