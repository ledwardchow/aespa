import pluginReact from "eslint-plugin-react";

export default [
  {
    files: ["src/**/*.{js,jsx,mjs,cjs}"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      parserOptions: {
        ecmaFeatures: {
          jsx: true
        }
      },
      globals: {
        AbortController: "readonly",
        alert: "readonly",
        Blob: "readonly",
        cancelAnimationFrame: "readonly",
        clearInterval: "readonly",
        clearTimeout: "readonly",
        confirm: "readonly",
        console: "readonly",
        document: "readonly",
        EventSource: "readonly",
        fetch: "readonly",
        FileReader: "readonly",
        FormData: "readonly",
        localStorage: "readonly",
        navigator: "readonly",
        prompt: "readonly",
        requestAnimationFrame: "readonly",
        setInterval: "readonly",
        setTimeout: "readonly",
        TextDecoder: "readonly",
        URL: "readonly",
        window: "readonly"
      }
    },
    plugins: {
      react: pluginReact
    },
    rules: {
      "no-undef": "error",
      "react/jsx-no-undef": "error"
    }
  }
];
