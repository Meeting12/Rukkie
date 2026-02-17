import { Link } from "react-router-dom";
import { ChevronDown, Truck, RotateCcw, Clock, Globe, Package } from "lucide-react";
import { Layout } from "@/components/layout/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

const shippingOptions = [
  {
    name: "Standard Shipping",
    time: "5-7 business days",
    price: "$5.99",
    freeOver: "$100",
  },
  {
    name: "Express Shipping",
    time: "2-3 business days",
    price: "$12.99",
    freeOver: "$200",
  },
  {
    name: "Next Day Delivery",
    time: "1 business day",
    price: "$24.99",
    freeOver: null,
  },
];

const internationalZones = [
  { region: "Canada", time: "7-10 business days", price: "From $15.99" },
  { region: "Europe", time: "10-14 business days", price: "From $19.99" },
  { region: "UK", time: "7-12 business days", price: "From $17.99" },
  { region: "Australia", time: "12-18 business days", price: "From $24.99" },
  { region: "Rest of World", time: "14-21 business days", price: "From $29.99" },
];

const ShippingReturns = () => {
  return (
    <Layout>
      <div className="bg-secondary/30 py-8">
        <div className="container mx-auto px-4">
          <nav className="breadcrumb mb-4">
            <Link to="/">Home</Link>
            <ChevronDown className="h-4 w-4 rotate-[-90deg]" />
            <span className="text-foreground">Shipping & Returns</span>
          </nav>
          <h1 className="font-serif text-3xl md:text-4xl font-bold text-foreground">
            Shipping & Returns
          </h1>
        </div>
      </div>

      <div className="container mx-auto px-4 py-12">
        <Tabs defaultValue="shipping" className="max-w-4xl mx-auto">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="shipping" className="flex items-center gap-2">
              <Truck className="h-4 w-4" />
              Shipping
            </TabsTrigger>
            <TabsTrigger value="returns" className="flex items-center gap-2">
              <RotateCcw className="h-4 w-4" />
              Returns
            </TabsTrigger>
          </TabsList>

          <TabsContent value="shipping" className="space-y-8 mt-8">
            {/* Domestic Shipping */}
            <section>
              <h2 className="font-serif text-2xl font-semibold mb-6">
                Domestic Shipping (USA)
              </h2>
              <div className="grid gap-4 md:grid-cols-3">
                {shippingOptions.map((option) => (
                  <Card key={option.name}>
                    <CardHeader>
                      <CardTitle className="text-lg">{option.name}</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <Clock className="h-4 w-4" />
                        {option.time}
                      </div>
                      <p className="text-2xl font-bold text-primary">{option.price}</p>
                      {option.freeOver && (
                        <p className="text-sm text-muted-foreground">
                          Free on orders over {option.freeOver}
                        </p>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            </section>

            {/* International Shipping */}
            <section>
              <h2 className="font-serif text-2xl font-semibold mb-6 flex items-center gap-2">
                <Globe className="h-6 w-6" />
                International Shipping
              </h2>
              <Card>
                <CardContent className="p-0">
                  <div className="divide-y divide-border">
                    {internationalZones.map((zone) => (
                      <div
                        key={zone.region}
                        className="flex flex-col sm:flex-row sm:items-center justify-between p-4 gap-2"
                      >
                        <span className="font-medium">{zone.region}</span>
                        <span className="text-muted-foreground">{zone.time}</span>
                        <span className="text-primary font-semibold">{zone.price}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
              <p className="text-sm text-muted-foreground mt-4">
                * International orders may be subject to customs duties and taxes, which are the
                responsibility of the recipient.
              </p>
            </section>

            {/* Shipping FAQs */}
            <section>
              <h2 className="font-serif text-2xl font-semibold mb-6">
                Shipping Information
              </h2>
              <div className="prose prose-invert max-w-none space-y-4 text-foreground/80">
                <p>
                  <strong>Processing Time:</strong> Orders are typically processed within 1-2
                  business days. Orders placed after 2 PM EST will begin processing the next
                  business day.
                </p>
                <p>
                  <strong>Order Tracking:</strong> You'll receive a shipping confirmation email
                  with tracking information once your order ships. You can also track your order
                  on our <Link to="/order-tracking" className="text-primary hover:underline">Order Tracking</Link> page.
                </p>
                <p>
                  <strong>Delivery Signature:</strong> Orders over $200 may require a signature
                  upon delivery for security purposes.
                </p>
              </div>
            </section>
          </TabsContent>

          <TabsContent value="returns" className="space-y-8 mt-8">
            {/* Return Policy */}
            <section>
              <h2 className="font-serif text-2xl font-semibold mb-6">
                Our Return Policy
              </h2>
              <Card>
                <CardContent className="p-6 space-y-4">
                  <div className="flex items-start gap-4">
                    <div className="h-12 w-12 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0">
                      <Clock className="h-6 w-6 text-primary" />
                    </div>
                    <div>
                      <h3 className="font-semibold mb-1">30-Day Return Window</h3>
                      <p className="text-muted-foreground">
                        Return any unworn item within 30 days of delivery for a full refund.
                      </p>
                    </div>
                  </div>
                  <div className="flex items-start gap-4">
                    <div className="h-12 w-12 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0">
                      <Package className="h-6 w-6 text-primary" />
                    </div>
                    <div>
                      <h3 className="font-semibold mb-1">Free Returns</h3>
                      <p className="text-muted-foreground">
                        We provide free return shipping on all US orders. International returns are
                        at the customer's expense.
                      </p>
                    </div>
                  </div>
                  <div className="flex items-start gap-4">
                    <div className="h-12 w-12 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0">
                      <RotateCcw className="h-6 w-6 text-primary" />
                    </div>
                    <div>
                      <h3 className="font-semibold mb-1">Easy Exchanges</h3>
                      <p className="text-muted-foreground">
                        Need a different size or color? We'll ship your exchange for free.
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </section>

            {/* Return Conditions */}
            <section>
              <h2 className="font-serif text-2xl font-semibold mb-6">
                Return Conditions
              </h2>
              <div className="grid gap-4 md:grid-cols-2">
                <Card className="border-primary/30 bg-primary/5">
                  <CardHeader>
                    <CardTitle className="text-primary">Eligible for Return</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2 text-sm">
                      <li>✓ Unworn and unwashed items</li>
                      <li>✓ Original tags attached</li>
                      <li>✓ Original packaging included</li>
                      <li>✓ Within 30 days of delivery</li>
                      <li>✓ Proof of purchase</li>
                    </ul>
                  </CardContent>
                </Card>
                <Card className="border-destructive/30 bg-destructive/5">
                  <CardHeader>
                    <CardTitle className="text-destructive">Not Eligible</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2 text-sm">
                      <li>✗ Worn or washed items</li>
                      <li>✗ Items without tags</li>
                      <li>✗ Sale or clearance items (final sale)</li>
                      <li>✗ Swimwear & intimates</li>
                      <li>✗ Customized items</li>
                    </ul>
                  </CardContent>
                </Card>
              </div>
            </section>

            {/* How to Return */}
            <section>
              <h2 className="font-serif text-2xl font-semibold mb-6">
                How to Start a Return
              </h2>
              <div className="space-y-4">
                <div className="flex gap-4">
                  <div className="h-8 w-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-semibold flex-shrink-0">
                    1
                  </div>
                  <div>
                    <h3 className="font-semibold">Log into your account</h3>
                    <p className="text-muted-foreground text-sm">
                      Go to your Order History and select the item you wish to return.
                    </p>
                  </div>
                </div>
                <div className="flex gap-4">
                  <div className="h-8 w-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-semibold flex-shrink-0">
                    2
                  </div>
                  <div>
                    <h3 className="font-semibold">Print your return label</h3>
                    <p className="text-muted-foreground text-sm">
                      We'll email you a prepaid return label (US orders only).
                    </p>
                  </div>
                </div>
                <div className="flex gap-4">
                  <div className="h-8 w-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-semibold flex-shrink-0">
                    3
                  </div>
                  <div>
                    <h3 className="font-semibold">Ship your return</h3>
                    <p className="text-muted-foreground text-sm">
                      Drop off your package at any authorized shipping location.
                    </p>
                  </div>
                </div>
                <div className="flex gap-4">
                  <div className="h-8 w-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-semibold flex-shrink-0">
                    4
                  </div>
                  <div>
                    <h3 className="font-semibold">Receive your refund</h3>
                    <p className="text-muted-foreground text-sm">
                      Refunds are processed within 5-7 business days of receiving your return.
                    </p>
                  </div>
                </div>
              </div>
            </section>
          </TabsContent>
        </Tabs>
      </div>
    </Layout>
  );
};

export default ShippingReturns;
