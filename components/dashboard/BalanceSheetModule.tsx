"use client";

import type { FinanceOverviewData } from "@/lib/types";

const money = new Intl.NumberFormat("fr-FR", {
  maximumFractionDigits: 0,
});

const n = (value?: number | string | null) => Number(value || 0);

type BalanceSheetModuleProps = {
  overview?: FinanceOverviewData | null;
};

export default function BalanceSheetModule({
  overview,
}: BalanceSheetModuleProps) {
  const totals = overview?.totals || {};
  const ratios = overview?.ratios || {};

  return (
    <div className="space-y-5">
      <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-5">
        <p className="text-xs font-bold uppercase tracking-widest text-[#f7d154]">
          Bilan long terme
        </p>
        <h3 className="mt-2 text-3xl font-black text-white">
          Epargne, dettes et liquidite
        </h3>
        <p className="mt-3 max-w-3xl text-sm leading-relaxed text-gray-300">
          Lecture des stocks financiers renseignes. Le cashflow reste dans la
          page Finances, le futur reste dans l'Accueil.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-2xl border border-emerald-400/20 bg-emerald-400/10 p-5">
          <p className="mb-2 text-sm text-gray-400">Patrimoine liquide</p>
          <h3 className="text-2xl font-black text-emerald-300">
            {money.format(n(totals.savings))} EUR
          </h3>
        </div>

        <div className="rounded-2xl border border-[#3fa9f5]/20 bg-[#3fa9f5]/10 p-5">
          <p className="mb-2 text-sm text-gray-400">Mois de securite</p>
          <h3 className="text-2xl font-black text-[#3fa9f5]">
            {n(ratios.liquid_months).toFixed(1)}
          </h3>
          <p className="mt-2 text-xs text-gray-400">base charges mensuelles</p>
        </div>

        <div className="rounded-2xl border border-amber-300/20 bg-amber-300/10 p-5">
          <p className="mb-2 text-sm text-gray-400">Dette totale</p>
          <h3 className="text-2xl font-black text-amber-200">
            {money.format(n(totals.debt))} EUR
          </h3>
        </div>

        <div className="rounded-2xl border border-white/10 bg-black/20 p-5">
          <p className="mb-2 text-sm text-gray-400">Dette / revenus</p>
          <h3 className="text-2xl font-black text-white">
            {n(ratios.debt_to_income).toFixed(2)}x
          </h3>
        </div>
      </div>
    </div>
  );
}
