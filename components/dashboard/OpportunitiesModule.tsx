"use client";

import { useState } from "react";
import type {
  CommandCenter,
  Opportunity,
  OpportunityData,
} from "@/lib/types";

type OpportunitiesModuleProps = {
  commandCenter: CommandCenter | null;
};

const priorityClasses: Record<string, string> = {
  high: "border-red-500/30 bg-red-500/10 text-red-300",
  medium: "border-yellow-500/30 bg-yellow-500/10 text-yellow-300",
  low: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
};

const normalizeOpportunities = (
  opportunities: CommandCenter["opportunities"]
): Opportunity[] => {
  if (Array.isArray(opportunities)) return opportunities;

  return (opportunities as OpportunityData | undefined)?.opportunities || [];
};

const opportunitySummary = (opportunity: Opportunity) =>
  opportunity.why_this_opportunity ||
  opportunity.description ||
  opportunity.impact_potential ||
  "";

export default function OpportunitiesModule({
  commandCenter,
}: OpportunitiesModuleProps) {
  const [selectedOpportunity, setSelectedOpportunity] =
    useState<Opportunity | null>(null);
  const opportunities = normalizeOpportunities(commandCenter?.opportunities);
  const detectedCount =
    typeof commandCenter?.opportunities_count === "number"
      ? commandCenter.opportunities_count
      : opportunities.length;
  const topOpportunity = opportunities[0];
  const strategicOpportunities = opportunities.slice(1, 3);
  const restOpportunities = opportunities.slice(3);

  const renderOpportunityCard = (
    opportunity: Opportunity,
    index: number,
    variant: "primary" | "standard" = "standard"
  ) => {
    const priority = opportunity.priority || "medium";
    const badgeClass = priorityClasses[priority] || priorityClasses.medium;
    const summary = opportunitySummary(opportunity);

    return (
      <button
        type="button"
        key={`${opportunity.type || opportunity.title}-${index}-${variant}`}
        onClick={() => setSelectedOpportunity(opportunity)}
        className={`rounded-2xl border p-4 text-left transition hover:border-[#3fa9f5]/50 ${
          variant === "primary"
            ? "border-[#3fa9f5]/35 bg-[#3fa9f5]/10"
            : "border-white/10 bg-white/5 hover:bg-white/[0.07]"
        }`}
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-bold uppercase tracking-widest text-[#3fa9f5]">
              {variant === "primary" ? "Signal principal" : "Signal"}
            </p>
            <h3 className="mt-2 font-bold text-white">
              {opportunity.title || "Opportunite"}
            </h3>
            {summary && (
              <p className="mt-2 text-sm leading-relaxed text-gray-400">
                {summary}
              </p>
            )}
          </div>

          <span
            className={`shrink-0 rounded-full border px-3 py-1 text-xs uppercase ${badgeClass}`}
          >
            {priority}
          </span>
        </div>

        <div className="mt-4 grid grid-cols-1 gap-2 text-xs sm:grid-cols-2">
          {opportunity.next_action && (
            <div className="rounded-xl border border-white/10 bg-black/25 p-2">
              <p className="text-gray-500">Action</p>
              <p className="mt-1 text-gray-300">{opportunity.next_action}</p>
            </div>
          )}
          {(opportunity.profile_compatibility || opportunity.difficulty) && (
            <div className="rounded-xl border border-white/10 bg-black/25 p-2">
              <p className="text-gray-500">Profil</p>
              <p className="mt-1 text-gray-300">
                {opportunity.profile_compatibility || opportunity.difficulty}
              </p>
            </div>
          )}
        </div>

        {opportunity.premium && (
          <p className="mt-3 text-xs text-yellow-300">Signal premium</p>
        )}
      </button>
    );
  };

  return (
    <section className="bg-zinc-950 border border-white/10 rounded-2xl p-5">
      <div className="flex flex-col gap-1 mb-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold">Opportunites</h2>
          <p className="text-sm text-gray-400">
            Signaux fournis par le backend selon ton profil et ton portefeuille
          </p>
        </div>

        <span className="text-sm text-[#3fa9f5]">
          {detectedCount} detectee
          {detectedCount > 1 ? "s" : ""}
        </span>
      </div>

      {opportunities.length === 0 ? (
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 text-sm text-gray-400">
          Aucun signal disponible pour le moment.
        </div>
      ) : (
        <div className="space-y-4">
          {topOpportunity && renderOpportunityCard(topOpportunity, 0, "primary")}

          {strategicOpportunities.length > 0 && (
            <div>
              <div className="mb-2 flex items-center justify-between">
                <p className="text-xs font-bold uppercase tracking-widest text-gray-500">
                  Autres signaux
                </p>
              </div>
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                {strategicOpportunities.map((opportunity, index) =>
                  renderOpportunityCard(opportunity, index + 1)
                )}
              </div>
            </div>
          )}

          {restOpportunities.length > 0 && (
            <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
              <div>
                <p className="text-xs font-bold uppercase tracking-widest text-gray-500">
                  Signaux supplementaires
                </p>
              </div>

              <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-2">
                {restOpportunities.map((opportunity, index) =>
                  renderOpportunityCard(opportunity, index + 3)
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {selectedOpportunity && (
        <div className="mt-5 rounded-2xl border border-[#3fa9f5]/25 bg-[#3fa9f5]/10 p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-widest text-[#3fa9f5]">
                Detail opportunite
              </p>
              <h3 className="mt-1 text-lg font-bold text-white">
                {selectedOpportunity.title || "Opportunite"}
              </h3>
            </div>
            <button
              type="button"
              onClick={() => setSelectedOpportunity(null)}
              className="rounded-full border border-white/10 px-3 py-1 text-xs text-gray-400 hover:text-white"
            >
              Fermer
            </button>
          </div>
          {opportunitySummary(selectedOpportunity) && (
            <p className="mt-3 text-sm leading-relaxed text-gray-300">
              {opportunitySummary(selectedOpportunity)}
            </p>
          )}
          <div className="mt-4 grid grid-cols-1 gap-3 text-sm sm:grid-cols-3">
            <div className="rounded-xl border border-white/10 bg-black/30 p-3">
              <p className="text-xs text-gray-500">Type</p>
              <p className="mt-1 font-bold text-white">
                {selectedOpportunity.type || "signal"}
              </p>
            </div>
            <div className="rounded-xl border border-white/10 bg-black/30 p-3">
              <p className="text-xs text-gray-500">Priorite</p>
              <p className="mt-1 font-bold text-white">
                {selectedOpportunity.priority || "medium"}
              </p>
            </div>
            <div className="rounded-xl border border-white/10 bg-black/30 p-3">
              <p className="text-xs text-gray-500">Difficulte</p>
              <p className="mt-1 font-bold text-[#3fa9f5]">
                {selectedOpportunity.difficulty || "non renseignee"}
              </p>
            </div>
          </div>
          {(selectedOpportunity.why_now || selectedOpportunity.impact_potential) && (
            <div className="mt-3 grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
              {selectedOpportunity.why_now && (
                <div className="rounded-xl border border-white/10 bg-black/30 p-3">
                  <p className="text-xs text-gray-500">Pourquoi maintenant</p>
                  <p className="mt-1 text-gray-300">{selectedOpportunity.why_now}</p>
                </div>
              )}
              {selectedOpportunity.impact_potential && (
                <div className="rounded-xl border border-white/10 bg-black/30 p-3">
                  <p className="text-xs text-gray-500">Impact potentiel</p>
                  <p className="mt-1 text-gray-300">{selectedOpportunity.impact_potential}</p>
                </div>
              )}
            </div>
          )}
          {selectedOpportunity.next_action && (
            <p className="mt-4 rounded-xl border border-white/10 bg-black/30 p-3 text-sm leading-relaxed text-gray-300">
              {selectedOpportunity.next_action}
            </p>
          )}
        </div>
      )}
    </section>
  );
}
