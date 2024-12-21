#
# Copyright (C) 2024 Tomislav Markoc, unpublished work. All rights reserved.
# Title and version: KubernetesCluster, version 2.0
#
# This is an unpublished work registered with the U.S. Copyright Office. As
# per https://www.copyright.gov/comp3/chap1900/ch1900-publication.pdf and
# https://www.govinfo.gov/content/pkg/USCODE-2011-title17/pdf/USCODE-2011-title17-chap1-sec101.pdf,
# public performance or a public display of a work "does not of itself
# constitute publication." Therefore, you only have permission to view this
# work in your web browser.
#
# You do not do not have permission to make copies by downloading files,
# copy and paste texts, use git clone, clone, fork, or use any other means
# to make copies of this work.
#
# If you make a copy of this work, you must delete it immediately.
#
# You do not have permission to modify this work or create derivative work.
#
# You do not have permission to use this work for any Artificial Intelligence
# (AI) purposes, including and not limited to training AI models or
# generative AI.
#
# By hosting this work you accept this agreement.
#
# In the case of conflict this licensing agreement takes precedence over all
# other agreements.
#
# In the case any provision of this licensing agreement is invalid or
# unenforceable, any invalidity or unenforceability will affect only that
# provision.
#
# ---------------------------------------------------------------------------
#
# Copyright statutory damages are up to $150,000 for willful infringement.
# Other damages may be more.
#
# This work was created without AI assistance. Therefore, the copyright
# status is clear.
#
# For info about this work or demo, contact me at tmarkoc@hotmail.com.

# This script creates the Azure VM on which the installation will be
# performed and then the VM image will be created.

import sys
import json
import requests

from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.resource.resources.models import DeploymentMode

from azure.mgmt.compute.models import SubResource
from azure.mgmt.compute.models import Image

from azure.core.exceptions import (
    HttpResponseError,
)

import install_utilities

print("####################################################################"
      "############\n"
      "CREATING VM IMAGE.\n"
      "####################################################################"
      "############")

with open("kube_settings.json", 'r') as settings_file:
    SETTINGS = json.load(settings_file)

CREDENTIALS_PATH = SETTINGS["CredentialsPath"]
with open(CREDENTIALS_PATH, 'r') as credentials_file:
    CREDENTIALS = json.load(credentials_file)

TENANT_ID = CREDENTIALS["TenantId"]
azure_credential = DefaultAzureCredential(
    exclude_interactive_browser_credential=False,
    interactive_browser_tenant_id = TENANT_ID)
SUBSCRIPTION_ID = CREDENTIALS["SubscriptionId"]

################################################################################
################################################################################
# Check if that vm image storage resource group already exists and that vm
# image does not exist. Create temporary resource group fro creation of this
# vm image.
################################################################################
################################################################################

# Verify that storage resource group exists.
VM_IMAGE_STORAGE_RESOURCE_GROUP_NAME = \
    SETTINGS["VMImageStorage"]["ResourceGroupName"]
resource_management_client = ResourceManagementClient(
    azure_credential, SUBSCRIPTION_ID)
if (resource_management_client.resource_groups.check_existence(
    VM_IMAGE_STORAGE_RESOURCE_GROUP_NAME) != True):
    print(f"Error, resource group {VM_IMAGE_STORAGE_RESOURCE_GROUP_NAME} "
          f"does not exist.")
    sys.exit(1)

# Verify that image does not already exist.
image_does_not_exist = False
VM_IMAGE_SETTINGS = SETTINGS["VMImageCreation"]
VM_IMAGE_NAME = VM_IMAGE_SETTINGS["ImageName"]
compute_management_client = ComputeManagementClient(
    azure_credential, SUBSCRIPTION_ID)
try:
    compute_management_client.images.get(
        VM_IMAGE_STORAGE_RESOURCE_GROUP_NAME, VM_IMAGE_NAME)
except HttpResponseError as ex:
    if ex.status_code == 404:
        image_does_not_exist = True
        print(f"Image {VM_IMAGE_NAME} will be created.")
    else:
        print(ex.message)
        sys.exit(1)
if (image_does_not_exist != True):
    print(f"Image {VM_IMAGE_NAME} already exists.")
    sys.exit(1)

# Provision VM image creation resource group.
VM_IMAGE_RESOURCE_GROUP_NAME = VM_IMAGE_SETTINGS["ResourceGroupName"]
print(f"Provisioning VM image resource group "
      f"{VM_IMAGE_RESOURCE_GROUP_NAME}...")
if (resource_management_client.resource_groups.check_existence(
    VM_IMAGE_RESOURCE_GROUP_NAME) == True):
    print(f"Error, resource group {VM_IMAGE_RESOURCE_GROUP_NAME} "
          f"already exist.")
    sys.exit(1)
LOCATION = SETTINGS["CloudLocation"]
vm_image_resource_group =\
    resource_management_client.resource_groups.create_or_update(
    VM_IMAGE_RESOURCE_GROUP_NAME, {"location": LOCATION}
)
print(f"Provisioned VM image resource group {vm_image_resource_group.name} "
      f"in the {vm_image_resource_group.location} location.")

################################################################################
################################################################################
# Deploy networking and vm.
################################################################################
################################################################################

# Deploy the VM that will be used to create VM image.
DEPLOYMENT_NAME = VM_IMAGE_SETTINGS["DeploymentName"]
print(f"Starting VM image creation deployment {DEPLOYMENT_NAME} in "
      f"resource group {VM_IMAGE_RESOURCE_GROUP_NAME}...")

VM_IMAGE_IP_ADDRESS_NAME = VM_IMAGE_SETTINGS["PublicIPAddressName"]
VM_IMAGE_VIRTUAL_NETWORK_NAME = VM_IMAGE_SETTINGS["VirtualNetworkName"]
VM_IMAGE_VIRTUAL_NETWORK_ADDRESS_PREFIX =\
   VM_IMAGE_SETTINGS["VirtualNetworkAddressPrefix"]
VM_IMAGE_SUBNET_NAME = VM_IMAGE_SETTINGS["SubnetName"]
VM_IMAGE_SUBNET_ADDRESS_PREFIX = VM_IMAGE_SETTINGS["SubnetAddressPrefix"]
VM_IMAGE_NETWORK_SECURITY_GROUP_NAME =\
    VM_IMAGE_SETTINGS["NetworkSecurityGroupName"]
VM_IMAGE_NETWORK_INTERFACE_NAME = VM_IMAGE_SETTINGS["NetworkInterfaceName"]
VM_IMAGE_VM_NAME = VM_IMAGE_SETTINGS["VMName"]
VM_IMAGE_VM_COMPUTER_NAME = VM_IMAGE_SETTINGS["ComputerName"]
VM_IMAGE_USERNAME = CREDENTIALS["VMImageUserName"]
VM_IMAGE_PASSWORD = CREDENTIALS["VMImagePassword"]
VM_IMAGE_VM_SIZE = VM_IMAGE_SETTINGS["Size"]
VM_IMAGE_VM_STORAGE_ACCOUNT_TYPE = VM_IMAGE_SETTINGS["StorageAccountType"]

response = requests.get("https://api.ipify.org")
print(f"This machine public IP address is {response.text}. If this "
        f"changes update Azure NSG inbound security rule.")
with open("ARMTemplates/vm_image.json", "r") as arm_template_file:
    arm_template_json = json.load(arm_template_file)
pooler = resource_management_client.deployments.begin_create_or_update(
    VM_IMAGE_RESOURCE_GROUP_NAME,
    DEPLOYMENT_NAME,
    {
        "properties": {
            "template": arm_template_json,
            "parameters": {
                "localIPAddress": {
                    "value": response.text,
                    "type": "String"
                },
                "publicIPAddressName": {
                    "value": VM_IMAGE_IP_ADDRESS_NAME,
                    "type": "String"
                },
                "virtualNetworkName": {
                    "value": VM_IMAGE_VIRTUAL_NETWORK_NAME,
                    "type": "String"
                },
                "virtualNetworkAddressPrefix": {
                    "value": VM_IMAGE_VIRTUAL_NETWORK_ADDRESS_PREFIX,
                    "type": "String"
                },
                "subnetName": {
                    "value": VM_IMAGE_SUBNET_NAME,
                    "type": "String"
                },
                "subnetAddressPrefix": {
                    "value": VM_IMAGE_SUBNET_ADDRESS_PREFIX,
                    "type": "String"
                },
                "networkSecurityGroupName": {
                    "value": VM_IMAGE_NETWORK_SECURITY_GROUP_NAME,
                    "type": "String"
                },
                "networkInterfaceName": {
                    "value": VM_IMAGE_NETWORK_INTERFACE_NAME,
                    "type": "String"
                },
                "vmName": {
                    "value": VM_IMAGE_VM_NAME,
                    "type": "String"
                },
                "vmComputerName": {
                    "value": VM_IMAGE_VM_COMPUTER_NAME,
                    "type": "String"
                },
                "adminUsername": {
                    "value": VM_IMAGE_USERNAME,
                    "type": "String"
                },
                "adminPassword": {
                    "value": VM_IMAGE_PASSWORD,
                    "type": "String"
                },
                "vmSize": {
                    "value": VM_IMAGE_VM_SIZE,
                    "type": "String"
                },
                "vmStorageAccountType": {
                    "value": VM_IMAGE_VM_STORAGE_ACCOUNT_TYPE,
                    "type": "String"
                }
            },
            "mode": DeploymentMode.incremental
        }
    }
)
deployment_result = pooler.result()
print(f"Finished VM image creation deployment.")

################################################################################
################################################################################
# Setup SSH key and run the installation script on the vm.
################################################################################
################################################################################

poller = compute_management_client.virtual_machines.begin_start(
    VM_IMAGE_RESOURCE_GROUP_NAME,
    VM_IMAGE_VM_NAME)
vm_image_vm_start_result = poller.result()

vm_status_code = install_utilities.get_vm_power_state(
    compute_management_client, VM_IMAGE_RESOURCE_GROUP_NAME, VM_IMAGE_VM_NAME)
print(f"VM {VM_IMAGE_VM_NAME} power state is {vm_status_code}.")

# TODO: Could simply get this info from the ARM template output.
network_management_client = NetworkManagementClient(
    azure_credential, SUBSCRIPTION_ID, api_version='2023-09-01')
public_ip_address = network_management_client.public_ip_addresses.\
    get(VM_IMAGE_RESOURCE_GROUP_NAME, VM_IMAGE_IP_ADDRESS_NAME)
# TODO: Could simply get this info from the ARM template output.
vm_image_public_ip = public_ip_address.ip_address
print(f"Public IP address of the VM is {vm_image_public_ip}.")
network_interface = network_management_client.network_interfaces.\
    get(VM_IMAGE_RESOURCE_GROUP_NAME, VM_IMAGE_NETWORK_INTERFACE_NAME)
vm_image_private_ip = network_interface.ip_configurations[0].\
    private_ip_address
print(f"Private IP address of the VM is {vm_image_private_ip}.")

# Install SSH public key.
SSH_PUBLIC_KEY_PATH = CREDENTIALS["SSHPublicKeyPath"]
install_utilities.install_ssh_keys(
    VM_IMAGE_USERNAME,
    install_utilities.ssh_conn_param(vm_image_public_ip, 22),
    open(SSH_PUBLIC_KEY_PATH, 'r'))

install_utilities.install_kubernetes(
        SETTINGS["Configurations"], VM_IMAGE_USERNAME, VM_IMAGE_PASSWORD,
        install_utilities.ssh_conn_param(vm_image_public_ip, 22), 
        "InstallKubernetes", "generalize",
        VM_IMAGE_VIRTUAL_NETWORK_ADDRESS_PREFIX)

################################################################################
################################################################################
# Deallocate and generalize VM, create image and delete the vm and rest of the
# image creation resource group.
################################################################################
################################################################################

# Deallocate and generalize the VM image virtual machine.
print(f"Deallocating and generalizing VM image virtual machine "
      f"{VM_IMAGE_VM_NAME}...")
poller = compute_management_client.virtual_machines.begin_deallocate(
    VM_IMAGE_RESOURCE_GROUP_NAME,
    VM_IMAGE_VM_NAME)
vm_image_vm_deallocate_result = poller.result()

vm_status_code = install_utilities.get_vm_power_state(
    compute_management_client, VM_IMAGE_RESOURCE_GROUP_NAME, VM_IMAGE_VM_NAME)
print(f"VM {VM_IMAGE_VM_NAME} power state is {vm_status_code}.")

vm_image_vm_generalize_result = compute_management_client.\
virtual_machines.generalize(VM_IMAGE_RESOURCE_GROUP_NAME, VM_IMAGE_VM_NAME)
print(f"Generalized VM image virtual machine {VM_IMAGE_VM_NAME}.")

# Create VM image.
print(f"Creating VM image {VM_IMAGE_NAME} in resource group "
      f"{VM_IMAGE_STORAGE_RESOURCE_GROUP_NAME}...")
# TODO: Could simply get this info from the ARM template output.
vm = compute_management_client.virtual_machines.get(
    VM_IMAGE_RESOURCE_GROUP_NAME, VM_IMAGE_VM_NAME, expand = "instanceView")
sub_resource = SubResource(id=vm.id)
params = Image(location = LOCATION, source_virtual_machine = sub_resource)
poller = compute_management_client.images.begin_create_or_update(
    VM_IMAGE_STORAGE_RESOURCE_GROUP_NAME, VM_IMAGE_NAME, parameters=params)
vm_image_result = poller.result()
print(f"Finished creating VM image {VM_IMAGE_NAME} in resource group "
      f"{VM_IMAGE_STORAGE_RESOURCE_GROUP_NAME}.")

# Delete the resource group.
print(f"Deleting the VM image resource group "
      f"{VM_IMAGE_RESOURCE_GROUP_NAME}...")
poller = resource_management_client.resource_groups.begin_delete(
    VM_IMAGE_RESOURCE_GROUP_NAME)
vm_image_resource_group_delete_result = poller.result()
print(f"Deleted the VM image resource group {VM_IMAGE_RESOURCE_GROUP_NAME}.")
