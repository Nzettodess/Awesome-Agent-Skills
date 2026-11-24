Here is the HAR file path you need to analyze:
<har_path>
{har_path}
</har_path>

Here is the original user prompt with context about what they're trying to accomplish:
<user_prompt>
{prompt}
</user_prompt>

Here is the output directory where you should save your generated files:
<output_dir>
{scripts_dir}
</output_dir>
{existing_client_guidance}
{additional_instructions}
## Run Context

- Mode: {tag_mode_label}
- Target run: {run_id}
- HAR location: {har_parent}
- Existing {existing_label}: {scripts_dir}
- Message history: {messages_path} (available for reference if needed)
- Fresh mode: {is_fresh}

By default, treat this as an iterative refinement. The user's prompt describes
changes or improvements to make to the existing {existing_artifact}. If fresh mode is enabled,
ignore previous implementation and start from scratch.

Note: Full message history is available at the messages path above if you need
to understand previous context, but it is not automatically loaded into this
conversation.