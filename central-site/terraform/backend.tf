# Terraform backend configuration for S3
# Note: You need to create the backend S3 bucket and DynamoDB table manually first
# or use a separate Terraform configuration to create them

terraform {
  backend "s3" {
    bucket       = "tfstates-059247592146-s3bucket"
    key          = "judi-expert/terraform.tfstate"
    region       = "eu-west-1"
    use_lockfile = true
    encrypt      = true
  }
}
