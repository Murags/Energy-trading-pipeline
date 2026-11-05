# Investigation: Fargate dashboard public IP timeout

## Hand-off Brief

1. **What happened.** Confirmed: the dashboard container started successfully, but its task was launched in the default VPC with the default security group, which does not allow inbound TCP 8501.
2. **Where the case stands.** Concluded with high confidence; the deployed application is healthy and the timeout is caused by the task's manually selected network configuration.
3. **What's needed next.** Stop this task and launch a replacement using the Terraform-managed subnet `subnet-08a0d495a82a3d217` and security group `sg-00407df26da4f2db8`.

## Case Info

| Field | Value |
| --- | --- |
| Ticket | N/A |
| Date opened | 2026-11-05 |
| Status | Concluded |
| System | AWS ECS Fargate, eu-central-1, cluster `energy-trading-pipeline-dashboard` |
| Evidence sources | ECS task description, EC2 ENI/subnet/security-group descriptions, CloudWatch logs, HTTP connection test |

## Problem Statement

User reported that the public IP assigned to the manually started dashboard task took too long to respond.

## Evidence Inventory

| Source | Status | Notes |
| --- | --- | --- |
| ECS task | Available | Task `d21e87b4b4134bf5b2455a27bf5de33a` is RUNNING. |
| CloudWatch dashboard logs | Available | Streamlit reported startup on `0.0.0.0:8501` at 2026-11-05 05:47:20 UTC. |
| ECS task ENI | Available | ENI `eni-0d6fa0469f8d62e18` uses default VPC/subnet/security group. |
| Terraform-managed network | Available | Expected subnet and security group were compared with the task attachment. |
| HTTP probe | Available | Port 8501 on public IP timed out after five seconds. |

## Investigation Backlog

| # | Path to Explore | Priority | Status | Notes |
| - | --- | --- | --- | --- |
| 1 | Verify container startup | High | Done | Streamlit is listening on all interfaces at port 8501. |
| 2 | Verify task network attachment | High | Done | Wrong VPC, subnet, and security group selected. |
| 3 | Verify expected ingress restriction | High | Done | Terraform SG permits TCP 8501 from `197.232.120.194/32`. |

## Timeline of Events

| Time | Event | Source | Confidence |
| --- | --- | --- | --- |
| 2026-11-05 05:47:18 UTC | ECS task started | ECS task description | Confirmed |
| 2026-11-05 05:47:20 UTC | Server started on `0.0.0.0:8501` | CloudWatch logs | Confirmed |
| 2026-11-05 investigation | HTTP connection to public IP port 8501 timed out | Direct probe | Confirmed |

## Confirmed Findings

### Finding 1: Application startup succeeded

**Evidence:** CloudWatch log timestamp 2026-11-05 05:47:20 UTC.

**Detail:** The container reports `Uvicorn server started on 0.0.0.0:8501` and an external URL, so application startup is not the cause.

### Finding 2: Task used the wrong network configuration

**Evidence:** ECS attachment and EC2 ENI descriptions observed on 2026-11-05.

**Detail:** The running task uses subnet `subnet-0ba29dc43f8a67585`, VPC `vpc-0eabe0f1eef8301e7`, and default security group `sg-02d5316b0e9dcc470`. The deployment outputs require subnet `subnet-08a0d495a82a3d217`, VPC `vpc-0167e701dcac546d6`, and security group `sg-00407df26da4f2db8`.

### Finding 3: Expected security group has the required restricted ingress

**Evidence:** EC2 security-group description observed on 2026-11-05.

**Detail:** `sg-00407df26da4f2db8` allows TCP 8501 from `197.232.120.194/32`; the running ENI does not use this group.

## Deduced Conclusions

### Deduction 1: Network selection causes the timeout

**Based on:** Findings 1–3.

**Reasoning:** The application is listening, the public IP exists, but the ENI uses a security group without the deployment's inbound rule.

**Conclusion:** Re-launching with the Terraform-managed subnet and security group should make the dashboard reachable from the allowed source IP.

## Hypothesized Paths

### Hypothesis 1: Application startup is taking too long

**Status:** Refuted

**Theory:** Streamlit had not finished starting.

**Resolution:** CloudWatch confirms startup completed at 05:47:20 UTC.

### Hypothesis 2: The source public IP has changed

**Status:** Open

**Theory:** After correcting the task network, access could still fail if the reviewer's current public IP is no longer `197.232.120.194`.

**Would confirm:** Current client public IP differs from the security-group CIDR.

**Would refute:** Current client public IP is `197.232.120.194` and the corrected task is reachable.

## Missing Evidence

| Gap | Impact | How to Obtain |
| --- | --- | --- |
| User's current public IP | Could explain a timeout after the network correction | Visit `https://checkip.amazonaws.com` from the browser being used. |

## Source Code Trace

| Element | Detail |
| --- | --- |
| Error origin | AWS task network configuration, not application source |
| Trigger | Manual ECS Run task configuration |
| Condition | Default VPC subnet and default security group selected |
| Related files | `infrastructure/terraform/network.tf`, `infrastructure/terraform/README.md` |

## Conclusion

**Confidence:** High

The timeout is caused by the task's wrong subnet and security group. The container is healthy and listening on port 8501. A secondary source-IP mismatch remains possible only after the task is relaunched with the correct network settings.

## Recommended Next Steps

### Fix direction

Stop the current task and launch a replacement in subnet `subnet-08a0d495a82a3d217` with security group `sg-00407df26da4f2db8` and public IP assignment enabled.

### Diagnostic

If the corrected task still times out, compare the browser client's current public IP with `197.232.120.194/32`.

## Reproduction Plan

Run the task with the default VPC/default security group and observe that Streamlit starts while TCP 8501 times out. Re-run it with the Terraform-managed subnet/security group and verify `http://<public-ip>:8501` responds from the allowed source address.

## Side Findings

- The running task incurs Fargate and public IPv4 charges until stopped.

## Follow-up: 2026-11-05

### New Evidence

- The incorrectly networked task was stopped.
- Replacement task `b73af296cc0349f9abe7b53616aef2f7` was launched in `subnet-08a0d495a82a3d217` with security group `sg-00407df26da4f2db8` and public IP assignment enabled.
- ECS reported the replacement RUNNING, and CloudWatch confirmed Streamlit listening on `0.0.0.0:8501`.
- An HTTP probe to `http://3.121.215.178:8501` returned `HTTP/1.1 200 OK` at 2026-11-05 06:03:03 UTC.

### Updated Conclusion

The diagnosis and correction are verified. The dashboard is reachable through the corrected task network configuration.
