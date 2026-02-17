import { Link } from "react-router-dom";
import { Heart, ShoppingBag, Trash2, ChevronDown } from "lucide-react";
import { Layout } from "@/components/layout/Layout";
import { Button } from "@/components/ui/button";
import { useWishlist } from "@/context/WishlistContext";
import { useCart } from "@/context/CartContext";

const Wishlist = () => {
  const { items, removeFromWishlist, clearWishlist } = useWishlist();
  const { addToCart } = useCart();

  const handleAddToCart = (product: typeof items[0]) => {
    addToCart(product);
  };

  const handleRemove = (productId: string) => {
    removeFromWishlist(productId);
  };

  return (
    <Layout>
      <div className="bg-secondary/30 py-8">
        <div className="container mx-auto px-4">
          <nav className="breadcrumb mb-4">
            <Link to="/">Home</Link>
            <ChevronDown className="h-4 w-4 rotate-[-90deg]" />
            <span className="text-foreground">Wishlist</span>
          </nav>
          <h1 className="font-serif text-3xl md:text-4xl font-bold text-foreground">
            My Wishlist
          </h1>
        </div>
      </div>

      <div className="container mx-auto px-4 py-12">
        {items.length === 0 ? (
          <div className="text-center py-16">
            <Heart className="h-16 w-16 mx-auto text-muted-foreground/50 mb-6" />
            <h2 className="text-2xl font-serif font-semibold mb-4">
              Your wishlist is empty
            </h2>
            <p className="text-muted-foreground mb-8 max-w-md mx-auto">
              Save items you love by clicking the heart icon on any product.
            </p>
            <Link to="/products">
              <Button size="lg">Browse Products</Button>
            </Link>
          </div>
        ) : (
          <>
            <div className="flex justify-between items-center mb-8">
              <p className="text-muted-foreground">
                {items.length} item{items.length !== 1 ? "s" : ""} in your wishlist
              </p>
              <Button variant="outline" size="sm" onClick={clearWishlist}>
                Clear All
              </Button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              {items.map((product) => (
                <div
                  key={product.id}
                  className="group bg-card border border-border rounded-xl overflow-hidden transition-all hover:shadow-lg"
                >
                  <div className="relative aspect-square overflow-hidden">
                    <img
                      src={product.images[0]}
                      alt={product.name}
                      className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                    />
                    <button
                      onClick={() => handleRemove(product.id)}
                      className="absolute top-3 right-3 p-2 rounded-full bg-background/80 backdrop-blur-sm hover:bg-destructive hover:text-destructive-foreground transition-colors"
                      aria-label="Remove from wishlist"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>

                  <div className="p-4">
                    <Link to={`/product/${product.slug}`}>
                      <h3 className="font-medium text-foreground hover:text-primary transition-colors line-clamp-2 mb-2">
                        {product.name}
                      </h3>
                    </Link>
                    <p className="text-lg font-semibold text-primary mb-4">
                      ${product.price.toFixed(2)}
                    </p>
                    <Button
                      className="w-full"
                      onClick={() => handleAddToCart(product)}
                    >
                      <ShoppingBag className="h-4 w-4 mr-2" />
                      Add to Cart
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </Layout>
  );
};

export default Wishlist;
