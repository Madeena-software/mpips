# Server Access Constraints

## Strict Prohibition

Direct server access via SSH is explicitly prohibited. Assume production and
staging environments may be behind CGNAT, firewall restrictions, or other
managed network boundaries. Agents must not attempt SSH access and must not
suggest SSH commands as a deployment or troubleshooting path.

## Infrastructure And Deployment

- All deployment and infrastructure changes must be performed through CI/CD
  pipelines or configuration files committed to Git.
- Infrastructure configuration changes must be represented in repository files
  such as `Dockerfile`, `docker/entrypoint.sh`, environment examples,
  deployment manifests, or workflow definitions.
- The repository currently has no detected `.github/workflows/` files. Add or
  confirm CI/CD before relying on automated deployment.
- To change runtime behavior, modify committed configuration or environment
  examples and let the deployment pipeline apply the change.
- Never put production secrets in the repository. Use environment variables or
  the deployment platform's secret store.

## Operational Debugging

- Prefer local reproduction, automated tests, logs collected by the platform,
  and committed configuration changes.
- If a production issue appears to require shell access, stop and ask for an
  approved non-SSH operational route such as CI job logs, container logs,
  metrics, or a deployment platform console action performed by a human.
