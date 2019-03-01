# Quick Start Guide - Rubrik CloudCluster AWS Encryption

## Installation

1. Install [python 3.6.1 and pip](http://docs.python-guide.org/en/latest/starting/installation/) or higher
2. Install [boto3](https://boto3.readthedocs.io/en/latest/guide/quickstart.html)
3. Downlaod and save the [cc_encyrpt_aws](https://github.com/rubrik-devops/cc_encrypt_aws) script from GitHub to a working directory.

## Usage Instructions

To use the script run `python3 cc_encypt_aws.py [options]`. Specify the appopriate options for the instance. These include:

```text
usage: cc_encrypt_aws.py [-h] --instanceid IID --disksize DS
                         [--clientmasterkey CMK] [--profile PROFILE]
                         [--stopinstance] [--dryrun]

Encrypt disks for Rubrik Cloud Cluster in AWS

required arguments:

  --instanceid IID, -i IID
                        AWS Instance ID for Rubrik Cloud Cluster node.
  --disksize DS, -d DS  Disk size for disks in nodes. Minimum 512GiB, Maximum
                        2048 GiB. Default is 1024 days.

optional arguments:
  -h, --help            show this help message and exit
  --clientmasterkey CMK, -k CMK
                        Customer Master Key to encrypt volumes. If this is not
                        specified the AWS default key is used.
  --profile PROFILE, -p PROFILE
                        AWS Profile to use. If left blank the default profile
                        will be used.
  --stopinstance, -s    Stop instances if they are running.
  --dryrun, -D          Dry run only. Do not encrypt disks. Default is false.
```

## Future

- Add these functions depending on necessity
  - Include capability to run one script and act on a whole cluster.
  - Add ability to encrypt a running bootstrapped cluster.
  - Support use with CloudFormation
- Clean up the code
  - Break out into multiple files to support CloudFormation integration
  - Standardize methods used in the script
