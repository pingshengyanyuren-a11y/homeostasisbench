# GitHub Bootstrap

Current machine-side setup status:

- SSH authentication to GitHub works
- `gh` CLI is installed
- local Git identity is configured

Remaining one-time step:

```powershell
gh auth login --git-protocol ssh --web
```

After that, the repository can be published with:

```powershell
.\scripts\publish_homeostasisbench.ps1
```

Default behavior:

- creates `homeostasisbench` as a public GitHub repo
- attaches local repo as `origin`
- commits current changes if needed
- pushes the current branch
- adds baseline benchmark topics
