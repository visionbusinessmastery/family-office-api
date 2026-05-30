"use client";

import { useEffect, useMemo, useState } from "react";
import AuthExperienceShell from "@/components/AuthExperienceShell";
import CockpitBackLink from "@/components/CockpitBackLink";
import { API_BASE_URL, apiRequest } from "@/lib/api";
import {
  ActionButton,
  MetricCard,
  TextField,
  WealthToast,
} from "@/components/ui/WealthUI";

type ConsentRecord = {
  accepted?: boolean;
  policy_version?: string;
  region?: string;
  created_at?: string;
};

type PrivacyCenterData = {
  policy_version: string;
  data_summary: Record<string, number>;
  consents: Record<string, ConsentRecord>;
  consent_history: Array<{
    consent_key: string;
    accepted: boolean;
    policy_version?: string;
    region?: string;
    created_at?: string;
  }>;
  preferences: {
    email_preferences?: Record<string, boolean>;
    ai_preferences?: Record<string, boolean>;
    cookie_preferences?: Record<string, boolean>;
  };
  deletion_request?: {
    status?: string;
    scheduled_for?: string;
  } | null;
  ai_disclosure: {
    provider: string;
    purpose: string;
    training: string;
    retention: string;
    human_note: string;
  };
};

const consentLabels: Record<string, string> = {
  terms_accepted: "Conditions generales",
  privacy_policy_accepted: "Politique de confidentialite",
  ai_processing_accepted: "Accompagnement Ethan",
  marketing_emails_accepted: "Emails marketing",
  analytics_accepted: "Mesure d'usage",
  personalized_opportunities_accepted: "Opportunites personnalisees",
  weekly_reports_accepted: "Rapports hebdomadaires",
  third_party_data_processing_accepted: "Donnees partenaires",
};

const emailLabels: Record<string, string> = {
  weekly_reports: "Rapports hebdomadaires",
  marketing: "Marketing",
  product_updates: "Evolutions produit",
  opportunities: "Opportunites",
  challenges: "Challenges",
  onboarding: "Accompagnement onboarding",
  founder_program: "Programme fondateur",
};

const dataLabels: Record<string, string> = {
  portfolio: "Actifs portefeuille",
  real_estate: "Actifs immobiliers",
  ethan_memory: "Memoire Ethan",
  notifications: "Notifications",
  legacy: "Elements Dynasty",
  oauth_accounts: "Comptes sociaux",
};

function ToggleRow({
  label,
  checked,
  onChange,
  locked,
}: {
  label: string;
  checked: boolean;
  onChange: (value: boolean) => void;
  locked?: boolean;
}) {
  return (
    <label className="flex items-center justify-between gap-4 rounded-xl border border-white/10 bg-white/[0.04] px-4 py-3">
      <span className="text-sm font-semibold text-gray-100">{label}</span>
      <input
        type="checkbox"
        checked={checked}
        disabled={locked}
        onChange={(event) => onChange(event.target.checked)}
        className="h-4 w-4 accent-[#3fa9f5] disabled:opacity-40"
      />
    </label>
  );
}

export default function PrivacyCenterPage() {
  const [token] = useState<string | null>(() =>
    typeof window === "undefined" ? null : localStorage.getItem("token")
  );
  const [data, setData] = useState<PrivacyCenterData | null>(null);
  const [consents, setConsents] = useState<Record<string, boolean>>({});
  const [emailPreferences, setEmailPreferences] = useState<Record<string, boolean>>({});
  const [deletePassword, setDeletePassword] = useState("");
  const [deleteReason, setDeleteReason] = useState("");
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" | "info" } | null>(null);
  const [loading, setLoading] = useState(true);

  const downloadBase = useMemo(() => API_BASE_URL.replace(/\/$/, ""), []);

  const load = async (nextToken: string) => {
    setLoading(true);
    try {
      const response = await apiRequest<PrivacyCenterData>("/privacy/center", nextToken);
      setData(response);
      setConsents(
        Object.fromEntries(
          Object.keys(consentLabels).map((key) => [
            key,
            Boolean(response.consents?.[key]?.accepted),
          ])
        )
      );
      setEmailPreferences(response.preferences?.email_preferences || {});
    } catch (error) {
      setToast({
        type: "error",
        message: error instanceof Error ? error.message : "Impossible de charger le Privacy Center.",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!token) {
      window.location.href = "/login";
      return;
    }
    Promise.resolve().then(() => load(token));

    const params = new URLSearchParams(window.location.search);
    const confirmToken = params.get("confirm_delete");
    if (confirmToken) {
      apiRequest(`/privacy/delete-account/confirm/${confirmToken}`, token, {
        method: "POST",
      })
        .then(() => {
          setToast({ type: "success", message: "Demande de suppression confirmee." });
          window.history.replaceState({}, "", "/privacy-center");
          Promise.resolve().then(() => load(token));
        })
        .catch(() => setToast({ type: "error", message: "Confirmation impossible ou deja traitee." }));
    }
  }, [token]);

  const saveConsents = async () => {
    if (!token) return;
    try {
      await apiRequest("/privacy/consents", token, {
        method: "PUT",
        body: JSON.stringify(consents),
      });
      setToast({ type: "success", message: "Consentements mis a jour." });
      await load(token);
    } catch (error) {
      setToast({ type: "error", message: error instanceof Error ? error.message : "Mise a jour impossible." });
    }
  };

  const saveEmailPreferences = async () => {
    if (!token) return;
    try {
      await apiRequest("/privacy/email-preferences", token, {
        method: "PUT",
        body: JSON.stringify(emailPreferences),
      });
      setToast({ type: "success", message: "Preferences email mises a jour." });
      await load(token);
    } catch (error) {
      setToast({ type: "error", message: error instanceof Error ? error.message : "Mise a jour impossible." });
    }
  };

  const requestExport = async (format: "json" | "csv" | "pdf") => {
    if (!token) return;
    try {
      const response = await apiRequest<{ download_url: string }>(
        "/privacy/export",
        token,
        {
          method: "POST",
          body: JSON.stringify({ format }),
        }
      );
      window.open(`${downloadBase}${response.download_url}`, "_blank", "noopener,noreferrer");
      setToast({ type: "success", message: "Export prepare. Le lien expire dans 7 jours." });
    } catch (error) {
      setToast({ type: "error", message: error instanceof Error ? error.message : "Export impossible." });
    }
  };

  const requestDeletion = async () => {
    if (!token) return;
    try {
      await apiRequest("/privacy/delete-account", token, {
        method: "POST",
        body: JSON.stringify({ password: deletePassword, reason: deleteReason }),
      });
      setDeletePassword("");
      setDeleteReason("");
      setToast({
        type: "success",
        message: "Demande enregistree. Confirme-la depuis l'email de securite.",
      });
      await load(token);
    } catch (error) {
      setToast({ type: "error", message: error instanceof Error ? error.message : "Demande impossible." });
    }
  };

  const cancelDeletion = async () => {
    if (!token) return;
    try {
      await apiRequest("/privacy/delete-account/cancel", token, { method: "POST" });
      setToast({ type: "success", message: "Demande de suppression annulee." });
      await load(token);
    } catch (error) {
      setToast({ type: "error", message: error instanceof Error ? error.message : "Annulation impossible." });
    }
  };

  return (
    <AuthExperienceShell fullScreen>
      <WealthToast
        message={toast?.message}
        type={toast?.type}
        onClose={() => setToast(null)}
      />

      <main className="relative z-10 mx-auto min-h-screen max-w-6xl px-5 py-24 text-white sm:px-6">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs uppercase tracking-widest text-[#3fa9f5]">
              Privacy Center
            </p>
            <h1 className="mt-2 text-3xl font-black sm:text-5xl">
              Controle, transparence et confiance.
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-gray-300 sm:text-base">
              Gere tes consentements, tes exports et tes preferences de
              confidentialite depuis un espace clair et securise.
            </p>
          </div>
          <CockpitBackLink />
        </div>

        {loading ? (
          <section className="rounded-2xl border border-white/10 bg-black/45 p-6 backdrop-blur-xl">
            <div className="h-4 w-40 animate-pulse rounded-full bg-white/10" />
            <div className="mt-5 grid gap-4 sm:grid-cols-3">
              {[0, 1, 2].map((item) => (
                <div key={item} className="h-28 animate-pulse rounded-2xl bg-white/[0.05]" />
              ))}
            </div>
          </section>
        ) : (
          <div className="space-y-6">
            <section className="rounded-2xl border border-white/10 bg-black/45 p-5 backdrop-blur-xl">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <h2 className="text-2xl font-black">Donnees stockees</h2>
                  <p className="mt-2 text-sm text-gray-400">
                    Resume operationnel des principales categories rattachees a ton compte.
                  </p>
                </div>
                <p className="text-xs uppercase tracking-widest text-gray-500">
                  Version {data?.policy_version}
                </p>
              </div>
              <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                {Object.entries(data?.data_summary || {}).map(([key, value]) => (
                  <MetricCard key={key} label={dataLabels[key] || key} value={value} tone="primary" />
                ))}
              </div>
            </section>

            <section className="grid gap-6 lg:grid-cols-2">
              <div className="rounded-2xl border border-white/10 bg-black/45 p-5 backdrop-blur-xl">
                <h2 className="text-2xl font-black">Consentements</h2>
                <p className="mt-2 text-sm text-gray-400">
                  Les consentements essentiels restent necessaires pour exploiter ton espace en securite.
                </p>
                <div className="mt-5 space-y-3">
                  {Object.entries(consentLabels).map(([key, label]) => (
                    <ToggleRow
                      key={key}
                      label={label}
                      checked={Boolean(consents[key])}
                      locked={key === "terms_accepted" || key === "privacy_policy_accepted"}
                      onChange={(value) =>
                        setConsents((current) => ({ ...current, [key]: value }))
                      }
                    />
                  ))}
                </div>
                <div className="mt-5">
                  <ActionButton onClick={saveConsents}>Enregistrer</ActionButton>
                </div>
              </div>

              <div className="rounded-2xl border border-white/10 bg-black/45 p-5 backdrop-blur-xl">
                <h2 className="text-2xl font-black">Emails et rapports</h2>
                <p className="mt-2 text-sm text-gray-400">
                  Choisis les messages que WHITE ROCK peut t&apos;envoyer.
                </p>
                <div className="mt-5 space-y-3">
                  {Object.entries(emailLabels).map(([key, label]) => (
                    <ToggleRow
                      key={key}
                      label={label}
                      checked={Boolean(emailPreferences[key])}
                      onChange={(value) =>
                        setEmailPreferences((current) => ({ ...current, [key]: value }))
                      }
                    />
                  ))}
                </div>
                <div className="mt-5">
                  <ActionButton onClick={saveEmailPreferences}>Enregistrer</ActionButton>
                </div>
              </div>
            </section>

            <section className="grid gap-6 lg:grid-cols-2">
              <div className="rounded-2xl border border-white/10 bg-black/45 p-5 backdrop-blur-xl">
                <h2 className="text-2xl font-black">Export de donnees</h2>
                <p className="mt-2 text-sm leading-relaxed text-gray-400">
                  Genere une copie securisee de ton profil, patrimoine, historique,
                  progression, abonnements et memoire Ethan.
                </p>
                <div className="mt-5 flex flex-wrap gap-3">
                  <ActionButton onClick={() => requestExport("json")}>Archive complete</ActionButton>
                  <ActionButton variant="secondary" onClick={() => requestExport("csv")}>
                    Tableau
                  </ActionButton>
                  <ActionButton variant="ghost" onClick={() => requestExport("pdf")}>
                    PDF
                  </ActionButton>
                </div>
              </div>

              <div className="rounded-2xl border border-red-300/20 bg-red-950/20 p-5 backdrop-blur-xl">
                <h2 className="text-2xl font-black">Suppression du compte</h2>
                <p className="mt-2 text-sm leading-relaxed text-red-100/80">
                  Une demande active lance un delai de securite de 7 jours. Les
                  donnees de facturation legalement necessaires sont conservees.
                </p>
                {data?.deletion_request?.status === "pending" ||
                data?.deletion_request?.status === "confirmed" ? (
                  <div className="mt-5 rounded-xl border border-red-300/20 bg-black/30 p-4">
                    <p className="text-sm text-red-100">
                      Demande {data.deletion_request.status}. Execution prevue le{" "}
                      {data.deletion_request.scheduled_for || "delai en cours"}.
                    </p>
                    <div className="mt-4">
                      <ActionButton variant="secondary" onClick={cancelDeletion}>
                        Annuler la demande
                      </ActionButton>
                    </div>
                  </div>
                ) : (
                  <div className="mt-5 space-y-3">
                    <TextField
                      label="Mot de passe"
                      type="password"
                      value={deletePassword}
                      onChange={setDeletePassword}
                    />
                    <TextField
                      label="Raison optionnelle"
                      value={deleteReason}
                      onChange={setDeleteReason}
                    />
                    <ActionButton
                      variant="danger"
                      disabled={!deletePassword}
                      onClick={requestDeletion}
                    >
                      Demander la suppression
                    </ActionButton>
                  </div>
                )}
              </div>
            </section>

            <section className="rounded-2xl border border-white/10 bg-black/45 p-5 backdrop-blur-xl">
              <h2 className="text-2xl font-black">Ethan et traitement des donnees</h2>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                {data?.ai_disclosure &&
                  Object.entries(data.ai_disclosure).map(([key, value]) => (
                    <div key={key} className="rounded-xl border border-white/10 bg-white/[0.04] p-4">
                      <p className="text-xs uppercase tracking-widest text-gray-500">{key}</p>
                      <p className="mt-2 text-sm leading-relaxed text-gray-200">{value}</p>
                    </div>
                  ))}
              </div>
            </section>

            <section id="policy" className="rounded-2xl border border-white/10 bg-black/45 p-5 backdrop-blur-xl">
              <h2 className="text-2xl font-black">Transparence</h2>
              <p className="mt-3 text-sm leading-relaxed text-gray-400">
                WHITE ROCK applique une logique privacy by design : minimisation
                des donnees, consentements historises, audit des actions sensibles,
                expiration automatique des exports et suppression differee avec
                delai de securite.
              </p>
            </section>
          </div>
        )}
      </main>
    </AuthExperienceShell>
  );
}

