import { useState, useMemo, useEffect } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { Filter, Grid, List, ChevronDown, X } from "lucide-react";
import { Layout } from "@/components/layout/Layout";
import { ProductCard } from "@/components/products/ProductCard";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { fetchProducts, fetchCategories, fetchProductsByCategory } from "@/data/products";
import { Category } from "@/types/product";
import { cn } from "@/lib/utils";

const sortOptions = [
  { value: "newest", label: "Newest" },
  { value: "price-low", label: "Price: Low to High" },
  { value: "price-high", label: "Price: High to Low" },
  { value: "popular", label: "Most Popular" },
];

const priceRanges = [
  { value: "0-50", label: "Under $50" },
  { value: "50-100", label: "$50 - $100" },
  { value: "100-200", label: "$100 - $200" },
  { value: "200+", label: "$200+" },
];

const Products = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [isGridView, setIsGridView] = useState(true);
  
  const selectedCategory = searchParams.get("category");
  const selectedSort = searchParams.get("sort") || "newest";
  const selectedPriceRange = searchParams.get("price");
  const showSaleOnly = searchParams.get("sale") === "true";

  const [products, setProducts] = useState([] as any[]);
  const [allCategories, setAllCategories] = useState<Category[]>([]);

  useEffect(() => {
    let mounted = true;
    fetchCategories().then((c) => { if (mounted) setAllCategories(c); }).catch(() => {});
    return () => { mounted = false; };
  }, []);

  useEffect(() => {
    let mounted = true;
    const loadProducts = async () => {
      try {
        const list = selectedCategory
          ? await fetchProductsByCategory(selectedCategory)
          : await fetchProducts();
        if (mounted) setProducts(Array.isArray(list) ? list : []);
      } catch {
        if (mounted) setProducts([]);
      }
    };
    loadProducts();
    return () => { mounted = false; };
  }, [selectedCategory]);

  const filteredProducts = useMemo(() => {
    let result = [...products];

    // Filter by sale
    if (showSaleOnly) {
      result = result.filter((p) => p.isFlashSale || p.originalPrice);
    }

    // Filter by price range
    if (selectedPriceRange) {
      const [min, max] = selectedPriceRange.split("-").map(Number);
      if (max) {
        result = result.filter((p) => p.price >= min && p.price <= max);
      } else {
        result = result.filter((p) => p.price >= min);
      }
    }

    // Sort
    switch (selectedSort) {
      case "price-low":
        result.sort((a, b) => a.price - b.price);
        break;
      case "price-high":
        result.sort((a, b) => b.price - a.price);
        break;
      case "popular":
        result.sort((a, b) => b.reviewCount - a.reviewCount);
        break;
      case "newest":
      default:
        result.sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime());
    }

    return result;
  }, [products, selectedSort, selectedPriceRange, showSaleOnly]);

  const handleCategoryChange = (slug: string) => {
    const newParams = new URLSearchParams(searchParams);
    if (selectedCategory === slug) {
      newParams.delete("category");
    } else {
      newParams.set("category", slug);
    }
    setSearchParams(newParams);
  };

  const handleSortChange = (value: string) => {
    const newParams = new URLSearchParams(searchParams);
    newParams.set("sort", value);
    setSearchParams(newParams);
  };

  const handlePriceChange = (value: string) => {
    const newParams = new URLSearchParams(searchParams);
    if (selectedPriceRange === value) {
      newParams.delete("price");
    } else {
      newParams.set("price", value);
    }
    setSearchParams(newParams);
  };

  const clearFilters = () => {
    setSearchParams({});
  };

  const hasActiveFilters = selectedCategory || selectedPriceRange || showSaleOnly;

  const FilterSidebar = ({ categoriesProp }: { categoriesProp?: Category[] }) => (
    <div className="space-y-8">
      {/* Categories */}
      <div>
        <h3 className="font-serif text-lg font-semibold mb-4">Categories</h3>
        <div className="space-y-3">
          {(categoriesProp || []).map((category) => (
            <label
              key={category.id}
              className="flex items-center gap-3 cursor-pointer group"
            >
              <Checkbox
                checked={selectedCategory === category.slug}
                onCheckedChange={() => handleCategoryChange(category.slug)}
              />
              <span className="text-sm text-foreground/80 group-hover:text-foreground transition-colors">
                {category.name}
              </span>
              <span className="text-xs text-muted-foreground ml-auto">
                ({category.productCount})
              </span>
            </label>
          ))}
        </div>
      </div>

      {/* Price Range */}
      <div>
        <h3 className="font-serif text-lg font-semibold mb-4">Price Range</h3>
        <div className="space-y-3">
          {priceRanges.map((range) => (
            <label
              key={range.value}
              className="flex items-center gap-3 cursor-pointer group"
            >
              <Checkbox
                checked={selectedPriceRange === range.value}
                onCheckedChange={() => handlePriceChange(range.value)}
              />
              <span className="text-sm text-foreground/80 group-hover:text-foreground transition-colors">
                {range.label}
              </span>
            </label>
          ))}
        </div>
      </div>

      {/* Clear Filters */}
      {hasActiveFilters && (
        <Button variant="outline" className="w-full" onClick={clearFilters}>
          <X className="h-4 w-4 mr-2" />
          Clear All Filters
        </Button>
      )}
    </div>
  );

  return (
    <Layout>
      <div className="bg-secondary/30 py-8">
        <div className="container mx-auto px-5 sm:px-6 lg:px-8">
          {/* Breadcrumb */}
          <nav className="breadcrumb mb-4">
            <Link to="/">Home</Link>
            <ChevronDown className="h-4 w-4 rotate-[-90deg]" />
            <span className="text-foreground">Shop</span>
            {selectedCategory && (
              <>
                <ChevronDown className="h-4 w-4 rotate-[-90deg]" />
                <span className="text-foreground capitalize">{selectedCategory.replace("-", " ")}</span>
              </>
            )}
          </nav>

          <h1 className="font-serif text-3xl md:text-4xl font-bold text-foreground">
            {selectedCategory
              ? `Shop ${selectedCategory.replace("-", " ").replace(/\b\w/g, (c) => c.toUpperCase())}`
              : "All Products"}
          </h1>
        </div>
      </div>

      <div className="container mx-auto px-5 sm:px-6 lg:px-8 py-8">
        <div className="flex gap-8">
          {/* Desktop Sidebar */}
          <aside className="hidden lg:block w-64 flex-shrink-0">
            <FilterSidebar categoriesProp={allCategories} />
          </aside>

          {/* Main Content */}
          <div className="flex-1">
            {/* Toolbar */}
            <div className="flex flex-wrap items-center justify-between gap-4 mb-6 pb-4 border-b border-border">
              <p className="text-sm text-muted-foreground">
                Showing {filteredProducts.length} products
              </p>

              <div className="flex items-center gap-4">
                {/* Mobile Filter */}
                <Sheet>
                  <SheetTrigger asChild>
                    <Button variant="outline" className="lg:hidden">
                      <Filter className="h-4 w-4 mr-2" />
                      Filters
                      {hasActiveFilters && (
                        <span className="ml-2 h-5 w-5 rounded-full bg-primary text-primary-foreground text-xs flex items-center justify-center">
                          !
                        </span>
                      )}
                    </Button>
                  </SheetTrigger>
                  <SheetContent side="left">
                    <SheetHeader>
                      <SheetTitle>Filters</SheetTitle>
                    </SheetHeader>
                    <div className="mt-6">
                      <FilterSidebar categoriesProp={allCategories} />
                    </div>
                  </SheetContent>
                </Sheet>

                {/* Sort */}
                <Select value={selectedSort} onValueChange={handleSortChange}>
                  <SelectTrigger className="w-[180px]">
                    <SelectValue placeholder="Sort by" />
                  </SelectTrigger>
                  <SelectContent>
                    {sortOptions.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                {/* View Toggle */}
                <div className="hidden sm:flex items-center border border-border rounded-md">
                  <button
                    onClick={() => setIsGridView(true)}
                    className={cn(
                      "p-2 transition-colors",
                      isGridView ? "bg-secondary" : "hover:bg-secondary/50"
                    )}
                    aria-label="Grid view"
                  >
                    <Grid className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => setIsGridView(false)}
                    className={cn(
                      "p-2 transition-colors",
                      !isGridView ? "bg-secondary" : "hover:bg-secondary/50"
                    )}
                    aria-label="List view"
                  >
                    <List className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>

            {/* Products Grid */}
            {filteredProducts.length > 0 ? (
              <div
                className={cn(
                  "grid gap-4 md:gap-6",
                  isGridView
                    ? "grid-cols-2 md:grid-cols-3"
                    : "grid-cols-1"
                )}
              >
                {filteredProducts.map((product, index) => (
                  <div
                    key={product.id}
                    className="animate-fade-up"
                    style={{ animationDelay: `${index * 0.05}s` }}
                  >
                    <ProductCard product={product} />
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-16">
                <p className="text-lg text-muted-foreground mb-4">
                  No products found matching your criteria.
                </p>
                <Button variant="outline" onClick={clearFilters}>
                  Clear Filters
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default Products;
