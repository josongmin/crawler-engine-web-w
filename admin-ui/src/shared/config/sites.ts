/* ── Site Definitions ─────────────────────────────────
 *
 * Each site has a unique ID, metadata, and a list of
 * crawl operations it supports. Operations map 1:1 to
 * "one-click" actions in the Site Hub UI.
 *
 * When the backend API is connected, site capabilities
 * will be fetched from /api/sites/{id}/capabilities.
 * Until then, this static config drives the UI.
 * ──────────────────────────────────────────────────── */

export type OperationType = "search" | "detail" | "review" | "list";

export interface SiteOperation {
  /** Unique within a site, used to match jobs and rules */
  id: string;
  /** Human-readable name shown on the card */
  name: string;
  /** Determines icon and color of the card */
  type: OperationType;
  /** One-liner describing the action */
  description: string;
  /** Linked crawl rule ID (if configured) */
  ruleId?: string;
  /** Default item limit for quick-run */
  defaultLimit: number;
}

export interface SiteDefinition {
  /** Machine name, used in URLs and API paths */
  id: string;
  /** Display name */
  name: string;
  /** Primary domain */
  domain: string;
  /** Base URL for the site */
  url: string;
  /** Tailwind color palette key for theming (e.g. "rose") */
  themeColor: string;
  /** Available crawl operations */
  operations: SiteOperation[];
  /** Whether Request Kit export is supported */
  supportsRequestKit: boolean;
  /** Whether paste-auth (cookie injection) is supported */
  supportsPasteAuth: boolean;
}

// ── Site Registry ──────────────────────────────────────

export const SITES: SiteDefinition[] = [
  {
    id: "burghound",
    name: "Burghound",
    domain: "burghound.com",
    url: "https://www.burghound.com",
    themeColor: "rose",
    operations: [
      {
        id: "search-all",
        name: "Search All",
        type: "search",
        description: "Search and extract wine tasting notes from the database",
        ruleId: "r1",
        defaultLimit: 50,
      },
      {
        id: "wine-detail",
        name: "Wine Detail",
        type: "detail",
        description: "Extract individual wine tasting note details",
        ruleId: "r2",
        defaultLimit: 10,
      },
    ],
    supportsRequestKit: true,
    supportsPasteAuth: true,
  },
  {
    id: "vivino",
    name: "Vivino",
    domain: "vivino.com",
    url: "https://www.vivino.com",
    themeColor: "violet",
    operations: [
      {
        id: "search",
        name: "Wine Search",
        type: "search",
        description: "Search wines by name, region, or grape variety",
        defaultLimit: 100,
      },
      {
        id: "wine-detail",
        name: "Wine Page",
        type: "detail",
        description: "Extract wine details, ratings, and price info",
        defaultLimit: 10,
      },
      {
        id: "reviews",
        name: "User Reviews",
        type: "review",
        description: "Extract user reviews and community ratings",
        defaultLimit: 50,
      },
    ],
    supportsRequestKit: true,
    supportsPasteAuth: true,
  },
  {
    id: "wine-searcher",
    name: "Wine-Searcher",
    domain: "wine-searcher.com",
    url: "https://www.wine-searcher.com",
    themeColor: "amber",
    operations: [
      {
        id: "search",
        name: "Price Search",
        type: "search",
        description: "Search wines and compare prices across merchants",
        defaultLimit: 100,
      },
      {
        id: "wine-detail",
        name: "Wine Detail",
        type: "detail",
        description: "Extract wine info, average price, and price history",
        defaultLimit: 10,
      },
      {
        id: "merchant-list",
        name: "Merchant Offers",
        type: "list",
        description: "Extract merchant listings and offer prices for a wine",
        defaultLimit: 20,
      },
    ],
    supportsRequestKit: true,
    supportsPasteAuth: true,
  },
];

// ── Helpers ────────────────────────────────────────────

export function getSiteById(id: string): SiteDefinition | undefined {
  return SITES.find((s) => s.id === id);
}
