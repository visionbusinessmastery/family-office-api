"use client";

import { FormEvent, useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";
import type { GamificationData } from "@/lib/types";

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

type AdvisorResponse = {
  result?: {
    analysis?: string;
    context_score?: number;
  };
};

type AdvisorChatProps = {
  recommendations?: string[];
  aiCoach?: GamificationData["ai_coach"];
  notification?: GamificationData["notification"];
};

const initialMessages: ChatMessage[] = [
  {
    role: "assistant",
    content:
      "Je suis Ethan. Pose-moi une question sur ton patrimoine, tes risques, tes opportunites ou ta prochaine action utile.",
  },
];

const CACHE_TTL_MS = 24 * 60 * 60 * 1000;
const MAX_CACHED_MESSAGES = 40;
const CONVERSATION_CACHE_VERSION = "v2-zero-template-guard";
const LEGACY_RESPONSE_PATTERNS = [
  "ton score est",
  "score 39/100",
  "pour le cashflow",
  "action simple",
  "action prioritaire",
  "priorite:",
  "priorité:",
  "clarifier la capacite",
  "capacité mensuelle disponible",
];

type CachedConversation = {
  version?: string;
  updatedAt: number;
  messages: ChatMessage[];
};

function getUserCacheKey() {
  if (typeof window === "undefined") {
    return `ethanConversation:${CONVERSATION_CACHE_VERSION}:anonymous`;
  }

  const token = localStorage.getItem("token");
  if (!token) return `ethanConversation:${CONVERSATION_CACHE_VERSION}:anonymous`;

  try {
    const tokenPayload = token.split(".")[1];
    const paddedPayload = tokenPayload.padEnd(
      tokenPayload.length + ((4 - (tokenPayload.length % 4)) % 4),
      "="
    );
    const payload = JSON.parse(
      atob(paddedPayload.replace(/-/g, "+").replace(/_/g, "/"))
    );
    return `ethanConversation:${CONVERSATION_CACHE_VERSION}:${
      payload.sub || payload.email || payload.user_id || "user"
    }`;
  } catch {
    return `ethanConversation:${CONVERSATION_CACHE_VERSION}:user`;
  }
}

function normalizeConversationText(value: string) {
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

function hasLegacyResponse(messages: ChatMessage[]) {
  const normalizedMessages = messages.map((message) =>
    normalizeConversationText(message.content)
  );

  return normalizedMessages.some((content) =>
    LEGACY_RESPONSE_PATTERNS.some((pattern) =>
      content.includes(normalizeConversationText(pattern))
    )
  );
}

function clearConversationCache() {
  if (typeof window === "undefined") return;

  Object.keys(localStorage)
    .filter((key) => key.startsWith("ethanConversation:"))
    .forEach((key) => localStorage.removeItem(key));
}

function trimMessages(messages: ChatMessage[]) {
  if (messages.length <= MAX_CACHED_MESSAGES) return messages;

  const conversation = messages.filter(
    (message) => message.content !== initialMessages[0].content
  );

  return [
    initialMessages[0],
    ...conversation.slice(-(MAX_CACHED_MESSAGES - 1)),
  ];
}

function readCachedMessages() {
  if (typeof window === "undefined") return initialMessages;

  try {
    const raw = localStorage.getItem(getUserCacheKey());
    if (!raw) return initialMessages;

    const cached = JSON.parse(raw) as CachedConversation;
    if (
      cached.version !== CONVERSATION_CACHE_VERSION ||
      !cached.updatedAt ||
      Date.now() - cached.updatedAt > CACHE_TTL_MS ||
      !Array.isArray(cached.messages) ||
      hasLegacyResponse(cached.messages)
    ) {
      clearConversationCache();
      return initialMessages;
    }

    return cached.messages.length > 0
      ? trimMessages(cached.messages)
      : initialMessages;
  } catch {
    return initialMessages;
  }
}

function writeCachedMessages(messages: ChatMessage[]) {
  if (typeof window === "undefined") return;

  const payload: CachedConversation = {
    version: CONVERSATION_CACHE_VERSION,
    updatedAt: Date.now(),
    messages: trimMessages(messages),
  };

  localStorage.setItem(getUserCacheKey(), JSON.stringify(payload));
}

export default function AdvisorChat({
  recommendations = [],
  aiCoach,
  notification,
}: AdvisorChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [cacheReady, setCacheReady] = useState(false);
  const [detail, setDetail] = useState<{
    title: string;
    body: string;
    tone?: "blue" | "amber" | "cyan";
  } | null>(null);

  const token =
    typeof window !== "undefined" ? localStorage.getItem("token") : null;
  const affiliations = aiCoach?.affiliations || [];

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setMessages(readCachedMessages());
      setCacheReady(true);
    }, 0);

    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!cacheReady) return;
    writeCachedMessages(messages);
  }, [cacheReady, messages]);

  const clearConversation = () => {
    clearConversationCache();
    setMessages(initialMessages);
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();

    const question = input.trim();
    if (!question || loading) return;

    setMessages((current) => [
      ...current,
      { role: "user", content: question },
    ]);
    setInput("");
    setLoading(true);

    try {
      const data = await apiRequest<AdvisorResponse>("/advisor/advisor", token, {
        method: "POST",
        body: JSON.stringify({ message: question }),
      });

      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content:
            data.result?.analysis ||
            "Le moteur Ethan n'a pas renvoye de reponse exploitable pour le moment.",
        },
      ]);
    } catch (err) {
      console.error(err);
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content:
            "Je n'arrive pas a joindre le moteur de conseil pour le moment. Reessaie dans quelques instants.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="bg-zinc-950 border border-white/10 rounded-2xl p-4 shadow-2xl shadow-black/20 transition sm:p-6">
      <div className="mb-4">
        <p className="text-xs uppercase tracking-widest text-[#3fa9f5]">
          Conseiller Patrimonial
        </p>
        <div className="mt-1 flex items-center justify-between gap-3">
          <h2 className="text-2xl font-black">Ethan</h2>
          {messages.length > 1 && (
            <button
              type="button"
              onClick={clearConversation}
              className="rounded-full border border-white/10 px-3 py-1 text-xs text-gray-400 transition hover:border-red-400/40 hover:text-red-200"
            >
              Effacer
            </button>
          )}
        </div>
        <p className="text-sm text-gray-400">
          Un regard calme pour transformer ton contexte en decisions simples.
        </p>
      </div>

      <div className="mb-5 space-y-4">
        <div className="bg-[#3fa9f5]/10 border border-[#3fa9f5]/20 rounded-2xl p-4 transition hover:border-[#3fa9f5]/35">
          <h3 className="font-bold text-[#3fa9f5] mb-3">
            Conseils prioritaires
          </h3>

          <div className="space-y-2">
            {recommendations.length > 0 ? (
              recommendations.map((advice, index) => (
                <p key={`${advice}-${index}`} className="text-sm text-gray-300">
                  {advice}
                </p>
              ))
            ) : (
              <p className="text-sm text-gray-400">
                Aucun conseil prioritaire pour le moment.
              </p>
            )}
          </div>
        </div>

        <button
          type="button"
          onClick={() =>
            setDetail({
              title: "Guidance du jour",
              body:
                aiCoach?.message ||
                "Complete ton cockpit avec une donnee utile pour enrichir le contexte backend.",
              tone: "cyan",
            })
          }
          className="w-full rounded-2xl border border-white/10 bg-white/5 p-4 text-left transition hover:border-white/20"
        >
          <h3 className="font-bold text-white mb-2">Guidance du jour</h3>

          <p className="text-sm text-gray-300 leading-relaxed">
            {aiCoach?.message ||
              "Tu construis une vraie base patrimoniale. Continue a completer ton cockpit, une donnee utile a la fois."}
          </p>

        </button>

        <button
          type="button"
          onClick={() =>
            setDetail({
              title: "Opportunités partenaires",
              body:
                affiliations.length > 0
                  ? affiliations
                      .map((item) => `${item.title}: ${item.reason}`)
                      .join("\n")
                  : "Aucun partenaire prioritaire pour le moment. Ethan n'affiche cette zone que lorsqu'une proposition est cohérente avec ton profil.",
              tone: "amber",
            })
          }
          className="w-full rounded-2xl border border-amber-300/20 bg-amber-300/10 p-4 text-left transition hover:border-amber-300/35"
        >
          <h3 className="font-bold text-amber-200 mb-3">
            Opportunités partenaires
          </h3>

          {affiliations.length > 0 ? (
            <div className="space-y-2">
              {affiliations.map((item, index) => (
                <div
                  key={`${item.title}-${index}`}
                  className="rounded-xl border border-white/10 bg-black/30 p-3"
                >
                  <p className="text-sm font-semibold text-white">
                    {item.title}
                  </p>
                  <p className="text-xs text-gray-400 mt-1">{item.reason}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-400">
              Ethan proposera des partenaires uniquement lorsqu&apos;ils sont coherents avec ton profil.
            </p>
          )}
        </button>

        <button
          type="button"
          onClick={() =>
            setDetail({
              title: notification?.title || "Notifications Ethan",
              body:
                notification?.message ||
                "Aucune alerte urgente pour l'instant. Les notifications apparaîtront ici lorsqu'un signal mérite ton attention.",
              tone: "blue",
            })
          }
          className="w-full rounded-2xl border border-blue-500/30 bg-blue-500/10 p-4 text-left transition hover:border-blue-400/40"
        >
          <h3 className="font-bold text-blue-400 mb-2">Notification</h3>

          <p className="text-sm text-white">
            {notification?.title || "Aucune alerte urgente"}
          </p>

          {notification?.message && (
            <p className="text-xs text-gray-400 mt-1">
              {notification.message}
            </p>
          )}
        </button>

        {detail && (
          <div className="rounded-2xl border border-white/10 bg-black/50 p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-widest text-[#3fa9f5]">
                  Détail
                </p>
                <h3 className="mt-1 font-bold text-white">{detail.title}</h3>
              </div>
              <button
                type="button"
                onClick={() => setDetail(null)}
                className="rounded-full border border-white/10 px-3 py-1 text-xs text-gray-400 hover:text-white"
              >
                Fermer
              </button>
            </div>
            <p className="mt-3 whitespace-pre-line text-sm leading-relaxed text-gray-300">
              {detail.body}
            </p>
          </div>
        )}
      </div>

      <div className="h-72 overflow-y-auto rounded-2xl border border-white/10 bg-black/40 p-3 space-y-3 sm:h-80 sm:p-4">
        {messages.map((message, index) => (
          <div
            key={`${message.role}-${index}`}
            className={`flex ${
              message.role === "user" ? "justify-end" : "justify-start"
            }`}
          >
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                message.role === "user"
                  ? "bg-[#3fa9f5] text-white"
                  : "bg-white/10 text-gray-200"
              }`}
            >
              {message.content}
            </div>
          </div>
        ))}

        {loading && (
          <div className="text-sm text-gray-400">Ethan reflechit...</div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-3 sm:flex-row">
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Ex: ou suis-je trop expose ?"
          className="min-w-0 flex-1 rounded-xl border border-white/10 bg-black px-4 py-3 text-white placeholder:text-gray-500 focus:outline-none focus:border-[#3fa9f5]"
        />

        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="rounded-xl bg-[#3fa9f5] px-5 py-3 font-semibold text-white disabled:opacity-50"
        >
          Demander
        </button>
      </form>
    </section>
  );
}
