import { createRoot } from "react-dom/client";
import PaymentLink from "./pages/PaymentLink";

const container = document.getElementById("payment-link-page");
if (container) createRoot(container).render(<PaymentLink />);
