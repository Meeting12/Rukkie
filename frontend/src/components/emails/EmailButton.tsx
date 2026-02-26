interface EmailButtonProps {
  children: React.ReactNode;
  variant?: "primary" | "outline";
}

const EmailButton = ({ children, variant = "primary" }: EmailButtonProps) => {
  const base = "inline-block px-8 py-3 text-sm font-semibold uppercase tracking-widest transition-all duration-200 font-body cursor-pointer";
  const styles = variant === "primary"
    ? "bg-primary text-primary-foreground hover:bg-brand-gold hover:text-accent-foreground"
    : "border-2 border-primary text-primary hover:bg-primary hover:text-primary-foreground";

  return (
    <a href="#" className={`${base} ${styles}`}>
      {children}
    </a>
  );
};

export default EmailButton;
