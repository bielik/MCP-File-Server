# Phase 4 Migration Guide: From Legacy Config to Database & Mount Point Transition

**Last Updated:** January 17, 2025
**Status:** Production Ready
**Phase:** 4 - Migration & Deprecation Strategy

## Overview

This guide will help you migrate your MCP KnowledgeExplorer instance from:
1. **Config-based permissions** → **Database-driven permissions**
2. **Legacy `/shared-fs` mount** → **New `/source` mount point**

The migration is designed to be **backward compatible** and **non-breaking**. Your application will continue to work during the transition period.

## 🚨 Before You Start

### Prerequisites Checklist
- [ ] Backup your current `config/permissions.json` file
- [ ] Ensure you have database permissions enabled: `ENABLE_DATABASE_PERMISSIONS=true`
- [ ] Verify your current environment configuration (`.env` file)
- [ ] Stop any running instances of the application

### What This Migration Includes
- ✅ Move all permission rules from JSON files to SQLite database
- ✅ Create workspace structure for better organization
- ✅ Add dual mount point support (`/shared-fs` + `/source`)
- ✅ Deprecation warnings with guidance
- ✅ Backward compatibility during transition

## Step 1: Config-to-Database Migration

### Current State Check
First, verify your current permission configuration:

```bash
# Check your current config file
cat config/permissions.json

# Verify it has rules
jq '.rules | length' config/permissions.json
```

### Run the Migration

#### Dry-Run First (Recommended)
```bash
cd backend
python -m app.scripts.migrate_config_to_db \
  --workspace-name "Legacy Config" \
  --activate \
  --dry-run
```

**Expected Output:**
```
DRY RUN MODE - No changes will be made to the database
Prerequisites validated. Found 6 rules to migrate.
DRY RUN: Would migrate rule context-docs-read - allow read on docs
DRY RUN: Would migrate rule working-projects-write - allow write on projects
...
```

#### Execute Actual Migration
```bash
cd backend
python -m app.scripts.migrate_config_to_db \
  --workspace-name "Legacy Config" \
  --activate
```

**Expected Output:**
```
Created workspace 'Legacy Config' with ID: 3
Migrated rule context-docs-read -> Permission ID 2
Migration completed successfully
```

### Verify Migration Success

#### Via API
```bash
# Check workspaces
curl http://localhost:8000/api/workspaces

# Check permissions in the migrated workspace
curl http://localhost:8000/api/workspaces/3/permissions
```

#### Via Web UI
1. Open http://localhost:5173 (or your frontend port)
2. Navigate to "🏠 Workspaces" tab
3. Verify "Legacy Config" workspace exists and is active
4. Check that all your permission rules are present

## Step 2: Enable Dual Mount Points

### Update Environment Configuration

Add these flags to your `.env` file:

```bash
# Phase 4 Feature Flags (Migration & Deprecation)
ENABLE_SOURCE_MOUNT=true
SHOW_DEPRECATION_WARNING=true
```

### Update Docker Configuration

Update your `docker-compose.yml` to include both mount points:

```yaml
services:
  backend:
    volumes:
      - ./backend:/app
      - ${DATABASE_PATH:-./data}:/data
      - ${SHARED_FS_PATH:-./shared-fs}:/shared-fs  # Legacy mount point
      - ${SHARED_FS_PATH:-./shared-fs}:/source     # New primary mount point
      - ./config:/config
```

### Restart Services
```bash
docker-compose down
docker-compose up -d
```

## Step 3: Verify Dual Mount Setup

### Check Mount Point Status
```bash
# Check deprecation status
curl http://localhost:8000/api/system/deprecation-status

# Check mount points
curl http://localhost:8000/api/system/mount-status
```

**Expected Response:**
```json
{
  "legacy_mount_detected": true,
  "current_mount": "/shared-fs",
  "recommended_mount": "/source",
  "dual_mount_available": true,
  "source_mount_enabled": true
}
```

### Web UI Verification
1. Open your application in the browser
2. You should see a deprecation warning banner at the top
3. The warning will show:
   - Current mount point: `/shared-fs (legacy)`
   - Available mount points
   - Recommended actions

## Step 4: Test Both Mount Points

### File Access Testing
```bash
# Test via MCP tools (if you have claude connected)
# This should work with both mount points now

# Test API access
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

### Verify Path Resolution
The system should now:
- ✅ Resolve paths in both `/shared-fs` and `/source`
- ✅ Maintain all existing functionality
- ✅ Show deprecation warnings appropriately

## Step 5: Plan Legacy Mount Removal

### When You're Ready (Future)
Once you've verified everything works correctly:

1. **Update references:** Change any hardcoded paths from `/shared-fs` to `/source`
2. **Remove legacy mount:** Remove the `/shared-fs` mount from `docker-compose.yml`
3. **Update environment:** Set `SHOW_DEPRECATION_WARNING=false`

**Note:** This step is optional and should only be done when you're confident the migration is complete.

## Troubleshooting

### Common Issues

#### Issue: "Database permissions are not enabled"
**Solution:**
```bash
# Verify your .env file has:
ENABLE_DATABASE_PERMISSIONS=true

# Restart the application
docker-compose restart backend
```

#### Issue: "Migration script can't find config file"
**Solution:**
```bash
# Run from the correct directory
cd /path/to/MCPFileServer
python -m backend.app.scripts.migrate_config_to_db --workspace-name "Legacy Config" --activate
```

#### Issue: "CORS errors in browser"
**Solution:** Ensure your backend includes the frontend port in CORS configuration:
```python
# In backend/app/main.py
origins = [
    "http://localhost:5173",
    "http://localhost:5175",  # If using different port
    # ... other origins
]
```

#### Issue: "Deprecation warning doesn't appear"
**Solution:**
1. Check browser console for errors
2. Verify API endpoint: `curl http://localhost:8000/api/system/deprecation-status`
3. Ensure `SHOW_DEPRECATION_WARNING=true` in your environment

### Rollback Plan

If you need to rollback:

1. **Disable database permissions:**
   ```bash
   ENABLE_DATABASE_PERMISSIONS=false
   ENABLE_SOURCE_MOUNT=false
   ```

2. **Restart services:**
   ```bash
   docker-compose restart
   ```

3. **Your original `permissions.json` file remains intact** and will be used automatically

## Migration Verification Checklist

### ✅ Phase 1: Database Migration
- [ ] Config file rules migrated to database workspace
- [ ] "Legacy Config" workspace is active
- [ ] All permission rules work as before
- [ ] Web UI shows the migrated workspace

### ✅ Phase 2: Dual Mount Points
- [ ] `ENABLE_SOURCE_MOUNT=true` is set
- [ ] Both mount points available in container
- [ ] Deprecation warning appears in UI
- [ ] API endpoints return correct mount status

### ✅ Phase 3: Functionality Verification
- [ ] File operations work correctly
- [ ] MCP tools function as expected
- [ ] Permission resolution unchanged
- [ ] No breaking changes detected

## Support

### Getting Help
If you encounter issues during migration:

1. **Check the logs:**
   ```bash
   docker-compose logs backend
   ```

2. **Verify API endpoints:**
   ```bash
   curl http://localhost:8000/api/system/health
   ```

3. **Report issues:** [GitHub Issues](https://github.com/anthropics/claude-code/issues)

### Migration Status API

Monitor your migration progress:
```bash
# Overall system health
curl http://localhost:8000/api/system/health

# Deprecation status
curl http://localhost:8000/api/system/deprecation-status

# Mount point details
curl http://localhost:8000/api/system/mount-status
```

## Advanced Configuration

### Custom Workspace Names
```bash
python -m app.scripts.migrate_config_to_db \
  --workspace-name "My Custom Workspace" \
  --activate
```

### Multiple Config Migrations
```bash
# If you have multiple config files
python -m app.scripts.migrate_config_to_db \
  --config-file /path/to/other-config.json \
  --workspace-name "Another Workspace"
```

---

## Summary

This migration guide helps you transition from:
- **Config files** → **Database workspaces** ✅
- **Single mount** → **Dual mount support** ✅
- **Manual management** → **UI-driven workflows** ✅

The migration is **safe**, **backward compatible**, and **reversible**. Your application will continue working throughout the process.

**Next Steps:**
1. Follow this guide step by step
2. Test thoroughly in your environment
3. Plan for future legacy mount point removal
4. Enjoy improved workspace management! 🎉

---

*This guide is part of Phase 4 implementation for the MCP KnowledgeExplorer project.*