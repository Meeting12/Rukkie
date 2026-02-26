import EmailHeader from "./EmailHeader";
import EmailFooter from "./EmailFooter";
import EmailButton from "./EmailButton";
import { AlertTriangle } from "lucide-react";

const LoginWarningEmail = () => (
  <div className="max-w-[600px] mx-auto bg-card shadow-xl overflow-hidden">
    <EmailHeader />

    <div className="px-8 py-10 text-center">
      <div className="w-14 h-14 rounded-full bg-destructive/15 flex items-center justify-center mx-auto mb-4">
        <AlertTriangle className="h-7 w-7 text-destructive" />
      </div>
      <h3 className="font-display text-2xl text-foreground mb-2">Unusual Login Detected</h3>
      <p className="text-muted-foreground font-body text-sm">Security Alert for Your Account</p>
      <div className="w-12 h-0.5 bg-destructive mx-auto mt-4" />
    </div>

    <div className="px-8 pb-8">
      <p className="text-muted-foreground font-body text-sm leading-relaxed mb-6">
        We noticed a new sign-in to your <strong className="text-foreground">De-Rukkies Collection</strong> account. 
        If this was you, no action is needed. If not, please secure your account immediately.
      </p>

      <div className="bg-secondary rounded p-5 mb-6 space-y-3">
        {[
          ["Date & Time", "Feb 25, 2026 • 11:47 PM"],
          ["Device", "Chrome on Windows 11"],
          ["IP Address", "102.89.47.***"],
          ["Location", "Lagos, Nigeria"],
        ].map(([label, value]) => (
          <div key={label} className="flex justify-between items-center">
            <span className="font-body text-xs text-muted-foreground">{label}</span>
            <span className="font-body text-sm font-semibold text-secondary-foreground">{value}</span>
          </div>
        ))}
      </div>

      <div className="border border-destructive/30 rounded p-4 mb-8 bg-destructive/5">
        <p className="font-body text-xs text-destructive font-semibold mb-1">⚠️ Wasn't you?</p>
        <p className="font-body text-xs text-muted-foreground leading-relaxed">
          We recommend changing your password right away and enabling two-factor authentication to keep your account safe.
        </p>
      </div>

      <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
        <EmailButton>Secure My Account</EmailButton>
        <EmailButton variant="outline">Change Password</EmailButton>
      </div>
    </div>

    <EmailFooter />
  </div>
);

export default LoginWarningEmail;
