import { useEffect, useMemo, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { Search, ShoppingBag, Heart, Menu, X, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useCart } from "@/context/CartContext";
import { useWishlist } from "@/context/WishlistContext";
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

const promoTextColors = [
  "text-amber-200",
  "text-emerald-200",
  "text-sky-200",
  "text-rose-200",
  "text-violet-200",
];

export const Header = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [promoIndex, setPromoIndex] = useState(0);
  const location = useLocation();
  const { getCartCount } = useCart();
  const { items: wishlistItems } = useWishlist();

  const cartCount = getCartCount();
  const wishlistCount = wishlistItems.length;
  const promoLoopText = useMemo(() => {
    const rotated = [...promoMessages.slice(promoIndex), ...promoMessages.slice(0, promoIndex)];
    return rotated.join(" | ");
  }, [promoIndex]);

  useEffect(() => {
    const timer = setInterval(() => {
      setPromoIndex((prev) => (prev + 1) % promoMessages.length);
    }, 5000);
    return () => clearInterval(timer);
  }, []);

  return (
    <header className="sticky top-0 z-50 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80 border-b border-border">
      {/* Top bar */}
      <div className="bg-primary py-2 text-sm overflow-hidden">
        <p className="sr-only">Free shipping on orders over $100 | Use code WELCOME15 for 15% off</p>
        <div className="promo-ticker-mask">
          <div className="promo-ticker-track">
            <p className={cn("promo-ticker-item", promoTextColors[promoIndex % promoTextColors.length])}>
              {promoLoopText}
            </p>
            <p
              aria-hidden="true"
              className={cn("promo-ticker-item", promoTextColors[promoIndex % promoTextColors.length])}
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
            <div className="relative hidden sm:block">
              {isSearchOpen ? (
                <div className="absolute right-0 top-1/2 -translate-y-1/2 animate-fade-in">
                  <Input
                    type="search"
                    placeholder="Search products..."
                    className="w-64 pr-10"
                    autoFocus
                    onBlur={() => setIsSearchOpen(false)}
                  />
                  <Search className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
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
            <Link to="/account" className="hidden md:flex">
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
              <div className="pt-4 border-t border-border">
                <Input
                  type="search"
                  placeholder="Search products..."
                  className="w-full"
                />
              </div>
            </div>
          </nav>
        )}
      </div>
    </header>
  );
};
