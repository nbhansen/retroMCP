# Development Partnership - Python SOLID and CLEAN code

We're building production-quality code together. Your role is to create maintainable, efficient solutions while catching potential issues early.

When you seem stuck or overly complex, I'll redirect you - my guidance helps you stay on track.

🚨 **AUTOMATED CHECKS ARE MANDATORY**
ALL hook issues are BLOCKING - EVERYTHING must be ✅ GREEN!
No errors. No formatting issues. No linting problems. Zero tolerance.
These are not suggestions. Fix ALL issues before continuing.

**Required Tools - BOTH Must Pass:**
- 🐍 **Python**: `ruff check` + `ruff format --check` (backend)
- something similar for any frontend or stuff we build

ALL issues are BLOCKING - same zero tolerance policy.

## CRITICAL WORKFLOW - ALWAYS FOLLOW THIS!
Research → Plan → Implement
NEVER JUMP STRAIGHT TO CODING! Always follow this sequence:

- **Research**: Explore the codebase, understand existing patterns
- **Plan**: Create a detailed implementation plan and verify it with me  
- **Implement**: Execute the plan with validation checkpoints

When asked to implement any feature, you'll first say: "Let me research the codebase and create a plan before implementing."

For complex architectural decisions or challenging problems, use "ultrathink" to engage maximum reasoning capacity.

## USE MULTIPLE AGENTS!
Leverage subagents aggressively for better results:
- Spawn agents to explore different parts of the codebase in parallel
- Use one agent to write tests while another implements features
- Delegate research tasks
- For complex refactors: One agent identifies changes, another implements them

## Reality Checkpoints
Stop and validate at these moments:
- After implementing a complete feature
- Before starting a new major component
- When something feels wrong
- Before declaring "done"

🚨 **CRITICAL: Hook Failures Are BLOCKING**
When hooks report ANY issues, you MUST:
1. **STOP IMMEDIATELY** - Do not continue with other tasks
2. **FIX ALL ISSUES** - Address every ❌ issue until everything is ✅ GREEN
3. **VERIFY THE FIX** - Re-run the failed command to confirm it's fixed
4. **CONTINUE ORIGINAL TASK** - Return to what you were doing before the interrupt

### FORBIDDEN - NEVER DO THESE:
- NO keeping old and new code together
- NO migration functions or compatibility layers

### Required Standards:
- Delete old code when replacing it
- Type hints on all functions and methods
- Meaningful names: `user_id` not `id`

## Implementation Standards
Our code is complete when:
- All linters pass
- All tests pass
- Feature works end-to-end
- Old code is deleted
- Docstrings on all public functions/classes

## Testing Strategy - Test-Driven Development (TDD)
**WE USE COMPREHENSIVE TDD WITH CONTRACT TESTING:**

- **Write tests FIRST, implementation SECOND** - Always start with failing tests
- **Test Pyramid**: Unit → Integration → Contract → End-to-End
- **Coverage Requirement**: 80% minimum (currently 81% achieved)
- **Contract Testing**: Every test validates CLAUDE.md compliance (immutability, DI, type safety)
- **MCP Protocol Testing**: All responses must follow MCP TextContent standards
- **Real-time Validation**: Architecture principles enforced during test execution

**TDD Workflow:**
1. **Red**: Write failing test that captures requirement
2. **Green**: Write minimal code to make test pass
3. **Refactor**: Clean up while keeping tests green
4. **Contract**: Verify CLAUDE.md compliance is maintained

**Test Categories We Maintain:**
- **Unit Tests**: Domain logic, use cases, repositories (isolated with mocks)
- **Integration Tests**: End-to-end workflows, SSH error handling, tool execution
- **Contract Tests**: Architecture compliance, MCP protocol adherence
- **Fixtures**: Comprehensive mocking infrastructure for all external dependencies

**BEFORE WRITING ANY CODE:**
1. Write the test that describes expected behavior
2. Check if it follows hexagonal architecture
3. Verify no global state is created
4. Ensure all dependencies are injected
5. Confirm domain logic is separated from infrastructure
6. Validate all objects are immutable
7. Run tests to confirm they fail initially (Red)
8. Implement minimal code to pass (Green)
9. Refactor while maintaining test coverage (Refactor)

## Problem-Solving Together
When you're stuck:
1. **Stop** - Don't spiral into complex solutions
2. **Delegate** - Consider spawning agents
3. **Ultrathink** - For complex problems
4. **Step back** - Re-read requirements
5. **Simplify** - The simple solution is usually correct
6. **Ask** - Present clear alternatives


## Communication Protocol
Progress Updates:
- ✓ Implemented authentication (all tests passing)
- ✗ Found issue with token validation - investigating

## Working Together
This is always a feature branch - no backwards compatibility needed.
When in doubt, we choose clarity over cleverness.

**REMINDER: If this file hasn't been referenced in 30+ minutes, RE-READ IT!**

