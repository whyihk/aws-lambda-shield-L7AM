# AWS Lambda Shield Remediation Switch

A Lambda function that manages AWS Shield Application Layer Automatic Response configuration for CloudFront distributions, switching between COUNT and BLOCK modes based on environment configuration.

## Features

- Switches from COUNT to BLOCK modes
- Validates protection status before making changes
- Comprehensive error handling with detailed logging
- Environment variable controlled behavior

## Requirements

- AWS Shield Advanced subscription
- CloudFront distribution protected by Shield
- IAM permissions for Shield operations (see below)
- Python 3.8+ runtime

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DISTRIBUTION_ID` | Yes | - | CloudFront distribution ID to manage |
| `ENABLE_BLOCK` | No | "true" | Set to "false" to skip switching to BLOCK mode |

## Detailed Function Behavior

1. **Initialization**:
   - Validates required environment variables
   - Sets up logging with INFO level

2. **Protection Lookup**:
   - Constructs CloudFront ARN from distribution ID
   - Lists protections with exact ARN and type filters
   - Validates exactly one protection exists

3. **Status Check**:
   - Gets current automatic response configuration
   - Logs current status (ENABLED/DISABLED) and action (COUNT/BLOCK)

4. **Mode Management**:
   - **DISABLED**: Enables automatic response in BLOCK mode
   - **ENABLED (COUNT)**: Updates to BLOCK mode
   - **ENABLED (BLOCK)**: No changes needed
   - **ENABLED (Unknown)**: Logs error and returns 500
   - **ENABLE_BLOCK=false**: Skips all mode changes

## Error Handling

| Error Case | Status Code | Response |
|------------|-------------|----------|
| Missing DISTRIBUTION_ID | 400 | Error message |
| Protection not found | 404 | Error message |
| Multiple protections | 400 | Error message |
| Unknown state/action | 500 | Error message |
| AWS API errors | 500 | Error details |

## IAM Policy Requirements

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "shield:ListProtections",
        "shield:DescribeProtection",
        "shield:EnableApplicationLayerAutomaticResponse", 
        "shield:UpdateApplicationLayerAutomaticResponse"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

## Deployment

1. Package the function:
```bash
zip function.zip shield_remediation_switch.py
```

2. Create Lambda with:
- Python 3.8+ runtime
- 128MB memory (minimum)
- 1 minute timeout
- Above IAM policy
- Environment variables set

3. Recommended triggers:
- CloudWatch Events for scheduled execution
- SNS for on-demand invocation

## Monitoring

The function emits detailed CloudWatch logs including:
- Configuration validation results
- Protection status before/after changes
- Any errors encountered
- Execution metrics (duration, memory used)

## Example Use Cases

1. **Emergency Block Mode**:
   - Trigger manually during attacks to switch from COUNT to BLOCK

2. **Scheduled Testing**:
   - Run weekly to verify protection status

3. **Automated Response**:
   - Chain with GuardDuty or Shield alerts

## Testing

Test scenarios should cover:
- All protection states (ENABLED/DISABLED)
- All action types (COUNT/BLOCK/Unknown)
- Error conditions (missing vars, no protection, etc)
- Environment variable combinations
