<h1> <img src="build/image/gear_logo.png"> DevOps /etc</h1>

### Automatic deployment of a secure, AWS S3-backed and CloudFront CDN-distributed, static website using Python, Boto3 and CloudFormation.

A site built with static site generator, Hugo, hosted on AWS S3, and served up via the AWS CloudFront CDN. This project, built with the AWS SDK for Python (Boto3) and CloudFormation, allows you to quickly deploy the requisite AWS infrastructure needed to host a secure, static website, serve it up fast, and spend relatively little money in the process.

Blog post with additional information can be found at:  [DevOpsEtc.com/post/s3-cf-static-site](https://DevOpsEtc.com/post/s3-cf-static-site)

**Known Issues:**
- None

**Road Map:**
- Add instructions for Hugo static generator install and config
- Add Python function to create local/remote repos and push initial build to remote
- Add CloudFormation resources for CI/CD workflow (CodeCommit, CodePipeline, CodeBuild, CodeDeploy)
- Add CloudWatch billing alerts

**Contributing:**
1. Review open issues
2. Open new issue to start discussion about a feature request or bug
3. Fork the repo, make changes, then send pull request to dev branch
