import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { Layout } from "@/components/layout/Layout";
import { ProductCard } from "@/components/products/ProductCard";
import { fetchProductsByCategory } from "@/data/products";
import { Button } from "@/components/ui/button";

const CategoryPage = () => {
  const { slug } = useParams<{ slug: string }>();
  const [products, setProducts] = useState<any[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);
    if (!slug) {
      setProducts([]);
      setLoading(false);
      return;
    }
    fetchProductsByCategory(slug).then((list) => {
      if (!mounted) return;
      setProducts(list || []);
    }).catch((e) => {
      setError('Failed to load products');
    }).finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, [slug]);

  return (
    <Layout>
      <div className="container mx-auto px-4 py-12">
        <nav className="breadcrumb mb-6">
          <Link to="/">Home</Link> / <span className="capitalize">{slug}</span>
        </nav>
        <h1 className="font-serif text-3xl mb-6">{slug?.replace('-', ' ')}</h1>

        {loading && <p>Loading...</p>}
        {error && <p className="text-destructive">{error}</p>}

        {!loading && products && products.length === 0 && (
          <div className="py-12 text-center">
            <p className="text-lg text-muted-foreground mb-4">No products available.</p>
            <Button asChild>
              <Link to="/products">Browse other products</Link>
            </Button>
          </div>
        )}

        {!loading && products && products.length > 0 && (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
            {products.map((p, i) => (
              <ProductCard key={p.id || i} product={p} />
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
};

export default CategoryPage;
