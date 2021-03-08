# Lambda function to get releases data

### How it works

The functions lists all the k8-proxy GitHub repos, and releases data, marges it to and extracts out the following information;

- Repo name
- Repo URL
- Release name
- Release tag
- Date & Time of the released

This information is then converted into a json file and stored into an s3 bucket, triggered by a github webhook to an AWS API Gateway.

