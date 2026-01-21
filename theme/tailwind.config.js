/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
      "./templates/**/*.html",  // Detecta clases en plantillas Django
      "./static/**/*.js",       // Archivos JavaScript en static/
      ".static_src/**/*.css",   // Asegura que detecte los estilos propios
      "./**/*.py"               // Opcional: Detectar en archivos Python (Django)
    ],
    theme: {
      extend: {},
    },
    plugins: [],
  };