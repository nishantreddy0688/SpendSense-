import type { Config } from "tailwindcss";
const config: Config = { content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"], theme: { extend: { colors: { ink: "#192c25", muted: "#78847e", canvas: "#f6f8f6", mint: "#e8f5ed", forest: "#218452" }, fontFamily: { sans: ["Arial", "sans-serif"] }, boxShadow: { card: "0 2px 12px rgba(29,55,41,.045)" } } }, plugins: [] };
export default config;
