import boto3
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    shield_client = boto3.client('shield')
    cloudfront_dist_id = os.environ.get('DISTRIBUTION_ID')
    enable_block = os.environ.get('ENABLE_BLOCK', 'true').lower() == 'true'
    
    if not cloudfront_dist_id:
        logger.error("DISTRIBUTION_ID environment variable not set")
        return {
            'statusCode': 400,
            'body': 'Missing required environment variable: DISTRIBUTION_ID'
        }

    try:
        # Construct CloudFront ARN
        resource_arn = f"arn:aws:cloudfront::{context.invoked_function_arn.split(':')[4]}:distribution/{cloudfront_dist_id}"
        
        # Find protection for this resource with proper filters
        protections = shield_client.list_protections(
            InclusionFilters={
                'ResourceArns': [resource_arn],
                'ResourceTypes': ['CLOUDFRONT_DISTRIBUTION']
            }
        )
        # Check if no protections exist
        if not protections['Protections']:
            logger.error(f"No protections found for distribution {cloudfront_dist_id}")
            return {
                'statusCode': 404,
                'body': f'No Shield protection found for distribution {cloudfront_dist_id}'
            }
            
        # Check if multiple protections exist
        if len(protections['Protections']) > 1:
            logger.error(f"Multiple protections found for distribution {cloudfront_dist_id}")
            return {
                'statusCode': 400,
                'body': f'Multiple protections found for distribution {cloudfront_dist_id} - expected exactly one'
            }
            
        protection_id = protections['Protections'][0]['Id']
        
        # Get current protection details using correct API
        protection = shield_client.describe_protection(
            ProtectionId=protection_id,
            ResourceArn=resource_arn
        )
        
        auto_response_config = protection['Protection']['ApplicationLayerAutomaticResponseConfiguration']
        current_status = auto_response_config['Status']
        current_action = auto_response_config['Action']
        logger.info(f"Current Shield protection status: {current_status}, action: {current_action}")
        
        if not enable_block:
            logger.info("ENABLE_BLOCK is false - would change to BLOCK but skipping due to flag")
            return {
                'statusCode': 200,
                'body': f'Current status: {current_status}, action: {current_action}, ENABLE_BLOCK=false - no changes made'
            }
            
        # Handle automatic response configuration
        if current_status == 'DISABLED':
            # Enable automatic response in BLOCK mode
            shield_client.enable_application_layer_automatic_response(
                ResourceArn=resource_arn,
                Action={'Block': {}}
            )
            logger.info(f"Enabled automatic response for protection {protection_id} (CloudFront {cloudfront_dist_id}) in BLOCK mode")
            return {
                'statusCode': 200,
                'body': f'Enabled automatic response for CloudFront {cloudfront_dist_id} in BLOCK mode'
            }
        elif current_status == 'ENABLED':
            # Check action type by looking at dictionary keys
            if 'Block' in current_action:
                # Already in BLOCK mode - return without making changes
                logger.info(f"Protection {protection_id} (CloudFront {cloudfront_dist_id}) is already in BLOCK mode")
                return {
                    'statusCode': 200,
                    'body': f'CloudFront {cloudfront_dist_id} already in BLOCK mode - no changes made'
                }
            elif 'Count' in current_action:
                # Currently in COUNT mode - update to BLOCK
                shield_client.update_application_layer_automatic_response_configuration(
                    ResourceArn=resource_arn,
                    Action={'Block': {}}
                )
                logger.info(f"Updated protection {protection_id} (CloudFront {cloudfront_dist_id}) to BLOCK mode")
                return {
                    'statusCode': 200,
                    'body': f'Updated CloudFront {cloudfront_dist_id} to BLOCK mode'
                }
            else:
                # Unknown action - log warning but don't make changes
                logger.error(f"Unknown action for ENABLED protection {protection_id} (CloudFront {cloudfront_dist_id}): {current_action}")
                return {
                    'statusCode': 500,
                    'body': f'Unknown action - no changes made for CloudFront {cloudfront_dist_id}'
                }
        else:
            # Unknown state - log error and return 500
            logger.error(f"Unknown protection state for {protection_id} (CloudFront {cloudfront_dist_id}): status={current_status}, action={current_action}")
            return {
                'statusCode': 500,
                'body': f'Unknown protection state: status={current_status}, action={current_action}'
            }
            
    except shield_client.exceptions.ResourceNotFoundException:
        logger.error("Specified protection not found")
        return {
            'statusCode': 404,
            'body': 'Protection not found'
        }
    except Exception as e:
        logger.error(f"Error updating protection: {str(e)}")
        return {
            'statusCode': 500,
            'body': f'Error: {str(e)}'
        }