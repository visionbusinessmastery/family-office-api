import type { LegacyOverview } from "@/lib/types";

type LegacyOfficePanelProps = {
  data?: LegacyOverview | null;
  locked?: boolean;
  onUpgrade?: (plan: string) => void;
};

const fallbackInsights = [
  "Le vrai luxe est la stabilite.",
  "La richesse se construit vite. Une dynastie patrimoniale demande plusieurs generations.",
  "Ton patrimoine doit survivre a tes emotions.",
];

const legacyModules = [
  {
    title: "Family Vault",
    description: "Documents familiaux, notes privees, succession et coffre-fort.",
  },
  {
    title: "Governance",
    description: "Regles familiales, conseil de famille et structure de decision.",
  },
  {
    title: "Heirs",
    description: "Preparation des heritiers, education financiere et module junior.",
  },
  {
    title: "Protection Layer",
    description: "Concentration, vulnerabilite, inflation lifestyle et protection.",
  },
  {
    title: "Global Strategy",
    description: "Residence fiscale, diversification geographique et international.",
  },
  {
    title: "Dynasty Timeline",
    description: "Vision 10 ans, 20 ans et projection generationnelle.",
  },
];

const scoreCards = [
  ["Dynasty Score", "legacy_score"],
  ["Dynasty Stability", "dynasty_stability_score"],
  ["Transmission", "transmission_readiness"],
  ["Gouvernance", "family_governance_index"],
  ["Protection", "asset_protection_index"],
] as const;

export default function LegacyOfficePanel({
  data,
  locked,
  onUpgrade,
}: LegacyOfficePanelProps) {
  const scores = data?.scores || {};
  const insights = data?.insights?.length ? data.insights : fallbackInsights;

  if (locked) {
    return (
      <section className="rounded-2xl border border-amber-300/20 bg-gradient-to-br from-[#080b12] via-black to-[#111827] p-5 shadow-2xl">
        <p className="text-xs uppercase tracking-widest text-amber-200">
          Dynasty
        </p>
        <h2 className="mt-2 text-2xl font-black text-white">
          Dynasty Office
        </h2>
        <p className="mt-3 max-w-3xl text-sm leading-relaxed text-gray-400">
          Au-dessus de Liberty: transmission, gouvernance familiale, protection
          patrimoniale et vision multi-generationnelle.
        </p>
        {onUpgrade && (
          <button
            onClick={() => onUpgrade("legacy")}
            className="mt-5 rounded-xl bg-amber-300 px-4 py-2 text-sm font-bold text-black transition hover:bg-amber-200"
          >
            Debloquer Dynasty
          </button>
        )}
      </section>
    );
  }

  return (
    <section className="rounded-2xl border border-amber-300/20 bg-gradient-to-br from-[#070912] via-black to-[#101724] p-5 shadow-2xl">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs uppercase tracking-widest text-amber-200">
            Dynasty
          </p>
          <h2 className="mt-2 text-2xl font-black text-white">
            Dynasty Office
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-relaxed text-gray-400">
            Un centre de controle calme pour proteger, transmettre et structurer
            ce qui doit te survivre.
          </p>
        </div>
        <span className="rounded-full border border-amber-300/30 bg-amber-300/10 px-4 py-2 text-xs font-bold uppercase tracking-widest text-amber-100">
          Dynasty Architect
        </span>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {scoreCards.map(([label, key]) => (
          <div key={key} className="rounded-xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-xs text-gray-500">{label}</p>
            <p className="mt-2 text-3xl font-black text-white">
              {Number(scores[key] || 0)}
            </p>
          </div>
        ))}
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 xl:grid-cols-[0.85fr_1.15fr]">
        <div className="rounded-xl border border-amber-300/20 bg-amber-300/10 p-4">
          <h3 className="font-bold text-amber-100">Signaux Dynasty</h3>
          <div className="mt-3 space-y-3">
            {insights.slice(0, 3).map((insight) => (
              <p key={insight} className="text-sm leading-relaxed text-gray-300">
                {insight}
              </p>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {legacyModules.map((module) => (
            <div
              key={module.title}
              className="rounded-xl border border-white/10 bg-black/35 p-4 transition hover:border-amber-300/30"
            >
              <p className="font-bold text-white">{module.title}</p>
              <p className="mt-1 text-sm leading-relaxed text-gray-400">
                {module.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
