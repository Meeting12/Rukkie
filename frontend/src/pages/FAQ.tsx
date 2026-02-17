import { Link } from "react-router-dom";
import { ChevronDown, HelpCircle } from "lucide-react";
import { Layout } from "@/components/layout/Layout";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

const faqData = [
  {
    category: "Orders & Shipping",
    questions: [
      {
        q: "How long does shipping take?",
        a: "Standard shipping typically takes 5-7 business days within the US. Express shipping is available for 2-3 business day delivery. International orders may take 10-14 business days.",
      },
      {
        q: "How can I track my order?",
        a: "Once your order ships, you'll receive an email with a tracking number. You can also track your order in your account under 'Order History' or visit our Order Tracking page.",
      },
      {
        q: "Do you offer free shipping?",
        a: "Yes! We offer free standard shipping on all orders over $100. Use code WELCOME15 for 15% off your first order.",
      },
      {
        q: "Can I change or cancel my order?",
        a: "You can modify or cancel your order within 1 hour of placing it. After that, please contact our customer service team for assistance.",
      },
    ],
  },
  {
    category: "Returns & Exchanges",
    questions: [
      {
        q: "What is your return policy?",
        a: "We offer a 30-day return policy for unworn items with original tags attached. Items must be in their original condition. Sale items are final sale.",
      },
      {
        q: "How do I start a return?",
        a: "Log into your account and go to 'Order History'. Select the order and items you'd like to return, then follow the prompts to generate a return label.",
      },
      {
        q: "When will I receive my refund?",
        a: "Refunds are processed within 5-7 business days after we receive your return. The refund will be issued to your original payment method.",
      },
      {
        q: "Can I exchange an item for a different size?",
        a: "Yes! You can request an exchange for a different size during the return process. We'll ship the new size once we receive your return.",
      },
    ],
  },
  {
    category: "Products & Sizing",
    questions: [
      {
        q: "How do I find my size?",
        a: "Check our Size Guide for detailed measurements. Each product page also includes specific sizing information. When in doubt, our customer service team can help you find the perfect fit.",
      },
      {
        q: "Are your products authentic?",
        a: "Absolutely! De-Rukkies Collections only sells 100% authentic products sourced directly from brands and authorized distributors.",
      },
      {
        q: "How should I care for my items?",
        a: "Care instructions are included on each product's tag and listed on the product page. Generally, we recommend following the label instructions for best results.",
      },
    ],
  },
  {
    category: "Payment & Security",
    questions: [
      {
        q: "What payment methods do you accept?",
        a: "We accept all major credit cards (Visa, Mastercard, American Express), PayPal, Apple Pay, Google Pay, and Flutterwave for international payments.",
      },
      {
        q: "Is my payment information secure?",
        a: "Yes, we use industry-standard SSL encryption to protect your data. We never store your full credit card information on our servers.",
      },
      {
        q: "Do you offer payment plans?",
        a: "Yes! We partner with Klarna and Afterpay to offer interest-free payment plans. Select your preferred option at checkout.",
      },
    ],
  },
];

const FAQ = () => {
  return (
    <Layout>
      <div className="bg-secondary/30 py-8">
        <div className="container mx-auto px-4">
          <nav className="breadcrumb mb-4">
            <Link to="/">Home</Link>
            <ChevronDown className="h-4 w-4 rotate-[-90deg]" />
            <span className="text-foreground">FAQ</span>
          </nav>
          <h1 className="font-serif text-3xl md:text-4xl font-bold text-foreground">
            Frequently Asked Questions
          </h1>
        </div>
      </div>

      <div className="container mx-auto px-4 py-12">
        <div className="max-w-3xl mx-auto">
          <div className="flex items-center gap-3 mb-8 p-4 bg-primary/10 rounded-lg">
            <HelpCircle className="h-6 w-6 text-primary flex-shrink-0" />
            <p className="text-sm text-foreground/80">
              Can't find what you're looking for?{" "}
              <Link to="/contact" className="text-primary font-medium hover:underline">
                Contact our support team
              </Link>
            </p>
          </div>

          <div className="space-y-8">
            {faqData.map((section) => (
              <div key={section.category}>
                <h2 className="font-serif text-xl font-semibold mb-4">
                  {section.category}
                </h2>
                <Accordion type="single" collapsible className="space-y-2">
                  {section.questions.map((item, index) => (
                    <AccordionItem
                      key={index}
                      value={`${section.category}-${index}`}
                      className="border border-border rounded-lg px-4 bg-card"
                    >
                      <AccordionTrigger className="text-left hover:no-underline">
                        {item.q}
                      </AccordionTrigger>
                      <AccordionContent className="text-muted-foreground">
                        {item.a}
                      </AccordionContent>
                    </AccordionItem>
                  ))}
                </Accordion>
              </div>
            ))}
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default FAQ;
