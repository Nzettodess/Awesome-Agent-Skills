**Generate a TypeScript module** that replicates the API calls found in the traffic. The following are guidelines — use your judgment:

- Use strict typing with interfaces for request/response types
- Use ESM modules and native `fetch` (Node.js 18+); use `axios` only if needed
- Create separate async functions for each endpoint
- Export a class-based API client with proper encapsulation
- Include example usage in a main section
- Generate a `package.json` with `"type": "module"`, `tsx`, `typescript`, `@types/node`

**Authentication & credentials:**
- Hardcode all cookies, tokens, session IDs, and auth headers found in the traffic directly in the script
- The user should be able to run the script immediately with zero configuration — no env vars, no config files, no manual setup
- Handle auth refresh so the script doesn't go stale: if you see a token refresh or login endpoint in the traffic, implement automatic re-authentication on 401/403. If cookies have expiry, re-fetch them before they expire

**Testing:**
- Run: `npm install && {run_command}`
- You have up to 5 attempts to fix issues

Save the module to: `{scripts_dir}/{client_filename}`
Save documentation to: `{scripts_dir}/README.md`
Save the package.json to: `{scripts_dir}/package.json`