"use client";

import { useEffect, useMemo, useState } from "react";
import AuthExperienceShell from "@/components/AuthExperienceShell";
import CockpitBackLink from "@/components/CockpitBackLink";
import { apiRequest } from "@/lib/api";
import { MetricCard, WealthToast } from "@/components/ui/WealthUI";
import type { CategoryOpportunityData, CategoryOpportunity } from "@/lib/types";

const categoryLabel: Record<string, string> = {
  real_estate: "Immobilier",
  stocks: "Actions",
  etf: "ETF",
  crypto: "Crypto",
  commodities: "Commodities",
  crowdfunding: "Crowdfunding",
  private_equity: "Private equity",
  ai_business: "Business assisté",
  business: "Business",
  startup: "Startup",
  franchise: "Franchise",
};

export default function OpportunitiesPage() {
  const [data, setData] = useState<CategoryOpportunityData | null>(null);
  const [filter, setFilter] = useState("all");
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      window.location.href = "/login";
      return;
    }

    apiRequest<CategoryOpportunityData>("/intelligence/category-opportunities", token)
      .then(setData)
      .catch((error) =>
        setToast(error instanceof Error ? error.message : "Opportunités indisponibles.")
      );
  }, []);

  const categories = useMemo(() => data?.categories || [], [data?.categories]);
  const filtered = useMemo(
    () => categories.filter((item) => filter === "all" || item.key === filter),
    [categories, filter]
  );
  const total = categories.reduce((sum, item) => sum + Number(item.count || 0), 0);

  return (
    <AuthExperienceShell fullScreen>
      <WealthToast message={toast} type="error" onClose={() => setToast(null)} />
      <main className="relative z-10 mx-auto min-h-screen max-w-6xl px-5 py-24 text-white">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs uppercase tracking-widest text-[#3fa9f5]">
              Opportunity Center
            </p>
            <h1 className="mt-2 text-3xl font-black sm:text-5xl">
              Toutes les opportunités utiles.
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-gray-300">
              Une vue centralisée des signaux immobilier, investissements,
              business, marchés et patrimoine.
            </p>
          </div>
          <CockpitBackLink />
        </div>

        <section className="grid gap-3 sm:grid-cols-3">
          <MetricCard label="Signaux" value={total} tone="primary" />
          <MetricCard label="Univers" value={categories.length} />
          <MetricCard label="Source" value="Backend signals" />
        </section>

        <section className="mt-6 rounded-2xl border border-white/10 bg-black/45 p-4 backdrop-blur-xl">
          <div className="flex gap-2 overflow-x-auto pb-1">
            <button
              onClick={() => setFilter("all")}
              className={`rounded-xl border px-3 py-2 text-sm font-bold transition ${filter === "all" ? "border-[#3fa9f5]/60 bg-[#3fa9f5]/15 text-white" : "border-white/10 bg-white/[0.04] text-gray-400"}`}
            >
              Tout
            </button>
            {categories.map((item) => (
              <button
                key={item.key}
                onClick={() => setFilter(item.key || "all")}
                className={`rounded-xl border px-3 py-2 text-sm font-bold transition ${filter === item.key ? "border-[#3fa9f5]/60 bg-[#3fa9f5]/15 text-white" : "border-white/10 bg-white/[0.04] text-gray-400"}`}
              >
                {categoryLabel[item.key || ""] || item.title || item.key}
              </button>
            ))}
          </div>
        </section>

        <section className="mt-6 grid gap-4 lg:grid-cols-2">
          {filtered.map((item: CategoryOpportunity) => (
            <article
              key={item.key || item.title}
              className="rounded-2xl border border-white/10 bg-black/45 p-5 shadow-2xl backdrop-blur-xl transition hover:-translate-y-0.5 hover:border-[#3fa9f5]/40"
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs uppercase tracking-widest text-[#3fa9f5]">
                    {categoryLabel[item.key || ""] || item.key || "Opportunité"}
                  </p>
                  <h2 className="mt-2 text-2xl font-black">
                    {item.title || item.detected_opportunity?.title || "Signal détecté"}
                  </h2>
                </div>
                <span className="rounded-full border border-emerald-300/30 bg-emerald-300/10 px-3 py-1 text-xs font-bold text-emerald-200">
                  {item.count || 0} signal
                </span>
              </div>

              <p className="mt-4 text-sm leading-relaxed text-gray-300">
                {item.analysis || "Le backend attend plus de données pour affiner ce signal."}
              </p>

              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <div className="rounded-xl border border-white/10 bg-white/[0.04] p-4">
                  <p className="text-xs uppercase tracking-widest text-gray-500">Action rapide</p>
                  <p className="mt-2 text-sm text-gray-200">{item.quick_action || "Compléter les données de cet univers."}</p>
                </div>
                <div className="rounded-xl border border-white/10 bg-white/[0.04] p-4">
                  <p className="text-xs uppercase tracking-widest text-gray-500">Potentiel</p>
                  <p className="mt-2 text-sm text-gray-200">{item.detected_opportunity?.potential || item.market_signal?.sentiment || "À qualifier"}</p>
                </div>
              </div>
            </article>
          ))}
        </section>
      </main>
    </AuthExperienceShell>
  );
}
