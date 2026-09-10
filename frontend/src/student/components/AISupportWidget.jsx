import { useEffect, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useLocation } from "react-router-dom";
import { askStudentSupport } from "@/api/studentSupport";

const quickPrompts = ["Explain this lesson", "Help debug my code", "Give me a hint"];

function AIMessageIcon({ className = "h-6 w-6" }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" aria-hidden="true">
      <path
        d="M5 6.75A3.75 3.75 0 0 1 8.75 3h6.5A3.75 3.75 0 0 1 19 6.75v4.8a3.75 3.75 0 0 1-3.75 3.75h-3.6L7.2 19v-3.86A3.75 3.75 0 0 1 5 11.55v-4.8Z"
        fill="currentColor"
      />
      <path
        d="M9 10.25h6M9 12.9h3.6"
        stroke="#0f4c75"
        strokeWidth="1.7"
        strokeLinecap="round"
      />
      <path
        d="M16.8 4.9v2.2M15.7 6h2.2"
        stroke="#ff6f61"
        strokeWidth="1.45"
        strokeLinecap="round"
      />
    </svg>
  );
}

function SendIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d="m4 12 16-7-7 16-2-7-7-2Z" strokeLinejoin="round" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d="m6 6 12 12M18 6 6 18" strokeLinecap="round" />
    </svg>
  );
}

function toSupportHistory(messages) {
  return messages
    .filter((message) => message.role === "student" || message.role === "assistant")
    .slice(-8)
    .map((message) => ({ role: message.role, content: message.content }));
}

export default function AISupportWidget({ avoidMobileNav = true }) {
  const location = useLocation();
  const listRef = useRef(null);
  const [isOpen, setIsOpen] = useState(false);
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState([
    {
      id: "welcome",
      role: "assistant",
      content: "What are you working on?",
    },
  ]);
  const [error, setError] = useState("");

  const supportMutation = useMutation({
    mutationFn: askStudentSupport,
  });

  useEffect(() => {
    if (isOpen) {
      listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
    }
  }, [messages, isOpen, supportMutation.isPending]);

  const submitQuestion = async (question) => {
    const clean = question.trim();
    if (!clean || supportMutation.isPending) {
      return;
    }

    setDraft("");
    setError("");
    const studentMessage = {
      id: `${Date.now()}-student`,
      role: "student",
      content: clean,
    };
    const previousMessages = messages;
    setMessages((current) => [...current, studentMessage]);

    try {
      const data = await supportMutation.mutateAsync({
        question: clean,
        history: toSupportHistory(previousMessages),
        pagePath: location.pathname,
      });
      setMessages((current) => [
        ...current,
        {
          id: `${Date.now()}-assistant`,
          role: "assistant",
          content: data?.answer || "I could not produce an answer for that.",
        },
      ]);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "AI support is not available right now.");
    }
  };

  const panelBottomClass = avoidMobileNav ? "bottom-[92px] md:bottom-24" : "bottom-24";
  const buttonBottomClass = avoidMobileNav ? "bottom-20 md:bottom-6" : "bottom-5 md:bottom-6";

  return (
    <>
      {isOpen ? (
        <section
          className={`fixed right-4 z-[60] flex max-h-[min(640px,calc(100vh-120px))] w-[calc(100vw-2rem)] max-w-sm flex-col overflow-hidden rounded-2xl border border-ocean-600/10 bg-white shadow-[0_24px_60px_rgba(16,33,47,0.2)] ${panelBottomClass} md:right-6`}
          aria-label="AI support chat"
        >
          <header className="flex min-h-14 items-center justify-between border-b border-line px-4">
            <div>
              <p className="text-sm font-bold text-ink">AI Support</p>
              <p className="text-xs text-muted">LearnCode tutor</p>
            </div>
            <button
              type="button"
              onClick={() => setIsOpen(false)}
              className="inline-flex h-9 w-9 items-center justify-center rounded-xl text-ocean-800 transition hover:bg-reef/50"
              aria-label="Close AI support"
            >
              <CloseIcon />
            </button>
          </header>

          <div ref={listRef} className="min-h-0 flex-1 space-y-3 overflow-y-auto bg-cream p-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.role === "student" ? "justify-end" : "justify-start"}`}
              >
                <p
                  className={`max-w-[84%] whitespace-pre-wrap rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed ${
                    message.role === "student"
                      ? "bg-ocean-600 text-white"
                      : "border border-line bg-white text-ink"
                  }`}
                >
                  {message.content}
                </p>
              </div>
            ))}
            {supportMutation.isPending ? (
              <div className="flex justify-start">
                <p className="rounded-2xl border border-line bg-white px-3.5 py-2.5 text-sm text-muted">
                  Thinking...
                </p>
              </div>
            ) : null}
          </div>

          <div className="border-t border-line bg-white p-3">
            {messages.length === 1 ? (
              <div className="mb-3 flex gap-2 overflow-x-auto pb-1">
                {quickPrompts.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => submitQuestion(prompt)}
                    className="shrink-0 rounded-xl border border-ocean-200 bg-reef/35 px-3 py-1.5 text-xs font-semibold text-ocean-800 transition hover:bg-reef"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            ) : null}
            {error ? (
              <p className="mb-2 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700" role="alert">
                {error}
              </p>
            ) : null}
            <form
              className="flex items-end gap-2"
              onSubmit={(event) => {
                event.preventDefault();
                submitQuestion(draft);
              }}
            >
              <label htmlFor="ai-support-question" className="sr-only">
                Ask AI support
              </label>
              <textarea
                id="ai-support-question"
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                rows={2}
                maxLength={4000}
                placeholder="Ask for help..."
                className="min-h-[44px] flex-1 resize-none rounded-xl border border-line bg-cream px-3 py-2 text-sm text-ink outline-none transition placeholder:text-muted/80 focus:border-ocean-600 focus:bg-white focus:ring-2 focus:ring-ocean-600/20"
              />
              <button
                type="submit"
                disabled={!draft.trim() || supportMutation.isPending}
              className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-ocean-800 text-white transition hover:bg-ocean-700 disabled:cursor-not-allowed disabled:opacity-50"
                aria-label="Send question"
              >
                <SendIcon />
              </button>
            </form>
          </div>
        </section>
      ) : null}

      <button
        type="button"
        onClick={() => setIsOpen((value) => !value)}
        className={`fixed right-5 z-[61] inline-flex h-[70px] w-[70px] items-center justify-center rounded-full border border-ocean-200 bg-cream text-ocean-800 shadow-[0_18px_38px_rgba(16,44,61,0.22)] transition hover:-translate-y-0.5 hover:border-ocean-600/30 hover:bg-reef focus:outline-none focus:ring-4 focus:ring-ocean-600/20 md:right-8 ${buttonBottomClass}`}
        aria-label={isOpen ? "Close AI support" : "Open AI support"}
        aria-expanded={isOpen}
      >
        <span className="relative inline-flex h-12 w-12 items-center justify-center rounded-[16px] bg-ocean-800 text-cream shadow-[inset_0_1px_0_rgba(255,255,255,0.16)]">
          <AIMessageIcon className="h-8 w-8" />
          <span className="absolute -right-1 -top-1 h-3.5 w-3.5 rounded-full border-2 border-cream bg-coral" />
        </span>
      </button>
    </>
  );
}
