/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#0B1120",
        surface: "#0d1526",
        card: "#111827",
        cardhover: "#151f31",
        border: "rgba(255,255,255,0.08)",
        primary: {
          DEFAULT: "#3B82F6",
          hover: "#2563EB",
          soft: "rgba(59,130,246,0.14)",
        },
        success: {
          DEFAULT: "#10B981",
          soft: "rgba(16,185,129,0.14)",
        },
        warning: {
          DEFAULT: "#F59E0B",
          soft: "rgba(245,158,11,0.14)",
        },
        danger: {
          DEFAULT: "#EF4444",
          soft: "rgba(239,68,68,0.14)",
        },
        muted: "#94A3B8",
        foreground: "#F8FAFC",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      borderRadius: {
        xl: "0.9rem",
        "2xl": "1.1rem",
      },
      keyframes: {
        "fade-in": {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        "slide-up": {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "scale-in": {
          from: { opacity: "0", transform: "scale(0.96)" },
          to: { opacity: "1", transform: "scale(1)" },
        },
      },
      animation: {
        "fade-in": "fade-in 0.2s ease-out",
        "slide-up": "slide-up 0.25s ease-out",
        "scale-in": "scale-in 0.18s ease-out",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
