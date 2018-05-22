<h1> <img src="img/logo.png"> DevOps /etc</h1>

### Static Site on AWS S3 and CloudFront CDN

A static site hosted on an S3 bucket, and served up fast via the CloudFront CDN. This project consists of three parts. Part one, deploys AWS infrastructure and supporting services using the AWS SDK for Python (Boto3) and CloudFormation, resulting in quick builds, updates and tear-downs. Part two, prepares a development environment, including repo,

security
integrated with part three

with a cloned repo,  

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
