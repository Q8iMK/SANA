# Upstream Synchronization Guide

SANA maintains a clean Git relationship with the original upstream repository (`https://github.com/NousResearch/hermes-agent.git`) via the `upstream` remote.

---

## Branch Responsibilities

| Branch | Purpose |
|---|---|
| `upstream-baseline` | Pristine snapshot of upstream Hermes Agent |
| `main` | SANA distribution branch (upstream + SANA branding & features) |

---

## Exact Commands for Future Upstream Updates

Never use `git reset --hard` on `main`. Always merge or rebase cleanly and re-run SANA's idempotent branding tool:

```bash
# 1. Fetch latest upstream commits
git fetch upstream

# 2. Create an integration branch from main
git checkout -b sync/upstream-$(date +%Y%m%d) main

# 3. Merge upstream/main (preserving SANA history)
git merge upstream/main

# 4. Resolve any merge conflicts, then re-apply SANA branding idempotently
python branding/scripts/apply_branding.py

# 5. Verify branding and run tests
python branding/scripts/apply_branding.py --check
python -m pytest branding/tests/ -v

# 6. Merge back to main when green
git checkout main
git merge --no-ff sync/upstream-$(date +%Y%m%d)
```
