import { Instagram, Facebook, Twitter } from "lucide-react";

const EmailFooter = () => (
  <div className="bg-primary px-8 py-8 text-center">
    <div className="flex items-center justify-center gap-5 mb-5">
      <a href="#" className="text-brand-gold hover:text-primary-foreground transition-colors">
        <Instagram className="h-5 w-5" />
      </a>
      <a href="#" className="text-brand-gold hover:text-primary-foreground transition-colors">
        <Facebook className="h-5 w-5" />
      </a>
      <a href="#" className="text-brand-gold hover:text-primary-foreground transition-colors">
        <Twitter className="h-5 w-5" />
      </a>
    </div>
    <p className="text-sm text-primary-foreground/70 mb-2 font-body">
      © 2026 De-Rukkies Collection. All rights reserved.
    </p>
    <div className="flex items-center justify-center gap-4 text-xs text-primary-foreground/50 font-body">
      <a href="#" className="hover:text-brand-gold transition-colors">Privacy Policy</a>
      <span>•</span>
      <a href="#" className="hover:text-brand-gold transition-colors">Terms of Service</a>
      <span>•</span>
      <a href="#" className="hover:text-brand-gold transition-colors">Unsubscribe</a>
    </div>
    <p className="text-xs text-primary-foreground/40 mt-4 font-body">
      123 Fashion Avenue, Lagos, Nigeria
    </p>
  </div>
);

export default EmailFooter;
