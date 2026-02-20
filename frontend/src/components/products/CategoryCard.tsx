import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { Category } from "@/types/product";
import { prefetchCategoryProducts, prefetchProductsPage } from "@/data/products";

interface CategoryCardProps {
  category: Category;
}

const FALLBACK_CATEGORY_IMAGE =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 600 800'%3E%3Crect width='600' height='800' fill='%23ececec'/%3E%3Ctext x='50%25' y='50%25' fill='%23777' font-size='28' text-anchor='middle' dominant-baseline='middle'%3ECategory%3C/text%3E%3C/svg%3E";

export const CategoryCard = ({ category }: CategoryCardProps) => {
  return (
    <Link
      to={`/products?category=${category.slug}`}
      className="group block relative aspect-[4/5] overflow-hidden rounded-2xl"
      onMouseEnter={() => {
        prefetchCategoryProducts(category.slug);
        prefetchProductsPage();
      }}
      onFocus={() => {
        prefetchCategoryProducts(category.slug);
        prefetchProductsPage();
      }}
      onTouchStart={() => {
        prefetchCategoryProducts(category.slug);
        prefetchProductsPage();
      }}
    >
      <img
        src={category.image || FALLBACK_CATEGORY_IMAGE}
        alt={category.name}
        className="w-full h-full object-cover opacity-85 transition-all duration-700 group-hover:scale-110 group-hover:opacity-75"
        loading="lazy"
        onError={(e) => {
          e.currentTarget.src = FALLBACK_CATEGORY_IMAGE;
        }}
      />
      
      {/* Elegant gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-t from-foreground/90 via-foreground/50 to-foreground/10 transition-opacity duration-300" />
      
      {/* Content */}
      <div className="absolute inset-0 z-10 flex flex-col justify-end p-6">
        <div className="transform transition-transform duration-300 group-hover:-translate-y-2">
          <span className="inline-block text-primary-foreground/70 text-xs uppercase tracking-[0.2em] mb-2">
            {category.productCount} Products
          </span>
          <h3 className="font-serif text-2xl md:text-3xl font-bold text-primary-foreground mb-3">
            {category.name}
          </h3>
          <span className="inline-flex items-center gap-2 text-sm font-medium text-primary-foreground/90 group-hover:gap-3 transition-all">
            Shop Now
            <ArrowRight className="h-4 w-4" />
          </span>
        </div>
      </div>
      
      {/* Hover border effect */}
      <div className="absolute inset-0 border-2 border-transparent group-hover:border-primary/30 rounded-2xl transition-colors duration-300" />
    </Link>
  );
};
