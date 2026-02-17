export interface Product {
  id: string;
  name: string;
  slug: string;
  description: string;
  price: number;
  originalPrice?: number;
  images: string[];
  category: string;
  subcategory?: string;
  rating: number;
  reviewCount: number;
  inStock: boolean;
  isDigital: boolean;
  isFeatured?: boolean;
  isFlashSale?: boolean;
  flashSaleEndTime?: Date;
  features?: string[];
  benefits?: string[];
  tags?: string[];
  createdAt: Date;
}

export interface Category {
  id: string;
  name: string;
  slug: string;
  description: string;
  image: string;
  productCount: number;
}

export interface HeroSlide {
  id: string;
  badge: string;
  title: string;
  titleAccent: string;
  description: string;
  image: string;
  cta: {
    text: string;
    link: string;
  };
  secondaryCta: {
    text: string;
    link: string;
  };
  promo: string;
}

export interface CartItem {
  product: Product;
  quantity: number;
}

export interface Review {
  id: string;
  productId: string;
  userName: string;
  rating: number;
  comment: string;
  createdAt: Date;
  verified: boolean;
}
