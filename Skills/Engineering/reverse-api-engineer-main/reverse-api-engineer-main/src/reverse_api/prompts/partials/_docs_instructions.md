**Generate an OpenAPI 3.0 specification** documenting the API endpoints found in the traffic. Guidelines — use your judgment:

- Use OpenAPI 3.0.0 format
- Include all discovered endpoints with methods, parameters, request/response schemas, and auth schemes
- Organize endpoints into logical tags/groups
- Infer meaningful descriptions for endpoints, parameters, and response fields
- Use JSON Schema `$ref` for shared components
- Add a `servers` array with the base URL from the HAR

**Enhance with inference:**
- Identify required vs optional params, add example values from captured requests
- Document error responses and rate limiting headers if observed
- Describe multi-step auth flows if present

**Supplementary docs:**
- Generate a README.md covering: API overview, auth method, base URL, common use cases, rate limiting, special headers

Save the OpenAPI spec to: `{scripts_dir}/openapi.json`
Save the README to: `{scripts_dir}/README.md`
Optionally create: `{scripts_dir}/examples.md` with curl examples