import { Link } from "react-router-dom";
import { ChevronDown } from "lucide-react";
import { Layout } from "@/components/layout/Layout";

const TermsOfService = () => {
  return (
    <Layout>
      <div className="bg-secondary/30 py-8">
        <div className="container mx-auto px-4">
          <nav className="breadcrumb mb-4">
            <Link to="/">Home</Link>
            <ChevronDown className="h-4 w-4 rotate-[-90deg]" />
            <span className="text-foreground">Terms of Service</span>
          </nav>
          <h1 className="font-serif text-3xl md:text-4xl font-bold text-foreground">
            Terms of Service
          </h1>
          <p className="text-muted-foreground mt-2">Last updated: February 6, 2026</p>
        </div>
      </div>

      <div className="container mx-auto px-4 py-12">
        <div className="max-w-3xl mx-auto prose prose-invert">
          <section className="mb-8">
            <h2 className="font-serif text-2xl font-semibold mb-4">1. Acceptance of Terms</h2>
            <p className="text-foreground/80">
              By accessing and using the De-Rukkies Collections website ("Site"), you accept and
              agree to be bound by these Terms of Service. If you do not agree to these terms,
              please do not use our Site.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="font-serif text-2xl font-semibold mb-4">2. Use of the Site</h2>
            <p className="text-foreground/80 mb-4">You agree to use the Site only for lawful purposes and in accordance with these Terms. You agree not to:</p>
            <ul className="list-disc pl-6 text-foreground/80 space-y-2">
              <li>Use the Site in any way that violates applicable laws or regulations</li>
              <li>Impersonate any person or entity</li>
              <li>Interfere with or disrupt the Site or servers</li>
              <li>Attempt to gain unauthorized access to any portion of the Site</li>
              <li>Use any automated system to access the Site</li>
              <li>Transmit any viruses, malware, or harmful code</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="font-serif text-2xl font-semibold mb-4">3. Account Registration</h2>
            <p className="text-foreground/80">
              To access certain features, you may need to create an account. You are responsible
              for maintaining the confidentiality of your account credentials and for all
              activities under your account. You must notify us immediately of any unauthorized
              use.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="font-serif text-2xl font-semibold mb-4">4. Products and Pricing</h2>
            <ul className="list-disc pl-6 text-foreground/80 space-y-2">
              <li>All prices are displayed in USD unless otherwise stated</li>
              <li>Prices are subject to change without notice</li>
              <li>We reserve the right to limit quantities</li>
              <li>Product images are for illustration purposes; actual products may vary slightly</li>
              <li>We reserve the right to discontinue any product at any time</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="font-serif text-2xl font-semibold mb-4">5. Orders and Payment</h2>
            <p className="text-foreground/80 mb-4">
              By placing an order, you are making an offer to purchase. We reserve the right to
              refuse or cancel any order for any reason, including:
            </p>
            <ul className="list-disc pl-6 text-foreground/80 space-y-2">
              <li>Product unavailability</li>
              <li>Pricing errors</li>
              <li>Suspected fraud</li>
              <li>Order quantity limits</li>
            </ul>
            <p className="text-foreground/80 mt-4">
              Payment must be made at the time of purchase. We accept major credit cards, PayPal,
              and other payment methods as displayed at checkout.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="font-serif text-2xl font-semibold mb-4">6. Shipping and Delivery</h2>
            <p className="text-foreground/80">
              Shipping times are estimates and not guaranteed. We are not responsible for delays
              caused by shipping carriers, customs, or other factors beyond our control. Risk of
              loss transfers to you upon delivery to the carrier.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="font-serif text-2xl font-semibold mb-4">7. Returns and Refunds</h2>
            <p className="text-foreground/80">
              Our return policy is detailed on our{" "}
              <Link to="/shipping-returns" className="text-primary hover:underline">
                Shipping & Returns
              </Link>{" "}
              page. By making a purchase, you agree to our return policy terms.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="font-serif text-2xl font-semibold mb-4">8. Intellectual Property</h2>
            <p className="text-foreground/80">
              All content on this Site, including text, graphics, logos, images, and software, is
              the property of De-Rukkies Collections or its content suppliers and is protected by
              intellectual property laws. You may not reproduce, distribute, or create derivative
              works without our written permission.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="font-serif text-2xl font-semibold mb-4">9. User Content</h2>
            <p className="text-foreground/80">
              By submitting reviews, comments, or other content, you grant us a non-exclusive,
              royalty-free, perpetual license to use, reproduce, and display such content. You
              represent that you own or have the right to submit such content and that it does
              not violate any third-party rights.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="font-serif text-2xl font-semibold mb-4">10. Limitation of Liability</h2>
            <p className="text-foreground/80">
              To the fullest extent permitted by law, De-Rukkies Collections shall not be liable
              for any indirect, incidental, special, consequential, or punitive damages arising
              from your use of the Site or products purchased. Our total liability shall not
              exceed the amount you paid for the specific product in question.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="font-serif text-2xl font-semibold mb-4">11. Indemnification</h2>
            <p className="text-foreground/80">
              You agree to indemnify and hold harmless De-Rukkies Collections and its affiliates
              from any claims, damages, or expenses arising from your use of the Site, violation
              of these Terms, or infringement of any third-party rights.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="font-serif text-2xl font-semibold mb-4">12. Modifications</h2>
            <p className="text-foreground/80">
              We reserve the right to modify these Terms at any time. Changes will be effective
              immediately upon posting. Your continued use of the Site after changes constitutes
              acceptance of the modified Terms.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="font-serif text-2xl font-semibold mb-4">13. Governing Law</h2>
            <p className="text-foreground/80">
              These Terms shall be governed by the laws of the State of New York, without regard
              to conflict of law principles. Any disputes shall be resolved in the courts of
              New York County, New York.
            </p>
          </section>

          <section>
            <h2 className="font-serif text-2xl font-semibold mb-4">14. Contact Information</h2>
            <p className="text-foreground/80">
              For questions about these Terms, please contact us:
            </p>
            <ul className="list-none text-foreground/80 space-y-1 mt-4">
              <li>Email: legal@derukkies.com</li>
              <li>Phone: +1 (555) 123-4567</li>
              <li>Address: 123 Fashion Street, New York, NY 10001</li>
            </ul>
          </section>
        </div>
      </div>
    </Layout>
  );
};

export default TermsOfService;
