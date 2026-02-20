import React, { createContext, useContext, useState, useCallback, useEffect } from "react";
import { Product, CartItem } from "@/types/product";
import { toast } from "sonner";
import { fetchJSON } from "@/lib/api";

interface CartContextType {
  items: CartItem[];
  addToCart: (product: Product, quantity?: number) => Promise<void>;
  removeFromCart: (productId: string) => Promise<void>;
  updateQuantity: (productId: string, quantity: number) => Promise<void>;
  clearCart: () => Promise<void>;
  getCartTotal: () => number;
  getCartCount: () => number;
}

const CartContext = createContext<CartContextType | undefined>(undefined);

const CART_PLACEHOLDER_IMAGE =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 160 160'%3E%3Crect width='160' height='160' fill='%23f1f1f1'/%3E%3Ctext x='50%25' y='50%25' fill='%23777' font-size='14' text-anchor='middle' dominant-baseline='middle'%3ENo Image%3C/text%3E%3C/svg%3E";

function isPlaceholderCloudinaryUrl(value: string): boolean {
  const normalized = String(value || "").toLowerCase();
  return normalized.includes("<cloud_name>") || normalized.includes("%3ccloud_name%3e");
}

function normalizeImageUrl(value: any): string {
  const raw = typeof value === "string" ? value : (value?.image_url || value?.image || value?.url || "");
  const cleaned = String(raw || "").trim().replace(/\\/g, "/");
  if (!cleaned) return CART_PLACEHOLDER_IMAGE;
  if (isPlaceholderCloudinaryUrl(cleaned)) return CART_PLACEHOLDER_IMAGE;
  if (/^https?:\/\//i.test(cleaned) || cleaned.startsWith("data:")) return cleaned;
  if (cleaned.startsWith("res.cloudinary.com/")) return `https://${cleaned}`;
  if (cleaned.startsWith("/")) return cleaned;
  if (cleaned.startsWith("media/")) return `/${cleaned}`;
  if (cleaned.startsWith("products/")) return `/media/${cleaned}`;
  if (/^[^/]+\.(jpg|jpeg|png|webp|gif|bmp|svg|avif)$/i.test(cleaned)) return `/media/products/${cleaned}`;
  return CART_PLACEHOLDER_IMAGE;
}

function normalizeProductForCart(product: any): Product {
  const images = Array.isArray(product?.images) ? product.images : [];
  const mappedImages = images.map((img: any) => normalizeImageUrl(img)).filter(Boolean);

  return {
    ...product,
    id: String(product?.id ?? ""),
    slug: product?.slug || "",
    images: mappedImages.length ? mappedImages : [CART_PLACEHOLDER_IMAGE],
    category:
      product?.category ||
      (Array.isArray(product?.categories) && product.categories.length > 0
        ? (product.categories[0]?.name || product.categories[0]?.slug || "General")
        : "General"),
  } as Product;
}

function mapCartItems(data: any): CartItem[] {
  const rows = Array.isArray(data?.items) ? data.items : [];
  return rows.map((i: any) => ({
    product: normalizeProductForCart(i.product),
    quantity: Number(i.quantity || 0),
  }));
}

function findBackendCartItemByProductId(cart: any, productId: string) {
  const rows = Array.isArray(cart?.items) ? cart.items : [];
  return rows.find((i: any) => String(i?.product?.id ?? "") === String(productId));
}

export const CartProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [items, setItems] = useState<CartItem[]>([]);

  const refreshCart = useCallback(async () => {
    const data = await fetchJSON('/api/cart/');
    setItems(mapCartItems(data));
    return data;
  }, []);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const data = await fetchJSON('/api/cart/');
        if (!mounted) return;
        setItems(mapCartItems(data));
      } catch (e) {
        // keep client empty if backend not available
      }
    })();
    return () => { mounted = false; };
  }, []);

  const addToCart = useCallback(async (product: Product, quantity = 1) => {
    try {
      await fetchJSON('/api/cart/add/', { method: 'POST', body: JSON.stringify({ product_id: product.id, quantity }) });
      await refreshCart();
      toast.success(`Added ${product.name} to cart`);
    } catch (e:any) {
      toast.error(e.message || 'Could not add to cart');
    }
  }, [refreshCart]);

  const removeFromCart = useCallback(async (productId: string) => {
    try {
      const cart = await fetchJSON('/api/cart/');
      const item = findBackendCartItemByProductId(cart, productId);
      if (!item) {
        await refreshCart();
        return;
      }
      await fetchJSON('/api/cart/remove/', { method: 'POST', body: JSON.stringify({ item_id: item.id }) });
      await refreshCart();
      toast.info(`Removed ${item.product.name} from cart`);
    } catch (e:any) {
      toast.error(e.message || 'Could not remove from cart');
    }
  }, [refreshCart]);

  const updateQuantity = useCallback(async (productId: string, quantity: number) => {
    if (quantity < 1) {
      await removeFromCart(productId);
      return;
    }
    try {
      const cart = await fetchJSON('/api/cart/');
      const item = findBackendCartItemByProductId(cart, productId);
      if (!item) {
        await refreshCart();
        return;
      }
      await fetchJSON('/api/cart/update/', { method: 'POST', body: JSON.stringify({ item_id: item.id, quantity }) });
      await refreshCart();
    } catch (e:any) {
      toast.error(e.message || 'Could not update quantity');
    }
  }, [refreshCart, removeFromCart]);

  const clearCart = useCallback(async () => {
    try {
      await fetchJSON('/api/cart/clear/', { method: 'POST', body: JSON.stringify({}) });
      setItems([]);
      toast.info("Cart cleared");
    } catch (e:any) {
      toast.error(e.message || 'Could not clear cart');
    }
  }, []);

  const getCartTotal = useCallback(() => {
    return items.reduce((total, item) => total + item.product.price * item.quantity, 0);
  }, [items]);

  const getCartCount = useCallback(() => {
    return items.reduce((count, item) => count + item.quantity, 0);
  }, [items]);

  return (
    <CartContext.Provider
      value={{
        items,
        addToCart,
        removeFromCart,
        updateQuantity,
        clearCart,
        getCartTotal,
        getCartCount,
      }}
    >
      {children}
    </CartContext.Provider>
  );
};

export const useCart = () => {
  const context = useContext(CartContext);
  if (!context) {
    throw new Error("useCart must be used within a CartProvider");
  }
  return context;
};
