"use client";

import { useState, useRef, useEffect, useCallback, FormEvent, KeyboardEvent } from "react";
import { chatbotApi, getErrorMessage, type ChatMessage } from "@/lib/api";
import styles from "./ChatWidget.module.css";

export default function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [streaming, setStreaming] = useState("");
  const [error, setError] = useState("");
  const [historyLoaded, setHistoryLoaded] = useState(false);

  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = useCallback(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => { scrollToBottom(); }, [messages, streaming, scrollToBottom]);

  // Load history when first opened
  useEffect(() => {
    if (open && !historyLoaded) {
      chatbotApi.getHistory().then((data) => {
        setMessages(data ?? []);
        setHistoryLoaded(true);
      }).catch(() => setHistoryLoaded(true));
    }
  }, [open, historyLoaded]);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  async function handleSend(e?: FormEvent) {
    e?.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || sending) return;

    setError("");
    setInput("");
    const userMsg: ChatMessage = {
      role: "user",
      content: trimmed,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setSending(true);
    setStreaming("");

    try {
      let full = "";
      for await (const chunk of chatbotApi.sendMessageStream(trimmed)) {
        full += chunk;
        setStreaming(full);
      }
      const assistantMsg: ChatMessage = {
        role: "assistant",
        content: full,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
      setStreaming("");
    } catch (err: unknown) {
      setError(getErrorMessage(err, "Erreur. Réessayez."));
      setStreaming("");
    } finally {
      setSending(false);
      inputRef.current?.focus();
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <>
      {/* Floating button */}
      {!open && (
        <button
          className={styles.fab}
          onClick={() => setOpen(true)}
          aria-label="Ouvrir le chat"
        >
          💬
        </button>
      )}

      {/* Chat popup */}
      {open && (
        <div className={styles.popup}>
          <div className={styles.popupHeader}>
            <span className={styles.popupTitle}>Assistant Judi-Expert</span>
            <button
              className={styles.closeBtn}
              onClick={() => setOpen(false)}
              aria-label="Fermer le chat"
            >
              ✕
            </button>
          </div>

          <div className={styles.messagesArea}>
            {messages.length === 0 && !sending && (
              <p className={styles.empty}>Posez votre question…</p>
            )}
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`${styles.msg} ${msg.role === "user" ? styles.msgUser : styles.msgBot}`}
              >
                {msg.content}
              </div>
            ))}
            {streaming && (
              <div className={`${styles.msg} ${styles.msgBot}`}>
                {streaming}
                <span className={styles.cursor}>▌</span>
              </div>
            )}
            {sending && !streaming && (
              <div className={styles.typing}>
                <span /><span /><span />
              </div>
            )}
            {error && <p className={styles.error}>{error}</p>}
            <div ref={endRef} />
          </div>

          <form className={styles.inputArea} onSubmit={handleSend}>
            <textarea
              ref={inputRef}
              className={styles.input}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Tapez votre message…"
              rows={1}
              disabled={sending}
            />
            <button
              type="submit"
              className={styles.sendBtn}
              disabled={sending || !input.trim()}
            >
              ➤
            </button>
          </form>
        </div>
      )}
    </>
  );
}
