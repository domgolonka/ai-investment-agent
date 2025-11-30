# Scripts Directory Audit for Public Repository

**Purpose**: Identify which scripts are useful for public users vs. which are personal/vestigial/dangerous

---

## ✅ KEEP - Useful for Public Users

### 1. **prompt_manager.py** ⭐ HIGH VALUE
- **Purpose**: CLI tool for managing agent prompts
- **Commands**: list, show, validate, export, compare
- **Why Keep**: Core functionality for customizing agent behavior
- **User Benefit**: Lets users modify prompts without touching code
- **Status**: Well-documented, safe, educational
```bash
poetry run python scripts/prompt_manager.py list
poetry run python scripts/prompt_manager.py show market_analyst
```

### 2. **run-analysis.sh** ⭐ HIGH VALUE
- **Purpose**: Convenient wrapper for analyzing single tickers
- **Why Keep**: Primary user interface for running analyses
- **User Benefit**: Easier than remembering Python module syntax
- **Needs**: Minor cleanup (remove Docker option if not shipping Docker)
```bash
./scripts/run-analysis.sh --ticker AAPL --quick
```

### 3. **run_tickers.sh** ⭐ MEDIUM VALUE
- **Purpose**: Batch analysis of multiple tickers from a file
- **Why Keep**: Useful for portfolio analysis
- **User Benefit**: Automates running multiple analyses
- **Note**: Contains macOS gRPC fix (GRPC_POLL_STRATEGY=poll) - keep this!
```bash
./scripts/run_tickers.sh  # reads from scratch/sample_tickers.txt
```

### 4. **check-environment.sh** ⭐ MEDIUM VALUE
- **Purpose**: Validates .env configuration
- **Why Keep**: Helps users troubleshoot setup
- **User Benefit**: Quick sanity check before running
- **Already Updated**: Uses GOOGLE_API_KEY (Gemini)
```bash
./scripts/check-environment.sh
```

---

## ⚠️ CONDITIONAL KEEP - Needs Heavy Documentation/Warning

### 5. **setup-github-secrets.sh**
- **Purpose**: Automates GitHub secrets setup for CI/CD
- **Risk Level**: Medium
- **Issues**: 
  - Requires GitHub CLI (`gh`) 
  - Only useful if deploying via GitHub Actions
  - Could confuse local-only users
- **Recommendation**: **KEEP but add big warning header**
- **Header Should Say**:
  ```bash
  # ⚠️ ONLY USE IF: You're deploying via GitHub Actions
  # NOT NEEDED FOR: Local execution (just use .env file)
  ```

### 6. **setup-terraform-backend.sh**
- **Purpose**: One-time Azure backend setup for Terraform
- **Risk Level**: Medium-High (creates billable Azure resources)
- **Issues**:
  - Only relevant for Azure deployment
  - Creates resources that cost money
  - Most users won't use this
- **Recommendation**: **KEEP but add MASSIVE warning**
- **Header Should Say**:
  ```bash
  # ════════════════════════════════════════════════════════════════
  # ⚠️  CREATES BILLABLE AZURE RESOURCES - DO NOT RUN CASUALLY!
  # ════════════════════════════════════════════════════════════════
  # Purpose: One-time setup of Terraform remote state storage in Azure
  # Only needed if: You're deploying this system to Azure using Terraform
  # Estimated cost: ~$1-2/month for storage account
  # 
  # If you just want to run locally, YOU DO NOT NEED THIS SCRIPT.
  ```

### 7. **deploy.sh**
- **Purpose**: Master deployment script (Terraform operations)
- **Risk Level**: **HIGH** (can destroy infrastructure)
- **Issues**:
  - Contains `destroy` command
  - Expects complex Azure/Terraform setup
  - Auto-approve option is dangerous
- **Recommendation**: **KEEP but rename and add nuclear warnings**
- **Suggested Rename**: `deploy-terraform.sh` or `terraform-ops.sh`
- **Header Should Say**:
  ```bash
  # ════════════════════════════════════════════════════════════════
  # ⚠️  ⚠️  ⚠️  DESTRUCTIVE OPERATIONS - EXPERTS ONLY ⚠️  ⚠️  ⚠️
  # ════════════════════════════════════════════════════════════════
  # This script performs Terraform operations on Azure infrastructure.
  # Commands like 'destroy' will DELETE ALL RESOURCES and cannot be undone.
  # 
  # DO NOT run this script unless you:
  #   ✓ Have a configured Azure subscription
  #   ✓ Have set up Terraform backend (setup-terraform-backend.sh)
  #   ✓ Understand what Terraform plan/apply/destroy do
  #   ✓ Are comfortable with infrastructure-as-code
  # 
  # If you just want to analyze stocks locally, DO NOT USE THIS SCRIPT.
  # Use: ./scripts/run-analysis.sh instead
  ```

---

## ❌ REMOVE - Vestigial/Personal/Confusing

### 8. **dump-to-scratch.sh** ❌ DELETE
- **Purpose**: Creates text archive of entire repo for AI analysis
- **Why Remove**: This is YOUR workflow tool, not user-facing
- **User Confusion**: "Why would I archive my own repo?"
- **Verdict**: Personal utility script - **DELETE**

### 9. **dump-to-scratch-brief.sh** ❌ DELETE
- **Purpose**: Briefer version of dump-to-scratch.sh
- **Why Remove**: Same as above
- **Verdict**: Personal utility script - **DELETE**

### 10. **graph_diagnostic_script.py** ❌ DELETE
- **Purpose**: Debug LangGraph node creation issues
- **Why Remove**: 
  - Debugging artifact from development
  - References old issues you've already fixed
  - Not useful to end users
- **Verdict**: Development debugging tool - **DELETE**

### 11. **fix-python-compatibility.sh** ❌ DELETE (or merge into setup)
- **Purpose**: Fixes Python 3.13/NumPy compatibility issues
- **Why Remove**: 
  - Very specific to a past compatibility crisis
  - Most users will use Python 3.11/3.12
  - Outdated references to OpenAI migration
- **Verdict**: Either **DELETE** or merge relevant parts into README setup instructions

### 12. **check-python-compatibility.py** ❌ DELETE (or merge into main health check)
- **Purpose**: Checks Python version and NumPy compatibility
- **Why Remove**:
  - Overlaps with health_check.py
  - Solves a problem that's mostly historical
- **Alternative**: Add Python version check to `src/health_check.py`
- **Verdict**: **DELETE** - merge into health check if needed

### 13. **update_dependencies.sh** ⚠️ DANGEROUS - DELETE
- **Purpose**: Nuclear option - clears Poetry cache, removes venv, deletes ChromaDB
- **Why Remove**:
  - **DESTRUCTIVE** - deletes user's ChromaDB database!
  - Too aggressive for public repo
  - Most issues don't require this
- **Alternative**: Document this in troubleshooting section of README
- **Verdict**: **DELETE** - provide instructions in README instead

---

## 📊 Summary Table

| Script | Action | Reason |
|--------|--------|--------|
| **prompt_manager.py** | ✅ KEEP | Core user-facing tool |
| **run-analysis.sh** | ✅ KEEP | Primary CLI interface |
| **run_tickers.sh** | ✅ KEEP | Batch analysis utility |
| **check-environment.sh** | ✅ KEEP | Setup validation |
| **setup-github-secrets.sh** | ⚠️ KEEP + WARN | Only for CI/CD users |
| **setup-terraform-backend.sh** | ⚠️ KEEP + WARN | Only for Azure deployment |
| **deploy.sh** | ⚠️ KEEP + RENAME + WARN | Rename to `terraform-ops.sh` |
| **dump-to-scratch.sh** | ❌ DELETE | Personal utility |
| **dump-to-scratch-brief.sh** | ❌ DELETE | Personal utility |
| **graph_diagnostic_script.py** | ❌ DELETE | Debug artifact |
| **fix-python-compatibility.sh** | ❌ DELETE | Historical fix |
| **check-python-compatibility.py** | ❌ DELETE | Merge into health_check |
| **update_dependencies.sh** | ❌ DELETE | Too destructive |

---

## 📝 Recommended Actions

### Phase 1: Delete Vestigial Scripts
```bash
rm scripts/dump-to-scratch.sh
rm scripts/dump-to-scratch-brief.sh
rm scripts/graph_diagnostic_script.py
rm scripts/fix-python-compatibility.sh
rm scripts/check-python-compatibility.py
rm scripts/update_dependencies.sh
```

### Phase 2: Add Warning Headers
Add prominent warnings to:
- `scripts/setup-github-secrets.sh` → "Only for CI/CD users"
- `scripts/setup-terraform-backend.sh` → "Creates billable Azure resources"
- `scripts/deploy.sh` → Rename to `terraform-ops.sh` + nuclear warning

### Phase 3: Update README
Add a **Scripts Overview** section:

```markdown
## Available Scripts

### For Local Development (Most Users)
- `scripts/run-analysis.sh` - Analyze a single stock ticker
- `scripts/run_tickers.sh` - Batch analyze multiple tickers
- `scripts/check-environment.sh` - Validate your .env configuration
- `scripts/prompt_manager.py` - Manage and customize agent prompts

### For Deployment (Advanced Users Only)
⚠️ **These scripts are for deploying to Azure and are NOT needed for local use:**
- `scripts/terraform-ops.sh` - Terraform operations (plan/apply/destroy)
- `scripts/setup-terraform-backend.sh` - One-time Terraform backend setup
- `scripts/setup-github-secrets.sh` - GitHub Actions secrets automation

**If you just want to analyze stocks locally, only use the first four scripts.**
```

---

## 🎯 Final Script List (After Cleanup)

**Core User Scripts (7 files):**
1. `prompt_manager.py` - Prompt management CLI
2. `run-analysis.sh` - Single ticker analysis
3. `run_tickers.sh` - Batch ticker analysis  
4. `check-environment.sh` - Environment validation

**Advanced/Optional (3 files):**
5. `setup-github-secrets.sh` - GitHub Actions secrets (with warning)
6. `setup-terraform-backend.sh` - Terraform backend setup (with warning)
7. `terraform-ops.sh` - Terraform operations (renamed from deploy.sh, with warning)

**Total: 7 scripts** (down from 13)

---

## 💡 Key Principles

1. **"Will a typical user need this?"** → If no, delete or heavily warn
2. **"Could this destroy user data/cost money?"** → Nuclear warnings required
3. **"Is this my personal workflow?"** → Delete
4. **"Does this overlap with better tools?"** → Merge or delete
5. **"Is this solving a historical problem?"** → Delete and document in README

The goal is a **lean, safe, obvious** scripts directory where every file has a clear purpose and users won't accidentally shoot themselves in the foot.
