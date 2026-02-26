import { Package } from "lucide-react";

const EmailHeader = () => (
  <div className="bg-primary px-8 py-6 text-center">
    <div className="flex items-center justify-center gap-2">
      <Package className="h-6 w-6 text-brand-gold" />
      <h1 className="font-display text-2xl font-semibold tracking-widest text-primary-foreground uppercase">
        De-Rukkies Collection
      </h1>
    </div>
  </div>
);

export default EmailHeader;
