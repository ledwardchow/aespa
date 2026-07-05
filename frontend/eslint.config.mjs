import pluginReact from "eslint-plugin-react";
import babelParser from "@babel/eslint-parser";
export default [
  {
    files: ["**/*.{js,jsx,mjs,cjs,ts,tsx}"],
    languageOptions: {
      parser: babelParser,
      parserOptions: {
        requireConfigFile: false,
        babelOptions: {
          babelrc: false,
          configFile: false,
          presets: ["@babel/preset-react"]
        },
        ecmaFeatures: {
          jsx: true
        }
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
