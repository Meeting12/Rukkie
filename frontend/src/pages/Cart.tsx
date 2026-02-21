import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ChevronDown, Minus, Plus, Trash2, ShoppingBag, ArrowLeft } from "lucide-react";
import { Layout } from "@/components/layout/Layout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useCart } from "@/context/CartContext";
import { toast } from "sonner";
import { advanceImageFallback } from "@/lib/imageFallback";

const FALLBACK_IMAGE =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 160 160'%3E%3Crect width='160' height='160' fill='%23f1f1f1'/%3E%3Ctext x='50%25' y='50%25' fill='%23777' font-size='14' text-anchor='middle' dominant-baseline='middle'%3ENo Image%3C/text%3E%3C/svg%3E";

const Cart = () => {
  const navigate = useNavigate();
  const { items, updateQuantity, removeFromCart, getCartTotal, clearCart } = useCart();
  const [busyItems, setBusyItems] = useState<Set<string>>(new Set());
  const [isClearing, setIsClearing] = useState(false);

  const subtotal = getCartTotal();
  const shipping = subtotal > 100 ? 0 : 9.99;
  const tax = subtotal * 0.08;
  const total = subtotal + shipping + tax;

  const handleCheckout = () => {
    if (items.length === 0) {
      toast.error("Your cart is empty");
      return;
    }
    navigate("/checkout");
  };

  const runItemAction = async (productId: string, action: () => Promise<void>) => {
    if (busyItems.has(productId)) return;
    setBusyItems((prev) => new Set(prev).add(productId));
    try {
      await action();
    } finally {
      setBusyItems((prev) => {
        const next = new Set(prev);
        next.delete(productId);
        return next;
      });
    }
  };

  const handleClearCart = async () => {
    if (isClearing) return;
    setIsClearing(true);
    try {
      await clearCart();
    } finally {
      setIsClearing(false);
    }
  };

  if (items.length === 0) {
    return (
      <Layout>
        <div className="container mx-auto px-4 py-16 text-center">
          <div className="max-w-md mx-auto">
            <ShoppingBag className="h-16 w-16 mx-auto text-muted-foreground mb-6" />
            <h1 className="font-serif text-2xl font-bold mb-4">Your Cart is Empty</h1>
            <p className="text-muted-foreground mb-8">
              Looks like you haven't added anything to your cart yet. Start shopping and discover amazing products!
            </p>
            <Button variant="hero" asChild>
              <Link to="/products">
                Start Shopping
              </Link>
            </Button>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      {/* Breadcrumb */}
      <div className="bg-secondary/30 py-4">
        <div className="container mx-auto px-4">
          <nav className="breadcrumb">
            <Link to="/">Home</Link>
            <ChevronDown className="h-4 w-4 rotate-[-90deg]" />
            <span className="text-foreground">Shopping Cart</span>
          </nav>
        </div>
      </div>

      <div className="container mx-auto px-4 py-8 md:py-12">
        <div className="flex items-center justify-between mb-8">
          <h1 className="font-serif text-3xl font-bold text-foreground">
            Shopping Cart ({items.length} {items.length === 1 ? "item" : "items"})
          </h1>
          <Button variant="ghost" onClick={handleClearCart} className="text-muted-foreground" disabled={isClearing}>
            {isClearing ? "Clearing..." : "Clear Cart"}
          </Button>
        </div>

        <div className="grid lg:grid-cols-3 gap-8">
          {/* Cart Items */}
          <div className="lg:col-span-2 space-y-4">
            {items.map((item) => (
              <div
                key={item.product.id}
                className="flex gap-4 p-4 bg-card rounded-lg border border-border"
              >
                {/* Product Image */}
                <Link to={`/product/${item.product.slug}`} className="flex-shrink-0">
                  <img
                    src={item.product.images?.[0] || FALLBACK_IMAGE}
                    alt={item.product.name}
                    className="w-24 h-24 object-cover rounded-lg"
                    onError={(e) => {
                      advanceImageFallback(e.currentTarget, FALLBACK_IMAGE);
                    }}
                  />
                </Link>

                {/* Product Info */}
                <div className="flex-1 min-w-0">
                  <Link to={`/product/${item.product.slug}`}>
                    <h3 className="font-medium text-foreground hover:text-primary transition-colors line-clamp-2">
                      {item.product.name}
                    </h3>
                  </Link>
                  <p className="text-sm text-muted-foreground mt-1">
                    {item.product.category}
                  </p>
                  
                  <div className="flex items-center justify-between mt-4">
                    {/* Quantity */}
                    <div className="flex items-center border border-border rounded-md">
                      <button
                        onClick={() =>
                          runItemAction(item.product.id, () =>
                            updateQuantity(item.product.id, item.quantity - 1)
                          )
                        }
                        className="p-2 hover:bg-secondary transition-colors disabled:opacity-50"
                        disabled={busyItems.has(item.product.id)}
                      >
                        <Minus className="h-4 w-4" />
                      </button>
                      <span className="w-10 text-center text-sm">{item.quantity}</span>
                      <button
                        onClick={() =>
                          runItemAction(item.product.id, () =>
                            updateQuantity(item.product.id, item.quantity + 1)
                          )
                        }
                        className="p-2 hover:bg-secondary transition-colors disabled:opacity-50"
                        disabled={busyItems.has(item.product.id)}
                      >
                        <Plus className="h-4 w-4" />
                      </button>
                    </div>

                    {/* Price & Remove */}
                    <div className="flex items-center gap-4">
                      <span className="font-semibold text-foreground">
                        ${(item.product.price * item.quantity).toFixed(2)}
                      </span>
                      <button
                        onClick={() =>
                          runItemAction(item.product.id, () => removeFromCart(item.product.id))
                        }
                        className="p-2 text-muted-foreground hover:text-destructive transition-colors disabled:opacity-50"
                        aria-label="Remove item"
                        disabled={busyItems.has(item.product.id)}
                      >
                        <Trash2 className="h-5 w-5" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}

            {/* Continue Shopping */}
            <Button variant="ghost" asChild className="mt-4">
              <Link to="/products">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Continue Shopping
              </Link>
            </Button>
          </div>

          {/* Order Summary */}
          <div className="lg:col-span-1">
            <div className="bg-secondary/30 rounded-xl p-6 sticky top-24">
              <h2 className="font-serif text-xl font-semibold mb-6">Order Summary</h2>
              
              {/* Promo Code */}
              <div className="flex gap-2 mb-6">
                <Input placeholder="Enter promo code" className="flex-1" />
                <Button variant="outline">Apply</Button>
              </div>

              {/* Summary */}
              <div className="space-y-3 pb-4 border-b border-border">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Subtotal</span>
                  <span className="text-foreground">${subtotal.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Shipping</span>
                  <span className="text-foreground">
                    {shipping === 0 ? "FREE" : `$${shipping.toFixed(2)}`}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Tax</span>
                  <span className="text-foreground">${tax.toFixed(2)}</span>
                </div>
              </div>

              {/* Total */}
              <div className="flex justify-between py-4">
                <span className="font-semibold text-foreground">Total</span>
                <span className="text-xl font-bold text-foreground">${total.toFixed(2)}</span>
              </div>

              {/* Free Shipping Notice */}
              {shipping > 0 && (
                <p className="text-sm text-center text-muted-foreground mb-4">
                  Add ${(100 - subtotal).toFixed(2)} more for FREE shipping
                </p>
              )}

              {/* Checkout Button */}
              <Button variant="hero" className="w-full" onClick={handleCheckout}>
                Proceed to Checkout
              </Button>

              {/* Trust Badges */}
              <div className="flex justify-center gap-4 mt-6 text-sm text-muted-foreground">
                <span>🔒 Secure Checkout</span>
                <span>💳 Multiple Payment Options</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default Cart;
