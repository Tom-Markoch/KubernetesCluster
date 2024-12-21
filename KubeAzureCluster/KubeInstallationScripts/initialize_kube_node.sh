#!/bin/bash
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

# Usage:
# scp initialize_kube_node.sh '<username>@<ip-address>:$HOME/Documents/initialize_kube_node.sh'
# then
# ssh -t <username>@<ip-address> 'bash $HOME/Documents/initialize_kube_node.sh <password> init <kube_control_plane_endpoint> <allow_workloads> <cluster_address_prefix>'
# or
# ssh -t <username>@<ip-address> 'bash $HOME/Documents/initialize_kube_node.sh <password> join "<kubeadm_join_command>" <kubeadm_join_cert_key> <kube_control_plane_endpoint> <is_control_plane> <allow_workloads> <cluster_address_prefix>'
# Example:
# ssh -t <username>@<ip-address> 'bash $HOME/Documents/initialize_kube_node.sh <password> init <kube_control_plane_endpoint> True 1.2.3.4/24'
# or
# ssh -t <username>@<ip-address> 'bash $HOME/Documents/initialize_kube_node.sh <password> join "kubeadm join 1.2.3.4:6443 --token ttp6xo.oxmsm5pmxaag5eto --discovery-token-ca-cert-hash sha256:c163f5a5a70b2818145f2072d3a2e9ad0b6623e91a2f33f9c42f4de97d7a52b3" <kubeadm_join_cert_key> <kube_control_plane_endpoint> True True 1.2.3.4/24'

echo "###############################################################################"
echo "Running Kubernetes Node Initialization Script..."
echo "###############################################################################"

echo $1 | sudo -S echo "LOADING PASSWORD"

set -e # End script on first error.
#set -x

script_command=$2
echo "script_command=$script_command"

if [[ "$script_command" == "init" ]]; then
    kube_control_plane_endpoint=$3
    allow_workloads=$4
    cluster_address_prefix=$5
    is_control_plane="True"
    echo "kube_control_plane_endpoint=$kube_control_plane_endpoint"
    echo "is_control_plane=$is_control_plane"
    echo "allow_workloads=$allow_workloads"
    echo "cluster_address_prefix=$cluster_address_prefix"
elif [[ "$script_command" == "join" ]]; then
    kubeadm_join_command=$3
    kubeadm_join_cert_key=$4
    kube_control_plane_endpoint=$5
    is_control_plane=$6
    allow_workloads=$7
    cluster_address_prefix=$8
    echo "kubeadm_join_command=$kubeadm_join_command"
    echo "kubeadm_join_cert_key=$kubeadm_join_cert_key"
    echo "kube_control_plane_endpoint=$kube_control_plane_endpoint"
    echo "is_control_plane=$is_control_plane"
    echo "allow_workloads=$allow_workloads"
    echo "cluster_address_prefix=$cluster_address_prefix"
else
    echo "ERROR, invalid command $script_command."
    exit 1
fi

# There is equivalent UFW code in the installation script.
# For troubleshooting see:
# https://manpages.debian.org/bookworm/iptables/iptables-extensions.8.en.html
# xtables-monitor --trace
# sudo iptables -t raw -I PREROUTING -p tcp --dport 80 -j TRACE
# sudo iptables -t raw -I PREROUTING -p tcp --dport 30080 -j TRACE
# https://linux.die.net/man/8/iptables
# journalctl -k | grep UFW
# cat /var/log/kern.log | grep UFW
# sudo iptables -L -v -n -t nat --line-numbers

# At this point firewall should be already on and "allow ssh" UFW rule should be already set.

# Allows default Kube service ip range (10.96.0.0/12) and our pod ip range set by podSubnet.
# TODO: the problem is that we really do not know what the range is for pods, only pods on node 0
# are within the podSubnet range, so we set UFW to allow entire private IP range from 10.0.0.0/8.
sudo ufw allow from 10.0.0.0/8
# Allows node ip range (nodes and some Kube system services are in the same range).
sudo ufw allow from $cluster_address_prefix
# Allows load balancer ip address.
sudo ufw allow from $kube_control_plane_endpoint
# Allows Azure load balancer health probe. TODO: pass as a parameter.
sudo ufw allow from 168.63.129.16
# Allows HTTP
sudo ufw allow http

# TODO: Create swap file when running the install script? But creating it here allows to select the size when creating the new node.
swap_on=$(sudo swapon --show)
if [[ -z $swap_on ]]; then
    echo "Swap space not detected. Creating 4GB swap file."
# START OF COPYRIGHT UNCLAIMABLE MATERIAL. Public domain.
    sudo fallocate -l 4G /SWAPFILE
    sudo chmod 600 /SWAPFILE
    sudo mkswap /SWAPFILE
    sudo swapon /SWAPFILE
    echo "/swapfile none swap sw 0 0" | sudo tee -a /etc/fstab
# END OF COPYRIGHT UNCLAIMABLE MATERIAL.
fi

# Reinitialize Kubernetes to pickup new node ip address and hostname.
#sudo sed -i "s/controlPlaneEndpoint:.*/controlPlaneEndpoint: $kube_control_plane_endpoint/g" "$HOME/Documents/kubeadm-config.yaml"
sudo sed -i "s/.* control-plane-endpoint/$kube_control_plane_endpoint control-plane-endpoint/g" /etc/hosts
if [[ "$script_command" == "init" ]]; then
    sudo kubeadm init --config "$HOME/Documents/kubeadm-config.yaml" --upload-certs --ignore-preflight-errors=NumCPU --ignore-preflight-errors=Mem
else
    if [[ "$is_control_plane" == "True" ]]; then
        # TODO: Maybe do not send entire kubeadm join command as a sting so it does not need to be evaluated here.
        join_command_key="sudo $kubeadm_join_command --control-plane --ignore-preflight-errors=NumCPU --ignore-preflight-errors=Mem --certificate-key $kubeadm_join_cert_key"
    else
        # TODO: Maybe do not send entire kubeadm join command as a sting so it does not need to be evaluated here.
        join_command_key="sudo $kubeadm_join_command --ignore-preflight-errors=NumCPU --ignore-preflight-errors=Mem"
    fi
    echo "$join_command_key"
    #echo $($join_command_key)
    eval "$join_command_key"
    echo "Joined."
fi

if [[ "$script_command" == "init" || "$is_control_plane" == "True" ]]; then
# https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/create-cluster-kubeadm/
# START OF COPYRIGHT UNCLAIMABLE MATERIAL. Public domain.
    mkdir -p $HOME/.kube
    sudo cp /etc/kubernetes/admin.conf $HOME/.kube/config # "cp -i ..." to ask confirmation
    sudo chown $(id -u):$(id -g) $HOME/.kube/config
# END OF COPYRIGHT UNCLAIMABLE MATERIAL.
    if [[ "$allow_workloads" == "True" ]]; then
        kubectl taint nodes $(hostname) node-role.kubernetes.io/control-plane:NoSchedule-
    fi
fi

if [[ "$script_command" == "init" ]]; then
    # Reinitialize networking to pickup new node ip address and hostname.
    cilium install --version 1.15.7
fi

echo "###############################################################################"
echo "Finished Kubernetes Node Initialization Script."
echo "###############################################################################"
