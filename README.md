<h1> <img src="image/logo.png"> DevOps /etc</h1>

### Automatic deployment of a secure, AWS S3-backed and CloudFront CDN-distributed, static website using Python, Boto3 and CloudFormation.

Do you like setting up and maintaining the server that runs your blog? Do you like how slow your pages load from the CMS's database? How about how much money you're spending on hosting?! I didn't like any of these things, so I switched from a CMS to a statically generated website and migrated to an AWS S3 bucket served up by a CDN distribution using AWS CloudFront. This project, built with the AWS SDK for Python (Boto3) and CloudFormation, allows you to quickly deploy the requisite AWS infrastructure needed to host your blog inexpensively and to serve it up fast.

Code walkthrough and additional information can be found at:  [DevOpsEtc.com/post/s3-cf-static-site](https://DevOpsEtc.com/post/s3-cf-static-site)

**Features/Benefits:**
  * CloudFormation for quicker provisioning of repeatable and updatable AWS resources
  * CloudFront CDN distribution for faster pages loads
  * S3 bucket for managed server setup/maintenance/availability; autoscales as needed; no updating
  * ACM SSL/TLS certificate for secure page loading via HTTPS

**Prerequisites:**
  * MacOS High Sierra (should work on other versions and Linux too, but YMMV)
  * Python 3: $ brew install python3
  * GoAccess: $ brew install goaccess # optional visual web log analyzer
  * Python Modules: $ pip3 install awscli boto3 colorama (sudo may be needed for elevated privileges)
  * Amazon Web Services account (if new to AWS, there's a year long free-tier plan available)
  * AWS credentials: $ aws configure (paste in access keys from AWS management console)
  * Custom domain name
  * AWS Route 53 hosted zone for your domain name
  * Valid email@your_domain_name that's a catch-all address (for certificate validation)

**Script Output Screenshot:**

  <p align="center"> <img src="image/output1.png"></p>

  <p align="center"> <img src="image/output2.png"></p>

**What Gets Provisioned:**
  * One ACM SSL/TLS certificate
  * One IAM group
  * One IAM group policy
  * One IAM user
  * Two S3 buckets
  * One CloudFront distribution
  * Two Route 53 DNS records
  * Region us-east-1 (for ACM certificate/CloudFront compatibility)

**Getting Started:**

    # Clone the repo on GitHub
    $ git clone https://github.com/DevOpsEtc/s3-cf-static-site ~/DevOpsEtc/s3-cf-static-site

    # Update domain name in ~/DevOpsEtc/s3-cf-static-site/deploy.py
    domain = 'devopsetc.com' # your bare domain name

    # Run script
    $ cd ~/DevOpsEtc/s3-cf-static-site && ./deploy.py

    # Update CloudFormation stack with template changes
    $ cd ~/DevOpsEtc/s3-cf-static-site && ./deploy.py
    $ U # enter after prompt: Update|Delete|Cancel (U|D|C)

    # Delete CloudFormation stack and rollback updates/initial launch resources
    $ cd ~/DevOpsEtc/s3-cf-static-site && ./deploy.py
    $ D # enter after prompt: Update|Delete|Cancel (U|D|C)

    # Invalidate objects from CloudFront edge caches
    $ dist_id=$(aws cloudfront list-distributions --query "DistributionList.Items[?contains(Aliases.Items, 'your_distro_alias')].Id" --output text) && aws cloudfront create-invalidation --distribution-id $dist_id --paths "/*"

    # Sync log files
    $ aws s3 sync s3://your_bucket-log ~/path/to/synced/logs

    # Visual log analysis in terminal
    $ gunzip -c ~/path/to/synced/logs/*.gz | goaccess

    # Visual log analysis in browser
    $ gunzip -c ~/path/to/synced/logs/*.gz | goaccess -a -o ~/path/to/synced/logs/report.html
    $ open ~/path/to/synced/logs/report.html

    # Automatically sync/parse/analyze logs; update path & bucket
    # Paste in terminal for single use or bashrc for reuse
    web_logs() {
      logs=$HOME/path/to/synced/logs
      aws s3 sync s3://your_bucket-log $logs/..
      [[ "$1" == "-t" ]] && gunzip -c $logs/*.gz | goaccess || gunzip -c $logs/*.gz | goaccess -a -o $logs/report.html; open $logs/report.html
    }
    $ web_logs # to view in browser
    $ web_logs -t # to view in terminal

    # List all S3 buckets
    $ aws s3 ls

    # List all objects in an S3 bucket
    $ aws s3 ls s3://your_bucket --recursive --human-readable --summarize

    # Remove an object from S3 bucket
    $ aws s3 rm s3://your_bucket/your_object

    # Remove all objects from S3 bucket
    $ aws s3 rm s3://your_bucket --recursive

    # Remove all objects except type from S3 bucket
    $ aws s3 rm s3://your_bucket --recursive --exclude "your_object_type"

    # Copy a file to S3 bucket or an object within bucket
    $ aws s3 cp ~/path/to/file s3://your_bucket

    # Move and/or rename an object from one path to another
    $ aws s3 mv s3://your_bucket/your_object s3://your_bucket/new_path/your_object

**Notes:**    
Running this script will launch an AWS CloudFormation stack that provisions, among other things, S3 buckets and CloudFront distributions, both of which incur minimal service fees... i.e. don't forget to delete the stack when it's no longer needed!

**Known Issues:**
- None

**Road Map:**
- Add static website boilerplate content
- Add instructions for Hugo static generator install and config
- Add Python function to create local/remote repos and push initial build to remote
- Add CloudFormation resources for CI/CD workflow (CodeCommit, CodePipeline, CodeBuild, CodeDeploy)

**Contributing:**
1. Review open issues
2. Open new issue to start discussion about a feature request or bug
3. Fork the repo, make changes, then send pull request to dev branch
