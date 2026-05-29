"use client";

import type { ProductContext } from "@/lib/types";

type DailyWealthCheckProps = {
  score: number;
  gain: number;
  product?: ProductContext | null;
  opportunitiesCount?: number;
  onOpenStatus?: () => void;
  onOpenAction?: () => void;
  onOpenOpportunities?: () => void;
};

const money = new Intl.NumberFormat("fr-FR", {
  maximumFractionDigits: 0,
});

export default function DailyWealthCheck({
  score,
  gain,
  product,
  opportunitiesCount = 0,
  onOpenStatus,
  onOpenAction,
  onOpenOpportunities,
}: DailyWealthCheckProps) {
  const mission = product?.missions?.[0];
  const completion = product?.data_profile?.completion_percent || 0;
  const level = product?.progression?.level || "Builder";
  const gainLabel = `${gain >= 0 ? "+" : ""}${money.format(gain)} EUR`;

  return (
    <section className="rounded-2xl border border-[#3fa9f5]/20 bg-gradient-to-br from-[#07111c] via-black to-[#101923] p-5">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
        <div className="max-w-2xl">
          <p className="text-xs uppercase tracking-widest text-[#3fa9f5]">
            Daily Insight
          </p>
          <h2 className="mt-2 text-2xl font-black text-white">
            Tu avances vers une situation plus claire.
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-gray-400">
            Le cockpit garde le cap: progression, point d&apos;attention et
            prochain signal utile, sans bruit inutile.
          </p>
        </div>

        <div className="grid grid-cols-3 gap-2 text-center sm:min-w-[420px]">
          <div className="rounded-xl border border-white/10 bg-white/[0.04] p-3">
            <p className="text-xs text-gray-500">Score</p>
            <p className="mt-1 text-lg font-black text-white">{score}/100</p>
          </div>
          <div className="rounded-xl border border-white/10 bg-white/[0.04] p-3">
            <p className="text-xs text-gray-500">Progression</p>
            <p className="mt-1 text-lg font-black text-[#3fa9f5]">{completion}%</p>
          </div>
          <div className="rounded-xl border border-white/10 bg-white/[0.04] p-3">
            <p className="text-xs text-gray-500">Momentum</p>
            <p className={gain >= 0 ? "mt-1 text-lg font-black text-emerald-300" : "mt-1 text-lg font-black text-red-300"}>
              {gainLabel}
            </p>
          </div>
        </div>
      </div>

      <div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-3">
        <button
          type="button"
          onClick={onOpenStatus}
          className="rounded-xl border border-white/10 bg-black/30 p-4 text-left transition hover:border-[#3fa9f5]/40 hover:bg-white/[0.04]"
        >
          <p className="text-xs uppercase tracking-widest text-gray-500">
            Statut
          </p>
          <p className="mt-2 font-semibold text-white">{level}</p>
          <p className="mt-1 text-xs text-gray-400">
            Le niveau reflete ton activite et ta qualite de pilotage, pas
            seulement ton abonnement.
          </p>
        </button>

        <button
          type="button"
          onClick={onOpenAction}
          className="rounded-xl border border-white/10 bg-black/30 p-4 text-left transition hover:border-[#3fa9f5]/40 hover:bg-white/[0.04]"
        >
          <p className="text-xs uppercase tracking-widest text-gray-500">
            Action du jour
          </p>
          <p className="mt-2 font-semibold text-white">
            {mission?.title || "Ajouter une donnee qui manque"}
          </p>
          <p className="mt-1 text-xs text-gray-400">
            {mission?.description ||
              "Une petite action suffit pour rendre ton cockpit plus precis demain."}
          </p>
        </button>

        <button
          type="button"
          onClick={onOpenOpportunities}
          className="rounded-xl border border-white/10 bg-black/30 p-4 text-left transition hover:border-[#3fa9f5]/40 hover:bg-white/[0.04]"
        >
          <p className="text-xs uppercase tracking-widest text-gray-500">
            Signal
          </p>
          <p className="mt-2 font-semibold text-white">
            {opportunitiesCount > 0
              ? `${opportunitiesCount} opportunite(s) a regarder`
              : "Aucun signal urgent"}
          </p>
          <p className="mt-1 text-xs text-gray-400">
            Priorise ce qui peut reduire le risque ou accelerer ta trajectoire.
          </p>
        </button>
      </div>
    </section>
  );
}
