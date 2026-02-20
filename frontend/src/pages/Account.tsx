import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  ChevronDown,
  User,
  Package,
  Heart,
  MapPin,
  CreditCard,
  Settings,
  Bell,
  Mail,
  LogOut,
} from "lucide-react";
import { Layout } from "@/components/layout/Layout";
import { useAuth } from "@/context/AuthContext";
import { fetchJSON } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";

type AccountSection = "profile" | "orders" | "wishlist" | "addresses" | "payments" | "notifications" | "mailbox" | "settings";
type PaymentRecord = {
  id: number;
  provider: string;
  provider_transaction_id: string;
  amount: number | string;
  success: boolean;
  created_at: string;
};

type OrderRecord = {
  id: number;
  order_number: string;
  status: string;
  total: number | string;
  created_at: string;
  items: Array<{ id: number; quantity: number; price: number | string; product?: { name?: string } }>;
  transactions?: PaymentRecord[];
};

type AddressRecord = {
  id: number;
  full_name: string;
  line1: string;
  line2?: string;
  city: string;
  state?: string;
  postal_code: string;
  country: string;
  phone?: string;
};

type NotificationRecord = {
  id: number;
  title: string;
  message: string;
  level: "info" | "success" | "warning" | "error";
  is_read: boolean;
  read_at?: string | null;
  created_at: string;
};

type MailboxRecord = {
  id: number;
  subject: string;
  body: string;
  category: string;
  is_read: boolean;
  read_at?: string | null;
  created_at: string;
};

const Account = () => {
  const location = useLocation();
  const { isAuthenticated, username, login, logout, lastError } = useAuth();
  const [authTab, setAuthTab] = useState<"login" | "register">("login");
  const [loginForm, setLoginForm] = useState({ username: "", password: "" });
  const [registerForm, setRegisterForm] = useState({
    username: "",
    firstName: "",
    lastName: "",
    email: "",
    password: "",
  });
  const [activeSection, setActiveSection] = useState<AccountSection>("profile");
  const [orders, setOrders] = useState<OrderRecord[]>([]);
  const [ordersLoading, setOrdersLoading] = useState(false);
  const [addresses, setAddresses] = useState<AddressRecord[]>([]);
  const [addressesLoading, setAddressesLoading] = useState(false);
  const [notifications, setNotifications] = useState<NotificationRecord[]>([]);
  const [notificationsUnread, setNotificationsUnread] = useState(0);
  const [notificationsLoading, setNotificationsLoading] = useState(false);
  const [mailbox, setMailbox] = useState<MailboxRecord[]>([]);
  const [mailboxUnread, setMailboxUnread] = useState(0);
  const [mailboxLoading, setMailboxLoading] = useState(false);
  const [editingAddressId, setEditingAddressId] = useState<number | null>(null);
  const [addressForm, setAddressForm] = useState({
    full_name: "",
    line1: "",
    line2: "",
    city: "",
    state: "",
    postal_code: "",
    country: "United States",
    phone: "",
  });

  const loadOrders = async () => {
    setOrdersLoading(true);
    try {
      const data = await fetchJSON("/api/orders/");
      setOrders(Array.isArray(data) ? data : []);
    } catch {
      setOrders([]);
    } finally {
      setOrdersLoading(false);
    }
  };

  const loadAddresses = async () => {
    setAddressesLoading(true);
    try {
      const data = await fetchJSON("/api/account/addresses/");
      setAddresses(Array.isArray(data) ? data : []);
    } catch {
      setAddresses([]);
    } finally {
      setAddressesLoading(false);
    }
  };

  const loadNotifications = async () => {
    setNotificationsLoading(true);
    try {
      const data = await fetchJSON("/api/account/notifications/");
      setNotifications(Array.isArray(data?.results) ? data.results : []);
      setNotificationsUnread(Number(data?.unread_count || 0));
    } catch {
      setNotifications([]);
      setNotificationsUnread(0);
    } finally {
      setNotificationsLoading(false);
    }
  };

  const loadMailbox = async () => {
    setMailboxLoading(true);
    try {
      const data = await fetchJSON("/api/account/mailbox/");
      setMailbox(Array.isArray(data?.results) ? data.results : []);
      setMailboxUnread(Number(data?.unread_count || 0));
    } catch {
      setMailbox([]);
      setMailboxUnread(0);
    } finally {
      setMailboxLoading(false);
    }
  };

  useEffect(() => {
    if (!isAuthenticated) return;
    if (activeSection === "orders" || activeSection === "payments") {
      loadOrders();
    }
    if (activeSection === "addresses") {
      loadAddresses();
    }
    if (activeSection === "notifications") {
      loadNotifications();
    }
    if (activeSection === "mailbox") {
      loadMailbox();
    }
  }, [isAuthenticated, activeSection]);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const verified = params.get("verified");
    if (verified === "1") {
      toast.success("Email verified successfully. You can now log in.");
      setAuthTab("login");
    } else if (verified === "0") {
      toast.error("Verification link is invalid or expired.");
      setAuthTab("register");
    }
  }, [location.search]);

  const menuItems: Array<{ id: AccountSection; icon: typeof User; label: string }> = [
    { id: "profile", icon: User, label: "Profile" },
    { id: "orders", icon: Package, label: "Orders" },
    { id: "wishlist", icon: Heart, label: "Wishlist" },
    { id: "addresses", icon: MapPin, label: "Addresses" },
    { id: "payments", icon: CreditCard, label: "Payment Methods" },
    { id: "notifications", icon: Bell, label: notificationsUnread > 0 ? `Notifications (${notificationsUnread})` : "Notifications" },
    { id: "mailbox", icon: Mail, label: mailboxUnread > 0 ? `Mailbox (${mailboxUnread})` : "Mailbox" },
    { id: "settings", icon: Settings, label: "Settings" },
  ];

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    const ok = await login(loginForm.username, loginForm.password);
    if (ok) {
      toast.success("Welcome back!");
    } else {
      toast.error(lastError || "Invalid credentials");
    }
  };

  const parseApiErrorMessage = (raw: string) => {
    try {
      const parsed = JSON.parse(raw);
      if (parsed?.error === "username_taken") return "Username already exists.";
      if (parsed?.error === "email_taken") return "Email is already in use.";
      return parsed?.detail || parsed?.error || raw;
    } catch {
      return raw;
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await fetchJSON("/api/auth/register/", {
        method: "POST",
        body: JSON.stringify({
          username: registerForm.username,
          email: registerForm.email,
          password: registerForm.password,
          first_name: registerForm.firstName,
          last_name: registerForm.lastName,
        }),
      });
      toast.success("Verification link sent. Check your email to complete signup.");
      setRegisterForm({ username: "", firstName: "", lastName: "", email: "", password: "" });
      setAuthTab("login");
    } catch (err: any) {
      toast.error(parseApiErrorMessage(err?.message || "Registration failed"));
    }
  };

  if (!isAuthenticated) {
    return (
      <Layout>
        <div className="bg-secondary/30 py-8">
          <div className="container mx-auto px-4">
            <nav className="breadcrumb mb-4">
              <Link to="/">Home</Link>
              <ChevronDown className="h-4 w-4 rotate-[-90deg]" />
              <span className="text-foreground">Account</span>
            </nav>
            <h1 className="font-serif text-3xl md:text-4xl font-bold text-foreground">
              My Account
            </h1>
          </div>
        </div>

        <div className="container mx-auto px-4 py-12">
          <div className="max-w-md mx-auto">
            <Tabs value={authTab} onValueChange={(value) => setAuthTab(value as "login" | "register")} className="w-full">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="login">Login</TabsTrigger>
                <TabsTrigger value="register">Register</TabsTrigger>
              </TabsList>

              <TabsContent value="login">
                <Card>
                  <CardHeader>
                    <CardTitle>Welcome Back</CardTitle>
                    <CardDescription>
                      Sign in to your account to continue shopping
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <form onSubmit={handleLogin} className="space-y-4">
                      <div className="space-y-2">
                        <Label htmlFor="email">Email</Label>
                        <Input
                          id="username"
                          placeholder="Username"
                          value={loginForm.username}
                          onChange={(e) => setLoginForm({ ...loginForm, username: e.target.value })}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="password">Password</Label>
                        <Input
                          id="password"
                          type="password"
                          placeholder="Enter your password"
                          value={loginForm.password}
                          onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })}
                        />
                      </div>
                      <div className="flex items-center justify-between">
                        <Link
                          to="#"
                          className="text-sm text-primary hover:underline"
                        >
                          Forgot password?
                        </Link>
                      </div>
                      <Button type="submit" className="w-full">
                        Sign In
                      </Button>
                    </form>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="register">
                <Card>
                  <CardHeader>
                    <CardTitle>Create Account</CardTitle>
                    <CardDescription>
                      Join De-Rukkies Collections for exclusive offers
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <form onSubmit={handleRegister} className="space-y-4">
                      <div className="space-y-2">
                        <Label htmlFor="registerUsername">Username</Label>
                        <Input
                          id="registerUsername"
                          value={registerForm.username}
                          onChange={(e) => setRegisterForm({ ...registerForm, username: e.target.value })}
                          placeholder="john_doe"
                          required
                        />
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label htmlFor="firstName">First Name</Label>
                          <Input
                            id="firstName"
                            value={registerForm.firstName}
                            onChange={(e) => setRegisterForm({ ...registerForm, firstName: e.target.value })}
                            placeholder="John"
                            required
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="lastName">Last Name</Label>
                          <Input
                            id="lastName"
                            value={registerForm.lastName}
                            onChange={(e) => setRegisterForm({ ...registerForm, lastName: e.target.value })}
                            placeholder="Doe"
                            required
                          />
                        </div>
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="registerEmail">Email</Label>
                        <Input
                          id="registerEmail"
                          type="email"
                          value={registerForm.email}
                          onChange={(e) => setRegisterForm({ ...registerForm, email: e.target.value })}
                          placeholder="john@example.com"
                          required
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="registerPassword">Password</Label>
                        <Input
                          id="registerPassword"
                          type="password"
                          value={registerForm.password}
                          onChange={(e) => setRegisterForm({ ...registerForm, password: e.target.value })}
                          placeholder="Create a password"
                          required
                        />
                      </div>
                              <Button type="submit" className="w-full">
                                Create Account
                              </Button>
                    </form>
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          </div>
        </div>
      </Layout>
    );
  }

  const sectionMeta: Record<AccountSection, { title: string; description: string }> = {
    profile: { title: "Profile Information", description: "Update your personal details" },
    orders: { title: "Order History", description: "Track and review your recent orders" },
    wishlist: { title: "My Wishlist", description: "Products you saved for later" },
    addresses: { title: "Saved Addresses", description: "Manage shipping and billing addresses" },
    payments: { title: "Payment Methods", description: "Manage your saved payment options" },
    notifications: { title: "Notifications", description: "Stay updated with account and order alerts" },
    mailbox: { title: "Mailbox", description: "Read your account and order messages" },
    settings: { title: "Account Settings", description: "Update account preferences and security" },
  };

  const asMoney = (value: number | string) => {
    const n = Number(value);
    if (Number.isNaN(n)) return "$0.00";
    return `$${n.toFixed(2)}`;
  };

  const latestPayment = (order: OrderRecord) => {
    const txns = Array.isArray(order.transactions) ? order.transactions : [];
    if (!txns.length) return null;
    return [...txns].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0];
  };

  const resetAddressForm = () => {
    setAddressForm({
      full_name: "",
      line1: "",
      line2: "",
      city: "",
      state: "",
      postal_code: "",
      country: "United States",
      phone: "",
    });
    setEditingAddressId(null);
  };

  const saveAddress = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingAddressId) {
        await fetchJSON(`/api/account/addresses/${editingAddressId}/`, {
          method: "PUT",
          body: JSON.stringify(addressForm),
        });
        toast.success("Address updated.");
      } else {
        await fetchJSON("/api/account/addresses/create/", {
          method: "POST",
          body: JSON.stringify(addressForm),
        });
        toast.success("Address saved.");
      }
      resetAddressForm();
      loadAddresses();
    } catch (err: any) {
      toast.error(err?.message || "Unable to save address.");
    }
  };

  const editAddress = (address: AddressRecord) => {
    setEditingAddressId(address.id);
    setAddressForm({
      full_name: address.full_name || "",
      line1: address.line1 || "",
      line2: address.line2 || "",
      city: address.city || "",
      state: address.state || "",
      postal_code: address.postal_code || "",
      country: address.country || "United States",
      phone: address.phone || "",
    });
  };

  const deleteAddress = async (addressId: number) => {
    try {
      await fetchJSON(`/api/account/addresses/${addressId}/`, { method: "DELETE" });
      toast.success("Address deleted.");
      if (editingAddressId === addressId) {
        resetAddressForm();
      }
      loadAddresses();
    } catch (err: any) {
      toast.error(err?.message || "Unable to delete address.");
    }
  };

  const markNotificationRead = async (notificationId: number) => {
    try {
      await fetchJSON(`/api/account/notifications/${notificationId}/read/`, { method: "POST" });
      setNotifications((prev) => prev.map((row) => (row.id === notificationId ? { ...row, is_read: true } : row)));
      setNotificationsUnread((prev) => Math.max(0, prev - 1));
    } catch {
      toast.error("Unable to update notification.");
    }
  };

  const markAllNotificationsRead = async () => {
    try {
      await fetchJSON("/api/account/notifications/mark-all-read/", { method: "POST" });
      setNotifications((prev) => prev.map((row) => ({ ...row, is_read: true })));
      setNotificationsUnread(0);
    } catch {
      toast.error("Unable to update notifications.");
    }
  };

  const markMailboxRead = async (messageId: number) => {
    try {
      await fetchJSON(`/api/account/mailbox/${messageId}/read/`, { method: "POST" });
      setMailbox((prev) => prev.map((row) => (row.id === messageId ? { ...row, is_read: true } : row)));
      setMailboxUnread((prev) => Math.max(0, prev - 1));
    } catch {
      toast.error("Unable to update mailbox message.");
    }
  };

  const markAllMailboxRead = async () => {
    try {
      await fetchJSON("/api/account/mailbox/mark-all-read/", { method: "POST" });
      setMailbox((prev) => prev.map((row) => ({ ...row, is_read: true })));
      setMailboxUnread(0);
    } catch {
      toast.error("Unable to update mailbox.");
    }
  };

  const renderSectionContent = () => {
    if (activeSection === "profile") {
      return (
        <form className="space-y-6">
          <div className="flex items-center gap-6">
            <div className="h-20 w-20 rounded-full bg-primary/20 flex items-center justify-center">
              <User className="h-10 w-10 text-primary" />
            </div>
            <Button variant="outline">Change Photo</Button>
          </div>

          <div className="grid md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>First Name</Label>
              <Input defaultValue="John" />
            </div>
            <div className="space-y-2">
              <Label>Last Name</Label>
              <Input defaultValue="Doe" />
            </div>
            <div className="space-y-2">
              <Label>Email</Label>
              <Input type="email" defaultValue="john@example.com" />
            </div>
            <div className="space-y-2">
              <Label>Username</Label>
              <Input defaultValue={username || ""} />
            </div>
          </div>

          <Button type="button">Save Changes</Button>
        </form>
      );
    }

    if (activeSection === "orders") {
      if (ordersLoading) {
        return <div className="py-6 text-sm text-muted-foreground">Loading orders...</div>;
      }
      if (!orders.length) {
        return <div className="py-6 text-sm text-muted-foreground">No orders yet.</div>;
      }
      return (
        <div className="space-y-4">
          {orders.map((order) => {
            const payment = latestPayment(order);
            return (
              <div key={order.id} className="rounded-lg border border-border p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="font-medium">Order #{order.order_number || order.id}</p>
                    <p className="text-xs text-muted-foreground">
                      {new Date(order.created_at).toLocaleString()}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="font-semibold">{asMoney(order.total)}</p>
                    <p className="text-xs text-muted-foreground">Status: {order.status}</p>
                  </div>
                </div>
                <div className="mt-3 text-sm text-muted-foreground">
                  {order.items?.length || 0} item(s)
                </div>
                {payment && (
                  <div className="mt-2 text-xs text-muted-foreground">
                    Payment: {payment.provider} | {payment.success ? "successful" : "pending"} | {asMoney(payment.amount)}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      );
    }

    if (activeSection === "addresses") {
      return (
        <div className="space-y-6">
          <form onSubmit={saveAddress} className="space-y-4 rounded-lg border border-border p-4">
            <p className="text-sm font-medium">{editingAddressId ? "Edit Address" : "Add New Address"}</p>
            <div className="space-y-2">
              <Label>Full Name</Label>
              <Input
                value={addressForm.full_name}
                onChange={(e) => setAddressForm({ ...addressForm, full_name: e.target.value })}
                required
              />
            </div>
            <div className="space-y-2">
              <Label>Address Line 1</Label>
              <Input
                value={addressForm.line1}
                onChange={(e) => setAddressForm({ ...addressForm, line1: e.target.value })}
                required
              />
            </div>
            <div className="space-y-2">
              <Label>Address Line 2</Label>
              <Input
                value={addressForm.line2}
                onChange={(e) => setAddressForm({ ...addressForm, line2: e.target.value })}
              />
            </div>
            <div className="grid md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>City</Label>
                <Input
                  value={addressForm.city}
                  onChange={(e) => setAddressForm({ ...addressForm, city: e.target.value })}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label>State/Region</Label>
                <Input
                  value={addressForm.state}
                  onChange={(e) => setAddressForm({ ...addressForm, state: e.target.value })}
                />
              </div>
            </div>
            <div className="grid md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Postal Code</Label>
                <Input
                  value={addressForm.postal_code}
                  onChange={(e) => setAddressForm({ ...addressForm, postal_code: e.target.value })}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label>Country</Label>
                <Input
                  value={addressForm.country}
                  onChange={(e) => setAddressForm({ ...addressForm, country: e.target.value })}
                  required
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Phone</Label>
              <Input
                value={addressForm.phone}
                onChange={(e) => setAddressForm({ ...addressForm, phone: e.target.value })}
              />
            </div>
            <div className="flex gap-3">
              <Button type="submit">{editingAddressId ? "Update Address" : "Save Address"}</Button>
              {editingAddressId && (
                <Button type="button" variant="outline" onClick={resetAddressForm}>
                  Cancel
                </Button>
              )}
            </div>
          </form>

          <div className="space-y-3">
            {addressesLoading && <div className="text-sm text-muted-foreground">Loading addresses...</div>}
            {!addressesLoading && !addresses.length && (
              <div className="text-sm text-muted-foreground">No saved addresses yet.</div>
            )}
            {addresses.map((address) => (
              <div key={address.id} className="rounded-lg border border-border p-4">
                <p className="font-medium">{address.full_name}</p>
                <p className="text-sm text-muted-foreground break-words">
                  {address.line1}
                  {address.line2 ? `, ${address.line2}` : ""}, {address.city}, {address.state || ""} {address.postal_code}, {address.country}
                </p>
                {address.phone && <p className="text-xs text-muted-foreground mt-1">{address.phone}</p>}
                <div className="mt-3 flex gap-2">
                  <Button type="button" size="sm" variant="outline" onClick={() => editAddress(address)}>
                    Edit
                  </Button>
                  <Button type="button" size="sm" variant="outline" onClick={() => deleteAddress(address.id)}>
                    Delete
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      );
    }

    if (activeSection === "payments") {
      if (ordersLoading) {
        return <div className="py-6 text-sm text-muted-foreground">Loading payment records...</div>;
      }
      const paymentRows = orders.flatMap((order) =>
        (order.transactions || []).map((txn) => ({
          ...txn,
          order_number: order.order_number || String(order.id),
          order_status: order.status,
        }))
      );
      if (!paymentRows.length) {
        return <div className="py-6 text-sm text-muted-foreground">No payment records yet.</div>;
      }
      return (
        <div className="space-y-3">
          {paymentRows
            .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
            .map((txn) => (
              <div key={txn.id} className="rounded-lg border border-border p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="font-medium">{txn.provider} payment</p>
                    <p className="text-xs text-muted-foreground">
                      Order #{txn.order_number} | {txn.order_status}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="font-semibold">{asMoney(txn.amount)}</p>
                    <p className="text-xs text-muted-foreground">{txn.success ? "successful" : "pending"}</p>
                  </div>
                </div>
                <p className="mt-2 text-xs text-muted-foreground break-all">
                  Transaction ID: {txn.provider_transaction_id || "not available"}
                </p>
              </div>
            ))}
        </div>
      );
    }

    if (activeSection === "notifications") {
      if (notificationsLoading) {
        return <div className="py-6 text-sm text-muted-foreground">Loading notifications...</div>;
      }
      if (!notifications.length) {
        return <div className="py-6 text-sm text-muted-foreground">No notifications yet.</div>;
      }
      return (
        <div className="space-y-3">
          <div className="flex items-center justify-end">
            <Button type="button" variant="outline" size="sm" onClick={markAllNotificationsRead}>
              Mark all as read
            </Button>
          </div>
          {notifications.map((row) => (
            <div key={row.id} className={`rounded-lg border p-4 ${row.is_read ? "border-border" : "border-primary/40 bg-primary/5"}`}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-medium">{row.title}</p>
                  <p className="text-sm text-muted-foreground mt-1 break-words">{row.message}</p>
                  <p className="text-xs text-muted-foreground mt-2">{new Date(row.created_at).toLocaleString()}</p>
                </div>
                {!row.is_read && (
                  <Button type="button" variant="outline" size="sm" onClick={() => markNotificationRead(row.id)}>
                    Mark read
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      );
    }

    if (activeSection === "mailbox") {
      if (mailboxLoading) {
        return <div className="py-6 text-sm text-muted-foreground">Loading mailbox...</div>;
      }
      if (!mailbox.length) {
        return <div className="py-6 text-sm text-muted-foreground">No mailbox messages yet.</div>;
      }
      return (
        <div className="space-y-3">
          <div className="flex items-center justify-end">
            <Button type="button" variant="outline" size="sm" onClick={markAllMailboxRead}>
              Mark all as read
            </Button>
          </div>
          {mailbox.map((row) => (
            <div key={row.id} className={`rounded-lg border p-4 ${row.is_read ? "border-border" : "border-primary/40 bg-primary/5"}`}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-medium">{row.subject}</p>
                  <p className="text-sm text-muted-foreground mt-1 whitespace-pre-wrap break-words">{row.body}</p>
                  <p className="text-xs text-muted-foreground mt-2">
                    {new Date(row.created_at).toLocaleString()} | {row.category}
                  </p>
                </div>
                {!row.is_read && (
                  <Button type="button" variant="outline" size="sm" onClick={() => markMailboxRead(row.id)}>
                    Mark read
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      );
    }

    return (
      <div className="py-6 text-sm text-muted-foreground">
        {sectionMeta[activeSection].title} is ready for integration.
      </div>
    );
  };

          return (
    <Layout>
      <div className="bg-secondary/30 py-8">
        <div className="container mx-auto px-4">
          <nav className="breadcrumb mb-4">
            <Link to="/">Home</Link>
            <ChevronDown className="h-4 w-4 rotate-[-90deg]" />
            <span className="text-foreground">Account</span>
          </nav>
          <h1 className="font-serif text-3xl md:text-4xl font-bold text-foreground">
            My Account
          </h1>
        </div>
      </div>

      <div className="container mx-auto px-4 py-8 md:py-12">
        <div className="grid lg:grid-cols-4 gap-6 lg:gap-8">
          {/* Desktop Sidebar */}
          <div className="hidden lg:block lg:col-span-1">
            <nav className="space-y-2">
              {menuItems.map((item) => (
                <button
                  key={item.id}
                  onClick={() => setActiveSection(item.id)}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                    activeSection === item.id
                      ? "bg-primary text-primary-foreground"
                      : "hover:bg-secondary"
                  }`}
                >
                  <item.icon className="h-5 w-5" />
                  {item.label}
                </button>
              ))}
              <button
                onClick={async () => { await logout(); toast.success('Logged out'); }}
                className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-destructive hover:bg-destructive/10 transition-colors"
              >
                <LogOut className="h-5 w-5" />
                Log Out
              </button>
            </nav>
          </div>

          {/* Main Content */}
          <div className="lg:col-span-3 space-y-4">
            {/* Mobile Account Header */}
            <div className="lg:hidden rounded-xl border border-border bg-card p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">Signed in as</p>
                  <p className="text-base font-semibold truncate max-w-[12rem]">{username || "Account User"}</p>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={async () => { await logout(); toast.success("Logged out"); }}
                  className="text-destructive border-destructive/30 hover:bg-destructive/10"
                >
                  <LogOut className="h-4 w-4 mr-2" />
                  Log Out
                </Button>
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                <span className="rounded-full bg-secondary px-2 py-1 max-w-full break-words">Unread notifications: {notificationsUnread}</span>
                <span className="rounded-full bg-secondary px-2 py-1 max-w-full break-words">Unread mailbox: {mailboxUnread}</span>
              </div>
            </div>

            {/* Mobile Section Switcher */}
            <div className="lg:hidden w-full overflow-x-auto pb-1">
              <div className="inline-flex min-w-max gap-2">
                {menuItems.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => setActiveSection(item.id)}
                    className={`inline-flex items-center gap-2 whitespace-nowrap rounded-full border px-3 py-2 text-sm transition-colors ${
                      activeSection === item.id
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-border bg-card text-foreground hover:bg-secondary"
                    }`}
                  >
                    <item.icon className="h-4 w-4" />
                    <span>{item.label}</span>
                  </button>
                ))}
              </div>
            </div>

            <Card>
              <CardHeader>
                <CardTitle>{sectionMeta[activeSection].title}</CardTitle>
                <CardDescription>{sectionMeta[activeSection].description}</CardDescription>
              </CardHeader>
              <CardContent>{renderSectionContent()}</CardContent>
            </Card>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default Account;
