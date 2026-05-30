"use client";

import { useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";
import type { ChildAccountsData } from "@/lib/types";
import { ActionButton, EmptyState, TextField, WealthModal } from "@/components/ui/WealthUI";

type ChildAccountsPanelProps = {
  enabled?: boolean;
  onUpgrade?: (plan: string) => void;
};

const money = new Intl.NumberFormat("fr-FR", {
  maximumFractionDigits: 0,
});

export default function ChildAccountsPanel({ enabled, onUpgrade }: ChildAccountsPanelProps) {
  const [data, setData] = useState<ChildAccountsData | null>(null);
  const [open, setOpen] = useState(false);
  const [values, setValues] = useState({
    child_name: "",
    goal: "",
    target_amount: "",
    current_amount: "",
    monthly_contribution: "",
    horizon: "",
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!enabled) return;
    const token = localStorage.getItem("token");
    if (!token) return;

    let cancelled = false;
    apiRequest<ChildAccountsData>("/finance/child-accounts", token)
      .then((payload) => {
        if (!cancelled) setData(payload);
      })
      .catch(() => {
        if (!cancelled) setData({ accounts: [], totals: {} });
      });

    return () => {
      cancelled = true;
    };
  }, [enabled]);

  if (!enabled) {
    return (
      <section className="rounded-2xl border border-white/10 bg-white/[0.04] p-5">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs uppercase tracking-widest text-[#3fa9f5]">Liberty+</p>
            <h3 className="mt-2 text-xl font-black text-white">Comptes enfants</h3>
            <p className="mt-2 text-sm text-gray-400">
              Portefeuille enfant, objectifs education et transmission deviennent disponibles a partir de Liberty.
            </p>
          </div>
          {onUpgrade && (
            <ActionButton onClick={() => onUpgrade("liberty")}>
              Passer a Liberty
            </ActionButton>
          )}
        </div>
      </section>
    );
  }

  const accounts = data?.accounts || [];
  const totals = data?.totals || {};

  const updateValue = (key: keyof typeof values, value: string) => {
    setValues((current) => ({ ...current, [key]: value }));
  };

  const createAccount = async () => {
    const token = localStorage.getItem("token");
    if (!token || !values.child_name.trim()) return;

    setLoading(true);
    try {
      await apiRequest("/finance/child-accounts", token, {
        method: "POST",
        body: JSON.stringify({
          ...values,
          target_amount: Number(values.target_amount || 0),
          current_amount: Number(values.current_amount || 0),
          monthly_contribution: Number(values.monthly_contribution || 0),
        }),
      });
      const payload = await apiRequest<ChildAccountsData>("/finance/child-accounts", token);
      setData(payload);
      setOpen(false);
      setValues({
        child_name: "",
        goal: "",
        target_amount: "",
        current_amount: "",
        monthly_contribution: "",
        horizon: "",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="rounded-2xl border border-white/10 bg-white/[0.04] p-5">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs uppercase tracking-widest text-[#3fa9f5]">Liberty+</p>
          <h3 className="mt-1 text-xl font-black text-white">Comptes enfants</h3>
          <p className="mt-1 text-sm text-gray-400">
            Objectifs education, capital enfant et trajectoire generationnelle.
          </p>
        </div>
        <ActionButton onClick={() => setOpen(true)} icon="+">
          Ajouter
        </ActionButton>
      </div>

      <div className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div className="rounded-xl border border-white/10 bg-black/25 p-3">
          <p className="text-xs text-gray-500">Capital actuel</p>
          <p className="font-black text-white">{money.format(Number(totals.current_amount || 0))} EUR</p>
        </div>
        <div className="rounded-xl border border-white/10 bg-black/25 p-3">
          <p className="text-xs text-gray-500">Objectif</p>
          <p className="font-black text-white">{money.format(Number(totals.target_amount || 0))} EUR</p>
        </div>
        <div className="rounded-xl border border-white/10 bg-black/25 p-3">
          <p className="text-xs text-gray-500">Mensuel</p>
          <p className="font-black text-[#3fa9f5]">{money.format(Number(totals.monthly_contribution || 0))} EUR</p>
        </div>
      </div>

      {accounts.length === 0 ? (
        <EmptyState
          title="Aucun compte enfant"
          description="Cree une premiere enveloppe familiale avec objectif, capital actuel et contribution mensuelle."
          action={<ActionButton onClick={() => setOpen(true)}>Ajouter</ActionButton>}
        />
      ) : (
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          {accounts.map((account) => (
            <article key={account.id} className="rounded-xl border border-white/10 bg-black/25 p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h4 className="font-black text-white">{account.child_name}</h4>
                  <p className="mt-1 text-sm text-gray-400">{account.goal || "Objectif a preciser"}</p>
                </div>
                <span className="text-xs font-black text-[#3fa9f5]">
                  {Number(account.progress_percent || 0)}%
                </span>
              </div>
              <div className="mt-4 h-2 overflow-hidden rounded-full bg-white/10">
                <div className="h-full rounded-full bg-[#3fa9f5]" style={{ width: `${Number(account.progress_percent || 0)}%` }} />
              </div>
              <p className="mt-3 text-sm text-gray-300">
                {money.format(Number(account.current_amount || 0))} / {money.format(Number(account.target_amount || 0))} EUR
              </p>
            </article>
          ))}
        </div>
      )}

      <WealthModal
        open={open}
        title="Ajouter un compte enfant"
        description="Structure une enveloppe simple et mesurable. La validation reste cote backend Liberty+."
        onClose={() => setOpen(false)}
        footer={
          <>
            <ActionButton variant="secondary" onClick={() => setOpen(false)}>
              Annuler
            </ActionButton>
            <ActionButton onClick={createAccount} disabled={loading || !values.child_name.trim()}>
              {loading ? "Enregistrement..." : "Valider"}
            </ActionButton>
          </>
        }
      >
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <TextField label="Prenom" value={values.child_name} onChange={(value) => updateValue("child_name", value)} />
          <TextField label="Objectif" value={values.goal} onChange={(value) => updateValue("goal", value)} />
          <TextField label="Capital cible" type="number" value={values.target_amount} onChange={(value) => updateValue("target_amount", value)} />
          <TextField label="Capital actuel" type="number" value={values.current_amount} onChange={(value) => updateValue("current_amount", value)} />
          <TextField label="Contribution mensuelle" type="number" value={values.monthly_contribution} onChange={(value) => updateValue("monthly_contribution", value)} />
          <TextField label="Horizon" value={values.horizon} onChange={(value) => updateValue("horizon", value)} />
        </div>
      </WealthModal>
    </section>
  );
}
