import { Suspense } from "react";
import { useRoute } from "../shared/navigation/router.js";
import { AppShell } from "./AppShell.jsx";
import { useAppPreferences } from "./useAppPreferences.js";
import { RouteErrorBoundary } from "./RouteErrorBoundary.jsx";
import { routes } from "./routes.js";

export default function App() {
  const route = useRoute();
  const preferences = useAppPreferences();
  const definition = routes[route.name];
  const Component = definition?.Component;
  const { key, ...props } = definition ? definition.props(route, preferences) : {};
  const content = (
    <RouteErrorBoundary key={route.name + ":" + (route.id ?? "")}>
      <Suspense
        fallback={
          <div className="content scroll-content">
            <div className="subtle">Loading…</div>
          </div>
        }
      >
        {Component ? (
          <Component key={key} {...props} />
        ) : (
          <div className="content">
            <h1>Page not found</h1>
            <a href="#/">Return to Sites</a>
          </div>
        )}
      </Suspense>
    </RouteErrorBoundary>
  );
  return route.name === "alice-popout" ? (
    content
  ) : (
    <AppShell section={definition?.section} preferences={preferences}>
      {content}
    </AppShell>
  );
}
