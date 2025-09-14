# TNF App AWS Deployment Guide

This guide will help you deploy your TNF application to AWS using ECS Fargate, providing a scalable and managed containerized deployment.

## 🏗️ Infrastructure Overview

The deployment includes:
- **VPC** with public/private subnets across 2 AZs
- **Application Load Balancer** for high availability  
- **ECS Fargate** cluster for containerized deployment
- **CloudWatch** for logging and monitoring
- **Systems Manager Parameter Store** for secure secret management
- **ECR** for Docker image storage

## 📋 Prerequisites

1. **AWS CLI** installed and configured
   ```bash
   aws configure
   ```

2. **Docker** installed and running

3. **Required API Keys** ready:
   - GROQ API Key
   - OpenAI API Key  
   - Anthropic API Key
   - Stripe API Key
   - Salesforce credentials (username, password, security token)

## 🚀 Quick Deployment

1. **Navigate to the TNF directory:**
   ```bash
   cd tnf/
   ```

2. **Run the deployment script:**
   ```bash
   ./deploy.sh
   ```

3. **Follow the prompts** to set up your API keys in Parameter Store

4. **Wait for deployment** (typically 5-10 minutes)

## 🔧 Manual Deployment Steps

If you prefer manual deployment or need to customize:

### Step 1: Create ECR Repository
```bash
aws ecr create-repository --repository-name tnf-chatbot --region us-east-1
```

### Step 2: Build and Push Docker Image
```bash
# Get login token
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Build and tag image
docker build -t tnf-chatbot .
docker tag tnf-chatbot:latest YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/tnf-chatbot:latest

# Push image
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/tnf-chatbot:latest
```

### Step 3: Store Secrets in Parameter Store
```bash
aws ssm put-parameter --name '/tnf/groq-api-key' --value 'YOUR_GROQ_API_KEY' --type 'SecureString'
aws ssm put-parameter --name '/tnf/openai-api-key' --value 'YOUR_OPENAI_API_KEY' --type 'SecureString'
aws ssm put-parameter --name '/tnf/anthropic-api-key' --value 'YOUR_ANTHROPIC_API_KEY' --type 'SecureString'
aws ssm put-parameter --name '/tnf/stripe-api-key' --value 'YOUR_STRIPE_API_KEY' --type 'SecureString'
aws ssm put-parameter --name '/tnf/salesforce-username' --value 'YOUR_SALESFORCE_USERNAME' --type 'SecureString'
aws ssm put-parameter --name '/tnf/salesforce-password' --value 'YOUR_SALESFORCE_PASSWORD' --type 'SecureString'
aws ssm put-parameter --name '/tnf/salesforce-security-token' --value 'YOUR_SALESFORCE_SECURITY_TOKEN' --type 'SecureString'
```

### Step 4: Deploy Infrastructure
```bash
aws cloudformation deploy \
    --template-file aws/cloudformation-template.yaml \
    --stack-name tnf-chatbot-stack \
    --parameter-overrides \
        AppName=tnf-chatbot \
        DockerImage=YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/tnf-chatbot:latest \
    --capabilities CAPABILITY_IAM \
    --region us-east-1
```

## 🔍 Monitoring and Troubleshooting

### View Application Logs
```bash
aws logs tail /ecs/tnf-chatbot --follow --region us-east-1
```

### Check ECS Service Status
```bash
aws ecs describe-services --cluster tnf-chatbot-cluster --services tnf-chatbot-service --region us-east-1
```

### Update Application
To deploy updates:
1. Build and push new Docker image with updated tag
2. Update ECS service to use new image:
```bash
aws ecs update-service --cluster tnf-chatbot-cluster --service tnf-chatbot-service --force-new-deployment
```

## 💰 Cost Optimization

- **Fargate Pricing**: Based on vCPU and memory usage
- **Load Balancer**: ~$16/month for ALB
- **Data Transfer**: Charges apply for outbound traffic
- **CloudWatch**: Minimal charges for log storage

**Estimated Monthly Cost**: $30-50 for light usage

## 🔒 Security Features

- Secrets stored in encrypted Parameter Store
- Private subnets for ECS tasks
- Security groups restrict access
- HTTPS support (add SSL certificate ARN)
- IAM roles with least privilege

## 🛠️ Customization Options

### Custom Domain with HTTPS
1. Get SSL certificate in AWS Certificate Manager
2. Update CloudFormation with certificate ARN:
```bash
aws cloudformation update-stack \
    --stack-name tnf-chatbot-stack \
    --use-previous-template \
    --parameters ParameterKey=CertificateArn,ParameterValue=arn:aws:acm:region:account:certificate/xxx
```

### Auto Scaling
Add auto scaling to handle traffic spikes:
```bash
aws application-autoscaling register-scalable-target \
    --service-namespace ecs \
    --scalable-dimension ecs:service:DesiredCount \
    --resource-id service/tnf-chatbot-cluster/tnf-chatbot-service \
    --min-capacity 1 \
    --max-capacity 10
```

## 🧹 Cleanup

To remove all resources:
```bash
aws cloudformation delete-stack --stack-name tnf-chatbot-stack --region us-east-1
aws ecr delete-repository --repository-name tnf-chatbot --force --region us-east-1
```

## 📞 Support

For deployment issues:
1. Check CloudWatch logs for errors
2. Verify all API keys are set correctly in Parameter Store
3. Ensure Docker image builds successfully locally
4. Review ECS service events for deployment failures

## 🔄 CI/CD Integration

For automated deployments, integrate with:
- **GitHub Actions**: Use provided workflow files
- **AWS CodePipeline**: Automated build and deploy
- **Jenkins**: Custom pipeline integration