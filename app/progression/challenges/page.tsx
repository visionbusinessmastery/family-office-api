"use client";

import { useEffect, useState } from "react";
import AuthExperienceShell from "@/components/AuthExperienceShell";
import CockpitBackLink from "@/components/CockpitBackLink";
import { apiRequest } from "@/lib/api";
import { MetricCard, WealthToast } from "@/components/ui/WealthUI";
import type { ProductContext, ProductMission } from "@/lib/types";

const fallbackMissions: ProductMission[] = [
  {
    key: "complete_finances",
    title: "Clarifier les fondations",
    description: "Ajoute revenus, charges, epargne et dettes pour enrichir le contexte backend.",
    xp: 120,
    module: "Finances",
  },
  {
    key: "add_first_asset",
    title: "Ajouter un premier actif",
    description: "Un actif rend ton allocation et tes opportunités plus pertinentes.",
    xp: 180,
    module: "Investments",
  },
  {
    key: "review_opportunities",
    title: "Lire les opportunités",
    description: "Passe en revue les signaux détectés et choisis une action simple.",
    xp: 90,
    module: "Opportunity Center",
  },
];

export default function ChallengesPage() {
  const [product, setProduct] = useState<ProductContext | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      window.location.href = "/login";
      return;
    }
    apiRequest<ProductContext>("/product/context", token)
      .then(setProduct)
      .catch((error) =>
        setToast(error instanceof Error ? error.message : "Progression indisponible.")
      );
  }, []);

  const missions = product?.missions?.length ? product.missions : fallbackMissions;
  const xp = product?.progression?.xp || 0;

  return (
    <AuthExperienceShell fullScreen>
      <WealthToast message={toast} type="error" onClose={() => setToast(null)} />
      <main className="relative z-10 mx-auto min-h-screen max-w-6xl px-5 py-24 text-white">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs uppercase tracking-widest text-[#3fa9f5]">
              Progression
            </p>
            <h1 className="mt-2 text-3xl font-black sm:text-5xl">
              Défis, badges et récompenses.
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-gray-300">
              Comprends pourquoi chaque mission compte, ce qu’elle débloque et
              comment elle améliore ton cockpit.
            </p>
          </div>
          <CockpitBackLink />
        </div>

        <section className="grid gap-3 sm:grid-cols-4">
          <MetricCard label="XP" value={xp} tone="primary" />
          <MetricCard label="Niveau" value={product?.progression?.level || "Builder"} />
          <MetricCard label="Progression" value={`${product?.progression?.progress_percent || 0}%`} tone="success" />
          <MetricCard label="Missions" value={missions.length} />
        </section>

        <section className="mt-6 grid gap-4 lg:grid-cols-3">
          {missions.map((mission) => (
            <article
              key={mission.key}
              className="rounded-2xl border border-white/10 bg-black/45 p-5 shadow-2xl backdrop-blur-xl transition hover:-translate-y-0.5 hover:border-[#3fa9f5]/40"
            >
              <p className="text-xs uppercase tracking-widest text-[#3fa9f5]">
                {mission.module || "WHITE ROCK"}
              </p>
              <h2 className="mt-2 text-xl font-black">{mission.title}</h2>
              <p className="mt-3 text-sm leading-relaxed text-gray-300">
                {mission.description}
              </p>
              <div className="mt-4 rounded-xl border border-emerald-300/20 bg-emerald-300/10 p-3">
                <p className="text-xs uppercase tracking-widest text-emerald-200">
                  Récompense
                </p>
                <p className="mt-1 text-sm font-bold text-white">
                  +{mission.xp || 80} XP · meilleur contexte backend
                </p>
              </div>
              <p className="mt-4 text-xs leading-relaxed text-gray-500">
                Impact : score plus fiable, modules mieux priorisés et
                opportunités plus adaptées.
              </p>
            </article>
          ))}
        </section>
      </main>
    </AuthExperienceShell>
  );
}
