"use client";

import type {
  CategoryOpportunity,
  VentureAsset,
  VentureAssetData,
  VentureAssetType,
} from "@/lib/types";
import OpportunityInsightCard from "./OpportunityInsightCard";
import { ActionButton, EmptyState, MetricCard } from "@/components/ui/WealthUI";

type Props = {
  data?: VentureAssetData | null;
  onAdd?: (type: VentureAssetType) => void;
  onUpdate?: (asset: VentureAsset) => void;
  onDelete?: (id: number) => void;
  opportunities?: CategoryOpportunity[];
};

const money = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 });
const n = (value?: number | string | null) => Number(value || 0);

const types: Array<{ key: VentureAssetType; label: string }> = [
  { key: "ai_business", label: "Business digital" },
  { key: "business", label: "Business" },
  { key: "startup", label: "Startup" },
  { key: "franchise", label: "Franchise" },
];

export default function VentureAssetsModule({
  data,
  onAdd,
  onUpdate,
  onDelete,
  opportunities = [],
}: Props) {
  const assets = data?.assets || [];
  const totals = data?.totals || {};
  const access = data?.access;
  const canAddAsset = !access || access.is_unlimited || n(access.remaining) > 0;
  const accessLine = access
    ? access.is_unlimited
      ? `${access.depth_label || "Lecture avancee"} - business illimites`
      : `${access.depth_label || "Lecture"} - ${access.count || 0}/${access.limit} business`
    : null;

  return (
    <section className="rounded-2xl border border-white/10 bg-zinc-950 p-5">
      <div className="mb-5">
        <h2 className="text-2xl font-bold">Portfolio Business</h2>
        <p className="text-sm text-gray-400">
          Les actifs que tu possedes ou structures: activites, startups,
          franchises et reprises.
        </p>
        {accessLine && (
          <p className="mt-2 text-xs font-bold uppercase tracking-widest text-emerald-300">
            {accessLine}
          </p>
        )}
      </div>

      <div className="mb-5 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="Chiffre d'affaires"
          value={`${money.format(n(totals.total_revenue))} EUR`}
        />
        <MetricCard
          label="Charges"
          value={`${money.format(n(totals.total_charges))} EUR`}
        />
        <MetricCard
          label="Performance"
          value={`${n(totals.total_result) >= 0 ? "+" : ""}${money.format(n(totals.total_result))} EUR`}
          tone={n(totals.total_result) >= 0 ? "success" : "danger"}
        />
        <MetricCard
          label="Valeur suivie"
          value={`${money.format(n(totals.total_final_value))} EUR`}
          tone="primary"
        />
      </div>

      <div className="mb-5 rounded-2xl border border-amber-300/20 bg-amber-300/10 p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs uppercase tracking-widest text-amber-200">
              Reprise d'entreprise
            </p>
            <h3 className="mt-1 text-lg font-bold text-white">
              Rachat et fonds de commerce
            </h3>
            <p className="mt-1 text-sm text-gray-400">
              Ces volets restent rattaches au portefeuille Business pour
              conserver une lecture investisseur simple.
            </p>
          </div>
          {onAdd && canAddAsset && (
            <div className="flex flex-col gap-2 sm:flex-row">
              <ActionButton onClick={() => onAdd("business")} variant="secondary">
                Rachat / Reprise
              </ActionButton>
              <ActionButton onClick={() => onAdd("business")} variant="secondary">
                Fonds de commerce
              </ActionButton>
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {types.map((type) => {
          const rows = assets.filter((asset) => asset.asset_type === type.key);
          const opportunity = opportunities.find((item) => item.key === type.key);

          return (
            <div
              key={type.key}
              className="rounded-2xl border border-white/10 bg-white/5 p-4"
            >
              <div className="mb-4 flex items-center justify-between gap-3">
                <h3 className="font-bold">{type.label}</h3>
                {onAdd && canAddAsset && (
                  <ActionButton onClick={() => onAdd(type.key)} icon="+">
                    Ajouter
                  </ActionButton>
                )}
              </div>

              <div className="space-y-3">
                <OpportunityInsightCard opportunity={opportunity} variant="compact" />

                {rows.length === 0 ? (
                  <EmptyState
                    title={
                      canAddAsset
                        ? "Aucun actif suivi"
                        : `${type.label} en apercu limite`
                    }
                    description={
                      canAddAsset
                        ? "Ajoute une ligne pour suivre revenus, performance, dette et valeur."
                        : "Disponible avec un niveau de lecture superieur. Le portefeuille reste visible sans creer de fausse donnee."
                    }
                    action={
                      onAdd && canAddAsset ? (
                        <ActionButton onClick={() => onAdd(type.key)} icon="+">
                          Ajouter
                        </ActionButton>
                      ) : null
                    }
                  />
                ) : (
                  rows.map((asset) => {
                    const assetResultClass =
                      n(asset.result) >= 0 ? "text-emerald-400" : "text-red-400";

                    return (
                      <article
                        key={asset.id}
                        className="rounded-xl border border-white/10 bg-black/30 p-4"
                      >
                        <div className="flex justify-between gap-3">
                          <div>
                            <h4 className="font-bold">{asset.name}</h4>
                            <p className="text-xs text-gray-400">
                              {type.label} - revenus{" "}
                              {money.format(n(asset.revenue))} EUR
                            </p>
                          </div>
                          <div className="text-right">
                            <p className="text-xs text-gray-400">Valeur</p>
                            <p className="font-black text-[#3fa9f5]">
                              {money.format(n(asset.final_value))} EUR
                            </p>
                          </div>
                        </div>

                        <div className="mt-3 grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
                          <div>
                            <p className="text-xs text-gray-500">Resultat</p>
                            <p className={assetResultClass}>
                              {n(asset.result) >= 0 ? "+" : ""}
                              {money.format(n(asset.result))} EUR
                            </p>
                          </div>
                          <div>
                            <p className="text-xs text-gray-500">Charges</p>
                            <p>{money.format(n(asset.charges))} EUR</p>
                          </div>
                          <div>
                            <p className="text-xs text-gray-500">Dette</p>
                            <p>{money.format(n(asset.debts))} EUR</p>
                          </div>
                          <div>
                            <p className="text-xs text-gray-500">Financement</p>
                            <p>{money.format(n(asset.fundraising))} EUR</p>
                          </div>
                        </div>

                        {(onUpdate || onDelete) && (
                          <div className="mt-4 flex justify-end gap-2">
                            {onUpdate && (
                              <ActionButton
                                onClick={() => onUpdate(asset)}
                                variant="secondary"
                                className="px-3 py-1.5 text-xs"
                              >
                                Modifier
                              </ActionButton>
                            )}
                            {onDelete && (
                              <ActionButton
                                onClick={() => onDelete(asset.id)}
                                variant="danger"
                                className="px-3 py-1.5 text-xs"
                              >
                                Supprimer
                              </ActionButton>
                            )}
                          </div>
                        )}
                      </article>
                    );
                  })
                )}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
