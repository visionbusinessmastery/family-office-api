"use client";

import type { CategoryOpportunity } from "@/lib/types";

type OpportunityInsightCardProps = {
  opportunity?: CategoryOpportunity;
  variant?: "card" | "compact";
};

export default function OpportunityInsightCard({
  opportunity,
  variant = "card",
}: OpportunityInsightCardProps) {
  if (!opportunity) return null;
  const signalText =
    opportunity.quick_action ||
    opportunity.detected_opportunity?.title ||
    opportunity.market_signal?.headline ||
    opportunity.analysis;

  if (variant === "compact") {
    return (
      <div className="rounded-full border border-emerald-300/25 bg-emerald-400/10 px-3 py-2 text-xs text-emerald-100">
        <span className="font-bold text-emerald-200">Signal</span>
        {signalText ? <span className="ml-2 text-emerald-50">{signalText}</span> : null}
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-[#3fa9f5]/20 bg-[#3fa9f5]/10 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase text-[#3fa9f5]">
            Opportunite rubrique
          </p>
          <h4 className="font-bold text-white mt-1">
            {opportunity.title || "Rubrique"}
          </h4>
        </div>

        <span className="rounded-full border border-[#3fa9f5]/30 bg-black/30 px-3 py-1 text-xs text-[#3fa9f5]">
          Signal
        </span>
      </div>

      <div className="mt-3 space-y-3 text-sm">
        {opportunity.analysis && (
          <div>
            <p className="text-xs uppercase text-gray-500">Donnee contexte</p>
            <p className="text-gray-300">{opportunity.analysis}</p>
          </div>
        )}

        {opportunity.quick_action && (
          <div>
            <p className="text-xs uppercase text-gray-500">Signal operationnel</p>
            <p className="text-gray-300">{opportunity.quick_action}</p>
          </div>
        )}

        {opportunity.detected_opportunity && (
          <div>
            <p className="text-xs uppercase text-gray-500">
              Opportunite detectee
            </p>
            <p className="font-semibold text-white">
              {opportunity.detected_opportunity.title}
            </p>
            <p className="text-xs text-gray-400">
              {[
                opportunity.detected_opportunity.platform,
                opportunity.detected_opportunity.risk &&
                  `risque ${opportunity.detected_opportunity.risk}`,
                opportunity.detected_opportunity.potential &&
                  `potentiel ${opportunity.detected_opportunity.potential}`,
              ]
                .filter(Boolean)
                .join(" - ")}
            </p>
          </div>
        )}

        {opportunity.market_signal?.headline && (
          <div>
            <p className="text-xs uppercase text-gray-500">Signal marche</p>
            <p className="text-gray-300">
              {opportunity.market_signal.headline}
            </p>
            <p className="text-xs text-gray-500">
              {opportunity.market_signal.source ||
                opportunity.market_signal.query}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
