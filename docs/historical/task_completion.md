# Task Completion Instructions

**MANDATORY**: Follow these instructions strictly for every new task. Complete each step in order before proceeding to the next.

---

## Phase 1: Project Understanding (REQUIRED BEFORE CODING)

### Step 1: Read Project Documentation
- **MUST READ**: `README-SERVERLESS.md`
- **PURPOSE**: Understand the project scope and serverless architecture
- **COMPLETION CRITERIA**: You can explain the project's purpose and architecture

### Step 2: Study Best Practices Documentation
- **MUST READ**: All documents in the `./docs` folder
- **PURPOSE**: Learn from previous developers' experiences, including:
  - Development best practices
  - Testing strategies
  - Deployment procedures
  - Known issues and solutions
- **COMPLETION CRITERIA**: You understand the documented patterns and potential pitfalls

### Step 3: Review Codebase Structure
- **MUST READ**: `./docs/CODEBASE_STRUCTURE.md`
- **PURPOSE**: Understand where different types of code belong
- **COMPLETION CRITERIA**: You know exactly where to place new code

---

## Phase 2: Implementation (FOLLOW THIS EXACT ORDER)

### Step 4: Plan Implementation Strategy
**BEFORE writing any code, answer these questions:**

1. **Location Decision**:
   - Which existing folder should contain this code?
   - If no suitable folder exists, what new folder is needed?
   - Should this be a new file or extend an existing module?

2. **Architecture Alignment**:
   - How does this fit with the current codebase structure?
   - What dependencies will this introduce?

3. **Approval Requirement**:
   - **MANDATORY**: If creating new folders or files, request approval FIRST
   - **MANDATORY**: If unsure about placement, ask for guidance FIRST

### Step 5: Design Interfaces
- **ACTION**: Create boilerplate code with clear function/class signatures
- **INCLUDE**: Input parameters, return types, and main responsibilities
- **PURPOSE**: Define the contract before implementation

### Step 6: Write Tests First (TDD Approach)
- **ACTION**: Write comprehensive test cases BEFORE implementing logic
- **REQUIREMENTS**:
  - Test happy path scenarios
  - Test edge cases and error conditions
  - Test integration points
- **COMPLETION CRITERIA**: Tests fail appropriately (since logic isn't implemented yet)

### Step 7: Implement Core Logic
- **ACTION**: Write the minimum code needed to make tests pass
- **FOCUS**: Functionality first, optimization later
- **VALIDATION**: Run tests continuously during development

### Step 8: Final Review and Refinement
- **CHECKLIST**:
  - [ ] All tests pass
  - [ ] Code follows project conventions
  - [ ] No unnecessary complexity
  - [ ] Performance is acceptable
  - [ ] Documentation is clear

---

## Mandatory Guidelines

### Code Quality Standards
- **Simplicity**: Write the simplest solution that works
- **Readability**: Code should be self-documenting
- **Maintainability**: Future developers should easily understand and modify your code

### Project Constraints
- **MVP Focus**: Build only what's explicitly required
- **No Over-Engineering**: Avoid complex patterns unless absolutely necessary
- **Latest Stable Versions**: Use current stable releases unless specified otherwise

### Communication Requirements
- **Ask Before Creating**: Always request approval for new files/folders
- **Clarify Uncertainties**: Ask questions rather than making assumptions
- **Document Decisions**: Explain non-obvious implementation choices

---

## Success Criteria

Your task is complete when:
1. ✅ All tests pass
2. ✅ Code follows established patterns
3. ✅ Documentation is updated (if applicable)
4. ✅ No breaking changes to existing functionality
5. ✅ Code review checklist is satisfied