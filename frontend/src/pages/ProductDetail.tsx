import { useState, useEffect, type FormEvent } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { 
  ChevronDown, 
  Minus, 
  Plus, 
  ShoppingBag, 
  Heart, 
  Share2, 
  Truck, 
  Shield, 
  RefreshCw,
  Star,
  Check,
  Download
} from "lucide-react";
import { Layout } from "@/components/layout/Layout";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ProductCard } from "@/components/products/ProductCard";
import { fetchJSON } from "@/lib/api";
import { fetchProductBySlug, fetchProducts } from "@/data/products";
import { useCart } from "@/context/CartContext";
import { useWishlist } from "@/context/WishlistContext";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";

const ProductDetail = () => {
  const fallbackImage = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 400 400'%3E%3Crect width='400' height='400' fill='%23f1f1f1'/%3E%3Ctext x='50%25' y='50%25' fill='%23777' font-size='24' text-anchor='middle' dominant-baseline='middle'%3ENo Image%3C/text%3E%3C/svg%3E";
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const [product, setProduct] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedImage, setSelectedImage] = useState(0);
  const [quantity, setQuantity] = useState(1);
  const [relatedProducts, setRelatedProducts] = useState<any[]>([]);
  const [reviews, setReviews] = useState<any[]>([]);
  const [reviewLoading, setReviewLoading] = useState(false);
  const [submittingReview, setSubmittingReview] = useState(false);
  const [reviewForm, setReviewForm] = useState({
    reviewer_name: "",
    reviewer_email: "",
    rating: 5,
    comment: "",
  });
  const displayImages = product?.images?.length ? product.images : [fallbackImage];

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        // use mapped fetch helper so frontend gets consistent Product shape
        const data = await fetchProductBySlug(slug || "");
        if (!mounted) return;
        setProduct(data);

        if (data && data.category) {
          try {
            const list = await fetchProducts();
            if (!mounted) return;
            const items = Array.isArray(list) ? list : [];
            setRelatedProducts(items.filter((p: any) => p.id !== data.id && p.category === data.category).slice(0, 4));
          } catch (e) {
            setRelatedProducts([]);
          }
        }
      } catch (e: any) {
        // If backend has no product (dev mode), attempt dynamic fallback to local sample data
        const msg = (e && e.message) || String(e || "");
        if (msg.includes("No Product matches") || msg.includes("not found") || msg.includes("Product not found")) {
          try {
            const mod = await import("@/data/products");
            const local = mod.getProductBySlug(slug || "");
            if (local) {
              setProduct(local);
              setRelatedProducts(mod.products.filter((p: any) => p.category === local.category && p.id !== local.id).slice(0,4));
              setError(null);
            } else {
              setError('Product not found');
              setProduct(null);
            }
          } catch {
            setError('Product not found');
            setProduct(null);
          }
        } else {
          setError(msg || 'Product not found');
          setProduct(null);
        }
      } finally {
        if (mounted) setLoading(false);
      }
    };
    load();
    return () => { mounted = false; };
  }, [slug]);

  useEffect(() => {
    let mounted = true;
    if (!slug) return;

    const loadReviews = async () => {
      setReviewLoading(true);
      try {
        const rows = await fetchJSON(`/api/products/slug/${encodeURIComponent(slug)}/reviews/`);
        if (!mounted) return;
        setReviews(Array.isArray(rows) ? rows : []);
      } catch {
        if (!mounted) return;
        setReviews([]);
      } finally {
        if (mounted) setReviewLoading(false);
      }
    };

    loadReviews();
    return () => { mounted = false; };
  }, [slug]);
  
  const { addToCart } = useCart();
  const { addToWishlist, removeFromWishlist, isInWishlist } = useWishlist();
  if (loading) {
    return (
      <Layout>
        <div className="container mx-auto px-4 py-16 text-center">Loading...</div>
      </Layout>
    );
  }

  if (!product || error) {
    return (
      <Layout>
        <div className="container mx-auto px-4 py-16 text-center">
          <h1 className="font-serif text-2xl font-bold mb-4">Product Not Found</h1>
          <p className="text-muted-foreground mb-6">{error || "The product you're looking for doesn't exist or has been removed."}</p>
          <Button onClick={() => navigate("/products")}>Browse Products</Button>
        </div>
      </Layout>
    );
  }

  const inWishlist = isInWishlist(product.id);
  const discountPercent = product.originalPrice
    ? Math.round(((product.originalPrice - product.price) / product.originalPrice) * 100)
    : 0;

  

  const handleAddToCart = () => {
    addToCart(product, quantity);
  };

  const handleBuyNow = () => {
    navigate("/checkout");
  };

  const handleWishlistToggle = () => {
    if (inWishlist) {
      removeFromWishlist(product.id);
    } else {
      addToWishlist(product);
    }
  };

  const handleShare = async () => {
    try {
      await navigator.share({
        title: product.name,
        text: product.description,
        url: window.location.href,
      });
    } catch {
      navigator.clipboard.writeText(window.location.href);
      toast.success("Link copied to clipboard!");
    }
  };

  const handleReviewSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!slug) return;
    if (!reviewForm.reviewer_name.trim()) {
      toast.error("Please enter your name");
      return;
    }
    if (!reviewForm.comment.trim()) {
      toast.error("Please enter your review");
      return;
    }

    setSubmittingReview(true);
    try {
      const payload = {
        reviewer_name: reviewForm.reviewer_name.trim(),
        reviewer_email: reviewForm.reviewer_email.trim(),
        rating: reviewForm.rating,
        comment: reviewForm.comment.trim(),
      };
      const created = await fetchJSON(`/api/products/slug/${encodeURIComponent(slug)}/reviews/`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setReviews((prev) => [created, ...prev]);
      setReviewForm({
        reviewer_name: "",
        reviewer_email: "",
        rating: 5,
        comment: "",
      });
      const refreshed = await fetchProductBySlug(slug);
      if (refreshed) setProduct(refreshed);
      toast.success("Review submitted successfully");
    } catch (err: any) {
      toast.error(err?.message || "Could not submit review");
    } finally {
      setSubmittingReview(false);
    }
  };

  return (
    <Layout>
      {/* Breadcrumb */}
      <div className="bg-secondary/30 py-4">
        <div className="container mx-auto px-4">
          <nav className="breadcrumb">
            <Link to="/">Home</Link>
            <ChevronDown className="h-4 w-4 rotate-[-90deg]" />
            <Link to="/products">Shop</Link>
            <ChevronDown className="h-4 w-4 rotate-[-90deg]" />
            <Link to={`/products?category=${product.category.toLowerCase()}`}>
              {product.category}
            </Link>
            <ChevronDown className="h-4 w-4 rotate-[-90deg]" />
            <span className="text-foreground">{product.name}</span>
          </nav>
        </div>
      </div>

      <div className="container mx-auto px-4 py-8 md:py-12">
        <div className="grid md:grid-cols-2 gap-8 lg:gap-12">
          {/* Product Images */}
          <div className="space-y-4">
            <div className="aspect-square bg-secondary rounded-xl overflow-hidden">
              <img
                src={displayImages[selectedImage] || displayImages[0]}
                alt={product.name}
                className="w-full h-full object-cover"
              />
            </div>
            
            {displayImages.length > 1 && (
              <div className="flex gap-4 overflow-x-auto pb-2">
                {displayImages.map((image, index) => (
                  <button
                    key={index}
                    onClick={() => setSelectedImage(index)}
                    className={cn(
                      "flex-shrink-0 w-20 h-20 rounded-lg overflow-hidden border-2 transition-colors",
                      selectedImage === index
                        ? "border-primary"
                        : "border-transparent hover:border-primary/50"
                    )}
                  >
                    <img
                      src={image}
                      alt={`${product.name} ${index + 1}`}
                      className="w-full h-full object-cover"
                    />
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Product Info */}
          <div className="space-y-6">
            {/* Category & Title */}
            <div>
              <p className="text-sm text-primary uppercase tracking-wider font-medium mb-2">
                {product.category}
              </p>
              <h1 className="font-serif text-3xl md:text-4xl font-bold text-foreground">
                {product.name}
              </h1>
            </div>

            {/* Rating */}
            <div className="flex items-center gap-3">
              <div className="flex">
                {[...Array(5)].map((_, i) => (
                  <Star
                    key={i}
                    className={cn(
                      "h-5 w-5",
                      i < Math.floor(product.rating)
                        ? "fill-yellow-400 text-yellow-400"
                        : "text-muted-foreground/30"
                    )}
                  />
                ))}
              </div>
              <span className="text-sm text-muted-foreground">
                {product.rating} ({product.reviewCount} reviews)
              </span>
            </div>

            {/* Price */}
            <div className="flex items-baseline gap-3">
              <span className="text-3xl font-bold text-foreground">
                ${product.price.toFixed(2)}
              </span>
              {product.originalPrice && (
                <>
                  <span className="text-xl text-muted-foreground line-through">
                    ${product.originalPrice.toFixed(2)}
                  </span>
                  <span className="text-sm font-medium text-destructive">
                    {discountPercent}% OFF
                  </span>
                </>
              )}
            </div>

            {/* Description */}
            <p className="text-muted-foreground leading-relaxed">
              {product.description}
            </p>

            {/* Digital/Physical Badge */}
            <div className="flex items-center gap-2 text-sm">
              {product.isDigital ? (
                <span className="flex items-center gap-2 text-primary">
                  <Download className="h-4 w-4" />
                  Instant Digital Download
                </span>
              ) : (
                <span className="flex items-center gap-2 text-muted-foreground">
                  <Truck className="h-4 w-4" />
                  Ships within 2-3 business days
                </span>
              )}
            </div>

            {/* Quantity & Add to Cart */}
            <div className="space-y-4 pt-4 border-t border-border">
              {/* Quantity */}
              <div className="flex items-center gap-4">
                <span className="text-sm font-medium">Quantity:</span>
                <div className="flex items-center border border-border rounded-md">
                  <button
                    onClick={() => setQuantity(Math.max(1, quantity - 1))}
                    className="p-2 hover:bg-secondary transition-colors"
                    disabled={quantity <= 1}
                  >
                    <Minus className="h-4 w-4" />
                  </button>
                  <span className="w-12 text-center font-medium">{quantity}</span>
                  <button
                    onClick={() => setQuantity(quantity + 1)}
                    className="p-2 hover:bg-secondary transition-colors"
                  >
                    <Plus className="h-4 w-4" />
                  </button>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row gap-3">
                <Button
                  variant="hero"
                  className="flex-1"
                  onClick={handleAddToCart}
                  disabled={!product.inStock}
                >
                  <ShoppingBag className="h-5 w-5 mr-2" />
                  Add to Cart
                </Button>
                <Button
                  variant="elegant"
                  className="flex-1"
                  onClick={handleBuyNow}
                  disabled={!product.inStock}
                >
                  Buy Now
                </Button>
              </div>

              {/* Secondary Actions */}
              <div className="flex gap-4">
                <button
                  onClick={handleWishlistToggle}
                  className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                  <Heart
                    className={cn(
                      "h-5 w-5",
                      inWishlist && "fill-destructive text-destructive"
                    )}
                  />
                  {inWishlist ? "In Wishlist" : "Add to Wishlist"}
                </button>
                <button
                  onClick={handleShare}
                  className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                  <Share2 className="h-5 w-5" />
                  Share
                </button>
              </div>
            </div>

            {/* Trust Badges */}
            <div className="grid grid-cols-3 gap-4 pt-6 border-t border-border">
              <div className="text-center">
                <Truck className="h-6 w-6 mx-auto text-primary mb-2" />
                <p className="text-xs text-muted-foreground">Free Shipping</p>
              </div>
              <div className="text-center">
                <Shield className="h-6 w-6 mx-auto text-primary mb-2" />
                <p className="text-xs text-muted-foreground">Secure Payment</p>
              </div>
              <div className="text-center">
                <RefreshCw className="h-6 w-6 mx-auto text-primary mb-2" />
                <p className="text-xs text-muted-foreground">Easy Returns</p>
              </div>
            </div>
          </div>
        </div>

        {/* Product Details Tabs */}
        <div className="mt-12 md:mt-16">
          <Tabs defaultValue="description" className="w-full">
            <TabsList className="w-full justify-start border-b border-border rounded-none h-auto p-0 bg-transparent">
              <TabsTrigger
                value="description"
                className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent px-6 py-3"
              >
                Description
              </TabsTrigger>
              <TabsTrigger
                value="features"
                className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent px-6 py-3"
              >
                Features
              </TabsTrigger>
              <TabsTrigger
                value="reviews"
                className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent px-6 py-3"
              >
                Reviews ({product.reviewCount})
              </TabsTrigger>
            </TabsList>

            <TabsContent value="description" className="pt-6">
              <div className="prose prose-gray max-w-none">
                <p className="text-muted-foreground leading-relaxed">
                  {product.description}
                </p>
                {product.benefits && (
                  <div className="mt-6">
                    <h4 className="font-serif text-lg font-semibold text-foreground mb-3">
                      Benefits
                    </h4>
                    <ul className="space-y-2">
                      {product.benefits.map((benefit, index) => (
                        <li key={index} className="flex items-start gap-2 text-muted-foreground">
                          <Check className="h-5 w-5 text-primary flex-shrink-0 mt-0.5" />
                          {benefit}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </TabsContent>

            <TabsContent value="features" className="pt-6">
              {product.features ? (
                <ul className="grid md:grid-cols-2 gap-4">
                  {product.features.map((feature, index) => (
                    <li key={index} className="flex items-center gap-3">
                      <div className="h-2 w-2 rounded-full bg-primary" />
                      <span className="text-muted-foreground">{feature}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-muted-foreground">No features listed.</p>
              )}
            </TabsContent>

            <TabsContent value="reviews" className="pt-6">
              <div className="space-y-8">
                <div className="space-y-4">
                  {reviewLoading && (
                    <p className="text-muted-foreground">Loading reviews...</p>
                  )}
                  {!reviewLoading && reviews.length === 0 && (
                    <p className="text-muted-foreground">
                      No reviews yet. Be the first to review this product.
                    </p>
                  )}
                  {reviews.map((review) => (
                    <div key={review.id} className="rounded-lg border border-border p-4">
                      <div className="flex items-center justify-between gap-3 mb-2">
                        <div>
                          <p className="font-medium text-foreground">{review.display_name || review.reviewer_name || "Anonymous"}</p>
                          <p className="text-xs text-muted-foreground">
                            {review.created_at ? new Date(review.created_at).toLocaleDateString() : ""}
                          </p>
                        </div>
                        <div className="flex">
                          {[...Array(5)].map((_, i) => (
                            <Star
                              key={i}
                              className={cn(
                                "h-4 w-4",
                                i < Number(review.rating || 0)
                                  ? "fill-yellow-400 text-yellow-400"
                                  : "text-muted-foreground/30"
                              )}
                            />
                          ))}
                        </div>
                      </div>
                      <p className="text-sm text-muted-foreground">{review.comment}</p>
                    </div>
                  ))}
                </div>

                <form onSubmit={handleReviewSubmit} className="rounded-lg border border-border p-4 space-y-4">
                  <h4 className="font-serif text-lg font-semibold text-foreground">Write a Review</h4>
                  <div className="grid sm:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="review_name">Name</Label>
                      <Input
                        id="review_name"
                        value={reviewForm.reviewer_name}
                        onChange={(e) => setReviewForm((prev) => ({ ...prev, reviewer_name: e.target.value }))}
                        placeholder="Your name"
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="review_email">Email (optional)</Label>
                      <Input
                        id="review_email"
                        type="email"
                        value={reviewForm.reviewer_email}
                        onChange={(e) => setReviewForm((prev) => ({ ...prev, reviewer_email: e.target.value }))}
                        placeholder="you@example.com"
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label>Rating</Label>
                    <div className="flex items-center gap-2">
                      {[1, 2, 3, 4, 5].map((rate) => (
                        <button
                          key={rate}
                          type="button"
                          onClick={() => setReviewForm((prev) => ({ ...prev, rating: rate }))}
                          className="p-1"
                          aria-label={`Set rating ${rate}`}
                        >
                          <Star
                            className={cn(
                              "h-5 w-5",
                              rate <= reviewForm.rating
                                ? "fill-yellow-400 text-yellow-400"
                                : "text-muted-foreground/30"
                            )}
                          />
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="review_comment">Review</Label>
                    <Textarea
                      id="review_comment"
                      value={reviewForm.comment}
                      onChange={(e) => setReviewForm((prev) => ({ ...prev, comment: e.target.value }))}
                      placeholder="Share your experience with this product"
                      rows={4}
                      required
                    />
                  </div>

                  <Button variant="outline" type="submit" disabled={submittingReview}>
                    {submittingReview ? "Submitting..." : "Write a Review"}
                  </Button>
                </form>
              </div>
            </TabsContent>
          </Tabs>
        </div>

        {/* Related Products */}
        {relatedProducts.length > 0 && (
          <div className="mt-16">
            <h2 className="font-serif text-2xl md:text-3xl font-bold text-foreground mb-8">
              You May Also Like
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-6">
              {relatedProducts.map((relatedProduct) => (
                <ProductCard key={relatedProduct.id} product={relatedProduct} />
              ))}
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
};

export default ProductDetail;
