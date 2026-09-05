# Root cause tracing

A bug often surfaces far from where it starts: a repository initialised in the wrong directory, a
file written to the wrong location, a database opened on the wrong path. The instinct is to fix the
line that raised the error, but that line is usually a symptom. Trace backwards through the call
chain to the original trigger and fix it there.

## When this applies

- The error happens deep in execution rather than at an entry point.
- The stack trace shows a long call chain.
- It is unclear where an invalid value came from.
- You need to find which test or code path triggers the problem.

If the chain runs into a dead end — the caller is outside your control, or the value arrives from a
system you cannot inspect — fix at the symptom point and say that is what you did, and why.

## The tracing process

1. **Observe the symptom.** Take the error exactly as reported.

   ```
   Error: git init failed in ~/project/packages/core
   ```

2. **Find the immediate cause.** Which line directly performs the failing operation?

   ```typescript
   await execFileAsync('git', ['init'], { cwd: projectDir });
   ```

3. **Ask what called it.** Walk one level up at a time and write the chain down.

   ```
   WorktreeManager.createSessionWorktree(projectDir, sessionId)
     ← Session.initializeWorkspace()
     ← Session.create()
     ← the test, at Project.create()
   ```

4. **Follow the value, not just the frames.** At each level, ask what was passed.

   - `projectDir` is `''`, an empty string.
   - An empty `cwd` resolves to `process.cwd()`.
   - That is the source directory, which is where the damage landed.

5. **Find the original trigger.** Keep going until a level produces the bad value rather than
   passing it on.

   ```typescript
   const context = setupCoreTest(); // returns { tempDir: '' }
   Project.create('name', context.tempDir); // read before beforeEach ran
   ```

## When you cannot trace by reading

Add instrumentation before the operation that fails, not after it has failed, and include enough
context to identify the caller.

```typescript
async function gitInit(directory: string) {
  const stack = new Error().stack;
  console.error('DEBUG git init:', {
    directory,
    cwd: process.cwd(),
    nodeEnv: process.env.NODE_ENV,
    stack,
  });

  await execFileAsync('git', ['init'], { cwd: directory });
}
```

Use `console.error` inside tests, because a project logger may be suppressed there. Then run the
suite and read only the lines you added:

```bash
npm test 2>&1 | grep 'DEBUG git init'
```

Read the captured traces for the test file name, the line that triggers the call, and the pattern
across occurrences — the same test each time, or the same parameter value.

When something appears during a test run and you do not know which test produced it, bisect: run
the tests in halves, or one file at a time, until the first run that reproduces the artefact names
the culprit.

## Worked example: the empty project directory

**Symptom.** A `.git` directory appears inside the package source tree.

**Trace chain.**

1. `git init` ran in `process.cwd()`, because its `cwd` parameter was empty.
2. The worktree manager was called with an empty project directory.
3. `Session.create()` had been passed an empty string.
4. The test read `context.tempDir` before `beforeEach` had assigned it.
5. `setupCoreTest()` returns `{ tempDir: '' }` until then.

**Root cause.** A top-level variable initialised from a value that is not populated yet.

**Fix at the source.** `tempDir` became a getter that throws when it is read too early.

**Validation added along the way.** Project creation rejects a directory it cannot verify, the
workspace manager rejects an empty path, a guard refuses to initialise a repository outside the
temporary directory during tests, and the call logs its stack first. Each layer turns the same
mistake into an immediate, readable failure instead of a silent one.

## What to hold on to

Trace one level up for as long as the level above still hands the bad value on. Fix where the value
is produced, then add a check at each layer it passed through, so the same mistake cannot travel
that far again. Fixing only the line that raised the error leaves the trigger in place.
