"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiRequest } from "@/lib/api";
import { useDashboard } from "@/hooks/useDashboard";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import BrandMark from "@/components/BrandMark";
import {
  ActionButton,
  SelectField,
  TextField,
  WealthModal,
  WealthToast,
} from "@/components/ui/WealthUI";
import type {
  FinanceEntry,
  FinancePayload,
  PortfolioAsset,
  PortfolioPayload,
  ProductContext,
  RealEstateAsset,
  RealEstatePayload,
  RealEstateType,
  VentureAsset,
  VentureAssetPayload,
  VentureAssetType,
  WealthProfile,
  YieldAsset,
  YieldAssetPayload,
  YieldAssetType,
} from "@/lib/types";

import Header from "@/components/dashboard/Header";
import AdvisorChat from "@/components/dashboard/AdvisorChat";
import FinanceModule from "@/components/dashboard/FinanceModule";
import LegacyOfficePanel from "@/components/dashboard/LegacyOfficePanel";
import OpportunityDiscoveryPanel from "@/components/dashboard/OpportunityDiscoveryPanel";
import OpportunitiesModule from "@/components/dashboard/OpportunitiesModule";
import PortfolioModule from "@/components/dashboard/PortfolioModule";
import ProfileReferralPanel from "@/components/dashboard/ProfileReferralPanel";
import RealEstateModule from "@/components/dashboard/RealEstateModule";
import RubricBreakdownChart from "@/components/dashboard/RubricBreakdownChart";
import ThemeSwitcher from "@/components/dashboard/ThemeSwitcher";
import VentureAssetsModule from "@/components/dashboard/VentureAssetsModule";
import YieldInvestmentsModule from "@/components/dashboard/YieldInvestmentsModule";
import WorkspacePanel from "@/components/dashboard/WorkspacePanel";
import ChildAccountsPanel from "@/components/finance/ChildAccountsPanel";
import FinanceBlock from "@/components/finance/FinanceBlock";
import GamificationPanel from "@/components/gamification/GamificationPanel";

const money = new Intl.NumberFormat("fr-FR", {
  maximumFractionDigits: 0,
});

const formatChartMoney = (value: number | string) =>
  `${money.format(Number(value || 0))} EUR`;

const planOrder: Record<string, number> = {
  FREE: 0,
  GOLD: 1,
  ELITE: 2,
  LIBERTY: 3,
  LEGACY: 4,
};

const planSequence = ["FREE", "GOLD", "ELITE", "LIBERTY", "LEGACY"];

const planExperienceCopy: Record<
  string,
  { name: string; promise: string; unlocks: string[] }
> = {
  FREE: {
    name: "Foundation",
    promise: "Ton patrimoine commence a prendre forme.",
    unlocks: ["Gold - Growth", "Future Intelligence", "Wealth Narrative", "Patrimoine activable"],
  },
  GOLD: {
    name: "Gold - Growth",
    promise: "Accelere ta croissance patrimoniale.",
    unlocks: ["Elite - Wealth OS", "Family Office CEO", "Simulations avancees", "Lecture operationnelle"],
  },
  ELITE: {
    name: "Elite - Wealth OS",
    promise: "Pilote ton patrimoine comme un systeme.",
    unlocks: ["Liberty - Sovereign Wealth", "Comptes enfants", "Arbitrages avances", "Objectifs patrimoniaux"],
  },
  LIBERTY: {
    name: "Liberty - Sovereign Wealth",
    promise: "Prends le controle de ta richesse.",
    unlocks: ["Dynasty Office", "Transmission Center", "Gouvernance familiale", "Succession"],
  },
  LEGACY: {
    name: "Dynasty Office",
    promise: "Construis un patrimoine transmissible.",
    unlocks: ["Tous les espaces", "Gouvernance familiale", "Transmission avancee", "Vision generationnelle"],
  },
};

const normalizePlan = (plan?: string | null) => {
  const value = String(plan || "FREE").trim().toUpperCase();
  if (value === "GROWTH") return "GOLD";
  if (value === "PLATINUM" || value === "WEALTH_OS") return "ELITE";
  if (value === "DYNASTY" || value === "DYNASTY_OFFICE") return "LEGACY";
  return planOrder[value] === undefined ? "FREE" : value;
};

const planAllows = (plan: string | undefined | null, required: string) =>
  planOrder[normalizePlan(plan)] >= planOrder[normalizePlan(required)];

type DashboardSection =
  | "home"
  | "opportunities"
  | "finances"
  | "investments"
  | "real_estate"
  | "ventures"
  | "ai"
  | "progression"
  | "legacy"
  | "profile"
  | "billing"
  | "settings";

type NavigationItem = {
  key: DashboardSection;
  label: string;
  description: string;
  locked?: boolean;
};

type DashboardFormKind =
  | "onboarding"
  | "workspace"
  | "invite"
  | "portfolio"
  | "finance"
  | "real_estate"
  | "yield"
  | "venture";

type DashboardFormState = {
  kind: DashboardFormKind;
  title: string;
  description?: string;
  values: Record<string, string>;
  context?: {
    id?: number;
    workspaceId?: number;
    propertyType?: RealEstateType;
    yieldType?: YieldAssetType;
    ventureType?: VentureAssetType;
    financeItem?: FinanceEntry;
  };
};

type ConfirmState = {
  title: string;
  description: string;
  onConfirm: () => Promise<void>;
};

function LockedSection({
  title,
  description,
  onUpgrade,
  plan = "gold",
}: {
  title: string;
  description: string;
  onUpgrade?: (plan: string) => void;
  plan?: string;
}) {
  return (
    <section className="rounded-2xl border border-white/10 bg-zinc-950 p-6">
      <div className="max-w-2xl">
        <p className="text-xs uppercase tracking-widest text-[#3fa9f5]">
          Module progressif
        </p>
        <h2 className="mt-2 text-2xl font-black text-white">{title}</h2>
        <p className="mt-3 text-sm leading-relaxed text-gray-400">
          {description}
        </p>
        {onUpgrade && (
          <button
            onClick={() => onUpgrade(plan)}
            className="mt-5 rounded-xl bg-[#3fa9f5] px-4 py-2 text-sm font-semibold text-white"
          >
            Debloquer
          </button>
        )}
      </div>
    </section>
  );
}

function SectionHeader({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <div className="mb-5">
      <p className="text-xs uppercase tracking-widest text-[#3fa9f5]">
        {eyebrow}
      </p>
      <h1 className="mt-2 text-3xl font-black text-white">{title}</h1>
      <p className="mt-2 max-w-3xl text-sm leading-relaxed text-gray-400">
        {description}
      </p>
    </div>
  );
}

function WealthIntelligencePanel({ product }: { product?: ProductContext | null }) {
  const narrative = product?.wealth_intelligence;
  const hiddenItems = narrative?.hidden_items || [];
  const domains = narrative?.domains || [];

  if (!narrative) return null;

  const potentialData = [
    { label: "Visible", value: Number(narrative.visible_wealth || 0), fill: "#3fa9f5" },
    { label: "Activable", value: Number(narrative.activable_wealth || 0), fill: "#ffd21a" },
    { label: "Potentiel", value: Number(narrative.total_potential || 0), fill: "#16d99a" },
  ].filter((item) => item.value > 0);

  return (
    <section className="rounded-2xl border border-[#ffd21a]/30 bg-[radial-gradient(circle_at_top_left,_rgba(255,210,26,0.24),_transparent_35%),linear-gradient(135deg,#080808,#1b1503_58%,#020202)] p-6">
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <div>
          <p className="text-xs uppercase tracking-widest text-[#ffd21a]">
            {narrative.title || "Wealth Intelligence"}
          </p>
          <h2 className="mt-2 text-3xl font-black text-white md:text-4xl">
            {narrative.headline || narrative.question || "Ou j'en suis ?"}
          </h2>
          <p className="mt-4 max-w-3xl text-base leading-relaxed text-gray-300">
            {narrative.narrative}
          </p>
          {narrative.memorable_insight ? (
            <div className="mt-5 rounded-2xl border border-[#ffd21a]/30 bg-[#ffd21a]/10 p-4">
              <p className="text-xs uppercase tracking-widest text-[#ffd21a]">
                Insight memorable
              </p>
              <p className="mt-2 text-lg font-black leading-snug text-white">
                {narrative.memorable_insight}
              </p>
              {narrative.why_it_matters ? (
                <p className="mt-2 text-sm leading-relaxed text-gray-400">
                  {narrative.why_it_matters}
                </p>
              ) : null}
            </div>
          ) : null}
          <p className="mt-4 text-sm leading-relaxed text-gray-500">
            {narrative.gravity_reading}
          </p>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3 xl:grid-cols-1">
          {[
            ["Patrimoine visible", narrative.visible_wealth],
            ["Patrimoine activable", narrative.activable_wealth],
            ["Potentiel total", narrative.total_potential],
          ].map(([label, value]) => (
            <div key={String(label)} className="rounded-xl border border-white/10 bg-black/35 p-4">
              <p className="text-xs text-gray-500">{label}</p>
              <p className="mt-2 text-2xl font-black text-white">
                {money.format(Number(value || 0))} EUR
              </p>
            </div>
          ))}
        </div>
      </div>
      {potentialData.length > 0 && (
        <div className="mt-5 rounded-2xl border border-white/10 bg-black/25 p-4">
          <div className="mb-3 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-xs uppercase tracking-widest text-gray-500">
                Potentiel patrimonial
              </p>
              <h3 className="text-lg font-black text-white">
                Visible vs activable
              </h3>
            </div>
            <p className="text-sm text-gray-500">
              Lecture consolidee White Rock
            </p>
          </div>
          <div className="h-52">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={potentialData} margin={{ left: 4, right: 4, top: 8, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                <XAxis dataKey="label" tick={{ fill: "#a1a1aa", fontSize: 11 }} />
                <YAxis tick={{ fill: "#a1a1aa", fontSize: 11 }} width={48} />
                <Tooltip
                  cursor={{ fill: "rgba(255,255,255,0.04)" }}
                  formatter={(value) => formatChartMoney(String(value))}
                />
                <Bar dataKey="value" radius={[8, 8, 0, 0]}>
                  {potentialData.map((item) => (
                    <Cell key={item.label} fill={item.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
      {domains.length > 0 && (
        <div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-3">
          {domains.slice(0, 3).map((item) => (
            <div key={item.key || item.label} className="rounded-xl border border-white/10 bg-black/30 p-4">
              <p className="text-xs uppercase tracking-widest text-gray-500">
                {item.label}
              </p>
              <p className="mt-2 text-2xl font-black text-white">
                {money.format(Number(item.value || 0))} EUR
              </p>
              <p className="mt-2 text-xs leading-relaxed text-gray-400">
                {item.description}
              </p>
            </div>
          ))}
        </div>
      )}
      {hiddenItems.length > 0 && (
        <div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-4">
          {hiddenItems.slice(0, 4).map((item) => (
            <div key={item.key || item.label} className="rounded-xl border border-white/10 bg-black/30 p-4">
              <p className="text-sm font-bold text-white">{item.label}</p>
              <p className="mt-2 text-xl font-black text-[#ffd21a]">
                {money.format(Number(item.potential_value || 0))} EUR
              </p>
              <p className="mt-2 text-xs leading-relaxed text-gray-400">
                {item.description}
              </p>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function FamilyOfficeCeoPanel({ product }: { product?: ProductContext | null }) {
  const ceo = product?.family_office_ceo;

  if (!ceo) return null;

  const runway =
    ceo.runway_months === "stable"
      ? "Stable"
      : ceo.runway_months !== null && ceo.runway_months !== undefined
        ? `${ceo.runway_months} mois`
        : "A confirmer";

  return (
    <section className="rounded-2xl border border-[#ffd21a]/35 bg-[radial-gradient(circle_at_top_right,_rgba(255,210,26,0.18),_transparent_34%),linear-gradient(135deg,#070707,#111827_58%,#1b1503)] p-5">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs uppercase tracking-widest text-[#ffd21a]">
            {ceo.title || "Family Office CEO"}
          </p>
          <h2 className="mt-1 text-2xl font-black text-white">
            {ceo.question || "Piloter sa vie financiere"}
          </h2>
        </div>
        <p className="max-w-xl text-sm leading-relaxed text-gray-400">
          {ceo.operating_reading}
        </p>
      </div>

      {ceo.objective ? (
        <div className="mt-4 rounded-2xl border border-white/10 bg-black/30 p-4">
          <p className="text-xs uppercase tracking-widest text-gray-500">
            Pourquoi c&apos;est important
          </p>
          <p className="mt-2 text-lg font-black leading-snug text-white">
            {ceo.objective}
          </p>
        </div>
      ) : null}

      <div className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[
          ["Patrimoine", ceo.wealth],
          ["Revenus / mois", ceo.monthly_income],
          ["Burn rate", ceo.burn_rate],
          ["Marge / mois", ceo.monthly_capacity],
        ].map(([label, value]) => (
          <div key={String(label)} className="rounded-xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-xs text-gray-500">{label}</p>
            <p className="mt-2 text-xl font-black text-white">
              {money.format(Number(value || 0))} EUR
            </p>
          </div>
        ))}
      </div>

      <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3">
        <div className="rounded-xl border border-white/10 bg-black/30 p-4">
          <p className="text-xs uppercase tracking-widest text-gray-500">Runway</p>
          <p className="mt-2 text-xl font-black text-[#ffd21a]">{runway}</p>
          <p className="mt-1 text-xs text-gray-500">Lecture operationnelle White Rock</p>
        </div>
        <div className="rounded-xl border border-white/10 bg-black/30 p-4">
          <p className="text-xs uppercase tracking-widest text-gray-500">Decision</p>
          <p className="mt-2 text-sm font-bold text-white">{ceo.decision?.title || "A consolider"}</p>
          <p className="mt-1 text-xs leading-relaxed text-gray-400">{ceo.decision?.action || ceo.decision?.description}</p>
        </div>
        <div className="rounded-xl border border-white/10 bg-black/30 p-4">
          <p className="text-xs uppercase tracking-widest text-gray-500">Point faible</p>
          <p className="mt-2 text-sm font-bold text-white">{ceo.weakest_dimension?.label || ceo.risk?.title || "A confirmer"}</p>
          <p className="mt-1 text-xs leading-relaxed text-gray-400">
            {ceo.weakest_dimension?.score !== undefined
              ? `${ceo.weakest_dimension.score}/100`
              : ceo.risk?.description}
          </p>
        </div>
      </div>
    </section>
  );
}

function FutureIntelligencePanel({ product }: { product?: ProductContext | null }) {
  const future = product?.future_intelligence;
  const position = future?.position;
  const timeline = future?.timeline || [];
  const simulations = future?.simulations || [];
  const film = future?.film || [];

  if (!future) return null;

  const trajectoryData = film
    .map((chapter) => ({
      year: String(chapter.year || ""),
      wealth: Number(chapter.wealth || 0),
    }))
    .filter((item) => item.year && item.wealth > 0);

  return (
    <section className="rounded-2xl border border-[#3fa9f5]/20 bg-zinc-950 p-5">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs uppercase tracking-widest text-[#3fa9f5]">
            Future Intelligence
          </p>
          <h2 className="mt-1 text-2xl font-black text-white">
            {future.question || "Ou vais-je ?"}
          </h2>
          {future.why_it_matters ? (
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-gray-400">
              {future.why_it_matters}
            </p>
          ) : null}
        </div>
        <div className="text-sm text-gray-400">
          Prochain palier:{" "}
          <span className="font-bold text-white">
            {position?.destination?.label || "a confirmer"}
          </span>
          {position?.estimated_label ? (
            <span className="text-[#3fa9f5]"> · {position.estimated_label}</span>
          ) : null}
        </div>
      </div>

      <div className="mt-5 grid grid-cols-1 gap-4 xl:grid-cols-[0.85fr_1.15fr]">
        <div className="rounded-xl border border-white/10 bg-white/[0.04] p-4">
          <p className="text-xs uppercase tracking-widest text-gray-500">Wealth Map</p>
          <p className="mt-2 text-3xl font-black text-white">
            {money.format(Number(position?.current || 0))} EUR
          </p>
          <p className="mt-1 text-sm text-gray-400">
            vers {money.format(Number(position?.destination?.target || 0))} EUR
          </p>
          <div className="mt-4 h-3 overflow-hidden rounded-full bg-white/10">
            <div
              className="h-full rounded-full bg-gradient-to-r from-[#3fa9f5] via-[#16d99a] to-[#ffd21a]"
              style={{ width: `${Math.min(100, Number(position?.progress_percent || 0))}%` }}
            />
          </div>
          <p className="mt-3 text-sm text-gray-400">
            Reste {money.format(Number(position?.distance_remaining || 0))} EUR · vitesse{" "}
            {money.format(Number(position?.monthly_velocity || 0))} EUR/mois
          </p>
        </div>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          {simulations.slice(0, 3).map((scenario) => (
            <div key={scenario.key || scenario.label} className="rounded-xl border border-white/10 bg-white/[0.04] p-4">
              <p className="text-sm font-bold text-white">{scenario.label}</p>
              <p className="mt-2 text-2xl font-black text-white">
                {money.format(Number(scenario.value_10y || 0))} EUR
              </p>
              <p className="mt-1 text-xs text-gray-500">projection 10 ans</p>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-5 grid grid-cols-1 gap-3 xl:grid-cols-[1.15fr_0.85fr]">
        {trajectoryData.length > 0 && (
          <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
            <div className="mb-3 flex items-center justify-between gap-3">
              <h3 className="font-bold text-white">Film du futur</h3>
              <span className="text-xs text-gray-500">projection White Rock</span>
            </div>
            <div className="h-60">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trajectoryData} margin={{ left: 0, right: 12, top: 8, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                  <XAxis dataKey="year" tick={{ fill: "#a1a1aa", fontSize: 11 }} />
                  <YAxis tick={{ fill: "#a1a1aa", fontSize: 11 }} width={50} />
                  <Tooltip formatter={(value) => formatChartMoney(String(value))} />
                  <Line
                    type="monotone"
                    dataKey="wealth"
                    stroke="#3fa9f5"
                    strokeWidth={3}
                    dot={{ r: 3, fill: "#ffd21a", stroke: "#ffd21a" }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
        <div className="space-y-2">
          {timeline.slice(0, 5).map((stage) => (
            <div key={stage.label} className="grid grid-cols-[90px_1fr_120px] items-center gap-3 rounded-xl border border-white/10 bg-white/[0.03] p-3">
              <p className="text-sm font-bold text-white">{stage.label}</p>
              <div className="h-2 overflow-hidden rounded-full bg-white/10">
                <div
                  className="h-full rounded-full bg-[#3fa9f5]"
                  style={{ width: `${Math.min(100, Number(stage.progress_percent || 0))}%` }}
                />
              </div>
              <p className="text-right text-xs text-gray-400">{stage.estimated_label}</p>
            </div>
          ))}
        </div>
        <div className="space-y-2 xl:col-span-2">
          {film.slice(0, 4).map((chapter) => (
            <div key={`${chapter.year}-${chapter.title}`} className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-black text-[#3fa9f5]">{chapter.year}</p>
                <p className="text-sm font-black text-white">
                  {money.format(Number(chapter.wealth || 0))} EUR
                </p>
              </div>
              <p className="mt-1 text-sm font-bold text-white">{chapter.title}</p>
              <p className="mt-1 text-xs leading-relaxed text-gray-400">{chapter.narrative}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function DecisionIntelligencePanel({ product }: { product?: ProductContext | null }) {
  const strategy = product?.decision_intelligence;
  const cards = strategy?.cards || [];

  if (!strategy || cards.length === 0) return null;

  return (
    <section className="rounded-2xl border border-white/10 bg-zinc-950 p-5">
      <p className="text-xs uppercase tracking-widest text-[#3fa9f5]">
        {strategy.title || "Decision Intelligence"}
      </p>
      <h2 className="mt-1 text-2xl font-black text-white">
        {strategy.question || "Que dois-je faire ?"}
      </h2>
      {strategy.why_it_matters ? (
        <p className="mt-2 max-w-3xl text-sm leading-relaxed text-gray-400">
          {strategy.why_it_matters}
        </p>
      ) : null}
      {strategy.next_action ? (
        <div className="mt-4 rounded-2xl border border-[#3fa9f5]/25 bg-[#3fa9f5]/10 p-4">
          <p className="text-xs uppercase tracking-widest text-[#3fa9f5]">
            Action utile
          </p>
          <p className="mt-2 text-lg font-black leading-snug text-white">
            {strategy.next_action}
          </p>
        </div>
      ) : null}
      <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-4">
        {cards.slice(0, 4).map((card) => (
          <div key={card.key || card.label} className="rounded-xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-xs uppercase tracking-widest text-gray-500">{card.label}</p>
            <h3 className="mt-2 text-sm font-bold text-white">{card.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-gray-400">{card.description}</p>
            {card.action ? (
              <p className="mt-3 text-xs font-semibold text-[#3fa9f5]">{card.action}</p>
            ) : null}
            {card.score ? (
              <p className="mt-3 text-xs font-semibold text-[#ffd21a]">impact {card.score}/100</p>
            ) : null}
          </div>
        ))}
      </div>
    </section>
  );
}

function FamilyOfficeIntelligencePanel({ product }: { product?: ProductContext | null }) {
  const intelligence = product?.family_office_intelligence;
  const scorecard = intelligence?.scorecard || [];
  const stressTests = intelligence?.stress_tests || [];
  const dependencies = intelligence?.dependencies || [];

  if (!intelligence) return null;

  const scorecardData = scorecard
    .slice(0, 6)
    .map((item) => ({
      label: String(item.label || ""),
      score: Number(item.score || 0),
    }))
    .filter((item) => item.label);
  const stressData = stressTests
    .slice(0, 4)
    .map((test) => ({
      label: String(test.label || ""),
      delta: Number(test.delta || 0),
    }))
    .filter((item) => item.label);

  return (
    <section className="rounded-2xl border border-white/10 bg-zinc-950 p-5">
      <p className="text-xs uppercase tracking-widest text-[#3fa9f5]">
        Family Office Intelligence
      </p>
      <h2 className="mt-1 text-2xl font-black text-white">
        {intelligence.question || "Quelle est la solidite globale ?"}
      </h2>
      <div className="mt-4 grid grid-cols-1 gap-5 xl:grid-cols-[1fr_1fr_1fr]">
        <div className="rounded-xl border border-white/10 bg-white/[0.04] p-4">
          <h3 className="font-bold text-white">Scorecard</h3>
          <div className="mt-3 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={scorecardData}>
                <PolarGrid stroke="rgba(255,255,255,0.12)" />
                <PolarAngleAxis dataKey="label" tick={{ fill: "#a1a1aa", fontSize: 10 }} />
                <Tooltip formatter={(value) => `${Number(value || 0)}/100`} />
                <Radar
                  dataKey="score"
                  stroke="#ffd21a"
                  fill="#ffd21a"
                  fillOpacity={0.24}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="rounded-xl border border-white/10 bg-white/[0.04] p-4">
          <h3 className="font-bold text-white">Stress tests</h3>
          <div className="mt-3 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={stressData} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                <XAxis dataKey="label" tick={{ fill: "#a1a1aa", fontSize: 10 }} />
                <YAxis tick={{ fill: "#a1a1aa", fontSize: 11 }} width={48} />
                <Tooltip formatter={(value) => formatChartMoney(String(value))} />
                <Bar dataKey="delta" radius={[8, 8, 0, 0]}>
                  {stressData.map((item) => (
                    <Cell
                      key={item.label}
                      fill={item.delta >= 0 ? "#3fa9f5" : "#ef4444"}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="rounded-xl border border-white/10 bg-white/[0.04] p-4">
          <h3 className="font-bold text-white">Dependances</h3>
          <div className="mt-3 space-y-2">
            {dependencies.slice(0, 3).map((signal) => (
              <div key={`${signal.type}-${signal.title}`} className="rounded-lg bg-black/30 p-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-bold text-white">{signal.title}</p>
                  <span className="text-xs uppercase text-gray-500">{signal.severity}</span>
                </div>
                <p className="mt-1 text-xs leading-relaxed text-gray-400">{signal.description}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

const getAssetValue = (asset: PortfolioAsset) =>
  Number(asset.value ?? asset.current_value ?? 0);

const parsePositiveNumber = (value: string | null) => {
  if (value === null) return null;

  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
};

const parseNonNegativeNumber = (value: string | null) => {
  if (value === null) return null;

  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : null;
};

const isRealEstatePortfolioType = (value: string) =>
  [
    "IMMOBILIER",
    "REAL_ESTATE",
    "REAL ESTATE",
    "IMMO",
    "CROWDFUNDING",
    "PRIVATE_EQUITY",
    "PRIVATE EQUITY",
    "AI_BUSINESS",
    "AI BUSINESS",
    "BUSINESS",
    "STARTUP",
    "FRANCHISE",
    "BANKING",
    "ENTREPRENEURSHIP",
    "MARKET",
  ].includes(
    value.trim().toUpperCase()
  );

const normalizePortfolioAssetTypePreset = (value?: string) => {
  const normalized = String(value || "").trim().toUpperCase();
  if (!normalized) return "STOCK";
  if (["STOCKS", "EQUITY", "EQUITIES", "ACTION", "ACTIONS"].includes(normalized)) {
    return "STOCK";
  }
  return normalized;
};

const userValidationMessages = new Set([
  "Nom d'actif requis.",
  "Classe d'actif requise.",
  "Quantite invalide: saisis un nombre superieur a 0.",
  "Prix d'achat invalide: saisis un nombre superieur a 0.",
  "Cette categorie se gere dans son module dedie.",
]);

const isUserValidationError = (error: unknown) =>
  error instanceof Error && userValidationMessages.has(error.message);

const buildStructuredNotes = (
  values: Record<string, string>,
  descriptors: Array<[string, string | undefined]>
) => {
  const details = descriptors
    .filter(([, value]) => Boolean(value))
    .map(([label, value]) => `${label}: ${value}`);
  const notes = String(values.notes || "").trim();

  return [...details, notes].filter(Boolean).join("\n") || null;
};

const toNullableNumber = (value?: string) => {
  const trimmed = String(value || "").trim();
  if (!trimmed) return null;
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : null;
};

const yesNoLabel = (value?: boolean | null) => (value ? "Oui" : "Non");

const compactText = (value?: string | number | null, fallback = "A renseigner") => {
  const text = String(value ?? "").trim();
  return text || fallback;
};

const formatDate = (value?: string | number | null) => {
  if (!value) return "";
  const date =
    typeof value === "number" && value < 100000000000
      ? new Date(value * 1000)
      : new Date(value);
  if (Number.isNaN(date.getTime())) return "";

  return new Intl.DateTimeFormat("fr-FR", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  }).format(date);
};

export default function Dashboard() {
  const router = useRouter();
  const {
    dashboard,
    portfolio,
    realEstate,
    yieldAssets,
    ventureAssets,
    businessIntelligence,
    categoryOpportunities,
    legacyOverview,
    onboarding,
    finance,
    financeOverview,
    gamification,
    commandCenter,
    workspaces,
    product,
    billingSubscription,
    progressionTimeline,
    advisorContext,
    refreshAll,
    refreshAfterMutation,
    loading,
  } = useDashboard();

  const token =
    typeof window !== "undefined" ? localStorage.getItem("token") : null;
  const [activeSection, setActiveSection] = useState<DashboardSection>("home");
  const [formModal, setFormModal] = useState<DashboardFormState | null>(null);
  const [confirmModal, setConfirmModal] = useState<ConfirmState | null>(null);
  const [toast, setToast] = useState<{
    message: string;
    type: "success" | "error" | "info";
  } | null>(null);
  const [modalLoading, setModalLoading] = useState(false);
  const [wealthProfile, setWealthProfile] = useState<WealthProfile | null>(null);

  const showToast = (message: string, type: "success" | "error" | "info" = "info") => {
    setToast({ message, type });
  };

  const loadWealthProfile = useCallback(async () => {
    if (!token) return null;

    try {
      const data = await apiRequest<{ profile?: WealthProfile }>("/profile/me", token);
      const profile = data.profile || {};
      setWealthProfile(profile);
      return profile;
    } catch (err) {
      console.error(err);
      setWealthProfile({});
      return {};
    }
  }, [token]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("checkout") !== "success") return;

    const timeoutId = window.setTimeout(() => {
      setToast({
        message: "Paiement confirme. Ton abonnement est en cours de synchronisation.",
        type: "success",
      });
      router.replace("/dashboard", { scroll: false });
    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, [router]);

  useEffect(() => {
    if (!["profile", "settings"].includes(activeSection) || !token) return;
    loadWealthProfile();
  }, [activeSection, loadWealthProfile, token]);

  const updateModalValue = (key: string, value: string) => {
    setFormModal((current) =>
      current
        ? { ...current, values: { ...current.values, [key]: value } }
        : current
    );
  };

  const closeFormModal = () => {
    if (!modalLoading) setFormModal(null);
  };

  const goToSection = (section: DashboardSection) => {
    setActiveSection(section);
    if (typeof window !== "undefined") {
      window.requestAnimationFrame(() => {
        window.scrollTo({ top: 0, behavior: "smooth" });
      });
    }
  };

  const interactiveCard =
    "cursor-pointer transition hover:-translate-y-0.5 hover:border-[#3fa9f5]/40 hover:bg-white/[0.07]";

  if (loading) {
    return (
      <main className="relative min-h-screen overflow-hidden bg-black p-4 text-white">
        <div className="absolute inset-0 bg-[url('/bg-family-office.jpg')] bg-cover bg-center opacity-25" />
        <div className="absolute inset-0 bg-gradient-to-br from-black via-black/90 to-[#061827]" />
        <div className="relative mx-auto max-w-7xl space-y-5 opacity-35 blur-[1px]">
          <div className="h-20 rounded-2xl border border-white/10 bg-white/[0.04]" />
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-[260px_1fr]">
            <div className="hidden h-96 rounded-2xl border border-white/10 bg-white/[0.04] lg:block" />
            <div className="space-y-5">
              <div className="h-56 rounded-2xl border border-white/10 bg-white/[0.04]" />
              <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
                <div className="h-72 rounded-2xl border border-white/10 bg-white/[0.04]" />
                <div className="h-72 rounded-2xl border border-white/10 bg-white/[0.04]" />
              </div>
            </div>
          </div>
        </div>
        <div className="absolute inset-0 flex items-center justify-center bg-black/45 backdrop-blur-sm">
          <div className="fade-in flex flex-col items-center text-center">
            <BrandMark />
            <p className="mt-6 max-w-md text-sm leading-relaxed text-gray-300">
              Le cockpit se materialise progressivement. Synchronisation du plan,
              des modules et de la progression.
            </p>
            <div className="mt-8 h-16 w-16 rounded-full border-2 border-[#3fa9f5]/30 border-r-amber-300 border-t-[#3fa9f5] animate-spin" />
          </div>
        </div>
      </main>
    );
  }

  const globalScore =
    Number(commandCenter?.global_score ?? 0) || 0;
  const realEstateAssets = realEstate?.assets || [];
  const investmentRubrics = portfolio.map((asset) => ({
    label: String(asset.asset_type || asset.type || "Autre").replace(/_/g, " ").toUpperCase(),
    value: getAssetValue(asset),
  }));
  const realEstateRubrics = realEstateAssets.map((asset) => ({
    label: String(asset.property_type || "Immobilier").replace(/_/g, " ").toUpperCase(),
    value: Number(asset.estimated_value || asset.resale_price || asset.purchase_price || 0),
  }));
  const businessRubrics = [
    ...(yieldAssets?.assets || []).map((asset) => ({
      label:
        asset.asset_type === "private_equity"
          ? "PRIVATE EQUITY"
          : "CROWDFUNDING",
      value: Number(asset.final_value || asset.principal || 0),
    })),
    ...(ventureAssets?.assets || []).map((asset) => ({
      label: String(asset.asset_type || "Business").replace(/_/g, " ").toUpperCase(),
      value: Number(asset.final_value || asset.computed_value || asset.valuation || 0),
    })),
  ];
  const businessMetrics = businessIntelligence?.metrics || {};
  const businessDecision = businessIntelligence?.decision;
  const businessNarrative = businessIntelligence?.narrative;
  const categoryOpportunityItems = categoryOpportunities?.categories || [];
  const findOpportunity = (key: string) =>
    categoryOpportunityItems.find((item) => item.key === key);
  const financialOpportunityKeys = [
    "stock",
    "stocks",
    "etf",
    "crypto",
    "commodities",
    "forex",
  ];
  const financialOpportunities = categoryOpportunityItems.filter((item) =>
    financialOpportunityKeys.includes(item.key || "")
  );
  const visibleModules = new Set(
    product?.modules?.visible
      ?.filter((module) => module.state === "active")
      .map((module) => module.key) || []
  );
  const currentPlan = product?.plan || dashboard?.plan;
  const currentPlanKey = normalizePlan(currentPlan);
  const currentPlanCopy =
    planExperienceCopy[currentPlanKey] || planExperienceCopy.FREE;
  const backendNextPlan = normalizePlan(product?.next_plan);
  const currentPlanIndex = planSequence.indexOf(currentPlanKey);
  const fallbackNextPlan =
    currentPlanIndex >= 0 && currentPlanIndex < planSequence.length - 1
      ? planSequence[currentPlanIndex + 1]
      : "LEGACY";
  const nextPlanKey =
    planOrder[backendNextPlan] > planOrder[currentPlanKey]
      ? backendNextPlan
      : fallbackNextPlan;
  const nextPlanCopy = planExperienceCopy[nextPlanKey] || planExperienceCopy.LEGACY;
  const activeModuleCount = (product?.modules?.visible || []).filter(
    (module) => module.state === "active"
  ).length;
  const lockedModuleCount = (product?.modules?.locked || []).length;
  const billingRenewalDate =
    formatDate(
      billingSubscription?.renewal_at ||
        billingSubscription?.current_period_end ||
        billingSubscription?.effective_at ||
        billingSubscription?.cancel_at
    ) || "Visible dans le portail";
  const billingAmount =
    billingSubscription?.display_amount ||
    billingSubscription?.price ||
    product?.entitlements?.copy?.price ||
    "Visible dans le portail";
  const futurePlanName = compactText(
    billingSubscription?.future_plan || billingSubscription?.pending_plan,
    ""
  );
  const profileIncome = Number(
    onboarding?.revenus_mensuels ?? onboarding?.monthly_income ?? 0
  );
  const profileExpenses = Number(
    onboarding?.charges_mensuelles ?? onboarding?.monthly_expenses ?? 0
  );
  const profileCapacity =
    profileIncome > 0 && profileExpenses >= 0 ? profileIncome - profileExpenses : null;
  const profileCompletionItems = [
    wealthProfile?.first_name,
    onboarding?.age,
    onboarding?.situation_pro || wealthProfile?.investor_profile,
    wealthProfile?.motivation,
    wealthProfile?.horizon,
    wealthProfile?.risk_level,
    wealthProfile?.main_currency,
    profileIncome > 0,
    profileExpenses > 0,
  ];
  const profileCompletedCount = profileCompletionItems.filter(Boolean).length;
  const profileCompletionPercent = Math.round(
    (profileCompletedCount / profileCompletionItems.length) * 100
  );
  const profileNarrative = `${compactText(
    wealthProfile?.first_name,
    "Ton profil"
  )} construit un projet ${compactText(
    wealthProfile?.motivation,
    "patrimonial"
  ).toLowerCase()} avec un horizon ${compactText(
    wealthProfile?.horizon,
    "a preciser"
  ).toLowerCase()} et un profil ${compactText(
    wealthProfile?.risk_level,
    "a definir"
  ).toLowerCase()}.`;
  const eliteChartsEnabled = planAllows(currentPlan, "ELITE");
  const legacyNavigationEnabled = planAllows(currentPlan, "LIBERTY");
  const progressionMissions = product?.missions || [];
  const progressionTimelineItems = progressionTimeline?.timeline || [];
  const hasModule = (key: string) =>
    visibleModules.has(key);
  const maxAssets = product?.entitlements?.max_assets;
  const totalAssetsCount =
    product?.data_profile?.total_assets_count ??
    portfolio.length +
      (realEstate?.assets?.length || 0) +
      (yieldAssets?.assets?.length || 0) +
      (ventureAssets?.assets?.length || 0);
  const canAddPortfolioAsset =
    maxAssets === null ||
    maxAssets === undefined ||
    totalAssetsCount < Number(maxAssets);
  const navigation: NavigationItem[] = [
    {
      key: "home",
      label: "Home",
      description: "Vue globale",
    },
    {
      key: "opportunities",
      label: "Opportunites",
      description: "Signaux",
    },
    {
      key: "ai",
      label: "Conseiller",
      description: "Conseiller",
    },
    {
      key: "finances",
      label: "Finances",
      description: "Cashflow",
    },
    {
      key: "investments",
      label: "Investments",
      description: "Allocation",
    },
    {
      key: "real_estate",
      label: "Immobilier",
      description: "Biens",
    },
    {
      key: "ventures",
      label: "Business",
      description: "Ventures",
    },
    ...(legacyNavigationEnabled
      ? [
          {
            key: "legacy" as const,
            label: "Dynasty",
            description: "Transmission",
          },
        ]
      : []),
    {
      key: "progression",
      label: "Progression",
      description: "Statut",
    },
    {
      key: "profile",
      label: "Mon Profil",
      description: "Profil",
    },
    {
      key: "billing",
      label: "Plan & Facturation",
      description: "Abonnement",
    },
    {
      key: "settings",
      label: "Family Office",
      description: "Gouvernance",
    },
  ];
  const handleUpdateOnboarding = async () => {
    const profile = (await loadWealthProfile()) || wealthProfile || {};

    setFormModal({
      kind: "onboarding",
      title: "Modifier le profil utilisateur",
      description: "Mets a jour les informations issues de l'onboarding et enrichis ton profil patrimonial.",
      values: {
        first_name: profile.first_name || "",
        bio: profile.bio || "",
        age: String(onboarding?.age ?? ""),
        situation_pro: onboarding?.situation_pro || profile.investor_profile || "",
        revenus_mensuels: String(
          onboarding?.revenus_mensuels ?? onboarding?.monthly_income ?? 0
        ),
        charges_mensuelles: String(
          onboarding?.charges_mensuelles ?? onboarding?.monthly_expenses ?? 0
        ),
        motivation: profile.motivation || "",
        horizon: profile.horizon || "5-10 ans",
        risk_level: profile.risk_level || "equilibre",
        main_currency: profile.main_currency || "EUR",
        has_children: profile.has_children ? "true" : "false",
        transmission_goal: profile.transmission_goal || "",
        expatriation_interest: profile.expatriation_interest || "",
        governance_need: profile.governance_need || "",
        confidentiality_need: profile.confidentiality_need || "",
        family_strategy: profile.family_strategy || "",
      },
    });
  };

  const handleUpgradePlan = async (plan: string) => {
    try {
      const data = await apiRequest<{ url?: string }>("/billing/create-checkout-session", token, {
        method: "POST",
        body: JSON.stringify({ plan }),
      });

      if (data.url) {
        window.location.href = data.url;
      } else {
        showToast("Paiement indisponible pour le moment.", "error");
      }
    } catch (err) {
      console.error(err);
      const message = err instanceof Error ? err.message : "";
      const missingPrice = message.match(/STRIPE_PRICE_[A-Z_]+/)?.[0];

      showToast(
        missingPrice
          ? `Abonnement indisponible pour le moment: l'offre ${missingPrice} doit encore etre activee.`
          : "Impossible d'ouvrir l'abonnement pour le moment. Reessaie dans quelques instants.",
        "error"
      );
    }
  };

  const handleOpenBillingPortal = async () => {
    try {
      const data = await apiRequest<{ url?: string }>("/billing/customer-portal", token, {
        method: "POST",
      });

      if (data.url) {
        window.location.href = data.url;
      } else {
        showToast("Portail abonnement indisponible pour le moment.", "error");
      }
    } catch (err) {
      console.error(err);
      showToast("Impossible d'ouvrir le portail abonnement pour le moment.", "error");
    }
  };

  const handleCreateWorkspace = async () => {
    setFormModal({
      kind: "workspace",
      title: "Nouvel espace",
      description: "Cree un espace Family Office clair et partageable.",
      values: { name: "Family Office" },
    });
  };

  const handleInviteWorkspaceMember = async (workspaceId: number) => {
    setFormModal({
      kind: "invite",
      title: "Inviter un membre",
      description: "Ajoute une personne avec le role adapte a ton espace.",
      values: { email: "", role: "member" },
      context: { workspaceId },
    });
  };

  const handleSwitchWorkspace = async (workspaceId: number) => {
    if (typeof window !== "undefined") {
      localStorage.setItem("activeWorkspaceId", String(workspaceId));
    }

    await refreshAll();
  };

  const savePortfolioAsset = async (
    url: string,
    method: "POST" | "PUT",
    payload: PortfolioPayload
  ) => {
    await apiRequest(url, token, {
      method,
      body: JSON.stringify(payload),
    });

    await refreshAfterMutation();
  };

  const handleAddPortfolioAsset = async (assetTypePreset?: string) => {
    if (!canAddPortfolioAsset) {
      showToast(
        `Limite du plan atteinte (${totalAssetsCount}/${maxAssets}). Passe au plan superieur pour ajouter plus d'assets.`,
        "error"
      );
      return;
    }

    setFormModal({
      kind: "portfolio",
      title: "Ajouter un actif",
      description: "Actions, ETF, crypto, commodities ou devises. Les autres categories ont leur espace dedie.",
      values: {
        asset_name: "",
        asset_type: normalizePortfolioAssetTypePreset(assetTypePreset),
        quantity: "1",
        purchase_price: "",
      },
    });
  };

  const handleUpdatePortfolioAsset = async (asset: PortfolioAsset) => {
    setFormModal({
      kind: "portfolio",
      title: "Modifier l'actif",
      description: "Garde cette ligne dans les categories financieres dediees au portefeuille.",
      values: {
        asset_name: asset.asset_name || asset.name || "",
        asset_type: asset.asset_type || asset.type || "",
        quantity: String(asset.quantity ?? 1),
        purchase_price: String(asset.purchase_price ?? 0),
      },
      context: { id: asset.id },
    });
  };

  const handleDeletePortfolioAsset = async (id: number) => {
    setConfirmModal({
      title: "Supprimer cet actif ?",
      description: "Cette action retire la ligne du portefeuille.",
      onConfirm: async () => {
        await apiRequest(`/portfolio/${id}`, token, { method: "DELETE" });
        await refreshAfterMutation();
        showToast("Actif supprime.", "success");
      },
    });
  };

  const handleAddFinance = async (data: FinancePayload) => {
    await apiRequest("/finance/", token, {
      method: "POST",
      body: JSON.stringify(data),
    });

    await refreshAfterMutation();
  };

  const handleDeleteFinance = async (id: number) => {
    await apiRequest(`/finance/${id}`, token, {
      method: "DELETE",
    });

    await refreshAfterMutation();
  };

  const handleUpdateFinance = async (item: FinanceEntry) => {
    await apiRequest(`/finance/${item.id}`, token, {
      method: "PUT",
      body: JSON.stringify({
        name: item.name || item.label || "",
        amount: Number(item.amount || 0),
      }),
    });

    await refreshAfterMutation();
  };

  const handleAddRealEstate = async (type: RealEstateType) => {
    setFormModal({
      kind: "real_estate",
      title: "Ajouter un bien",
      description: "Suis achat, valeur cible, plus-value et rendement dans un format unifie.",
      values: {
        name: "",
        residence_type:
          type === "primary_residence" ? "Résidence principale" : "",
        property_kind: "Maison/Villa",
        asset_usage: type === "primary_residence" ? "Usage privé" : "",
        purchase_price: "0",
        estimated_value: "0",
        resale_price: "0",
        monthly_rent: "0",
        monthly_charges: "0",
        notes: "",
      },
      context: { propertyType: type },
    });
  };

  const handleUpdateRealEstate = async (asset: RealEstateAsset) => {
    setFormModal({
      kind: "real_estate",
      title: "Modifier le bien",
      description: "Mets a jour les chiffres sans changer la logique de calcul.",
      values: {
        name: asset.name || "",
        residence_type: "",
        property_kind: "",
        asset_usage: "",
        purchase_price: String(asset.purchase_price ?? 0),
        estimated_value: String(asset.estimated_value ?? asset.target_value ?? 0),
        resale_price: String(asset.resale_price ?? 0),
        monthly_rent: String(asset.monthly_rent ?? 0),
        monthly_charges: String(asset.monthly_charges ?? 0),
        notes: asset.notes || "",
      },
      context: { id: asset.id, propertyType: asset.property_type },
    });
  };

  const handleDeleteRealEstate = async (id: number) => {
    setConfirmModal({
      title: "Supprimer ce bien ?",
      description: "Cette action retire ce bien de la rubrique immobilier.",
      onConfirm: async () => {
        await apiRequest(`/real-estate/${id}`, token, { method: "DELETE" });
        await refreshAfterMutation();
        showToast("Bien supprime.", "success");
      },
    });
  };

  const handleAddYieldAsset = async (type: YieldAssetType) => {
    setFormModal({
      kind: "yield",
      title: "Ajouter un investissement",
      description: "Renseigne capital, taux moyen et duree dans un format homogene.",
      values: {
        name: "",
        principal: "0",
        average_rate: "0",
        duration_months: "12",
        notes: "",
      },
      context: { yieldType: type },
    });
  };

  const handleUpdateYieldAsset = async (asset: YieldAsset) => {
    setFormModal({
      kind: "yield",
      title: "Modifier l'investissement",
      description: "Mets a jour capital, taux moyen et duree.",
      values: {
        name: asset.name || "",
        principal: String(asset.principal ?? 0),
        average_rate: String(asset.average_rate ?? 0),
        duration_months: String(asset.duration_months ?? 12),
        notes: asset.notes || "",
      },
      context: { id: asset.id, yieldType: asset.asset_type },
    });
  };

  const handleDeleteYieldAsset = async (id: number) => {
    setConfirmModal({
      title: "Supprimer cet investissement ?",
      description: "Cette action retire cet actif de la rubrique rendement prive.",
      onConfirm: async () => {
        await apiRequest(`/yield-assets/${id}`, token, { method: "DELETE" });
        await refreshAfterMutation();
        showToast("Investissement supprime.", "success");
      },
    });
  };

  const handleAddVentureAsset = async (type: VentureAssetType) => {
    setFormModal({
      kind: "venture",
      title: "Ajouter un business",
      description: "Suis chiffre d'affaires, charges, levees, dettes et valorisation.",
      values: {
        name: "",
        revenue: "0",
        charges: "0",
        fundraising: "0",
        debts: "0",
        valuation: "0",
        notes: "",
      },
      context: { ventureType: type },
    });
  };

  const handleUpdateVentureAsset = async (asset: VentureAsset) => {
    setFormModal({
      kind: "venture",
      title: "Modifier le business",
      description: "Mets a jour les donnees d'exploitation sans changer le calcul.",
      values: {
        name: asset.name || "",
        revenue: String(asset.revenue ?? 0),
        charges: String(asset.charges ?? 0),
        fundraising: String(asset.fundraising ?? 0),
        debts: String(asset.debts ?? 0),
        valuation: String(asset.valuation ?? 0),
        notes: asset.notes || "",
      },
      context: { id: asset.id, ventureType: asset.asset_type },
    });
  };

  const handleDeleteVentureAsset = async (id: number) => {
    setConfirmModal({
      title: "Supprimer ce business ?",
      description: "Cette action retire cette ligne de la rubrique Business & Ventures.",
      onConfirm: async () => {
        await apiRequest(`/venture-assets/${id}`, token, { method: "DELETE" });
        await refreshAfterMutation();
        showToast("Business supprime.", "success");
      },
    });
  };

  const requireName = (value?: string) => {
    const trimmed = String(value || "").trim();
    return trimmed.length > 0 ? trimmed : null;
  };

  const handleSubmitModal = async () => {
    if (!formModal) return;

    const values = formModal.values;

    try {
      setModalLoading(true);

      if (formModal.kind === "onboarding") {
        const age = toNullableNumber(values.age);
        const revenusMensuels = toNullableNumber(values.revenus_mensuels) ?? 0;
        const chargesMensuelles = toNullableNumber(values.charges_mensuelles) ?? 0;
        const goals = [values.motivation, values.transmission_goal]
          .map((item) => String(item || "").trim())
          .filter(Boolean);

        await apiRequest("/auth/onboarding/update", token, {
          method: "PUT",
          body: JSON.stringify({
            age,
            situation_pro: values.situation_pro || null,
            revenus_mensuels: revenusMensuels,
            charges_mensuelles: chargesMensuelles,
          }),
        });

        await apiRequest("/profile/me", token, {
          method: "PUT",
          body: JSON.stringify({
            first_name: values.first_name || null,
            bio: values.bio || null,
            avatar_url: wealthProfile?.avatar_url || null,
            goals,
            horizon: values.horizon || null,
            investor_profile: values.situation_pro || null,
            risk_level: values.risk_level || null,
            main_currency: values.main_currency || "EUR",
            motivation: values.motivation || null,
            has_children: values.has_children === "true",
            transmission_goal: values.transmission_goal || null,
            expatriation_interest: values.expatriation_interest || null,
            governance_need: values.governance_need || null,
            confidentiality_need: values.confidentiality_need || null,
            family_strategy: values.family_strategy || null,
          }),
        });

        await loadWealthProfile();
        await refreshAfterMutation();
        showToast("Profil utilisateur mis a jour.", "success");
      }

      if (formModal.kind === "workspace") {
        const name = requireName(values.name);
        if (!name) throw new Error("Nom requis");

        const data = await apiRequest<{ workspace_id?: number }>("/workspaces/", token, {
          method: "POST",
          body: JSON.stringify({ name }),
        });

        if (data.workspace_id && typeof window !== "undefined") {
          localStorage.setItem("activeWorkspaceId", String(data.workspace_id));
        }

        await refreshAll();
        showToast("Espace cree.", "success");
      }

      if (formModal.kind === "invite") {
        const email = requireName(values.email);
        const role = values.role || "member";
        const workspaceId = formModal.context?.workspaceId;
        if (!email || !workspaceId) throw new Error("Invitation incomplete");

        const data = await apiRequest<{ invite_url?: string; token?: string }>(
          `/workspaces/${workspaceId}/invite`,
          token,
          {
            method: "POST",
            body: JSON.stringify({ email, role }),
          }
        );

        await refreshAll();
        showToast(
          data.invite_url
            ? `Invitation creee. Lien: ${data.invite_url}`
            : "Invitation creee.",
          "success"
        );
      }

      if (formModal.kind === "portfolio") {
        const assetName = requireName(values.asset_name);
        const assetType = requireName(values.asset_type);
        const quantity = parsePositiveNumber(values.quantity);
        const purchasePrice = parsePositiveNumber(values.purchase_price);

        if (!assetName) throw new Error("Nom d'actif requis.");
        if (!assetType) throw new Error("Classe d'actif requise.");
        if (quantity === null) throw new Error("Quantite invalide: saisis un nombre superieur a 0.");
        if (purchasePrice === null) throw new Error("Prix d'achat invalide: saisis un nombre superieur a 0.");

        if (isRealEstatePortfolioType(assetType)) {
          throw new Error("Cette categorie se gere dans son module dedie.");
        }

        await savePortfolioAsset(
          formModal.context?.id ? `/portfolio/${formModal.context.id}` : "/portfolio/",
          formModal.context?.id ? "PUT" : "POST",
          {
            asset_name: assetName,
            asset_type: assetType,
            quantity,
            purchase_price: purchasePrice,
          }
        );
        showToast("Portefeuille mis a jour.", "success");
      }

      if (formModal.kind === "real_estate") {
        const propertyType = formModal.context?.propertyType;
        const name = requireName(values.name);
        const purchasePrice = parseNonNegativeNumber(values.purchase_price);
        const estimatedValue = parseNonNegativeNumber(values.estimated_value);
        const resalePrice = parseNonNegativeNumber(values.resale_price);
        const monthlyRent = parseNonNegativeNumber(values.monthly_rent);
        const monthlyCharges = parseNonNegativeNumber(values.monthly_charges);

        if (
          !propertyType ||
          !name ||
          purchasePrice === null ||
          estimatedValue === null ||
          resalePrice === null ||
          monthlyRent === null ||
          monthlyCharges === null
        ) {
          throw new Error("Donnees immobilieres invalides");
        }

        const payload: RealEstatePayload = {
          property_type: propertyType,
          name,
          purchase_price: purchasePrice,
          estimated_value: estimatedValue,
          resale_price: resalePrice,
          monthly_rent: monthlyRent,
          monthly_charges: monthlyCharges,
          notes: buildStructuredNotes(values, [
            ["Type de résidence", values.residence_type],
            ["Type de bien", values.property_kind],
            ["Usage", values.asset_usage],
          ]),
        };

        await apiRequest(
          formModal.context?.id
            ? `/real-estate/${formModal.context.id}`
            : "/real-estate/",
          token,
          {
            method: formModal.context?.id ? "PUT" : "POST",
            body: JSON.stringify(payload),
          }
        );
        await refreshAfterMutation();
        showToast("Immobilier mis a jour.", "success");
      }

      if (formModal.kind === "yield") {
        const assetType = formModal.context?.yieldType;
        const name = requireName(values.name);
        const principal = parseNonNegativeNumber(values.principal);
        const averageRate = parseNonNegativeNumber(values.average_rate);
        const durationMonths = parsePositiveNumber(values.duration_months);

        if (!assetType || !name || principal === null || averageRate === null || durationMonths === null) {
          throw new Error("Donnees invalides");
        }

        const payload: YieldAssetPayload = {
          asset_type: assetType,
          name,
          principal,
          average_rate: averageRate,
          duration_months: Math.round(durationMonths),
          notes: values.notes || null,
        };

        await apiRequest(
          formModal.context?.id
            ? `/yield-assets/${formModal.context.id}`
            : "/yield-assets/",
          token,
          {
            method: formModal.context?.id ? "PUT" : "POST",
            body: JSON.stringify(payload),
          }
        );
        await refreshAfterMutation();
        showToast("Investissement mis a jour.", "success");
      }

      if (formModal.kind === "venture") {
        const assetType = formModal.context?.ventureType;
        const name = requireName(values.name);
        const revenue = parseNonNegativeNumber(values.revenue);
        const charges = parseNonNegativeNumber(values.charges);
        const fundraising = parseNonNegativeNumber(values.fundraising);
        const debts = parseNonNegativeNumber(values.debts);
        const valuation = parseNonNegativeNumber(values.valuation);

        if (
          !assetType ||
          !name ||
          revenue === null ||
          charges === null ||
          fundraising === null ||
          debts === null ||
          valuation === null
        ) {
          throw new Error("Donnees business invalides");
        }

        const payload: VentureAssetPayload = {
          asset_type: assetType,
          name,
          revenue,
          charges,
          fundraising,
          debts,
          valuation,
          notes: values.notes || null,
        };

        await apiRequest(
          formModal.context?.id
            ? `/venture-assets/${formModal.context.id}`
            : "/venture-assets/",
          token,
          {
            method: formModal.context?.id ? "PUT" : "POST",
            body: JSON.stringify(payload),
          }
        );
        await refreshAfterMutation();
        showToast("Business mis a jour.", "success");
      }

      setFormModal(null);
      if (typeof window !== "undefined") {
        window.requestAnimationFrame(() => {
          window.scrollTo({ top: 0, behavior: "smooth" });
        });
      }
    } catch (err) {
      if (!isUserValidationError(err)) {
        console.error(err);
      }
      showToast(
        err instanceof Error ? err.message : "Impossible d'enregistrer.",
        "error"
      );
    } finally {
      setModalLoading(false);
    }
  };

  const handleConfirmModal = async () => {
    if (!confirmModal) return;

    try {
      setModalLoading(true);
      await confirmModal.onConfirm();
      setConfirmModal(null);
    } catch (err) {
      console.error(err);
      showToast("Impossible de supprimer cet element.", "error");
    } finally {
      setModalLoading(false);
    }
  };

  const renderFormFields = () => {
    if (!formModal) return null;
    const values = formModal.values;

    if (formModal.kind === "invite") {
      return (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <TextField label="Email" value={values.email || ""} onChange={(value) => updateModalValue("email", value)} />
          <SelectField
            label="Role"
            value={values.role || "member"}
            onChange={(value) => updateModalValue("role", value)}
            options={[
              { label: "Owner", value: "owner" },
              { label: "Admin", value: "admin" },
              { label: "Member", value: "member" },
              { label: "Viewer", value: "viewer" },
            ]}
          />
        </div>
      );
    }

    if (formModal.kind === "onboarding") {
      return (
        <div className="space-y-5">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <TextField label="Prenom" value={values.first_name || ""} onChange={(value) => updateModalValue("first_name", value)} />
            <TextField label="Age" type="number" value={values.age || ""} onChange={(value) => updateModalValue("age", value)} />
            <SelectField
              label="Situation professionnelle"
              value={values.situation_pro || ""}
              onChange={(value) => updateModalValue("situation_pro", value)}
              options={[
                { label: "A renseigner", value: "" },
                { label: "Salarie", value: "salarie" },
                { label: "Independant", value: "independant" },
                { label: "Entrepreneur", value: "entrepreneur" },
                { label: "Investisseur", value: "investisseur" },
                { label: "Etudiant", value: "etudiant" },
                { label: "Retraite", value: "retraite" },
              ]}
            />
            <SelectField
              label="Enfants"
              value={values.has_children || "false"}
              onChange={(value) => updateModalValue("has_children", value)}
              options={[
                { label: "Non", value: "false" },
                { label: "Oui", value: "true" },
              ]}
            />
            <TextField label="Revenus mensuels" type="number" value={values.revenus_mensuels || "0"} onChange={(value) => updateModalValue("revenus_mensuels", value)} />
            <TextField label="Charges mensuelles" type="number" value={values.charges_mensuelles || "0"} onChange={(value) => updateModalValue("charges_mensuelles", value)} />
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <SelectField
              label="Objectif principal"
              value={values.motivation || ""}
              onChange={(value) => updateModalValue("motivation", value)}
              options={[
                { label: "A renseigner", value: "" },
                { label: "Liberte financiere", value: "liberte financiere" },
                { label: "Augmenter mes revenus", value: "augmenter mes revenus" },
                { label: "Consolider mon patrimoine", value: "consolider mon patrimoine" },
                { label: "Transmission familiale", value: "transmission familiale" },
                { label: "Revenus passifs", value: "revenus passifs" },
              ]}
            />
            <SelectField
              label="Horizon"
              value={values.horizon || "5-10 ans"}
              onChange={(value) => updateModalValue("horizon", value)}
              options={[
                { label: "1 - 3 ans", value: "1-3 ans" },
                { label: "3 - 5 ans", value: "3-5 ans" },
                { label: "5 - 10 ans", value: "5-10 ans" },
                { label: "10 ans et plus", value: "10 ans et plus" },
              ]}
            />
            <SelectField
              label="Profil de risque"
              value={values.risk_level || "equilibre"}
              onChange={(value) => updateModalValue("risk_level", value)}
              options={[
                { label: "Prudent", value: "prudent" },
                { label: "Equilibre", value: "equilibre" },
                { label: "Dynamique", value: "dynamique" },
              ]}
            />
            <SelectField
              label="Devise"
              value={values.main_currency || "EUR"}
              onChange={(value) => updateModalValue("main_currency", value)}
              options={[
                { label: "EUR", value: "EUR" },
                { label: "USD", value: "USD" },
                { label: "CAD", value: "CAD" },
                { label: "CHF", value: "CHF" },
                { label: "GBP", value: "GBP" },
              ]}
            />
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <TextField label="Bio courte" value={values.bio || ""} onChange={(value) => updateModalValue("bio", value)} />
            <TextField label="Objectif de transmission" value={values.transmission_goal || ""} onChange={(value) => updateModalValue("transmission_goal", value)} />
            <SelectField
              label="Mobilite internationale"
              value={values.expatriation_interest || ""}
              onChange={(value) => updateModalValue("expatriation_interest", value)}
              options={[
                { label: "A renseigner", value: "" },
                { label: "Non prioritaire", value: "non prioritaire" },
                { label: "A etudier", value: "a etudier" },
                { label: "Prioritaire", value: "prioritaire" },
              ]}
            />
            <SelectField
              label="Besoin de gouvernance"
              value={values.governance_need || ""}
              onChange={(value) => updateModalValue("governance_need", value)}
              options={[
                { label: "A renseigner", value: "" },
                { label: "Simple", value: "simple" },
                { label: "Structure", value: "structure" },
                { label: "Familial avance", value: "familial avance" },
              ]}
            />
            <SelectField
              label="Confidentialite"
              value={values.confidentiality_need || ""}
              onChange={(value) => updateModalValue("confidentiality_need", value)}
              options={[
                { label: "A renseigner", value: "" },
                { label: "Standard", value: "standard" },
                { label: "Renforcee", value: "renforcee" },
                { label: "Tres elevee", value: "tres elevee" },
              ]}
            />
            <TextField label="Strategie familiale" value={values.family_strategy || ""} onChange={(value) => updateModalValue("family_strategy", value)} />
          </div>
        </div>
      );
    }

    if (formModal.kind === "workspace") {
      return (
        <TextField label="Nom de l'espace" value={values.name || ""} onChange={(value) => updateModalValue("name", value)} />
      );
    }

    if (formModal.kind === "portfolio") {
      return (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <TextField label="Nom de l'actif" value={values.asset_name || ""} onChange={(value) => updateModalValue("asset_name", value)} placeholder="AAPL, BTC, EUR/USD" />
          <SelectField
            label="Classe d'actif"
            value={values.asset_type || ""}
            onChange={(value) => updateModalValue("asset_type", value)}
            options={[
              { label: "Action", value: "STOCK" },
              { label: "ETF", value: "ETF" },
              { label: "Crypto", value: "CRYPTO" },
              { label: "Forex", value: "FOREX" },
              { label: "Commodities", value: "COMMODITIES" },
            ]}
          />
          <TextField label="Quantité" type="number" value={values.quantity || "1"} onChange={(value) => updateModalValue("quantity", value)} />
          <TextField label="Prix d'achat unitaire" type="number" value={values.purchase_price || "0"} onChange={(value) => updateModalValue("purchase_price", value)} />
        </div>
      );
    }

    if (formModal.kind === "real_estate") {
      const propertyType = formModal.context?.propertyType;

      return (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <TextField label="Nom du bien" value={values.name || ""} onChange={(value) => updateModalValue("name", value)} />
          {propertyType === "primary_residence" && (
            <SelectField
              label="Type de résidence"
              value={values.residence_type || "Résidence principale"}
              onChange={(value) => updateModalValue("residence_type", value)}
              options={[
                { label: "Résidence principale", value: "Résidence principale" },
                { label: "Résidence secondaire", value: "Résidence secondaire" },
                { label: "Résidence partagée", value: "Résidence partagée" },
              ]}
            />
          )}
          <SelectField
            label="Type de bien"
            value={values.property_kind || "Maison/Villa"}
            onChange={(value) => updateModalValue("property_kind", value)}
            options={[
              { label: "Maison / Villa", value: "Maison/Villa" },
              { label: "Appartement", value: "Appartement" },
              { label: "Bureaux", value: "Bureaux" },
              { label: "Locaux commerciaux", value: "Locaux commerciaux" },
              { label: "Autre", value: "Autre" },
            ]}
          />
          {(propertyType === "flip" || propertyType === "rental") && (
            <SelectField
              label="Usage"
              value={values.asset_usage || "Usage privé"}
              onChange={(value) => updateModalValue("asset_usage", value)}
              options={[
                { label: "Usage privé", value: "Usage privé" },
                { label: "Usage commercial", value: "Usage commercial" },
              ]}
            />
          )}
          <TextField label="Prix d'achat" type="number" value={values.purchase_price || "0"} onChange={(value) => updateModalValue("purchase_price", value)} />
          <TextField label="Valeur estimée / cible" type="number" value={values.estimated_value || "0"} onChange={(value) => updateModalValue("estimated_value", value)} />
          <TextField label="Prix de revente cible" type="number" value={values.resale_price || "0"} onChange={(value) => updateModalValue("resale_price", value)} />
          <TextField label="Loyer mensuel" type="number" value={values.monthly_rent || "0"} onChange={(value) => updateModalValue("monthly_rent", value)} />
          <TextField label="Charges mensuelles" type="number" value={values.monthly_charges || "0"} onChange={(value) => updateModalValue("monthly_charges", value)} />
          <div className="sm:col-span-2">
            <TextField label="Notes" value={values.notes || ""} onChange={(value) => updateModalValue("notes", value)} />
          </div>
        </div>
      );
    }

    if (formModal.kind === "yield") {
      return (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <TextField label="Nom" value={values.name || ""} onChange={(value) => updateModalValue("name", value)} />
          <TextField label="Capital prêté / investi" type="number" value={values.principal || "0"} onChange={(value) => updateModalValue("principal", value)} />
          <TextField label="Taux moyen annuel" type="number" value={values.average_rate || "0"} onChange={(value) => updateModalValue("average_rate", value)} />
          <TextField label="Durée en mois" type="number" value={values.duration_months || "12"} onChange={(value) => updateModalValue("duration_months", value)} />
          <div className="sm:col-span-2">
            <TextField label="Notes" value={values.notes || ""} onChange={(value) => updateModalValue("notes", value)} />
          </div>
        </div>
      );
    }

    if (formModal.kind === "venture") {
      return (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <TextField label="Nom" value={values.name || ""} onChange={(value) => updateModalValue("name", value)} />
          <TextField label="Chiffre d'affaires" type="number" value={values.revenue || "0"} onChange={(value) => updateModalValue("revenue", value)} />
          <TextField label="Charges" type="number" value={values.charges || "0"} onChange={(value) => updateModalValue("charges", value)} />
          <TextField label="Levée de fonds" type="number" value={values.fundraising || "0"} onChange={(value) => updateModalValue("fundraising", value)} />
          <TextField label="Dettes" type="number" value={values.debts || "0"} onChange={(value) => updateModalValue("debts", value)} />
          <TextField label="Valorisation" type="number" value={values.valuation || "0"} onChange={(value) => updateModalValue("valuation", value)} />
          <div className="sm:col-span-2">
            <TextField label="Notes" value={values.notes || ""} onChange={(value) => updateModalValue("notes", value)} />
          </div>
        </div>
      );
    }

    return null;
  };

  return (
    <main className="min-h-screen bg-black pb-32 text-white lg:pb-24">
      <WealthToast
        message={toast?.message}
        type={toast?.type}
        onClose={() => setToast(null)}
      />

      <WealthModal
        open={Boolean(formModal)}
        title={formModal?.title || ""}
        description={formModal?.description}
        onClose={closeFormModal}
        footer={
          <>
            <ActionButton variant="secondary" onClick={closeFormModal}>
              Annuler
            </ActionButton>
            <ActionButton onClick={handleSubmitModal} disabled={modalLoading}>
              {modalLoading ? "Enregistrement..." : "Valider"}
            </ActionButton>
          </>
        }
      >
        {renderFormFields()}
      </WealthModal>

      <WealthModal
        open={Boolean(confirmModal)}
        title={confirmModal?.title || ""}
        description={confirmModal?.description}
        eyebrow="Confirmation"
        onClose={() => setConfirmModal(null)}
        footer={
          <>
            <ActionButton variant="secondary" onClick={() => setConfirmModal(null)}>
              Annuler
            </ActionButton>
            <ActionButton variant="danger" onClick={handleConfirmModal} disabled={modalLoading}>
              Supprimer
            </ActionButton>
          </>
        }
      >
        <p className="text-sm text-gray-400">
          Confirme uniquement si tu veux vraiment retirer cet element.
        </p>
      </WealthModal>

      <div className="sticky top-0 z-20 backdrop-blur-xl bg-black/80 border-b border-white/10">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <Header dashboard={dashboard} onUpgrade={handleUpgradePlan} />
        </div>
      </div>

      <div className="mx-auto grid max-w-7xl grid-cols-1 gap-5 p-4 lg:grid-cols-[260px_1fr]">
        <aside className="hidden lg:sticky lg:top-24 lg:block lg:h-[calc(100vh-7rem)]">
          <div className="rounded-2xl border border-white/10 bg-zinc-950/90 p-3">
            <div className="mb-3 px-2">
              <p className="text-xs uppercase tracking-widest text-[#3fa9f5]">
                Navigation
              </p>
              <p className="mt-1 text-sm text-gray-400">
                Summary first. Drill-down second.
              </p>
            </div>

            <nav className="no-scrollbar flex gap-2 overflow-x-auto pb-1 lg:max-h-[calc(100vh-12rem)] lg:flex-col lg:overflow-y-auto lg:pr-1">
              {navigation.map((item) => {
                const active = item.key === activeSection;

                return (
                  <button
                    key={item.key}
                    onClick={() => goToSection(item.key)}
                    className={`min-w-[150px] rounded-xl border px-3 py-3 text-left transition lg:min-w-0 ${
                      active
                        ? "border-[#3fa9f5]/60 bg-[#3fa9f5]/15 text-white"
                        : "border-white/10 bg-white/[0.03] text-gray-300 hover:border-white/20"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-bold">{item.label}</span>
                      {item.locked && (
                        <span className="rounded-full bg-white/10 px-2 py-0.5 text-[10px] text-gray-400">
                          lock
                        </span>
                      )}
                    </div>
                    <p className="mt-1 text-xs text-gray-500">
                      {item.description}
                    </p>
                  </button>
                );
              })}
            </nav>
          </div>
        </aside>

        <div className="min-w-0 space-y-6">
          {activeSection === "home" && (
            <div className="space-y-6">
              <SectionHeader
                eyebrow="Accueil"
                title="Ton cockpit du jour"
                description="Une vue complete mais lisible: trajectoire, decisions, domaines patrimoniaux et prochaine action utile."
              />

              <WealthIntelligencePanel product={product} />

              <FutureIntelligencePanel product={product} />

              <DecisionIntelligencePanel product={product} />

              <FamilyOfficeIntelligencePanel product={product} />

              {planAllows(currentPlan, "ELITE") ? (
                <FamilyOfficeCeoPanel product={product} />
              ) : (
                <LockedSection
                  title="Family Office CEO"
                  description="Debloque en ELITE le burn rate, la marge mensuelle, le runway et la lecture operationnelle de ta trajectoire."
                  onUpgrade={handleUpgradePlan}
                  plan="elite"
                />
              )}

              {!planAllows(currentPlan, "LIBERTY") && (
                <LockedSection
                  title="Arbitrages Family Office"
                  description="LIBERTY ajoute les priorites d'allocation, le board virtuel, les objectifs avances, les comptes enfants et la transmission."
                  onUpgrade={handleUpgradePlan}
                  plan="liberty"
                />
              )}

              {!planAllows(currentPlan, "LEGACY") && (
                <LockedSection
                  title="Dynasty Office"
                  description="Dynasty ouvre la projection generationnelle, la gouvernance familiale, la protection et les scenarios successoraux."
                  onUpgrade={handleUpgradePlan}
                  plan="legacy"
                />
              )}
            </div>
          )}

          {activeSection === "finances" && (
            <div className="space-y-6">
              <SectionHeader
                eyebrow="Finances"
                title="Financial Clarity"
                description="Cashflow, reste a vivre, epargne et dettes. Cette section clarifie ta marge de liberte mensuelle."
              />

              <section className="rounded-2xl border border-white/10 bg-zinc-950 p-5">
                <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="text-xs font-bold uppercase tracking-widest text-emerald-300">
                      Realite financiere actuelle
                    </p>
                    <h2 className="mt-1 text-2xl font-bold">Marge de liberte</h2>
                  </div>
                  <button
                    onClick={handleUpdateOnboarding}
                    className="rounded-xl border border-white/10 bg-white/[0.05] px-4 py-2 text-sm font-bold text-gray-100 transition hover:border-[#3fa9f5]/40 hover:bg-[#3fa9f5]/10"
                  >
                    Modifier le profil
                  </button>
                </div>
                <FinanceModule overview={financeOverview} />
              </section>

              <section className="grid grid-cols-1 gap-5 xl:grid-cols-2">
                <FinanceBlock title="Revenus" type="revenus" data={finance.revenus} onCreate={handleAddFinance} onDelete={handleDeleteFinance} onUpdate={handleUpdateFinance} />
                <FinanceBlock title="Charges" type="charges" data={finance.charges} onCreate={handleAddFinance} onDelete={handleDeleteFinance} onUpdate={handleUpdateFinance} />
                <FinanceBlock title="Epargne" type="epargne" data={finance.epargne} onCreate={handleAddFinance} onDelete={handleDeleteFinance} onUpdate={handleUpdateFinance} />
                <FinanceBlock title="Dettes" type="dettes" data={finance.dettes} onCreate={handleAddFinance} onDelete={handleDeleteFinance} onUpdate={handleUpdateFinance} />
              </section>

              <ChildAccountsPanel
                enabled={hasModule("child_accounts")}
                onUpgrade={handleUpgradePlan}
              />
            </div>
          )}

          {activeSection === "investments" && (
            <div className="space-y-6">
              <SectionHeader
                eyebrow="Investments"
                title="Allocation & multi-assets"
                description="Stocks, ETF, crypto, forex, commodities, diversification et exposition. Pas de trading complexe: uniquement pilotage patrimonial."
              />

              {hasModule("diversification") ? (
                <section className="grid grid-cols-1 gap-5">
                  {eliteChartsEnabled ? (
                    <RubricBreakdownChart
                      title="Repartition investissements"
                      description="Vue limitee aux rubriques de l'onglet Investments."
                      items={investmentRubrics}
                    />
                  ) : (
                    <LockedSection
                      title="Graphique Investments"
                      description="La repartition par rubrique de cet onglet est disponible a partir du plan Elite."
                      onUpgrade={handleUpgradePlan}
                      plan="elite"
                    />
                  )}
                </section>
              ) : (
                <LockedSection
                  title="Analytics d'allocation"
                  description="L'exposition avancee et les graphiques d'allocation se debloquent progressivement avec la phase Growth."
                  onUpgrade={handleUpgradePlan}
                  plan="gold"
                />
              )}

              <section className="rounded-2xl border border-white/10 bg-zinc-950 p-5">
                <h2 className="mb-4 text-2xl font-bold">Portfolio</h2>
                <PortfolioModule
                  portfolio={portfolio}
                  onAdd={handleAddPortfolioAsset}
                  onUpdate={handleUpdatePortfolioAsset}
                  onDelete={handleDeletePortfolioAsset}
                  opportunities={financialOpportunities}
                />
              </section>
            </div>
          )}

          {activeSection === "real_estate" && (
            <div className="space-y-6">
              <SectionHeader
                eyebrow="Immobilier"
                title="Biens & rendement"
                description="Residence principale, locatif, achat/revente, valorisation et plus-value potentielle."
              />

              {eliteChartsEnabled ? (
                <RubricBreakdownChart
                  title="Repartition immobilier"
                  description="Vue limitee aux rubriques de l'onglet Immobilier."
                  items={realEstateRubrics}
                />
              ) : (
                <LockedSection
                  title="Graphique immobilier"
                  description="La repartition par rubrique de cet onglet est disponible a partir du plan Elite."
                  onUpgrade={handleUpgradePlan}
                  plan="elite"
                />
              )}

              <RealEstateModule
                data={realEstate}
                onAdd={handleAddRealEstate}
                onUpdate={handleUpdateRealEstate}
                onDelete={handleDeleteRealEstate}
                opportunity={findOpportunity("real_estate")}
              />
            </div>
          )}

          {activeSection === "ventures" && (
            <div className="space-y-6">
              <SectionHeader
                eyebrow="Business & Ventures"
                title="Entreprises, startups et rendement prive"
                description="Une lecture investisseur: intelligence business, actifs suivis, puis opportunites a explorer."
              />

              <section className="rounded-2xl border border-white/10 bg-zinc-950 p-5">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div className="max-w-3xl">
                    <p className="text-xs font-bold uppercase tracking-widest text-emerald-300">
                      Business Intelligence
                    </p>
                    <h2 className="mt-2 text-2xl font-black text-white">
                      {compactText(businessNarrative?.title, "Lecture business")}
                    </h2>
                    <p className="mt-3 text-sm leading-relaxed text-gray-300">
                      {compactText(
                        businessNarrative?.text,
                        "La rubrique Business se construit a partir des actifs et investissements prives deja renseignes."
                      )}
                    </p>
                    {businessNarrative?.emphasis && (
                      <p className="mt-3 rounded-xl border border-emerald-300/20 bg-emerald-400/10 p-3 text-sm text-emerald-100">
                        {businessNarrative.emphasis}
                      </p>
                    )}
                  </div>

                  <div className="rounded-2xl border border-amber-300/20 bg-amber-300/10 p-4 lg:w-80">
                    <p className="text-xs font-bold uppercase tracking-widest text-amber-200">
                      Decision du moment
                    </p>
                    <h3 className="mt-2 text-lg font-black text-white">
                      {compactText(businessDecision?.title, "Structurer la prochaine action")}
                    </h3>
                    <p className="mt-2 text-sm leading-relaxed text-gray-300">
                      {compactText(
                        businessDecision?.description,
                        "Ajoute ou precise un actif business pour obtenir une lecture priorisee."
                      )}
                    </p>
                    <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                      <div className="rounded-xl border border-white/10 bg-black/20 p-3">
                        <p className="uppercase tracking-widest text-gray-500">Horizon</p>
                        <p className="mt-1 font-bold text-white">
                          {compactText(businessDecision?.timeframe, "A definir")}
                        </p>
                      </div>
                      <div className="rounded-xl border border-white/10 bg-black/20 p-3">
                        <p className="uppercase tracking-widest text-gray-500">Impact</p>
                        <p className="mt-1 font-bold text-white">
                          {compactText(businessDecision?.impact, "Pilotage")}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
                  {[
                    ["CA", businessMetrics.revenue],
                    ["Resultat", businessMetrics.result],
                    ["Dette", businessMetrics.debts],
                    ["Actifs prives", businessMetrics.private_capital],
                    ["Valeur business", businessMetrics.total_business_value],
                  ].map(([label, value]) => (
                    <div
                      key={String(label)}
                      className="rounded-2xl border border-white/10 bg-white/[0.04] p-4"
                    >
                      <p className="text-xs uppercase tracking-widest text-gray-500">
                        {label}
                      </p>
                      <p className="mt-2 text-xl font-black text-white">
                        {money.format(Number(value || 0))} EUR
                      </p>
                    </div>
                  ))}
                </div>
              </section>

              {eliteChartsEnabled ? (
                <RubricBreakdownChart
                  title="Repartition business"
                  description="Vue limitee aux rubriques de l'onglet Business."
                  items={businessRubrics}
                />
              ) : (
                <LockedSection
                  title="Graphique business"
                  description="La repartition par rubrique de cet onglet est disponible a partir du plan Elite."
                  onUpgrade={handleUpgradePlan}
                  plan="elite"
                />
              )}

              <VentureAssetsModule
                data={ventureAssets}
                onAdd={handleAddVentureAsset}
                onUpdate={handleUpdateVentureAsset}
                onDelete={handleDeleteVentureAsset}
                opportunities={categoryOpportunityItems.filter((item) =>
                  ["ai_business", "business", "startup", "franchise"].includes(
                    item.key || ""
                  )
                )}
              />

              <YieldInvestmentsModule
                data={yieldAssets}
                onAdd={handleAddYieldAsset}
                onUpdate={handleUpdateYieldAsset}
                onDelete={handleDeleteYieldAsset}
                opportunities={categoryOpportunityItems.filter((item) =>
                  ["crowdfunding", "private_equity"].includes(item.key || "")
                )}
              />

            </div>
          )}

          {activeSection === "opportunities" && (
            <div className="space-y-6">
              <SectionHeader
                eyebrow="Opportunites"
                title="Centre d'opportunites"
                description="Recherche, exploration et signaux centralises. Les pages metier restent dediees au pilotage."
              />

              <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-5">
                <div className="mb-4 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
                  <div>
                    <p className="text-xs font-bold uppercase tracking-widest text-[#3fa9f5]">
                      Explorateur d'opportunites
                    </p>
                    <h2 className="mt-1 text-2xl font-bold">Explorer manuellement</h2>
                    <p className="mt-1 text-sm text-gray-400">
                      Recherche par univers quand tu veux comparer plusieurs pistes.
                    </p>
                  </div>
                  <span className="text-xs uppercase tracking-widest text-gray-500">
                    Investissement / Immobilier / Business
                  </span>
                </div>

                <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
                  <OpportunityDiscoveryPanel
                    universe="investments"
                    title="Investissements"
                    description="Explorer les pistes d'allocation selon l'horizon, le risque, le portefeuille et les signaux disponibles."
                    plan={currentPlan}
                    token={token}
                  />

                  <OpportunityDiscoveryPanel
                    universe="real_estate"
                    title="Immobilier"
                    description="Explorer residence principale, locatif, achat-revente ou commercial avec une lecture de rendement et de risque."
                    plan={currentPlan}
                    token={token}
                  />

                  <OpportunityDiscoveryPanel
                    universe="business"
                    title="Business"
                    description="Explorer business digital, startup, franchise, reprise, crowdfunding et private equity selon ton contexte White Rock."
                    plan={currentPlan}
                    token={token}
                  />
                </div>
              </section>

              <OpportunitiesModule
                commandCenter={commandCenter}
                plan={currentPlan}
              />
            </div>
          )}

          {activeSection === "ai" && (
            <div className="space-y-6">
              <SectionHeader
                eyebrow="Conseiller patrimonial"
                title="Ethan"
                description="Intelligence patrimoniale active: contexte, decision et conversation dans une seule interface."
              />

              <section className="grid grid-cols-1 gap-5 xl:grid-cols-[1.2fr_0.8fr]">
                <div className="rounded-2xl border border-[#3fa9f5]/20 bg-gradient-to-br from-[#07111c] via-black to-[#101923] p-5">
                  <p className="text-xs font-bold uppercase tracking-widest text-[#8bd0ff]">
                    Daily Insight
                  </p>
                  <h2 className="mt-2 text-2xl font-black text-white">
                    {compactText(
                      product?.wealth_narrative?.memorable_insight ||
                        product?.board_briefing?.headline,
                      "Ethan garde le cap sur la prochaine decision utile."
                    )}
                  </h2>
                  <p className="mt-3 text-sm leading-relaxed text-gray-300">
                    {compactText(
                      product?.wealth_narrative?.why_it_matters ||
                        product?.decision_intelligence?.why_it_matters,
                      "La valeur de cette page est d'isoler ce qui merite vraiment ton attention."
                    )}
                  </p>

                  <div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-3">
                    {[
                      [
                        "Situation",
                        product?.decision_intelligence?.risk?.title ||
                          product?.board_briefing?.main_risk ||
                          "Lecture du contexte",
                        product?.decision_intelligence?.risk?.description ||
                          "Ethan part de ta situation actuelle avant de proposer une direction.",
                      ],
                      [
                        "Analyse",
                        product?.decision_intelligence?.opportunity?.title ||
                          product?.board_briefing?.main_opportunity ||
                          "Signal utile",
                        product?.decision_intelligence?.opportunity?.description ||
                          "Les signaux sont priorises pour eviter la dispersion.",
                      ],
                      [
                        "Decision",
                        product?.decision_intelligence?.decision?.title ||
                          "Decision du moment",
                        product?.decision_intelligence?.next_action ||
                          product?.decision_intelligence?.decision?.action ||
                          "Choisir une action simple et executable.",
                      ],
                    ].map(([label, title, description]) => (
                      <article
                        key={label}
                        className="rounded-2xl border border-white/10 bg-white/[0.04] p-4"
                      >
                        <p className="text-xs font-bold uppercase tracking-widest text-gray-500">
                          {label}
                        </p>
                        <h3 className="mt-2 font-bold text-white">
                          {compactText(title)}
                        </h3>
                        <p className="mt-2 text-xs leading-relaxed text-gray-400">
                          {compactText(description)}
                        </p>
                      </article>
                    ))}
                  </div>
                </div>

                <div className="space-y-5">
                  <section className="rounded-2xl border border-white/10 bg-zinc-950 p-5">
                    <p className="text-xs font-bold uppercase tracking-widest text-emerald-300">
                      Mode Ethan
                    </p>
                    <h3 className="mt-2 text-2xl font-black text-white">
                      {compactText(advisorContext?.mode, "Simple")}
                    </h3>
                    <p className="mt-2 text-sm leading-relaxed text-gray-400">
                      {compactText(
                        advisorContext?.depth,
                        "Un insight clair et une action utile."
                      )}
                    </p>
                  </section>

                  <section className="rounded-2xl border border-white/10 bg-zinc-950 p-5">
                    <p className="text-xs font-bold uppercase tracking-widest text-[#ffd21a]">
                      Ce qu'Ethan retient
                    </p>
                    <p className="mt-3 text-sm leading-relaxed text-gray-300">
                      {compactText(
                        advisorContext?.memory?.reading,
                        "Ethan construit progressivement une lecture fiable de ton contexte."
                      )}
                    </p>
                  </section>

                  <section className="rounded-2xl border border-white/10 bg-zinc-950 p-5">
                    <p className="text-xs font-bold uppercase tracking-widest text-gray-500">
                      Acces rapides
                    </p>
                    <div className="mt-4 grid grid-cols-1 gap-2">
                      {[
                        ["Finances", "finances"],
                        ["Business", "ventures"],
                        ["Opportunites", "opportunities"],
                      ].map(([label, target]) => (
                        <button
                          key={target}
                          type="button"
                          onClick={() => setActiveSection(target as DashboardSection)}
                          className="rounded-xl border border-white/10 bg-white/[0.04] px-4 py-3 text-left text-sm font-bold text-gray-100 transition hover:border-[#3fa9f5]/40 hover:bg-[#3fa9f5]/10"
                        >
                          {label}
                        </button>
                      ))}
                    </div>
                  </section>
                </div>
              </section>

              <AdvisorChat />
            </div>
          )}

          {activeSection === "progression" && (
            <div className="space-y-6">
              <SectionHeader
                eyebrow="Progression patrimoniale"
                title="Ton evolution au sein de White Rock"
                description="Chaque action ameliore la qualite de ton pilotage, la profondeur de ton contexte et les capacites disponibles dans ton Family Office."
              />

              <GamificationPanel
                gamification={gamification || undefined}
                score={globalScore}
                userLevel={product?.progression?.level || commandCenter?.level || dashboard?.level}
                plan={product?.plan || dashboard?.plan}
                onUpgrade={handleUpgradePlan}
              />

              <section className="rounded-2xl border border-white/10 bg-zinc-950 p-5">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                  <div>
                    <p className="text-xs uppercase tracking-widest text-[#ffd21a]">
                      Historique de progression
                    </p>
                    <h2 className="mt-2 text-2xl font-bold">Le chemin parcouru</h2>
                    <p className="mt-2 text-sm text-gray-400">
                      Evenements exposes par White Rock a partir des missions, XP, accomplissements et niveaux suivis.
                    </p>
                  </div>
                  <span className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-xs font-bold text-gray-300">
                    {progressionTimelineItems.length} evenement(s)
                  </span>
                </div>

                <div className="mt-5 space-y-3">
                  {progressionTimelineItems.slice(0, 8).map((item, index) => (
                    <article
                      key={`${item.type || "event"}-${item.date || index}`}
                      className="rounded-2xl border border-white/10 bg-black/35 p-4"
                    >
                      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                        <div>
                          <p className="text-xs uppercase tracking-widest text-gray-500">
                            {item.type || "progression"}
                          </p>
                          <h3 className="mt-1 text-lg font-bold text-white">
                            {compactText(item.title, "Progression enregistree")}
                          </h3>
                        </div>
                        <span className="text-xs font-semibold text-gray-500">
                          {formatDate(item.date)}
                        </span>
                      </div>
                      <p className="mt-3 text-sm leading-relaxed text-gray-300">
                        {compactText(item.description, "Evenement de progression enregistre.")}
                      </p>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {item.xp !== undefined && Number(item.xp) > 0 && (
                          <span className="rounded-full border border-emerald-300/25 bg-emerald-300/10 px-3 py-1 text-xs font-bold text-emerald-200">
                            +{item.xp} XP acquis
                          </span>
                        )}
                        {item.impact && (
                          <span className="rounded-full border border-[#3fa9f5]/25 bg-[#3fa9f5]/10 px-3 py-1 text-xs font-semibold text-[#bfe8ff]">
                            {item.impact}
                          </span>
                        )}
                      </div>
                    </article>
                  ))}

                  {progressionTimelineItems.length === 0 && (
                    <p className="rounded-xl border border-white/10 bg-black/30 p-4 text-sm text-gray-400">
                      Aucun historique detaille n'est encore disponible. Les prochains jalons valides par White Rock apparaitront ici.
                    </p>
                  )}
                </div>
              </section>

              <section className="rounded-2xl border border-white/10 bg-zinc-950 p-5">
                <p className="text-xs uppercase tracking-widest text-[#3fa9f5]">
                  Missions patrimoniales
                </p>
                <h2 className="mt-2 text-2xl font-bold">Missions, accomplissements et jalons</h2>
                <p className="mt-2 text-sm text-gray-400">
                  Comprends pourquoi chaque mission compte, ce qu&apos;elle debloque et comment elle ameliore ton cockpit.
                </p>
                <div className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
                  <div className="rounded-xl border border-white/10 bg-black/30 p-3">
                    <p className="text-xs text-gray-500">XP acquis</p>
                    <p className="mt-1 text-xl font-black text-white">
                      {product?.progression?.xp || gamification?.xp || 0}
                    </p>
                  </div>
                  <div className="rounded-xl border border-white/10 bg-black/30 p-3">
                    <p className="text-xs text-gray-500">Niveau actuel</p>
                    <p className="mt-1 text-xl font-black text-white">
                      {product?.progression?.level || "Builder"}
                    </p>
                  </div>
                  <div className="rounded-xl border border-white/10 bg-black/30 p-3">
                    <p className="text-xs text-gray-500">Progression</p>
                    <p className="mt-1 text-xl font-black text-[#3fa9f5]">
                      {product?.progression?.progress_percent || gamification?.progress_percent || 0}%
                    </p>
                  </div>
                  <div className="rounded-xl border border-white/10 bg-black/30 p-3">
                    <p className="text-xs text-gray-500">Missions disponibles</p>
                    <p className="mt-1 text-xl font-black text-white">
                      {progressionMissions.length}
                    </p>
                  </div>
                </div>

                <div className="mt-5 grid grid-cols-1 gap-4 lg:grid-cols-3">
                  {progressionMissions.map((mission) => (
                    <article
                      key={mission.key}
                      className="rounded-2xl border border-white/10 bg-black/45 p-5 shadow-2xl transition hover:-translate-y-0.5 hover:border-[#3fa9f5]/40"
                    >
                      <p className="text-xs uppercase tracking-widest text-[#3fa9f5]">
                        {mission.module || "WHITE ROCK"}
                      </p>
                      <h3 className="mt-2 text-xl font-black text-white">{mission.title}</h3>
                      <p className="mt-3 text-sm leading-relaxed text-gray-300">
                        {mission.description}
                      </p>
                      {mission.context_reason && (
                        <p className="mt-3 rounded-xl border border-[#3fa9f5]/20 bg-[#3fa9f5]/10 p-3 text-xs leading-relaxed text-[#bfe8ff]">
                          Pourquoi maintenant: {mission.context_reason}
                        </p>
                      )}
                      <div className="mt-4 rounded-xl border border-emerald-300/20 bg-emerald-300/10 p-3">
                        <p className="text-xs uppercase tracking-widest text-emerald-200">
                          Impact attendu
                        </p>
                        <p className="mt-1 text-sm font-bold text-white">
                          +{mission.xp || 80} XP acquis - pilotage plus precis
                        </p>
                      </div>
                      <p className="mt-4 text-xs leading-relaxed text-gray-500">
                        Impact: modules mieux priorises, contexte plus fiable et opportunites plus adaptees.
                      </p>
                      {mission.status && (
                        <span className="mt-4 inline-flex rounded-full border border-white/10 px-3 py-1 text-[10px] uppercase text-gray-400">
                          {mission.status}
                        </span>
                      )}
                    </article>
                  ))}
                  {progressionMissions.length === 0 && (
                    <p className="rounded-xl border border-white/10 bg-black/30 p-4 text-sm text-gray-400">
                      Toutes les missions disponibles ont ete completees. Continue a enrichir ton patrimoine pour debloquer de nouvelles opportunites.
                    </p>
                  )}
                </div>
              </section>
            </div>
          )}

          {activeSection === "legacy" && legacyNavigationEnabled && (
            <div className="space-y-6">
              <SectionHeader
                eyebrow="Dynasty"
                title="Dynasty Office"
                description="Transmission, héritiers, gouvernance familiale, protection et stratégie long terme."
              />

              <LegacyOfficePanel
                data={legacyOverview}
                locked={false}
                onUpgrade={handleUpgradePlan}
              />
            </div>
          )}

          {activeSection === "profile" && (
            <div className="space-y-6">
              <SectionHeader
                eyebrow="Mon Profil"
                title="Mon Profil"
                description="Ton identite, ta situation, tes objectifs et tes preferences personnelles."
              />

              <section className="rounded-2xl border border-[#3fa9f5]/25 bg-[radial-gradient(circle_at_top_right,_rgba(63,169,245,0.16),_transparent_34%),linear-gradient(135deg,#060912,#020202)] p-5">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <p className="text-xs uppercase tracking-widest text-[#3fa9f5]">
                      Identite personnelle
                    </p>
                    <h2 className="mt-2 text-3xl font-black">
                      {compactText(wealthProfile?.first_name, "Profil White Rock")}
                    </h2>
                    <p className="mt-2 max-w-2xl text-sm leading-relaxed text-gray-400">
                      {profileNarrative}
                    </p>
                  </div>
                  <div className="flex flex-col gap-3 sm:items-end">
                    <span className="rounded-full border border-emerald-300/30 bg-emerald-300/10 px-3 py-1 text-xs font-bold text-emerald-100">
                      Profil complete a {profileCompletionPercent}%
                    </span>
                    <ActionButton onClick={handleUpdateOnboarding}>
                      Modifier mon profil
                    </ActionButton>
                  </div>
                </div>

                <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
                  {[
                    ["Situation", compactText(onboarding?.situation_pro || wealthProfile?.investor_profile)],
                    ["Objectif", compactText(wealthProfile?.motivation)],
                    ["Horizon", compactText(wealthProfile?.horizon)],
                    ["Risque", compactText(wealthProfile?.risk_level)],
                    ["Devise", compactText(wealthProfile?.main_currency || "EUR")],
                    ["Age", compactText(onboarding?.age)],
                    ["Revenus", (onboarding?.revenus_mensuels ?? onboarding?.monthly_income) ? `${money.format(Number(onboarding?.revenus_mensuels ?? onboarding?.monthly_income))} EUR` : "A completer"],
                    ["Charges", (onboarding?.charges_mensuelles ?? onboarding?.monthly_expenses) ? `${money.format(Number(onboarding?.charges_mensuelles ?? onboarding?.monthly_expenses))} EUR` : "A completer"],
                    ["Capacite mensuelle", profileCapacity !== null ? `${money.format(profileCapacity)} EUR` : "A completer"],
                    ["Completion", `${profileCompletedCount}/${profileCompletionItems.length} informations`],
                  ].map(([label, value]) => (
                    <div key={label} className="rounded-xl border border-white/10 bg-white/[0.04] p-4">
                      <p className="text-xs uppercase tracking-widest text-gray-500">
                        {label}
                      </p>
                      <p className="mt-2 text-sm font-semibold text-white">
                        {value}
                      </p>
                    </div>
                  ))}
                </div>
              </section>

              <ProfileReferralPanel mode="identity" />

              <section className="rounded-2xl border border-white/10 bg-zinc-950 p-5">
                <p className="text-xs uppercase tracking-widest text-gray-500">
                  Preferences et confidentialite
                </p>
                <div className="mt-4 grid gap-4 lg:grid-cols-2">
                  <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
                    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                      <div>
                        <h2 className="text-xl font-bold">Theme</h2>
                        <p className="mt-2 text-sm text-gray-400">
                          Choisissez la couleur de votre theme.
                        </p>
                      </div>
                      <ThemeSwitcher />
                    </div>
                  </div>

                  <div className={`rounded-2xl border border-[#3fa9f5]/20 bg-[#3fa9f5]/5 p-4 ${interactiveCard}`}>
                    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                      <div>
                        <h2 className="text-xl font-bold">Confidentialite</h2>
                        <p className="mt-2 text-sm text-gray-400">
                          Consentements, exports, preferences emails, cookies et suppression du compte.
                        </p>
                      </div>
                      <ActionButton variant="secondary" onClick={() => router.push("/privacy-center")}>
                        Ouvrir
                      </ActionButton>
                    </div>
                  </div>
                </div>
              </section>
            </div>
          )}

          {activeSection === "billing" && (
            <div className="space-y-6">
              <SectionHeader
                eyebrow="Plan & Facturation"
                title="Plan & Facturation"
                description="Ton plan actuel, les acces disponibles et la gestion de ton abonnement."
              />

              <section className="rounded-2xl border border-emerald-300/25 bg-[radial-gradient(circle_at_top_right,_rgba(22,217,154,0.16),_transparent_36%),linear-gradient(135deg,#090909,#07120f_60%,#020202)] p-5">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                  <div>
                    <p className="text-xs uppercase tracking-widest text-emerald-300">
                      Plan et acces premium
                    </p>
                    <h2 className="mt-1 text-2xl font-bold">Mon Plan</h2>
                  </div>
                  <span className="rounded-full border border-emerald-300/30 bg-emerald-300/10 px-3 py-1 text-xs font-bold text-emerald-100">
                    {compactText(product?.entitlements?.copy?.promise || currentPlanCopy.promise)}
                  </span>
                </div>

                <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
                  <div className="rounded-xl border border-white/10 bg-black/25 p-4">
                    <p className="text-xs uppercase tracking-widest text-gray-500">Plan actuel</p>
                    <p className="mt-2 text-xl font-black text-white">
                      {compactText(product?.entitlements?.copy?.name || currentPlanCopy.name)}
                    </p>
                    <p className="mt-2 text-xs leading-relaxed text-gray-400">
                      {compactText(product?.entitlements?.copy?.promise || currentPlanCopy.promise)}
                    </p>
                  </div>
                  <div className="rounded-xl border border-white/10 bg-black/25 p-4">
                    <p className="text-xs uppercase tracking-widest text-gray-500">Progression White Rock</p>
                    <p className="mt-2 text-xl font-black text-emerald-300">
                      {activeModuleCount} espaces debloques
                    </p>
                    <p className="mt-2 text-xs leading-relaxed text-gray-400">
                      Ton cockpit actif aujourd'hui.
                    </p>
                  </div>
                  <div className="rounded-xl border border-white/10 bg-black/25 p-4">
                    <p className="text-xs uppercase tracking-widest text-gray-500">Espaces avances</p>
                    <p className="mt-2 text-xl font-black text-amber-200">
                      {lockedModuleCount} a decouvrir
                    </p>
                    <p className="mt-2 text-xs leading-relaxed text-gray-400">
                      Des lectures plus profondes selon ton plan.
                    </p>
                  </div>
                </div>

                <div className="mt-4 grid gap-3 lg:grid-cols-[1.2fr_0.8fr]">
                  <div className="rounded-2xl border border-[#ffd21a]/25 bg-[#ffd21a]/5 p-4">
                    <p className="text-xs uppercase tracking-widest text-[#ffd21a]">
                      Prochain palier
                    </p>
                    <h3 className="mt-2 text-xl font-black text-white">
                      {nextPlanCopy.name}
                    </h3>
                    <p className="mt-2 text-sm leading-relaxed text-gray-300">
                      {nextPlanCopy.promise}
                    </p>
                    <div className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-2">
                      {nextPlanCopy.unlocks.map((unlock) => (
                        <div key={unlock} className="rounded-xl border border-white/10 bg-black/25 px-3 py-2 text-sm text-gray-200">
                          {unlock}
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
                    <p className="text-xs uppercase tracking-widest text-gray-500">
                      Facturation
                    </p>
                    <div className="mt-3 space-y-3">
                      <div>
                        <p className="text-xs text-gray-500">Renouvellement</p>
                        <p className="text-sm font-semibold text-white">{billingRenewalDate}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500">Montant</p>
                        <p className="text-sm font-semibold text-white">{billingAmount}</p>
                      </div>
                      {futurePlanName && (
                        <div>
                          <p className="text-xs text-gray-500">Plan futur</p>
                          <p className="text-sm font-semibold text-amber-200">{futurePlanName}</p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                <div className="mt-4 flex flex-wrap gap-3">
                  <button onClick={() => router.push("/plans/standard")} className="rounded-xl border border-emerald-300/35 bg-emerald-300/10 px-4 py-2 text-sm font-semibold text-emerald-100">
                    Voir les plans
                  </button>
                  <button onClick={() => router.push("/plans/founder")} className="rounded-xl border border-emerald-300/35 bg-emerald-300/10 px-4 py-2 text-sm font-semibold text-emerald-100">
                    Plans fondateurs
                  </button>
                  <button onClick={() => handleUpgradePlan("gold")} className="rounded-xl border border-[#3fa9f5]/40 bg-[#3fa9f5]/10 px-4 py-2 text-sm font-semibold text-[#3fa9f5]">
                    Gold - Growth
                  </button>
                  <button onClick={() => handleUpgradePlan("elite")} className="rounded-xl bg-gradient-to-r from-[#3fa9f5] to-emerald-400 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-emerald-400/20">
                    Elite - Wealth OS
                  </button>
                  <button onClick={() => handleUpgradePlan("liberty")} className="rounded-xl bg-amber-300 px-4 py-2 text-sm font-semibold text-black">
                    Liberty - Sovereign Wealth
                  </button>
                  <button onClick={() => handleUpgradePlan("legacy")} className="rounded-xl border border-amber-300/40 bg-black px-4 py-2 text-sm font-semibold text-amber-200">
                    Dynasty Office
                  </button>
                  <button onClick={handleOpenBillingPortal} className="rounded-xl border border-white/10 bg-white/[0.04] px-4 py-2 text-sm font-semibold text-white">
                    Gerer mon abonnement
                  </button>
                </div>
              </section>

              <section className="rounded-2xl border border-white/10 bg-zinc-950 p-5">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="text-xs uppercase tracking-widest text-gray-500">
                      Historique de facturation
                    </p>
                    <h2 className="mt-2 text-2xl font-bold">Factures et recus</h2>
                    <p className="mt-2 text-sm text-gray-400">
                      Les factures restent gerees par le portail de facturation tant que l'historique detaille n'est pas expose ici.
                    </p>
                  </div>
                  <ActionButton variant="secondary" onClick={handleOpenBillingPortal}>
                    Ouvrir le portail
                  </ActionButton>
                </div>
              </section>

              <section className="space-y-4">
                <div className="rounded-2xl border border-white/10 bg-zinc-950 p-5">
                  <p className="text-xs uppercase tracking-widest text-[#ffd21a]">
                    Parrainage
                  </p>
                  <h2 className="mt-2 text-2xl font-bold">Recommandations et invitations</h2>
                  <p className="mt-2 text-sm text-gray-400">
                    Invite des proches depuis l'espace abonnement, sans melanger parrainage et gouvernance familiale.
                  </p>
                </div>

                <ProfileReferralPanel mode="referral" />
              </section>
            </div>
          )}

          {activeSection === "settings" && (
            <div className="space-y-6">
              <SectionHeader
                eyebrow="Family Office"
                title="Organisation patrimoniale"
                description="Vision familiale, gouvernance, collaboration et transmission autour de ton patrimoine."
              />

              <section className="rounded-2xl border border-white/10 bg-zinc-950 p-5">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                  <div>
                    <p className="text-xs uppercase tracking-widest text-amber-200">
                      Family Office Profile
                    </p>
                    <h2 className="mt-2 text-2xl font-bold">La vision patrimoniale qui guide les decisions de long terme</h2>
                    <p className="mt-2 text-sm text-gray-400">
                      Les informations qui permettent a White Rock de comprendre la dimension familiale, successorale et patrimoniale de ton projet.
                    </p>
                  </div>
                  <span className="rounded-full border border-amber-300/30 bg-amber-300/10 px-3 py-1 text-xs font-bold text-amber-100">
                    {yesNoLabel(wealthProfile?.has_children)} enfants
                  </span>
                </div>

                <div className="mt-5 grid grid-cols-1 gap-3 lg:grid-cols-3">
                  <div className="rounded-xl border border-white/10 bg-black/25 p-4">
                    <p className="text-xs uppercase tracking-widest text-gray-500">
                      Mission familiale
                    </p>
                    <p className="mt-2 text-sm text-gray-200">
                      {compactText(wealthProfile?.motivation || wealthProfile?.transmission_goal)}
                    </p>
                  </div>
                  <div className="rounded-xl border border-white/10 bg-black/25 p-4">
                    <p className="text-xs uppercase tracking-widest text-gray-500">
                      Transmission
                    </p>
                    <p className="mt-2 text-sm text-gray-200">
                      {compactText(wealthProfile?.transmission_goal)}
                    </p>
                  </div>
                  <div className="rounded-xl border border-white/10 bg-black/25 p-4">
                    <p className="text-xs uppercase tracking-widest text-gray-500">
                      Gouvernance
                    </p>
                    <p className="mt-2 text-sm text-gray-200">
                      {compactText(wealthProfile?.governance_need)}
                    </p>
                  </div>
                  <div className="rounded-xl border border-white/10 bg-black/25 p-4">
                    <p className="text-xs uppercase tracking-widest text-gray-500">
                      Strategie familiale
                    </p>
                    <p className="mt-2 text-sm text-gray-200">
                      {compactText(wealthProfile?.family_strategy)}
                    </p>
                  </div>
                </div>
              </section>

              <section className="rounded-2xl border border-[#ffd21a]/20 bg-[#ffd21a]/5 p-5">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <p className="text-xs uppercase tracking-widest text-[#ffd21a]">
                      Maturite Family Office
                    </p>
                    <h2 className="mt-2 text-2xl font-bold">Foundation</h2>
                    <p className="mt-2 text-sm text-gray-400">
                      Une lecture simple des piliers deja renseignes et des sujets familiaux a clarifier progressivement.
                    </p>
                  </div>
                  <span className="rounded-full border border-[#ffd21a]/35 bg-[#ffd21a]/10 px-3 py-1 text-xs font-bold text-[#ffd21a]">
                    {[
                      wealthProfile?.motivation,
                      wealthProfile?.transmission_goal,
                      wealthProfile?.governance_need,
                      wealthProfile?.has_children,
                      wealthProfile?.family_strategy,
                    ].filter(Boolean).length}/5 complete
                  </span>
                </div>

                <div className="mt-5 grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-5">
                  {[
                    ["Vision familiale", wealthProfile?.motivation],
                    ["Transmission", wealthProfile?.transmission_goal],
                    ["Gouvernance", wealthProfile?.governance_need],
                    ["Heritiers", wealthProfile?.has_children],
                    ["Succession", wealthProfile?.family_strategy],
                  ].map(([label, done]) => (
                    <div key={label as string} className="rounded-xl border border-white/10 bg-black/25 p-3">
                      <p className="text-sm font-semibold text-white">{label}</p>
                      <p className={`mt-1 text-xs ${done ? "text-emerald-300" : "text-gray-500"}`}>
                        {done ? "Renseigne" : "A clarifier"}
                      </p>
                    </div>
                  ))}
                </div>
              </section>

              <section className="space-y-4">
                <div className="rounded-2xl border border-white/10 bg-zinc-950 p-5">
                  <p className="text-xs uppercase tracking-widest text-[#3fa9f5]">
                    Mon Family Office
                  </p>
                  <h2 className="mt-2 text-2xl font-bold">Espaces, membres et droits</h2>
                  <p className="mt-2 text-sm text-gray-400">
                    Une organisation lisible pour inviter un conjoint, un associe, un conseiller ou un heritier au bon moment.
                  </p>
                </div>

                <WorkspacePanel
                  data={workspaces}
                  onCreate={handleCreateWorkspace}
                  onInvite={handleInviteWorkspaceMember}
                  onSwitch={handleSwitchWorkspace}
                />
              </section>
            </div>
          )}
        </div>
      </div>

      <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-white/10 bg-black/92 px-2 py-1.5 shadow-2xl backdrop-blur-xl lg:hidden">
        <div className="no-scrollbar mx-auto flex max-w-3xl gap-1.5 overflow-x-auto">
          {navigation.map((item) => {
            const active = item.key === activeSection;

            return (
              <button
                key={item.key}
                onClick={() => goToSection(item.key)}
                className={`min-w-[70px] rounded-xl border px-2 py-1.5 text-center transition ${
                  active
                    ? "border-[#3fa9f5]/60 bg-[#3fa9f5]/15 text-white"
                    : "border-white/10 bg-white/[0.03] text-gray-400"
                }`}
              >
                <span className="block text-[10px] font-bold leading-tight">
                  {item.label}
                </span>
                {item.locked && (
                  <span className="mt-1 block text-[9px] text-gray-500">
                    lock
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </nav>
    </main>
  );
}



