import React, { createContext, useContext, useState, useCallback, useEffect } from "react";
import { Product } from "@/types/product";
import { toast } from "sonner";
import { useAuth } from '@/context/AuthContext';
import { fetchJSON } from "@/lib/api";

interface WishlistContextType {
  items: Product[];
  addToWishlist: (product: Product) => Promise<void>;
  removeFromWishlist: (productId: string) => Promise<void>;
  isInWishlist: (productId: string) => boolean;
  clearWishlist: () => Promise<void>;
}

const WishlistContext = createContext<WishlistContextType | undefined>(undefined);
const LOCAL_WISHLIST_KEY = "rukkie_wishlist_items";
const WISHLIST_PLACEHOLDER_IMAGE =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 160 160'%3E%3Crect width='160' height='160' fill='%23f1f1f1'/%3E%3Ctext x='50%25' y='50%25' fill='%23777' font-size='14' text-anchor='middle' dominant-baseline='middle'%3ENo Image%3C/text%3E%3C/svg%3E";

function normalizeImageUrl(value: any): string {
  const raw = typeof value === "string" ? value : (value?.image_url || value?.image || value?.url || "");
  const cleaned = String(raw || "").trim().replace(/\\/g, "/");
  if (!cleaned) return WISHLIST_PLACEHOLDER_IMAGE;
  if (/^https?:\/\//i.test(cleaned) || cleaned.startsWith("data:")) return cleaned;
  if (cleaned.startsWith("/")) return cleaned;
  if (cleaned.startsWith("media/")) return `/${cleaned}`;
  if (cleaned.startsWith("products/")) return `/media/${cleaned}`;
  return `/${cleaned}`;
}

function normalizeWishlistProduct(product: any): Product {
  const images = Array.isArray(product?.images) ? product.images.map((img: any) => normalizeImageUrl(img)).filter(Boolean) : [];
  return {
    ...product,
    id: String(product?.id ?? ""),
    price: Number(product?.price || 0),
    rating: Number(product?.rating || 0),
    reviewCount: Number(product?.review_count || product?.reviewCount || 0),
    isDigital: !!product?.is_digital || !!product?.isDigital,
    isFeatured: !!product?.is_featured || !!product?.isFeatured,
    isFlashSale: !!product?.is_flash_sale || !!product?.isFlashSale,
    images: images.length ? images : [WISHLIST_PLACEHOLDER_IMAGE],
    category:
      product?.category ||
      (Array.isArray(product?.categories) && product.categories.length > 0
        ? (product.categories[0]?.slug || product.categories[0]?.name || "uncategorized")
        : "uncategorized"),
  } as Product;
}

function readLocalWishlist(): Product[] {
  try {
    const raw = window.localStorage.getItem(LOCAL_WISHLIST_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.map((p) => normalizeWishlistProduct(p));
  } catch {
    return [];
  }
}

function writeLocalWishlist(items: Product[]) {
  try {
    window.localStorage.setItem(LOCAL_WISHLIST_KEY, JSON.stringify(items));
  } catch {
    // ignore storage failures
  }
}

export const WishlistProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [items, setItems] = useState<Product[]>([]);
  const auth = useAuth();

  useEffect(() => {
    let mounted = true;
    (async () => {
      if (auth.loading) return;
      if (auth.isAuthenticated) {
        try {
          const resp = await fetchJSON('/api/wishlist/');
          if (!mounted) return;
          const products = Array.isArray(resp?.products) ? resp.products : [];
          setItems(products.map((p: any) => normalizeWishlistProduct(p)));
        } catch (e) {
          if (mounted) setItems([]);
        }
      } else {
        setItems(readLocalWishlist());
      }
    })();
    return () => { mounted = false };
  }, [auth.loading, auth.isAuthenticated]);

  useEffect(() => {
    if (!auth.isAuthenticated) {
      writeLocalWishlist(items);
    }
  }, [items, auth.isAuthenticated]);

  const addToWishlist = useCallback(async (product: Product) => {
    if (!auth.isAuthenticated) {
      setItems((prevItems) => {
        if (prevItems.find((item) => item.id === product.id)) {
          toast.info(`${product.name} is already in your wishlist`);
          return prevItems;
        }
        toast.success(`Added ${product.name} to wishlist`);
        return [...prevItems, normalizeWishlistProduct(product)];
      });
      return;
    }
    try {
      const resp = await fetchJSON('/api/wishlist/add/', { method: 'POST', body: JSON.stringify({ product_id: product.id }) });
      const products = Array.isArray(resp?.products) ? resp.products : [];
      setItems(products.map((p: any) => normalizeWishlistProduct(p)));
      toast.success(`Added ${product.name} to wishlist`);
    } catch (e) {
      toast.error('Could not add to wishlist');
    }
  }, [auth.isAuthenticated]);

  const removeFromWishlist = useCallback(async (productId: string) => {
    if (!auth.isAuthenticated) {
      setItems((prevItems) => {
        const item = prevItems.find((i) => i.id === productId);
        if (item) {
          toast.info(`Removed ${item.name} from wishlist`);
        }
        return prevItems.filter((item) => item.id !== productId);
      });
      return;
    }
    try {
      const resp = await fetchJSON('/api/wishlist/remove/', { method: 'POST', body: JSON.stringify({ product_id: productId }) });
      const products = Array.isArray(resp?.products) ? resp.products : [];
      setItems(products.map((p: any) => normalizeWishlistProduct(p)));
      toast.info('Removed from wishlist');
    } catch (e) {
      toast.error('Could not remove from wishlist');
    }
  }, [auth.isAuthenticated]);

  const isInWishlist = useCallback((productId: string) => {
    return items.some((item) => item.id === productId);
  }, [items]);

  const clearWishlist = useCallback(async () => {
    if (!auth.isAuthenticated) {
      setItems([]);
      return;
    }
    try {
      await fetchJSON('/api/wishlist/clear/', { method: 'POST', body: JSON.stringify({}) });
      setItems([]);
      toast.info('Wishlist cleared');
    } catch (e) {
      toast.error('Could not clear wishlist');
    }
  }, [auth.isAuthenticated]);

  return (
    <WishlistContext.Provider
      value={{
        items,
        addToWishlist,
        removeFromWishlist,
        isInWishlist,
        clearWishlist,
      }}
    >
      {children}
    </WishlistContext.Provider>
  );
};

export const useWishlist = () => {
  const context = useContext(WishlistContext);
  if (!context) {
    throw new Error("useWishlist must be used within a WishlistProvider");
  }
  return context;
};
