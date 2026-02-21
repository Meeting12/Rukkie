import { useState } from "react";
import { Link } from "react-router-dom";
import { Heart, ShoppingBag, Eye, Star } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Product } from "@/types/product";
import { useCart } from "@/context/CartContext";
import { useWishlist } from "@/context/WishlistContext";
import { prefetchProduct } from "@/data/products";
import { cn } from "@/lib/utils";
import { advanceImageFallback } from "@/lib/imageFallback";

interface ProductCardProps {
  product: Product;
}

export const ProductCard = ({ product }: ProductCardProps) => {
  const fallbackImage = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 400 400'%3E%3Crect width='400' height='400' fill='%23f1f1f1'/%3E%3Ctext x='50%25' y='50%25' fill='%23777' font-size='24' text-anchor='middle' dominant-baseline='middle'%3ENo Image%3C/text%3E%3C/svg%3E";
  const [isHovered, setIsHovered] = useState(false);
  const { addToCart } = useCart();
  const { addToWishlist, removeFromWishlist, isInWishlist } = useWishlist();

  const inWishlist = isInWishlist(product.id);
  const imageSrc = product.images?.[0] || fallbackImage;
  const discountPercent = product.originalPrice
    ? Math.round(((product.originalPrice - product.price) / product.originalPrice) * 100)
    : 0;

  const handleWishlistClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (inWishlist) {
      removeFromWishlist(product.id);
    } else {
      addToWishlist(product);
    }
  };

  const handleAddToCart = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    addToCart(product);
  };

  return (
    <div
      className="product-card group"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onFocusCapture={() => prefetchProduct(product.slug)}
      onMouseEnterCapture={() => prefetchProduct(product.slug)}
      onTouchStart={() => prefetchProduct(product.slug)}
    >
      <Link to={`/product/${product.slug}`} state={{ prefetchedProduct: product }}>
        {/* Image Container */}
        <div className="product-card-image relative aspect-square bg-secondary">
          <img
            src={imageSrc}
            alt={product.name}
            className="w-full h-full object-cover"
            loading="lazy"
            onError={(e) => {
              advanceImageFallback(e.currentTarget, fallbackImage);
            }}
          />

          {/* Badges */}
          <div className="absolute top-3 left-3 flex flex-col gap-2">
            {product.isFlashSale && (
              <span className="bg-destructive text-destructive-foreground px-3 py-1 text-xs font-semibold rounded-full">
                SALE
              </span>
            )}
            {product.isDigital && (
              <span className="bg-primary text-primary-foreground px-3 py-1 text-xs font-semibold rounded-full">
                DIGITAL
              </span>
            )}
            {discountPercent > 0 && !product.isFlashSale && (
              <span className="bg-foreground text-background px-3 py-1 text-xs font-semibold rounded-full">
                -{discountPercent}%
              </span>
            )}
          </div>

          {/* Wishlist Button */}
          <button
            onClick={handleWishlistClick}
            className="absolute top-3 right-3 p-2 bg-background/90 rounded-full shadow-md transition-all hover:scale-110"
            aria-label={inWishlist ? "Remove from wishlist" : "Add to wishlist"}
          >
            <Heart
              className={cn(
                "h-4 w-4 transition-colors",
                inWishlist ? "fill-destructive text-destructive" : "text-foreground"
              )}
            />
          </button>

          {/* Quick View Overlay */}
          <div
            className={cn(
              "quick-view-overlay",
              isHovered ? "opacity-100" : "opacity-0"
            )}
          >
            <div className="flex gap-2">
              <Button
                size="icon"
                variant="secondary"
                className="rounded-full"
                onClick={handleAddToCart}
                aria-label="Add to cart"
              >
                <ShoppingBag className="h-4 w-4" />
              </Button>
              <Button
                size="icon"
                variant="secondary"
                className="rounded-full"
                asChild
              >
                <Link to={`/product/${product.slug}`} state={{ prefetchedProduct: product }} aria-label="Quick view">
                  <Eye className="h-4 w-4" />
                </Link>
              </Button>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="p-4">
          {/* Category */}
          <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">
            {product.category}
          </p>

          {/* Title */}
          <h3 className="font-medium text-foreground line-clamp-2 mb-2 group-hover:text-primary transition-colors">
            {product.name}
          </h3>

          {/* Rating */}
          <div className="flex items-center gap-1 mb-2">
            <div className="flex">
              {[...Array(5)].map((_, i) => (
                <Star
                  key={i}
                  className={cn(
                    "h-3 w-3",
                    i < Math.floor(product.rating)
                      ? "fill-yellow-400 text-yellow-400"
                      : "text-muted-foreground/30"
                  )}
                />
              ))}
            </div>
            <span className="text-xs text-muted-foreground">
              ({product.reviewCount})
            </span>
          </div>

          {/* Price */}
          <div className="flex items-center gap-2">
            <span className="text-lg font-semibold text-foreground">
              ${product.price.toFixed(2)}
            </span>
            {product.originalPrice && (
              <span className="text-sm text-muted-foreground line-through">
                ${product.originalPrice.toFixed(2)}
              </span>
            )}
          </div>

          {/* Stock Status */}
          {!product.inStock && (
            <p className="text-sm text-destructive mt-2">Out of Stock</p>
          )}
        </div>
      </Link>
    </div>
  );
};
