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

const AppShell = () => {
  useEffect(() => {
    prefetchProductsPage();
    void fetchFeaturedProducts();
    void fetchHomeContent();
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
