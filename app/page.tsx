"use client";

import { FormEvent, useMemo, useState } from "react";
import AuthExperienceShell from "@/components/AuthExperienceShell";
import SocialLoginButtons from "@/components/auth/SocialLoginButtons";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  "https://family-office-api-n4sv.onrender.com";

function isValidEmail(email: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

type SubmitState = "idle" | "loading" | "success" | "error";

export default function Home() {
  const [email, setEmail] = useState("");
  const [consents, setConsents] = useState({
    terms_accepted: false,
    privacy_policy_accepted: false,
    ai_processing_accepted: true,
    marketing_emails_accepted: false,
    analytics_accepted: false,
    personalized_opportunities_accepted: true,
    weekly_reports_accepted: true,
    third_party_data_processing_accepted: false,
  });
  const [submitState, setSubmitState] = useState<SubmitState>("idle");
  const [message, setMessage] = useState("");

  const emailOk = useMemo(() => isValidEmail(email.trim()), [email]);
  const legalOk = consents.terms_accepted && consents.privacy_policy_accepted;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

    const cleanEmail = email.trim().toLowerCase();

    if (!cleanEmail || !isValidEmail(cleanEmail)) {
      setSubmitState("error");
      setMessage("Entre un email valide pour commencer.");
      return;
    }

    if (!legalOk) {
      setSubmitState("error");
      setMessage("Accepte les CGU et la politique de confidentialite pour creer ton espace.");
      return;
    }

    setSubmitState("loading");
    setMessage("");

    try {
      const res = await fetch(`${API_BASE_URL}/auth/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          accept: "application/json",
        },
        body: JSON.stringify({ email: cleanEmail, ...consents }),
      });

      const data = await res.json().catch(() => null);

      if (!res.ok) {
        throw new Error(data?.detail || "Erreur serveur");
      }

      localStorage.setItem("verified_email", cleanEmail);
      localStorage.setItem("current_email", cleanEmail);

      setSubmitState("success");

      if (data?.action === "login") {
        setMessage("Ton espace existe deja. Redirection...");
        setTimeout(() => {
          window.location.href = "/login";
        }, 900);
        return;
      }

      setMessage("Parfait. Verifie ton email pour activer ton espace.");
      setTimeout(() => {
        window.location.href = "/verify-email";
      }, 1100);
    } catch (err: unknown) {
      console.error(err);
      setSubmitState("error");
      setMessage(err instanceof Error ? err.message : "Erreur reseau");
    }
  };

  return (
    <AuthExperienceShell fullScreen>
      <section className="relative z-10 mx-auto flex min-h-screen max-w-6xl flex-col justify-between px-5 py-6 sm:px-6 sm:py-8">
        <header className="flex items-center justify-between">
          <div />
          <a
            href="/login"
            className="rounded-xl border border-[#3fa9f5]/50 bg-[#3fa9f5] px-4 py-2 text-sm font-bold text-white shadow-lg shadow-[#3fa9f5]/20 backdrop-blur transition hover:bg-white hover:text-[#0b1725]"
          >
            Connexion
          </a>
        </header>

        <div className="grid items-end gap-8 py-10 sm:py-14 lg:grid-cols-[1.2fr_0.8fr]">
          <div>
            <p className="mb-4 text-xs uppercase tracking-widest text-[#3fa9f5] sm:text-sm">
              Reprendre le controle sans subir la complexite.
            </p>
            <h1 className="max-w-3xl text-3xl font-black leading-tight sm:text-5xl">
              Pilote ton patrimoine avec clarte, calme et progression.
            </h1>
            <p className="mt-5 max-w-2xl text-base leading-relaxed text-gray-300 sm:text-lg">
              WHITE ROCK centralise ta situation, t&apos;aide a voir les priorites et
              transforme la gestion financiere en rituel simple, premium et
              motivant.
            </p>

            <form
              onSubmit={handleSubmit}
              className="mt-8 max-w-xl rounded-2xl border border-white/10 bg-black/45 p-3 backdrop-blur"
            >
              <div className="flex flex-col gap-3 sm:flex-row">
                <input
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="ton@email.com"
                  className="min-w-0 flex-1 rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-white outline-none placeholder:text-gray-500 focus:border-[#3fa9f5]"
                />
                <button
                  disabled={!emailOk || !legalOk || submitState === "loading"}
                  className="rounded-xl bg-[#3fa9f5] px-6 py-3 font-bold text-white disabled:opacity-50"
                >
                  {submitState === "loading" ? "Ouverture..." : "Creer mon espace"}
                </button>
              </div>

              <div className="mt-4 space-y-2 rounded-xl border border-white/10 bg-black/25 p-3 text-xs text-gray-300">
                {[
                  ["terms_accepted", "J'accepte les conditions generales."],
                  ["privacy_policy_accepted", "J'accepte la politique de confidentialite."],
                  ["ai_processing_accepted", "J'autorise le moteur IA a traiter mes donnees pour personnaliser l'accompagnement."],
                  ["weekly_reports_accepted", "Je souhaite recevoir mes rapports patrimoniaux hebdomadaires."],
                ].map(([key, label]) => (
                  <label key={key} className="flex items-start gap-2">
                    <input
                      type="checkbox"
                      checked={Boolean(consents[key as keyof typeof consents])}
                      onChange={(event) =>
                        setConsents((current) => ({
                          ...current,
                          [key]: event.target.checked,
                        }))
                      }
                      className="mt-0.5 h-4 w-4 accent-[#3fa9f5]"
                    />
                    <span>{label}</span>
                  </label>
                ))}
              </div>
            </form>

            {message && (
              <p
                className={`mt-4 text-sm ${
                  submitState === "error" ? "text-red-300" : "text-emerald-300"
                }`}
              >
                {message}
              </p>
            )}

            <div className="mt-5 max-w-xl">
              <div className="mb-3 flex items-center gap-3 text-xs uppercase tracking-widest text-white/40">
                <span className="h-px flex-1 bg-white/10" />
                Connexion rapide
                <span className="h-px flex-1 bg-white/10" />
              </div>
              <SocialLoginButtons disabled={!legalOk || submitState === "loading"} />
              {!legalOk && (
                <p className="mt-2 text-xs text-amber-100/80">
                  Accepte les conditions et la confidentialite avant de continuer
                  avec un provider social.
                </p>
              )}
            </div>

            <div className="mt-4 space-y-1 text-sm text-white/60">
              <p>Construis une vision claire de ton patrimoine.</p>
              <p>Un systeme pense pour progresser sereinement, sans surcharge.</p>
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-black/45 p-5 backdrop-blur-xl">
            <p className="text-xs uppercase tracking-widest text-gray-400">
              Experience
            </p>
            <div className="mt-4 space-y-4">
              {[
                ["Vision globale", "Un seul endroit pour comprendre ou tu en es."],
                ["Daily Insight", "Une action utile a chaque ouverture."],
                ["Progression", "Des niveaux et missions qui donnent envie de revenir."],
              ].map(([title, description]) => (
                <div key={title} className="rounded-xl bg-black/35 p-4">
                  <p className="font-semibold">{title}</p>
                  <p className="mt-1 text-sm text-gray-400">{description}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        <section className="mb-8 rounded-2xl border border-amber-300/20 bg-black/50 p-5 shadow-2xl backdrop-blur-xl sm:p-6">
          <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr] lg:items-end">
            <div>
              <p className="text-xs uppercase tracking-widest text-amber-200">
                Legacy
              </p>
              <h2 className="mt-2 text-2xl font-black text-white sm:text-3xl">
                Beyond Financial Freedom
              </h2>
              <p className="mt-3 max-w-2xl text-sm leading-relaxed text-gray-300 sm:text-base">
                Construire une fortune est une etape. Construire un heritage est
                une responsabilite.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              {[
                "Transmission",
                "Gouvernance",
                "Protection",
                "Dynastie",
                "Famille",
                "Stabilite",
              ].map((item) => (
                <div
                  key={item}
                  className="rounded-xl border border-white/10 bg-white/[0.04] px-3 py-3 text-sm font-semibold text-white"
                >
                  {item}
                </div>
              ))}
            </div>
          </div>
        </section>

        <footer className="flex flex-wrap items-center justify-between gap-3 text-xs text-white/50">
          <span>Vision Business Mastery</span>
          <div className="flex gap-4">
            <a href="https://vision-business.com">Site web</a>
            <a href="https://www.linkedin.com">LinkedIn</a>
            <a href="https://www.instagram.com">Instagram</a>
          </div>
        </footer>
      </section>
    </AuthExperienceShell>
  );
}
