import { registerServiceWorker } from "./app/registerServiceWorker.ts";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./styles/index.css";
import App from "./app/App.jsx";
import { AuthenticationGate } from "./app/AuthenticationGate.tsx";
import { installAuthFetch } from "./shared/auth/session.ts";

installAuthFetch();

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <AuthenticationGate>
      <App />
    </AuthenticationGate>
  </StrictMode>,
);

registerServiceWorker();
