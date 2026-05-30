"use client";

import type {
  CategoryOpportunity,
  YieldAsset,
  YieldAssetData,
  YieldAssetType,
} from "@/lib/types";
import OpportunityInsightCard from "./OpportunityInsightCard";
import { ActionButton, EmptyState, MetricCard } from "@/components/ui/WealthUI";

type Props = {
  data?: YieldAssetData | null;
  onAdd?: (type: YieldAssetType) => void;
  onUpdate?: (asset: YieldAsset) => void;
  onDelete?: (id: number) => void;
  opportunities?: CategoryOpportunity[];
};

const money = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 });
const n = (value?: number | string | null) => Number(value || 0);

const types: Array<{ key: YieldAssetType; label: string }> = [
  { key: "crowdfunding", label: "Crowdfunding" },
  { key: "private_equity", label: "Private Equity" },
];

export default function YieldInvestmentsModule({
  data,
  onAdd,
  onUpdate,
  onDelete,
  opportunities = [],
}: Props) {
  const assets = data?.assets || [];
  const totals = data?.totals || {};

  return (
    <section className="rounded-2xl border border-white/10 bg-zinc-950 p-5">
      <div className="mb-5">
        <h2 className="text-2xl font-bold">Actifs Prives</h2>
        <p className="text-sm text-gray-400">
          Crowdfunding, private equity, prets et investissements participatifs
          dans une lecture consolidee.
        </p>
      </div>

      <div className="mb-5 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="Capital investi"
          value={`${money.format(n(totals.total_principal))} EUR`}
        />
        <MetricCard
          label="Taux moyen"
          value={`${n(totals.average_rate).toFixed(2)}%`}
        />
        <MetricCard
          label="Gain projete"
          value={`+${money.format(n(totals.total_projected_gain))} EUR`}
          tone="success"
        />
        <MetricCard
          label="Valeur finale"
          value={`${money.format(n(totals.total_final_value))} EUR`}
          tone="primary"
        />
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
                {onAdd && (
                  <ActionButton onClick={() => onAdd(type.key)} icon="+">
                    Ajouter
                  </ActionButton>
                )}
              </div>

              <div className="space-y-3">
                <OpportunityInsightCard opportunity={opportunity} variant="compact" />

                {rows.length === 0 ? (
                  <EmptyState
                    title="Aucun actif prive"
                    description="Ajoute une ligne pour suivre capital, rendement et valeur finale."
                    action={
                      onAdd ? (
                        <ActionButton onClick={() => onAdd(type.key)} icon="+">
                          Ajouter
                        </ActionButton>
                      ) : null
                    }
                  />
                ) : (
                  rows.map((asset) => (
                    <article
                      key={asset.id}
                      className="rounded-xl border border-white/10 bg-black/30 p-4"
                    >
                      <div className="flex justify-between gap-3">
                        <div>
                          <h4 className="font-bold">{asset.name}</h4>
                          <p className="text-xs text-gray-400">
                            {type.label} - {money.format(n(asset.principal))} EUR
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-xs text-gray-400">Valeur finale</p>
                          <p className="font-black text-[#3fa9f5]">
                            {money.format(n(asset.final_value))} EUR
                          </p>
                        </div>
                      </div>

                      <div className="mt-3 grid grid-cols-2 gap-2 text-sm sm:grid-cols-3">
                        <div>
                          <p className="text-xs text-gray-500">Rendement</p>
                          <p>{n(asset.average_rate).toFixed(2)}%</p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-500">Gain projete</p>
                          <p className="text-emerald-400">
                            +{money.format(n(asset.projected_gain))} EUR
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-500">Horizon</p>
                          <p>{n(asset.duration_months)} mois</p>
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
                  ))
                )}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
