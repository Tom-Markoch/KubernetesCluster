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
# on physical machines or Windows Pro Hyper-V VM-s.

import sys
import json

import install_utilities

# To get WIndows Pro Hyper-V VM IPs execute as admin in PowerShell 7:
# get-vm | ?{$_.State -eq "Running"} | select -ExpandProperty networkadapters | select vmname, macaddress, switchname, ipaddresses | ft -wrap -autosize

def get_cluster_info():
    with open("kube_settings.json", 'r') as settings_file:
        SETTINGS = json.load(settings_file)

    CREDENTIALS_PATH = SETTINGS["CredentialsPath"]
    with open(CREDENTIALS_PATH, 'r') as credentials_file:
        CREDENTIALS = json.load(credentials_file)

    USERNAME = CREDENTIALS["MetalUserName"]
    PASSWORD = CREDENTIALS["MetalPassword"]
    SSH_PUBLIC_KEY_PATH = CREDENTIALS["SSHPublicKeyPath"]
    CLUSTER_CONFIGURATIONS = SETTINGS["Configurations"]
    SETTINGS = SETTINGS["MetalClusterConfig"]
    VMS = SETTINGS["VirtualMachines"]
    NETWORK_ADDRESS_PREFIX = SETTINGS["NetworkAddressPrefix"]
    USE_LOAD_BALANCER = SETTINGS["UseLoadBalancer"]
    CONTROL_PLANE_ENDPOINT = None
    CONTROL_PLANE_VM_INDEX = None
    if USE_LOAD_BALANCER:
        CONTROL_PLANE_ENDPOINT = VMS[CONTROL_PLANE_VM_INDEX]["IPAddress"]
    else:
        CONTROL_PLANE_VM_INDEX = \
            SETTINGS["ControlPlaneEndpointVMIndex"]

    vms = []
    for index in range(0, len(VMS)):
        vm_setting = VMS[index]
        vm = {
            # Mandatory parameters.
            "Index": index,
            "IsControlPlane": vm_setting["IsControlPlane"],
            "AllowWorkloads": vm_setting["AllowWorkloads"],
            "Running": vm_setting["Running"],
            "SSH": install_utilities.ssh_conn_param(
                vm_setting["IPAddress"], 22),
            # Optional parameters.
            "IPAddress": vm_setting["IPAddress"]
            }
        vms.append(vm)
    return install_utilities.cluster_info(
        vms, None, NETWORK_ADDRESS_PREFIX, USERNAME, PASSWORD,
        SSH_PUBLIC_KEY_PATH, CLUSTER_CONFIGURATIONS,
        CONTROL_PLANE_ENDPOINT, CONTROL_PLANE_VM_INDEX,
        "not-generalize")

install_utilities.ui_loop(get_cluster_info)
