"use client";

import { useState } from "react";
import type {
  CommandCenter,
  Opportunity,
  OpportunityData,
} from "@/lib/types";

type OpportunitiesModuleProps = {
  commandCenter: CommandCenter | null;
  plan?: string | null;
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

const normalize = (value?: string | null) => (value || "").toLowerCase();

const opportunitySummary = (opportunity: Opportunity) =>
  opportunity.why_this_opportunity ||
  opportunity.description ||
  opportunity.impact_potential ||
  "";

const opportunityText = (opportunity: Opportunity) =>
  normalize(
    [
      opportunity.type,
      opportunity.title,
      opportunity.description,
      opportunity.why_this_opportunity,
      opportunity.next_action,
    ]
      .filter(Boolean)
      .join(" ")
  );

const classifyOpportunity = (opportunity: Opportunity) => {
  const text = opportunityText(opportunity);

  if (
    /business|agence|agency|ugc|revenu|income|cashflow|client|freelance|side|marketing/.test(
      text
    )
  ) {
    return {
      label: "Income Building",
      description: "Creation de revenus",
      className: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
    };
  }

  if (
    /crypto|bitcoin|btc|solana|trading|swing|forex|speculat|opportunistic/.test(
      text
    )
  ) {
    return {
      label: "Opportunistic",
      description: "Signal tactique",
      className: "border-orange-400/30 bg-orange-400/10 text-orange-200",
    };
  }

  return {
    label: "Wealth Building",
    description: "Construction long terme",
    className: "border-[#f7d154]/30 bg-[#f7d154]/10 text-[#f7d154]",
  };
};

const difficultyRank = (opportunity: Opportunity) => {
  const value = normalize(
    opportunity.difficulty || opportunity.profile_compatibility || ""
  );

  if (/advanced|expert|complex|hard|eleve|difficile/.test(value)) return 3;
  if (/medium|intermediate|moyen|modere/.test(value)) return 2;
  if (/easy|simple|low|faible|debutant/.test(value)) return 1;

  return 1;
};

const allowedDifficultyRank = (plan?: string | null) => {
  const normalizedPlan = normalize(plan);
  if (/elite|liberty|legacy|dynasty/.test(normalizedPlan)) return 3;
  if (/gold/.test(normalizedPlan)) return 2;
  return 1;
};

const isStrategySignal = (opportunity: Opportunity) =>
  /strategie|strategy|plan|10 ans|liberte financiere|freedom/.test(
    opportunityText(opportunity)
  );

export default function OpportunitiesModule({
  commandCenter,
  plan,
}: OpportunitiesModuleProps) {
  const [selectedOpportunity, setSelectedOpportunity] =
    useState<Opportunity | null>(null);
  const [showMore, setShowMore] = useState(false);
  const opportunities = normalizeOpportunities(commandCenter?.opportunities);
  const detectedCount =
    typeof commandCenter?.opportunities_count === "number"
      ? commandCenter.opportunities_count
      : opportunities.length;
  const maxDifficulty = allowedDifficultyRank(plan);
  const strategySignals = opportunities.filter(isStrategySignal);
  const actionableOpportunities = opportunities.filter(
    (opportunity) => !isStrategySignal(opportunity)
  );
  const planAlignedOpportunities = actionableOpportunities.filter(
    (opportunity) => difficultyRank(opportunity) <= maxDifficulty
  );
  const visibleBase =
    planAlignedOpportunities.length > 0
      ? planAlignedOpportunities
      : actionableOpportunities;
  const visibleOpportunities = visibleBase.slice(0, 3);
  const topOpportunity = visibleOpportunities[0];
  const secondaryOpportunities = visibleOpportunities.slice(1, 3);
  const restOpportunities = actionableOpportunities.filter(
    (opportunity) => !visibleOpportunities.includes(opportunity)
  );
  const nextBestAction =
    topOpportunity?.next_action ||
    topOpportunity?.why_now ||
    topOpportunity?.impact_potential;

  const classificationCounts = actionableOpportunities.reduce<
    Record<string, number>
  >((acc, opportunity) => {
    const label = classifyOpportunity(opportunity).label;
    acc[label] = (acc[label] || 0) + 1;
    return acc;
  }, {});

  const renderOpportunityCard = (
    opportunity: Opportunity,
    index: number,
    variant: "primary" | "standard" = "standard"
  ) => {
    const priority = opportunity.priority || "medium";
    const badgeClass = priorityClasses[priority] || priorityClasses.medium;
    const summary = opportunitySummary(opportunity);
    const lens = classifyOpportunity(opportunity);

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
              {variant === "primary" ? "Priorite du moment" : "Signal priorise"}
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

        <div className="mt-3 flex flex-wrap gap-2">
          <span
            className={`rounded-full border px-3 py-1 text-xs ${lens.className}`}
          >
            {lens.label}
          </span>
          {opportunity.difficulty && (
            <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-gray-300">
              {opportunity.difficulty}
            </span>
          )}
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
          <h2 className="text-2xl font-bold">Intelligence des opportunites</h2>
          <p className="text-sm text-gray-400">
            Les signaux sont priorises pour faire ressortir ce qui merite vraiment ton attention.
          </p>
        </div>

        <span className="text-sm text-[#3fa9f5]">
          Top {visibleOpportunities.length} / {detectedCount} suivis
        </span>
      </div>

      {opportunities.length === 0 ? (
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 text-sm text-gray-400">
          Aucun signal disponible pour le moment.
        </div>
      ) : (
        <div className="space-y-4">
          {nextBestAction && (
            <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-4">
              <p className="text-xs font-bold uppercase tracking-widest text-emerald-300">
                Prochaine meilleure action
              </p>
              <p className="mt-2 text-sm leading-relaxed text-emerald-50">
                {nextBestAction}
              </p>
            </div>
          )}

          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            {["Wealth Building", "Income Building", "Opportunistic"].map(
              (label) => (
                <div
                  key={label}
                  className="rounded-2xl border border-white/10 bg-white/[0.03] p-3"
                >
                  <p className="text-xs uppercase tracking-widest text-gray-500">
                    {label}
                  </p>
                  <p className="mt-1 text-lg font-bold text-white">
                    {classificationCounts[label] || 0}
                  </p>
                </div>
              )
            )}
          </div>

          {topOpportunity && renderOpportunityCard(topOpportunity, 0, "primary")}

          {secondaryOpportunities.length > 0 && (
            <div>
              <div className="mb-2 flex items-center justify-between">
                <p className="text-xs font-bold uppercase tracking-widest text-gray-500">
                  Top 3 priorisees
                </p>
              </div>
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                {secondaryOpportunities.map((opportunity, index) =>
                  renderOpportunityCard(opportunity, index + 1)
                )}
              </div>
            </div>
          )}

          {restOpportunities.length > 0 && (
            <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
              <div className="flex items-center justify-between gap-3">
                <p className="text-xs font-bold uppercase tracking-widest text-gray-500">
                  Autres signaux suivis
                </p>
                <button
                  type="button"
                  onClick={() => setShowMore((current) => !current)}
                  className="rounded-full border border-white/10 px-3 py-1 text-xs text-gray-300 hover:border-[#3fa9f5]/50 hover:text-white"
                >
                  {showMore ? "Masquer" : "Voir plus"}
                </button>
              </div>

              {showMore && (
                <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-2">
                  {restOpportunities.map((opportunity, index) =>
                    renderOpportunityCard(opportunity, index + 3)
                  )}
                </div>
              )}
            </div>
          )}

          {strategySignals.length > 0 && (
            <div className="rounded-2xl border border-[#3fa9f5]/20 bg-[#3fa9f5]/10 p-4">
              <p className="text-xs font-bold uppercase tracking-widest text-[#3fa9f5]">
                Strategie long terme
              </p>
              <p className="mt-2 text-sm text-gray-300">
                Ces elements relevent davantage de la trajectoire long terme que
                d'une opportunite immediate.
              </p>
              <div className="mt-3 grid grid-cols-1 gap-3 lg:grid-cols-2">
                {strategySignals.slice(0, 2).map((opportunity, index) =>
                  renderOpportunityCard(opportunity, index, "standard")
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
