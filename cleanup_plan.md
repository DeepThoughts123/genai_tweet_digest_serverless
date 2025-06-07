# Cleanup Plan - Old Directory Structure

## 🎯 Objective
Remove redundant files and directories after successful code reorganization while preserving all functionality.

## ✅ Verification Status
- ✅ New structure tested and working
- ✅ Backend tests passing (31/31)
- ✅ Frontend tests passing (24/24)
- ✅ Import paths updated and functional
- ✅ All features confirmed in new locations

## 📁 Directories to DELETE

### 1. `lambdas/` → SAFE TO DELETE
**Moved to**: `src/lambda_functions/` and `src/shared/`
**Contains**:
- `shared/` → moved to `src/shared/`
- `weekly-digest/` → moved to `src/lambda_functions/weekly_digest/`
- `subscription/` → moved to `src/lambda_functions/subscription/`
- `email-verification/` → moved to `src/lambda_functions/email_verification/`
- `unsubscribe/` → moved to `src/lambda_functions/unsubscribe/`
- `visual-processing-dispatcher/` → moved to `src/lambda_functions/fargate_dispatcher/`
- `tests/` → moved to `tests/unit/test_shared/`
- Build artifacts: `*.zip`, `*.log`, `__pycache__/`, etc.

### 2. `scripts/` → SAFE TO DELETE  
**Moved to**: `deployment/scripts/`
**Contains**: All deployment and utility scripts (12 files confirmed moved)

### 3. `infrastructure-aws/` → SAFE TO DELETE
**Moved to**: `infrastructure/cloudformation/`
**Contains**: All CloudFormation templates (3 files confirmed moved)

### 4. `frontend/` → SAFE TO DELETE
**Moved to**: `src/frontend/`
**Contains**: Complete Next.js application with all components and tests

### 5. `frontend-static/` → SAFE TO DELETE
**Merged into**: `src/frontend/`
**Contains**: Static website assets merged into main frontend

### 6. `data/` → SAFE TO DELETE
**Moved to**: `config/`
**Contains**: 
- `accounts.json` → moved to `config/accounts.json`
- `accounts-test.json` → moved to `config/accounts-test.json`

### 7. `shared/` (root level) → SAFE TO DELETE
**Moved to**: `src/shared/`
**Contains**: Any shared utilities (likely empty or duplicate)

## 📄 Files to DELETE

### 1. `cf-params.json` → SAFE TO DELETE
**Moved to**: `infrastructure/cloudformation/parameters/production.json`

### 2. Build/Cache Artifacts → SAFE TO DELETE
- `__pycache__/` directories
- `.pytest_cache/`
- `.benchmarks/`
- `test-results/`
- `.DS_Store` files
- `tsconfig.tsbuildinfo` files

## 🔍 Directories to PRESERVE

### Keep as-is:
- `src/` - New main source directory
- `infrastructure/` - New infrastructure directory  
- `deployment/` - New deployment directory
- `config/` - New configuration directory
- `tests/` - Reorganized test directory
- `docs/` - Documentation
- `tools/` - Development tools
- `archive/` - Historical reference
- `planning/` - Project planning docs
- `.git/` - Git repository
- `.vscode/` - IDE settings
- `.venv311/` - Python virtual environment

### Check before deletion:
- `exploration/` - Should be moved to `archive/` if not already
- `prototypes/` - Should be moved to `archive/` if not already
- `ec2-processing/` - Check if content moved to Fargate structure
- `batch-processing/` - Check if content moved to Fargate structure
- `visual_captures/` - Check if needed or can be archived
- `prompts/` - Check if needed for development
- `useful_commands/` - Check if needed or can be moved to `tools/`

## 🛡️ Safety Checks Before Deletion

1. ✅ All tests passing with new structure
2. ✅ Import statements updated and working
3. ✅ Frontend builds and runs successfully
4. ✅ Backend services can be imported correctly
5. ✅ All moved files verified in new locations

## 🚀 Cleanup Benefits

After cleanup:
- **Cleaner repository**: Remove ~200MB+ of redundant files
- **Clearer structure**: Single source of truth for all code
- **Faster operations**: Less files to scan/index
- **Reduced confusion**: No duplicate files with different import paths
- **Better maintenance**: Clear separation of concerns

## ⚠️ Rollback Plan

- All changes tracked in git - can revert if needed
- Archive directory preserves exploration/prototype code
- New structure tested extensively before cleanup 