import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        skywash: "#eaf6ff",
        newsroom: "#0b6ea8",
        ink: "#102235",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        serif: ["Georgia", "Times New Roman", "serif"],
      },
      boxShadow: {
        news: "0 14px 36px rgba(11,110,168,0.14)",
      },
    },
  },
  plugins: [],
};

export default config;
