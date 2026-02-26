import EmailHeader from "./EmailHeader";
import EmailFooter from "./EmailFooter";
import EmailButton from "./EmailButton";
import { UserCheck } from "lucide-react";

const SignupVerificationEmail = () => (
  <div className="max-w-[600px] mx-auto bg-card shadow-xl overflow-hidden">
    <EmailHeader />

    <div className="px-8 py-10 text-center">
      <div className="w-14 h-14 rounded-full bg-brand-gold/20 flex items-center justify-center mx-auto mb-4">
        <UserCheck className="h-7 w-7 text-brand-gold" />
      </div>
      <h3 className="font-display text-2xl text-foreground mb-2">Verify Your Email</h3>
      <p className="text-muted-foreground font-body text-sm">One last step to get started</p>
      <div className="w-12 h-0.5 bg-brand-gold mx-auto mt-4" />
    </div>

    <div className="px-8 pb-8">
      <p className="text-muted-foreground font-body text-sm leading-relaxed mb-6">
        Thanks for signing up at <strong className="text-foreground">De-Rukkies Collection</strong>! 
        Please verify your email address by clicking the button below or entering the verification code.
      </p>

      {/* OTP Code */}
      <div className="bg-secondary rounded p-6 mb-6 text-center">
        <p className="font-body text-xs text-muted-foreground uppercase tracking-widest mb-3">Your Verification Code</p>
        <div className="flex items-center justify-center gap-2">
          {["4", "8", "2", "9", "1", "6"].map((digit, i) => (
            <div
              key={i}
              className="w-10 h-12 rounded bg-card border border-border flex items-center justify-center font-display text-xl font-bold text-foreground"
            >
              {digit}
            </div>
          ))}
        </div>
        <p className="font-body text-xs text-muted-foreground mt-3">Code expires in 30 minutes</p>
      </div>

      <div className="text-center mb-6">
        <p className="font-body text-xs text-muted-foreground mb-4">Or click the button to verify instantly:</p>
        <EmailButton>Verify My Email</EmailButton>
      </div>

      <div className="border-t border-border pt-5">
        <p className="font-body text-xs text-muted-foreground leading-relaxed text-center">
          If you didn't create an account with De-Rukkies Collection, you can safely ignore this email. 
          This link will expire in 24 hours.
        </p>
      </div>
    </div>

    <EmailFooter />
  </div>
);

export default SignupVerificationEmail;
