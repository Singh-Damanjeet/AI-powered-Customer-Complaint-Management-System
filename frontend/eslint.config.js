import eslint from '@eslint/js'
import react from 'eslint-plugin-react'
import globals from 'globals'

export default [
  {
    ignores: ['dist/**', 'node_modules/**'],
  },
  eslint.configs.recommended,
  {
    files: ['**/*.{js,jsx}'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      parserOptions: {
        ecmaFeatures: { jsx: true },
      },
      globals: {
        ...globals.browser,
        ...globals.node,
        ...globals.vitest,
      },
    },
    plugins: {
      react,
    },
    settings: {
      react: { version: 'detect' },
    },
    rules: {
      'react/jsx-uses-vars': 'error',
      'no-unused-vars': [
        'error',
        { args: 'none', varsIgnorePattern: '^_' },
      ],
    },
  },
]
