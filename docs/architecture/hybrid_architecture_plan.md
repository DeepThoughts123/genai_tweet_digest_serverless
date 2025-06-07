# Hybrid Architecture Migration Plan

## Overview
This document outlines the migration from pure Lambda to a hybrid Lambda + EC2 architecture to accommodate the long-running visual tweet capture pipeline while maintaining the cost-effective serverless architecture for fast operations.

## Architecture Decision

### Current Limitation
- Lambda 15-minute timeout limit
- Visual tweet capture can take hours (browser automation, screenshots, processing)
- Current production system uses text-only processing (fast)

### Recommended Solution: Hybrid Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    HYBRID ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐                    │
│  │   FAST TRACK    │    │   SLOW TRACK    │                    │
│  │   (Lambda)      │    │   (EC2)         │                    │
│  │                 │    │                 │                    │
│  │ • Text fetching │    │ • Visual capture│                    │
│  │ • Categorization│    │ • Screenshots   │                    │
│  │ • Summarization │    │ • Text extraction│                   │
│  │ • Email sending │    │ • Heavy AI work │                    │
│  │                 │    │                 │                    │
│  │ < 15 minutes    │    │ Hours if needed │                    │
│  └─────────────────┘    └─────────────────┘                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Implementation Options

### Option 1: Event-Driven EC2 (Recommended)
**Architecture:**
```
EventBridge → Lambda Dispatcher → EC2 Auto Scaling → Visual Processing → S3 → Lambda Trigger → Email
```

**Benefits:**
- Cost-effective (only runs when needed)
- Automatic scaling
- Serverless management via Lambda

**Implementation:**
1. Create EC2 Auto Scaling Group (min: 0, max: 1)
2. Lambda function triggers EC2 instance launch
3. EC2 runs visual processing pipeline
4. EC2 saves results to S3 and terminates
5. S3 event triggers Lambda for email distribution

### Option 2: ECS Fargate (Alternative)
**Architecture:**
```
EventBridge → ECS Task Definition → Fargate Container → Visual Processing → S3 → Lambda Trigger
```

**Benefits:**
- Containerized approach
- No server management
- Automatic resource allocation

### Option 3: AWS Batch (For Heavy Workloads)  
**Architecture:**
```
EventBridge → Lambda → AWS Batch Job → EC2 Compute Environment → Processing → S3
```

**Benefits:**
- Designed for batch processing
- Automatic resource management
- Cost optimization

## Recommended Implementation: Option 1 (Event-Driven EC2)

### Step-by-Step Migration

#### Phase 1: Prepare EC2 Processing Script
1. Adapt `exploration/integrated_tweet_pipeline.py` for EC2 execution
2. Add S3 result publishing
3. Add CloudWatch logging
4. Add error handling and notifications

#### Phase 2: Infrastructure Setup
1. Create EC2 AMI with required dependencies
2. Set up Auto Scaling Group
3. Create Lambda dispatcher function
4. Update CloudFormation templates

#### Phase 3: Integration
1. Modify EventBridge to trigger dispatcher
2. Set up S3 event triggers
3. Update monitoring and alerting

### Code Structure Changes

#### New Components to Add:

```
lambdas/
├── visual-processing-dispatcher/     # New Lambda to launch EC2
│   └── lambda_function.py
├── processing-complete-handler/      # New Lambda for S3 triggers  
│   └── lambda_function.py
└── shared/
    └── ec2_management.py            # EC2 launch/monitoring utilities

ec2-processing/                      # New directory
├── visual_processing_service.py     # Adapted from exploration/
├── requirements.txt
├── setup_environment.sh
└── user_data.sh                    # EC2 initialization script

infrastructure-aws/
├── ec2-processing-template.yaml     # New EC2 infrastructure
└── hybrid-architecture-template.yaml # Combined template
```

#### Modified Components:

```
lambdas/weekly-digest/
└── lambda_function.py              # Modified to handle both modes

shared/
├── config.py                       # Add EC2 configuration options
└── processing_orchestrator.py      # New - decides Lambda vs EC2
```

### Cost Analysis

#### Current Lambda-Only Costs:
- Weekly digest: ~$0.02 per execution
- Other Lambda functions: ~$0.05 per month
- **Total: ~$0.13/month**

#### Estimated Hybrid Costs:
- Lambda functions (unchanged): ~$0.13/month  
- EC2 processing (t3.medium, 2 hours/week): ~$1.60/month
- **Total: ~$1.73/month** (still very cost-effective)

### Configuration Options

Add environment variables to control behavior:

```bash
# Processing mode selection
PROCESSING_MODE=hybrid              # hybrid, lambda-only, ec2-only
ENABLE_VISUAL_CAPTURE=true          # Enable/disable visual processing
EC2_INSTANCE_TYPE=t3.medium         # Instance type for processing
MAX_PROCESSING_TIME=7200            # Max seconds (2 hours)

# Visual processing parameters
VISUAL_ACCOUNTS_LIMIT=10            # Max accounts to process visually
VISUAL_TWEETS_PER_ACCOUNT=20        # Max tweets per account
PROCESSING_BATCH_SIZE=5             # Tweets to process in parallel
```

### Migration Timeline

#### Week 1-2: Preparation
- [ ] Adapt exploration pipeline for EC2
- [ ] Create EC2 AMI with dependencies
- [ ] Develop Lambda dispatcher function
- [ ] Test processing script locally

#### Week 3: Infrastructure
- [ ] Create CloudFormation templates
- [ ] Set up Auto Scaling Group
- [ ] Deploy dispatcher Lambda
- [ ] Test end-to-end flow in dev environment

#### Week 4: Integration & Testing
- [ ] Deploy to production environment
- [ ] Run parallel processing (Lambda + EC2) for validation
- [ ] Monitor costs and performance
- [ ] Switch traffic to hybrid mode

#### Week 5: Optimization
- [ ] Fine-tune instance types and processing parameters
- [ ] Optimize costs based on actual usage
- [ ] Add advanced monitoring and alerting
- [ ] Documentation and runbooks

## Testing Strategy

### Local Development
1. Test visual processing script on local machine
2. Validate S3 integration and result format
3. Test Lambda dispatcher with mock EC2 calls

### Staging Environment  
1. Deploy full hybrid architecture to staging
2. Process subset of accounts for validation
3. Compare results with current Lambda-only output
4. Performance and cost testing

### Production Rollout
1. Deploy infrastructure with feature flag (disabled)
2. Enable hybrid mode for single account initially  
3. Gradually increase scope based on performance
4. Full rollout once validated

## Monitoring & Observability

### CloudWatch Metrics
- EC2 instance launch/termination events
- Processing duration and success rates
- Cost tracking per execution
- Queue depth and processing lag

### Alarms & Notifications
- EC2 instance stuck (running > max time)
- Processing failures or errors
- Cost threshold exceeded
- S3 result validation failures

### Dashboards
- Processing pipeline health
- Cost breakdown (Lambda vs EC2)
- Performance metrics and trends
- Error rates and debugging info

## Rollback Plan

If issues arise with the hybrid architecture:

1. **Immediate**: Set `PROCESSING_MODE=lambda-only` to disable EC2 processing
2. **Short-term**: Fall back to current text-only processing
3. **Long-term**: Troubleshoot EC2 issues while maintaining service availability

## Future Enhancements

### Parallel Processing
- Process multiple accounts simultaneously
- Batch tweet processing for efficiency
- Dynamic scaling based on workload

### Advanced Features
- Incremental processing (only new tweets)
- Priority-based processing (important accounts first)
- A/B testing between text-only and visual processing

### Cost Optimization
- Spot instances for non-critical processing
- Reserved instances for predictable workloads
- Multi-region processing for global optimization

## Success Criteria

### Performance
- [ ] Visual processing completes within 2 hours
- [ ] 95%+ success rate for tweet capture
- [ ] No degradation in current Lambda performance

### Cost
- [ ] Monthly costs remain under $5
- [ ] Cost per processed tweet under $0.01  
- [ ] ROI positive within 3 months

### Reliability  
- [ ] 99.9% uptime for email delivery
- [ ] Automated error recovery
- [ ] Comprehensive monitoring and alerting

## Conclusion

The hybrid Lambda + EC2 architecture provides the best solution for your requirements:

- **Maintains cost efficiency** for fast operations
- **Enables unlimited processing time** for visual capture
- **Preserves serverless benefits** where appropriate
- **Provides flexibility** for future enhancements

This approach allows you to integrate your comprehensive visual tweet processing pipeline while maintaining the proven reliability and cost-effectiveness of your current serverless architecture. 