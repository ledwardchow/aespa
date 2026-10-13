import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, test } from "vitest";

import { SitemapSidePanel } from "./SitemapSidePanel.jsx";

beforeEach(() => localStorage.clear());
afterEach(cleanup);

test("collapses to a rail and remembers the choice", () => {
  const { unmount } = render(
    <SitemapSidePanel>
      <p>Users</p>
    </SitemapSidePanel>,
  );
  expect(screen.getByText("Users")).toBeTruthy();

  fireEvent.click(screen.getByRole("button", { name: "Collapse crawl details" }));
  expect(screen.queryByText("Users")).toBeNull();
  expect(screen.getByRole("button", { name: /Crawl details/ })).toBeTruthy();
  unmount();

  render(
    <SitemapSidePanel>
      <p>Users</p>
    </SitemapSidePanel>,
  );
  expect(screen.queryByText("Users")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: /Crawl details/ }));
  expect(screen.getByText("Users")).toBeTruthy();
  expect(localStorage.getItem("aespa_sitemap_details_open")).toBe("true");
});
