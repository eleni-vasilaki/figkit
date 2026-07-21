# Scientific Coding Principles

Scientific code is part of the scientific argument. It makes the method **visible and
auditable to another scientist**.

---

1. **Clarity is the first optimization target.**
   Write code you can read and check line by line. Add complexity only when it makes
   the logic clearer, reduces errors, or improves auditability. Have good README files and code comemnts.

2. **Keep the experiment visible.**
   Put the choices that define the experiment near the top of the script: data, model
   size, repetitions, learning rate, noise, stopping rule, device, metrics.

3. **Separate the scientific steps.**
   Give data loading, preprocessing, model definition, parameter counting, training,
   evaluation, statistics, plotting, and export their own visible sections.

4. **Use simple abstractions.**
   Write functions for transformations. Use a class for a thing with real state: a
   network, a simulator, a fitted model.

5. **Name the scientific quantity.**
   Let each name state what it measures: `validation_mse`, `noise_fraction`,
   `repeat_index`.

6. **Preserve individual observations.**
   Save the per-run, per-condition data, and derive every summary from that saved
   table. Trained models are observations too: save them as weights + config, with a
   parseable name (task, shape, size, run) and the split that trained them.

7. **Prefer human-readable outputs.**
   Write logs, config, and formulas as plain text, and numeric tables as TSV. Reserve
   binary formats for a real technical need.

8. **Save the audit trail.**
   With each run, record its configuration, formulas, environment, warnings, and
   failures — enough to reconstruct what ran.

9. **Treat randomness scientifically.**
   Fix seeds for debugging but otherwise do *not* use a seed. Instead, support each 
   conclusion with enough independent repetitions to be **statistically stable**, 
   not identical. Fixing seeds for reproducability (only if needed) should
   happen at the end, and then several seeds are needed.

10. **Checkpoint long runs.**
    Write intermediate results to disk as the run proceeds, so a crash or timeout
    leaves the experiment recoverable.

11. **Justify every dependency.**
    Add a library when it earns its place. Use the standard library for simple tasks.

12. **Keep one shared copy of every piece of code.**
    A single source keeps bugs fixable and records which version produced which
    result. Do not copy variables, calculate them based on your data 
	(Generic, beyond scientific coding.)
