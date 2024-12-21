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

import os
import subprocess
import sys
import tempfile
import time

################################################################################
# Get Azure VM power state.

def get_vm_power_state(compute_management_client,
                       resource_group_name, vm_name):
    prefix = "PowerState/"
    vm = compute_management_client.virtual_machines.get(
        resource_group_name, vm_name, expand = "instanceView")
    for status in vm.instance_view.statuses:
        if (status.code.startswith(prefix)):
            return status.code[len(prefix):]
    return "UNKNOWN";

def get_scale_set_vm_power_state(
        compute_management_client, resource_group_name, vmss_name,
        instance_id):
    prefix = "PowerState/"
    vm_instance = compute_management_client.virtual_machine_scale_set_vms.\
        get_instance_view(resource_group_name, vmss_name, instance_id)
    for status in vm_instance.statuses:
        if (status.code.startswith(prefix)):
            return status.code[len(prefix):]
    return "UNKNOWN";

################################################################################
# SCP and SSH.

def scp(src_file_name, username, ssh_conn_param,
        dest_file_name = None):
    if (dest_file_name == None):
        dest_file_name = src_file_name

    args = []
    args.append(f"scp")
    args.append(f"-O")# Suddenly had to add compatibility mode!
    if ssh_conn_param.use_proxy:
        args.append(f"-J")
        args.append(f"{username}@{ssh_conn_param.proxy_ip_address}:"
                    f"{ssh_conn_param.proxy_port}")
    args.append(f"-P")# NOTICE, must be UPPER CASE?!
    args.append(f"{ssh_conn_param.port}")
    args.append(f"{src_file_name}")
    args.append(f"{username}@{ssh_conn_param.ip_address}:"
                f"$HOME/{dest_file_name}")

    subprocess_return = subprocess.run(args)
    if (subprocess_return.returncode != 0):
        print(
            f"Error, cannot copy {src_file_name}, "
            f"'{subprocess_return.stderr}'."
        )
        sys.exit(1)
    print(f"Finished SCP copying file {src_file_name}.")

def ssh(command, username, ssh_conn_param,
        capture_output = False,
        stdin = None):
    
    args = []
    args.append(f"ssh")
    if ssh_conn_param.use_proxy:
        args.append(f"-J")
        args.append(f"{username}@{ssh_conn_param.proxy_ip_address}:"
                    f"{ssh_conn_param.proxy_port}")
    args.append("-p")# NOTICE, must be LOWER CASE?!
    args.append(f"{ssh_conn_param.port}")
    args.append(f"-t")
    args.append(f"{username}@{ssh_conn_param.ip_address}")
    args.append(f"{command}")

    subprocess_return = subprocess.run(
        args,
        capture_output = capture_output,
        text = capture_output,
        stdin = stdin)
    if (subprocess_return.returncode != 0):
        print(
            f"Error SSH executing command, '{subprocess_return.stderr}'."
        )
        sys.exit(1)
    print(f"Finished SSH executing command.")
    return subprocess_return.stdout

def install_ssh_keys(username, ssh_conn_param, stdin):
    # TODO: Remove password login, make sure SSH works on all versions.
    ssh("mkdir -p $HOME/.ssh && cat >> $HOME/.ssh/authorized_keys",
        username, ssh_conn_param, False, stdin)
    print(f"Installed ssh key on {ssh_conn_param}.")

################################################################################
# Kubernetes operations.

def kubeadm_reset(username, password, ssh_conn_param):
    print(f"Running kubeadm reset on {ssh_conn_param}...")
    ssh(f"echo {password} | sudo -S kubeadm reset -f",
        username, ssh_conn_param, False, None)
    print(f"Finished kubernetes kubeadm reset on {ssh_conn_param}.")

def install_kubernetes(
        configurations, username, password, ssh_conn_param,
        config_name, generalize, network_address_prefix):

    # Copy Kubernetes cluster deployment and service configuration
    # files that will be run after Kubernetes is installed.
    copy_configuration_files(
        configurations, config_name, username, ssh_conn_param)

    # Copy pod test definition files that will be used
    # after Kubernetes is installed.
    config = configurations[config_name]
    test_pod_names = config["TestPodNames"]
    with tempfile.NamedTemporaryFile(mode='w+t',
                                     delete_on_close=False) as tmp:
        for test_pod_name in test_pod_names:
            tmp.write(f"{test_pod_name}\n")
        tmp.close()
        scp(tmp.name, username, ssh_conn_param, "TestPodNames.txt")

    # Copy service endpoint test definition files that will be used
    # after Kubernetes is installed.
    test_endpoints = config["TestEndpoints"]
    with tempfile.NamedTemporaryFile(mode='w+t',
                                     delete_on_close=False) as tmp:
        for test_endpoint in test_endpoints:
            tmp.write(f"{test_endpoint["PortAndPath"]}\t"
                      f"{test_endpoint["StatusCode"]}\n")
        tmp.close()
        scp(tmp.name, username, ssh_conn_param, "TestEndpoints.txt")

    # Copy installation script to the server.
    SRC_SCRIPT_NAME = "KubeInstallationScripts/install_kube.sh"
    SCRIPT_NAME = "install_kube.sh"
    print(
        f"Executing installation script {SCRIPT_NAME} on "
        f"{ssh_conn_param}...")

    scp(SRC_SCRIPT_NAME, username, ssh_conn_param, SCRIPT_NAME)

    # Execute the installation script.
    ssh(
        f"bash $HOME/{SCRIPT_NAME} {password} {generalize} "\
        f"{network_address_prefix}",
        username, ssh_conn_param)
    print(
        f"Finished executing installation script {SCRIPT_NAME} on "
        f"{ssh_conn_param}.")

def kubeadm_init(
        username, password, ssh_conn_param, control_plane_endpoint,
        cluster_address_prefix, is_control_plane, allow_workloads):
    SRC_SCRIPT_NAME = "KubeInstallationScripts/initialize_kube_node.sh"
    SCRIPT_NAME = "initialize_kube_node.sh"
    print(
        f"Executing kubeadm init script {SCRIPT_NAME} on "
        f"{ssh_conn_param}...")

    # Copy over and execute the initialization script.
    scp(SRC_SCRIPT_NAME, username, ssh_conn_param, SCRIPT_NAME)
 
    if not is_control_plane:
        print("ERROR, trying to initialize the node that is not in the "
              "control plane!")
        sys.exit(1)

    command = (f"bash $HOME/{SCRIPT_NAME} {password} init "
               f"{control_plane_endpoint} {allow_workloads} "
               f"{cluster_address_prefix}")

    ssh(command, username, ssh_conn_param)
    print(
        f"Finished executing kubeadm init script {SCRIPT_NAME} on "
        f"{ssh_conn_param}.")

def kubeadm_join(
        username, password, join_to_ssh_conn_param, ssh_conn_param,
        control_plane_endpoint, cluster_address_prefix, is_control_plane,
        allow_workloads):

    SRC_SCRIPT_NAME = "KubeInstallationScripts/initialize_kube_node.sh"
    SCRIPT_NAME = "initialize_kube_node.sh"
    print(
        f"Executing kubeadm join script {SCRIPT_NAME} on "
        f"{ssh_conn_param} using {join_to_ssh_conn_param} to join...")

    # Get the join command with token and certificate key so other nodes
    # can join the cluster.
    kubeadm_join_command = ssh(
        "kubeadm token create --print-join-command",
        username,
        join_to_ssh_conn_param, True).rstrip()

    #kubeadm_join_cert_key = ssh(
    #     f"cat $HOME/Documents/certificate-key.txt",
    #     username, join_to_ssh_conn_param, True).rstrip()

    # Certificate key expires after some time. Create new certificate key.
    kubeadm_join_cert_key = ssh(
        f"echo {password} | sudo -S kubeadm init phase upload-certs "
        f"--upload-certs 2>/dev/null | tail -1",
        username,
        join_to_ssh_conn_param, True).rstrip()

    # Copy over and execute the join script.
    scp(SRC_SCRIPT_NAME, username, ssh_conn_param, SCRIPT_NAME)

    if (not is_control_plane) and allow_workloads:
        print("ERROR, allow_workloads should be set to true only on "
              "the control plane nodes. On worker nodes it is implicitly "
              "set!")
        sys.exit(1)

    command = (f"bash $HOME/{SCRIPT_NAME} {password} join "
               f"'{kubeadm_join_command}' {kubeadm_join_cert_key} "
               f"{control_plane_endpoint} "
               f"{is_control_plane} {allow_workloads} "
               f"{cluster_address_prefix}")

    ssh(command, username, ssh_conn_param)
    print(
        f"Finished executing kubeadm join script {SCRIPT_NAME} on "
        f"{ssh_conn_param} using {join_to_ssh_conn_param} to join.")

def copy_configuration_files(
        configurations, config_name, username, ssh_conn_param):
    config = configurations[config_name]
    dest_config_dir = f"configurations/{config_name}/"
    ssh(f"rm -rf $HOME/{dest_config_dir}", username, ssh_conn_param)
    ssh(f"mkdir -p $HOME/{dest_config_dir}", username, ssh_conn_param)
    for config_file in config["Files"]:
        scp(config_file, username, ssh_conn_param,
            f"'{dest_config_dir}{os.path.basename(config_file)}'")
    return dest_config_dir

def kubectl_apply(configurations, username, ssh_conn_param):
    print("Available configurations:")
    config_index_to_name = []
    for config_name in configurations.keys():
        print(f"{len(config_index_to_name)}\t"
              f"{config_name}")
        config_index_to_name.append(config_name)
    config_index = int(input("Enter configuration index to be applied: "))
    config_name = config_index_to_name[config_index]
    print(f"Applying configuration {config_name} on {ssh_conn_param}...")
    dest_config_dir = copy_configuration_files(
        configurations, config_name, username, ssh_conn_param)
    ssh(f"while ! kubectl apply -f $HOME/{dest_config_dir}; "
        f"do echo 'Will retry in 5 sec...'; sleep 5; done",
        username, ssh_conn_param)
    print(f"Finished applying configuration {config_name} on "
          f"{ssh_conn_param}.")

################################################################################
# Command line user interface.

class ssh_conn_param:
    def __init__(
            self, ip_address, port, use_proxy = False,
            proxy_ip_address = None, proxy_port = None):
        self.ip_address = ip_address
        self.port = port
        self.use_proxy = use_proxy
        self.proxy_ip_address = proxy_ip_address
        self.proxy_port = proxy_port
    def __str__(self):
        if self.use_proxy:
            return f"{self.proxy_ip_address}:{self.proxy_port}->"\
                   f"{self.ip_address}:{self.port}"
        else:
            return f"{self.ip_address}:{self.port}"

class cluster_info:
    def __init__(
            self, vms, public_ip_address, network_address_prefix, username,
            password, ssh_public_key_path, configurations,
            control_plane_endpoint, control_plane_vm_index,
            generalize):
        self.vms = vms
        self.public_ip_address = public_ip_address
        self.network_address_prefix = network_address_prefix
        self.username = username
        self.password = password
        self.ssh_public_key_path = ssh_public_key_path
        self.configurations = configurations
        self.generalize = generalize
        #
        # IMPORTANT:
        # If load balancer is USED, then control_plane_vm_index is
        # not used and MUST be set to None. One of the running control plane
        # endpoints will be automatically selected for cluster operations
        # where needed (such as init, join to, apply etc.).
        # control_plane_endpoint MUST be set to the load balancer IP address.
        #
        # If load balancer is NOT USED, then control_plane_vm_index
        # MUST be set to a valid control plane node that is also used as a 
        # control_plane_endpoint (ip address), and this node must be running
        # at all times. This node is used for all cluster operations where
        # needed. control_plane_endpoint MUST be set to None.
        #
        if (control_plane_endpoint != None) and \
            (control_plane_vm_index != None):
            print("Only control_plane_endpoint OR "
                  "control_plane_vm_index must be set.")
        self.control_plane_vm_index = control_plane_vm_index
        self.control_plane_endpoint = control_plane_endpoint

        # control_plane_vm_index is set, get the endpoint.
        if self.control_plane_vm_index != None:
            self.control_plane_endpoint =\
                self.vms[self.control_plane_vm_index]["IPAddress"]
            return

        # control_plane_endpoint is set. Get the index of one of the control
        # plane machibes that is running (this index may change over time if
        # machines are added/removed or turned on/off).
        for index in range(0, len(self.vms)):
            vm = self.vms[index]
            if vm["IsControlPlane"] and vm["Running"]:
                self.control_plane_vm_index = index

def print_vm_info(vms_info):
    # Get max length for each column.
    col_max_length = {}
    for vm in vms_info:
        for key, value in vm.items():
            if key not in col_max_length:
                col_max_length[key] = max(len(key), len(str(value)))
            else:
                col_max_length[key] = max(col_max_length[key],
                                          len(str(value)))
    # Print header.
    for key, value in col_max_length.items():
        print("".rjust(value + 1, "-"), end='')
    print("-")
    for key, value in col_max_length.items():
        print("|", end='')
        print(key.rjust(value, " "), end='')
    print("|")
    # Print VM info.
    for vm in vms_info:
        # for key, value in col_max_length.items():
        #     print("".rjust(value + 1, "-"), end='')
        # print("-")
        for key, value in col_max_length.items():
            vm_value = ""
            if key in vm:
                vm_value = vm[key];
            print("|", end='')
            print(str(vm_value).rjust(value, " "), end='')
        print("|")
    # Print last line.
    for key, value in col_max_length.items():
        print("".rjust(value + 1, "-"), end='')
    print("-")

def execute_operation(
        cluster_info, vm_index, operation, control_plane_vm_index):
    print("################################################################"
          "################")

    if vm_index != None:
        if (vm_index < 0 or vm_index >= len(cluster_info.vms)):
            print("ERROR, invalid VM index!")
            return
        vm = cluster_info.vms[vm_index]
        ssh_conn_param = vm["SSH"]

    if (control_plane_vm_index < 0 or 
        control_plane_vm_index >= len(cluster_info.vms)):
        print("ERROR, invalid control plane VM index!")
        return
    control_plane_vm = cluster_info.vms[control_plane_vm_index]
    control_plane_ssh_conn_param = control_plane_vm["SSH"]

    vm_str = ""
    if vm_index != None:
        vm_str = f", on VM {vm_index} IP {ssh_conn_param}"
    control_plane_str = (\
        f", with control plane VM {control_plane_vm_index} "
        f"IP {control_plane_ssh_conn_param}.")
    print(f"Executing operation '{operation}'{vm_str}{control_plane_str}")
    match operation:
        case "s":
            install_ssh_keys(
                cluster_info.username, ssh_conn_param,
                open(cluster_info.ssh_public_key_path, 'r'))
        case "r":
            kubeadm_reset(cluster_info.username, cluster_info.password,
                          ssh_conn_param)
        case "n":
            install_kubernetes(
                cluster_info.configurations, cluster_info.username,
                cluster_info.password, ssh_conn_param,
                "InstallKubernetes", cluster_info.generalize,
                cluster_info.network_address_prefix)
        case "i":
            kubeadm_init(
                cluster_info.username, cluster_info.password,
                control_plane_ssh_conn_param,
                cluster_info.control_plane_endpoint,
                cluster_info.network_address_prefix,
                control_plane_vm["IsControlPlane"],
                control_plane_vm["AllowWorkloads"])
        case "j":
            kubeadm_join(
                cluster_info.username, cluster_info.password,
                control_plane_ssh_conn_param, ssh_conn_param,
                cluster_info.control_plane_endpoint,
                cluster_info.network_address_prefix,
                vm["IsControlPlane"], vm["AllowWorkloads"])
        case "c":
            kubectl_apply(
                cluster_info.configurations, cluster_info.username,
                control_plane_ssh_conn_param)
        case _:
            print("ERROR, invalid operation!")
            return

def ui_loop(get_cluster_info):
    while True:
        print("########################################################"
              "########################")

        cluster_info = get_cluster_info()
        print(f"PublicIPAddress: "
              f"{cluster_info.public_ip_address}")
        print(f"NetworkAddressPrefix: "
              f"{cluster_info.network_address_prefix}")
        print(f"ControlPlaneVMIndex: "
              f"{cluster_info.control_plane_vm_index}")
        print(f"ControlPlaneEndpoint: "
              f"{cluster_info.control_plane_endpoint}")
        print_vm_info(cluster_info.vms)

        print("Select operation:")
        print("as: Install ssh keys on all VMs")
        print("s: Install ssh keys on a single VM")
        print("ar: Run 'kubeadm reset' on all VMs")
        print("r: Run 'kubeadm reset' on a single VM")
        print("n: Install Kubernetes on a single VM")
        print("i: Run 'kubeadm init'")
        print("j: Run 'kubeadm join'")
        print("c: Run 'kubectl apply'")
        print("g: Reload VM data")
        print("q: quit")
        op = input("Enter operation: ")

        start_time = time.time()
        match op:
            case "as" | "ar":
                match op:
                    case "as": op = "s"
                    case "ar": op = "r"
                for vm_index in range(0, len(cluster_info.vms)):
                    execute_operation(cluster_info, vm_index, op,
                                      cluster_info.control_plane_vm_index)
            case "i" | "c":
                execute_operation(cluster_info, None, op,
                                  cluster_info.control_plane_vm_index)
            case "g": continue
            case "q": return
            case _:
                vm_index = int(input("Enter VM index: "))
                execute_operation(cluster_info, vm_index, op,
                                  cluster_info.control_plane_vm_index)
        end_time = time.time()
        print(f"Command took {end_time - start_time} seconds to execute.")

# TODO: Kubernetes Dashboard instructions:
# sudo snap install helm --classic
# helm repo add kubernetes-dashboard https://kubernetes.github.io/dashboard/
# helm upgrade --install kubernetes-dashboard kubernetes-dashboard/kubernetes-dashboard --create-namespace --namespace kubernetes-dashboard
# kubectl apply -f dashboard_service_account.yaml
# kubectl -n kubernetes-dashboard port-forward svc/kubernetes-dashboard-kong-proxy 8443:443
# Web browser: https://127.0.0.1:8443/
# Then to get temp token:
# kubectl -n kubernetes-dashboard create token admin-user


# Example how to do Azure REST call (NOTE: should also use requests
# session for better performance):
# azure_token = azure_credential.get_token(
#     'https://management.core.windows.net//.default').token
# params = { "api-version" : "2024-03-01" }
# url = f"https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}/\
# resourceGroups/{RESOURCE_GROUP_NAME}/providers/microsoft.Compute/\
# virtualMachineScaleSets/{VMSS_NAME}/networkInterfaces"
# headers = { "Authorization": f"Bearer {azure_token}" }
# response = requests.get(url, params=params, headers=headers)
# if (response.status_code != 200):
#     print( f"Error {response.status_code} getting NICs.")
#     sys.exit(1)
# response_json = response.json()
