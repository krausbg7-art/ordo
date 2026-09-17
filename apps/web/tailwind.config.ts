import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        cream: "#F4F1EA",
        sand: "#EAE5DA",
        stone: "#6B665D",
        ink: "#1C1B19",
        gold: "#A8844E",
      },
      fontFamily: {
        serif: ["'Cormorant Garamond'", "serif"],
        sans: ["'Manrope'", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
