import { FormEvent, KeyboardEvent, useEffect, useMemo, useRef, useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { Search, ShoppingBag, Heart, Menu, X, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useCart } from "@/context/CartContext";
import { useWishlist } from "@/context/WishlistContext";
import { fetchSearchSuggestions, prefetchProductsPage } from "@/data/products";
import { Product } from "@/types/product";
import { cn } from "@/lib/utils";

const navigation = [
  { name: "Home", href: "/" },
  { name: "Shop", href: "/products" },
  { name: "About", href: "/about" },
  { name: "Contact", href: "/contact" },
];

const promoMessages = [
  "Free shipping on orders over $100",
  "Use code WELCOME15 for 15% off your first order",
  "New arrivals drop every week across fashion and lifestyle",
  "Secure checkout with Stripe, Flutterwave, and PayPal card",
  "Fast support and order updates in your account mailbox",
];

export const Header = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [desktopSearchTerm, setDesktopSearchTerm] = useState("");
  const [mobileSearchTerm, setMobileSearchTerm] = useState("");
  const [desktopSuggestions, setDesktopSuggestions] = useState<Product[]>([]);
  const [mobileSuggestions, setMobileSuggestions] = useState<Product[]>([]);
  const [desktopLoading, setDesktopLoading] = useState(false);
  const [mobileLoading, setMobileLoading] = useState(false);
  const [desktopSubmitting, setDesktopSubmitting] = useState(false);
  const [mobileSubmitting, setMobileSubmitting] = useState(false);
  const [desktopActiveIndex, setDesktopActiveIndex] = useState(-1);
  const [mobileActiveIndex, setMobileActiveIndex] = useState(-1);
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { getCartCount } = useCart();
  const { items: wishlistItems } = useWishlist();
  const desktopSearchRef = useRef<HTMLDivElement | null>(null);
  const mobileSearchRef = useRef<HTMLDivElement | null>(null);

  const cartCount = getCartCount();
  const wishlistCount = wishlistItems.length;
  const promoLoopText = useMemo(() => promoMessages.join(" | "), []);
  const activeSearchQuery = location.pathname === "/products" ? (searchParams.get("q") || "").trim() : "";

  useEffect(() => {
    setDesktopSearchTerm(activeSearchQuery);
    setMobileSearchTerm(activeSearchQuery);
    setDesktopSubmitting(false);
    setMobileSubmitting(false);
  }, [activeSearchQuery, location.pathname]);

  useEffect(() => {
    setDesktopActiveIndex(-1);
  }, [desktopSuggestions]);

  useEffect(() => {
    setMobileActiveIndex(-1);
  }, [mobileSuggestions]);

  useEffect(() => {
    if (!isSearchOpen) {
      setDesktopSuggestions([]);
      setDesktopLoading(false);
      setDesktopActiveIndex(-1);
      return;
    }
    const cleaned = desktopSearchTerm.trim();
    if (cleaned.length < 2) {
      setDesktopSuggestions([]);
      setDesktopLoading(false);
      setDesktopActiveIndex(-1);
      return;
    }
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      setDesktopLoading(true);
      try {
        const rows = await fetchSearchSuggestions(cleaned, 6);
        if (!cancelled) setDesktopSuggestions(rows);
      } catch {
        if (!cancelled) setDesktopSuggestions([]);
      } finally {
        if (!cancelled) setDesktopLoading(false);
      }
    }, 220);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [desktopSearchTerm, isSearchOpen]);

  useEffect(() => {
    if (!isMenuOpen) {
      setMobileSuggestions([]);
      setMobileLoading(false);
      setMobileActiveIndex(-1);
      return;
    }
    const cleaned = mobileSearchTerm.trim();
    if (cleaned.length < 2) {
      setMobileSuggestions([]);
      setMobileLoading(false);
      setMobileActiveIndex(-1);
      return;
    }
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      setMobileLoading(true);
      try {
        const rows = await fetchSearchSuggestions(cleaned, 6);
        if (!cancelled) setMobileSuggestions(rows);
      } catch {
        if (!cancelled) setMobileSuggestions([]);
      } finally {
        if (!cancelled) setMobileLoading(false);
      }
    }, 220);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [mobileSearchTerm, isMenuOpen]);

  useEffect(() => {
    const handlePointerDown = (event: MouseEvent | TouchEvent) => {
      const target = event.target as Node | null;
      if (desktopSearchRef.current && target && !desktopSearchRef.current.contains(target)) {
        setIsSearchOpen(false);
        setDesktopSuggestions([]);
        setDesktopActiveIndex(-1);
      }
      if (mobileSearchRef.current && target && !mobileSearchRef.current.contains(target)) {
        setMobileSuggestions([]);
        setMobileActiveIndex(-1);
      }
    };

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("touchstart", handlePointerDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("touchstart", handlePointerDown);
    };
  }, []);

  const submitSearch = (rawValue: string, { closeMobileMenu = false, closeDesktopSearch = false } = {}) => {
    const query = rawValue.trim();
    navigate(query ? `/products?q=${encodeURIComponent(query)}` : "/products");
    setDesktopSuggestions([]);
    setMobileSuggestions([]);
    setDesktopActiveIndex(-1);
    setMobileActiveIndex(-1);
    if (closeMobileMenu) setIsMenuOpen(false);
    if (closeDesktopSearch) setIsSearchOpen(false);
  };

  const handleDesktopSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setDesktopSubmitting(true);
    submitSearch(desktopSearchTerm, { closeDesktopSearch: true });
  };

  const handleMobileSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setMobileSubmitting(true);
    submitSearch(mobileSearchTerm, { closeMobileMenu: true });
  };

  const handleSuggestionSelect = (slug: string, { closeMobileMenu = false, closeDesktopSearch = false } = {}) => {
    if (!slug) return;
    navigate(`/product/${encodeURIComponent(slug)}`);
    setDesktopSuggestions([]);
    setMobileSuggestions([]);
    setDesktopActiveIndex(-1);
    setMobileActiveIndex(-1);
    if (closeMobileMenu) setIsMenuOpen(false);
    if (closeDesktopSearch) setIsSearchOpen(false);
  };

  const moveActiveIndex = (current: number, size: number, direction: 1 | -1) => {
    if (!size) return -1;
    if (current < 0) return direction === 1 ? 0 : size - 1;
    return (current + direction + size) % size;
  };

  const handleSuggestionKeyDown = (
    event: KeyboardEvent<HTMLInputElement>,
    suggestions: Product[],
    activeIndex: number,
    setActiveIndex: (value: number) => void,
    selectSuggestion: (slug: string) => void,
    closeSearch?: () => void,
  ) => {
    if (event.key === "ArrowDown") {
      if (!suggestions.length) return;
      event.preventDefault();
      setActiveIndex(moveActiveIndex(activeIndex, suggestions.length, 1));
      return;
    }
    if (event.key === "ArrowUp") {
      if (!suggestions.length) return;
      event.preventDefault();
      setActiveIndex(moveActiveIndex(activeIndex, suggestions.length, -1));
      return;
    }
    if (event.key === "Enter" && activeIndex >= 0 && suggestions[activeIndex]) {
      event.preventDefault();
      selectSuggestion(suggestions[activeIndex].slug);
      return;
    }
    if (event.key === "Escape") {
      setActiveIndex(-1);
      if (closeSearch) closeSearch();
    }
  };

  const SuggestionList = ({
    suggestions,
    loading,
    onSelect,
    activeIndex,
    onHighlight,
    query,
    onViewAll,
  }: {
    suggestions: Product[];
    loading: boolean;
    onSelect: (slug: string) => void;
    activeIndex: number;
    onHighlight: (index: number) => void;
    query: string;
    onViewAll: () => void;
  }) => {
    if (loading) {
      return <div className="rounded-xl border border-border bg-background px-4 py-3 text-sm text-muted-foreground shadow-lg">Searching...</div>;
    }
    if (!suggestions.length && query.trim().length < 2) return null;
    return (
      <div className="rounded-xl border border-border bg-background p-2 shadow-lg">
        {suggestions.length ? (
          <ul className="space-y-1">
          {suggestions.map((product, index) => (
            <li key={product.id}>
              <button
                type="button"
                className={cn(
                  "flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left transition-colors hover:bg-secondary",
                  activeIndex === index ? "bg-secondary" : ""
                )}
                onMouseDown={(event) => {
                  event.preventDefault();
                  onSelect(product.slug);
                }}
                onMouseEnter={() => onHighlight(index)}
                onFocus={() => onHighlight(index)}
              >
                <img
                  src={product.images[0]}
                  alt={product.name}
                  className="h-10 w-10 rounded-md border border-border object-cover bg-secondary"
                />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium text-foreground">{product.name}</span>
                  <span className="block truncate text-xs text-muted-foreground">{product.category}</span>
                </span>
                <span className="text-xs font-semibold text-primary">${product.price.toFixed(2)}</span>
              </button>
            </li>
          ))}
          </ul>
        ) : (
          <div className="px-3 py-2 text-sm text-muted-foreground">No matching products found.</div>
        )}
        {query.trim().length >= 2 && (
          <button
            type="button"
            className="mt-2 flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm font-medium text-foreground transition-colors hover:bg-secondary"
            onMouseDown={(event) => {
              event.preventDefault();
              onViewAll();
            }}
          >
            <span>View all results for "{query.trim()}"</span>
            <Search className="h-4 w-4 text-muted-foreground" />
          </button>
        )}
      </div>
    );
  };

  return (
    <header className="sticky top-0 z-50 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80 border-b border-border">
      {/* Top bar */}
      <div className="bg-primary py-2 text-sm overflow-hidden">
        <p className="sr-only">Free shipping on orders over $100 | Use code WELCOME15 for 15% off</p>
        <div className="promo-ticker-mask">
          <div className="promo-ticker-track">
            <p className="promo-ticker-item text-primary-foreground/95">
              {promoLoopText}
            </p>
            <p
              aria-hidden="true"
              className="promo-ticker-item text-primary-foreground/95"
            >
              {promoLoopText}
            </p>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16 md:h-20">
          {/* Mobile menu button */}
          <button
            className="md:hidden p-2"
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            aria-label="Toggle menu"
          >
            {isMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>

          {/* Logo */}
          <Link to="/" className="flex items-center">
            <h1 className="text-xl md:text-2xl font-serif font-bold tracking-tight">
              <span className="text-primary">De-Rukkies</span>
              <span className="text-foreground"> Collections</span>
            </h1>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-8">
            {navigation.map((item) => (
              <Link
                key={item.name}
                to={item.href}
                onMouseEnter={item.href === "/products" ? prefetchProductsPage : undefined}
                onFocus={item.href === "/products" ? prefetchProductsPage : undefined}
                onTouchStart={item.href === "/products" ? prefetchProductsPage : undefined}
                className={cn(
                  "text-sm font-medium transition-colors elegant-underline",
                  location.pathname === item.href
                    ? "text-primary"
                    : "text-foreground/80 hover:text-foreground"
                )}
              >
                {item.name}
              </Link>
            ))}
          </nav>

          {/* Actions */}
          <div className="flex items-center gap-2 md:gap-4">
            {/* Search */}
            <div ref={desktopSearchRef} className="relative hidden sm:block">
              {isSearchOpen ? (
                <div className="absolute right-0 top-1/2 w-80 -translate-y-1/2 animate-fade-in">
                  <form
                    onSubmit={handleDesktopSubmit}
                    className="flex items-center gap-2 rounded-xl border border-border bg-background p-2 shadow-lg"
                  >
                    <Input
                      type="search"
                      placeholder="Search products..."
                      className="border-0 shadow-none focus-visible:ring-0"
                      autoFocus
                      value={desktopSearchTerm}
                      onChange={(event) => {
                        setDesktopSearchTerm(event.target.value);
                        setDesktopActiveIndex(-1);
                      }}
                      onFocus={() => {
                        if (desktopSearchTerm.trim().length >= 2) {
                          setIsSearchOpen(true);
                        }
                      }}
                      onKeyDown={(event) => {
                        handleSuggestionKeyDown(
                          event,
                          desktopSuggestions,
                          desktopActiveIndex,
                          setDesktopActiveIndex,
                          (slug) => handleSuggestionSelect(slug, { closeDesktopSearch: true }),
                          () => setIsSearchOpen(false),
                        );
                      }}
                    />
                    <Button
                      type="submit"
                      variant="ghost"
                      size="icon"
                      aria-label="Submit product search"
                      loading={desktopSubmitting}
                      loadingText={null}
                    >
                      <Search className="h-4 w-4" />
                    </Button>
                  </form>
                  <div className="mt-2">
                    <SuggestionList
                      suggestions={desktopSuggestions}
                      loading={desktopLoading}
                      activeIndex={desktopActiveIndex}
                      onHighlight={setDesktopActiveIndex}
                      query={desktopSearchTerm}
                      onViewAll={() => submitSearch(desktopSearchTerm, { closeDesktopSearch: true })}
                      onSelect={(slug) => handleSuggestionSelect(slug, { closeDesktopSearch: true })}
                    />
                  </div>
                </div>
              ) : (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setIsSearchOpen(true)}
                  aria-label="Search"
                >
                  <Search className="h-5 w-5" />
                </Button>
              )}
            </div>

            {/* Wishlist */}
            <Link to="/wishlist">
              <Button variant="ghost" size="icon" className="relative" aria-label="Wishlist">
                <Heart className="h-5 w-5" />
                {wishlistCount > 0 && (
                  <span className="absolute -top-1 -right-1 h-5 w-5 rounded-full bg-primary text-primary-foreground text-xs flex items-center justify-center">
                    {wishlistCount}
                  </span>
                )}
              </Button>
            </Link>

            {/* Cart */}
            <Link to="/cart">
              <Button variant="ghost" size="icon" className="relative" aria-label="Cart">
                <ShoppingBag className="h-5 w-5" />
                {cartCount > 0 && (
                  <span className="absolute -top-1 -right-1 h-5 w-5 rounded-full bg-primary text-primary-foreground text-xs flex items-center justify-center">
                    {cartCount}
                  </span>
                )}
              </Button>
            </Link>

            {/* Account */}
            <Link to="/account">
              <Button variant="ghost" size="icon" aria-label="Account">
                <User className="h-5 w-5" />
              </Button>
            </Link>
          </div>
        </div>

        {/* Mobile Navigation */}
        {isMenuOpen && (
          <nav className="md:hidden py-4 border-t border-border animate-fade-in">
            <div className="flex flex-col gap-4">
              {navigation.map((item) => (
                <Link
                  key={item.name}
                  to={item.href}
                  onMouseEnter={item.href === "/products" ? prefetchProductsPage : undefined}
                  onFocus={item.href === "/products" ? prefetchProductsPage : undefined}
                  onTouchStart={item.href === "/products" ? prefetchProductsPage : undefined}
                  className={cn(
                    "text-base font-medium py-2 transition-colors",
                    location.pathname === item.href
                      ? "text-primary"
                      : "text-foreground/80"
                  )}
                  onClick={() => setIsMenuOpen(false)}
                >
                  {item.name}
                </Link>
              ))}
              {/* Mobile Search */}
              <div ref={mobileSearchRef} className="pt-4 border-t border-border">
                <form onSubmit={handleMobileSubmit} className="flex items-center gap-2">
                  <Input
                    type="search"
                    placeholder="Search products..."
                    className="w-full"
                    value={mobileSearchTerm}
                    onChange={(event) => {
                      setMobileSearchTerm(event.target.value);
                      setMobileActiveIndex(-1);
                    }}
                    onKeyDown={(event) =>
                      handleSuggestionKeyDown(
                        event,
                        mobileSuggestions,
                        mobileActiveIndex,
                        setMobileActiveIndex,
                        (slug) => handleSuggestionSelect(slug, { closeMobileMenu: true }),
                      )
                    }
                  />
                  <Button type="submit" variant="outline" size="icon" aria-label="Search products" loading={mobileSubmitting} loadingText={null}>
                    <Search className="h-4 w-4" />
                  </Button>
                </form>
                <div className="mt-3">
                  <SuggestionList
                    suggestions={mobileSuggestions}
                    loading={mobileLoading}
                    activeIndex={mobileActiveIndex}
                    onHighlight={setMobileActiveIndex}
                    query={mobileSearchTerm}
                    onViewAll={() => submitSearch(mobileSearchTerm, { closeMobileMenu: true })}
                    onSelect={(slug) => handleSuggestionSelect(slug, { closeMobileMenu: true })}
                  />
                </div>
              </div>
            </div>
          </nav>
        )}
      </div>
    </header>
  );
};
