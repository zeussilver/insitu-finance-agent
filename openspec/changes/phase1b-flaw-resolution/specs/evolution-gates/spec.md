## ADDED Requirements

### Requirement: Three-Tier Gate Classification
Evolution actions MUST be classified into three tiers: AUTO, CHECKPOINT, and APPROVAL.

#### Scenario: EvolutionGate enum defines three tiers
- **WHEN** code imports `from src.core.gates import EvolutionGate`
- **THEN** the enum contains `AUTO`, `CHECKPOINT`, and `APPROVAL` values

### Requirement: Gate Classification Rules
The gatekeeper MUST classify actions according to risk level.

#### Scenario: Read operations are AUTO tier
- **WHEN** an action reads cached data or executes read-only calculation
- **THEN** the gatekeeper classifies it as `EvolutionGate.AUTO`

#### Scenario: Tool creation is CHECKPOINT tier
- **WHEN** an action creates a new tool in any category
- **THEN** the gatekeeper classifies it as `EvolutionGate.CHECKPOINT`

#### Scenario: Tool modification is CHECKPOINT tier
- **WHEN** an action modifies an existing tool
- **THEN** the gatekeeper classifies it as `EvolutionGate.CHECKPOINT`

#### Scenario: Library persistence is APPROVAL tier
- **WHEN** an action persists a tool to the permanent library
- **THEN** the gatekeeper classifies it as `EvolutionGate.APPROVAL`

#### Scenario: Verification rule changes are APPROVAL tier
- **WHEN** an action modifies verification rules or constraints
- **THEN** the gatekeeper classifies it as `EvolutionGate.APPROVAL`

### Requirement: AUTO Tier Executes Immediately
Actions classified as AUTO MUST execute without blocking.

#### Scenario: AUTO tier has no delay
- **WHEN** an AUTO-tier action is submitted
- **THEN** it executes immediately without user interaction

### Requirement: CHECKPOINT Tier Creates Rollback Point
Actions classified as CHECKPOINT MUST create a rollback checkpoint before execution.

#### Scenario: CHECKPOINT creates state snapshot
- **WHEN** a CHECKPOINT-tier action is submitted
- **THEN** a rollback checkpoint is created before execution proceeds

#### Scenario: CHECKPOINT logs the action
- **WHEN** a CHECKPOINT-tier action executes
- **THEN** the action is logged with full context for audit trail

### Requirement: APPROVAL Tier Blocks Until Human Approval
Actions classified as APPROVAL MUST block until explicit human approval is received.

#### Scenario: APPROVAL tier prompts for approval
- **WHEN** an APPROVAL-tier action is submitted
- **THEN** execution blocks and the user is prompted for approval via CLI

#### Scenario: Approved action executes
- **WHEN** the user approves an APPROVAL-tier action
- **THEN** execution proceeds with checkpoint and logging

#### Scenario: Denied action is cancelled
- **WHEN** the user denies an APPROVAL-tier action
- **THEN** execution is cancelled and no mutation occurs

#### Scenario: Timeout cancels action
- **WHEN** no approval is received within the configured timeout
- **THEN** the action is cancelled by default

### Requirement: Development Mode Relaxes Gates
A development mode MUST exist that relaxes gate enforcement for rapid iteration.

#### Scenario: Dev mode auto-approves APPROVAL tier
- **WHEN** `EVOLUTION_GATE_MODE=dev` is set
- **THEN** APPROVAL-tier actions execute with only a warning, no blocking

#### Scenario: Production mode enforces strictly
- **WHEN** `EVOLUTION_GATE_MODE=prod` is set (or default)
- **THEN** all gate tiers are strictly enforced
