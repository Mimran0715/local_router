The router will work on 40 assigned coding tasks (to start with). These were generated via some of my project repos. Each task is represented in JSON and has a verifier via pytest / unitttest. 

The router must decide between using Codex and Ollama coding models based on: latency, cost (Codex, quota consumed on a basic subscription), and quality. 

The router will use the Nimble decision model. 

Evaluation will be based on latency, and quota usage. 

Each coder model will create a git worktree (task_modelname) for each task. 
