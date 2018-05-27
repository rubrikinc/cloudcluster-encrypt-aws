import sys
import boto3
import botocore
from datetime import datetime, timedelta, timezone
import argparse
import pprint
import logging

product = "Rubrik Cloud Cluster"
defaultdisksize = 1024
dryrun = False

parser = argparse.ArgumentParser(description='Encrypt disks for {product} in AWS'.format(product=product))
parser.add_argument('--instanceid', '-i', metavar='IID', required=True,
                    help='AWS Instance ID for {product} node.'.format(product=product))
parser.add_argument('--disksize', '-d', metavar='DS', type=int, default=defaultdisksize, required=True,
                    help='Disk size for disks in nodes. Minimum 512GiB, Maximum 2048 GiB. Default is {defaultdisksize} days.'.format(
                        product=product,
                        defaultdisksize=defaultdisksize))
parser.add_argument('--clientmasterkey', '-k', action='store', metavar='CMK',
                    help='Customer Master Key to encrypt volumes. If this is not specified the AWS default key is used.')
parser.add_argument('--profile', '-p', metavar='PROFILE',required=False,
                    help='AWS Profile to use. If left blank the default profile will be used.')
parser.add_argument('--stopinstance', '-s', action='store_true',
                    help='Stop instances if they are running.')
parser.add_argument('--dryrun', '-D', action='store_true',
                    help='Dry run only. Do not encrypt disks. Default is false.')
args = parser.parse_args()

def setup_custom_logger(name):
    formatter = logging.Formatter(fmt='%(asctime)s %(levelname)-8s %(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S')
    handler = logging.FileHandler(__file__ + '.' + instanceid + '.log', mode='w')
    handler.setFormatter(formatter)
    screen_handler = logging.StreamHandler(stream=sys.stdout)
    screen_handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    logger.addHandler(screen_handler)
    return logger

def encrypt_root_volume():
    logger.info('Encrypting root disk of instance {instanceid}'.format(instanceid=instanceid))

    logger.info('Creating snapshot of volume {}'.format(original_root_volume))
    snapshot = ec2.create_snapshot(
        VolumeId=original_root_volume,
        Description='Unencrypted Snapshot of volume {}'.format(original_root_volume),
        DryRun=dryrun
    )
    
    try:
        waiter_snapshot_complete.wait(
            SnapshotIds=[
                snapshot.id,
            ],
            DryRun=dryrun
        )
    except botocore.exceptions.WaiterError as e:
        if not dryrun:
            snapshot.delete(DryRun=dryrun)
            logger.error('Snapshot of volume {VolumeID} failed for instance {instanceid}'.format(
                    VolumeID=original_root_volume,
                    instanceid=instanceid))
            logger.error('{}'.format(e))
            sys.exit(1)

    if cmk:
    # Use custom key
        logger.info('Creating encrypted copy of root volume snapshot using client master key...')
        snapshot_encrypted_dict = snapshot.copy(
            SourceRegion=session.region_name,
            Description='Encrypted copy of snapshot #{}'.format(snapshot.id),
            KmsKeyId=cmk,
            Encrypted=True,
            DryRun=dryrun
        )
    else:
    # Use default key
        logger.info('Creating encrypted copy of root volume snapshot using AWS default key...')
        snapshot_encrypted_dict = snapshot.copy(
            SourceRegion=session.region_name,
            Description='Encrypted copy of snapshot {}'.format(snapshot.id),
            Encrypted=True,
            DryRun=dryrun
        )
    
    snapshot_encrypted = ec2.Snapshot(snapshot_encrypted_dict['SnapshotId'])
    
    try:
        waiter_snapshot_complete.wait(
            SnapshotIds=[
                snapshot_encrypted.id,
            ],
            WaiterConfig={
                'Delay': 15,
                'MaxAttempts': 360
            },
            DryRun=dryrun
        )
    except botocore.exceptions.WaiterError as e:
        if not dryrun:
            snapshot.delete(DryRun=dryrun)
            snapshot_encrypted.delete(DryRun=dryrun)
            logger.error('Failed to copy snapshot {snapshotid} to encrypted snapshot for instance {instanceid}'.format(
                snapshotid=snapshot.id,
                instanceid=instanceid
                ))
            logger.error('{}'.format(e))
            sys.exit(1)


    logger.info('Creating encrypted volume from snapshot...')
    volume_encrypted = ec2.create_volume(
        SnapshotId=snapshot_encrypted.id,
        AvailabilityZone=instance.placement['AvailabilityZone'],
        DryRun=dryrun
    )

    logger.info('Detaching unencrypted root volume {} from instance {instanceid}'.format(
        original_root_volume,
        instanceid=instanceid))

    instance.detach_volume(
        VolumeId=original_root_volume,
        Device=instance.root_device_name,
        DryRun=dryrun
    )

    try:
        waiter_volume_available.wait(
            VolumeIds=[
                volume_encrypted.id,
            ],
            DryRun=dryrun
        )
    except botocore.exceptions.WaiterError as e:
        if not dryrun:
            snapshot.delete(DryRun=dryrun)
            snapshot_encrypted.delete(DryRun=dryrun)
            volume_encrypted.delete(DryRun=dryrun)
            logger.error('Failed to detach encrypted volume {volume_encrypted} to instance {instanceid}'.format(
                volume_encrypted=volume_encrypted.id,
                instanceid=instanceid))
            logger.error('{}'.format(e))
            sys.exit(1)


    logger.info('Attaching encrypted volume {} to instance {instanceid} as device {device}'.format(
        volume_encrypted.id,
        instanceid=instanceid,
        device=instance.root_device_name))
    
    instance.attach_volume(
        VolumeId=volume_encrypted.id,
        Device=instance.root_device_name,
        DryRun=dryrun
    )

    logger.info('Reapplying properties to device {}'.format(instance.root_device_name))
    instance.modify_attribute(
        BlockDeviceMappings=[
            {
                'DeviceName': instance.root_device_name,
                'Ebs': {
                    'DeleteOnTermination': original_root_volume_termination,
                },
            },
        ],
        DryRun=dryrun
    )

    logger.info('Cleaning up intermediary snapshots and original root volume...')
    
    # Delete snapshots and original volume
    snapshot.delete(DryRun=dryrun)
    snapshot_encrypted.delete(DryRun=dryrun)
    ec2.Volume(original_root_volume).delete(DryRun=dryrun)


def encrypt_data_volumes():

    logger.info('Replacing data disks with encrypted disks for instance {})'.format(instanceid))
    logger.info('Removing data disks from instance {instanceid}...'.format(instanceid=instanceid))

    for v in instancevolumes:
        original_data_volume_device_name = v['DeviceName']
        if original_data_volume_device_name in newdatadevicemap:
            ebs = v.get('Ebs')
            original_data_volume = ebs.get('VolumeId')
            original_data_volume_termination = ebs.get('DeleteOnTermination')
            volume = ec2.Volume(original_data_volume)
            encrypted_data_volume_device_name = newdatadevicemap[original_data_volume_device_name]

            logger.info('Detaching unencrypted data volume {} on device {original_data_volume_device_name}...'.format(
                original_data_volume,
                original_data_volume_device_name=original_data_volume_device_name))
            instance.detach_volume(
                VolumeId=original_data_volume,
                DryRun=dryrun
            )
            if cmk:
                logger.info('Creating encrypted data volume using user provided key...')
                encrypted_data_volume = ec2.create_volume(
                    AvailabilityZone=instance.placement['AvailabilityZone'],
                    Encrypted=True,
                    KmsKeyId=cmk,
                    Size=disksize,
                    VolumeType='st1',
                    DryRun=dryrun
                )
            else:
                logger.info('Creating encrypted data volume using default AWS key...')
                encrypted_data_volume = ec2.create_volume(
                    AvailabilityZone=instance.placement['AvailabilityZone'],
                    Encrypted=True,
                    Size=disksize,
                    VolumeType='st1',
                    DryRun=dryrun
                )
            
            try:
                waiter_volume_available.wait(
                    VolumeIds=[
                        encrypted_data_volume.id,
                    ],
                    DryRun=dryrun
                )
            except botocore.exceptions.WaiterError as e:
                if not dryrun:
                    encrypted_data_volume.delete(DryRun=dryrun)
                    instance.attach_volume(
                        VolumeId=original_data_volume,
                        Device=original_data_volume_device_name,
                        DryRun=dryrun
                    )
                    logger.error('Failed to create new encrypted volume for device {newdevice} for instance {instanceid}'.format(
                        newdevice=encrypted_data_volume_device_name,
                        instanceid=instanceid
                        ))
                    logger.error('{}'.format(e))
                    sys.exit(1)

            logger.info('Attaching encrypted volume {encrypted_data_volume} to instance {instanceid} as device {device}...'.format(
                instanceid=instanceid,
                device=encrypted_data_volume_device_name,
                encrypted_data_volume=encrypted_data_volume.id
                ))
            instance.attach_volume(
                VolumeId=encrypted_data_volume.id,
                Device=encrypted_data_volume_device_name,
                DryRun=dryrun
            )
            logger.info('Reapplying properties to new device {}'.format(encrypted_data_volume_device_name))
            instance.modify_attribute(
                BlockDeviceMappings=[
                    {
                        'DeviceName': encrypted_data_volume_device_name,
                        'Ebs': {
                            'DeleteOnTermination': original_data_volume_termination,
                        },
                    },
                ],
                DryRun=dryrun
            )

            logger.info('Deleting unencrypted volume {original_data_volume} from instance {instanceid}'.format(
                original_data_volume=original_data_volume,
                instanceid=instanceid
                ))
            volume.delete(DryRun=dryrun)

dryrun = args.dryrun
stopinstance = args.stopinstance
instanceid = args.instanceid
disksize = args.disksize
cmk = args.clientmasterkey

if args.profile:
# Create custom session
    logger.info('Using profile {}'.format(args.profile))
    session = boto3.session.Session(profile_name=args.profile)
else:
# Use default session
    session = boto3.session.Session()

newdatadevicemap = {'/dev/sdb': '/dev/sde', '/dev/sdc': '/dev/sdf', '/dev/sdd': '/dev/sdg'}

if disksize < 512 or disksize > 2048:
    logger.error ('The disk size: {disksize} is out of range. Disk size must be between 512 and 4096 GIB.'.format(disksize=disksize))
    exit(1)

ec2 = boto3.resource('ec2')
client = boto3.client('ec2')
waiter_instance_exists = client.get_waiter('instance_exists')
waiter_instance_stopped = client.get_waiter('instance_stopped')
waiter_instance_running = client.get_waiter('instance_running')
waiter_snapshot_complete = client.get_waiter('snapshot_completed')
waiter_volume_available = client.get_waiter('volume_available')
logger = setup_custom_logger('cc_encrypt')

logger.info('Encrypting disks for Rubrik Cloud Cluster node with instance ID: {instanceid}'.format(instanceid=instanceid))

logger.info('Verifying instance {}...'.format(instanceid))
instance = ec2.Instance(instanceid)

try:
    waiter_instance_exists.wait(
        InstanceIds=[
            instanceid,
        ],
        DryRun=dryrun
    )
except botocore.exceptions.WaiterError as e:
    if not dryrun:
        logger.error('Failed to validate instance {}'.format(instanceid))
        logger.error('{}'.format(e))
        sys.exit(1)


logger.info('Checking for existing encryption of instance {}...'.format(instanceid))

instancevolumes = [v for v in instance.block_device_mappings]
if instancevolumes:
    data_volume_encrypted = False
    for v in instancevolumes:
        if v['DeviceName'] == instance.root_device_name:
            ebs = v.get('Ebs')
            original_root_volume = ebs.get('VolumeId')
            original_root_volume_termination = ebs.get('DeleteOnTermination')
            root_volume_encrypted = ec2.Volume(original_root_volume).encrypted
        else:
            ebs = v.get('Ebs')
            original_data_volume = ebs.get('VolumeId')
            volume = ec2.Volume(original_data_volume)
            if volume.encrypted:
                data_volume_encrypted = volume.encrypted
                logger.warn('Data volume {} in instance {instanceid} is already encrypted'.format(
                    original_data_volume,
                    instanceid=instanceid
                    ))

if root_volume_encrypted:
    logger.warn('Root volume {} in instance {instanceid} is already encrypted'.format(
        original_root_volume,
        instanceid=instanceid
        ))

if root_volume_encrypted and data_volume_encrypted:
    logger.error('All volumes on instance {} encrypted. Nothing to do here.'.format(instanceid))
    sys.exit(1)

logger.info('Verifying that instance {instanceid} is stopped...'.format(instanceid=instanceid))

if stopinstance:
    logger.info('Stopping instance {instanceid}...'.format(instanceid=instanceid))
    instance_exit_states = [0, 32, 48]
    if instance.state['Code'] in instance_exit_states:
        logger.error('Instance is {} please make sure this instance is active.'.format(instance.state['Name']))
        sys.exit(1)

# Validate successful shutdown if it is running or stopping
    if instance.state['Code'] is 16:
        instance.stop(DryRun=dryrun)

    try:
        waiter_instance_stopped.wait(
            InstanceIds=[
                instanceid,
            ],
            DryRun=dryrun
        )
    except botocore.exceptions.WaiterError as e:
        if not dryrun:
            logger.error ('Instance {instanceid} is {state}'.format(
                instanceid=instanceid,
                state=instance.state['Name']))
            logger.error ('Stop instance {instanceid} before procceding.'.format(instanceid=instanceid))
            sys.exit(1)

if root_volume_encrypted:
    logger.warn('Root volume of instance {} is already encrypted. Skipping...'.format(instanceid))
else:
    encrypt_root_volume()

if data_volume_encrypted:
   logger.warn('Some or all data volumes are already encrypted. Skiping...')
else:
    encrypt_data_volumes()

if stopinstance and instance.state['Code'] is 80:
    logger.info('Restarting instance {}...'.format(instanceid))
    instance.start(DryRun=dryrun)

    try:
        waiter_instance_running.wait(
            InstanceIds=[
                instanceid
            ],
            DryRun=dryrun
        )
    except botocore.exceptions.WaiterError as e:
        if not dryrun:
            logger.error('Instance {} failed to start'.format(instanceid))
            logger.error('{}'.format(e))
            sys.exit(1)

logger.info('Encryption complete.')
