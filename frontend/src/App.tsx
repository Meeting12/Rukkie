import { useEffect } from "react";
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { CartProvider } from "@/context/CartContext";
import { WishlistProvider } from "@/context/WishlistContext";
import { AuthProvider } from "@/context/AuthContext";
import ProtectedRoute from "@/components/ProtectedRoute";
import { ChatBot } from "@/components/chat/ChatBot";
import ScrollToTop from "@/components/ScrollToTop";
import { prefetchProductsPage, fetchFeaturedProducts, fetchHomeContent } from "@/data/products";
import { fetchJSON } from "@/lib/api";
import Index from "./pages/Index";
import Products from "./pages/Products";
import ProductDetail from "./pages/ProductDetail";
import CategoryPage from "./pages/Category";
import Cart from "./pages/Cart";
import Checkout from "./pages/Checkout";
import About from "./pages/About";
import Contact from "./pages/Contact";
import Wishlist from "./pages/Wishlist";
import FAQ from "./pages/FAQ";
import Account from "./pages/Account";
import OrderTracking from "./pages/OrderTracking";
import ShippingReturns from "./pages/ShippingReturns";
import PrivacyPolicy from "./pages/PrivacyPolicy";
import TermsOfService from "./pages/TermsOfService";
import OrderSuccess from "./pages/OrderSuccess";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();
const STOREFRONT_THEME_STORAGE_KEY = "rukkie_storefront_theme";

const applyStorefrontTheme = (theme?: string | null) => {
  const html = document.documentElement;
  const normalized = (theme || "").trim().toLowerCase();
  if (normalized === "luxury-beauty") {
    html.setAttribute("data-storefront-theme", "luxury-beauty");
    try {
      localStorage.setItem(STOREFRONT_THEME_STORAGE_KEY, "luxury-beauty");
    } catch {
      // Ignore storage errors.
    }
    return;
  }
  html.removeAttribute("data-storefront-theme");
  try {
    localStorage.setItem(STOREFRONT_THEME_STORAGE_KEY, "default");
  } catch {
    // Ignore storage errors.
  }
};

const AppShell = () => {
  useEffect(() => {
    prefetchProductsPage();
    void fetchFeaturedProducts();
    void fetchHomeContent();
  }, []);

  useEffect(() => {
    try {
      const cached = localStorage.getItem(STOREFRONT_THEME_STORAGE_KEY);
      if (cached) {
        applyStorefrontTheme(cached);
      }
    } catch {
      // Ignore storage errors.
    }

    let isMounted = true;
    void fetchJSON("/api/storefront/theme/")
      .then((payload: any) => {
        if (!isMounted) return;
        applyStorefrontTheme(payload?.theme);
      })
      .catch(() => {
        // Keep current UI stable; fail quietly.
      });

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <>
      <ScrollToTop />
      <Toaster />
      <Sonner />
      <Routes>
        <Route path="/" element={<Index />} />
        <Route path="/products" element={<Products />} />
        <Route path="/product/:slug" element={<ProductDetail />} />
        <Route path="/category/:slug" element={<CategoryPage />} />
        <Route path="/cart" element={<Cart />} />
        <Route path="/checkout" element={<ProtectedRoute><Checkout /></ProtectedRoute>} />
        <Route path="/order/success" element={<ProtectedRoute><OrderSuccess /></ProtectedRoute>} />
        <Route path="/order/success/" element={<ProtectedRoute><OrderSuccess /></ProtectedRoute>} />
        <Route path="/about" element={<About />} />
        <Route path="/contact" element={<Contact />} />
        <Route path="/wishlist" element={<ProtectedRoute><Wishlist /></ProtectedRoute>} />
        <Route path="/faq" element={<FAQ />} />
        <Route path="/account" element={<Account />} />
        <Route path="/order-tracking" element={<ProtectedRoute><OrderTracking /></ProtectedRoute>} />
        <Route path="/shipping-returns" element={<ShippingReturns />} />
        <Route path="/privacy-policy" element={<PrivacyPolicy />} />
        <Route path="/terms-of-service" element={<TermsOfService />} />
        {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
        <Route path="*" element={<NotFound />} />
      </Routes>
      <ChatBot />
    </>
  );
};

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <CartProvider>
        <BrowserRouter>
          <AuthProvider>
            <WishlistProvider>
              <AppShell />
            </WishlistProvider>
          </AuthProvider>
        </BrowserRouter>
      </CartProvider>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
