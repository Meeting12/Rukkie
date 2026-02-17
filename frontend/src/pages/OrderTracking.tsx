import { useState } from "react";
import { Link } from "react-router-dom";
import {
  ChevronDown,
  Package,
  Search,
  CheckCircle2,
  Circle,
  Truck,
  MapPin,
  Clock,
} from "lucide-react";
import { Layout } from "@/components/layout/Layout";
import axios from 'axios';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const mockOrderStatuses = [
  {
    status: "Order Placed",
    date: "Feb 1, 2026 - 10:30 AM",
    completed: true,
    description: "Your order has been confirmed",
  },
  {
    status: "Processing",
    date: "Feb 1, 2026 - 2:15 PM",
    completed: true,
    description: "We're preparing your items",
  },
  {
    status: "Shipped",
    date: "Feb 2, 2026 - 9:00 AM",
    completed: true,
    description: "Your package is on its way",
  },
  {
    status: "Out for Delivery",
    date: "Expected Feb 5, 2026",
    completed: false,
    description: "Package is with the courier",
  },
  {
    status: "Delivered",
    date: "",
    completed: false,
    description: "Package delivered to your address",
  },
];

const OrderTracking = () => {
  const [orderNumber, setOrderNumber] = useState("");
  const [isTracking, setIsTracking] = useState(false);
  const [orderData, setOrderData] = useState<any | null>(null);

  const handleTrack = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!orderNumber.trim()) return;
    setIsTracking(true);
    try {
      const resp = await axios.get('/api/orders/track/', { params: { order_number: orderNumber } });
      setOrderData(resp.data);
    } catch (err) {
      setOrderData(null);
    }
  };

  return (
    <Layout>
      <div className="bg-secondary/30 py-8">
        <div className="container mx-auto px-4">
          <nav className="breadcrumb mb-4">
            <Link to="/">Home</Link>
            <ChevronDown className="h-4 w-4 rotate-[-90deg]" />
            <span className="text-foreground">Order Tracking</span>
          </nav>
          <h1 className="font-serif text-3xl md:text-4xl font-bold text-foreground">
            Track Your Order
          </h1>
        </div>
      </div>

      <div className="container mx-auto px-4 py-12">
        <div className="max-w-2xl mx-auto">
          {/* Search Form */}
          <Card className="mb-8">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Search className="h-5 w-5" />
                Enter Your Order Details
              </CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleTrack} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="orderNumber">Order Number</Label>
                  <Input
                    id="orderNumber"
                    placeholder="e.g., DRK-2026-001234"
                    value={orderNumber}
                    onChange={(e) => setOrderNumber(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email">Email Address (optional)</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="Email used for the order"
                  />
                </div>
                <Button type="submit" className="w-full">
                  <Package className="h-4 w-4 mr-2" />
                  Track Order
                </Button>
              </form>
            </CardContent>
          </Card>

          {/* Tracking Results */}
          {isTracking && (
            <div className="space-y-6 animate-fade-in">
              <Card>
                <CardHeader>
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                    <div>
                      <CardTitle>Order #{orderNumber}</CardTitle>
                      <p className="text-sm text-muted-foreground mt-1">Status: {orderData ? orderData.status : 'Unknown'}</p>
                    </div>
                    <div className="flex items-center gap-2 text-primary">
                      <Truck className="h-5 w-5" />
                      <span className="font-medium">{orderData ? orderData.status : 'N/A'}</span>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="relative">
                    {orderData && orderData.items && orderData.items.map((it:any, index:number) => (
                      <div key={index} className="flex gap-4 pb-8 last:pb-0">
                        <div className="flex flex-col items-center">
                          <Circle className="h-6 w-6 text-muted-foreground flex-shrink-0" />
                          {index < orderData.items.length - 1 && (
                            <div className={`w-0.5 flex-1 mt-2 bg-muted`} />
                          )}
                        </div>
                        <div className="flex-1 pb-2">
                          <h3 className="font-medium text-foreground">{it.product.name}</h3>
                          <p className="text-sm text-muted-foreground">Qty: {it.quantity}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Shipping Details */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <MapPin className="h-5 w-5" />
                    Shipping Address
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-sm space-y-1">
                    <p className="font-medium">John Doe</p>
                    <p className="text-muted-foreground">123 Main Street</p>
                    <p className="text-muted-foreground">Apt 4B</p>
                    <p className="text-muted-foreground">New York, NY 10001</p>
                    <p className="text-muted-foreground">United States</p>
                  </div>
                </CardContent>
              </Card>

              <div className="text-center">
                <p className="text-sm text-muted-foreground mb-4">
                  Have questions about your order?
                </p>
                <Link to="/contact">
                  <Button variant="outline">Contact Support</Button>
                </Link>
              </div>
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
};

export default OrderTracking;
