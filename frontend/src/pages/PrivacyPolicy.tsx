import { Link } from "react-router-dom";
import { ChevronDown } from "lucide-react";
import { Layout } from "@/components/layout/Layout";

const PrivacyPolicy = () => {
  return (
    <Layout>
      <div className="bg-secondary/30 py-8">
        <div className="container mx-auto px-4">
          <nav className="breadcrumb mb-4">
            <Link to="/">Home</Link>
            <ChevronDown className="h-4 w-4 rotate-[-90deg]" />
            <span className="text-foreground">Privacy Policy</span>
          </nav>
          <h1 className="font-serif text-3xl md:text-4xl font-bold text-foreground">
            Privacy Policy
          </h1>
          <p className="text-muted-foreground mt-2">Last updated: February 6, 2026</p>
        </div>
      </div>

      <div className="container mx-auto px-4 py-12">
        <div className="max-w-3xl mx-auto prose prose-invert">
          <section className="mb-8">
            <h2 className="font-serif text-2xl font-semibold mb-4">Introduction</h2>
            <p className="text-foreground/80">
              De-Rukkies Collections ("we," "our," or "us") respects your privacy and is committed
              to protecting your personal data. This privacy policy explains how we collect, use,
              disclose, and safeguard your information when you visit our website or make a
              purchase.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="font-serif text-2xl font-semibold mb-4">Information We Collect</h2>
            <h3 className="text-lg font-semibold mb-2">Personal Information</h3>
            <ul className="list-disc pl-6 text-foreground/80 space-y-2 mb-4">
              <li>Name and contact information (email, phone number, address)</li>
              <li>Payment information (credit card details, billing address)</li>
              <li>Account credentials (username, password)</li>
              <li>Order history and preferences</li>
              <li>Communication preferences</li>
            </ul>

            <h3 className="text-lg font-semibold mb-2">Automatically Collected Information</h3>
            <ul className="list-disc pl-6 text-foreground/80 space-y-2">
              <li>Device information (IP address, browser type, operating system)</li>
              <li>Usage data (pages visited, time spent, click patterns)</li>
              <li>Cookies and similar tracking technologies</li>
              <li>Location data (with your consent)</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="font-serif text-2xl font-semibold mb-4">How We Use Your Information</h2>
            <ul className="list-disc pl-6 text-foreground/80 space-y-2">
              <li>Process and fulfill your orders</li>
              <li>Communicate with you about your orders and account</li>
              <li>Send marketing communications (with your consent)</li>
              <li>Improve our website and customer experience</li>
              <li>Detect and prevent fraud</li>
              <li>Comply with legal obligations</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="font-serif text-2xl font-semibold mb-4">Information Sharing</h2>
            <p className="text-foreground/80 mb-4">
              We may share your information with:
            </p>
            <ul className="list-disc pl-6 text-foreground/80 space-y-2">
              <li>Service providers (payment processors, shipping carriers)</li>
              <li>Analytics partners (Google Analytics)</li>
              <li>Marketing platforms (with your consent)</li>
              <li>Law enforcement (when required by law)</li>
            </ul>
            <p className="text-foreground/80 mt-4">
              We never sell your personal information to third parties.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="font-serif text-2xl font-semibold mb-4">Your Rights</h2>
            <p className="text-foreground/80 mb-4">You have the right to:</p>
            <ul className="list-disc pl-6 text-foreground/80 space-y-2">
              <li>Access your personal data</li>
              <li>Correct inaccurate data</li>
              <li>Request deletion of your data</li>
              <li>Opt-out of marketing communications</li>
              <li>Data portability</li>
              <li>Withdraw consent at any time</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="font-serif text-2xl font-semibold mb-4">Cookies</h2>
            <p className="text-foreground/80">
              We use cookies and similar technologies to enhance your browsing experience,
              analyze site traffic, and personalize content. You can control cookie preferences
              through your browser settings. Essential cookies are required for the site to
              function properly.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="font-serif text-2xl font-semibold mb-4">Data Security</h2>
            <p className="text-foreground/80">
              We implement appropriate technical and organizational measures to protect your
              personal data, including encryption, secure servers, and regular security audits.
              However, no method of transmission over the Internet is 100% secure.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="font-serif text-2xl font-semibold mb-4">Children's Privacy</h2>
            <p className="text-foreground/80">
              Our website is not intended for children under 13 years of age. We do not knowingly
              collect personal information from children under 13.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="font-serif text-2xl font-semibold mb-4">Changes to This Policy</h2>
            <p className="text-foreground/80">
              We may update this privacy policy from time to time. We will notify you of any
              changes by posting the new policy on this page and updating the "Last updated" date.
            </p>
          </section>

          <section>
            <h2 className="font-serif text-2xl font-semibold mb-4">Contact Us</h2>
            <p className="text-foreground/80">
              If you have questions about this privacy policy or our practices, please contact us:
            </p>
            <ul className="list-none text-foreground/80 space-y-1 mt-4">
              <li>Email: privacy@derukkies.com</li>
              <li>Phone: +1 (555) 123-4567</li>
              <li>Address: 123 Fashion Street, New York, NY 10001</li>
            </ul>
          </section>
        </div>
      </div>
    </Layout>
  );
};

export default PrivacyPolicy;
