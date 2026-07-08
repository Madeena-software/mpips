# Server Access Constraints

## Strict Prohibition
**Direct server access via SSH is EXPLICITLY PROHIBITED.** 
This constraint is in place because the environment operates under CGNAT and firewall restrictions. AI Agents MUST NEVER attempt to SSH into production or staging environments, nor suggest SSH commands as part of a troubleshooting process.

## Infrastructure & Deployment
- All deployment and infrastructure changes MUST be performed strictly via CI/CD pipelines.
- Infrastructure configurations (e.g., Dockerfiles, `docker-compose.yml`, Nginx configs) must be committed to Git.
- To change server settings, modify the relevant configuration files in the repository and rely on the deployment pipeline to apply the changes.
