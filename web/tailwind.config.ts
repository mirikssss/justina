import type { Config } from "tailwindcss";

// Тема ссылается на CSS-переменные из components/mygov/tokens.css — менять цвета только там.
const config: Config = {
  corePlugins: { preflight: false }, // базовые стили задаёт mygov.css (как в макете)
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./features/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        surface: "var(--surface)",
        "surface-2": "var(--surface-2)",
        border: "var(--border)",
        fg: "var(--fg)",
        muted: "var(--muted)",
        accent: "var(--accent)",
        blue: "var(--blue)",
        teal: "var(--teal)",
        faint: "var(--faint)",
        good: "var(--good)",
        "good-bg": "var(--good-bg)",
        warn: "var(--warn)",
        "warn-bg": "var(--warn-bg)",
        crit: "var(--crit)",
        "crit-bg": "var(--crit-bg)",
        "info-bg": "var(--info-bg)",
      },
      borderRadius: { card: "var(--radius-card)", ctl: "var(--radius-ctl)" },
      boxShadow: { card: "var(--shadow)" },
      fontFamily: { sans: "var(--ff)" },
    },
  },
};

export default config;
