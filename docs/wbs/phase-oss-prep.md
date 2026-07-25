# Phase OSS: Open Source Preparation

> **Tasks:** 10 · **Effort:** 12h (1.5 days)  
> **Dependencies:** Phase 0 (scaffolding must exist), runs alongside all phases

---

### OSS-01: Complete GitHub Community Profile (#360)
**Effort:** 1h
**Checklist:**
- [ ] Verify all items green on community profile page
- [ ] Create SUPPORT.md (how to get help, report issues, request features)
- [ ] Create pull_request_template.md in .github/
- [ ] Enable GitHub Discussions for Q&A and community
- [ ] Add repo topics: mcp, agent, governance, tool-mesh, platform, ai
- [ ] Add repo description
- [ ] Verify repo has a website URL (if applicable)
**Success Criteria:** GitHub Community Profile shows 100% complete. SUPPORT.md present. Discussions tab visible.

### OSS-02: README Overhaul with Badges and Quick Start (#361)
**Effort:** 1.5h
**Checklist:**
- [ ] Add CI status, coverage, license, Python version, Docker, PyPI badges
- [ ] Add OpenSSF Best Practices passing badge
- [ ] Rewrite Quick Start: 5-curl commands from zero to first request
- [ ] Add Architecture, Features, Contributing, License sections
- [ ] Fix any broken links
**Success Criteria:** Badges render correctly. Quick Start works in <10 min. No broken links.

### OSS-03: OpenSSF Best Practices Badge (#362)
**Effort:** 2h
**Checklist:**
- [ ] Register at bestpractices.coreinfrastructure.org
- [ ] Answer all passing-level criteria
- [ ] Add badge to README
- [ ] Fix gaps identified by checklist
**Success Criteria:** Passing badge achieved and linked in README.

### OSS-04: Contributing Guide Enhancement (#363)
**Effort:** 1h
**Checklist:**
- [ ] Add step-by-step local setup, commit conventions, branch naming
- [ ] Document PR lifecycle and code review expectations
- [ ] Add links to testing guide and release guide
- [ ] Add CI workflow diagram
**Success Criteria:** New contributor can set up and contribute from this guide alone.

### OSS-05: Governance and Maintainership Docs (#364)
**Effort:** 1.5h
**Checklist:**
- [ ] Create GOVERNANCE.md: scope, maintainer roles, lazy consensus
- [ ] Create MAINTAINERS.md: current maintainers
- [ ] Create ROADMAP.md: v0.1.0, v0.2.0, GA
- [ ] Define release cadence and semver policy
**Success Criteria:** Community docs standards complete. Roadmap visible.

### OSS-06: Release Automation and Publishing (#365)
**Effort:** 2h
**Checklist:**
- [ ] Create PYPI_TOKEN secret in GitHub repo
- [ ] Configure ghcr.io visibility to public
- [ ] Verify release workflow creates GitHub Release with changelog
- [ ] Verify PyPI publish and Docker push work
- [ ] Document in RELEASE.md
- [ ] E2E test on pre-release tag
**Success Criteria:** pip install + docker pull work post-release. Release page has changelog.

### OSS-07: Dependency Management and Security Scanning (#366)
**Effort:** 1h
**Checklist:**
- [ ] Verify Dependabot weekly schedule with grouped PRs
- [ ] Add Dependabot auto-merge for patch updates (CI-gated)
- [ ] Configure pip-audit and npm audit in CI
- [ ] Add OpenSSF Scorecard GitHub Action + badge
**Success Criteria:** Dependabot opens grouped PRs. CI fails on high/critical vulns. Scorecard badge on README.

### OSS-08: Documentation Site and API Reference (#367)
**Effort:** 2h
**Checklist:**
- [ ] Choose docs platform (MkDocs, Docusaurus, or GitHub Pages)
- [ ] Scaffold config with: Getting Started, User Guide, API Reference, Admin Guide, Deployment, FAQ
- [ ] Auto-deploy via GitHub Pages on push to main
- [ ] Auto-export OpenAPI spec to docs
- [ ] Add docs status badge to README
**Success Criteria:** Docs site deployed. API reference auto-generated from OpenAPI.

### OSS-09: Community Health Files and Automation (#368)
**Effort:** 1h
**Checklist:**
- [ ] Verify CODE_OF_CONDUCT.md (Contributor Covenant 2.1)
- [ ] Verify CODEOWNERS auto-requests reviewers
- [ ] Add Stale bot config (90d stale, 120d close)
- [ ] Create FUNDING.yml if applicable
- [ ] Create issue label automation
- [ ] Add welcome message for first-time contributors
**Success Criteria:** Stale issues auto-closed. CODEOWNERS functions. All health files validated.

### OSS-10: Release Notes and Changelog Process (#369)
**Effort:** 0.5h
**Checklist:**
- [ ] Verify CHANGELOG.md follows Keep a Changelog
- [ ] Add link to CHANGELOG in README
- [ ] Add Release Drafter workflow (auto-draft from PR labels)
- [ ] Define changelog per-PR process
- [ ] Update CHANGELOG for v0.1.0
**Success Criteria:** Release Drafter auto-generates notes. Changelog up to date.
