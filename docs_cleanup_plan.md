# Documentation Cleanup Plan

## Current Issues

### 1. **Outdated Documentation**
- `CODEBASE_STRUCTURE.md` - References old `lambdas/` directory structure
- `TODO.md` - Contains old development notes, mostly completed tasks
- Architecture docs reference old structure

### 2. **Historical vs Current Content**
- `IMPLEMENTATION_PROGRESS.md` (46KB, 790 lines) - Historical development tracking
- Multiple deployment success/testing results docs are historical records
- Migration docs are historical but may be useful for reference

### 3. **Poor Organization**
- 25+ files at root level should be categorized
- Multiple testing guides that should be consolidated
- API, deployment, development subdirectories are mostly empty
- Duplicated content across multiple files

### 4. **Content Categories Needed**
- **Architecture** - Current system design, structure
- **Development** - Setup, testing, contribution guides  
- **Deployment** - Deployment guides, troubleshooting
- **API** - API documentation
- **Historical** - Implementation history, migration records
- **Reference** - Quick references, best practices

## Cleanup Actions

### Phase 1: Update Core Documentation
1. **Update CODEBASE_STRUCTURE.md** - Reflect new src/ structure
2. **Archive IMPLEMENTATION_PROGRESS.md** - Move to historical/
3. **Delete TODO.md** - Outdated development notes

### Phase 2: Consolidate Testing Documentation  
1. **Create unified TESTING_GUIDE.md** from:
   - `TESTING_GUIDE.md`
   - `FRONTEND_TESTING_GUIDE.md` 
   - `DEPLOYMENT_TESTING_GUIDE.md`
   - `E2E_TESTING_PLAN.md`
   - `E2E_TESTING_QUICK_REFERENCE.md`
2. **Archive detailed test results** to historical/

### Phase 3: Organize by Categories
1. **Architecture/**:
   - Current system architecture
   - Hybrid Lambda + Fargate design
   - Component documentation
   
2. **Development/**:
   - Development setup
   - Testing guide (consolidated)
   - Contributing guidelines
   
3. **Deployment/**:
   - Deployment guides
   - Best practices
   - Troubleshooting
   
4. **Historical/**:
   - Implementation progress
   - Migration documentation  
   - Historical testing results

5. **Reference/**:
   - Quick reference guides
   - Best practices
   - Security recommendations

### Phase 4: Create Navigation
1. **README.md** for docs/ - Directory guide
2. **Quick-start documentation** for new developers
3. **Cross-references** between related docs

## File Organization Plan

### Keep and Update:
- `CODEBASE_STRUCTURE.md` → Update for new structure
- `DEVELOPMENT_SETUP.md` → Move to development/
- `SECURITY_RECOMMENDATIONS.md` → Move to reference/
- Architecture files → Keep in architecture/

### Consolidate:
- Testing guides → Single `development/TESTING.md`
- Deployment guides → Single `deployment/DEPLOYMENT.md`

### Archive:
- `IMPLEMENTATION_PROGRESS.md` → historical/
- Testing results → historical/testing_results/
- Migration docs → historical/migration/

### Delete:
- `TODO.md` - Outdated
- Duplicate content
- Obsolete guides

## Expected Benefits

1. **Easy Navigation**: Clear categories, intuitive structure
2. **Current Information**: Up-to-date documentation only
3. **Reduced Duplication**: Single source of truth
4. **Better Maintenance**: Easier to keep docs current
5. **New Developer Friendly**: Clear entry points and guides 