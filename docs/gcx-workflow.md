# Typical gcx workflow

[gcx](https://github.com/grafana/gcx) is Grafana Cloud's CLI. Its `fleet`
provider talks to the same Fleet Management API as the GitOps sync in this
repo, which makes it the right tool for the two things git is bad at:
**inspecting live fleet state** and **break-glass changes during an incident**.

Rule of thumb for this repo:

| Task | Tool |
|---|---|
| Durable config changes | PR to `pipelines/` (GitOps sync) |
| Inspecting collectors, effective config, pipeline state | `gcx fleet ...` (read) |
| Temporary/emergency changes | `gcx fleet pipelines ...` (write, see caveats) |

## 0. One-time setup

```sh
# Point a context at your stack and authenticate
gcx config set contexts.fleet-demo.grafana.server https://<your-stack>.grafana.net
gcx config set contexts.fleet-demo.cloud.stack <your-stack>
gcx config use-context fleet-demo

# The fleet provider needs a Grafana Cloud token; the CI token
# (fleet-management:write) from the README works
gcx config set cloud.token <TOKEN>     # or: export GRAFANA_CLOUD_TOKEN=<TOKEN>

# Verify before doing anything
gcx config check
```

Use `--context fleet-demo` on any command instead of `use-context` if you
juggle multiple stacks.

## 1. Inspect the fleet

```sh
# All collectors with health and attributes — the three demo collectors
# show up here once `make up` is running
gcx fleet collectors list

# Drill into one: attributes, health, which pipelines matched
gcx fleet collectors get collector-prod-checkout -o yaml

# What configuration is deployed right now?
gcx fleet pipelines list
gcx fleet pipelines get baseline-hostmetrics -o yaml

# Tenant quotas (pipeline/collector limits)
gcx fleet tenant limits
```

Handy for scripting — every command takes `-o json` and `--json` field
selection (`--json '?'` lists available fields):

```sh
gcx fleet collectors list -o json --json 'name,attributes' | jq .
```

## 2. Verify a GitOps sync landed

After merging a change to `pipelines/`:

```sh
# Compare what's deployed against what's in git
gcx fleet pipelines get dev-otlp-debug -o yaml
git show main:pipelines/dev-otlp-debug.yaml
```

## 3. Break-glass: ad-hoc pipeline during an incident

Scenario: the `checkout` team's collectors are misbehaving and you want
detailed debug output from them *now*, without waiting for a PR cycle.

The pipeline manifests in this repo are already in the format the API (and
`gcx fleet pipelines create -f`) expects. A canary manifest targeting only
`team="checkout"` lives in [`examples/canary-checkout-debug.yaml`](../examples/canary-checkout-debug.yaml)
— note it's in `examples/`, not `pipelines/`, so the GitOps sync never touches
it:

```sh
# 1. Read current state first
gcx fleet pipelines list

# 2. Create the canary
gcx fleet pipelines create -f examples/canary-checkout-debug.yaml

# 3. Verify it deployed and only matched checkout collectors
gcx fleet pipelines get canary-checkout-debug -o yaml
gcx fleet collectors get collector-prod-checkout -o yaml

# 4. Investigate (make logs shows the extra debug output on checkout
#    collectors only), then clean up
gcx fleet pipelines delete canary-checkout-debug
```

## Caveats: gcx writes vs GitOps

- **Don't `gcx fleet pipelines update` a pipeline that lives in `pipelines/`.**
  The repo is the source of truth: the next merge touching `pipelines/**`
  re-syncs and silently reverts your out-of-band edit. If a change should
  stick, make it a PR.
- Ad-hoc pipelines created with gcx (like the canary) are outside the
  `otelcol-fleet-demo` sync namespace, so the GitHub Action won't delete
  them — but that also means *you* own their cleanup.
- Give ad-hoc pipelines an obvious prefix (`canary-`, `incident-`) so they're
  easy to spot and reap in `gcx fleet pipelines list`.
