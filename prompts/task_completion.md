Follow the instructions below strictly whenever you need to complete a new task:

Step 1: Read README.md and README-SERVERLESS.md to understand the project and the serverless architecture.

Step 2: Ready documents in ./docs folder to understand the learnings and best practices that have been documented by people who have worked on the project before both on development, testing, and deployment so you understand the potential issues and solutions, as well as best practices. 

Step 3: Go on to work on the task. Whenever you need to add new code, make sure you check the ./docs/CODEBASE_STRUCTURE.md first to understand the codebase structure and determine the best place to add the new code before adding it. When you add new codes, follow the guidelines below:

1. **Plan your implementation strategy**  
   Decide where the code for Task 1.7 should live:
   - Given the existing folder structure, which folder should it go into? Is this folder existing or need to be created?
   - Within that folder, should it go into a new standalone file or should it extend an existing module?
   Pick the approach that best fits the current architecture.
   - If you need to create a new folder or a new file, make sure you ask for approval first.

2. **Outline key functionality**  
   Sketch out the main components and create boilerplate code that clearly defines the interfaces.

3. **Write test cases**  
   Use the TDD approach—write robust tests that reflect the expected behavior before fully implementing the logic.

4. **Implement and validate**  
   Complete the code and run your test cases to ensure everything functions as intended.

8. **Review and refine**  
   Do a final pass to optimize your code—look for simplification opportunities or performance improvements.

---

## Additional Guidelines

- **Keep it clean and simple**: Prioritize readability and maintainability.
- **Don’t over-engineer**: Avoid complex logic or unnecessary features unless absolutely necessary.
- **Remember**: This is just an MVP—build only what’s needed.
- **Use latest stable versions**: When no specific version is mentioned, choose the most recent stable release of libraries and tools.