output "deploy_job_id" {
  description = "The ID of the local deployment trigger."
  value       = var.deploy_agents ? terraform_data.run_python_deployer[0].id : "skipped"
}
