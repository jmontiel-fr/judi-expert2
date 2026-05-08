"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { apiChatbotMessage, type ChatbotMessage } from "@/lib/api";
import styles from "./ChatBot.module.css";

export default function ChatBot() {
  const { accessToken } = useAuth();
  const [messages, setMessages] = useState<ChatbotMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || isLoading || !accessToken) return;

    const userMsg: ChatbotMessage = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await apiChatbotMessage(text, [...messages, userMsg], accessToken);
      setMessages((prev) => [...prev, { role: "assistant", content: response }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Désolé, une erreur est survenue. Veuillez réessayer." },
      ]);
    } finally {
      setIsLoading(false);
    }
  }, [input, isLoading, accessToken, messages]);

  if (!accessToken) return null;

  return (
    <>
      {/* Floating button */}
      <button
        type="button"
        className={styles.floatingBtn}
        onClick={() => setIsOpen(!isOpen)}
        aria-label={isOpen ? "Fermer le chatbot" : "Ouvrir le chatbot"}
      >
        {isOpen ? "✕" : "💬"}
      </button>

      {/* Chat window */}
      {isOpen && (
        <div className={styles.chatWindow}>
          <div className={styles.chatHeader}>
            <span className={styles.chatTitle}>Assistant Judi-Expert</span>
            <button
              type="button"
              className={styles.closeBtn}
              onClick={() => setIsOpen(false)}
              aria-label="Fermer"
            >
              ✕
            </button>
          </div>

          <div className={styles.chatMessages}>
            {messages.length === 0 && (
              <div className={styles.welcomeMsg}>
                Bonjour ! Je suis l&apos;assistant Judi-Expert. Posez-moi vos questions sur le site, la FAQ, les CGU ou la méthodologie.
              </div>
            )}
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`${styles.message} ${msg.role === "user" ? styles.userMsg : styles.assistantMsg}`}
              >
                {msg.content}
              </div>
            ))}
            {isLoading && (
              <div className={`${styles.message} ${styles.assistantMsg}`}>
                <span className={styles.typing}>●●●</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className={styles.chatInput}>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              placeholder="Votre question…"
              className={styles.input}
              disabled={isLoading}
            />
            <button
              type="button"
              onClick={handleSend}
              disabled={isLoading || !input.trim()}
              className={styles.sendBtn}
            >
              ➤
            </button>
          </div>
        </div>
      )}
    </>
  );
}
