"use client";

import { useEffect, useRef, useCallback } from "react";

declare global {
  interface Window {
    grecaptcha?: {
      render: (
        container: HTMLElement,
        params: {
          sitekey: string;
          callback: (token: string) => void;
          "expired-callback"?: () => void;
          "error-callback"?: () => void;
          theme?: string;
          size?: string;
        }
      ) => number;
      reset: (widgetId: number) => void;
    };
    onRecaptchaLoad?: () => void;
  }
}

interface ReCaptchaWidgetProps {
  onVerify: (token: string) => void;
  onExpire?: () => void;
  onError?: () => void;
}

export default function ReCaptchaWidget({
  onVerify,
  onExpire,
  onError,
}: ReCaptchaWidgetProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const widgetIdRef = useRef<number | null>(null);
  const renderedRef = useRef(false);

  const siteKey = process.env.NEXT_PUBLIC_RECAPTCHA_SITE_KEY || "";

  const renderWidget = useCallback(() => {
    if (
      !window.grecaptcha ||
      !containerRef.current ||
      renderedRef.current ||
      !siteKey
    )
      return;

    renderedRef.current = true;
    widgetIdRef.current = window.grecaptcha.render(containerRef.current, {
      sitekey: siteKey,
      callback: onVerify,
      "expired-callback": onExpire,
      "error-callback": onError,
    });
  }, [siteKey, onVerify, onExpire, onError]);

  useEffect(() => {
    // If the script is already loaded, render immediately
    if (window.grecaptcha) {
      renderWidget();
      return;
    }

    // Set the global callback for when the script loads
    window.onRecaptchaLoad = renderWidget;

    // Check if script tag already exists
    const existing = document.querySelector(
      'script[src*="recaptcha/api.js"]'
    );
    if (!existing) {
      const script = document.createElement("script");
      script.src =
        "https://www.google.com/recaptcha/api.js?onload=onRecaptchaLoad&render=explicit";
      script.async = true;
      script.defer = true;
      document.head.appendChild(script);
    }

    return () => {
      window.onRecaptchaLoad = undefined;
    };
  }, [renderWidget]);

  if (!siteKey) {
    return (
      <div style={{ padding: "14px 16px", background: "#f9fafb", border: "1px solid var(--color-border)", borderRadius: 8, fontSize: "0.85rem", color: "var(--color-text-muted)" }}>
        reCAPTCHA non configuré (NEXT_PUBLIC_RECAPTCHA_SITE_KEY manquant)
      </div>
    );
  }

  return <div ref={containerRef} />;
}
