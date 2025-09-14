#!/bin/bash

# TNF App AWS Deployment Script
set -e

# Configuration
STACK_NAME="tnf-chatbot-stack"
REGION="us-east-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPOSITORY="tnf-chatbot"
IMAGE_TAG="latest"
APP_NAME="tnf-chatbot"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI not found. Please install it first."
        exit 1
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker not found. Please install it first."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials not configured. Please run 'aws configure' first."
        exit 1
    fi
    
    print_status "Prerequisites check passed ✓"
}

# Function to create ECR repository
create_ecr_repository() {
    print_status "Creating ECR repository..."
    
    # Check if repository exists
    if aws ecr describe-repositories --repository-names $ECR_REPOSITORY --region $REGION &> /dev/null; then
        print_status "ECR repository $ECR_REPOSITORY already exists"
    else
        aws ecr create-repository --repository-name $ECR_REPOSITORY --region $REGION
        print_status "ECR repository $ECR_REPOSITORY created ✓"
    fi
}

# Function to build and push Docker image
build_and_push_image() {
    print_status "Building and pushing Docker image..."
    
    # Get ECR login token
    aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com
    
    # Build image
    docker build -t $ECR_REPOSITORY .
    
    # Tag image
    docker tag $ECR_REPOSITORY:$IMAGE_TAG $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG
    
    # Push image
    docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG
    
    print_status "Docker image built and pushed ✓"
}

# Function to store secrets in Parameter Store
store_secrets() {
    print_status "Setting up secrets in AWS Systems Manager Parameter Store..."
    print_warning "You need to manually set your API keys in Parameter Store:"
    
    echo ""
    echo "Run these commands with your actual API keys:"
    echo ""
    echo "aws ssm put-parameter --name '/tnf/groq-api-key' --value 'YOUR_GROQ_API_KEY' --type 'SecureString' --region $REGION"
    echo "aws ssm put-parameter --name '/tnf/openai-api-key' --value 'YOUR_OPENAI_API_KEY' --type 'SecureString' --region $REGION"
    echo "aws ssm put-parameter --name '/tnf/anthropic-api-key' --value 'YOUR_ANTHROPIC_API_KEY' --type 'SecureString' --region $REGION"
    echo "aws ssm put-parameter --name '/tnf/stripe-api-key' --value 'YOUR_STRIPE_API_KEY' --type 'SecureString' --region $REGION"
    echo "aws ssm put-parameter --name '/tnf/salesforce-username' --value 'YOUR_SALESFORCE_USERNAME' --type 'SecureString' --region $REGION"
    echo "aws ssm put-parameter --name '/tnf/salesforce-password' --value 'YOUR_SALESFORCE_PASSWORD' --type 'SecureString' --region $REGION"
    echo "aws ssm put-parameter --name '/tnf/salesforce-security-token' --value 'YOUR_SALESFORCE_SECURITY_TOKEN' --type 'SecureString' --region $REGION"
    echo ""
    
    read -p "Press Enter after you have set up all the parameters..."
}

# Function to deploy CloudFormation stack
deploy_infrastructure() {
    print_status "Deploying CloudFormation stack..."
    
    # Update template with actual values
    sed -i.bak "s/YOUR_ACCOUNT_ID/$ACCOUNT_ID/g" aws/cloudformation-template.yaml
    sed -i.bak "s/YOUR_REGION/$REGION/g" aws/cloudformation-template.yaml
    
    # Deploy stack
    aws cloudformation deploy \
        --template-file aws/cloudformation-template.yaml \
        --stack-name $STACK_NAME \
        --parameter-overrides \
            AppName=$APP_NAME \
            DockerImage=$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG \
        --capabilities CAPABILITY_IAM \
        --region $REGION
    
    print_status "Infrastructure deployed ✓"
    
    # Get outputs
    LOAD_BALANCER_URL=$(aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerURL`].OutputValue' \
        --output text \
        --region $REGION)
    
    print_status "Application URL: $LOAD_BALANCER_URL"
}

# Function to check deployment status
check_deployment() {
    print_status "Checking deployment status..."
    
    # Get ECS service status
    CLUSTER_NAME=$(aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --query 'Stacks[0].Outputs[?OutputKey==`ECSCluster`].OutputValue' \
        --output text \
        --region $REGION)
    
    # Wait for service to be stable
    print_status "Waiting for ECS service to stabilize (this may take a few minutes)..."
    aws ecs wait services-stable \
        --cluster $CLUSTER_NAME \
        --services ${APP_NAME}-service \
        --region $REGION
    
    print_status "Deployment completed successfully! ✓"
}

# Function to clean up
cleanup() {
    print_status "Cleaning up temporary files..."
    
    # Restore original template
    if [[ -f aws/cloudformation-template.yaml.bak ]]; then
        mv aws/cloudformation-template.yaml.bak aws/cloudformation-template.yaml
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --region REGION     Set AWS region (default: us-east-1)"
    echo "  --stack-name NAME   Set CloudFormation stack name (default: tnf-chatbot-stack)"
    echo "  --help             Show this help message"
    echo ""
    echo "Example:"
    echo "  $0 --region us-west-2 --stack-name my-tnf-chatbot"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --region)
            REGION="$2"
            shift 2
            ;;
        --stack-name)
            STACK_NAME="$2"
            shift 2
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Main deployment flow
main() {
    print_status "Starting TNF App deployment to AWS..."
    print_status "Region: $REGION"
    print_status "Stack Name: $STACK_NAME"
    print_status "Account ID: $ACCOUNT_ID"
    
    check_prerequisites
    create_ecr_repository
    build_and_push_image
    store_secrets
    deploy_infrastructure
    check_deployment
    cleanup
    
    print_status "🎉 Deployment completed successfully!"
    print_status "Your TNF app is now running on AWS ECS with Fargate"
    
    # Show final information
    LOAD_BALANCER_URL=$(aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerURL`].OutputValue' \
        --output text \
        --region $REGION)
    
    echo ""
    echo "================================"
    echo "Deployment Information:"
    echo "================================"
    echo "Application URL: $LOAD_BALANCER_URL"
    echo "Stack Name: $STACK_NAME"
    echo "Region: $REGION"
    echo "ECR Repository: $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPOSITORY"
    echo ""
    echo "Next steps:"
    echo "1. Wait 2-3 minutes for the application to fully start"
    echo "2. Visit your application URL"
    echo "3. Monitor logs in CloudWatch: /ecs/$APP_NAME"
    echo ""
}

# Handle script interruption
trap cleanup EXIT

# Run main function
main