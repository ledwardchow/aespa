import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import App from "./App";
import SitesList from "./pages/SitesList";
import SiteForm from "./pages/SiteForm";
import SettingsPage from "./pages/SettingsPage";

const root = createRoot(document.getElementById("root")!);
root.render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />}>
          <Route index element={<SitesList />} />
          <Route path="sites/new" element={<SiteForm />} />
          <Route path="sites/:id" element={<SiteForm />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
