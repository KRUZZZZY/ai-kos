# **Comparative Architectural Evaluation of Zero-Trust Remote Access Systems: Hardening AWS Systems Manager vs. Transitioning to Tailscale and Headscale Mesh Protocols**

## **Baseline Assessment of the SSM-IN Tunnelling Infrastructure**

The remote access paradigm of the infrastructure relies on a single shared entry point designated as SSM-IN (Instance ID: i-060849b28c68f125e), operating within AWS Account 720774751067 in the eu-west-1 (Ireland) region. This host acts as the primary gateway for both the internal operations team and an external development team. It is deployed in the public subnet of the client web virtual private cloud (VPC) and bridged to a broader hub network via peered VPC connections. The technical attributes of this host, verified as of June 25, 2026, are detailed in the table below.

| Parameter | Operational Value |
| :---- | :---- |
| **Instance ID** | i-060849b28c68f125e |
| **Name Tag** | SSM-IN |
| **Instance Type** | t2.micro (1 vCPU / 1 GB RAM, burstable CPU credits) |
| **Launch Date** | 2023-05-11 (Maintained as an unreplaced, long-lived host) |
| **Operating System** | Ubuntu 24.04 LTS |
| **Availability Zone** | eu-west-1b |
| **Subnet Association** | subnet-0bfb9ac84c0272fdd (Publicly routed, target of internet gateway 0.0.0.0/0 route) |
| **VPC Association** | vpc-0011e80b5d8421413 |
| **VPC Peering Connection** | pcx-0bad874e6afea14bc (Bridging traffic to the 10.10.0.0/16 Hub VPC) |
| **Private IP Address** | 10.0.1.185 |
| **Public IP Address** | 34.244.233.73 (Dynamically allocated, auto-assigned; non-Elastic IP) |
| **Security Group** | sg-0c59b063dac2f017d ("VPC SSM Server") |
| **IAM Instance Profile** | AmazonSSMRoleForInstancesQuickSetup |
| **SSM Agent Runtime Version** | 3.3.4121.0 (Managed via Ubuntu snap package on latest/stable auto-updating track) |
| **AWS Systems Manager Status** | Online (PingStatus validated) |

The access pattern for the system requires users to execute a start-session API call via the AWS Command Line Interface (CLI) to initiate a local port-forwarding tunnel to port 22 on the target. From there, users establish a secure shell (SSH) session through the local loopback interface and tunnel onward to internal private resources. This reliance on a static target command string underpins the strict constraint that the target instance ID must remain unchanged.

## **Traffic Proxying Analysis and Service Mapping**

The SSM-IN server does not operate as an isolated shell landing zone; rather, it functions as a multi-target TCP gateway. The security group sg-0c59b063dac2f017d ("VPC SSM Server") restricts incoming traffic while permitting unrestricted routing from designated internal security groups. The inbound and outbound routing associations are detailed below.

| Source Security Group / Resource | ID | Protocol and Port | Functional Purpose |
| :---- | :---- | :---- | :---- |
| **VPC Backup Server (AIM Server)** | sg-04a0da01af166ea07 | TCP 22 | Administrative and Backup SSH Synchronizations |
| **VPC Dev Server** | sg-0e7c915b30c5851a6 | All Protocols / Ports | Development Environment Routing |
| **Amazon WorkSpaces Members** | sg-063cef4520003c4e3 | All Protocols / Ports | Remote Desktop Infrastructure Access |
| **VPC File Server** | sg-02cb8b61a14f7adcc | All Protocols / Ports | Central File Storage Resource Mounting |

Active socket connections on the host reveal that it proxies traffic to several unmanaged targets that do not (or cannot) run the Systems Manager agent natively1.

| Target Private IP Address | Protocol and Port | Target Workload Association |
| :---- | :---- | :---- |
| 10.0.3.32 | TCP 1433 | Microsoft SQL Server (MSSQL Database) |
| 10.0.1.227 | TCP 2049 | Network File System (NFS File Server) |
| 10.0.1.130 | TCP 22 | Private Downstream Secure Shell Target |
| 10.0.1.108 | TCP 443 | Private Internal Web Target and Port 443 Egress |

Because these resources do not run the Systems Manager agent, they cannot be targeted directly using standard AWS systems management sessions. Therefore, a centralized jump host or proxy layer remains a necessary component of the current network design.

## **Failure Analysis and Root Cause of Memory Exhaustion**

Historical downtime logs indicate that the SSM-IN instance experienced recurrent overnight drops in management connectivity. Diagnostic analysis shows that the primary bottleneck is a deficit in physical memory, while CPU capacity is underutilized. Over any given 24-hour window, CPU utilization averages below 4%, with rare spikes peaking at 27%. The instance's CPU credit balance remains at its maximum cap of 144 credits, confirming that CPU burst limits are not a factor in these outages.  
An evaluation of the host's memory state under active load reveals a highly constrained operating environment.

| Memory Metric | Value |
| :---- | :---- |
| **Total Physical RAM** | 954 MB |
| **Active Concurrent Logged-in Users** | 13 |
| **Total Running sshd Processes** | 27 |
| **Total Running ssm-session-worker Processes** | 8 |
| **Interactive Terminal Sessions (who)** | 1 (The remaining sessions are non-interactive port-forwarding tunnels) |
| **Available Operating System Memory** | Approximately 368 MB |

The memory footprint on the host scales linearly with the number of concurrent, active tunnel sessions. Prior to recent remediation, the operating system lacked a configured swapfile. Consequently, during overnight windows, automated system tasks (such as unattended package upgrades managed by systemd timers) introduced minor memory spikes. In the absence of virtual memory page-out space, the Linux kernel Out-of-Memory (OOM) killer was forced to terminate high-priority memory-consuming processes. The kernel repeatedly targeted the amazon-ssm-agent snap service, rendering the host instantly offline and removing the primary mechanism for remote administrative recovery.  
The current workaround consists of:

> * The manual generation and mounting of a persistent 2 GB swapfile (/swapfile) integrated into /etc/fstab to absorb overnight execution spikes.  
> * Ensuring the SSM agent tracks the latest stable version (currently 3.3.4121.0), which contains several internal memory management and leak prevention updates.

The current workaround configuration has temporarily stabilized the host, resulting in zero OOM events and stable uptimes over recent observation windows. However, running a critical, multi-user gateway on a 1 GB instance without automated failover or service-level redundancy represents an architectural risk.  
Regarding software versions, the operational task log notes that the SSM agent was updated to version 3.3.4624.0. However, live host queries indicate the active agent version is actually 3.3.4121.0. This difference is not an unauthorized downgrade, but rather a characteristic of Snap latest/stable management, which dynamically reconciles to the stable channel upstream.

## **In-Situ Optimization and Hardening of the SSM Architecture**

Before exploring external mesh architectures, the existing SSM-managed infrastructure can be significantly hardened. This strategy focuses on expanding physical host capacity, enforcing automatic process recovery, reaping stale connection assets, and integrating monitoring telemetry.

### **Non-Disruptive Virtualization Tier Scaling**

The single most effective action to eliminate memory pressure is to scale the virtual instance type. This operation can be performed without altering the unique Instance ID i-060849b28c68f125e. By executing an instance stop sequence, modifying the instance type attribute, and executing a start sequence, the underlying hypervisor preserves the instance's metadata, IAM profile bindings, and Instance ID.  
A transition from the legacy, Xen-based t2.micro type to a Nitro-based instance type—such as the t3a.small or the t3.medium—delivers immediate performance and reliability improvements.

| Parameter | Original Type (t2.micro) | Proposed Standard (t3a.small) | Proposed High-Capacity (t3.medium) |
| :---- | :---- | :---- | :---- |
| **vCPU Allocation** | 1 (burstable, Xen architecture) | 2 (burstable, Nitro architecture) | 2 (burstable, Nitro architecture) |
| **RAM Capacity** | 1.0 GB | 2.0 GB | 4.0 GB |
| **Hypervisor Interface** | Xen Hypervisor | AWS Nitro System | AWS Nitro System |
| **Auto-Recovery Support** | Xen Metric Alarm | Native Hardware-Assisted Auto-Recovery | Native Hardware-Assisted Auto-Recovery |
| **Estimated Monthly Cost** | \~$8.50 USD (eu-west-1) | \~$7.00 USD (eu-west-1, AMD discount) | \~$15.20 USD (eu-west-1) |

The t3a.small instance type is highly cost-effective, doubling physical memory allocation while reducing the hourly runtime cost below that of the legacy t2.micro. Additionally, the Nitro architecture supports native hardware-assisted auto-recovery. In the event of underlying hypervisor hardware failure, AWS automatically recreates the virtual instance on healthy hardware. This process fully preserves the Instance ID, the root volume data, and the private IPv4 configuration (10.0.1.185), minimizing recovery time objectives (RTO).  
It is important to note that stopping and starting the instance will cause the auto-assigned public IP address (34.244.233.73) to change. However, because Systems Manager establishes outbound persistent TCP connections to AWS endpoints, the changing public IP will have no effect on SSM-based connectivity2. If any team members bypass SSM to connect to the public IP directly, this pathway must be transitioned to an Elastic IP (EIP) or deleted to improve security.

### **Service-Level Recovery and Session Lifecycle Management**

To prevent the accumulation of abandoned connections and ensure the absolute survivability of the SSM agent, the Ubuntu operating system configuration should be hardened.

#### **Enforcing Daemon Recovery Actions**

The SSM agent is managed via a snap package. System engineers should verify that the underlying systemd service file enforces automated restarts under all failure conditions. This is achieved by creating a systemd override directory and configuring restart parameters:

Ini, TOML  
\# /etc/systemd/system/snap.amazon-ssm-agent.amazon-ssm-agent.service.d/override.conf  
\[Service\]  
Restart=always  
RestartSec=5s  
OOMScoreAdjust=-900

Setting OOMScoreAdjust to a highly negative value heavily deprioritizes the daemon during an OOM event, ensuring the Linux kernel terminates interactive client shells (sshd) or utility cron processes before interrupting the control plane agent.

#### **Reaping Inactive SSH Tunnels**

The current memory footprint is artificially inflated by stale client sessions that remain open indefinitely. This idle session accumulation can be mitigated by enforcing host-level timeouts inside the SSH configuration file /etc/ssh/sshd\_config:

Ini, TOML  
ClientAliveInterval 60  
ClientAliveCountMax 3

With this configuration, the SSH daemon transmits encrypted keep-alive null packets every 60 seconds. If a client terminal is closed or suffers a network drop and fails to respond to three consecutive probes, the daemon automatically terminates the child process and reclaims the allocated memory.

#### **Establishing Observability and Metric Ingestion**

Standard AWS EC2 CloudWatch metrics only monitor hypervisor-visible statistics, such as CPU utilization and network I/O. They cannot inspect internal OS memory allocation or swap utilization. To prevent unexpected outages, the unified AWS CloudWatch Agent must be deployed on the host to monitor RAM and swap states2.  
An alert threshold should be configured in CloudWatch:  
![][image1]  
This alert provides early warning of high memory utilization before the system is forced to swap or trigger the kernel OOM-killer.

### **Boundary Isolation and VPC Ingress/Egress Security**

The SSM-IN host currently exposes an auto-assigned public IP address to the internet. While its inbound security group configuration blocks public ingress, exposing a public IP on a jump host violates the principle of least privilege. Under standard AWS security best practices, the public IP should be removed, and the instance should be moved to a private subnet2.  
However, because the subnet is public (0.0.0.0/0 routed to the Internet Gateway) and the VPC lacks a NAT Gateway or VPC Endpoints, the instance currently relies on its public IP to establish outbound HTTPS connections to the AWS Systems Manager API endpoints2. Removing the public IP requires one of two architectural modifications:

> * **The NAT Gateway Approach**: The instance is moved to a private subnet, and outbound traffic is routed through a managed AWS NAT Gateway deployed in a public subnet4. This setup carries an estimated cost of approximately $32.00 USD per month in the eu-west-1 region, plus data processing fees.  
> * **The VPC Endpoints (AWS PrivateLink) Approach**: The public IP is removed, and three interface endpoints are provisioned inside the VPC2:  
  * com.amazonaws.eu-west-1.ssm  
  * com.amazonaws.eu-west-1.ssmmessages  
  * com.amazonaws.eu-west-1.ec2messages

This configuration permits the SSM agent to register and communicate with the Systems Manager service entirely within the AWS private network backbone, bypassing the public internet2. Interface endpoints are priced at approximately $21.00 USD per month in the eu-west-1 region, plus data transfer fees.  
Because the security group already blocks direct inbound public access, removing the public IP is not an immediate requirement. However, implementing the VPC endpoint approach is a highly secure, long-term improvement that aligns with a true zero-trust model2.

## **Zero-Trust Peer-to-Peer Mesh VPN: Tailscale and Headscale**

To address the single point of failure inherent in a jump host model, the enterprise can evaluate the implementation of a peer-to-peer mesh Virtual Private Network (VPN) built on the open-source WireGuard protocol5. This can be achieved through either Tailscale’s managed SaaS platform or Headscale, the community-driven, self-hosted control plane alternative5.  
The fundamental structural difference is that the coordination server acts exclusively as an out-of-band control plane5. It handles node registration, public cryptographic key distribution, split DNS policies, access control rule compilation, and NAT traversal coordination (via STUN and DERP relay servers)5. Actual user traffic flows directly peer-to-peer between client endpoints, fully encrypted with WireGuard5. The coordination server is entirely excluded from the data plane path and cannot inspect, decrypt, or intercept client data5.

| Architectural Feature | Tailscale (SaaS Platform) | Headscale (Self-Hosted Control Plane) |
| :---- | :---- | :---- |
| **Control Plane Hosting** | Managed SaaS (Hosted on Tailscale's global infrastructure)5 | Self-hosted on customer-managed virtual machines or Kubernetes5 |
| **Data Plane Architecture** | Encrypted peer-to-peer WireGuard tunnels5 | Encrypted peer-to-peer WireGuard tunnels (Identical data plane performance)5 |
| **Client Software Compatibility** | All official clients (macOS, iOS, Windows, Android, Linux)3 | Fully compatible with all unmodified official Tailscale clients5 |
| **Authentication & Identity Integration** | Integrated Identity Providers (OIDC, Okta, Microsoft Entra ID, Google Workspace)6 | OpenID Connect (OIDC) support via configuration (Authentik, Keycloak, Authelia)5 |
| **Access Control Mechanism** | Advanced centralized policy files supporting legacy ACLs and newer Grants11 | Standard ACLs and Grants (With structural compatibility limitations)11 |
| **High Availability Support** | Natively highly available, geographically distributed hosted SaaS5 | No native HA; single-writer architecture requiring external clustering tools12 |
| **Secure Shell (SSH) Session Orchestration** | Tailscale SSH with native identity integration and centralized key management14 | Experimental Tailscale SSH (Incomplete policy integration)5 |
| **Terminal Session Auditing & Recording** | Native tsrecorder engine with streaming export to AWS S315 | No native support; requires custom log aggregation or manual configurations17 |
| **Public Gateway Ingress (Funnel)** | Supported (Exposes private services securely to the public internet)5 | Unsupported natively5 |
| **DNS Management Mode** | Full MagicDNS with automated split-horizon DNS mappings9 | MagicDNS supported; custom static or dynamic extra record files19 |
| **Subnet Routing and Redundancy** | High availability failover natively managed via control plane21 | Subnet routing supported; failover requires manual database manipulation13 |
| **Administrative Tooling** | Polished graphical user interface with real-time analytics6 | Command-Line Interface (CLI) or third-party community web interfaces7 |

## **Core Policy Engine and Access Control Parity**

Both systems secure network routing by implementing a default-deny zero-trust posture11. Security administrators construct policy files in human-compatible JSON (HuJSON) format, which are compiled by the control plane into specific packet-filtering rules distributed directly to the clients for local enforcement11.  
While Tailscale fully supports both first-generation Access Control Lists and advanced, granular Application Grants (enabling application-layer policy decisions)11, Headscale's implementation has several functional gaps11.

### **The Posture Validation Deficit**

Tailscale supports device posture assessment rules, evaluating attributes such as OS version, auto-update status, local disk encryption, and Endpoint Detection and Response (EDR) agent integration before permitting a connection11. Headscale does not support any posture evaluation or posture-related stanzas in its policy engine11.

### **The IP Sets Omission**

Tailscale allows administrative grouping of arbitrary IP blocks and CIDRs inside an ipsets block for reference in global routing rules11. Headscale does not support IP sets, forcing administrators to construct individual, verbose routing rules for each external target network11.

### **The Self-Group Compiling Inefficiency**

The helper macro autogroup:self automatically allows a user to access only their own registered machines11. In Headscale, utilizing this autogroup triggers an inefficient compile sequence where filter rules are evaluated per-node rather than compiled as a unified matrix11. In networks with more than 100 devices, this can cause significant memory overhead and CPU spikes on the Headscale coordination node11.

## **Identity Provider and User Lifecycle Management**

Enterprise access control requires a single source of truth for identity management. Tailscale integrates directly with identity platforms, checking user group membership, multi-factor authentication (MFA) status, and employee offboarding state at each connection attempt9.  
Headscale implements OpenID Connect (OIDC) to enable single sign-on (SSO) via enterprise IdPs (including Microsoft Entra ID, Google Workspace, Authentik, or Authelia)23. However, Headscale has two significant OIDC limitations:

> * **No Dynamic Group Mappings**: Headscale cannot parse OIDC group claims to dynamically assign network access permissions in its policy file10. Although OIDC group claims can be parsed to filter who is *authorized to log into* the VPN overall (using allowed\_groups inside the configuration), once logged in, users cannot be dynamically assigned to specific Tailscale ACL groups based on their IdP groups10. Administrators must duplicate user group listings manually inside the Tailscale policy file.  
> * **The Provider Migration Database Barrier**: Headscale tracks and stores a unique, immutable provider\_identifier (derived from the token's iss and sub claims) in its database users table10. If the enterprise migrates to a different IdP (such as transitioning from Google Workspace to Entra ID), Headscale will register the users under the new provider identifiers10. However, the registration will fail because the username and email attributes conflict with the existing database profiles10. Resolving an IdP transition requires manual SQL operations to update the provider\_identifier column for every user record in the Headscale database10.

Modern security frameworks also require detailed logging of administrative actions on production servers.

### **Tailscale SSH Session Orchestration**

Tailscale SSH replaces static SSH keys and traditional authorization configurations (authorized\_keys) across the server fleet14. The local Tailscale daemon intercepts connections on port 22, validates the client’s identity against the central control plane, and provisions cryptographic, short-lived session keys on-the-fly14. While Headscale supports standard key distribution, its implementation of Tailscale SSH is officially categorized as experimental and lacks full policy integration5.

### **Session Recording Engine**

For compliance audits, Tailscale provides automated terminal session recording using a containerized service called tsrecorder15. When a user establishes an SSH connection, the target node streams terminal output in real-time in asciinema format to a customer-managed tsrecorder collector container15. The collector records metadata, timing data, and terminal output, storing the structured logs on a local filesystem or exporting them directly to an Amazon S3 bucket15.  
To configure S3-backed recording, an IAM policy must be attached to the container host instance profile:

JSON  
{  
  "Version": "2012-10-17",  
  "Statement": \[  
    {  
      "Effect": "Allow",  
      "Action": \[  
        "s3:PutObject",  
        "s3:GetBucketLocation",  
        "s3:GetObject",  
        "s3:ListBucket"  
      \],  
      "Resource": \[  
        "arn:aws:s3:::tailscale-ssh-audit-recordings",  
        "arn:aws:s3:::tailscale-ssh-audit-recordings/\*"  
      \]  
    }  
  \]  
}

The container can be run with the following parameters:

Bash  
docker run \-d \--name tsrecorder \\  
  \-e TS\_AUTHKEY=ts-authkey-example \\  
  \-e TSRECORDER\_BUCKET=tailscale-ssh-audit-recordings \\  
  \-v /var/lib/tsrecorder:/data \\  
  tailscale/tsrecorder:stable \\  
  /tsrecorder \--dst=s3://s3.eu-west-1.amazonaws.com \--statedir=/data/state \--ui

*Note: For deployments utilizing AWS IMDSv2, the hop limit must be configured to at least 2 to ensure the Docker container can query the EC2 instance profile metadata credentials.*  
This session recording architecture **cannot** be implemented natively with Headscale17. Headscale’s policy parser does not support parsing the recorder and enforceRecorder parameters within the SSH action blocks of the policy configuration17. Consequently, any attempt to define auditing targets inside a Headscale policy file will trigger configuration parsing errors, preventing the server from starting.

## **High Availability, Database Resiliency, and Disaster Recovery**

In zero-trust networking, the availability of the control plane dictates the stability of the entire network. If the coordination server goes offline, existing client connections remain active as long as their cryptographic keys remain valid12. However, no new nodes can authenticate, key rotation sequences fail, node posture validation checks halt, and changes to access policies cannot be distributed12.

### **Tailscale's Distributed SaaS Plane vs. Headscale's Monolithic Architecture**

Tailscale handles control plane availability natively through a multi-region, geographically distributed service level agreement (SLA)5. For the data plane, Tailscale supports native active-passive high availability failover for subnet routers21.  
When multiple subnet routers advertise the exact same IP prefix, Tailscale's coordination server designates the "primary" router based on chronological age (the oldest node registered in the tailnet is selected)21. If the primary router goes offline or loses connection for more than 15 seconds, the control plane automatically re-routes traffic to the oldest active standby router21.  
Conversely, Headscale is designed as a single-writer application and has no native high availability or active-active operational mode12. The coordination daemon assumes exclusive write-locks on its database, meaning multiple Headscale controller instances cannot run concurrently in an active-active configuration12.

### **Engineering Resiliency into a Headscale Control Plane**

To operate Headscale in a resilient production environment, platform engineers must build external failover and synchronization mechanisms.

#### **The Keepalived Virtual IP Design**

For on-premises virtual machine deployments, system engineers can deploy Keepalived on two distinct nodes, sharing a Virtual IP (VIP) address12. While only the primary node serves client requests, a health check daemon monitors the Headscale service. If the primary node fails, Keepalived dynamically migrates the VIP to the standby instance12. This standby instance mounts the shared backend database and takes over control plane coordination12.

#### **The LiteFS and Consul Distributed SQLite Model**

A highly resilient, self-healing architecture can be constructed by combining Consul with LiteFS to replicate the lightweight SQLite database across geographically separated hosts12.

> * **The Coordination Consensus**: A distributed Consul cluster manages automated leader elections12.  
> * **The Database Replication Layer**: SQLite database writes on the active primary node are replicated in real-time to secondary nodes using LiteFS, which streams write-ahead log (WAL) frames12.  
> * **The Failover Sequence**: If the active primary Headscale instance fails, Consul detects the loss of heartbeat, revokes the leadership key, and promotes a secondary node12. The newly promoted node mounts the replicated SQLite database and starts coordinating client keys12. This architecture achieves an RTO of approximately 15 seconds without requiring complex PostgreSQL clustering12.

#### **The PostgreSQL and Load Balancer Strategy**

Alternatively, Headscale can be configured to use a clustered PostgreSQL database backend13. Two Headscale application servers can be deployed behind an HTTP Load Balancer13. Because the Headscale application stores session states in memory, the load balancer must enforce strict sticky sessions13. If a node fails, the load balancer redirects client traffic to the surviving Headscale application instance, which queries the shared, highly available PostgreSQL database cluster13.

## **Operational Verification and Verification Playbook**

To ensure ongoing stability and maintain strict verification standards, the engineering team can utilize several automated AWS CLI and on-box diagnostic commands.

### **SSM-IN Structural Integrity Validation**

Bash  
\# Query baseline AWS instance metadata  
aws ec2 describe-instances \\  
  \--region eu-west-1 \\  
  \--instance-ids i-060849b28c68f125e

\# Extract live Systems Manager connection telemetry  
aws ssm describe-instance-information \\  
  \--region eu-west-1 \\  
  \--filters Key=InstanceIds,Values=i-060849b28c68f125e

### **Burstable CPU Credit Evaluation**

To verify that the host's performance drops are not caused by CPU exhaustion, engineers can run the following query to extract the minimum CPU credit balance over a designated three-hour window:

Bash  
aws cloudwatch get-metric-statistics \\  
  \--region eu-west-1 \\  
  \--namespace AWS/EC2 \\  
  \--metric-name CPUCreditBalance \\  
  \--dimensions Name=InstanceId,Value=i-060849b28c68f125e \\  
  \--start-time 2026-06-25T09:00:00Z \\  
  \--end-time 2026-06-25T12:00:00Z \\  
  \--period 10800 \\  
  \--statistics Minimum

### **On-Box Resource Diagnostics**

This automated script runs via Systems Manager to query internal OS memory metrics, active swap states, logged-in users, and active SSH processes:

Bash  
aws ssm send-command \\  
  \--region eu-west-1 \\  
  \--instance-ids i-060849b28c68f125e \\  
  \--document-name AWS-RunShellScript \\  
  \--parameters 'commands=\["free \-m", "swapon \--show", "who", "pgrep \-c sshd"\]'

### **Standard User and External Dev Access Commands**

Bash  
\# Establish an interactive shell on the jump host  
aws ssm start-session \\  
  \--region eu-west-1 \\  
  \--target i-060849b28c68f125e

\# Establish an encrypted tunnel targeting the private MSSQL server database instance  
aws ssm start-session \\  
  \--region eu-west-1 \\  
  \--target i-060849b28c68f125e \\  
  \--document-name AWS-StartPortForwardingSessionToRemoteHost \\  
  \--parameters '{"host":\["10.0.3.32"\],"portNumber":\["1433"\],"localPortNumber":\["11433"\]}'

## **Strategic Recommendations and Transition Matrix**

To address the single point of failure in the remote access architecture, the enterprise should execute a multi-phase remediation and migration strategy.

### **Recommendation 1: Scale and Harden the Existing SSM-IN Host (Immediate Action)**

The engineering team should immediately perform a scheduled, non-disruptive migration of the SSM-IN instance. This action addresses the critical single point of failure while preserving the Instance ID required by the external development team.

> * Stop the SSM-IN instance, upgrade its type from t2.micro to t3a.small (which doubles physical memory allocation and enables Nitro-based auto-recovery), and restart the instance.  
> * Deploy a systemd override file to prevent the kernel OOM killer from terminating the SSM agent during resource spikes.  
> * Configure active session reaping to automatically terminate idle SSH connections after 3 minutes of inactivity.  
> * Deploy the AWS CloudWatch agent to monitor internal OS memory and swap allocation, configuring alerts for high memory utilization.

### **Recommendation 2: Pilot Tailscale Subnet Routers (Medium-Term Migration)**

To transition away from a single-node bastion architecture, the organization should deploy a zero-trust mesh network.

> * Deploy two containerized Tailscale subnet routers across separate Availability Zones in the client VPC4.  
> * Configure the control plane to route private VPC subnet blocks through these routers, providing direct, encrypted connections to private resources without exposing public endpoints1.  
> * Integrate enterprise SSO and MFA to manage user authentication dynamically.  
> * Evaluate the implementation of Tailscale SSH and the tsrecorder engine to stream and store terminal audits in Amazon S315.

### **Recommendation 3: Choose Hosted Tailscale SaaS Over Self-Hosted Headscale**

The final choice between Tailscale's hosted platform and a self-hosted Headscale control plane depends on the organization's operational capacity and compliance guidelines.

> * **Tailscale SaaS is Recommended** for most organizations. This platform eliminates the overhead of managing a critical coordination server, providing built-in high availability, global scalability, robust device posture validation, and a compliant, out-of-the-box session auditing system5.  
> * **Headscale is Recommended Only** if strict compliance frameworks prohibit third-party SaaS integration. If the organization chooses to self-host the control plane, the engineering team must design, maintain, and secure the underlying coordination database and failover mechanisms (e.g., using LiteFS and Consul)12. Additionally, the team must accept the loss of advanced features like native device posture checks and audited session recording11.

#### **Works cited**

> 1. Subnet routers · Tailscale Docs, [https://tailscale.com/docs/features/subnet-routers](https://tailscale.com/docs/features/subnet-routers)  
> 2. AWS Bastion Hosts Obsolete? 2025 Secure Access Guide with SSM Session Manager & Tailscale | by Ismail Kovvuru | Medium, [https://medium.com/@ismailkovvuru/aws-bastion-hosts-obsolete-2025-secure-access-guide-with-ssm-session-manager-tailscale-07fd37592500](https://medium.com/@ismailkovvuru/aws-bastion-hosts-obsolete-2025-secure-access-guide-with-ssm-session-manager-tailscale-07fd37592500)  
> 3. How to Monitor and Visualize Failed SSH Access Attempts to Amazon EC2 Linux Instances | AWS Security Blog, [https://aws.amazon.com/blogs/security/how-to-monitor-and-visualize-failed-ssh-access-attempts-to-amazon-ec2-linux-instances/](https://aws.amazon.com/blogs/security/how-to-monitor-and-visualize-failed-ssh-access-attempts-to-amazon-ec2-linux-instances/)  
> 4. AWS reference architecture · Tailscale Docs, [https://tailscale.com/docs/reference/reference-architectures/aws](https://tailscale.com/docs/reference/reference-architectures/aws)  
> 5. Headscale vs Tailscale: Self-Hosted Control Plane \- DEV Community, [https://dev.to/selfhostingsh/headscale-vs-tailscale-self-hosted-control-plane-1h1f](https://dev.to/selfhostingsh/headscale-vs-tailscale-self-hosted-control-plane-1h1f)  
> 6. Headscale vs Tailscale: Which One Should You Choose? \- Startupik, [https://startupik.com/headscale-vs-tailscale-which-one-should-you-choose/](https://startupik.com/headscale-vs-tailscale-which-one-should-you-choose/)  
> 7. Headscale & Tailscale \- Lucas Janin, [https://www.lucasjanin.com/2025/01/03/headscale-tailscale-in-a-self-hosted-environment/](https://www.lucasjanin.com/2025/01/03/headscale-tailscale-in-a-self-hosted-environment/)  
> 8. Performance best practices · Tailscale Docs, [https://tailscale.com/docs/reference/best-practices/performance](https://tailscale.com/docs/reference/best-practices/performance)  
> 9. Tailscale on AWS: A Practical Guide to the Gotchas Nobody Warns You About \- yaw, [https://yaw.sh/blog/tailscale-aws-practical-guide-gotchas/](https://yaw.sh/blog/tailscale-aws-practical-guide-gotchas/)  
> 10. OpenID Connect \- Headscale, [https://headscale.net/stable/ref/oidc/](https://headscale.net/stable/ref/oidc/)  
> 11. Policy \- Headscale, [https://headscale.net/stable/ref/policy/](https://headscale.net/stable/ref/policy/)  
> 12. Headscale with sqlite as database with auto failover by LiteFS and Consul | Gawsoft, [https://gawsoft.com/blog/headscale-litefs-consul-replication-failover/](https://gawsoft.com/blog/headscale-litefs-consul-replication-failover/)  
> 13. \[Feature\] multiple replicas of headscale instances · Issue \#2695 \- GitHub, [https://github.com/juanfont/headscale/issues/2695](https://github.com/juanfont/headscale/issues/2695)  
> 14. Tailscale SSH: Set Up Secure Remote Access Without Managing Keys \- OneUptime, [https://oneuptime.com/blog/post/2026-01-27-tailscale-ssh/view](https://oneuptime.com/blog/post/2026-01-27-tailscale-ssh/view)  
> 15. Tailscale SSH session recording, [https://tailscale.com/docs/features/tailscale-ssh/tailscale-ssh-session-recording](https://tailscale.com/docs/features/tailscale-ssh/tailscale-ssh-session-recording)  
> 16. Send Tailscale SSH session recordings to S3, [https://tailscale.com/docs/features/tailscale-ssh/how-to/session-recording-s3](https://tailscale.com/docs/features/tailscale-ssh/how-to/session-recording-s3)  
> 17. Support SSH session recording configuration · Issue \#1793 · juanfont/headscale \- GitHub, [https://github.com/juanfont/headscale/issues/1793](https://github.com/juanfont/headscale/issues/1793)  
> 18. What is Split DNS & Why Should You Use It? \- Tailscale, [https://tailscale.com/learn/why-split-dns](https://tailscale.com/learn/why-split-dns)  
> 19. DNS \- Headscale, [http://headscale.net/0.23.0/ref/dns/](http://headscale.net/0.23.0/ref/dns/)  
> 20. DNS \- Headscale, [https://headscale.net/stable/ref/dns/](https://headscale.net/stable/ref/dns/)  
> 21. Set up high availability · Tailscale Docs, [https://tailscale.com/docs/how-to/set-up-high-availability](https://tailscale.com/docs/how-to/set-up-high-availability)  
> 22. Troubleshoot overlapping subnet route failover · Tailscale Docs, [https://tailscale.com/docs/reference/troubleshooting/network-configuration/overlapping-subnet-route-failover](https://tailscale.com/docs/reference/troubleshooting/network-configuration/overlapping-subnet-route-failover)  
> 23. Headscale Authentication with Google Workspace \- Linsomniac's Articles, [https://linsomniac.gitlab.io/post/2023-02-24-headscale\_authentication\_with\_google\_workspace/](https://linsomniac.gitlab.io/post/2023-02-24-headscale_authentication_with_google_workspace/)  
> 24. OIDC authentication \- Headscale, [https://headscale.net/0.25.0/ref/oidc/](https://headscale.net/0.25.0/ref/oidc/)  
> 25. Integrate with Headscale | authentik, [https://integrations.goauthentik.io/networking/headscale/](https://integrations.goauthentik.io/networking/headscale/)  
> 26. tsrecorder · Tailscale Docs, [https://tailscale.com/docs/features/tsrecorder](https://tailscale.com/docs/features/tsrecorder)  
> 27. PostgreSQL High Availability in Action | by Mehman Jafarov \- Medium, [https://medium.com/@mehmanjafarov1905/postgresql-high-availability-in-action-49aadf181549](https://medium.com/@mehmanjafarov1905/postgresql-high-availability-in-action-49aadf181549)

[image1]: <data:image/png;base64,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>