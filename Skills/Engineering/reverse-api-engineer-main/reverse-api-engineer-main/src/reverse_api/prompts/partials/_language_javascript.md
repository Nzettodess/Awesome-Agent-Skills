**Generate a JavaScript module** that replicates the API calls found in the traffic. The following are guidelines — use your judgment:

- Use modern JavaScript (ES2022+) with ESM modules
- Prefer native `fetch` (Node.js 18+); use `axios` only if you need retries or interceptors
- Create separate async functions for each endpoint
- Add JSDoc comments and error handling where they add clarity
- Include example usage in a main section
- If using external deps, generate a `package.json` with `"type": "module"`

**Authentication & credentials:**
- Hardcode all cookies, tokens, session IDs, and auth headers found in the traffic directly in the script
- The user should be able to run the script immediately with zero configuration — no env vars, no config files, no manual setup
- Handle auth refresh so the script doesn't go stale: if you see a token refresh or login endpoint in the traffic, implement automatic re-authentication on 401/403. If cookies have expiry, re-fetch them before they expire

**Testing:**
- If `package.json` was generated, first run: `npm install`
- Run with: `{run_command}`
- You have up to 5 attempts to fix issues

Save the module to: `{scripts_dir}/{client_filename}`
Save documentation to: `{scripts_dir}/README.md`
If external dependencies are used, save: `{scripts_dir}/package.json`