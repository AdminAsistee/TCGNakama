/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: "class",
    content: [
        "C:/Users/amrca/Documents/antigravity/tcgnakama/app/templates/**/*.html",
        "C:/Users/amrca/Documents/antigravity/tcgnakama/app/static/**/*.js",
    ],
    theme: {
        extend: {
            colors: {
                "primary": "#FFD700",
                "primary-dark": "#B8960F",
                "background-dark": "#0B1120",
                "surface": "#111827",
                "surface-light": "#1F2937",
                "vault-card": "#111827",
                "vault-border": "#1F2937",
                "neon-red": "#EF4444",
                "neon-green": "#22C55E",
                "accent-blue": "#3B82F6"
            },
            fontFamily: {
                "display": ["Space Grotesk", "sans-serif"]
            },
            borderRadius: {
                "DEFAULT": "0.5rem",
                "lg": "1rem",
                "xl": "1.5rem",
                "full": "9999px"
            },
        },
    },
    plugins: [],
}
