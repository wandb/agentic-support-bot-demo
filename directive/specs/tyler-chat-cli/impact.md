# Impact Analysis — Tyler Chat CLI Integration

## Modules/packages likely touched
- **New files**:
  - `support-bot.yaml` or `tyler-config.yaml` - Configuration file for tyler chat CLI
  
- **Modified files**:
  - `README.md` - Update instructions to use `tyler chat --config` instead of `python main.py`
  - `tools.py` - May need minor adjustments to ensure compatibility with tyler chat's tool loading mechanism
  - `.env.example` - Ensure it documents all required environment variables

- **Unchanged (kept as reference)**:
  - `main.py` - Kept as alternative/example implementation
  - `pyproject.toml` - Already has slide-tyler dependency

## Contracts to update (APIs, events, schemas, migrations)
- **Configuration contract**: 
  - New YAML configuration schema defining agent behavior
  - Must follow tyler chat's expected format (name, model_name, purpose, tools, temperature, etc.)
  
- **Tool loading mechanism**:
  - Tools must be loadable by tyler chat CLI
  - Current `get_tools()` function returns Tyler-format tool definitions
  - Need to verify tyler chat can load tools from custom Python files (e.g., `"./tools.py"`)

- **Environment variables**:
  - No changes to required env vars (WANDB_API_KEY, OPENAI_API_KEY)
  - tyler chat should respect these when initialized

- **No API/event/schema changes**: This is a CLI interface change, not a programmatic API change

## Risks

### Security:
- **Low risk**: No new security concerns
- tyler chat runs locally with same permissions as current Python script
- Tools still use stub implementations with no external system access
- Environment variables remain the only secret storage mechanism

### Performance/Availability:
- **Low risk**: No performance impact
- tyler chat uses the same Tyler agent internals as current implementation
- Interactive CLI may feel more responsive due to streaming built into tyler chat
- No availability concerns (runs locally)

### Data integrity:
- **Low risk**: No data persistence or integrity concerns
- In-session conversation context only (no ThreadStore for MVP)
- Mock data returned by tools remains unchanged
- No database or external system integration

### Compatibility:
- **Medium risk**: tyler chat tool loading mechanism needs validation
  - **Mitigation**: Test that tyler chat can load custom tools from `./tools.py`
  - **Alternative**: If file path doesn't work, may need to register tools differently or use tyler init scaffolding approach
  
- **Low risk**: Configuration format may evolve with tyler updates
  - **Mitigation**: Pin slide-tyler version in pyproject.toml
  - Follow official tyler chat documentation for config schema

### User Experience:
- **Medium risk**: Users familiar with `python main.py` need to adapt to `tyler chat`
  - **Mitigation**: Clear README documentation with examples
  - Keep main.py available as reference
  
- **Low risk**: tyler chat may have different UI/UX than custom streaming implementation
  - **Impact**: Built-in tyler chat UI may differ from current streaming output format
  - **Mitigation**: Document the change, highlight benefits (better interactive experience)

## Observability needs

### Logs:
- **Existing**: Weave integration should continue working automatically
  - tyler chat uses Tyler Agent internally, which will trigger Weave instrumentation
  - Verify `weave.init()` is called before tyler chat starts (may need script wrapper or env var)
  
- **New consideration**: tyler chat startup/configuration errors
  - CLI will output errors to stderr/stdout
  - Developers should see clear error messages for config issues

### Metrics:
- **Existing**: Weave will continue tracking:
  - Token usage
  - Latency per interaction
  - Tool call success/failure
  - Model interactions
  
- **No new metrics needed**: Same agent behavior, just different invocation method

### Alerts:
- **None required**: Local development tool
- No production deployment or monitoring in this phase
- Developers will see errors interactively in the CLI

## Testing considerations

### What to test:
- Configuration file validity (YAML syntax, required fields)
- Tool loading from custom Python file
- Weave initialization with tyler chat
- Environment variable validation before agent starts

### What NOT to test:
- Interactive chat sessions (manual testing only)
- Real-time streaming output (handled by tyler chat)
- Multi-turn conversation flow (handled by tyler chat)

### CI implications:
- Current pytest tests for `get_tools()` function remain valid
- May add config file schema validation test
- No need to test interactive CLI sessions in CI

