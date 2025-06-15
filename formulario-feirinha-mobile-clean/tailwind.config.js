// tailwind.config.js (dentro de formulario-feirinha-mobile-clean/)
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    // Esta linha é para escanear seu HTML principal (index.html)
    "./index.html",
    // Esta linha é CRUCIAL para o Tailwind escanear todos os seus componentes React na pasta `src/`
    // Ele vai procurar por classes Tailwind em todos os arquivos .js, .ts, .jsx e .tsx dentro de src/
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}

