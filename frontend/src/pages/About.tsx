import { Link } from "react-router-dom";
import { ChevronDown, Target, Heart, Users, Award, Mail, Phone, MapPin } from "lucide-react";
import { Layout } from "@/components/layout/Layout";
import { Button } from "@/components/ui/button";

const values = [
  {
    icon: Target,
    title: "Quality First",
    description: "We carefully curate every product to ensure it meets our high standards of quality and craftsmanship.",
  },
  {
    icon: Heart,
    title: "Customer Love",
    description: "Your satisfaction is our priority. We go above and beyond to create exceptional shopping experiences.",
  },
  {
    icon: Users,
    title: "Community",
    description: "We believe in building lasting relationships with our customers and supporting local artisans worldwide.",
  },
  {
    icon: Award,
    title: "Excellence",
    description: "From product selection to delivery, we strive for excellence in every aspect of our business.",
  },
];

const About = () => {
  return (
    <Layout>
      {/* Breadcrumb */}
      <div className="bg-secondary/30 py-4">
        <div className="container mx-auto px-4">
          <nav className="breadcrumb">
            <Link to="/">Home</Link>
            <ChevronDown className="h-4 w-4 rotate-[-90deg]" />
            <span className="text-foreground">About Us</span>
          </nav>
        </div>
      </div>

      {/* Hero Section */}
      <section className="section-padding hero-gradient">
        <div className="container mx-auto px-4">
          <div className="max-w-3xl mx-auto text-center">
            <span className="text-sm font-medium text-primary uppercase tracking-widest">
              Our Story
            </span>
            <h1 className="font-serif text-4xl md:text-5xl font-bold text-foreground mt-4 mb-6">
              Curating Lifestyle Excellence Since 2020
            </h1>
            <p className="text-lg text-muted-foreground leading-relaxed">
              De-Rukkies Collections was born from a passion for bringing the world's finest products to discerning customers. We believe that everyone deserves access to quality, style, and innovation.
            </p>
          </div>
        </div>
      </section>

      {/* Story Section */}
      <section className="section-padding">
        <div className="container mx-auto px-4">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div className="relative">
              <img
                src="https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=600&h=700&fit=crop"
                alt="Our boutique store"
                className="rounded-2xl shadow-lg w-full"
              />
              <div className="absolute -bottom-6 -right-6 bg-primary text-primary-foreground p-6 rounded-xl shadow-lg">
                <p className="font-serif text-3xl font-bold">5+</p>
                <p className="text-sm">Years of Excellence</p>
              </div>
            </div>

            <div>
              <h2 className="font-serif text-3xl md:text-4xl font-bold text-foreground mb-6">
                From Passion to Purpose
              </h2>
              <div className="space-y-4 text-muted-foreground leading-relaxed">
                <p>
                  What started as a small online boutique has grown into a trusted destination for premium lifestyle products. Our founder's vision was simple: make quality accessible and shopping delightful.
                </p>
                <p>
                  Today, we serve thousands of customers across the globe, offering carefully selected electronics, fashion pieces, beauty essentials, and home décor that reflect our commitment to excellence.
                </p>
                <p>
                  Every product in our collection is handpicked by our expert team, ensuring that when you shop with De-Rukkies, you're getting nothing but the best.
                </p>
              </div>
              <Button variant="hero" className="mt-8" asChild>
                <Link to="/products">Explore Our Collection</Link>
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* Values Section */}
      <section className="section-padding bg-secondary/30">
        <div className="container mx-auto px-4">
          <div className="text-center mb-12">
            <span className="text-sm font-medium text-primary uppercase tracking-widest">
              What We Stand For
            </span>
            <h2 className="font-serif text-3xl md:text-4xl font-bold text-foreground mt-2">
              Our Core Values
            </h2>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            {values.map((value, index) => (
              <div
                key={index}
                className="bg-card p-6 rounded-xl border border-border text-center hover:shadow-lg transition-shadow"
              >
                <div className="inline-flex items-center justify-center w-14 h-14 bg-primary/10 rounded-full mb-4">
                  <value.icon className="h-7 w-7 text-primary" />
                </div>
                <h3 className="font-serif text-xl font-semibold text-foreground mb-2">
                  {value.title}
                </h3>
                <p className="text-sm text-muted-foreground">{value.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Mission Section */}
      <section className="section-padding bg-foreground text-background">
        <div className="container mx-auto px-4">
          <div className="max-w-3xl mx-auto text-center">
            <h2 className="font-serif text-3xl md:text-4xl font-bold mb-6">Our Mission</h2>
            <p className="text-xl text-background/80 leading-relaxed mb-8">
              "To inspire and empower our customers through a curated selection of premium products that enhance everyday life, delivered with exceptional service and unwavering commitment to quality."
            </p>
            <div className="h-1 w-24 bg-primary mx-auto" />
          </div>
        </div>
      </section>

      {/* Contact Section */}
      <section className="section-padding">
        <div className="container mx-auto px-4">
          <div className="max-w-4xl mx-auto">
            <div className="text-center mb-12">
              <span className="text-sm font-medium text-primary uppercase tracking-widest">
                Get In Touch
              </span>
              <h2 className="font-serif text-3xl md:text-4xl font-bold text-foreground mt-2">
                We'd Love to Hear From You
              </h2>
            </div>

            <div className="grid md:grid-cols-3 gap-8">
              <div className="text-center p-6">
                <div className="inline-flex items-center justify-center w-14 h-14 bg-primary/10 rounded-full mb-4">
                  <Mail className="h-6 w-6 text-primary" />
                </div>
                <h3 className="font-semibold text-foreground mb-2">Email Us</h3>
                <a href="mailto:hello@rukkies.com" className="text-muted-foreground hover:text-primary transition-colors">
                  hello@rukkies.com
                </a>
              </div>

              <div className="text-center p-6">
                <div className="inline-flex items-center justify-center w-14 h-14 bg-primary/10 rounded-full mb-4">
                  <Phone className="h-6 w-6 text-primary" />
                </div>
                <h3 className="font-semibold text-foreground mb-2">Call Us</h3>
                <a href="tel:+15551234567" className="text-muted-foreground hover:text-primary transition-colors">
                  +1 (555) 123-4567
                </a>
              </div>

              <div className="text-center p-6">
                <div className="inline-flex items-center justify-center w-14 h-14 bg-primary/10 rounded-full mb-4">
                  <MapPin className="h-6 w-6 text-primary" />
                </div>
                <h3 className="font-semibold text-foreground mb-2">Visit Us</h3>
                <p className="text-muted-foreground">
                  Lagos, Nigeria
                </p>
              </div>
            </div>

            <div className="text-center mt-8">
              <Button variant="elegant" asChild>
                <Link to="/contact">Contact Us</Link>
              </Button>
            </div>
          </div>
        </div>
      </section>
    </Layout>
  );
};

export default About;
