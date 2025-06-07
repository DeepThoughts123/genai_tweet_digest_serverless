# Schedule Management Guide for GenAI Tweets Digest

This guide provides comprehensive instructions for manually managing the digest generation schedule in your serverless GenAI Tweets Digest system.

## 📋 Overview

The digest generation is controlled by an AWS EventBridge rule that triggers the weekly digest Lambda function. You can modify this schedule using several methods, from quick temporary changes to permanent infrastructure updates.

**Current EventBridge Rule**: `genai-tweets-digest-production-digest-schedule`

## 🎯 Method 1: Direct AWS CLI (Quickest for Immediate Changes)

### Quick Schedule Change

**Basic command structure:**
```bash
zsh -d -f -c "export AWS_PROFILE=personal && aws events put-rule \
  --name 'genai-tweets-digest-production-digest-schedule' \
  --schedule-expression 'CRON_EXPRESSION_HERE' \
  --state ENABLED \
  --region us-east-1"
```

### Common Schedule Examples

**Every 15 minutes (for testing):**
```bash
zsh -d -f -c "export AWS_PROFILE=personal && aws events put-rule \
  --name 'genai-tweets-digest-production-digest-schedule' \
  --schedule-expression 'cron(*/15 * * * ? *)' \
  --state ENABLED \
  --region us-east-1"
```

**Every 30 minutes:**
```bash
zsh -d -f -c "export AWS_PROFILE=personal && aws events put-rule \
  --name 'genai-tweets-digest-production-digest-schedule' \
  --schedule-expression 'cron(*/30 * * * ? *)' \
  --state ENABLED \
  --region us-east-1"
```

**Every hour:**
```bash
zsh -d -f -c "export AWS_PROFILE=personal && aws events put-rule \
  --name 'genai-tweets-digest-production-digest-schedule' \
  --schedule-expression 'cron(0 * * * ? *)' \
  --state ENABLED \
  --region us-east-1"
```

**Every 6 hours:**
```bash
zsh -d -f -c "export AWS_PROFILE=personal && aws events put-rule \
  --name 'genai-tweets-digest-production-digest-schedule' \
  --schedule-expression 'cron(0 */6 * * ? *)' \
  --state ENABLED \
  --region us-east-1"
```

**Daily at 9 AM UTC:**
```bash
zsh -d -f -c "export AWS_PROFILE=personal && aws events put-rule \
  --name 'genai-tweets-digest-production-digest-schedule' \
  --schedule-expression 'cron(0 9 * * ? *)' \
  --state ENABLED \
  --region us-east-1"
```

**Weekly on Sunday at 9 AM UTC (typical production schedule):**
```bash
zsh -d -f -c "export AWS_PROFILE=personal && aws events put-rule \
  --name 'genai-tweets-digest-production-digest-schedule' \
  --schedule-expression 'cron(0 9 ? * SUN *)' \
  --state ENABLED \
  --region us-east-1"
```

**Weekdays only at 8 AM UTC:**
```bash
zsh -d -f -c "export AWS_PROFILE=personal && aws events put-rule \
  --name 'genai-tweets-digest-production-digest-schedule' \
  --schedule-expression 'cron(0 8 ? * MON-FRI *)' \
  --state ENABLED \
  --region us-east-1"
```

### Enable/Disable Schedule

**Disable all digest generation:**
```bash
zsh -d -f -c "export AWS_PROFILE=personal && aws events disable-rule \
  --name 'genai-tweets-digest-production-digest-schedule' \
  --region us-east-1"
```

**Re-enable digest generation:**
```bash
zsh -d -f -c "export AWS_PROFILE=personal && aws events enable-rule \
  --name 'genai-tweets-digest-production-digest-schedule' \
  --region us-east-1"
```

### Check Current Schedule Status

**View current schedule and state:**
```bash
zsh -d -f -c "export AWS_PROFILE=personal && aws events describe-rule \
  --name 'genai-tweets-digest-production-digest-schedule' \
  --region us-east-1 \
  --query '{Name: Name, State: State, ScheduleExpression: ScheduleExpression}' \
  --output table"
```

**JSON output for scripting:**
```bash
zsh -d -f -c "export AWS_PROFILE=personal && aws events describe-rule \
  --name 'genai-tweets-digest-production-digest-schedule' \
  --region us-east-1 \
  --query '{Schedule: ScheduleExpression, State: State}' \
  --output json"
```

## 🛠️ Method 2: Using the Ad-hoc Testing Script

### Quick Ad-hoc Schedule Setup

The ad-hoc testing script provides an easy way to temporarily change schedules with automatic backup/restore.

**Setup a custom schedule (automatically backs up original):**
```bash
./scripts/adhoc-testing.sh setup YYYY-MM-DD HH:MM
```

**Examples:**
```bash
# Run every 15 minutes starting May 28 at 2 PM EST
./scripts/adhoc-testing.sh setup 2025-05-28 14:00

# Run every 15 minutes starting tomorrow at 10 AM EST
./scripts/adhoc-testing.sh setup 2025-05-29 10:00
```

**Check system status:**
```bash
./scripts/adhoc-testing.sh check
```

**Monitor digest execution in real-time:**
```bash
./scripts/adhoc-testing.sh monitor
```

**Manually trigger a single digest (for testing):**
```bash
./scripts/adhoc-testing.sh trigger
```

**Check recent digest results:**
```bash
./scripts/adhoc-testing.sh results
```

**Restore original schedule:**
```bash
./scripts/adhoc-testing.sh restore
```

### Script Commands Reference

| Command | Description | Example |
|---------|-------------|---------|
| `check` | Show system status and subscriber count | `./scripts/adhoc-testing.sh check` |
| `setup` | Configure ad-hoc testing schedule | `./scripts/adhoc-testing.sh setup 2025-05-28 11:15` |
| `monitor` | Real-time CloudWatch log monitoring | `./scripts/adhoc-testing.sh monitor` |
| `trigger` | Manually run digest generation once | `./scripts/adhoc-testing.sh trigger` |
| `results` | Show recent digest files and content | `./scripts/adhoc-testing.sh results` |
| `restore` | Restore original schedule from backup | `./scripts/adhoc-testing.sh restore` |

## 📋 Method 3: CloudFormation Template (Permanent Changes)

For permanent schedule changes that should be part of your infrastructure-as-code, edit the CloudFormation template.

### Edit the Template

**File:** `infrastructure-aws/cloudformation-template.yaml`  
**Line:** ~404

**Find this section:**
```yaml
# EventBridge rule for digest generation
WeeklyDigestSchedule:
  Type: AWS::Events::Rule
  Properties:
    Name: !Sub "${AWS::StackName}-digest-schedule"
    Description: Trigger digest generation every 30 minutes for testing
    ScheduleExpression: "cron(*/30 * * * ? *)"  # Change this line
    State: ENABLED
    Targets:
      - Arn: !GetAtt WeeklyDigestFunction.Arn
        Id: WeeklyDigestTarget
```

**Update the `ScheduleExpression` line with your desired schedule:**
```yaml
ScheduleExpression: "cron(0 9 ? * SUN *)"  # Weekly on Sunday at 9 AM UTC
```

### Deploy Changes

**After editing the template, deploy the changes:**
```bash
./scripts/deploy-optimized.sh
```

This will update the CloudFormation stack with your new schedule.

### Template Schedule Examples

**Weekly production schedule:**
```yaml
ScheduleExpression: "cron(0 9 ? * SUN *)"  # Every Sunday at 9 AM UTC
```

**Daily digest:**
```yaml
ScheduleExpression: "cron(0 9 * * ? *)"  # Every day at 9 AM UTC
```

**Twice daily:**
```yaml
ScheduleExpression: "cron(0 9,21 * * ? *)"  # Every day at 9 AM and 9 PM UTC
```

**Business hours only:**
```yaml
ScheduleExpression: "cron(0 9 ? * MON-FRI *)"  # Weekdays at 9 AM UTC
```

## 📱 Method 4: AWS Console (GUI)

### Step-by-Step Console Instructions

1. **Open AWS Console** and navigate to **Amazon EventBridge**
2. **Select "Rules"** from the left sidebar
3. **Find rule:** `genai-tweets-digest-production-digest-schedule`
4. **Click the rule name** to open details
5. **Click "Edit"** button
6. **Find "Schedule"** section
7. **Modify the "Schedule expression"** field
8. **Click "Save"** to apply changes

### Console Schedule Expression Examples

In the AWS Console, enter these expressions in the "Schedule expression" field:

- Every 15 minutes: `cron(*/15 * * * ? *)`
- Every hour: `cron(0 * * * ? *)`
- Daily at 9 AM UTC: `cron(0 9 * * ? *)`
- Weekly Sunday 9 AM UTC: `cron(0 9 ? * SUN *)`

## ⏰ Cron Expression Reference

### EventBridge Cron Format

EventBridge uses **6-field cron format**: `cron(minute hour day month day-of-week year)`

| Field | Values | Special Characters |
|-------|--------|--------------------|
| Minute | 0-59 | `,` `-` `*` `/` |
| Hour | 0-23 | `,` `-` `*` `/` |
| Day | 1-31 | `,` `-` `*` `?` `/` `L` `W` |
| Month | 1-12 or JAN-DEC | `,` `-` `*` `/` |
| Day-of-week | 1-7 or SUN-SAT | `,` `-` `*` `?` `/` `L` `#` |
| Year | 1970-2199 | `,` `-` `*` `/` |

### Common Patterns

| Pattern | Cron Expression | Description |
|---------|----------------|-------------|
| Every minute | `cron(* * * * ? *)` | For testing only |
| Every 5 minutes | `cron(*/5 * * * ? *)` | High frequency testing |
| Every 15 minutes | `cron(*/15 * * * ? *)` | Medium frequency testing |
| Every 30 minutes | `cron(*/30 * * * ? *)` | Low frequency testing |
| Every hour | `cron(0 * * * ? *)` | Hourly processing |
| Every 2 hours | `cron(0 */2 * * ? *)` | Every other hour |
| Every 6 hours | `cron(0 */6 * * ? *)` | 4 times per day |
| Every 12 hours | `cron(0 */12 * * ? *)` | Twice per day |
| Daily at midnight UTC | `cron(0 0 * * ? *)` | Once per day |
| Daily at 9 AM UTC | `cron(0 9 * * ? *)` | Morning digest |
| Daily at 6 PM UTC | `cron(0 18 * * ? *)` | Evening digest |
| Twice daily | `cron(0 9,18 * * ? *)` | Morning and evening |
| Weekly Sunday 9 AM | `cron(0 9 ? * SUN *)` | Weekly digest |
| Weekdays 8 AM | `cron(0 8 ? * MON-FRI *)` | Business days only |
| First day of month | `cron(0 9 1 * ? *)` | Monthly digest |

### Special Characters

- **`*`** = All values (any)
- **`?`** = No specific value (for day or day-of-week)
- **`/`** = Increments (e.g., `*/15` = every 15 units)
- **`,`** = List separator (e.g., `1,3,5`)
- **`-`** = Range (e.g., `MON-FRI`)

### Time Zone Notes

- **All cron expressions are in UTC**
- **Convert local times to UTC** when setting schedules
- **EST = UTC-5** (Standard Time)
- **EDT = UTC-4** (Daylight Time)

**Example conversions:**
- 9 AM EST = 2 PM UTC = `cron(0 14 * * ? *)`
- 9 AM EDT = 1 PM UTC = `cron(0 13 * * ? *)`

## 🔍 Monitoring and Verification

### Check Digest Generation Results

**List recent digest files:**
```bash
zsh -d -f -c "export AWS_PROFILE=personal && aws s3 ls 's3://genai-tweets-digest-production-data/tweets/digests/' \
  --recursive --human-readable --region us-east-1 | tail -10"
```

**Download and examine latest digest:**
```bash
zsh -d -f -c "export AWS_PROFILE=personal && aws s3 cp 's3://genai-tweets-digest-production-data/tweets/digests/latest-digest.json' \
  '/tmp/latest_digest.json' --region us-east-1"

# View digest summary
jq -r '.generation_metadata.summary // .summary // "No summary available"' /tmp/latest_digest.json
```

### Monitor CloudWatch Logs

**View recent Lambda execution logs:**
```bash
zsh -d -f -c "export AWS_PROFILE=personal && aws logs tail '/aws/lambda/genai-tweets-digest-production-weekly-digest' \
  --region us-east-1 --follow"
```

**Get specific log events:**
```bash
# Get latest log stream
LATEST_STREAM=$(zsh -d -f -c "export AWS_PROFILE=personal && aws logs describe-log-streams \
  --log-group-name '/aws/lambda/genai-tweets-digest-production-weekly-digest' \
  --order-by LastEventTime --descending --max-items 1 \
  --query 'logStreams[0].logStreamName' --output text --region us-east-1")

# Get log events from latest stream
zsh -d -f -c "export AWS_PROFILE=personal && aws logs get-log-events \
  --log-group-name '/aws/lambda/genai-tweets-digest-production-weekly-digest' \
  --log-stream-name '$LATEST_STREAM' --region us-east-1 \
  --start-time $(($(date +%s) - 3600))000"
```

### Check Subscriber Status

**View current subscribers:**
```bash
zsh -d -f -c "export AWS_PROFILE=personal && aws dynamodb scan \
  --table-name genai-tweets-digest-production-subscribers \
  --region us-east-1 --output json | \
  jq '.Items[] | {email: .email.S, status: .status.S, created_at: .created_at.S}'"
```

**Count total subscribers:**
```bash
zsh -d -f -c "export AWS_PROFILE=personal && aws dynamodb scan \
  --table-name genai-tweets-digest-production-subscribers \
  --select COUNT --region us-east-1 --output json | jq '.Count'"
```

## 🚨 Troubleshooting

### Common Issues

**Rule not found error:**
```
An error occurred (ResourceNotFoundException) when calling the DescribeRule operation
```
*Solution: Check the rule name and region. Rule name should be exactly `genai-tweets-digest-production-digest-schedule`*

**Permission denied:**
```
An error occurred (AccessDeniedException) when calling the PutRule operation
```
*Solution: Ensure AWS_PROFILE=personal is set and credentials have EventBridge permissions*

**Invalid cron expression:**
```
Parameter ScheduleExpression is not valid
```
*Solution: Verify cron expression format. EventBridge uses 6-field format, not standard 5-field*

### Verification Commands

**Check if AWS CLI is configured correctly:**
```bash
aws sts get-caller-identity --profile personal
```

**List all EventBridge rules:**
```bash
zsh -d -f -c "export AWS_PROFILE=personal && aws events list-rules \
  --region us-east-1 --query 'Rules[?contains(Name, \`genai-tweets-digest\`)].{Name: Name, State: State}'"
```

**Verify Lambda function exists:**
```bash
zsh -d -f -c "export AWS_PROFILE=personal && aws lambda get-function \
  --function-name genai-tweets-digest-production-weekly-digest \
  --region us-east-1 --query 'Configuration.FunctionName'"
```

## 📚 Best Practices

### 1. Testing New Schedules

- **Start with manual triggers** to verify functionality
- **Use short intervals** (15-30 minutes) for initial testing
- **Monitor CloudWatch logs** during test periods
- **Check digest file generation** in S3

### 2. Production Schedules

- **Weekly digests** are typically sufficient for production
- **Sunday 9 AM UTC** is a common choice (aligns with week start)
- **Consider subscriber time zones** when choosing times
- **Avoid peak usage periods** for cost optimization

### 3. Schedule Changes

- **Test in a separate stack** first if possible
- **Use Method 1 (AWS CLI)** for quick temporary changes
- **Use Method 3 (CloudFormation)** for permanent changes
- **Always verify changes** with status commands

### 4. Monitoring

- **Set up CloudWatch alarms** for Lambda errors
- **Monitor digest file generation** regularly
- **Check subscriber feedback** for timing preferences
- **Review costs** if using high-frequency schedules

## 📖 Quick Reference

### Essential Commands

```bash
# Check current schedule
zsh -d -f -c "export AWS_PROFILE=personal && aws events describe-rule --name 'genai-tweets-digest-production-digest-schedule' --region us-east-1 --query '{Schedule: ScheduleExpression, State: State}'"

# Change to weekly Sunday 9 AM UTC
zsh -d -f -c "export AWS_PROFILE=personal && aws events put-rule --name 'genai-tweets-digest-production-digest-schedule' --schedule-expression 'cron(0 9 ? * SUN *)' --state ENABLED --region us-east-1"

# Disable all scheduled digests
zsh -d -f -c "export AWS_PROFILE=personal && aws events disable-rule --name 'genai-tweets-digest-production-digest-schedule' --region us-east-1"

# Enable scheduled digests
zsh -d -f -c "export AWS_PROFILE=personal && aws events enable-rule --name 'genai-tweets-digest-production-digest-schedule' --region us-east-1"

# Manual trigger for testing
./scripts/adhoc-testing.sh trigger

# Check recent results
./scripts/adhoc-testing.sh results
```

### File Locations

- **CloudFormation template**: `infrastructure-aws/cloudformation-template.yaml` (line ~404)
- **Ad-hoc testing script**: `scripts/adhoc-testing.sh`
- **Schedule backup**: `/tmp/original_schedule_backup.txt` (created by ad-hoc script)

---

*This guide covers all methods for managing your digest generation schedule. Choose the method that best fits your use case: AWS CLI for quick changes, ad-hoc script for testing, CloudFormation for permanent changes, or AWS Console for GUI preference.* 