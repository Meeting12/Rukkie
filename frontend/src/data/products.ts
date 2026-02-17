import { Product, Category, HeroSlide } from "@/types/product";

const PLACEHOLDER_IMAGE = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 400 400'%3E%3Crect width='400' height='400' fill='%23f1f1f1'/%3E%3Ctext x='50%25' y='50%25' fill='%23777' font-size='24' text-anchor='middle' dominant-baseline='middle'%3ENo Image%3C/text%3E%3C/svg%3E";

function normalizeImageUrl(value: any): string {
  const raw = typeof value === "string" ? value : (value?.image_url || value?.image || value?.url || "");
  const cleaned = String(raw || "").trim().replace(/\\/g, "/");
  if (!cleaned) return PLACEHOLDER_IMAGE;
  if (/^https?:\/\//i.test(cleaned) || cleaned.startsWith("data:")) return cleaned;
  if (cleaned.startsWith("/")) return cleaned;
  if (cleaned.startsWith("media/")) return `/${cleaned}`;
  if (cleaned.startsWith("products/")) return `/media/${cleaned}`;
  return `/${cleaned}`;
}

function normalizeCategoryKey(value: any): string {
  return String(value || "")
    .toLowerCase()
    .replace(/[^a-z0-9]/g, "");
}

function mapImageArray(images: any): string[] {
  if (!Array.isArray(images) || images.length === 0) return [PLACEHOLDER_IMAGE];
  const mapped = images.map((i: any) => normalizeImageUrl(i)).filter(Boolean);
  return mapped.length ? mapped : [PLACEHOLDER_IMAGE];
}

function mapCategoryItem(c: any): Category {
  return {
    id: String(c.id),
    name: c.name,
    slug: c.slug,
    description: c.description || '',
    image: normalizeImageUrl(c.image_url || c.image),
    productCount: c.product_count || c.productCount || 0,
  } as Category;
}

export const categories: Category[] = [
  {
    id: "1",
    name: "Electronics",
    slug: "electronics",
    description: "Latest gadgets and tech essentials",
    image: "https://images.unsplash.com/photo-1498049794561-7780e7231661?w=600&h=400&fit=crop",
    productCount: 45,
  },
  {
    id: "2",
    name: "Fashion",
    slug: "fashion",
    description: "Trendy clothing and accessories",
    image: "https://images.unsplash.com/photo-1445205170230-053b83016050?w=600&h=400&fit=crop",
    productCount: 120,
  },
  {
    id: "3",
    name: "Beauty",
    slug: "beauty",
    description: "Premium skincare and cosmetics",
    image: "https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=600&h=400&fit=crop",
    productCount: 85,
  },
  {
    id: "4",
    name: "Home & Kitchen",
    slug: "home-kitchen",
    description: "Stylish home decor and essentials",
    image: "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=600&h=400&fit=crop",
    productCount: 95,
  },
];

export const heroSlidesFallback: HeroSlide[] = [
  {
    id: "1",
    badge: "New Collection 2024",
    title: "Elevate Your",
    titleAccent: "Lifestyle",
    description:
      "Discover curated collections of premium electronics, fashion, beauty, and home essentials. Where quality meets timeless elegance.",
    image: "https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=800&h=900&fit=crop",
    cta: { text: "Explore Collection", link: "/products" },
    secondaryCta: { text: "Our Story", link: "/about" },
    promo: "Up to 40% Off",
  },
  {
    id: "2",
    badge: "Coming Soon",
    title: "Summer",
    titleAccent: "Essentials",
    description:
      "Get ready for our exclusive summer collection. Premium fashion pieces designed for the modern lifestyle. Pre-order now and be the first to experience elegance.",
    image: "https://images.unsplash.com/photo-1483985988355-763728e1935b?w=800&h=900&fit=crop",
    cta: { text: "Pre-Order Now", link: "/products" },
    secondaryCta: { text: "Learn More", link: "/about" },
    promo: "Early Bird 25% Off",
  },
  {
    id: "3",
    badge: "Limited Time",
    title: "Flash",
    titleAccent: "Sale",
    description:
      "Don't miss our biggest sale of the season! Exclusive discounts on premium products. Limited stock available - shop now before it's gone.",
    image: "https://images.unsplash.com/photo-1607082348824-0a96f2a4b9da?w=800&h=900&fit=crop",
    cta: { text: "Shop Sale", link: "/products" },
    secondaryCta: { text: "View All Deals", link: "/products" },
    promo: "Up to 60% Off",
  },
  {
    id: "4",
    badge: "Exclusive Preview",
    title: "Tech",
    titleAccent: "Innovation",
    description:
      "Experience the future of technology. Premium gadgets and electronics arriving soon. Sign up for early access and exclusive member pricing.",
    image: "https://images.unsplash.com/photo-1468495244123-6c6c332eeece?w=800&h=900&fit=crop",
    cta: { text: "Get Early Access", link: "/products" },
    secondaryCta: { text: "Explore Tech", link: "/products" },
    promo: "Members Save 30%",
  },
];

export const products: Product[] = [
  {
    id: "1",
    name: "Premium Wireless Earbuds Pro",
    slug: "premium-wireless-earbuds-pro",
    description: "Experience crystal-clear audio with our flagship wireless earbuds featuring active noise cancellation, 30-hour battery life, and seamless connectivity.",
    price: 129.99,
    originalPrice: 179.99,
    images: [
      "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=600&h=600&fit=crop",
      "https://images.unsplash.com/photo-1598331668826-20cecc596b86?w=600&h=600&fit=crop",
    ],
    category: "Electronics",
    rating: 4.8,
    reviewCount: 234,
    inStock: true,
    isDigital: false,
    isFeatured: true,
    isFlashSale: true,
    features: ["Active Noise Cancellation", "30-Hour Battery", "Wireless Charging", "IPX5 Water Resistant"],
    benefits: ["Immersive sound experience", "All-day comfort", "Seamless device switching"],
    tags: ["bestseller", "new"],
    createdAt: new Date("2024-01-15"),
  },
  {
    id: "2",
    name: "Designer Silk Scarf Collection",
    slug: "designer-silk-scarf-collection",
    description: "Luxurious 100% pure silk scarf with hand-printed geometric patterns. Perfect for elevating any outfit.",
    price: 89.99,
    images: [
      "https://images.unsplash.com/photo-1601924994987-69e26d50dc26?w=600&h=600&fit=crop",
    ],
    category: "Fashion",
    rating: 4.9,
    reviewCount: 156,
    inStock: true,
    isDigital: false,
    isFeatured: true,
    features: ["100% Pure Silk", "Hand-Printed Design", "Multiple Colors Available"],
    tags: ["luxury", "gift"],
    createdAt: new Date("2024-02-01"),
  },
  {
    id: "3",
    name: "Advanced Skincare Serum Bundle",
    slug: "advanced-skincare-serum-bundle",
    description: "Complete anti-aging skincare set with Vitamin C serum, Retinol night cream, and Hyaluronic acid moisturizer.",
    price: 149.99,
    originalPrice: 199.99,
    images: [
      "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?w=600&h=600&fit=crop",
    ],
    category: "Beauty",
    rating: 4.7,
    reviewCount: 312,
    inStock: true,
    isDigital: false,
    isFeatured: true,
    isFlashSale: true,
    features: ["Vitamin C Serum", "Retinol Night Cream", "Hyaluronic Acid", "Cruelty-Free"],
    benefits: ["Reduces fine lines", "Brightens skin tone", "Deep hydration"],
    tags: ["bestseller", "bundle"],
    createdAt: new Date("2024-01-20"),
  },
  {
    id: "4",
    name: "Minimalist Ceramic Vase Set",
    slug: "minimalist-ceramic-vase-set",
    description: "Set of 3 handcrafted ceramic vases in matte finish. Perfect for modern home decor.",
    price: 79.99,
    images: [
      "https://images.unsplash.com/photo-1578500494198-246f612d3b3d?w=600&h=600&fit=crop",
    ],
    category: "Home & Kitchen",
    rating: 4.6,
    reviewCount: 89,
    inStock: true,
    isDigital: false,
    isFeatured: true,
    features: ["Handcrafted", "Matte Finish", "Set of 3", "Various Sizes"],
    tags: ["decor", "gift"],
    createdAt: new Date("2024-02-10"),
  },
  {
    id: "5",
    name: "Smart Watch Ultra",
    slug: "smart-watch-ultra",
    description: "Premium smartwatch with health monitoring, GPS, and 7-day battery life. Water resistant to 100m.",
    price: 299.99,
    originalPrice: 349.99,
    images: [
      "https://images.unsplash.com/photo-1546868871-7041f2a55e12?w=600&h=600&fit=crop",
    ],
    category: "Electronics",
    rating: 4.8,
    reviewCount: 567,
    inStock: true,
    isDigital: false,
    features: ["Health Monitoring", "GPS", "7-Day Battery", "100m Water Resistant"],
    tags: ["bestseller", "tech"],
    createdAt: new Date("2024-01-25"),
  },
  {
    id: "6",
    name: "Premium Leather Handbag",
    slug: "premium-leather-handbag",
    description: "Elegant Italian leather handbag with gold-tone hardware. Spacious interior with multiple compartments.",
    price: 249.99,
    images: [
      "https://images.unsplash.com/photo-1584917865442-de89df76afd3?w=600&h=600&fit=crop",
    ],
    category: "Fashion",
    rating: 4.9,
    reviewCount: 203,
    inStock: true,
    isDigital: false,
    features: ["Italian Leather", "Gold Hardware", "Multiple Compartments", "Dust Bag Included"],
    tags: ["luxury", "bestseller"],
    createdAt: new Date("2024-02-05"),
  },
  {
    id: "7",
    name: "Digital Marketing Masterclass",
    slug: "digital-marketing-masterclass",
    description: "Comprehensive online course covering SEO, social media marketing, and paid advertising. Lifetime access.",
    price: 49.99,
    originalPrice: 199.99,
    images: [
      "https://images.unsplash.com/photo-1432888498266-38ffec3eaf0a?w=600&h=600&fit=crop",
    ],
    category: "Electronics",
    subcategory: "Digital Products",
    rating: 4.7,
    reviewCount: 1245,
    inStock: true,
    isDigital: true,
    isFeatured: true,
    features: ["50+ Video Lessons", "Downloadable Resources", "Certificate of Completion", "Lifetime Access"],
    benefits: ["Learn at your own pace", "Real-world projects", "Expert instruction"],
    tags: ["course", "digital"],
    createdAt: new Date("2024-01-10"),
  },
  {
    id: "8",
    name: "Luxury Scented Candle Set",
    slug: "luxury-scented-candle-set",
    description: "Set of 4 premium soy wax candles with essential oils. 40-hour burn time each.",
    price: 59.99,
    images: [
      "https://images.unsplash.com/photo-1602607753891-9b1ed1e5a1c4?w=600&h=600&fit=crop",
    ],
    category: "Home & Kitchen",
    rating: 4.8,
    reviewCount: 178,
    inStock: true,
    isDigital: false,
    isFlashSale: true,
    features: ["Soy Wax", "Essential Oils", "40-Hour Burn Time", "Reusable Glass Jars"],
    tags: ["gift", "home"],
    createdAt: new Date("2024-02-15"),
  },
];

export const getProductsByCategory = (category: string): Product[] => {
  const key = normalizeCategoryKey(category);
  return products.filter((p) => normalizeCategoryKey(p.category) === key);
};

export const getFeaturedProducts = (): Product[] => {
  return products.filter(p => p.isFeatured);
};

export const getFlashSaleProducts = (): Product[] => {
  return products.filter(p => p.isFlashSale);
};

export const getProductBySlug = (slug: string): Product | undefined => {
  return products.find(p => p.slug === slug);
};

// API wrappers: attempt to fetch from backend; fall back to local data
export async function fetchProducts(): Promise<Product[]> {
  try {
    const res = await fetch('/api/products/');
    if (!res.ok) throw new Error('network');
    const data = await res.json();
    // DRF may return a paginated response { results: [...] } or a plain list.
    const items = Array.isArray(data) ? data : data.results || [];
    // Map backend product shape to frontend Product type expected by components
    const mapped = items.map((p: any) => ({
      id: String(p.id),
      name: p.name,
      slug: p.slug,
      description: p.description || "",
      price: Number(p.price),
      originalPrice: p.original_price ? Number(p.original_price) : (p.originalPrice ? Number(p.originalPrice) : undefined),
      images: mapImageArray(p.images),
      // Use category slug when available to keep filtering/URLs consistent
      category: (p.categories && p.categories.length>0) ? (p.categories[0].slug || p.categories[0].name) : (p.category || "uncategorized"),
      rating: p.rating || 0,
      reviewCount: p.review_count || p.reviewCount || 0,
      inStock: p.stock ? p.stock > 0 : (p.inStock !== undefined ? p.inStock : true),
      isDigital: !!p.is_digital || !!p.isDigital,
      isFeatured: !!p.is_featured || !!p.isFeatured,
      isFlashSale: !!p.is_flash_sale || !!p.isFlashSale,
      features: p.features || [],
      benefits: p.benefits || [],
      tags: p.tags || [],
      createdAt: p.created_at ? new Date(p.created_at) : (p.createdAt ? new Date(p.createdAt) : new Date()),
    } as Product));
    return mapped;
  } catch (e) {
    return products;
  }
}

export async function fetchCategories(): Promise<Category[]> {
  try {
    const res = await fetch('/api/categories/');
    if (!res.ok) throw new Error('network');
    const data = await res.json();
    const items = Array.isArray(data) ? data : data.results || [];
    return items.map((c: any) => mapCategoryItem(c));
  } catch (e) {
    return categories;
  }
}

export async function fetchHomeContent(): Promise<{ heroSlides: HeroSlide[]; categories: Category[] }> {
  try {
    const res = await fetch('/api/home/content/');
    if (!res.ok) throw new Error('network');
    const data = await res.json();
    const heroSlides = (Array.isArray(data?.hero_slides) ? data.hero_slides : [])
      .map((row: any) => ({
        id: String(row.id),
        badge: row.badge || '',
        title: row.title || '',
        titleAccent: row.title_accent || '',
        description: row.description || '',
        image: normalizeImageUrl(row.image_url || row.image),
        cta: {
          text: row.cta_text || 'Shop Now',
          link: row.cta_link || '/products',
        },
        secondaryCta: {
          text: row.secondary_cta_text || 'Learn More',
          link: row.secondary_cta_link || '/about',
        },
        promo: row.promo || '',
      } as HeroSlide))
      .filter((slide: HeroSlide) => slide.title);

    const homeCategories = (Array.isArray(data?.categories) ? data.categories : []).map((c: any) => mapCategoryItem(c));

    return {
      heroSlides: heroSlides.length ? heroSlides : heroSlidesFallback,
      categories: homeCategories.length ? homeCategories : categories,
    };
  } catch (e) {
    return { heroSlides: heroSlidesFallback, categories };
  }
}

export async function fetchFeaturedProducts(): Promise<Product[]> {
  try {
    const res = await fetch('/api/products/?featured=true');
    if (!res.ok) throw new Error('network');
    const data = await res.json();
    const items = Array.isArray(data) ? data : data.results || [];
    // reuse mapping by temporarily setting response
    return items.map((p: any) => ({
      id: String(p.id),
      name: p.name,
      slug: p.slug,
      description: p.description || '',
      price: Number(p.price),
      originalPrice: p.original_price ? Number(p.original_price) : undefined,
      images: mapImageArray(p.images),
      category: (p.categories && p.categories.length>0) ? (p.categories[0].slug || p.categories[0].name) : (p.category || 'uncategorized'),
      rating: p.rating || 0,
      reviewCount: p.review_count || p.reviewCount || 0,
      inStock: p.stock ? p.stock > 0 : true,
      isDigital: !!p.is_digital || !!p.isDigital,
      isFeatured: !!p.is_featured || !!p.isFeatured,
      isFlashSale: !!p.is_flash_sale || !!p.isFlashSale,
      features: p.features || [],
      benefits: p.benefits || [],
      tags: p.tags || [],
      createdAt: p.created_at ? new Date(p.created_at) : new Date(),
    } as Product));
  } catch (e) {
    return getFeaturedProducts();
  }
}

export async function fetchProductBySlug(slug: string): Promise<Product | undefined> {
  try {
    const res = await fetch(`/api/products/slug/${encodeURIComponent(slug)}/`);
    if (!res.ok) throw new Error('network');
    const p = await res.json();
    // map single product to frontend shape
    const mapped: Product = {
      id: String(p.id),
      name: p.name,
      slug: p.slug,
      description: p.description || "",
      price: Number(p.price),
      originalPrice: p.original_price ? Number(p.original_price) : (p.originalPrice ? Number(p.originalPrice) : undefined),
      images: mapImageArray(p.images),
      category: (p.categories && p.categories.length>0) ? (p.categories[0].slug || p.categories[0].name) : (p.category || 'uncategorized'),
      rating: p.rating || 0,
      reviewCount: p.review_count || p.reviewCount || 0,
      inStock: p.stock ? p.stock > 0 : (p.inStock !== undefined ? p.inStock : true),
      isDigital: !!p.is_digital || !!p.isDigital,
      isFeatured: !!p.is_featured || !!p.isFeatured,
      isFlashSale: !!p.is_flash_sale || !!p.isFlashSale,
      features: p.features || [],
      benefits: p.benefits || [],
      tags: p.tags || [],
      createdAt: p.created_at ? new Date(p.created_at) : (p.createdAt ? new Date(p.createdAt) : new Date()),
    };
    return mapped;
  } catch (e) {
    return getProductBySlug(slug);
  }
}

export async function fetchProductsByCategory(slug: string): Promise<Product[]> {
  try {
    const res = await fetch(`/api/products/?category=${encodeURIComponent(slug)}`);
    if (!res.ok) throw new Error('network');
    const data = await res.json();
    const items = Array.isArray(data) ? data : data.results || [];
    return items.map((p: any) => ({
      id: String(p.id),
      name: p.name,
      slug: p.slug,
      description: p.description || '',
      price: Number(p.price),
      originalPrice: p.original_price ? Number(p.original_price) : undefined,
      images: mapImageArray(p.images),
      category: (p.categories && p.categories.length>0) ? (p.categories[0].slug || p.categories[0].name) : (p.category || 'uncategorized'),
      rating: p.rating || 0,
      reviewCount: p.review_count || p.reviewCount || 0,
      inStock: p.stock ? p.stock > 0 : true,
      isDigital: !!p.is_digital || !!p.isDigital,
      isFeatured: !!p.is_featured || !!p.isFeatured,
      isFlashSale: !!p.is_flash_sale || !!p.isFlashSale,
      features: p.features || [],
      benefits: p.benefits || [],
      tags: p.tags || [],
      createdAt: p.created_at ? new Date(p.created_at) : new Date(),
    } as Product));
  } catch (e) {
    const key = normalizeCategoryKey(slug);
    return products.filter((p) => normalizeCategoryKey(p.category) === key);
  }
}
