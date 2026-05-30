"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiRequest } from "@/lib/api";
import { useDashboard } from "@/hooks/useDashboard";
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
  YieldAsset,
  YieldAssetPayload,
  YieldAssetType,
} from "@/lib/types";

import Header from "@/components/dashboard/Header";
import AdvisorChat from "@/components/dashboard/AdvisorChat";
import ChartModule from "@/components/dashboard/ChartModule";
import DailyWealthCheck from "@/components/dashboard/DailyWealthCheck";
import ExposureBreakdown from "@/components/dashboard/ExposureBreakdown";
import FinanceModule from "@/components/dashboard/FinanceModule";
import LegacyOfficePanel from "@/components/dashboard/LegacyOfficePanel";
import OpportunityDiscoveryPanel from "@/components/dashboard/OpportunityDiscoveryPanel";
import OpportunitiesModule from "@/components/dashboard/OpportunitiesModule";
import PortfolioModule from "@/components/dashboard/PortfolioModule";
import ProductProgressPanel from "@/components/dashboard/ProductProgressPanel";
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

const planOrder: Record<string, number> = {
  FREE: 0,
  GOLD: 1,
  ELITE: 2,
  LIBERTY: 3,
  LEGACY: 4,
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

function MissionControlPanel({
  product,
  onOpenMission,
}: {
  product?: ProductContext | null;
  onOpenMission: () => void;
}) {
  const control = product?.mission_control;
  const items = [
    control?.risk,
    control?.opportunity,
    control?.decision,
    control?.mission,
  ].filter(Boolean);

  if (!items.length) return null;

  return (
    <section className="rounded-2xl border border-[#3fa9f5]/25 bg-zinc-950 p-5">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs uppercase tracking-widest text-[#3fa9f5]">
            Mission Control
          </p>
          <h2 className="mt-1 text-2xl font-black text-white">
            Une lecture. Une direction.
          </h2>
        </div>
        <button
          onClick={onOpenMission}
          className="rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm text-gray-200 transition hover:border-[#3fa9f5]/50"
        >
          Voir progression
        </button>
      </div>
      <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-4">
        {items.map((item, index) => (
          <div key={`${item?.title}-${index}`} className="rounded-xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-xs uppercase tracking-widest text-gray-500">
              {index === 0 ? "Risque" : index === 1 ? "Opportunite" : index === 2 ? "Decision" : "Mission"}
            </p>
            <h3 className="mt-2 text-sm font-bold text-white">{item?.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-gray-400">
              {item?.description}
            </p>
            {item?.action && (
              <p className="mt-3 text-xs font-semibold text-[#3fa9f5]">
                {item.action}
              </p>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

function FutureViewPanel({ product }: { product?: ProductContext | null }) {
  const future = product?.future_view;
  const scenarios = future?.scenarios || [];

  if (!future || scenarios.length === 0) return null;

  return (
    <section className="rounded-2xl border border-white/10 bg-zinc-950 p-5">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs uppercase tracking-widest text-[#3fa9f5]">
            Future View
          </p>
          <h2 className="mt-1 text-2xl font-black text-white">
            Ton futur patrimonial visible
          </h2>
        </div>
        <div className="text-sm text-gray-400">
          Capacite mensuelle backend:{" "}
          <span className="font-bold text-white">
            {money.format(Number(future.monthly_capacity || 0))} EUR
          </span>
        </div>
      </div>
      <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
        {scenarios.map((scenario) => (
          <div key={scenario.label} className="rounded-xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-xs uppercase tracking-widest text-gray-500">
              {scenario.label}
            </p>
            <p className="mt-2 text-3xl font-black text-white">
              {money.format(Number(scenario.value || 0))} EUR
            </p>
          </div>
        ))}
      </div>
      <p className="mt-4 text-sm leading-relaxed text-gray-400">
        {future.assumption}
      </p>
    </section>
  );
}

function WealthTimelinePanel({ product }: { product?: ProductContext | null }) {
  const timeline = product?.wealth_timeline;
  const stages = timeline?.stages || [];

  if (!timeline || stages.length === 0) return null;

  return (
    <section className="rounded-2xl border border-white/10 bg-zinc-950 p-5">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs uppercase tracking-widest text-[#3fa9f5]">
            Timeline patrimoniale
          </p>
          <h2 className="mt-1 text-2xl font-black text-white">
            Le GPS de ta richesse globale
          </h2>
        </div>
        {timeline.next_milestone?.label && (
          <p className="text-sm text-gray-400">
            Prochain palier:{" "}
            <span className="font-bold text-white">{timeline.next_milestone.label}</span>
          </p>
        )}
      </div>
      <div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-6">
        {stages.map((stage) => {
          const active = stage.status === "achieved" || stage.status === "current";
          return (
            <div
              key={stage.label}
              className={`rounded-xl border p-4 ${
                active
                  ? "border-[#3fa9f5]/50 bg-[#3fa9f5]/10"
                  : "border-white/10 bg-white/[0.03]"
              }`}
            >
              <p className="text-sm font-bold text-white">{stage.label}</p>
              <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-white/10">
                <div
                  className="h-full rounded-full bg-[#3fa9f5]"
                  style={{ width: `${Math.min(100, Number(stage.progress_percent || 0))}%` }}
                />
              </div>
              {stage.target ? (
                <p className="mt-2 text-xs text-gray-500">
                  {money.format(Number(stage.target || 0))} EUR
                </p>
              ) : null}
            </div>
          );
        })}
      </div>
    </section>
  );
}

function FamilyOfficeModePanel({ product }: { product?: ProductContext | null }) {
  const view = product?.family_office_view;
  const allocation = view?.allocation || [];

  if (!view || allocation.length === 0) return null;

  return (
    <section className="rounded-2xl border border-[#d6b35a]/30 bg-gradient-to-br from-[#151006] via-zinc-950 to-black p-5">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs uppercase tracking-widest text-[#d6b35a]">
            Family Office Mode
          </p>
          <h2 className="mt-1 text-2xl font-black text-white">
            Tu ne pilotes plus des modules. Tu pilotes ta richesse.
          </h2>
        </div>
        <div className="text-right">
          <p className="text-xs text-gray-500">Patrimoine global backend</p>
          <p className="text-2xl font-black text-white">
            {money.format(Number(view.global_wealth || 0))} EUR
          </p>
        </div>
      </div>
      <p className="mt-3 text-sm leading-relaxed text-gray-400">{view.summary}</p>
      <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
        {allocation.map((item) => (
          <div key={item.key || item.label} className="rounded-xl border border-white/10 bg-black/30 p-4">
            <p className="text-xs uppercase tracking-widest text-gray-500">
              {item.label}
            </p>
            <p className="mt-2 text-2xl font-black text-white">
              {money.format(Number(item.value || 0))} EUR
            </p>
            <p className="mt-2 text-sm leading-relaxed text-gray-400">
              {item.description}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}

const getAssetValue = (asset: PortfolioAsset) =>
  Number(asset.value ?? asset.current_value ?? 0);

const getAssetCost = (asset: PortfolioAsset) =>
  Number(
    asset.cost ??
      Number(asset.quantity || 0) * Number(asset.purchase_price || 0)
  );

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

const getStrategicOpportunityCount = (
  opportunities: unknown
) => {
  if (Array.isArray(opportunities)) return opportunities.length;

  if (
    opportunities &&
    typeof opportunities === "object" &&
    "count" in opportunities &&
    typeof opportunities.count === "number"
  ) {
    return opportunities.count;
  }

  if (
    opportunities &&
    typeof opportunities === "object" &&
    "opportunities" in opportunities &&
    Array.isArray(opportunities.opportunities)
  ) {
    return opportunities.opportunities.length;
  }

  return 0;
};

const categoryNavigationTargets: Record<string, DashboardSection> = {
  "ASSETS FINANCIERS": "investments",
  "FOREX": "investments",
  "IMMOBILIER": "real_estate",
  "CROWDFUNDING": "ventures",
  "PRIVATE EQUITY": "ventures",
  "PRIVATE_EQUITY": "ventures",
  "BUSINESS": "ventures",
  "BUSINESS DIGITAL": "ventures",
  "AI BUSINESS": "ventures",
  "STARTUP": "ventures",
  "FRANCHISE": "ventures",
};

const getCategoryTarget = (label: string): DashboardSection =>
  categoryNavigationTargets[label.trim().toUpperCase()] || "settings";

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

export default function Dashboard() {
  const router = useRouter();
  const {
    dashboard,
    portfolio,
    history,
    realEstate,
    yieldAssets,
    ventureAssets,
    categoryOpportunities,
    legacyOverview,
    onboarding,
    finance,
    gamification,
    commandCenter,
    workspaces,
    product,
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

  const showToast = (message: string, type: "success" | "error" | "info" = "info") => {
    setToast({ message, type });
  };

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
  const totalValue = portfolio.reduce(
    (acc, asset) => acc + getAssetValue(asset),
    0
  );
  const initialInvestment = portfolio.reduce(
    (acc, asset) => acc + getAssetCost(asset),
    0
  );
  const portfolioGain = totalValue - initialInvestment;
  const realEstateAssets = realEstate?.assets || [];
  const realEstateFinal = Number(realEstate?.totals?.total_estimated_value || 0);
  const realEstateGain = Number(realEstate?.totals?.total_potential_gain || 0);
  const yieldFinal = Number(yieldAssets?.totals?.total_final_value || 0);
  const yieldGain = Number(yieldAssets?.totals?.total_projected_gain || 0);
  const ventureFinal = Number(ventureAssets?.totals?.total_final_value || 0);
  const ventureGain = Number(ventureAssets?.totals?.total_result || 0);
  const globalPortfolioValue =
    totalValue + realEstateFinal + yieldFinal + ventureFinal;
  const backendGlobalWealth = Number(
    product?.family_office_view?.global_wealth ??
      product?.data_profile?.current_wealth ??
      globalPortfolioValue
  );
  const globalPortfolioGain =
    portfolioGain + realEstateGain + yieldGain + ventureGain;
  const globalPortfolioGainClass =
    globalPortfolioGain >= 0 ? "text-emerald-400" : "text-red-400";
  const businessFinal = yieldFinal + ventureFinal;
  const businessGain = yieldGain + ventureGain;
  const realEstateSummary = {
    label: "Immobilier",
    count: realEstateAssets.length,
    value: realEstateFinal,
    gain: realEstateGain,
  };
  const investmentSummary = {
    label: "Investissements",
    count: portfolio.length,
    value: totalValue,
    gain: portfolioGain,
  };
  const businessSummary = {
    label: "Business",
    count: (yieldAssets?.assets || []).length + (ventureAssets?.assets || []).length,
    value: businessFinal,
    gain: businessGain,
  };
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
  const categoryCounts = [
    { label: "Assets financiers", value: portfolio.length },
    {
      label: "Forex",
      value: portfolio.filter(
        (asset) => String(asset.asset_type || asset.type).toUpperCase() === "FOREX"
      ).length,
    },
    { label: "Immobilier", value: realEstateAssets.length },
    { label: "Crowdfunding", value: (yieldAssets?.assets || []).filter((asset) => asset.asset_type === "crowdfunding").length },
    { label: "Private Equity", value: (yieldAssets?.assets || []).filter((asset) => asset.asset_type === "private_equity").length },
    { label: "Business", value: (ventureAssets?.assets || []).filter((asset) => asset.asset_type === "business").length },
    { label: "Startup", value: (ventureAssets?.assets || []).filter((asset) => asset.asset_type === "startup").length },
    { label: "Franchise", value: (ventureAssets?.assets || []).filter((asset) => asset.asset_type === "franchise").length },
    { label: "Business digital", value: (ventureAssets?.assets || []).filter((asset) => asset.asset_type === "ai_business").length },
  ].filter((item) => item.value > 0);
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
  const eliteChartsEnabled = planAllows(currentPlan, "ELITE");
  const legacyNavigationEnabled = planAllows(currentPlan, "LIBERTY");
  const progressionMissions = product?.missions || [];
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
  const hasPortfolioHistory = planAllows(currentPlan, "GOLD");
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
            label: "Legacy",
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
      key: "settings",
      label: "Family Office",
      description: "Identité",
    },
  ];
  const opportunitiesCount =
    typeof commandCenter?.opportunities_count === "number"
      ? commandCenter.opportunities_count
      : getStrategicOpportunityCount(commandCenter?.opportunities);

  const handleUpdateOnboarding = async () => {
    setFormModal({
      kind: "onboarding",
      title: "Modifier la situation",
      description: "Mets a jour revenus et charges avec une saisie claire.",
      values: {
        revenus_mensuels: String(
          onboarding?.revenus_mensuels ?? onboarding?.monthly_income ?? 0
        ),
        charges_mensuelles: String(
          onboarding?.charges_mensuelles ?? onboarding?.monthly_expenses ?? 0
        ),
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
        showToast("Checkout Stripe indisponible pour le moment.", "error");
      }
    } catch (err) {
      console.error(err);
      const message = err instanceof Error ? err.message : "";
      const missingPrice = message.match(/STRIPE_PRICE_[A-Z_]+/)?.[0];

      showToast(
        missingPrice
          ? `Abonnement Stripe non configure: ajoute ${missingPrice} dans Render.`
          : "Impossible d'ouvrir l'abonnement. Verifie la configuration Stripe.",
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
        await apiRequest("/auth/onboarding/update", token, {
          method: "PUT",
          body: JSON.stringify({
            revenus_mensuels: Number(values.revenus_mensuels || 0),
            charges_mensuelles: Number(values.charges_mensuelles || 0),
          }),
        });
        await refreshAfterMutation();
        showToast("Situation mise a jour.", "success");
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
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <TextField label="Revenus mensuels" type="number" value={values.revenus_mensuels || "0"} onChange={(value) => updateModalValue("revenus_mensuels", value)} />
          <TextField label="Charges mensuelles" type="number" value={values.charges_mensuelles || "0"} onChange={(value) => updateModalValue("charges_mensuelles", value)} />
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
                description="La synthese immediate: patrimoine, score, progression et prochaine action utile."
              />

              <DailyWealthCheck
                score={globalScore}
                gain={globalPortfolioGain}
                product={product}
                opportunitiesCount={opportunitiesCount}
                onOpenStatus={() => goToSection("progression")}
                onOpenAction={() => goToSection("progression")}
                onOpenOpportunities={() => goToSection("opportunities")}
              />

              <MissionControlPanel
                product={product}
                onOpenMission={() => goToSection("progression")}
              />

              <FutureViewPanel product={product} />

              <WealthTimelinePanel product={product} />

              <FamilyOfficeModePanel product={product} />

              <section className="rounded-2xl border border-[#3fa9f5]/20 bg-gradient-to-br from-[#08131f] via-black to-[#0b2035] p-6">
                <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1.1fr_1.4fr]">
                  <div>
                    <p className="text-sm uppercase tracking-widest text-[#3fa9f5]">
                      Patrimoine centralise
                    </p>
                    <div className="mt-4 flex items-center gap-4">
                      <span className="rounded-full bg-[#3fa9f5]/20 px-4 py-2 text-[#3fa9f5]">
                        {product?.progression?.level || commandCenter?.level || "Starter"}
                      </span>
                      <span className="text-5xl font-black">{globalScore}/100</span>
                    </div>
                    <p className="mt-4 text-gray-400">
                      Plan {product?.plan || dashboard?.plan || "charge"} ·{" "}
                      {product?.progression?.status || "Foundation"}
                    </p>
                  </div>

                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                    <button onClick={() => goToSection("settings")} className={`rounded-2xl border border-white/10 bg-white/5 p-4 text-left ${interactiveCard}`}>
                      <p className="text-xs text-gray-400">Patrimoine global</p>
                      <h3 className="mt-2 text-2xl font-black">
                        {money.format(backendGlobalWealth)} EUR
                      </h3>
                    </button>
                    <button onClick={() => goToSection("investments")} className={`rounded-2xl border border-white/10 bg-white/5 p-4 text-left ${interactiveCard}`}>
                      <p className="text-xs text-gray-400">+/- value</p>
                      <h3 className={`mt-2 text-2xl font-black ${globalPortfolioGainClass}`}>
                        {globalPortfolioGain >= 0 ? "+" : ""}
                        {money.format(globalPortfolioGain)} EUR
                      </h3>
                    </button>
                    <button onClick={() => goToSection("progression")} className={`rounded-2xl border border-white/10 bg-white/5 p-4 text-left ${interactiveCard}`}>
                      <p className="text-xs text-gray-400">Complétion</p>
                      <h3 className="mt-2 text-2xl font-black text-[#3fa9f5]">
                        {product?.data_profile?.completion_percent || 0}%
                      </h3>
                    </button>
                  </div>
                </div>

                {categoryCounts.length > 0 && (
                  <div className="mt-5 flex flex-wrap gap-2">
                    {categoryCounts.slice(0, 6).map((item) => (
                    <button
                      key={item.label}
                      onClick={() => goToSection(getCategoryTarget(item.label))}
                      className="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm"
                    >
                      <span className="text-gray-400">{item.label}</span>{" "}
                      <span className="font-bold text-white">{item.value}</span>
                    </button>
                    ))}
                  </div>
                )}
              </section>

              <section className="grid grid-cols-1 gap-3">
                {[realEstateSummary, investmentSummary, businessSummary].map((item) => (
                  <button
                    key={item.label}
                    onClick={() =>
                      goToSection(
                        item.label === "Immobilier"
                          ? "real_estate"
                          : item.label === "Investissements"
                            ? "investments"
                            : "ventures"
                      )
                    }
                    className={`rounded-2xl border border-white/10 bg-zinc-950 p-4 text-left ${interactiveCard}`}
                  >
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                      <div>
                        <p className="text-xs uppercase tracking-widest text-[#3fa9f5]">
                          {item.label}
                        </p>
                        <p className="mt-1 text-sm text-gray-400">
                          {item.count} element{item.count > 1 ? "s" : ""} suivi{item.count > 1 ? "s" : ""}
                        </p>
                      </div>
                      <div className="grid grid-cols-2 gap-3 text-right sm:min-w-[320px]">
                        <div>
                          <p className="text-xs text-gray-500">Valeur</p>
                          <p className="text-lg font-black text-white">
                            {money.format(item.value)} EUR
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-500">Resultat</p>
                          <p className={`text-lg font-black ${item.gain >= 0 ? "text-[#3fa9f5]" : "text-red-400"}`}>
                            {item.gain >= 0 ? "+" : ""}
                            {money.format(item.gain)} EUR
                          </p>
                        </div>
                      </div>
                    </div>
                  </button>
                ))}
              </section>

              <section className="rounded-2xl border border-white/10 bg-zinc-950 p-4 sm:p-5">
                <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
                  <div>
                    <p className="text-xs uppercase tracking-widest text-[#3fa9f5]">
                      Action utile
                    </p>
                    <h2 className="mt-1 text-2xl font-bold">Prochaines actions</h2>
                  </div>
                  <p className="text-sm text-gray-500">
                    Un petit pas, puis le cockpit devient plus clair.
                  </p>
                </div>
                <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
                  {(product?.missions || []).slice(0, 3).map((mission) => (
                    <button
                      key={mission.key}
                      onClick={() => {
                        router.push("/progression/challenges");
                      }}
                      className={`rounded-xl border border-white/10 bg-white/[0.04] p-4 text-left ${interactiveCard}`}
                    >
                      <div className="flex h-full flex-col justify-between gap-3">
                        <div>
                          <p className="font-bold text-white">{mission.title}</p>
                          <p className="mt-1 text-sm text-gray-400">
                            {mission.description}
                          </p>
                        </div>
                        {mission.xp ? (
                          <span className="text-xs font-bold text-emerald-300">
                            +{mission.xp} XP
                          </span>
                        ) : null}
                      </div>
                    </button>
                  ))}

                  {(product?.missions || []).length === 0 && (
                    <p className="text-sm text-gray-400">
                      Aucun signal urgent. Continue a enrichir ton patrimoine tranquillement.
                    </p>
                  )}
                </div>
              </section>

              <section className="rounded-2xl border border-white/10 bg-zinc-950 p-4 sm:p-5">
                <div className="mb-4">
                  <p className="text-xs uppercase tracking-widest text-[#3fa9f5]">
                    Repartition
                  </p>
                  <h2 className="mt-1 text-2xl font-bold">Allocation patrimoniale</h2>
                </div>
                {hasModule("diversification") ? (
                  <ExposureBreakdown
                    portfolio={portfolio}
                    realEstate={realEstate}
                    yieldAssets={yieldAssets}
                    ventureAssets={ventureAssets}
                    finance={finance}
                  />
                ) : (
                  <LockedSection
                    title="Allocation avancee"
                    description="Debloque la lecture par exposition pour visualiser les concentrations et les arbitrages prioritaires."
                    onUpgrade={handleUpgradePlan}
                  />
                )}
              </section>

              <section className="rounded-2xl border border-white/10 bg-zinc-950 p-4 sm:p-5">
                {hasPortfolioHistory ? (
                  <ChartModule
                    history={history}
                    initialInvestment={initialInvestment}
                    currentValue={globalPortfolioValue}
                    currentInvestment={initialInvestment}
                  />
                ) : (
                  <LockedSection
                    title="Historique portfolio"
                    description="Le graphique d'evolution est disponible a partir du plan Gold."
                    onUpgrade={handleUpgradePlan}
                  />
                )}
              </section>

              <ProductProgressPanel product={product} onUpgrade={handleUpgradePlan} />
            </div>
          )}

          {activeSection === "finances" && (
            <div className="space-y-6">
              <SectionHeader
                eyebrow="Finances"
                title="Base financiere"
                description="Revenus, charges, epargne, dettes et cashflow. Cette section sert a clarifier les fondations avant l'allocation."
              />

              <section className="rounded-2xl border border-white/10 bg-zinc-950 p-5">
                <div className="mb-4 flex justify-between gap-4">
                  <h2 className="text-2xl font-bold">Situation</h2>
                  <button
                    onClick={handleUpdateOnboarding}
                    className="rounded-xl bg-[#3fa9f5] px-4 py-2"
                  >
                    Modifier
                  </button>
                </div>
                <FinanceModule
                  revenusMensuels={
                    onboarding?.revenus_mensuels ?? onboarding?.monthly_income ?? 0
                  }
                  chargesMensuelles={
                    onboarding?.charges_mensuelles ?? onboarding?.monthly_expenses ?? 0
                  }
                />
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

              <OpportunityDiscoveryPanel
                universe="investments"
                title="Investment Discovery"
                description="Pistes d'allocation fournies par le backend selon ton horizon, ton risque, ton portefeuille et les signaux de marche disponibles."
                plan={currentPlan}
                token={token}
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

              <OpportunityDiscoveryPanel
                universe="real_estate"
                title="Recherche immobiliere patrimoniale"
                description="Residence principale, locatif, achat/revente ou commercial: donnees de rendement, risque local et prochaine verification."
                plan={currentPlan}
                token={token}
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
                description="Business, startup, activites digitales, franchise, crowdfunding et private equity dans une vue dediee."
              />

              <OpportunityDiscoveryPanel
                universe="business"
                title="Business Opportunity Engine"
                description="Donnees business digital, startup, franchise, reprise, crowdfunding et private equity selon ton budget, ton risque et ton ambition."
                plan={currentPlan}
                token={token}
              />

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

              <YieldInvestmentsModule
                data={yieldAssets}
                onAdd={handleAddYieldAsset}
                onUpdate={handleUpdateYieldAsset}
                onDelete={handleDeleteYieldAsset}
                opportunities={categoryOpportunityItems.filter((item) =>
                  ["crowdfunding", "private_equity"].includes(item.key || "")
                )}
              />

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
            </div>
          )}

          {activeSection === "opportunities" && (
            <div className="space-y-6">
              <SectionHeader
                eyebrow="Opportunites"
                title="Opportunity Center"
                description="Toutes les opportunites fournies par le backend, separees du chat Ethan pour garder une lecture claire."
              />

              <OpportunitiesModule commandCenter={commandCenter} />
            </div>
          )}

          {activeSection === "ai" && (
            <div className="space-y-6">
              <SectionHeader
                eyebrow="Conseiller patrimonial"
                title="ETHAN"
                description="Conversation uniquement. Les opportunites vivent dans leur page dediee."
              />

              <AdvisorChat />
            </div>
          )}

          {activeSection === "progression" && (
            <div className="space-y-6">
              <SectionHeader
                eyebrow="Progression"
                title="XP, niveaux et deblocages"
                description="Une gamification premium pour sentir la montee en puissance sans transformer l'app en jeu."
              />

              <GamificationPanel
                gamification={gamification || undefined}
                score={globalScore}
                userLevel={product?.progression?.level || commandCenter?.level || dashboard?.level}
                plan={product?.plan || dashboard?.plan}
                onUpgrade={handleUpgradePlan}
              />

              <section className="rounded-2xl border border-white/10 bg-zinc-950 p-5">
                <p className="text-xs uppercase tracking-widest text-[#3fa9f5]">
                  Missions et defis
                </p>
                <h2 className="mt-2 text-2xl font-bold">Defis, badges et recompenses</h2>
                <p className="mt-2 text-sm text-gray-400">
                  Comprends pourquoi chaque mission compte, ce qu&apos;elle debloque et comment elle ameliore ton cockpit.
                </p>
                <div className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
                  <div className="rounded-xl border border-white/10 bg-black/30 p-3">
                    <p className="text-xs text-gray-500">XP</p>
                    <p className="mt-1 text-xl font-black text-white">
                      {product?.progression?.xp || gamification?.xp || 0}
                    </p>
                  </div>
                  <div className="rounded-xl border border-white/10 bg-black/30 p-3">
                    <p className="text-xs text-gray-500">Niveau</p>
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
                    <p className="text-xs text-gray-500">Missions</p>
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
                          Recompense
                        </p>
                        <p className="mt-1 text-sm font-bold text-white">
                          +{mission.xp || 80} XP - meilleur contexte backend
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
                      Aucune mission supplementaire renvoyee par le backend pour le moment.
                    </p>
                  )}
                </div>
              </section>
            </div>
          )}

          {activeSection === "legacy" && legacyNavigationEnabled && (
            <div className="space-y-6">
              <SectionHeader
                eyebrow="Legacy"
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

          {activeSection === "settings" && (
            <div className="space-y-6">
              <SectionHeader
                eyebrow="Family Office"
                title="Identite, controle et personnalisation"
                description="Ton centre premium pour le profil, l'abonnement, les preferences et la gouvernance patrimoniale."
              />

              <ProfileReferralPanel mode="referral" />

              <section className="rounded-2xl border border-white/10 bg-zinc-950 p-5">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <h2 className="text-2xl font-bold">Theme</h2>
                    <p className="mt-2 text-sm text-gray-400">
                      Choisissez la couleur de votre theme.
                    </p>
                  </div>
                  <ThemeSwitcher />
                </div>
              </section>

              <section className="rounded-2xl border border-white/10 bg-zinc-950 p-5">
                <h2 className="text-2xl font-bold">Abonnement</h2>
                <p className="mt-2 text-sm text-gray-400">
                  Plan actuel: {product?.plan || dashboard?.plan || "charge"}
                </p>
                <div className="mt-4 flex flex-wrap gap-3">
                  <button onClick={() => router.push("/plans/standard")} className="rounded-xl border border-[#3fa9f5]/40 bg-[#3fa9f5]/10 px-4 py-2 text-sm font-semibold text-[#3fa9f5]">
                    Standard Plans
                  </button>
                  <button onClick={() => router.push("/plans/founder")} className="rounded-xl border border-orange-300/40 bg-orange-300/10 px-4 py-2 text-sm font-semibold text-orange-200">
                    Founder Plans
                  </button>
                  <button onClick={() => handleUpgradePlan("gold")} className="rounded-xl border border-[#3fa9f5]/40 bg-[#3fa9f5]/10 px-4 py-2 text-sm font-semibold text-[#3fa9f5]">
                    Gold - Growth
                  </button>
                  <button onClick={() => handleUpgradePlan("elite")} className="rounded-xl bg-[#3fa9f5] px-4 py-2 text-sm font-semibold text-white">
                    Elite - Wealth OS
                  </button>
                  <button onClick={() => handleUpgradePlan("liberty")} className="rounded-xl bg-amber-300 px-4 py-2 text-sm font-semibold text-black">
                    Liberty - Sovereign Wealth
                  </button>
                  <button onClick={() => handleUpgradePlan("legacy")} className="rounded-xl border border-amber-300/40 bg-black px-4 py-2 text-sm font-semibold text-amber-200">
                    Legacy - Dynasty Office
                  </button>
                  <button onClick={handleOpenBillingPortal} className="rounded-xl border border-white/10 bg-white/[0.04] px-4 py-2 text-sm font-semibold text-white">
                    Gerer mon abonnement
                  </button>
                </div>
              </section>

              <ProfileReferralPanel
                mode="identity"
                level={product?.progression?.level || commandCenter?.level || dashboard?.level}
              />

              <section className={`rounded-2xl border border-[#3fa9f5]/20 bg-[#3fa9f5]/5 p-5 ${interactiveCard}`}>
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="text-xs uppercase tracking-widest text-[#3fa9f5]">
                      Confiance et donnees
                    </p>
                    <h2 className="mt-2 text-2xl font-bold">Privacy Center</h2>
                    <p className="mt-2 text-sm text-gray-400">
                      Gere tes consentements, exports, preferences emails,
                      cookies et demandes de suppression depuis un espace dedie.
                    </p>
                  </div>
                  <ActionButton variant="secondary" onClick={() => router.push("/privacy-center")}>
                    Ouvrir
                  </ActionButton>
                </div>
              </section>

              <WorkspacePanel
                data={workspaces}
                onCreate={handleCreateWorkspace}
                onInvite={handleInviteWorkspaceMember}
                onSwitch={handleSwitchWorkspace}
              />

              <section className="rounded-2xl border border-white/10 bg-zinc-950 p-5">
                <h2 className="text-2xl font-bold">Espaces ouverts</h2>
                <div className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-3">
                  {(product?.modules?.visible || []).slice(0, 6).map((module) => (
                    <div key={module.key} className="rounded-xl border border-white/10 bg-white/[0.04] px-3 py-2">
                      <p className="text-sm font-semibold text-white">{module.label}</p>
                      <p className="text-xs text-gray-500">Stage {module.stage || "-"}</p>
                    </div>
                  ))}
                  {(product?.modules?.visible || []).length === 0 && (
                    <p className="text-sm text-gray-400">Aucun espace actif pour le moment.</p>
                  )}
                </div>
              </section>
            </div>
          )}        </div>
      </div>

      <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-white/10 bg-black/92 px-2 py-1.5 shadow-2xl backdrop-blur-xl lg:hidden">
        <div className="mx-auto flex max-w-3xl gap-1.5 overflow-x-auto">
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



