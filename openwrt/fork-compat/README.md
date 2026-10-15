# E5 internal-install compatibility

The pinned upstream device repositories own the shared runtime. This small
overlay retains the fork's independently reviewed internal-partition changes:

- `e5-gpt`: the `e5root` allocation, write-plan and recovery interfaces used by
  the fork's internal installer, alongside the current upstream GPT changes.
- `e5-next-boot`: transactional intent/boot-control writes and serialization.
- `e5-boot-ok`: acknowledge the completed internal-partition trial.
- `vendor-start.sh`: expose the verified physical internal storage aliases.

These are three-way merges of the common ancestor, the previous fork runtime
and the newly pinned shared runtime. `tools/stage-e5-compat.py` supplies the
startup sources **before** upstream isolated-NV staging; it does not overwrite
the already transformed vendor startup afterwards. All other device features
continue to come from the pinned upstream submodules.

The release audit independently reproduces this staging. The original runtime
and pre-sync firmware remain available in the repository history and Releases.
