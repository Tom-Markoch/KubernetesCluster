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

# This script creates Kubernetes cluster and performs cluster operations
# on Azure VM-s and Scale Sets.

import sys
import json
import requests

from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.resource.resources.models import DeploymentMode

import install_utilities

print(
    "########################################################################"
    "########\n"
    "CREATING KUBERNETES CLUSTER.\n"
    "########################################################################"
    "########"
)

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

# Verify that storage resource group exists.
VM_IMAGE_STORAGE = SETTINGS["VMImageStorage"]
VM_IMAGE_RESOURCE_GROUP_NAME =\
    VM_IMAGE_STORAGE["ResourceGroupName"]
resource_management_client = ResourceManagementClient(
    azure_credential, SUBSCRIPTION_ID)

if (resource_management_client.resource_groups.check_existence(
    VM_IMAGE_RESOURCE_GROUP_NAME) != True):
    print(f"Error, resource group {VM_IMAGE_RESOURCE_GROUP_NAME} "
          f"does not exist.")
    sys.exit(1)
    
# Provision the resource group.
CLUSTER_CONFIG = SETTINGS["ClusterConfig"]
RESOURCE_GROUP_NAME = CLUSTER_CONFIG["ResourceGroupName"]
PUBLIC_IP_ADDRESS_NAME = CLUSTER_CONFIG["PublicIPAddressName"]
VIRTUAL_NETWORK_NAME = CLUSTER_CONFIG["VirtualNetworkName"]
VIRTUAL_NETWORK_ADDRESS_PREFIX =\
    CLUSTER_CONFIG["VirtualNetworkAddressPrefix"]
SUBNET_NAME = CLUSTER_CONFIG["SubnetName"]
SUBNET_ADDRESS_PREFIX = CLUSTER_CONFIG["SubnetAddressPrefix"]
NETWORK_SECURITY_GROUP_NAME = CLUSTER_CONFIG["NetworkSecurityGroupName"]
# Even if the resource is conditionally NOT created, in order to pass
# the template validation we still need to pass a valid non empty strings
# instead of an empty strings or null, so we pass "null" string instead
# of null.
LOAD_BALANCER_NAME = "null"
BACKEND_POOL_NAME = "null"
PUBLIC_VM_NIC_NAME = "null"
PUBLIC_VM_NAME = "null"
PUBLIC_VM_COMPUTER_NAME = "null"
PUBLIC_VM_SIZE = "null"
PUBLIC_VM_IMAGE_NAME = "null"
PUBLIC_VM_STORAGE_ACCOUNT_TYPE = "null"
USE_LOAD_BALANCER = CLUSTER_CONFIG["UseLoadBalancer"]
if USE_LOAD_BALANCER:
    CLUSTER_CONFIG_LOAD_BALANCER = CLUSTER_CONFIG["LoadBalancer"]
    LOAD_BALANCER_NAME = CLUSTER_CONFIG_LOAD_BALANCER["Name"]
    BACKEND_POOL_NAME = CLUSTER_CONFIG_LOAD_BALANCER["BackendPoolName"]
else:
    CLUSTER_CONFIG_PUBLIC_VM = CLUSTER_CONFIG["PublicVM"]
    PUBLIC_VM_NIC_NAME = CLUSTER_CONFIG_PUBLIC_VM["NicName"]
    PUBLIC_VM_NAME = CLUSTER_CONFIG_PUBLIC_VM["Name"]
    PUBLIC_VM_COMPUTER_NAME = CLUSTER_CONFIG_PUBLIC_VM["ComputerName"]
    PUBLIC_VM_SIZE = CLUSTER_CONFIG_PUBLIC_VM["Size"]
    PUBLIC_VM_IMAGE_NAME = CLUSTER_CONFIG_PUBLIC_VM["ImageName"]
    PUBLIC_VM_STORAGE_ACCOUNT_TYPE =\
        CLUSTER_CONFIG_PUBLIC_VM["StorageAccountType"]

ADMIN_USER_NAME = CREDENTIALS["VMImageUserName"]
ADMIN_PASSWORD = CREDENTIALS["VMImagePassword"]

CLUSTER_CONFIG_SCALE_SETS = CLUSTER_CONFIG["ScaleSets"]

################################################################################
################################################################################
# Check if Azure components are already deployed. If so skip deployment,
# otherwise deploy networking, vms and scale sets.
################################################################################
################################################################################

if resource_management_client.resource_groups.check_existence(
    RESOURCE_GROUP_NAME):
    print(f"Resource group {RESOURCE_GROUP_NAME} already exists. "
          f"Skipping the deployment phase.")
else:
    print(f"Provisioning resource group {RESOURCE_GROUP_NAME}...")

    LOCATION = SETTINGS["CloudLocation"]
    resource_group =\
        resource_management_client.resource_groups.create_or_update(
        RESOURCE_GROUP_NAME, {"location": LOCATION}
    )
    print(f"Provisioned VM image resource group {resource_group.name} "
          f"in the {resource_group.location} location.")

    # Deploy the cluster.
    DEPLOYMENT_NAME = CLUSTER_CONFIG["DeploymentName"]
    print(f"Starting cluster deployment in resource group "
          f"{RESOURCE_GROUP_NAME}...")
    print(f"Provisioning cluster network under deployment name "
          f"{DEPLOYMENT_NAME}...")
    
    response = requests.get("https://api.ipify.org")
    print(f"This machine public IP address is {response.text}. If this "
          f"changes update Azure NSG inbound security rule.")
    with open("ARMTemplates/cluster.json", "r") as arm_template_file:
        arm_template_json = json.load(arm_template_file)
    pooler = resource_management_client.deployments.begin_create_or_update(
        RESOURCE_GROUP_NAME,
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
                        "value": PUBLIC_IP_ADDRESS_NAME,
                        "type": "String"
                    },
                    "virtualNetworkName": {
                        "value": VIRTUAL_NETWORK_NAME,
                        "type": "String"
                    },
                    "virtualNetworkAddressPrefix": {
                        "value": VIRTUAL_NETWORK_ADDRESS_PREFIX,
                        "type": "String"
                    },
                    "subnetName": {
                        "value": SUBNET_NAME,
                        "type": "String"
                    },
                    "subnetAddressPrefix": {
                        "value": SUBNET_ADDRESS_PREFIX,
                        "type": "String"
                    },
                    "networkSecurityGroupName": {
                        "value": NETWORK_SECURITY_GROUP_NAME,
                        "type": "String"
                    },
                    "useLoadBalancer": {
                        "value": USE_LOAD_BALANCER,
                        "type": "Bool"
                    },
                    "loadBalancerName": {
                        "value": LOAD_BALANCER_NAME,
                        "type": "String"
                    },
                    "backendPoolName": {
                        "value": BACKEND_POOL_NAME,
                        "type": "String"
                    },
                    "networkInterfaceName": {
                        "value": PUBLIC_VM_NIC_NAME,
                        "type": "String"
                    },
                    "vmName": {
                        "value": PUBLIC_VM_NAME,
                        "type": "String"
                    },
                    "vmComputerName": {
                        "value": PUBLIC_VM_COMPUTER_NAME,
                        "type": "String"
                    },
                    "adminUsername": {
                        "value": ADMIN_USER_NAME,
                        "type": "String"
                    },
                    "adminPassword": {
                        "value": ADMIN_PASSWORD,
                        "type": "String"
                    },
                    "vmSize": {
                        "value": PUBLIC_VM_SIZE,
                        "type": "String"
                    },
                    "vmStorageAccountType": {
                        "value": PUBLIC_VM_STORAGE_ACCOUNT_TYPE,
                        "type": "String"
                    },
                    "vmImageResourceGroupName": {
                        "value": VM_IMAGE_RESOURCE_GROUP_NAME,
                        "type": "String"
                    },
                    "vmImageName": {
                        "value": PUBLIC_VM_IMAGE_NAME,
                        "type": "String"
                    }
                },
                "mode": DeploymentMode.incremental
            }
        }
    )
    deployment_result = pooler.result()
    print(f"Provisioned cluster network.")

    # Deploy VM Scate Sets.
    with open("ARMTemplates/scale_set.json", "r") as scale_set_arm_template_file:
        scale_set_arm_template_json = json.load(scale_set_arm_template_file)

    scale_set_poolers = []
    for scale_set_name, scale_set_config in \
        CLUSTER_CONFIG_SCALE_SETS.items():
        VMSS_DEPLOYMENT_NAME = DEPLOYMENT_NAME + "-vmss-" + scale_set_name
        print(f"Provisioning scale set {scale_set_name} under deployment name "
              f"{VMSS_DEPLOYMENT_NAME}...")
        VMSS_COMPUTER_NAME_PREFIX = scale_set_config["ComputerNamePrefix"]
        VMSS_SIZE = scale_set_config["Size"]
        VMSS_STORAGE_ACCOUNT_TYPE = scale_set_config["StorageAccountType"]
        VMSS_IMAGE_NAME = scale_set_config["ImageName"]
        VMSS_SPOT =  scale_set_config["Spot"]
        VMSS_MAX_PRICE = ""
        if VMSS_SPOT:
            VMSS_MAX_PRICE = scale_set_config["MaxPrice"]
        scale_set_pooler = resource_management_client.deployments.\
        begin_create_or_update(
            RESOURCE_GROUP_NAME,
            VMSS_DEPLOYMENT_NAME,
            {
                "properties": {
                    "template": scale_set_arm_template_json,
                    "parameters": {
                        "virtualNetworkName": {
                            "value": VIRTUAL_NETWORK_NAME,
                            "type": "String"
                        },
                        "subnetName": {
                            "value": SUBNET_NAME,
                            "type": "String"
                        },
                        "networkSecurityGroupName": {
                            "value": NETWORK_SECURITY_GROUP_NAME,
                            "type": "String"
                        },
                        "useLoadBalancer": {
                            "value": USE_LOAD_BALANCER,
                            "type": "Bool"
                        },
                        "loadBalancerName": {
                            "value": LOAD_BALANCER_NAME,
                            "type": "String"
                        },
                        "backendPoolName": {
                            "value": BACKEND_POOL_NAME,
                            "type": "String"
                        },
                        "networkInterfaceName": {
                            "value": "nic",
                            "type": "String"
                        },
                        "vmssName": {
                            "value": scale_set_name,
                            "type": "String"
                        },
                        "vmComputerNamePrefix": {
                            "value": VMSS_COMPUTER_NAME_PREFIX,
                            "type": "String"
                        },
                        "adminUsername": {
                            "value": ADMIN_USER_NAME,
                            "type": "String"
                        },
                        "adminPassword": {
                            "value": ADMIN_PASSWORD,
                            "type": "String"
                        },
                        "vmSize": {
                            "value": VMSS_SIZE,
                            "type": "String"
                        },
                        "vmStorageAccountType": {
                            "value": VMSS_STORAGE_ACCOUNT_TYPE,
                            "type": "String"
                        },
                        "vmSpot": {
                            "value": VMSS_SPOT,
                            "type": "Bool"
                        },
                        "vmMaxPrice": {
                            "value": VMSS_MAX_PRICE,
                            "type": "String"
                        },
                        "vmImageResourceGroupName": {
                            "value": VM_IMAGE_RESOURCE_GROUP_NAME,
                            "type": "String"
                        },
                        "vmImageName": {
                            "value": VMSS_IMAGE_NAME,
                            "type": "String"
                        }
                    },
                    "mode": DeploymentMode.incremental
                }
            }
        )
        scale_set_poolers.append(scale_set_pooler)

    for scale_set_pooler in scale_set_poolers:
        scale_set_deployment_result = scale_set_pooler.result()
        print(f"Provisioned scale set under deployment name "
              f"{scale_set_deployment_result.name}.")

    print(f"Finished cluster deployment.")

################################################################################
################################################################################
# Run command line UI to operate the cluster.
################################################################################
################################################################################

compute_management_client = ComputeManagementClient(
    azure_credential, SUBSCRIPTION_ID)
network_management_client = NetworkManagementClient(
    azure_credential, SUBSCRIPTION_ID, api_version='2023-09-01')

vmss_public_ip_address = network_management_client.public_ip_addresses.\
    get(RESOURCE_GROUP_NAME, PUBLIC_IP_ADDRESS_NAME)

def get_cluster_info():
    # Prepare dictionaries that will contain Azure VM and networking data.
    vms_by_id_by_scale_set = {}
    for scale_set_name, scale_set_config in \
            CLUSTER_CONFIG_SCALE_SETS.items():
        vms_by_id_by_scale_set[scale_set_name] = {}

    # Loop through all the Scale Sets.
    for scale_set_name, vms_by_id in \
        vms_by_id_by_scale_set.items():

        # Loop through all the VM-s in the scale set and collect the data.
        vms = compute_management_client.virtual_machine_scale_set_vms.\
            list(RESOURCE_GROUP_NAME, scale_set_name)
        for vm in vms:
            all_vm_data = {}
            vms_by_id[vm.id] = all_vm_data
            all_vm_data["vm"] = vm
            all_vm_data["power_state"] = install_utilities.\
                get_scale_set_vm_power_state(
                    compute_management_client, RESOURCE_GROUP_NAME,
                    scale_set_name, vm.instance_id)

        # https://learn.microsoft.com/en-us/python/api/azure-mgmt-network/azure.mgmt.network.operations.networkinterfacesoperations?view=azure-python
        # Loop through all the NIC-s in the scale set and collect the data.
        nics = network_management_client.network_interfaces.\
            list_virtual_machine_scale_set_network_interfaces(
                RESOURCE_GROUP_NAME, scale_set_name)
        for nic in nics:
            if len(nic.ip_configurations) != 1:
                print("There must exactly one IP configuration per NIC.")
                sys.exit(1)
            vm_id = nic.virtual_machine.id
            # Find the VM this NIC belongs to and add NIC data to the VM data.
            all_vm_data = vms_by_id[vm_id]
            if "nic" in all_vm_data:
                print("There must exactly one NIC per VM.")
                sys.exit(1)
            all_vm_data["nic"] = nic
            # TODO: verify nic name matches!
            if USE_LOAD_BALANCER:
                port_mappings = network_management_client.load_balancers.\
                    begin_list_inbound_nat_rule_port_mappings(
                        RESOURCE_GROUP_NAME,
                        LOAD_BALANCER_NAME,
                        BACKEND_POOL_NAME,
                        {"ipAddress":
                            nic.ip_configurations[0].private_ip_address}
                    ).result()
                if len(port_mappings.inbound_nat_rule_port_mappings) != 1:
                    print("There must exactly one Port Mapping per NIC.")
                    sys.exit(1)
                all_vm_data["port_mappings"] = port_mappings

    # Generate VM data array for the user interface.
    vms_info = []
    # If no load balancer, add first the main public vm on index 0.
    if not USE_LOAD_BALANCER:
        power_state = install_utilities.\
            get_vm_power_state(compute_management_client,
                               RESOURCE_GROUP_NAME, PUBLIC_VM_NAME)
        is_running = False
        if power_state.lower() == "running":
            is_running  = True
        ssh = install_utilities.ssh_conn_param(
            vmss_public_ip_address.ip_address, 22)
        nic = network_management_client.network_interfaces.\
            get(RESOURCE_GROUP_NAME, PUBLIC_VM_NIC_NAME)
        vm = compute_management_client.virtual_machines.get(
            RESOURCE_GROUP_NAME, PUBLIC_VM_NAME)
        vm_info = {
            # Mandatory parameters.
            "Index": len(vms_info),
            "IsControlPlane": True,
            "AllowWorkloads": CLUSTER_CONFIG_PUBLIC_VM["AllowWorkloads"],
            "Running": is_running,
            "SSH": ssh,
            "IPAddress": nic.ip_configurations[0].private_ip_address,
            # Optional parameters.
            "ScaleSet": None,
            "VMId": None,
            "VMName": vm.name,
            "ComputerName": vm.os_profile.computer_name,
            "PowerState": power_state,
            "MAC": nic.mac_address
            }
        vms_info.append(vm_info)

    # Loop through all the Scale Sets.
    for scale_set_name, vms_by_id in \
        vms_by_id_by_scale_set.items():
        # Loop through all th VM-s in the Scale Set.
        for value in vms_by_id.values():
            vm = value["vm"]
            power_state = value["power_state"]
            nic = value["nic"]
            if USE_LOAD_BALANCER:
                port_mappings = value["port_mappings"]
                ssh = install_utilities.ssh_conn_param(
                    vmss_public_ip_address.ip_address,
                    port_mappings.inbound_nat_rule_port_mappings[0].
                        frontend_port)
            else:
                ssh = install_utilities.ssh_conn_param(
                    nic.ip_configurations[0].private_ip_address, 22,
                    True, vmss_public_ip_address.ip_address, 22)

            power_state = value["power_state"]
            is_running = False
            if power_state.lower() == "running":
                is_running  = True
            SCALE_SET_CONFIG = CLUSTER_CONFIG_SCALE_SETS[scale_set_name]
            is_control_plane = SCALE_SET_CONFIG["IsControlPlane"]
            if (not is_control_plane) and \
                ("AllowWorkloads" in SCALE_SET_CONFIG):
                print("Invalid settings file, IsControlPlane is False but "
                      "AllowWorkloads is set!")
                sys.exit(1)
            allow_workloads = None
            if (is_control_plane):
                allow_workloads = SCALE_SET_CONFIG["AllowWorkloads"]
            vm_info = {
                # Mandatory parameters.
                "Index": len(vms_info),
                "IsControlPlane": is_control_plane,
                "AllowWorkloads": allow_workloads,
                "Running": is_running,
                "SSH": ssh,
                "IPAddress": nic.ip_configurations[0].private_ip_address,
                # Optional parameters.
                "ScaleSet": scale_set_name,
                "VMId": vm.instance_id,
                "VMName": vm.name,
                "ComputerName": vm.os_profile.computer_name,
                "PowerState": power_state,
                "MAC": nic.mac_address
                # "BackPort": port_mappings.inbound_nat_rule_port_mappings[0].
                #        backend_port
                }
            vms_info.append(vm_info)

    control_plane_endpoint = None
    control_plane_vm_index = None
    if USE_LOAD_BALANCER:
        control_plane_endpoint = vmss_public_ip_address.ip_address
    else:
        control_plane_vm_index = 0
    return install_utilities.cluster_info(
        vms_info, vmss_public_ip_address.ip_address,
        VIRTUAL_NETWORK_ADDRESS_PREFIX, ADMIN_USER_NAME, ADMIN_PASSWORD,
        CREDENTIALS["SSHPublicKeyPath"], SETTINGS["Configurations"],
        control_plane_endpoint, control_plane_vm_index, "generalize")

install_utilities.ui_loop(get_cluster_info)
