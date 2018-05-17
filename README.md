<h1> <img src="build/img/logo.png"> DevOps /etc</h1>

### Static Website on AWS S3 served by CloudFront CDN

A static website hosted on an S3 bucket and served up fast via the CloudFront CDN. This project initially focuses on the deployment of infrastructure and uses the AWS SDK for Python (Boto3) and CloudFormation for quick builds, updates and tear-downs of infrastructure, security policies, logging and encryption. It will be updated soon with CI/CD workflow.

Blog post with additional information can be found at:  [https://devopsetc.com/post/aws-s3-static-website/](https://devopsetc.com/post/aws-s3-static-website/)

**Known Issues:**
- None

**Road Map:**
- Add CloudFormation resources for CI/CD workflow (CodeCommit, CodePipeline, CodeBuild, CodeDeploy)
- Add CloudWatch billing alerts

**Contributing:**
1. Review open issues
2. Open new issue to start discussion about a feature request or bug
3. Fork the repo, make changes, then send pull request to dev branch
