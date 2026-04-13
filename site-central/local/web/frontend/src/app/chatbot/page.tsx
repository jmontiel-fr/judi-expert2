"use client";

import { useState, useEffect, useCallback, useRef, FormEvent, KeyboardEvent } from "react";
import styles from "./chatbot.module.css";
import {
  chatbotApi,
  getErrorMessage,
  type ChatMessage,
} from "@/lib/api";

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString("fr-FR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

/* ------------------------------------------------------------------ */
/* Main component                                                      */
/* ------------------------------------------------------------------ */

export default function ChatBotPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  /* ---------------------------------------------------------------- */
  /* Auto-scroll                                                       */
  /* ---------------------------------------------------------------- */

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, sending, scrollToBottom]);

  /* ---------------------------------------------------------------- */
  /* Load history                                                      */
  /* ---------------------------------------------------------------- */

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await chatbotApi.getHistory();
      setMessages(data ?? []);
    } catch (err: unknown) {
      setError(getErrorMessage(err, "Impossible de charger l'historique."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  /* ---------------------------------------------------------------- */
  /* Send message                                                      */
  /* ---------------------------------------------------------------- */

  async function handleSend(e?: FormEvent) {
    e?.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || sending) return;

    setError("");
    setInput("");

    // Optimistically add user message
    const userMsg: ChatMessage = {
      role: "user",
      content: trimmed,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setSending(true);

    try {
      const data = await chatbotApi.sendMessage(trimmed);

      const assistantMsg: ChatMessage = {
        role: "assistant",
        content: data.response,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: unknown) {
      setError(getErrorMessage(err, "Erreur lors de l'envoi du message. Veuillez réessayer."));
    } finally {
      setSending(false);
      textareaRef.current?.focus();
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  /* ---------------------------------------------------------------- */
  /* Render                                                            */
  /* ---------------------------------------------------------------- */

  return (
    <div className={styles.container}>
      {/* Page header */}
      <div className={styles.header}>
        <h1 className={styles.title}>Assistant ChatBot</h1>
        <p className={styles.subtitle}>
          Posez vos questions sur le système ou votre domaine d&apos;expertise.
        </p>
      </div>

      {/* Loading state */}
      {loading && (
        <div className={styles.loading}>
          <span className={styles.spinner} aria-hidden="true" />
          Chargement de l&apos;historique…
        </div>
      )}

      {/* Error (history load) */}
      {!loading && error && messages.length === 0 && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}

      {/* Messages area */}
      {!loading && (
        <div className={styles.messagesArea} role="log" aria-live="polite">
          {messages.length === 0 && !sending && (
            <div className={styles.emptyState}>
              <div className={styles.emptyIcon} aria-hidden="true">💬</div>
              <p className={styles.emptyTitle}>Aucun message</p>
              <p className={styles.emptyText}>
                Commencez la conversation en posant une question ci-dessous.
              </p>
            </div>
          )}

          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`${styles.message} ${
                msg.role === "user" ? styles.messageUser : styles.messageAssistant
              }`}
            >
              <div
                className={`${styles.messageBubble} ${
                  msg.role === "user" ? styles.bubbleUser : styles.bubbleAssistant
                }`}
              >
                {msg.content}
              </div>
              <span className={styles.messageTime}>
                {formatTime(msg.created_at)}
              </span>
            </div>
          ))}

          {/* Typing indicator */}
          {sending && (
            <div className={styles.typingIndicator} aria-label="L'assistant rédige une réponse">
              <span className={styles.typingDot} />
              <span className={styles.typingDot} />
              <span className={styles.typingDot} />
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      )}

      {/* Inline error */}
      {!loading && error && messages.length > 0 && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}

      {/* Input area */}
      {!loading && (
        <form className={styles.inputArea} onSubmit={handleSend}>
          <textarea
            ref={textareaRef}
            className={styles.input}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Tapez votre message…"
            rows={1}
            disabled={sending}
            aria-label="Message à envoyer"
          />
          <button
            type="submit"
            className={styles.sendButton}
            disabled={sending || !input.trim()}
          >
            {sending ? "Envoi…" : "Envoyer"}
          </button>
        </form>
      )}
    </div>
  );
}
