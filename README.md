# Rubrik CloudCluster AWS Encryption Script

The CC_Encrypt_AWS script is used to convert Rubrik Cloud Clusters on AWS from unencrypted disks to encrypted disks, thus providing encryption at rest for Cloud Cluster in AWS.

CC_Encrypt_AWS will encrypt both the root disk and the data disks of a freshly launched Rubrik Cloud Cluster. It is not supported to use this script on a bootstrapped Cloud Cluster at this time. The script will take 40 minutes to an hour to run per node. It can be run in parrallel on separate nodes to speed up the proccess. Each iteration of the script will run on a separate AWS instance.

# :blue_book: Documentation 

Here are some resources to get you started! If you find any challenges from this project are not properly documented or are unclear, please [raise an issue](https://github.com/rubrikinc/use-case-cloudcluster-encrypt-aws/issues/new/choose) and let us know! This is a fun, safe environment - don't worry if you're a GitHub newbie! :heart:

* [Quick Start Guide](/docs/QUICKSTART.md)

# :white_check_mark: Prerequisites

There are a few services you'll need in order to get this project off the ground:

* python 3.6.1+ and pip
* boto3

# :muscle: How You Can Help

We glady welcome contributions from the community. From updating the documentation to adding more Intents for Roxie, all ideas are welcome. Thank you in advance for all of your issues, pull requests, and comments! :star:

* [Contributing Guide](CONTRIBUTING.md)
* [Code of Conduct](CODE_OF_CONDUCT.md)

# :pushpin: License

* [MIT License](LICENSE)

# :point_right: About Rubrik Build

We encourage all contributors to become members. We aim to grow an active, healthy community of contributors, reviewers, and code owners. Learn more in our [Welcome to the Rubrik Build Community](https://github.com/rubrikinc/welcome-to-rubrik-build) page.
