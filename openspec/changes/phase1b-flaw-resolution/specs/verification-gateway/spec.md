## ADDED Requirements

### Requirement: Mandatory Gateway for All Tool Registration
All tool registration paths MUST go through the `VerificationGateway` class. Direct calls to `ToolRegistry.register()` from evolution modules SHALL be prohibited.

#### Scenario: Synthesizer uses gateway for registration
- **WHEN** the synthesizer creates a new tool
- **THEN** registration is performed via `VerificationGateway.submit()` not direct registry access

#### Scenario: Refiner uses gateway for registration
- **WHEN** the refiner patches and re-registers a tool
- **THEN** registration is performed via `VerificationGateway.submit()` not direct registry access

#### Scenario: Direct registry access from evolution modules fails
- **WHEN** code attempts to call `registry.register()` from synthesizer or refiner modules
- **THEN** the code review/linting process flags this as a violation

### Requirement: Gateway Enforces Verification Before Registration
The `VerificationGateway.submit()` method MUST run all verification stages before allowing registration.

#### Scenario: Verification failure blocks registration
- **WHEN** a tool fails any verification stage
- **THEN** registration is blocked and `VerificationError` is raised with the failure report

#### Scenario: Verification success allows registration
- **WHEN** a tool passes all verification stages
- **THEN** registration proceeds and the tool artifact is returned

### Requirement: Gateway Provides Rollback Capability
The gateway MUST create rollback checkpoints for all tool mutations.

#### Scenario: Checkpoint created before registration
- **WHEN** `VerificationGateway.submit()` is called
- **THEN** a rollback checkpoint is created before any mutation occurs

#### Scenario: Rollback restores previous state
- **WHEN** rollback is triggered after a failed registration
- **THEN** the registry state is restored to the pre-mutation checkpoint

### Requirement: Gateway Logs All Registration Attempts
Every registration attempt through the gateway MUST be logged with full context.

#### Scenario: Successful registration is logged
- **WHEN** a tool is successfully registered via gateway
- **THEN** a log entry records: timestamp, tool name, category, verification stages passed

#### Scenario: Failed registration is logged
- **WHEN** a tool fails registration via gateway
- **THEN** a log entry records: timestamp, tool name, category, failure stage, error details
