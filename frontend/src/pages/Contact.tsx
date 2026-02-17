import { useState } from "react";
import { Link } from "react-router-dom";
import { ChevronDown, Mail, Phone, MapPin, MessageSquare, Clock, Send } from "lucide-react";
import { Layout } from "@/components/layout/Layout";
import { fetchJSON } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { toast } from "sonner";

const faqs = [
  {
    question: "What payment methods do you accept?",
    answer: "We accept all major credit and debit cards through Flutterwave, including Visa, Mastercard, and American Express. We also support bank transfers and mobile money payments for international customers.",
  },
  {
    question: "How long does shipping take?",
    answer: "Domestic orders typically arrive within 3-5 business days. International shipping takes 7-14 business days depending on your location. Digital products are delivered instantly via email.",
  },
  {
    question: "What is your return policy?",
    answer: "We offer a 30-day return policy for physical products in original condition. Digital products are non-refundable due to their nature. Please contact our support team to initiate a return.",
  },
  {
    question: "Do you ship internationally?",
    answer: "Yes! We ship to over 100 countries worldwide. Shipping costs and delivery times vary by location. You can see exact shipping costs at checkout.",
  },
  {
    question: "How can I track my order?",
    answer: "Once your order ships, you'll receive an email with tracking information. You can also track your order by logging into your account or contacting our support team.",
  },
  {
    question: "Are digital products available for immediate download?",
    answer: "Yes! All digital products are available for immediate download after purchase. You'll receive a download link via email and can also access your purchases from your account dashboard.",
  },
];

const Contact = () => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    subject: "",
    message: "",
  });

  const parseApiErrorMessage = (raw: string) => {
    try {
      const parsed = JSON.parse(raw);
      return parsed?.detail || parsed?.error || raw;
    } catch {
      return raw;
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      await fetchJSON("/api/contact/", {
        method: "POST",
        body: JSON.stringify(formData),
      });
      toast.success("Message sent! We'll get back to you within 24 hours.");
      setFormData({ name: "", email: "", subject: "", message: "" });
    } catch (err: any) {
      toast.error(parseApiErrorMessage(err?.message || "Failed to send message"));
    } finally {
      setIsSubmitting(false);
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
            <span className="text-foreground">Contact & FAQ</span>
          </nav>
        </div>
      </div>

      {/* Header */}
      <section className="section-padding hero-gradient">
        <div className="container mx-auto px-4">
          <div className="max-w-3xl mx-auto text-center">
            <h1 className="font-serif text-4xl md:text-5xl font-bold text-foreground mb-4">
              How Can We Help?
            </h1>
            <p className="text-lg text-muted-foreground">
              Have a question or need assistance? We're here to help you with anything you need.
            </p>
          </div>
        </div>
      </section>

      {/* Contact Info Cards */}
      <section className="py-12">
        <div className="container mx-auto px-4">
          <div className="grid md:grid-cols-4 gap-6 -mt-20 relative z-10">
            <div className="bg-card border border-border rounded-xl p-6 text-center shadow-lg">
              <div className="inline-flex items-center justify-center w-12 h-12 bg-primary/10 rounded-full mb-4">
                <Mail className="h-5 w-5 text-primary" />
              </div>
              <h3 className="font-semibold text-foreground mb-2">Email</h3>
              <a href="mailto:hello@rukkies.com" className="text-sm text-muted-foreground hover:text-primary transition-colors">
                hello@rukkies.com
              </a>
            </div>

            <div className="bg-card border border-border rounded-xl p-6 text-center shadow-lg">
              <div className="inline-flex items-center justify-center w-12 h-12 bg-primary/10 rounded-full mb-4">
                <Phone className="h-5 w-5 text-primary" />
              </div>
              <h3 className="font-semibold text-foreground mb-2">Phone</h3>
              <a href="tel:+15551234567" className="text-sm text-muted-foreground hover:text-primary transition-colors">
                +1 (555) 123-4567
              </a>
            </div>

            <div className="bg-card border border-border rounded-xl p-6 text-center shadow-lg">
              <div className="inline-flex items-center justify-center w-12 h-12 bg-primary/10 rounded-full mb-4">
                <MapPin className="h-5 w-5 text-primary" />
              </div>
              <h3 className="font-semibold text-foreground mb-2">Location</h3>
              <p className="text-sm text-muted-foreground">Lagos, Nigeria</p>
            </div>

            <div className="bg-card border border-border rounded-xl p-6 text-center shadow-lg">
              <div className="inline-flex items-center justify-center w-12 h-12 bg-primary/10 rounded-full mb-4">
                <Clock className="h-5 w-5 text-primary" />
              </div>
              <h3 className="font-semibold text-foreground mb-2">Hours</h3>
              <p className="text-sm text-muted-foreground">Mon-Fri: 9am-6pm WAT</p>
            </div>
          </div>
        </div>
      </section>

      {/* Contact Form & FAQ */}
      <section className="section-padding">
        <div className="container mx-auto px-4">
          <div className="grid lg:grid-cols-2 gap-12">
            {/* Contact Form */}
            <div>
              <div className="flex items-center gap-3 mb-6">
                <MessageSquare className="h-6 w-6 text-primary" />
                <h2 className="font-serif text-2xl font-bold text-foreground">Send Us a Message</h2>
              </div>

              <form onSubmit={handleSubmit} className="space-y-6">
                <div className="grid md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="name">Full Name</Label>
                    <Input
                      id="name"
                      required
                      placeholder="John Doe"
                      value={formData.name}
                      onChange={(e) => setFormData((prev) => ({ ...prev, name: e.target.value }))}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="email">Email Address</Label>
                    <Input
                      id="email"
                      type="email"
                      required
                      placeholder="john@example.com"
                      value={formData.email}
                      onChange={(e) => setFormData((prev) => ({ ...prev, email: e.target.value }))}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="subject">Subject</Label>
                  <Input
                    id="subject"
                    required
                    placeholder="How can we help?"
                    value={formData.subject}
                    onChange={(e) => setFormData((prev) => ({ ...prev, subject: e.target.value }))}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="message">Message</Label>
                  <Textarea
                    id="message"
                    required
                    placeholder="Tell us more about your inquiry..."
                    rows={6}
                    value={formData.message}
                    onChange={(e) => setFormData((prev) => ({ ...prev, message: e.target.value }))}
                  />
                </div>

                <Button variant="hero" type="submit" disabled={isSubmitting}>
                  {isSubmitting ? (
                    "Sending..."
                  ) : (
                    <>
                      Send Message
                      <Send className="ml-2 h-4 w-4" />
                    </>
                  )}
                </Button>
              </form>
            </div>

            {/* FAQ */}
            <div>
              <h2 className="font-serif text-2xl font-bold text-foreground mb-6">
                Frequently Asked Questions
              </h2>

              <Accordion type="single" collapsible className="space-y-4">
                {faqs.map((faq, index) => (
                  <AccordionItem
                    key={index}
                    value={`item-${index}`}
                    className="bg-card border border-border rounded-lg px-4"
                  >
                    <AccordionTrigger className="text-left font-medium hover:text-primary">
                      {faq.question}
                    </AccordionTrigger>
                    <AccordionContent className="text-muted-foreground">
                      {faq.answer}
                    </AccordionContent>
                  </AccordionItem>
                ))}
              </Accordion>

              {/* Additional Help */}
              <div className="mt-8 p-6 bg-secondary/50 rounded-xl">
                <h3 className="font-semibold text-foreground mb-2">Still have questions?</h3>
                <p className="text-sm text-muted-foreground mb-4">
                  Can't find what you're looking for? Our support team is always ready to help.
                </p>
                <Button variant="outline" asChild>
                  <a href="mailto:support@rukkies.com">Email Support</a>
                </Button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Policies Section */}
      <section className="section-padding bg-secondary/30">
        <div className="container mx-auto px-4">
          <div className="text-center mb-12">
            <h2 className="font-serif text-2xl md:text-3xl font-bold text-foreground">
              Our Policies
            </h2>
          </div>

          <div className="grid md:grid-cols-3 gap-8 max-w-4xl mx-auto">
            <div className="text-center">
              <h3 className="font-semibold text-foreground mb-3">Shipping Policy</h3>
              <p className="text-sm text-muted-foreground">
                Free shipping on orders over $100. Standard delivery 3-5 days. Express options available.
              </p>
            </div>
            <div className="text-center">
              <h3 className="font-semibold text-foreground mb-3">Return Policy</h3>
              <p className="text-sm text-muted-foreground">
                30-day hassle-free returns for physical products. Full refund or exchange guaranteed.
              </p>
            </div>
            <div className="text-center">
              <h3 className="font-semibold text-foreground mb-3">Privacy Policy</h3>
              <p className="text-sm text-muted-foreground">
                Your data is secure. We never share your information with third parties.
              </p>
            </div>
          </div>
        </div>
      </section>
    </Layout>
  );
};

export default Contact;
