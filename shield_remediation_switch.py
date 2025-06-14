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
        
        # Find protection for this resource
        protections = shield_client.list_protections(ResourceArns=[resource_arn])
        if not protections['Protections']:
            return {
                'statusCode': 404,
                'body': f'No Shield protection found for distribution {cloudfront_dist_id}'
            }
            
        protection_id = protections['Protections'][0]['Id']
        
        # Check current automatic response configuration
        auto_response = shield_client.describe_application_layer_automatic_response_configuration(
            ResourceArn=protection_id
        )
        
        current_action = auto_response['ApplicationLayerAutomaticResponseConfiguration']['Action']
        logger.info(f"Current Shield protection action: {current_action}")
        
        if not enable_block:
            logger.info("ENABLE_BLOCK is false - would change to BLOCK but skipping due to flag")
            return {
                'statusCode': 200,
                'body': f'Current mode: {current_action}, ENABLE_BLOCK=false - no changes made'
            }
            
        # Switch to BLOCK if currently in COUNT or DISABLED mode
        if current_action.get('Count') or not any(current_action.values()):
            # Currently in COUNT mode - switch to BLOCK
            shield_client.update_application_layer_automatic_response_configuration(
                ResourceArn=protection_id,
                ApplicationLayerAutomaticResponseConfiguration={
                    'Action': {
                        'Block': {},
                        'Count': None
                    }
                }
            )
            logger.info(f"Successfully updated protection {protection_id} (CloudFront {cloudfront_dist_id}) to BLOCK mode")
            return {
                'statusCode': 200,
                'body': f'Successfully updated CloudFront {cloudfront_dist_id} to BLOCK mode'
            }
        else:
            logger.info(f"Protection {protection_id} (CloudFront {cloudfront_dist_id}) is already in BLOCK mode")
            return {
                'statusCode': 200,
                'body': f'CloudFront {cloudfront_dist_id} already in BLOCK mode - no changes made'
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