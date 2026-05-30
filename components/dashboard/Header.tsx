import type { DashboardSummary } from "@/lib/types";
import BrandMark from "@/components/BrandMark";

type HeaderProps = {
  dashboard: DashboardSummary | null;
  onUpgrade?: (plan: string) => void;
};

export default function Header({ dashboard, onUpgrade }: HeaderProps) {
  const plan = dashboard?.plan ? String(dashboard.plan).toUpperCase() : undefined;
  const level = dashboard?.level || null;
  const isFounder = Boolean(dashboard?.is_founder);
  const nextPlan = dashboard?.next_plan || null;
  const ctaLabel =
    nextPlan === "liberty"
      ? "Debloquer Liberty"
      : nextPlan === "legacy"
        ? "Passer Dynasty"
      : nextPlan === "elite"
        ? "Passer en Wealth OS"
        : "Debloquer Gold";

  const getPlanStyle = (value: string) => {
    switch (value) {
      case "SILVER":
        return "bg-gray-400 text-yellow-200";
      case "GOLD":
        return "bg-yellow-500 text-black";
      case "ELITE":
        return "bg-black text-yellow-400";
      case "LIBERTY":
        return "bg-[#f4c95d] text-black";
      case "LEGACY":
        return "bg-gradient-to-r from-black to-[#261b0b] text-amber-200 border border-amber-300/40";
      case "FREE":
      default:
        return "bg-blue-500 text-white";
    }
  };

  const getLevelStyle = (value: string) => {
    switch (value) {
      case "BEGINNER":
        return "bg-blue-400 text-white";
      case "INTERMEDIATE":
        return "bg-gray-400 text-yellow-200";
      case "ADVANCED":
        return "bg-yellow-500 text-black";
      case "ELITE":
        return "bg-black text-yellow-400";
      case "LEGACY":
      case "DYNASTY ARCHITECT":
        return "bg-amber-300 text-black";
      default:
        return "bg-gray-500 text-white";
    }
  };

  return (
    <div className="flex items-center justify-between gap-3">
      <BrandMark compact />

      <div className="flex shrink-0 items-center gap-2 text-right text-sm text-white/60">
        {plan ? (
          <div className="hidden items-end gap-2 md:flex">
            <div className="space-y-1">
              <p className="text-[10px] uppercase tracking-widest text-gray-500">
                Plan
              </p>
              <span
                className={`rounded px-2 py-1 text-xs font-semibold ${getPlanStyle(
                  plan
                )}`}
              >
                {plan === "LEGACY" ? "DYNASTY" : plan}
              </span>
            </div>

            {isFounder && (
              <div className="space-y-1">
                <p className="text-[10px] uppercase tracking-widest text-gray-500">
                  Cercle
                </p>
                <span className="rounded border border-amber-300/40 bg-amber-300/10 px-2 py-1 text-xs font-semibold text-amber-100">
                  FOUNDING MEMBER
                </span>
              </div>
            )}

            {level && (
              <div className="space-y-1">
                <p className="text-[10px] uppercase tracking-widest text-gray-500">
                  Statut
                </p>
                <span
                  className={`rounded px-2 py-1 text-xs font-semibold ${getLevelStyle(
                    level
                  )}`}
                >
                  {level}
                </span>
              </div>
            )}
          </div>
        ) : (
          <div className="hidden h-8 w-28 animate-pulse rounded-lg bg-white/10 sm:block" />
        )}

        {nextPlan && onUpgrade && (
          <button
            onClick={() => onUpgrade(nextPlan)}
            className="rounded-xl border border-[#3fa9f5]/40 bg-[#3fa9f5] px-3 py-2 text-[11px] font-bold text-white transition hover:bg-[#2d91d5] sm:px-4 sm:text-xs"
          >
            {ctaLabel}
          </button>
        )}
      </div>
    </div>
  );
}
