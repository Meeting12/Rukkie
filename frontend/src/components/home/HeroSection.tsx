import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Truck, Shield, RefreshCw, ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollAnimation } from "@/hooks/useScrollAnimation";
import useEmblaCarousel from "embla-carousel-react";
import Autoplay from "embla-carousel-autoplay";
import { cn } from "@/lib/utils";
import { fetchHomeContent, heroSlidesFallback } from "@/data/products";
import { HeroSlide } from "@/types/product";

export const HeroSection = () => {
  const [heroSlides, setHeroSlides] = useState<HeroSlide[]>(heroSlidesFallback);
  const [emblaRef, emblaApi] = useEmblaCarousel({
    loop: true,
    watchDrag: (_api, event) => {
      const target = event.target as HTMLElement | null;
      if (target?.closest("a, button, input, textarea, select, label")) {
        return false;
      }
      return true;
    },
  }, [
    Autoplay({ delay: 5000, stopOnInteraction: false }),
  ]);
  const [selectedIndex, setSelectedIndex] = useState(0);

  useEffect(() => {
    let mounted = true;
    fetchHomeContent().then((content) => {
      if (!mounted) return;
      if (Array.isArray(content.heroSlides) && content.heroSlides.length > 0) {
        setHeroSlides(content.heroSlides);
      }
    }).catch(() => {});
    return () => { mounted = false; };
  }, []);

  const scrollPrev = useCallback(() => emblaApi?.scrollPrev(), [emblaApi]);
  const scrollNext = useCallback(() => emblaApi?.scrollNext(), [emblaApi]);
  const scrollTo = useCallback((index: number) => emblaApi?.scrollTo(index), [emblaApi]);

  useEffect(() => {
    if (!emblaApi) return;
    
    const onSelect = () => setSelectedIndex(emblaApi.selectedScrollSnap());
    emblaApi.on("select", onSelect);
    onSelect();
    
    return () => {
      emblaApi.off("select", onSelect);
    };
  }, [emblaApi]);

  return (
    <section className="relative overflow-hidden">
      {/* Hero Carousel */}
      <div className="relative" ref={emblaRef}>
        <div className="flex">
          {heroSlides.map((slide, index) => (
            <div
              key={slide.id}
              className="relative min-h-[85vh] md:min-h-[90vh] flex items-center flex-[0_0_100%]"
            >
              {/* Background with elegant gradient overlay */}
              <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-background via-secondary/30 to-accent/20" />
              
              {/* Decorative elements */}
              <div className="pointer-events-none absolute top-20 left-10 w-72 h-72 bg-primary/5 rounded-full blur-3xl" />
              <div className="pointer-events-none absolute bottom-20 right-10 w-96 h-96 bg-accent/30 rounded-full blur-3xl" />
              <div className="pointer-events-none absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-gradient-radial from-primary/5 to-transparent rounded-full" />
              
              <div className="container mx-auto px-5 sm:px-6 lg:px-8 relative z-10">
                <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
                  {/* Content */}
                  <div className="text-center lg:text-left space-y-8">
                    <div
                      className={cn(
                        "inline-flex items-center gap-2 bg-primary/10 text-primary px-4 py-2 rounded-full text-sm font-medium transition-all duration-700",
                        selectedIndex === index ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
                      )}
                    >
                      {slide.badge}
                    </div>
                    
                    <div
                      className={cn(
                        "space-y-4 transition-all duration-700 delay-100",
                        selectedIndex === index ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
                      )}
                    >
                      <h1 className="font-serif text-5xl md:text-6xl lg:text-7xl font-bold text-foreground leading-[1.1] tracking-tight">
                        {slide.title}
                        <span className="block mt-2 text-gradient">{slide.titleAccent}</span>
                      </h1>
                    </div>
                    
                    <p
                      className={cn(
                        "text-lg md:text-xl text-muted-foreground max-w-xl mx-auto lg:mx-0 leading-relaxed transition-all duration-700 delay-200",
                        selectedIndex === index ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
                      )}
                    >
                      {slide.description}
                    </p>
                    
                    <div
                      className={cn(
                        "flex flex-col sm:flex-row gap-4 justify-center lg:justify-start transition-all duration-700 delay-300",
                        selectedIndex === index ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
                      )}
                    >
                      <Button variant="hero" size="xl" asChild>
                        <Link to={slide.cta.link}>
                          {slide.cta.text}
                          <ArrowRight className="ml-2 h-5 w-5" />
                        </Link>
                      </Button>
                      <Button variant="heroOutline" size="xl" asChild>
                        <Link to={slide.secondaryCta.link}>{slide.secondaryCta.text}</Link>
                      </Button>
                    </div>

                    {/* Mini stats - only on first slide */}
                    {index === 0 && (
                      <div
                        className={cn(
                          "flex items-center justify-center lg:justify-start gap-8 pt-4 transition-all duration-700 delay-400",
                          selectedIndex === index ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
                        )}
                      >
                        <div className="text-center lg:text-left">
                          <div className="font-serif text-3xl font-bold text-foreground">10K+</div>
                          <div className="text-sm text-muted-foreground">Happy Customers</div>
                        </div>
                        <div className="w-px h-12 bg-border" />
                        <div className="text-center lg:text-left">
                          <div className="font-serif text-3xl font-bold text-foreground">500+</div>
                          <div className="text-sm text-muted-foreground">Premium Products</div>
                        </div>
                        <div className="w-px h-12 bg-border hidden sm:block" />
                        <div className="text-center lg:text-left hidden sm:block">
                          <div className="font-serif text-3xl font-bold text-foreground">4.9★</div>
                          <div className="text-sm text-muted-foreground">Customer Rating</div>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Hero Image */}
                  <div className="relative hidden lg:block">
                    <div
                      className={cn(
                        "relative z-10 transition-all duration-700 delay-200",
                        selectedIndex === index ? "opacity-100 scale-100" : "opacity-0 scale-95"
                      )}
                    >
                      {/* Main image container with elegant frame */}
                      <div className="relative">
                        <div className="absolute -inset-4 bg-gradient-to-br from-primary/20 via-transparent to-accent/30 rounded-3xl blur-xl" />
                        <img
                          src={slide.image}
                          alt={`${slide.title} ${slide.titleAccent}`}
                          className="relative rounded-2xl shadow-2xl object-cover w-full max-h-[600px] border border-border/50"
                        />
                        
                        {/* Floating badge */}
                        <div
                          className={cn(
                            "absolute -bottom-6 -left-6 transition-all duration-700 delay-500",
                            selectedIndex === index ? "opacity-100 translate-x-0" : "opacity-0 -translate-x-4"
                          )}
                        >
                          <div className="bg-card p-4 rounded-xl shadow-xl border border-border">
                            <div className="flex items-center gap-3">
                              <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center">
                                <Truck className="h-6 w-6 text-primary" />
                              </div>
                              <div>
                                <div className="font-semibold text-foreground">Free Shipping</div>
                                <div className="text-sm text-muted-foreground">On orders $100+</div>
                              </div>
                            </div>
                          </div>
                        </div>
                        
                        {/* Promo floating element */}
                        <div
                          className={cn(
                            "absolute -top-4 -right-4 transition-all duration-700 delay-600",
                            selectedIndex === index ? "opacity-100 translate-x-0" : "opacity-0 translate-x-4"
                          )}
                        >
                          <div className="bg-primary text-primary-foreground px-6 py-3 rounded-full shadow-xl">
                            <span className="font-medium">{slide.promo}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Navigation Arrows */}
      <button
        onClick={scrollPrev}
        className="absolute left-4 top-1/2 -translate-y-1/2 z-20 p-3 bg-card/80 backdrop-blur-sm rounded-full shadow-lg border border-border hover:bg-card transition-colors"
        aria-label="Previous slide"
      >
        <ChevronLeft className="h-6 w-6 text-foreground" />
      </button>
      <button
        onClick={scrollNext}
        className="absolute right-4 top-1/2 -translate-y-1/2 z-20 p-3 bg-card/80 backdrop-blur-sm rounded-full shadow-lg border border-border hover:bg-card transition-colors"
        aria-label="Next slide"
      >
        <ChevronRight className="h-6 w-6 text-foreground" />
      </button>

      {/* Dot Indicators */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-20 flex gap-3">
        {heroSlides.map((_, index) => (
          <button
            key={index}
            onClick={() => scrollTo(index)}
            className={cn(
              "h-2 rounded-full transition-all duration-300",
              selectedIndex === index
                ? "w-8 bg-primary"
                : "w-2 bg-foreground/30 hover:bg-foreground/50"
            )}
            aria-label={`Go to slide ${index + 1}`}
          />
        ))}
      </div>

      {/* Trust Badges - Refined */}
      <div className="bg-card border-t border-border py-10">
        <div className="container mx-auto px-5 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              { icon: Truck, title: "Free Shipping", desc: "On orders over $100" },
              { icon: Shield, title: "Secure Payment", desc: "100% secure checkout" },
              { icon: RefreshCw, title: "Easy Returns", desc: "30-day return policy" },
            ].map((item, index) => (
              <ScrollAnimation
                key={item.title}
                animation="fade-up"
                delay={index * 0.1}
              >
                <div className="flex items-center justify-center gap-4 group">
                  <div className="w-14 h-14 bg-primary/10 rounded-xl flex items-center justify-center group-hover:bg-primary/20 transition-colors duration-300">
                    <item.icon className="h-7 w-7 text-primary" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-foreground">{item.title}</h4>
                    <p className="text-sm text-muted-foreground">{item.desc}</p>
                  </div>
                </div>
              </ScrollAnimation>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};
